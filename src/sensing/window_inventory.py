"""Windows 顶层窗口目录的只读采集。"""
import ctypes
import sys
import time
from ctypes import wintypes
from typing import Any

import psutil


class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", _RECT), ("rcWork", _RECT),
                ("dwFlags", wintypes.DWORD)]


class WindowsWindowInventory:
    """枚举当前可见的应用顶层窗口，不读取窗口内容或屏幕像素。"""

    _GWL_EXSTYLE = -20
    _WS_EX_TOOLWINDOW = 0x00000080
    _WS_EX_TOPMOST = 0x00000008
    _MONITOR_DEFAULTTONEAREST = 2
    _SM_XVIRTUALSCREEN, _SM_YVIRTUALSCREEN = 76, 77
    _SM_CXVIRTUALSCREEN, _SM_CYVIRTUALSCREEN = 78, 79

    def __init__(self):
        self._is_windows = sys.platform == "win32" and hasattr(ctypes, "windll")
        self._process_name_cache: dict[int, tuple[float, str]] = {}

    def list_windows(self) -> list[dict[str, Any]]:
        if not self._is_windows:
            return []
        user32 = ctypes.windll.user32
        foreground_hwnd = int(user32.GetForegroundWindow() or 0)
        windows: list[dict[str, Any]] = []

        callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        @callback_type
        def collect(hwnd, _lparam):
            hwnd_value = int(hwnd or 0)
            if hwnd_value and self._is_user_window(user32, hwnd):
                record = self._window_record(user32, hwnd, len(windows), foreground_hwnd)
                if record is not None:
                    windows.append(record)
            return True

        user32.EnumWindows(collect, 0)
        # 前台窗口是窗口感知的核心事实，即使它带有工具窗口样式也必须保留。
        if foreground_hwnd and not any(item["hwnd"] == foreground_hwnd for item in windows):
            foreground = self._window_record(user32, wintypes.HWND(foreground_hwnd), 0, foreground_hwnd)
            if foreground is not None:
                windows.insert(0, foreground)
                for index, item in enumerate(windows):
                    item["z_order"] = index
        return windows

    def virtual_screen_bounds(self) -> dict[str, int] | None:
        """返回整个虚拟桌面边界；不读取任何屏幕像素。"""
        if not self._is_windows:
            return None
        user32 = ctypes.windll.user32
        width = int(user32.GetSystemMetrics(self._SM_CXVIRTUALSCREEN))
        height = int(user32.GetSystemMetrics(self._SM_CYVIRTUALSCREEN))
        if width <= 0 or height <= 0:
            return None
        return {"left": int(user32.GetSystemMetrics(self._SM_XVIRTUALSCREEN)),
                "top": int(user32.GetSystemMetrics(self._SM_YVIRTUALSCREEN)),
                "width": width, "height": height}

    def _is_user_window(self, user32, hwnd) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return False
        get_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
        ex_style = int(get_long(hwnd, self._GWL_EXSTYLE))
        return not bool(ex_style & self._WS_EX_TOOLWINDOW)

    def _window_record(self, user32, hwnd, z_order: int, foreground_hwnd: int) -> dict[str, Any] | None:
        try:
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            rect = _RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return None
            get_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
            ex_style = int(get_long(hwnd, self._GWL_EXSTYLE))
            application = self._application_for_pid(int(pid.value))
            hwnd_value = int(hwnd)
            return {
                "window_id": f"win:{hwnd_value:x}",
                "hwnd": hwnd_value,
                "application": application,
                "pid": int(pid.value),
                "bounds": {"left": rect.left, "top": rect.top,
                           "width": max(0, rect.right - rect.left),
                           "height": max(0, rect.bottom - rect.top)},
                "z_order": z_order,
                "is_foreground": hwnd_value == foreground_hwnd,
                "is_minimized": bool(user32.IsIconic(hwnd)),
                "is_maximized": bool(user32.IsZoomed(hwnd)),
                "is_topmost": bool(ex_style & self._WS_EX_TOPMOST),
                "display": self._display_for_window(user32, hwnd),
            }
        except Exception:
            return None

    def _application_for_pid(self, pid: int) -> str:
        """短暂缓存进程名，避免在每轮目录校准中重复查询同一 PID。"""
        if not pid:
            return "system"
        now = time.monotonic()
        cached = self._process_name_cache.get(pid)
        if cached and now - cached[0] < 30:
            return cached[1]
        try:
            application = psutil.Process(pid).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            application = "system_protected"
        self._process_name_cache[pid] = (now, application)
        return application

    def _display_for_window(self, user32, hwnd) -> dict[str, Any] | None:
        """返回窗口关联显示器的几何身份；不读取设备名称或屏幕像素。"""
        monitor = user32.MonitorFromWindow(hwnd, self._MONITOR_DEFAULTTONEAREST)
        if not monitor:
            return None
        info = _MONITORINFO()
        info.cbSize = ctypes.sizeof(_MONITORINFO)
        if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return None
        bounds = {"left": int(info.rcMonitor.left), "top": int(info.rcMonitor.top),
                  "width": max(0, int(info.rcMonitor.right - info.rcMonitor.left)),
                  "height": max(0, int(info.rcMonitor.bottom - info.rcMonitor.top))}
        return {"id": f"display:{bounds['left']}:{bounds['top']}:{bounds['width']}x{bounds['height']}",
                "bounds": bounds}
