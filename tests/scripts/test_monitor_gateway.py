import json
import tempfile
from pathlib import Path

from scripts import monitor_gateway
from src.core.event_queue import DurableEventQueue
from src.core.neural_gateway import NeuralSignalGateway
from src.core.neural_message import MessageKind, NeuralMessage
from src.core.plugin_manifest import load_manifest
from src.core.plugin_registration import PluginGrant


def test_observer_parser_accepts_safe_display_controls(tmp_path):
    args = monitor_gateway._parser().parse_args([str(tmp_path / "manifest.json"), "--duration", "1", "--display-interval", "0.5", "--no-clear"])
    assert args.duration == 1
    assert args.display_interval == 0.5
    assert args.no_clear is True


def _manifest(tmp_path):
    data = {
        "plugin_id": "peripheral.window.activity",
        "version": "1.0.0",
        "protocol_version": "1.0",
        "runtime": {"kind": "python", "entrypoint": "example:Plugin"},
        "capabilities": ["window.geometry_changed"],
        "signal_schemas": ["window.geometry_changed@1"],
        "permissions": [],
        "privacy": {"classification": "metadata_only"},
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, load_manifest(data)


def _gateway(tmp_path):
    path, manifest = _manifest(tmp_path)
    gateway = NeuralSignalGateway(DurableEventQueue(tmp_path / "signals.db"))
    gateway.register(manifest, PluginGrant.create(manifest.plugin_id, manifest.capabilities))
    return path, gateway, gateway.open_session(manifest.plugin_id, "observer-test", manifest.manifest_digest)


def _message(session, message_id="observer-message"):
    return NeuralMessage(
        message_id=message_id,
        kind=MessageKind.EVENT,
        source=session.plugin_id,
        topic="window.geometry_changed",
        payload_schema="window.geometry_changed@1",
        payload={"changes": []},
    )


def test_snapshot_aggregates_queue_governance_and_audit_without_payload(tmp_path):
    _, gateway, session = _gateway(tmp_path)
    monitor = monitor_gateway.GatewayMonitor(gateway, session.plugin_id, session.instance_id)
    gateway.publish(_message(session), session)
    view = monitor.snapshot()
    assert (view.pending, view.authorized, view.rejected, view.rate_limited) == (1, 1, 0, 0)
    assert view.last_topic == "window.geometry_changed"
    rendered = []
    monitor.render = rendered.append
    monitor.render_snapshot()
    assert "payload" not in rendered[0]
    assert "token" not in rendered[0]


def test_governance_demo_exposes_g2_states_only_as_safe_lines(tmp_path):
    _, gateway, session = _gateway(tmp_path)
    output = []
    monitor = monitor_gateway.GatewayMonitor(gateway, session.plugin_id, session.instance_id, output.append)
    monitor_gateway._governance_demo(gateway, session, monitor)
    text = "\n".join(output)
    for expected in ("authorized:1", "rate_limited:1", "health=degraded", "health=paused", "health=quarantined", "isolation decision=suppressed", "audit="):
        assert expected in text
    for secret in ("SECRET_PAYLOAD", "SECRET_TOKEN", "SECRET_TITLE", "SECRET_PATH", "SECRET_PID", "SECRET_CORRELATION"):
        assert secret not in text


def test_window_mode_stops_peripheral_on_keyboard_interrupt(tmp_path, monkeypatch):
    manifest_path, _, _ = _gateway(tmp_path)
    state = {"stopped": False}

    class FakePeripheral:
        def collect_messages(self):
            raise KeyboardInterrupt

        def stop(self):
            state["stopped"] = True

    monkeypatch.setattr("src.sensing.window_activity.WindowActivityPeripheral", FakePeripheral)
    assert monitor_gateway.main([str(manifest_path), "--window-snapshot", "--duration", "0"]) == 0
    assert state["stopped"] is True


def test_observer_removes_temporary_queue_before_exit(tmp_path, monkeypatch):
    manifest_path, _, _ = _gateway(tmp_path)
    locations = []
    real_temporary_directory = tempfile.TemporaryDirectory

    class TrackingTemporaryDirectory:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def __enter__(self):
            self.context = real_temporary_directory(ignore_cleanup_errors=False)
            path = self.context.__enter__()
            locations.append(path)
            return path

        def __exit__(self, *args):
            return self.context.__exit__(*args)

    monkeypatch.setattr(monitor_gateway.tempfile, "TemporaryDirectory", TrackingTemporaryDirectory)
    assert monitor_gateway.main([str(manifest_path), "--governance-demo"]) == 0
    assert locations and not Path(locations[0]).exists()


def test_observer_masks_runtime_exception_and_stops_peripheral(tmp_path, monkeypatch, capsys):
    manifest_path, _, _ = _gateway(tmp_path)
    state = {"stopped": False}

    class FailingPeripheral:
        def collect_messages(self):
            raise RuntimeError("SECRET_TITLE from untrusted sensor")

        def stop(self):
            state["stopped"] = True

    monkeypatch.setattr("src.sensing.window_activity.WindowActivityPeripheral", FailingPeripheral)
    assert monitor_gateway.main([str(manifest_path), "--window-snapshot", "--duration", "1"]) == 1
    assert state["stopped"] is True
    output = capsys.readouterr().out
    assert "observer_runtime_error" in output
    assert "SECRET_TITLE" not in output


def test_observer_masks_stop_exception_and_returns_failure(tmp_path, monkeypatch, capsys):
    manifest_path, _, _ = _gateway(tmp_path)
    state = {"stopped": False}

    class FailingStopPeripheral:
        def collect_messages(self):
            raise KeyboardInterrupt

        def stop(self):
            state["stopped"] = True
            raise RuntimeError("SECRET_TITLE during stop")

    monkeypatch.setattr("src.sensing.window_activity.WindowActivityPeripheral", FailingStopPeripheral)
    assert monitor_gateway.main([str(manifest_path), "--window-snapshot", "--duration", "0"]) == 1
    assert state["stopped"] is True
    output = capsys.readouterr().out
    assert "observer_runtime_error" in output
    assert "SECRET_TITLE" not in output
