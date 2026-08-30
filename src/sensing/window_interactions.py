"""按前台窗口归因的键盘/鼠标活动统计；绝不记录输入内容或坐标。"""
from collections import defaultdict, deque
from collections.abc import Callable
import ctypes
import sys
import threading
import time
from ctypes import wintypes
from typing import Deque, Optional


class WindowInteractionTracker:
    """保存有限时窗内的交互时间点，供窗口感知插件生成聚合统计。"""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._events: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.RLock()

    def record(self, window_id: str, at: Optional[float] = None) -> None:
        if not window_id:
            return
        with self._lock:
            self._events[window_id].append(self._clock() if at is None else at)

    def summary(self, window_id: str, period_seconds: float, high_frequency_per_minute: float,
                minimum_events: int, now: Optional[float] = None) -> dict:
        now = self._clock() if now is None else now
        cutoff = now - period_seconds
        with self._lock:
            events = self._events[window_id]
            while events and events[0] < cutoff:
                events.popleft()
            count = len(events)
            rate = count * 60 / period_seconds
            return {"period_seconds": period_seconds, "event_count": count,
                    "events_per_minute": round(rate, 2),
                    "is_high_frequency": count >= minimum_events and rate >= high_frequency_per_minute,
                    "last_interaction_monotonic": events[-1] if events else None}


class WindowsGlobalInputMonitor:
    """低级键盘/鼠标钩子，将按键按下、鼠标点击和滚轮归因至当前前台窗口。"""

    _WH_KEYBOARD_LL, _WH_MOUSE_LL = 13, 14
    _WM_KEYDOWN, _WM_SYSKEYDOWN = 0x0100, 0x0104
    _WM_LBUTTONDOWN, _WM_LBUTTONUP = 0x0201, 0x0202
    _WM_RBUTTONDOWN, _WM_RBUTTONUP = 0x0204, 0x0205
    _WM_MBUTTONDOWN, _WM_MBUTTONUP = 0x0207, 0x0208
    _WM_MOUSEWHEEL = 0x020B
    _MOUSE_ACTIONS = {_WM_LBUTTONDOWN, _WM_LBUTTONUP, _WM_RBUTTONDOWN, _WM_RBUTTONUP,
                      _WM_MBUTTONDOWN, _WM_MBUTTONUP, _WM_MOUSEWHEEL}
    _MOUSE_DOWN_ACTIONS = {_WM_LBUTTONDOWN, _WM_RBUTTONDOWN, _WM_MBUTTONDOWN}
    _MOUSE_UP_ACTIONS = {_WM_LBUTTONUP, _WM_RBUTTONUP, _WM_MBUTTONUP}

    def __init__(self, on_input: Callable[[int], None],
                 on_mouse_button_state: Optional[Callable[[bool], None]] = None):
        self._on_input = on_input
        self._on_mouse_button_state = on_mouse_button_state
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._running = threading.Event()
        self._ready = threading.Event()
        self._hooks: list[int] = []
        self._callbacks = []
        self._callback_error_count = 0
        self._pressed_mouse_buttons: set[int] = set()

    @property
    def is_running(self) -> bool:
        return self._running.is_set()

    @property
    def callback_error_count(self) -> int:
        return self._callback_error_count

    def start(self) -> bool:
        if sys.platform != "win32":
            return False
        if self.is_running:
            return True
        self._ready.clear()
        self._thread = threading.Thread(target=self._run, name="CyberSpineWindowInput", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=2)
        return self.is_running

    def stop(self) -> None:
        if self._thread_id and sys.platform == "win32":
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        user32.CallNextHookEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        user32.CallNextHookEx.restype = ctypes.c_ssize_t
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t)

        def make_callback(valid_actions, mouse=False):
            @callback_type
            def callback(code, w_param, l_param):
                try:
                    if code >= 0 and w_param in valid_actions:
                        hwnd = int(user32.GetForegroundWindow() or 0)
                        if hwnd:
                            self._on_input(hwnd)
                        if mouse and self._on_mouse_button_state:
                            if w_param in self._MOUSE_DOWN_ACTIONS:
                                self._pressed_mouse_buttons.add(w_param)
                            elif w_param in self._MOUSE_UP_ACTIONS:
                                self._pressed_mouse_buttons.discard(w_param - 1)
                            self._on_mouse_button_state(bool(self._pressed_mouse_buttons))
                except Exception:
                    self._callback_error_count += 1
                return user32.CallNextHookEx(None, code, w_param, l_param)
            return callback

        keyboard_callback = make_callback({self._WM_KEYDOWN, self._WM_SYSKEYDOWN})
        mouse_callback = make_callback(self._MOUSE_ACTIONS, mouse=True)
        self._callbacks = [keyboard_callback, mouse_callback]
        self._thread_id = int(kernel32.GetCurrentThreadId())
        self._hooks = [int(user32.SetWindowsHookExW(self._WH_KEYBOARD_LL, keyboard_callback, None, 0) or 0),
                       int(user32.SetWindowsHookExW(self._WH_MOUSE_LL, mouse_callback, None, 0) or 0)]
        self._hooks = [hook for hook in self._hooks if hook]
        self._running.set() if self._hooks else self._running.clear()
        self._ready.set()
        msg = wintypes.MSG()
        while self._running.is_set() and user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        for hook in self._hooks:
            user32.UnhookWindowsHookEx(hook)
        self._hooks = []
        self._callbacks = []
        self._running.clear()
