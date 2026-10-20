from __future__ import annotations

import pytest

from src.core.audit import MemoryAuditSink
from src.core.event_queue import DurableEventQueue
from src.core.flow_control import RateLimitPolicy
from src.core.gateway_errors import GatewayRejected, GatewayRejectionCode
from src.core.isolation_policy import IsolationPolicy
from src.core.neural_gateway import NeuralSignalGateway
from src.core.neural_message import MessageKind, NeuralMessage
from src.core.plugin_health import HealthKey, HealthState, PluginHealthMonitor
from src.core.plugin_manifest import load_manifest
from src.core.plugin_registration import PluginGrant


def _gateway(tmp_path, *, rate_limit_policy=None, audit_sink=None):
    manifest = load_manifest(
        {
            "plugin_id": "peripheral.window.activity",
            "version": "1.0.0",
            "protocol_version": "1.0",
            "runtime": {"kind": "python", "entrypoint": "example:Plugin"},
            "capabilities": ["window.geometry_changed"],
            "signal_schemas": ["window.geometry_changed@1"],
            "permissions": [],
            "privacy": {"classification": "metadata_only"},
        }
    )
    gateway = NeuralSignalGateway(
        DurableEventQueue(tmp_path / "signals.db"),
        rate_limit_policy=rate_limit_policy,
        audit_sink=audit_sink,
    )
    gateway.register(manifest, PluginGrant.create(manifest.plugin_id, manifest.capabilities))
    session = gateway.open_session(manifest.plugin_id, "window-test", manifest.manifest_digest)
    return gateway, session


def _message(session, *, correlation_id=None):
    return NeuralMessage(
        kind=MessageKind.EVENT,
        source=session.plugin_id,
        topic="window.geometry_changed",
        payload_schema="window.geometry_changed@1",
        payload={"changes": []},
        correlation_id=correlation_id,
    )


def test_rate_limit_rejects_before_queue_and_isolated_by_session(tmp_path):
    def clock():
        return 100.0

    gateway, first = _gateway(
        tmp_path, rate_limit_policy=RateLimitPolicy(capacity=1, refill_per_second=1, clock=clock)
    )
    second = gateway.open_session(first.plugin_id, "other-window", first.manifest_digest)
    gateway.publish(_message(first), first)
    with pytest.raises(GatewayRejected) as rejected:
        gateway.publish(_message(first), first)
    assert rejected.value.code is GatewayRejectionCode.RATE_LIMITED
    assert len(gateway.queue.pending()) == 1
    gateway.publish(_message(second), second)
    assert len(gateway.queue.pending()) == 2


def test_audit_is_redacted_and_failure_fails_closed(tmp_path):
    sink = MemoryAuditSink()
    gateway, session = _gateway(tmp_path, audit_sink=sink)
    gateway.publish(_message(session, correlation_id="do-not-audit-this"), session)
    assert "do-not-audit-this" not in repr(sink.events)
    assert "payload" not in sink.events[0].__dataclass_fields__

    class BrokenSink:
        def record(self, event):
            raise OSError("audit offline")

    blocked, blocked_session = _gateway(tmp_path / "blocked", audit_sink=BrokenSink())
    with pytest.raises(GatewayRejected) as rejected:
        blocked.publish(_message(blocked_session), blocked_session)
    assert rejected.value.code is GatewayRejectionCode.AUDIT_UNAVAILABLE
    assert blocked.queue.pending() == []

    with pytest.raises(GatewayRejected):
        gateway.publish(
            NeuralMessage(
                kind=MessageKind.EVENT,
                source="forged secret title",
                topic="secret-path-or-title",
            ),
            session,
        )
    rejected_audit = sink.events[-1]
    assert rejected_audit.source is None
    assert rejected_audit.topic is None
    assert "secret" not in repr(rejected_audit)

    with pytest.raises(GatewayRejected):
        gateway.publish(
            NeuralMessage(
                kind=MessageKind.EVENT,
                source=session.plugin_id,
                topic="ungranted-secret-title",
            ),
            session,
        )
    assert sink.events[-1].topic is None
    assert "secret" not in repr(sink.events[-1])


def test_health_is_sticky_and_isolation_only_decides():
    now = [0.0]
    monitor = PluginHealthMonitor(
        degraded_after_rejections=1,
        paused_after_rejections=2,
        quarantined_after_rejections=3,
        clock=lambda: now[0],
    )
    key = HealthKey("peripheral.a", "instance-a")
    monitor.observe(key, accepted=False)
    assert monitor.assess(key).state is HealthState.DEGRADED
    monitor.observe(key, accepted=False)
    assert monitor.assess(key).state is HealthState.PAUSED
    monitor.observe(key, accepted=True)
    assert monitor.assess(key).state is HealthState.PAUSED
    monitor.observe(key, accepted=False)
    assert monitor.assess(key).state is HealthState.QUARANTINED
    decision = IsolationPolicy().decide(monitor.assess(key))
    assert decision.suppress_upstream is True
    monitor.reset(key)
    assert monitor.assess(key).state is HealthState.HEALTHY


def test_queue_failure_is_a_single_health_rejection_without_accepted_audit(tmp_path):
    sink = MemoryAuditSink()
    gateway, session = _gateway(tmp_path, audit_sink=sink)

    class FailingQueue:
        def enqueue(self, message):
            raise OSError("storage unavailable")

    gateway.queue = FailingQueue()
    with pytest.raises(GatewayRejected) as rejected:
        gateway.publish(_message(session), session)

    assert rejected.value.code is GatewayRejectionCode.QUEUE_UNAVAILABLE
    assert gateway.health_for(session.plugin_id, session.instance_id).rejection_count == 1
    assert all(event.outcome != "accepted" for event in sink.events)
    assert any(event.reason == GatewayRejectionCode.QUEUE_UNAVAILABLE.value for event in sink.events)
