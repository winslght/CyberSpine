"""Pure admission policy for messages from a registered plugin session."""
from __future__ import annotations

from datetime import timedelta

from .gateway_errors import GatewayRejected, GatewayRejectionCode
from .message_limits import MessageLimits
from .neural_message import NeuralMessage, PrivacyClass, utc_now
from .plugin_registration import PluginSession, RegistrationRegistry
from .schema_validation import validate_payload


class AdmissionPolicy:
    _PRIVACY_ORDER = {PrivacyClass.PUBLIC: 0, PrivacyClass.METADATA_ONLY: 1,
                      PrivacyClass.SENSITIVE: 2, PrivacyClass.RESTRICTED: 3}

    _MAX_FUTURE_SKEW = timedelta(minutes=5)

    def __init__(self, registry: RegistrationRegistry, limits: MessageLimits | None = None) -> None:
        self._registry = registry
        self._limits = limits or MessageLimits()

    def admit(self, message: NeuralMessage, session: PluginSession) -> NeuralMessage:
        manifest, grant = self._registry.validate_session(session)
        if message.protocol_version != manifest.protocol_version:
            raise GatewayRejected(GatewayRejectionCode.PROTOCOL_UNSUPPORTED)
        if message.source != session.plugin_id:
            raise GatewayRejected(GatewayRejectionCode.SOURCE_MISMATCH)
        if message.target is not None:
            raise GatewayRejected(GatewayRejectionCode.SOURCE_MISMATCH, "upstream peripheral messages cannot set target")
        if message.extensions:
            raise GatewayRejected(GatewayRejectionCode.SCHEMA_INVALID, "extensions are not granted")
        if message.topic not in grant.topics:
            raise GatewayRejected(GatewayRejectionCode.TOPIC_NOT_GRANTED)
        if message.kind not in grant.kinds:
            raise GatewayRejected(GatewayRejectionCode.KIND_NOT_GRANTED)
        if self._PRIVACY_ORDER[message.privacy] > self._PRIVACY_ORDER[grant.maximum_privacy]:
            raise GatewayRejected(GatewayRejectionCode.PRIVACY_EXCEEDED)
        if message.payload_schema not in manifest.signal_schemas:
            raise GatewayRejected(GatewayRejectionCode.SCHEMA_INVALID)
        if message.payload_schema.rsplit("@", 1)[0] != message.topic:
            raise GatewayRejected(GatewayRejectionCode.SCHEMA_INVALID)
        now = utc_now()
        if message.timestamp.tzinfo is None or message.timestamp.utcoffset() is None:
            raise GatewayRejected(GatewayRejectionCode.TIMESTAMP_INVALID, "timestamp must be timezone-aware")
        if message.timestamp > now + self._MAX_FUTURE_SKEW:
            raise GatewayRejected(GatewayRejectionCode.TIMESTAMP_INVALID, "timestamp exceeds future skew")
        if message.is_expired(now):
            raise GatewayRejected(GatewayRejectionCode.MESSAGE_EXPIRED)
        self._limits.validate_size(message)
        validate_payload(message.payload_schema, message.payload)
        return message
