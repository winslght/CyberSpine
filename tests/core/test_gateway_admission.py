from datetime import datetime, timedelta, timezone

import pytest

from src.core.event_queue import DurableEventQueue
from src.core.gateway_errors import GatewayRejected, GatewayRejectionCode
from src.core.neural_gateway import NeuralSignalGateway
from src.core.neural_message import MessageKind, NeuralMessage
from src.core.plugin_manifest import load_manifest
from src.core.plugin_registration import PluginGrant


def _too_deep_payload():
    value = "value"
    for _ in range(9):
        value = {"nested": value}
    return {"changes": [value]}


@pytest.fixture
def secured_gateway(tmp_path):
    manifest = load_manifest({
        "plugin_id": "peripheral.window.activity", "version": "1.0.0", "protocol_version": "1.0",
        "runtime": {"kind": "python", "entrypoint": "example:Plugin"},
        "capabilities": ["window.geometry_changed"], "signal_schemas": ["window.geometry_changed@1"],
        "permissions": [], "privacy": {"classification": "metadata_only"},
    })
    gateway = NeuralSignalGateway(DurableEventQueue(tmp_path / "signals.db"))
    gateway.register(manifest, PluginGrant.create(manifest.plugin_id, {"window.geometry_changed"}))
    return gateway, gateway.open_session(manifest.plugin_id, "example-1", manifest.manifest_digest)


def test_manifest_plugin_requires_valid_session_before_queue_mutation(secured_gateway):
    gateway, session = secured_gateway
    message = NeuralMessage(kind=MessageKind.EVENT, source=session.plugin_id, topic="window.geometry_changed",
                            payload_schema="window.geometry_changed@1", payload={"changes": []})
    item = gateway.publish(message, session)
    assert item.message.message_id == message.message_id

    with pytest.raises(GatewayRejected) as rejected:
        gateway.publish(message)
    assert rejected.value.code is GatewayRejectionCode.SESSION_INVALID
    assert len(gateway.queue.pending()) == 1


@pytest.mark.parametrize("changes, code", [
    ({"source": "peripheral.forged"}, GatewayRejectionCode.SOURCE_MISMATCH),
    ({"target": "spinal_hub"}, GatewayRejectionCode.SOURCE_MISMATCH),
    ({"topic": "other.topic", "payload_schema": "other.topic@1"}, GatewayRejectionCode.TOPIC_NOT_GRANTED),
    ({"kind": MessageKind.DIRECTIVE}, GatewayRejectionCode.KIND_NOT_GRANTED),
    ({"payload_schema": "window.geometry_changed@99"}, GatewayRejectionCode.SCHEMA_INVALID),
    ({"extensions": {"untrusted": True}}, GatewayRejectionCode.SCHEMA_INVALID),
    ({"timestamp": datetime.now()}, GatewayRejectionCode.TIMESTAMP_INVALID),
    ({"timestamp": datetime.now(timezone.utc) + timedelta(minutes=6)}, GatewayRejectionCode.TIMESTAMP_INVALID),
    ({"payload": _too_deep_payload()}, GatewayRejectionCode.MESSAGE_TOO_LARGE),
    ({"payload": {"changes": "x" * 8_193}}, GatewayRejectionCode.MESSAGE_TOO_LARGE),
    ({"payload": {"changes": [{"window_title": "secret"}]}}, GatewayRejectionCode.PRIVACY_EXCEEDED),
])
def test_admission_rejects_cross_boundary_messages_without_queue_mutation(secured_gateway, changes, code):
    gateway, session = secured_gateway
    values = {"kind": MessageKind.EVENT, "source": session.plugin_id, "topic": "window.geometry_changed",
              "payload_schema": "window.geometry_changed@1", "payload": {"changes": []}}
    values.update(changes)
    with pytest.raises(GatewayRejected) as rejected:
        gateway.publish(NeuralMessage(**values), session)
    assert rejected.value.code is code
    assert gateway.queue.pending() == []


def test_manifest_schema_without_registered_content_validator_cannot_enter_queue(tmp_path):
    manifest = load_manifest({
        "plugin_id": "peripheral.example", "version": "1.0.0", "protocol_version": "1.0",
        "runtime": {"kind": "python", "entrypoint": "example:Plugin"},
        "capabilities": ["example.changed"], "signal_schemas": ["example.changed@1"],
        "permissions": [], "privacy": {"classification": "metadata_only"},
    })
    gateway = NeuralSignalGateway(DurableEventQueue(tmp_path / "signals.db"))
    gateway.register(manifest, PluginGrant.create(manifest.plugin_id, {"example.changed"}))
    session = gateway.open_session(manifest.plugin_id, "example-1", manifest.manifest_digest)
    with pytest.raises(GatewayRejected) as rejected:
        gateway.publish(NeuralMessage(kind=MessageKind.EVENT, source=manifest.plugin_id, topic="example.changed",
                                      payload_schema="example.changed@1", payload={}), session)
    assert rejected.value.code is GatewayRejectionCode.SCHEMA_INVALID
    assert gateway.queue.pending() == []


@pytest.mark.parametrize("foreground", [
    {"window_id": "win:1", "application": "Code.exe", "pid": 1,
     "bounds": {"left": 0, "top": 0, "width": 1, "height": 1, "opaque": {"x": 1}}},
    {"window_id": "win:1", "application": "Code.exe", "pid": 1,
     "bounds": {"left": 0, "top": 0, "width": 1, "height": 1},
     "interaction": {"period_seconds": 1, "event_count": 0, "events_per_minute": 0,
                     "is_high_frequency": False, "last_interaction_monotonic": None, "opaque": {"x": 1}}},
    {"window_id": "win:1", "application": "Code.exe", "pid": 1,
     "bounds": {"left": 0, "top": 0, "width": 1, "height": 1},
     "display": {"id": "display:0", "bounds": {"left": 0, "top": 0, "width": 1, "height": 1},
                 "opaque": {"x": 1}}},
])
def test_nested_opaque_window_data_is_rejected_without_queue_mutation(tmp_path, foreground):
    manifest = load_manifest({
        "plugin_id": "peripheral.window.activity", "version": "1.0.0", "protocol_version": "1.0",
        "runtime": {"kind": "python", "entrypoint": "example:Plugin"},
        "capabilities": ["window.current_state"], "signal_schemas": ["window.current_state@3"],
        "permissions": [], "privacy": {"classification": "metadata_only"},
    })
    gateway = NeuralSignalGateway(DurableEventQueue(tmp_path / "signals.db"))
    gateway.register(manifest, PluginGrant.create(manifest.plugin_id, {"window.current_state"}))
    session = gateway.open_session(manifest.plugin_id, "window-1", manifest.manifest_digest)
    with pytest.raises(GatewayRejected) as rejected:
        gateway.publish(NeuralMessage(kind=MessageKind.STATE, source=manifest.plugin_id,
                                      topic="window.current_state", payload_schema="window.current_state@3",
                                      payload={"window_count": 1, "foreground_status": "available",
                                               "foreground": foreground}), session)
    assert rejected.value.code is GatewayRejectionCode.SCHEMA_INVALID
    assert gateway.queue.pending() == []
