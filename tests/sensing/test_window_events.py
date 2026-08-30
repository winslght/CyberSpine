from src.sensing.window_events import WindowsWindowEventSource, WindowEventTicket, WindowImpulseCoalescer


def test_event_source_rejects_child_accessibility_object_events_but_keeps_window_and_system_events():
    assert WindowsWindowEventSource.accepts_callback(0x800B, 0, 0) is True
    assert WindowsWindowEventSource.accepts_callback(0x800B, -4, 0) is False
    assert WindowsWindowEventSource.accepts_callback(0x800B, 0, 7) is False
    assert WindowsWindowEventSource.accepts_callback(0x0003, -4, 7) is True


def test_coalescer_waits_then_returns_one_impulse_batch():
    now = [10.0]
    coalescer = WindowImpulseCoalescer(0.2, clock=lambda: now[0])
    coalescer.record([
        WindowEventTicket("location_changed", 10, 10.0),
        WindowEventTicket("location_changed", 10, 10.1),
        WindowEventTicket("foreground_changed", 20, 10.1),
    ])

    assert coalescer.drain_ready() == []
    assert coalescer.seconds_until_ready() == 0.2
    now[0] = 10.3
    assert [(item.kind, item.hwnd) for item in coalescer.drain_ready()] == [
        ("location_changed", 10), ("location_changed", 10), ("foreground_changed", 20)]
    assert coalescer.seconds_until_ready() is None


def test_coalescer_extends_quiet_period_for_later_ticket():
    now = [1.0]
    coalescer = WindowImpulseCoalescer(0.2, clock=lambda: now[0])
    coalescer.record([WindowEventTicket("shown", 10, 1.0)])
    now[0] = 1.15
    coalescer.record([WindowEventTicket("location_changed", 10, 1.15)])
    now[0] = 1.3

    assert coalescer.drain_ready() == []
    now[0] = 1.35
    assert len(coalescer.drain_ready()) == 2
