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
    _PROCESS_CACHE_TTL_SECONDS = 30.0
    _PROCESS_CACHE_MAX_ENTRIES = 256

    def __init__(self):
        self._is_windows = sys.platform == "win32" and hasattr(ctypes, "windll")
        self._process_name_cache: dict[int, tuple[float, str]] = {}
        self._next_process_cache_cleanup = 0.0
        self._read_error_count = 0
        if self._is_windows:
            self._configure_user32(ctypes.windll.user32)

    @property
    def read_error_count(self) -> int:
        """返回窗口元数据读取失败次数，不暴露窗口内容或异常文本。"""
        return self._read_error_count

    @staticmethod
    def _hwnd_value(hwnd: Any) -> int:
        """兼容 Win32 回调整数与 ctypes ``HWND`` 包装值。"""
        value = hwnd.value if hasattr(hwnd, "value") else hwnd
        return int(value or 0)

    @staticmethod
    def _configure_user32(user32) -> None:
        """声明增量窗口读取所依赖的 64 位安全 Win32 API 边界。"""
        user32.GetForegroundWindow.argtypes = []
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(_RECT)]
        user32.GetWindowRect.restype = wintypes.BOOL
        if hasattr(user32, "GetWindowLongPtrW"):
            user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
            user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        else:
            user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
            user32.GetWindowLongW.restype = ctypes.c_long

    def list_windows(self) -> list[dict[str, Any]]:
        if not self._is_windows:
            return []
        user32 = ctypes.windll.user32
        foreground_hwnd = self._hwnd_value(user32.GetForegroundWindow())
        windows: list[dict[str, Any]] = []

        callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        @callback_type
        def collect(hwnd, _lparam):
            hwnd_value = self._hwnd_value(hwnd)
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

    def window_for_handle(self, hwnd_value: int) -> dict[str, Any] | None:
        """只读取一个受事件影响的窗口；失效或隐藏窗口返回 ``None``。"""
        if not self._is_windows or not hwnd_value:
            return None
        user32 = ctypes.windll.user32
        hwnd = wintypes.HWND(hwnd_value)
        if not user32.IsWindow(hwnd) or not self._is_user_window(user32, hwnd):
            return None
        foreground_hwnd = self._hwnd_value(user32.GetForegroundWindow())
        return self._window_record(user32, hwnd, 0, foreground_hwnd)

    def foreground_window(self) -> dict[str, Any] | None:
        """读取当前前台窗口，即使它是工具窗口也保留为焦点事实。"""
        if not self._is_windows:
            return None
        user32 = ctypes.windll.user32
        foreground_hwnd = self._hwnd_value(user32.GetForegroundWindow())
        if not foreground_hwnd:
            return None
        return self._window_record(user32, wintypes.HWND(foreground_hwnd), 0, foreground_hwnd)

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
            hwnd_value = self._hwnd_value(hwnd)
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
            self._read_error_count += 1
            return None

    def _application_for_pid(self, pid: int) -> str:
        """短暂缓存进程名，避免在每轮目录校准中重复查询同一 PID。"""
        if not pid:
            return "system"
        now = time.monotonic()
        self._prune_process_name_cache(now)
        cached = self._process_name_cache.get(pid)
        if cached and now - cached[0] < self._PROCESS_CACHE_TTL_SECONDS:
            return cached[1]
        try:
            application = psutil.Process(pid).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            application = "system_protected"
        self._process_name_cache[pid] = (now, application)
        if len(self._process_name_cache) > self._PROCESS_CACHE_MAX_ENTRIES:
            self._prune_process_name_cache(now, force=True)
        return application

    def _prune_process_name_cache(self, now: float, force: bool = False) -> None:
        """定期淘汰过期 PID，并以硬上限约束长期守护进程的缓存。"""
        if not force and now < self._next_process_cache_cleanup \
                and len(self._process_name_cache) <= self._PROCESS_CACHE_MAX_ENTRIES:
            return
        cutoff = now - self._PROCESS_CACHE_TTL_SECONDS
        self._process_name_cache = {pid: value for pid, value in self._process_name_cache.items()
                                    if value[0] > cutoff}
        if len(self._process_name_cache) > self._PROCESS_CACHE_MAX_ENTRIES:
            newest = sorted(self._process_name_cache.items(), key=lambda item: item[1][0], reverse=True)
            self._process_name_cache = dict(newest[:self._PROCESS_CACHE_MAX_ENTRIES])
        self._next_process_cache_cleanup = now + self._PROCESS_CACHE_TTL_SECONDS

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
