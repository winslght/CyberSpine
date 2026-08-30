import json
from pathlib import Path


def test_window_activity_plugin_manifest_matches_reference_implementation():
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((root / "plugins" / "builtin" / "window_activity" / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["plugin_id"] == "peripheral.window.activity"
    assert manifest["entrypoint"] == "src.sensing.window_activity:WindowActivityPeripheral"
    assert "window.catalog" in manifest["capabilities"]
    assert "window.high_interaction_changed" in manifest["capabilities"]
    assert "window.time_window_summary" in manifest["capabilities"]
    assert "window.foreground_availability_changed" in manifest["capabilities"]
    assert "window.geometry_changed" in manifest["capabilities"]
    assert "window.time_window_summary@1" in manifest["signal_schemas"]
    assert "window.current_state@3" in manifest["signal_schemas"]
    assert "window.geometry_changed@1" in manifest["signal_schemas"]
    assert "keystrokes" in manifest["privacy"]["never_collect"]
