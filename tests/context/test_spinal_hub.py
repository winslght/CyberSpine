from src.context.spinal_hub import NeuralSpinalHub
from src.sensing.window_activity import WindowActivityPeripheral


def snapshots(*items):
    iterator = iter(items)
    return lambda: next(iterator)


def test_hub_builds_read_only_window_context(tmp_path):
    window = WindowActivityPeripheral(snapshots(
        {"active_process": "explorer.exe", "active_title": "Documents", "active_pid": 1},
        {"active_process": "code.exe", "active_title": "CyberSpine", "active_pid": 2},
    ))
    hub = NeuralSpinalHub(tmp_path / "neural.db", window)

    first_items = hub.collect_window()
    first_context = hub.current_context()
    second_items = hub.collect_window()
    second_context = hub.current_context()

    assert len(first_items) == 3
    assert first_context.states["window.current_state"]["foreground"]["application"] == "explorer.exe"
    assert len(second_items) == 4
    assert second_context.states["window.current_state"]["foreground"]["application"] == "code.exe"
    assert second_context.recent_events[0].topic == "window.focus_changed"
    assert second_context.recent_events[0].payload["previous"]["application"] == "explorer.exe"
    assert second_context.states["window.time_window_summary"]["foreground_window_id"]
