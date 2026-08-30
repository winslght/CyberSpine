import ctypes
import sys
from ctypes import wintypes

import pytest

from src.sensing.window_interactions import (
    WindowsGlobalInputMonitor,
    _MSLLHOOKSTRUCT,
    _handle_value,
)


def x_button_l_param(button: int):
    event = _MSLLHOOKSTRUCT()
    event.mouseData = button << 16
    return event, ctypes.addressof(event)


def test_mouse_message_constants_match_win32_values():
    assert WindowsGlobalInputMonitor._WM_MOUSEWHEEL == 0x020A
    assert WindowsGlobalInputMonitor._WM_XBUTTONDOWN == 0x020B
    assert WindowsGlobalInputMonitor._WM_XBUTTONUP == 0x020C
    assert {0x020A, 0x020B, 0x020C} <= WindowsGlobalInputMonitor._MOUSE_ACTIONS


def test_wheel_does_not_change_mouse_button_held_state():
    monitor = WindowsGlobalInputMonitor(lambda _hwnd: None)

    assert monitor._update_mouse_button_state(monitor._WM_MOUSEWHEEL) is None
    assert monitor._pressed_mouse_buttons == set()


def test_standard_and_x_buttons_release_independently():
    monitor = WindowsGlobalInputMonitor(lambda _hwnd: None)
    x1_event, x1_param = x_button_l_param(1)
    x2_event, x2_param = x_button_l_param(2)

    assert monitor._update_mouse_button_state(monitor._WM_LBUTTONDOWN) is True
    assert monitor._update_mouse_button_state(monitor._WM_XBUTTONDOWN, x1_param) is True
    assert monitor._update_mouse_button_state(monitor._WM_XBUTTONDOWN, x2_param) is True
    assert monitor._pressed_mouse_buttons == {"left", "x1", "x2"}
    assert monitor._update_mouse_button_state(monitor._WM_LBUTTONUP) is True
    assert monitor._update_mouse_button_state(monitor._WM_XBUTTONUP, x1_param) is True
    assert monitor._pressed_mouse_buttons == {"x2"}
    assert monitor._update_mouse_button_state(monitor._WM_XBUTTONUP, x2_param) is False
    assert monitor._pressed_mouse_buttons == set()
    assert x1_event.mouseData and x2_event.mouseData


def test_handle_value_accepts_integer_ctypes_handle_and_null():
    assert _handle_value(12345) == 12345
    assert _handle_value(wintypes.HWND(12345)) == 12345
    assert _handle_value(wintypes.HWND()) == 0


@pytest.mark.skipif(sys.platform != "win32" or not hasattr(ctypes, "windll"),
                    reason="requires the Windows hook ctypes boundary")
def test_input_hook_pointer_sized_signatures_are_declared():
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int,
                                      ctypes.c_size_t, ctypes.c_ssize_t)
    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32

    WindowsGlobalInputMonitor._configure_win32(user32, kernel32, callback_type)

    assert user32.GetForegroundWindow.argtypes == []
    assert user32.GetForegroundWindow.restype is wintypes.HWND
    assert user32.SetWindowsHookExW.restype is wintypes.HHOOK
    assert user32.CallNextHookEx.restype is ctypes.c_ssize_t
    assert kernel32.GetCurrentThreadId.restype is wintypes.DWORD
