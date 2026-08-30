from src.core.neural_message import MessageKind, PrivacyClass
from src.sensing.window_activity import WindowActivityPeripheral


def catalog(*windows):
    return lambda: list(windows)


def window(window_id, app, pid, foreground=False, **extra):
    return {"window_id": window_id, "application": app, "pid": pid,
            "window_title": extra.pop("window_title", app), "is_foreground": foreground,
            "bounds": extra.pop("bounds", {"left": 10, "top": 20, "width": 800, "height": 600}), **extra}


def test_catalog_reports_all_windows_layout_process_and_foreground():
    peripheral = WindowActivityPeripheral(catalog_provider=catalog(
        window("win:explorer", "explorer.exe", 10),
        window("win:browser", "chrome.exe", 20, foreground=True, is_maximized=True),
        window("win:office", "WINWORD.EXE", 30),
    ))
    messages = peripheral.collect_messages()
    state, directory = messages[:2]
    assert state.kind == MessageKind.STATE
    assert state.topic == "window.current_state"
    assert state.payload_schema == "window.current_state@3"
    assert state.payload["foreground"]["application"] == "chrome.exe"
    assert state.payload["foreground"]["bounds"]["width"] == 800
    assert directory.topic == "window.catalog"
    assert directory.payload_schema == "window.catalog@1"
    assert directory.payload["window_count"] == 3
    assert {item["application"] for item in directory.payload["windows"]} == {"explorer.exe", "chrome.exe", "WINWORD.EXE"}
    assert all(item["interaction"]["event_count"] == 0 for item in directory.payload["windows"])
    assert state.privacy == PrivacyClass.METADATA_ONLY


def test_catalog_distinguishes_screen_present_user_windows_from_minimized_and_system_surfaces():
    peripheral = WindowActivityPeripheral(catalog_provider=catalog(
        window("win:browser", "chrome.exe", 20, foreground=True, bounds={"left": 0, "top": 0, "width": 800, "height": 600}),
        window("win:editor", "code.exe", 30, bounds={"left": 900, "top": 0, "width": 800, "height": 600}),
        window("win:minimized", "Weixin.exe", 40, is_minimized=True, bounds={"left": -32000, "top": -32000, "width": 160, "height": 28}),
        window("win:offscreen", "music.exe", 50, bounds={"left": 3000, "top": 0, "width": 800, "height": 600}),
        window("win:input", "TextInputHost.exe", 60, bounds={"left": 0, "top": 0, "width": 1920, "height": 1080}),
    ), screen_bounds_provider=lambda: {"left": 0, "top": 0, "width": 1920, "height": 1080})
    directory = next(message for message in peripheral.collect_messages() if message.topic == "window.catalog")
    states = {item["application"]: item["presentation"]["state"] for item in directory.payload["windows"]}

    assert states == {"chrome.exe": "foreground", "code.exe": "screen_present", "Weixin.exe": "minimized",
                      "music.exe": "offscreen", "TextInputHost.exe": "system_surface"}
    assert directory.payload["window_count"] == 5
    assert directory.payload["screen_present_window_count"] == 3
    assert directory.payload["screen_present_user_window_count"] == 2


def test_catalog_reports_window_state_and_geometry_change_candidates_without_input_content():
    primary = {"id": "display:0:0:1920x1080", "bounds": {"left": 0, "top": 0, "width": 1920, "height": 1080}}
    secondary = {"id": "display:1920:0:1920x1080", "bounds": {"left": 1920, "top": 0, "width": 1920, "height": 1080}}
    current = [[window("win:video", "player.exe", 20, foreground=True, is_topmost=True,
                      bounds={"left": 0, "top": 0, "width": 1920, "height": 1080}, display=primary)]]
    peripheral = WindowActivityPeripheral(catalog_provider=lambda: current[0])
    initial = peripheral.collect_messages()
    foreground = next(message for message in initial if message.topic == "window.current_state").payload["foreground"]
    assert foreground["window_state"]["is_topmost"] is True
    assert foreground["window_state"]["is_fullscreen_candidate"] is True
    assert foreground["window_state"]["display"]["id"] == primary["id"]

    peripheral.record_mouse_button_state(True)
    current[0] = [window("win:video", "player.exe", 20, foreground=True, is_topmost=True,
                         bounds={"left": 30, "top": 0, "width": 1920, "height": 1080}, display=primary)]
    moved = peripheral.collect_messages()
    movement = next(message for message in moved if message.topic == "window.geometry_changed")
    change = movement.payload["changes"][0]
    assert movement.payload_schema == "window.geometry_changed@1"
    assert change["change"] == "moved"
    assert change["is_in_progress_candidate"] is True
    assert change["detection_basis"] == "mouse_button_held_and_geometry_change"
    assert "window_title" not in change["window"]

    peripheral.record_mouse_button_state(False)
    current[0] = [window("win:video", "player.exe", 20, foreground=True, is_topmost=True,
                         bounds={"left": 1920, "top": 0, "width": 1920, "height": 1080}, display=secondary)]
    transitioned = peripheral.collect_messages()
    display_change = next(message for message in transitioned if message.topic == "window.geometry_changed").payload["changes"][0]
    assert display_change["current_display"]["id"] == secondary["id"]
    assert display_change["previous_display"]["id"] == primary["id"]
    assert display_change["is_in_progress_candidate"] is False


def test_focus_dwell_and_focus_change_are_tracked_per_window():
    current = [[window("win:browser", "chrome.exe", 20, foreground=True)]]
    now = [10.0]
    peripheral = WindowActivityPeripheral(catalog_provider=lambda: current[0], clock=lambda: now[0])
    peripheral.collect_messages()
    now[0] = 25.5
    same_window = peripheral.collect_messages()[0]
    current[0] = [window("win:office", "WINWORD.EXE", 30, foreground=True)]
    now[0] = 30.0
    changed = peripheral.collect_messages()
    assert same_window.payload["foreground"]["focus_dwell_seconds"] == 15.5
    focus_event = next(message for message in changed if message.topic == "window.focus_changed")
    assert focus_event.kind == MessageKind.EVENT
    assert focus_event.payload["previous"]["application"] == "chrome.exe"
    assert focus_event.payload["current"]["application"] == "WINWORD.EXE"
    assert changed[0].payload["foreground"]["focus_dwell_seconds"] == 0.0


def test_high_frequency_interactions_are_attributed_to_windows():
    now = [60.0]
    peripheral = WindowActivityPeripheral(catalog_provider=catalog(
        window("win:browser", "chrome.exe", 20, foreground=True),
        window("win:office", "WINWORD.EXE", 30),
        window("win:music", "cloudmusic.exe", 40),
    ), clock=lambda: now[0], activity_window_seconds=60, high_frequency_per_minute=5, minimum_interactions=5)
    for instant in (20, 25, 30, 35, 40, 45):
        peripheral.record_interaction("win:browser", instant)
    for instant in (24, 44):
        peripheral.record_interaction("win:office", instant)
    messages = peripheral.collect_messages()
    directory = next(message for message in messages if message.topic == "window.catalog")
    browser = next(item for item in directory.payload["windows"] if item["window_id"] == "win:browser")
    office = next(item for item in directory.payload["windows"] if item["window_id"] == "win:office")
    activity_event = next(message for message in messages if message.topic == "window.high_interaction_changed")
    assert browser["interaction"]["event_count"] == 6
    assert browser["interaction"]["is_high_frequency"] is True
    assert office["interaction"]["is_high_frequency"] is False
    assert activity_event.payload["current_window_ids"] == ["win:browser"]
    now[0] = 121.0
    expired_messages = peripheral.collect_messages()
    expired_event = next(message for message in expired_messages if message.topic == "window.high_interaction_changed")
    assert expired_event.payload["current_window_ids"] == []


def test_time_window_summary_aggregates_focus_segments_and_interactions():
    current = [[window("win:browser", "chrome.exe", 20, foreground=True)]]
    now = [0.0]
    peripheral = WindowActivityPeripheral(catalog_provider=lambda: current[0], clock=lambda: now[0],
        focus_window_seconds=60, activity_window_seconds=60, high_frequency_per_minute=2,
        minimum_interactions=2)
    peripheral.collect_messages()
    peripheral.record_interaction("win:browser", 5)
    peripheral.record_interaction("win:browser", 8)
    now[0] = 15.0
    current[0] = [window("win:editor", "code.exe", 30, foreground=True)]
    peripheral.collect_messages()
    now[0] = 30.0
    messages = peripheral.collect_messages()

    summary = next(message for message in messages if message.topic == "window.time_window_summary")
    assert summary.payload_schema == "window.time_window_summary@1"
    assert summary.payload["period_seconds"] == 60
    assert summary.payload["observed_seconds"] == 30
    assert summary.payload["coverage_ratio"] == 0.5
    assert summary.payload["focus_switch_count"] == 1
    assert [(item["window_id"], item["duration_seconds"]) for item in summary.payload["segments"]] == [
        ("win:browser", 15.0), ("win:editor", 15.0)]
    browser = next(item for item in summary.payload["windows"] if item["window_id"] == "win:browser")
    editor = next(item for item in summary.payload["windows"] if item["window_id"] == "win:editor")
    assert browser["focus_ratio"] == 0.5
    assert browser["interaction"]["event_count"] == 2
    assert editor["focus_seconds"] == 15.0
    assert summary.privacy == PrivacyClass.METADATA_ONLY


def test_time_window_counts_a_focus_switch_before_the_new_segment_has_duration():
    current = [[window("win:browser", "chrome.exe", 20, foreground=True)]]
    now = [0.0]
    peripheral = WindowActivityPeripheral(catalog_provider=lambda: current[0], clock=lambda: now[0],
        focus_window_seconds=60)
    peripheral.collect_messages()
    now[0] = 10.0
    current[0] = [window("win:editor", "code.exe", 30, foreground=True)]

    summary = next(message for message in peripheral.collect_messages()
                   if message.topic == "window.time_window_summary")
    assert summary.payload["focus_switch_count"] == 1


def test_no_attributable_foreground_pauses_focus_attribution_without_title_leakage():
    current = [[window("win:browser", "chrome.exe", 20, foreground=True)]]
    now = [0.0]
    peripheral = WindowActivityPeripheral(catalog_provider=lambda: current[0], clock=lambda: now[0],
        focus_window_seconds=60)
    peripheral.collect_messages()
    now[0] = 5.0
    current[0] = [window("win:browser", "chrome.exe", 20, window_title="private title")]
    unavailable = peripheral.collect_messages()
    state = next(message for message in unavailable if message.topic == "window.current_state")
    summary = next(message for message in unavailable if message.topic == "window.time_window_summary")
    availability = next(message for message in unavailable
                        if message.topic == "window.foreground_availability_changed")

    assert state.payload["foreground"] is None
    assert state.payload["foreground_status"] == "unavailable"
    assert "window_title" not in state.payload
    assert availability.payload["current_status"] == "unavailable"
    assert summary.payload["unattributed_seconds"] == 0.0
    now[0] = 15.0
    current[0] = [window("win:editor", "code.exe", 30, foreground=True)]
    recovered = peripheral.collect_messages()
    recovered_summary = next(message for message in recovered if message.topic == "window.time_window_summary")
    focus_event = next(message for message in recovered if message.topic == "window.focus_changed")
    recovery = next(message for message in recovered if message.topic == "window.foreground_availability_changed")

    assert recovered_summary.payload["observed_seconds"] == 5.0
    assert recovered_summary.payload["unattributed_seconds"] == 10.0
    assert recovered_summary.payload["focus_switch_count"] == 1
    assert recovery.payload["recovered_foreground"]["application"] == "code.exe"
    assert "window_title" not in recovery.payload["recovered_foreground"]
    assert focus_event.payload["previous"]["application"] == "chrome.exe"
    assert focus_event.payload["current"]["application"] == "code.exe"
