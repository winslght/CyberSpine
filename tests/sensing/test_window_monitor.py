from scripts import monitor_window_activity


def test_deadline_check_reads_monotonic_time_when_called(monkeypatch):
    readings = iter((9.9, 10.0))
    monkeypatch.setattr(monitor_window_activity.time, "monotonic", lambda: next(readings))

    assert monitor_window_activity._deadline_reached(10.0) is False
    assert monitor_window_activity._deadline_reached(10.0) is True


def test_input_monitor_flag_has_an_explicit_opt_out():
    parser = monitor_window_activity._argument_parser()

    assert parser.parse_args([]).input_monitor is False
    assert parser.parse_args(["--input-monitor"]).input_monitor is True
    assert parser.parse_args(["--input-monitor", "--no-input-monitor"]).input_monitor is False


def test_official_launcher_enables_input_monitor_before_user_overrides():
    launcher = (monitor_window_activity.ROOT / "start_window_monitor.bat").read_text(encoding="utf-8")
    command = next(line for line in launcher.splitlines() if "monitor_window_activity.py" in line)

    assert command.index("--input-monitor") < command.index("%*")
