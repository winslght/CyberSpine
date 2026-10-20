"""统一神经信号网关：插件进入主干的唯一准入点。"""

from dataclasses import dataclass
from datetime import timedelta
from typing import FrozenSet, Iterable, Optional

from .audit import AuditSink, MemoryAuditSink, audit_event
from .event_queue import DurableEventQueue, QueueItem
from .flow_control import RateLimitPolicy
from .gateway_admission import AdmissionPolicy
from .gateway_errors import GatewayRejected, GatewayRejectionCode
from .neural_message import MessageKind, NeuralMessage, PrivacyClass, utc_now
from .plugin_health import HealthKey, HealthState, PluginHealthMonitor
from .plugin_manifest import PluginManifest
from .plugin_registration import PluginGrant, PluginSession, RegistrationRegistry


@dataclass(frozen=True)
class PeripheralRegistration:
    """一个末梢神经可发布的消息范围。topic 目前采用精确匹配。"""

    source: str
    topics: FrozenSet[str]
    kinds: FrozenSet[MessageKind] = frozenset(
        {MessageKind.STATE, MessageKind.EVENT, MessageKind.HEALTH}
    )
    maximum_privacy: PrivacyClass = PrivacyClass.METADATA_ONLY

    @classmethod
    def create(
        cls,
        source: str,
        topics: Iterable[str],
        kinds: Optional[Iterable[MessageKind]] = None,
        maximum_privacy: PrivacyClass = PrivacyClass.METADATA_ONLY,
    ) -> "PeripheralRegistration":
        return cls(
            source,
            frozenset(topics),
            frozenset(kinds) if kinds is not None else cls.kinds,
            maximum_privacy,
        )


class NeuralSignalGateway:
    """验证来源能力后，将合格消息写入持久队列。"""

    _SUPPORTED_PROTOCOLS = frozenset({"1.0"})
    _PRIVACY_ORDER = {
        PrivacyClass.PUBLIC: 0,
        PrivacyClass.METADATA_ONLY: 1,
        PrivacyClass.SENSITIVE: 2,
        PrivacyClass.RESTRICTED: 3,
    }
    _LEGACY_WINDOW_SOURCE = "peripheral.window.activity"
    _LEGACY_WINDOW_TOPICS = frozenset(
        {
            "window.current_state",
            "window.catalog",
            "window.focus_changed",
            "window.high_interaction_changed",
            "window.time_window_summary",
            "window.foreground_availability_changed",
            "window.geometry_changed",
        }
    )
    _LEGACY_KINDS = frozenset({MessageKind.STATE, MessageKind.EVENT, MessageKind.HEALTH})

    def __init__(
        self,
        queue: DurableEventQueue,
        *,
        session_ttl_seconds: int = 300,
        rate_limit_policy: RateLimitPolicy | None = None,
        audit_sink: AuditSink | None = None,
    ):
        self.queue = queue
        self.registry = RegistrationRegistry(session_ttl_seconds=session_ttl_seconds)
        self.admission = AdmissionPolicy(self.registry)
        self.flow_control = rate_limit_policy or RateLimitPolicy()
        self.health = PluginHealthMonitor()
        self.audit = audit_sink or MemoryAuditSink()
        self._registrations: dict[str, PeripheralRegistration] = {}

    def register(
        self,
        registration: PeripheralRegistration | PluginManifest,
        grant: PluginGrant | None = None,
    ) -> None:
        """Register either a legacy trusted built-in or a manifest plus local grant.

        ``PeripheralRegistration`` exists only for the original in-process reference
        peripheral. Any manifest-based plugin must subsequently present a session.
        """
        if isinstance(registration, PluginManifest):
            if grant is None:
                raise ValueError("manifest registration requires a local PluginGrant")
            self.registry.register(registration, grant)
            return
        if grant is not None:
            raise ValueError("legacy registration does not accept a PluginGrant")
        if (
            registration.source != self._LEGACY_WINDOW_SOURCE
            or not registration.topics
            or not registration.topics.issubset(self._LEGACY_WINDOW_TOPICS)
            or not registration.kinds.issubset(self._LEGACY_KINDS)
            or self._PRIVACY_ORDER[registration.maximum_privacy]
            > self._PRIVACY_ORDER[PrivacyClass.METADATA_ONLY]
        ):
            raise ValueError(
                "legacy registration is restricted to the built-in window reference contract"
            )
        self._registrations[registration.source] = registration

    def open_session(self, plugin_id: str, instance_id: str, manifest_digest: str) -> PluginSession:
        """Issue a short-lived session after a runtime has completed its hello check."""
        return self.registry.open_session(plugin_id, instance_id, manifest_digest)

    def publish(self, message: NeuralMessage, session: PluginSession | None = None) -> QueueItem:
        """Admit a signal before it can mutate the durable queue."""
        if session is not None:
            key = HealthKey(session.plugin_id, session.instance_id)
            session_is_trusted = False
            try:
                self.registry.validate_session(session)
                session_is_trusted = True
                accepted = self.admission.admit(message, session)
                assessment = self.health.assess(key)
                if assessment.state in {HealthState.PAUSED, HealthState.QUARANTINED}:
                    raise GatewayRejected(GatewayRejectionCode.INSTANCE_UNHEALTHY)
                self.flow_control.allow(session, accepted)
                self._record(
                    "admission",
                    "authorized",
                    session=session,
                    message=accepted,
                )
                try:
                    item = self.queue.enqueue(accepted)
                except Exception as error:
                    self._record(
                        "delivery",
                        "rejected",
                        session=session,
                        reason=GatewayRejectionCode.QUEUE_UNAVAILABLE.value,
                    )
                    raise GatewayRejected(GatewayRejectionCode.QUEUE_UNAVAILABLE) from error
                self.health.observe(key, accepted=True)
                return item
            except GatewayRejected as error:
                self.health.observe(key, accepted=False)
                registration = self.registry.registration_for(session.plugin_id)
                topic_is_granted = registration is not None and message.topic in registration[1].topics
                self._record(
                    "admission",
                    "rejected",
                    session=session if session_is_trusted else None,
                    message=(
                        message
                        if session_is_trusted
                        and message.source == session.plugin_id
                        and topic_is_granted
                        else None
                    ),
                    reason=error.code.value,
                )
                raise
        try:
            if self.registry.registration_for(message.source) is not None:
                raise GatewayRejected(
                    GatewayRejectionCode.SESSION_INVALID, "manifest plugins require a session"
                )
            accepted = self._admit_legacy(message)
            self._record("admission", "authorized", message=accepted)
            item = self.queue.enqueue(accepted)
            return item
        except GatewayRejected as error:
            registered = message.source in self._registrations
            topic_is_granted = registered and message.topic in self._registrations[message.source].topics
            self._record(
                "admission",
                "rejected",
                message=(
                    message
                    if topic_is_granted and message.source == self._LEGACY_WINDOW_SOURCE
                    else None
                ),
                reason=error.code.value,
            )
            raise

    def health_for(self, plugin_id: str, instance_id: str):
        return self.health.assess(HealthKey(plugin_id, instance_id))

    def _record(
        self,
        action: str,
        outcome: str,
        *,
        session: PluginSession | None = None,
        message: NeuralMessage | None = None,
        reason: str | None = None,
    ) -> None:
        """Fail closed before queue mutation if the trusted audit path is unavailable."""
        try:
            self.audit.record(
                audit_event(
                    action,
                    outcome,
                    plugin_id=session.plugin_id if session else None,
                    instance_id=session.instance_id if session else None,
                    source=message.source if message else None,
                    topic=message.topic if message else None,
                    reason=reason,
                )
            )
        except Exception as error:
            raise GatewayRejected(GatewayRejectionCode.AUDIT_UNAVAILABLE) from error

    def _admit_legacy(self, message: NeuralMessage) -> NeuralMessage:
        """Compatibility path for the pre-G1 in-process built-in reference plugin."""
        registration = self._registrations.get(message.source)
        if registration is None:
            raise GatewayRejected(GatewayRejectionCode.SESSION_INVALID, "unregistered source")
        if message.protocol_version not in self._SUPPORTED_PROTOCOLS:
            raise GatewayRejected(GatewayRejectionCode.PROTOCOL_UNSUPPORTED)
        if message.topic not in registration.topics:
            raise GatewayRejected(GatewayRejectionCode.TOPIC_NOT_GRANTED, "topic not granted")
        if message.kind not in registration.kinds:
            raise GatewayRejected(GatewayRejectionCode.KIND_NOT_GRANTED)
        if self._PRIVACY_ORDER[message.privacy] > self._PRIVACY_ORDER[registration.maximum_privacy]:
            raise GatewayRejected(
                GatewayRejectionCode.PRIVACY_EXCEEDED, "privacy level exceeds grant"
            )
        if message.target is not None:
            raise GatewayRejected(
                GatewayRejectionCode.SOURCE_MISMATCH,
                "upstream peripheral messages cannot set target",
            )
        now = utc_now()
        if message.timestamp.tzinfo is None or message.timestamp.utcoffset() is None:
            raise GatewayRejected(
                GatewayRejectionCode.TIMESTAMP_INVALID, "timestamp must be timezone-aware"
            )
        if message.timestamp > now + timedelta(minutes=5):
            raise GatewayRejected(
                GatewayRejectionCode.TIMESTAMP_INVALID, "timestamp exceeds future skew"
            )
        if message.is_expired(now):
            raise GatewayRejected(GatewayRejectionCode.MESSAGE_EXPIRED)
        return message
