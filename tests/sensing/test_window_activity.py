from src.core.neural_message import MessageKind, PrivacyClass
from src.sensing.window_activity import WindowActivityPeripheral
from src.sensing.window_events import WindowEventTicket


class FakeEventSource:
    def __init__(self):
        self.is_running = False
        self.callback_error_count = 0
        self.tickets = []

    def start(self):
        self.is_running = True
        return True

    def stop(self):
        self.is_running = False

    def drain(self):
        tickets, self.tickets = self.tickets, []
        return tickets

    def wait(self, _timeout):
        return None


class FakeInventory:
    def __init__(self, affected_window, foreground_window=None):
        self.affected_window = affected_window
        self.foreground_window_result = foreground_window
        self.foreground_reads = 0

    def window_for_handle(self, _hwnd):
        return self.affected_window

    def foreground_window(self):
        self.foreground_reads += 1
        return self.foreground_window_result


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
    assert state.payload["window_inventory_read_errors"] == 0
    assert directory.topic == "window.catalog"
    assert directory.payload_schema == "window.catalog@1"
    assert directory.payload["window_count"] == 3
    assert {item["application"] for item in directory.payload["windows"]} == {"explorer.exe", "chrome.exe", "WINWORD.EXE"}
    assert all(item["interaction"]["event_count"] == 0 for item in directory.payload["windows"])
    assert state.privacy == PrivacyClass.METADATA_ONLY


def test_state_reports_only_inventory_read_error_count():
    peripheral = WindowActivityPeripheral(catalog_provider=catalog(
        window("win:browser", "chrome.exe", 20, foreground=True)))
    inventory = FakeInventory(None)
    inventory.read_error_count = 3
    peripheral._inventory = inventory

    state = peripheral.collect_messages()[0]

    assert state.payload["window_inventory_read_errors"] == 3


def test_event_impulse_coalesces_before_refreshing_window_facts():
    now = [1.0]
    source = FakeEventSource()
    peripheral = WindowActivityPeripheral(catalog_provider=catalog(
        window("win:browser", "chrome.exe", 20, foreground=True)), clock=lambda: now[0],
        event_source=source, event_debounce_seconds=0.2)
    assert peripheral.start() is True
    peripheral.collect_messages()
    source.tickets = [WindowEventTicket("foreground_changed", 20, 1.0)]
    assert peripheral.collect_event_messages() == []
    now[0] = 1.2
    assert peripheral.collect_event_messages() == []
    peripheral.stop()


def test_unchanged_background_event_does_not_replace_foreground_or_emit_duplicate_state():
    now = [0.0]
    source = FakeEventSource()
    chrome = window("win:14", "chrome.exe", 20, foreground=True)
    editor = window("win:1e", "code.exe", 30, bounds={"left": 20, "top": 20, "width": 800, "height": 600})
    peripheral = WindowActivityPeripheral(catalog_provider=catalog(chrome, editor), clock=lambda: now[0],
        event_source=source, event_debounce_seconds=0.2)
    peripheral.collect_messages()
    inventory = FakeInventory(editor)
    peripheral._inventory = inventory
    source.tickets = [WindowEventTicket("location_changed", 30, 0.0)]
    peripheral.collect_event_messages()
    now[0] = 0.2
    messages = peripheral.collect_event_messages()

    assert inventory.foreground_reads == 0
    assert messages == []


def test_background_event_for_the_foreground_window_preserves_catalog_and_state_consistency():
    now = [0.0]
    source = FakeEventSource()
    chrome = window("win:14", "chrome.exe", 20, foreground=True)
    peripheral = WindowActivityPeripheral(catalog_provider=catalog(chrome), clock=lambda: now[0],
        event_source=source, event_debounce_seconds=0.2, event_diagnostics_enabled=True)
    peripheral.collect_messages()
    # WindowsWindowInventory.window_for_handle() can report false here when
    # GetForegroundWindow() is temporarily empty; a geometry update must not
    # erase the previously confirmed foreground fact.
    peripheral._inventory = FakeInventory(window("win:14", "chrome.exe", 20, foreground=False,
                                                 bounds={"left": 40, "top": 20, "width": 800, "height": 600}))
    source.tickets = [WindowEventTicket("location_changed", 20, 0.0)]
    peripheral.collect_event_messages()
    now[0] = 0.2
    messages = peripheral.collect_event_messages()

    state = next(message for message in messages if message.topic == "window.current_state")
    directory = next(message for message in messages if message.topic == "window.catalog")
    foregrounds = [item for item in directory.payload["windows"] if item["is_foreground"]]
    assert state.payload["foreground_status"] == "available"
    assert state.payload["foreground"]["window_id"] == "win:14"
    assert state.payload["event_diagnostics"] == {
        "source": "win_event_hook", "ticket_count": 1, "kinds": ["location_changed"],
        "window_identifiers_included": False}
    assert [item["window_id"] for item in foregrounds] == ["win:14"]


def test_hidden_confirmed_foreground_refreshes_to_the_new_foreground_window():
    now = [0.0]
    source = FakeEventSource()
    chrome = window("win:14", "chrome.exe", 20, foreground=True)
    editor = window("win:1e", "code.exe", 30, foreground=True)
    peripheral = WindowActivityPeripheral(catalog_provider=catalog(chrome), clock=lambda: now[0],
        event_source=source, event_debounce_seconds=0.2)
    peripheral.collect_messages()
    peripheral._inventory = FakeInventory(None, editor)
    source.tickets = [WindowEventTicket("hidden", 20, 0.0)]

    peripheral.collect_event_messages()
    now[0] = 0.2
    messages = peripheral.collect_event_messages()

    state = next(message for message in messages if message.topic == "window.current_state")
    assert state.payload["foreground_status"] == "available"
    assert state.payload["foreground"]["window_id"] == "win:1e"
    assert any(message.topic == "window.focus_changed" for message in messages)


def test_hidden_confirmed_foreground_keeps_catalog_consistent_during_empty_foreground_read():
    now = [0.0]
    source = FakeEventSource()
    chrome = window("win:14", "chrome.exe", 20, foreground=True)
    peripheral = WindowActivityPeripheral(catalog_provider=catalog(chrome), clock=lambda: now[0],
        event_source=source, event_debounce_seconds=0.2)
    peripheral.collect_messages()
    peripheral._inventory = FakeInventory(None)
    source.tickets = [WindowEventTicket("hidden", 20, 0.0)]

    peripheral.collect_event_messages()
    now[0] = 0.2
    messages = peripheral.collect_event_messages()

    state = next(message for message in messages if message.topic == "window.current_state")
    directory = next(message for message in messages if message.topic == "window.catalog")
    assert state.payload["foreground_status"] == "temporarily_unresolved"
    assert state.payload["foreground"]["window_id"] == "win:14"
    assert [item["window_id"] for item in directory.payload["windows"] if item["is_foreground"]] == ["win:14"]


def test_chatgpt_to_terminal_recovers_on_the_one_shot_foreground_retry():
    now = [0.0]
    source = FakeEventSource()
    chatgpt = window("win:14", "ChatGPT.exe", 20, foreground=True)
    terminal = window("win:1e", "WindowsTerminal.exe", 30, foreground=True)
    peripheral = WindowActivityPeripheral(catalog_provider=catalog(chatgpt), clock=lambda: now[0],
        event_source=source, event_debounce_seconds=0.2, foreground_grace_seconds=1.0)
    peripheral.collect_messages()
    inventory = FakeInventory(None)
    peripheral._inventory = inventory
    source.tickets = [WindowEventTicket("foreground_changed", 30, 0.0)]

    peripheral.collect_event_messages()
    now[0] = 0.2
    pending = peripheral.collect_event_messages()
    pending_state = next(message for message in pending if message.topic == "window.current_state")
    assert pending_state.payload["foreground_status"] == "temporarily_unresolved"

    inventory.foreground_window_result = terminal
    now[0] = 1.2
    resolved = peripheral.collect_foreground_resolution_messages()
    state = next(message for message in resolved if message.topic == "window.current_state")
    focus = next(message for message in resolved if message.topic == "window.focus_changed")
    assert inventory.foreground_reads == 2
    assert state.payload["foreground_status"] == "available"
    assert state.payload["foreground"]["application"] == "WindowsTerminal.exe"
    assert focus.payload["previous"]["application"] == "ChatGPT.exe"
    assert focus.payload["current"]["application"] == "WindowsTerminal.exe"


def test_foreground_resolution_retries_only_once_when_windows_still_returns_empty():
    now = [0.0]
    source = FakeEventSource()
    chatgpt = window("win:14", "ChatGPT.exe", 20, foreground=True)
    peripheral = WindowActivityPeripheral(catalog_provider=catalog(chatgpt), clock=lambda: now[0],
        event_source=source, event_debounce_seconds=0.2, foreground_grace_seconds=1.0)
    peripheral.collect_messages()
    inventory = FakeInventory(None)
    peripheral._inventory = inventory
    source.tickets = [WindowEventTicket("foreground_changed", 30, 0.0)]
    peripheral.collect_event_messages()
    now[0] = 0.2
    peripheral.collect_event_messages()

    now[0] = 1.2
    unresolved = peripheral.collect_foreground_resolution_messages()
    state = next(message for message in unresolved if message.topic == "window.current_state")
    assert state.payload["foreground_status"] == "unresolved"
    assert peripheral.collect_foreground_resolution_messages() == []
    assert inventory.foreground_reads == 2


def test_local_time_pulse_updates_dwell_without_reading_catalog_again():
    now = [0.0]
    calls = [0]

    def source_catalog():
        calls[0] += 1
        return [window("win:browser", "chrome.exe", 20, foreground=True)]

    peripheral = WindowActivityPeripheral(catalog_provider=source_catalog, clock=lambda: now[0])
    peripheral.collect_messages()
    now[0] = 12.0
    messages = peripheral.collect_local_time_messages()

    state = next(message for message in messages if message.topic == "window.current_state")
    summary = next(message for message in messages if message.topic == "window.time_window_summary")
    assert calls[0] == 1
    assert state.payload["foreground"]["focus_dwell_seconds"] == 12.0
    assert summary.payload["observed_seconds"] == 12.0


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


def test_input_method_and_synchronized_shell_geometry_only_update_internal_baselines():
    input_bounds = {"left": 396, "top": 957, "width": 467, "height": 80}
    shell_lower_bounds = {"left": 396, "top": 989, "width": 467, "height": 48}
    current = [[
        window("win:browser", "ChatGPT.exe", 20, foreground=True),
        window("win:input", "TextInputHost.exe", 30, window_title="", bounds=input_bounds),
        window("win:shell", "explorer.exe", 40, window_title="", bounds=input_bounds),
        window("win:shell-lower", "explorer.exe", 40, window_title="", bounds=shell_lower_bounds),
        window("win:explorer", "explorer.exe", 40, window_title="Downloads",
               bounds={"left": 40, "top": 100, "width": 1000, "height": 800}),
    ]]
    peripheral = WindowActivityPeripheral(catalog_provider=lambda: current[0])
    peripheral.collect_messages()

    moved_input_bounds = {"left": 424, "top": 957, "width": 519, "height": 80}
    moved_shell_lower_bounds = {"left": 424, "top": 989, "width": 519, "height": 48}
    current[0] = [
        window("win:browser", "ChatGPT.exe", 20, foreground=True),
        window("win:input", "TextInputHost.exe", 30, window_title="", bounds=moved_input_bounds),
        window("win:shell", "explorer.exe", 40, window_title="", bounds=moved_input_bounds),
        window("win:shell-lower", "explorer.exe", 40, window_title="", bounds=moved_shell_lower_bounds),
        window("win:explorer", "explorer.exe", 40, window_title="Downloads",
               bounds={"left": 40, "top": 100, "width": 1000, "height": 800}),
    ]
    messages = peripheral.collect_messages()
    directory = next(message for message in messages if message.topic == "window.catalog")
    presentations = {item["window_id"]: item["presentation"]["state"]
                     for item in directory.payload["windows"]}

    assert not any(message.topic == "window.geometry_changed" for message in messages)
    assert presentations["win:input"] == "system_surface"
    assert presentations["win:shell"] == "system_surface"
    assert presentations["win:shell-lower"] == "system_surface"
    assert presentations["win:explorer"] == "screen_present"
    assert peripheral._last_geometry["win:input"]["bounds"] == moved_input_bounds
    assert peripheral._last_geometry["win:shell-lower"]["bounds"] == moved_shell_lower_bounds

    current[0][-1] = window("win:explorer", "explorer.exe", 40, window_title="Downloads",
                            bounds={"left": 80, "top": 100, "width": 1000, "height": 800})
    user_window_messages = peripheral.collect_messages()
    geometry = next(message for message in user_window_messages if message.topic == "window.geometry_changed")
    assert [change["window"]["window_id"] for change in geometry.payload["changes"]] == ["win:explorer"]


def test_system_surface_geometry_is_excluded_from_event_fact_signature():
    base = {"window_id": "win:input", "presentation": {"state": "system_surface"},
            "bounds": {"left": 10, "top": 10, "width": 100, "height": 40},
            "geometry_activity": {"state": "stationary"}}
    moved = {**base, "bounds": {"left": 30, "top": 10, "width": 140, "height": 40},
             "geometry_activity": {"state": "geometry_changed"}}

    assert WindowActivityPeripheral._fact_signature([base], "available") == \
        WindowActivityPeripheral._fact_signature([moved], "available")


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
    unresolved = peripheral.collect_messages()
    state = next(message for message in unresolved if message.topic == "window.current_state")

    assert state.payload["foreground_status"] == "temporarily_unresolved"
    assert state.payload["foreground_confidence"] == "last_confirmed"
    assert "window_title" not in state.payload
    now[0] = 6.0
    unavailable = peripheral.collect_foreground_resolution_messages()
    state = next(message for message in unavailable if message.topic == "window.current_state")
    summary = next(message for message in unavailable if message.topic == "window.time_window_summary")

    assert state.payload["foreground"] is None
    assert state.payload["foreground_status"] == "unresolved"
    assert "window_title" not in state.payload
    assert not any(message.topic == "window.foreground_availability_changed" for message in unavailable)
    assert summary.payload["unattributed_seconds"] == 0.0
    now[0] = 15.0
    current[0] = [window("win:editor", "code.exe", 30, foreground=True)]
    recovered = peripheral.collect_messages()
    recovered_summary = next(message for message in recovered if message.topic == "window.time_window_summary")
    focus_event = next(message for message in recovered if message.topic == "window.focus_changed")

    assert recovered_summary.payload["observed_seconds"] == 6.0
    assert recovered_summary.payload["unattributed_seconds"] == 9.0
    assert recovered_summary.payload["focus_switch_count"] == 1
    assert focus_event.payload["previous"]["application"] == "chrome.exe"
    assert focus_event.payload["current"]["application"] == "code.exe"


def test_missing_foreground_uses_a_one_shot_grace_period_before_marking_unresolved():
    current = [[window("win:browser", "chrome.exe", 20, foreground=True)]]
    now = [0.0]
    peripheral = WindowActivityPeripheral(catalog_provider=lambda: current[0], clock=lambda: now[0],
        focus_window_seconds=60, foreground_grace_seconds=1.0)
    peripheral.collect_messages()
    now[0] = 5.0
    current[0] = [window("win:browser", "chrome.exe", 20)]
    unresolved = peripheral.collect_messages()
    unresolved_state = next(message for message in unresolved if message.topic == "window.current_state")

    assert unresolved_state.payload["foreground_status"] == "temporarily_unresolved"
    assert unresolved_state.payload["foreground_confidence"] == "last_confirmed"
    assert not any(message.topic == "window.foreground_availability_changed" for message in unresolved)
    assert peripheral.foreground_resolution_due_seconds() == 1.0

    now[0] = 6.0
    confirmed = peripheral.collect_foreground_resolution_messages()
    state = next(message for message in confirmed if message.topic == "window.current_state")
    assert state.payload["foreground_status"] == "unresolved"
    assert state.payload["foreground_resolution_reason"] == "foreground_resolution_timeout"
    assert not any(message.topic == "window.foreground_availability_changed" for message in confirmed)


def test_focus_and_unattributed_time_are_a_partition_with_bounded_focus_ratios():
    current = [[window("win:browser", "chrome.exe", 20, foreground=True)]]
    now = [0.0]
    peripheral = WindowActivityPeripheral(catalog_provider=lambda: current[0], clock=lambda: now[0],
        focus_window_seconds=60, foreground_grace_seconds=1.0)
    peripheral.collect_messages()
    now[0] = 5.0
    current[0] = [window("win:browser", "chrome.exe", 20)]
    peripheral.collect_messages()
    now[0] = 6.0
    peripheral.collect_local_time_messages()
    now[0] = 10.0
    peripheral.collect_local_time_messages()
    now[0] = 11.0
    current[0] = [window("win:editor", "code.exe", 30, foreground=True)]
    messages = peripheral.collect_messages()

    summary = next(message for message in messages if message.topic == "window.time_window_summary").payload
    focus_total = sum(item["focus_seconds"] for item in summary["windows"])
    assert focus_total + summary["unattributed_seconds"] == summary["elapsed_seconds"]
    assert all(0 <= item["focus_ratio"] <= 1 for item in summary["windows"])
    assert summary["time_accounting_invariant"] == "focus_plus_unattributed_equals_elapsed"
