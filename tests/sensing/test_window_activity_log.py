from src.core.neural_message import MessageKind, NeuralMessage
from src.sensing.window_activity_log import WindowActivityLog, analyze_window_activity_log


def test_window_activity_log_and_analysis(tmp_path):
    path = tmp_path / "window_activity.jsonl"
    logger = WindowActivityLog(path)
    logger.append([
        NeuralMessage(kind=MessageKind.STATE, source="peripheral.window.activity", topic="window.current_state",
                      payload={"foreground": {"application": "chrome.exe", "pid": 12}}),
        NeuralMessage(kind=MessageKind.STATE, source="peripheral.window.activity", topic="window.catalog",
                      payload={"window_count": 2, "windows": [
                          {"window_id": "win:browser", "application": "chrome.exe", "pid": 12,
                           "interaction": {"is_high_frequency": True, "event_count": 15, "events_per_minute": 30}},
                          {"window_id": "win:office", "application": "WINWORD.EXE", "pid": 13,
                           "interaction": {"is_high_frequency": False, "event_count": 2, "events_per_minute": 4}},
                      ]}),
        NeuralMessage(kind=MessageKind.EVENT, source="peripheral.window.activity", topic="window.focus_changed"),
        NeuralMessage(kind=MessageKind.STATE, source="peripheral.window.activity", topic="window.time_window_summary",
                      payload={"observed_seconds": 42, "unattributed_seconds": 3, "coverage_ratio": 0.7}),
        NeuralMessage(kind=MessageKind.EVENT, source="peripheral.window.activity",
                      topic="window.foreground_availability_changed"),
    ])

    report = analyze_window_activity_log(path)

    assert report["records"] == 5
    assert report["latest_foreground"]["application"] == "chrome.exe"
    assert report["visible_window_count"] == 2
    assert report["focus_changes"] == 1
    assert report["high_interaction_windows"][0]["application"] == "chrome.exe"
    assert report["latest_time_window"]["unattributed_seconds"] == 3
    assert report["foreground_availability_changes"] == 1
