import ctypes
import sys
from ctypes import wintypes

import pytest

from src.sensing.window_inventory import WindowsWindowInventory, _RECT


class FakeUser32:
    def GetWindowThreadProcessId(self, _hwnd, pid_pointer):
        pid_pointer._obj.value = 123
        return 1

    def GetWindowRect(self, _hwnd, rect_pointer):
        rect = rect_pointer._obj
        rect.left, rect.top, rect.right, rect.bottom = 10, 20, 810, 620
        return 1

    def GetWindowLongPtrW(self, _hwnd, _index):
        return 0

    def GetWindowLongW(self, _hwnd, _index):
        return 0

    def IsIconic(self, _hwnd):
        return 0

    def IsZoomed(self, _hwnd):
        return 0


def inventory_without_platform_setup():
    inventory = WindowsWindowInventory.__new__(WindowsWindowInventory)
    inventory._is_windows = True
    inventory._process_name_cache = {}
    inventory._next_process_cache_cleanup = 0.0
    inventory._read_error_count = 0
    return inventory


def test_hwnd_value_accepts_callback_integer_and_ctypes_handle():
    assert WindowsWindowInventory._hwnd_value(12345) == 12345
    assert WindowsWindowInventory._hwnd_value(wintypes.HWND(12345)) == 12345
    assert WindowsWindowInventory._hwnd_value(wintypes.HWND()) == 0


@pytest.mark.parametrize("hwnd", [12345, wintypes.HWND(12345)])
def test_window_record_preserves_handle_across_ctypes_boundary(monkeypatch, hwnd):
    inventory = inventory_without_platform_setup()
    monkeypatch.setattr(inventory, "_application_for_pid", lambda _pid: "terminal.exe")
    monkeypatch.setattr(inventory, "_display_for_window", lambda _user32, _hwnd: None)

    record = inventory._window_record(FakeUser32(), hwnd, 0, 12345)

    assert record is not None
    assert record["window_id"] == "win:3039"
    assert record["hwnd"] == 12345
    assert record["is_foreground"] is True
    assert inventory.read_error_count == 0


def test_window_record_failure_only_increments_redacted_counter():
    class BrokenUser32(FakeUser32):
        def GetWindowThreadProcessId(self, _hwnd, _pid_pointer):
            raise RuntimeError("sensitive internal window detail")

    inventory = inventory_without_platform_setup()

    assert inventory._window_record(BrokenUser32(), wintypes.HWND(12345), 0, 12345) is None
    assert inventory.read_error_count == 1
    assert vars(inventory) == {
        "_is_windows": True,
        "_process_name_cache": {},
        "_next_process_cache_cleanup": 0.0,
        "_read_error_count": 1,
    }


def test_process_name_cache_prunes_expired_entries_and_enforces_hard_limit():
    inventory = inventory_without_platform_setup()
    inventory._process_name_cache = {
        pid: (0.0, f"expired-{pid}.exe") for pid in range(300)
    }

    inventory._prune_process_name_cache(100.0, force=True)

    assert inventory._process_name_cache == {}
    inventory._process_name_cache = {
        pid: (100.0 + pid / 1000, f"current-{pid}.exe") for pid in range(300)
    }
    inventory._prune_process_name_cache(101.0, force=True)

    assert len(inventory._process_name_cache) == inventory._PROCESS_CACHE_MAX_ENTRIES
    assert min(inventory._process_name_cache) == 44
    assert max(inventory._process_name_cache) == 299


def test_process_lookup_automatically_prunes_expired_cache(monkeypatch):
    class FakeProcess:
        def __init__(self, pid):
            self.pid = pid

        def name(self):
            return f"process-{self.pid}.exe"

    inventory = inventory_without_platform_setup()
    inventory._process_name_cache = {pid: (0.0, f"expired-{pid}.exe") for pid in range(20)}
    monkeypatch.setattr("src.sensing.window_inventory.time.monotonic", lambda: 100.0)
    monkeypatch.setattr("src.sensing.window_inventory.psutil.Process", FakeProcess)

    assert inventory._application_for_pid(999) == "process-999.exe"
    assert inventory._process_name_cache == {999: (100.0, "process-999.exe")}


@pytest.mark.skipif(sys.platform != "win32" or not hasattr(ctypes, "windll"),
                    reason="requires the Windows user32 ctypes boundary")
def test_user32_pointer_sized_signatures_are_declared():
    WindowsWindowInventory()
    user32 = ctypes.windll.user32

    assert user32.GetForegroundWindow.argtypes == []
    assert user32.GetForegroundWindow.restype is wintypes.HWND
    assert user32.GetWindowThreadProcessId.argtypes == [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    assert user32.GetWindowRect.argtypes == [wintypes.HWND, ctypes.POINTER(_RECT)]
    if hasattr(user32, "GetWindowLongPtrW"):
        assert user32.GetWindowLongPtrW.argtypes == [wintypes.HWND, ctypes.c_int]
        assert user32.GetWindowLongPtrW.restype is ctypes.c_ssize_t
