import json
from copy import deepcopy
from pathlib import Path

import pytest

from src.core.event_queue import DurableEventQueue
from src.core.gateway_errors import GatewayRejected, GatewayRejectionCode
from src.core.neural_gateway import NeuralSignalGateway
from src.core.neural_message import MessageKind, NeuralMessage
from src.core.plugin_manifest import load_manifest
from src.core.plugin_registration import PluginGrant
from src.sensing.window_activity import WindowActivityPeripheral

_SAFE_PAYLOADS = {
    "window.current_state@3": {"window_count": 0, "foreground_status": "unresolved"},
    "window.catalog@1": {"windows": [], "window_count": 0},
    "window.focus_changed@2": {"previous": None, "current": {
        "window_id": "win:test", "application": "Code.exe", "pid": 1,
        "bounds": {"left": 0, "top": 0, "width": 1, "height": 1}}},
    "window.high_interaction_changed@1": {"previous_window_ids": [], "current_window_ids": [], "period_seconds": 1},
    "window.time_window_summary@1": {"period_seconds": 1, "segments": [], "windows": [], "foreground_status": "unresolved"},
    "window.foreground_availability_changed@1": {
        "previous_status": "available", "current_status": "unavailable", "reason": "test", "recovered_foreground": None},
    "window.geometry_changed@1": {"changes": []},
}


def test_every_window_manifest_topic_is_admitted_with_a_granted_session(tmp_path):
    root = Path(__file__).resolve().parents[2]
    manifest = load_manifest(json.loads(
        (root / "plugins" / "builtin" / "window_activity" / "manifest.json").read_text(encoding="utf-8")
    ))
    gateway = NeuralSignalGateway(DurableEventQueue(tmp_path / "signals.db"))
    gateway.register(manifest, PluginGrant.create(manifest.plugin_id, manifest.capabilities))
    session = gateway.open_session(manifest.plugin_id, "window-reference", manifest.manifest_digest)
    event_topics = {"window.focus_changed", "window.high_interaction_changed",
                    "window.foreground_availability_changed", "window.geometry_changed"}

    for topic in manifest.capabilities:
        schema = next(item for item in manifest.signal_schemas if item.startswith(f"{topic}@"))
        message = NeuralMessage(kind=MessageKind.EVENT if topic in event_topics else MessageKind.STATE,
                                source=manifest.plugin_id, topic=topic, payload_schema=schema,
                                payload=_SAFE_PAYLOADS[schema])
        gateway.publish(message, session)

    assert {item.message.topic for item in gateway.queue.pending()} == set(manifest.capabilities)


def test_real_window_peripheral_output_passes_registered_content_validators(tmp_path):
    root = Path(__file__).resolve().parents[2]
    manifest = load_manifest(json.loads(
        (root / "plugins" / "builtin" / "window_activity" / "manifest.json").read_text(encoding="utf-8")
    ))
    peripheral = WindowActivityPeripheral(catalog_provider=lambda: [{
        "window_id": "win:test", "application": "Code.exe", "pid": 1, "window_title": "private title",
        "is_foreground": True, "bounds": {"left": 0, "top": 0, "width": 100, "height": 100},
    }])
    gateway = NeuralSignalGateway(DurableEventQueue(tmp_path / "signals.db"))
    gateway.register(manifest, PluginGrant.create(manifest.plugin_id, manifest.capabilities))
    session = gateway.open_session(manifest.plugin_id, "window-reference", manifest.manifest_digest)

    messages = peripheral.collect_messages()
    for message in messages:
        gateway.publish(message, session)

    assert {message.payload_schema for message in messages} == {
        "window.current_state@3", "window.catalog@1", "window.time_window_summary@1"}
    assert len(gateway.queue.pending()) == len(messages)


def test_every_window_schema_rejects_unknown_payload_field_without_queue_mutation(tmp_path):
    root = Path(__file__).resolve().parents[2]
    manifest = load_manifest(json.loads(
        (root / "plugins" / "builtin" / "window_activity" / "manifest.json").read_text(encoding="utf-8")
    ))
    gateway = NeuralSignalGateway(DurableEventQueue(tmp_path / "signals.db"))
    gateway.register(manifest, PluginGrant.create(manifest.plugin_id, manifest.capabilities))
    session = gateway.open_session(manifest.plugin_id, "window-reference", manifest.manifest_digest)
    event_topics = {"window.focus_changed", "window.high_interaction_changed",
                    "window.foreground_availability_changed", "window.geometry_changed"}

    for schema, safe_payload in _SAFE_PAYLOADS.items():
        topic = schema.rsplit("@", 1)[0]
        payload = deepcopy(safe_payload)
        payload["opaque_untrusted_field"] = {"nested": True}
        with pytest.raises(GatewayRejected) as rejected:
            gateway.publish(NeuralMessage(kind=MessageKind.EVENT if topic in event_topics else MessageKind.STATE,
                                          source=manifest.plugin_id, topic=topic, payload_schema=schema,
                                          payload=payload), session)
        assert rejected.value.code is GatewayRejectionCode.SCHEMA_INVALID
    assert gateway.queue.pending() == []
