"""Windows 窗口事件源与末梢冲动合并。

回调线程只记录最小事件票据；窗口枚举和消息生成始终留在调用方，
避免在系统回调中进行进程查询或复杂计算。
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import ctypes
import queue
import sys
import threading
import time
from ctypes import wintypes
from typing import Callable, Iterable


@dataclass(frozen=True)
class WindowEventTicket:
    """不含窗口内容的原始系统变化提示。

    票据只保留事件类别、窗口句柄和单调时间；回调线程不做窗口枚举、进程
    查询或消息投递，以免阻塞 Windows 的 WinEvent 分发线程。
    """

    kind: str
    hwnd: int
    occurred_at: float


class WindowImpulseCoalescer:
    """把短时间内的多个事件合并成一次末梢冲动。

    200ms 静默窗口以实际收到票据的时钟为准，而不是信任跨线程传来的事件
    时间戳；这样拖动和窗口切换的事件风暴只触发一次上层读取。
    """

    def __init__(self, debounce_seconds: float = 0.2, clock: Callable[[], float] = time.monotonic):
        if debounce_seconds <= 0:
            raise ValueError("debounce_seconds must be positive")
        self._debounce_seconds = debounce_seconds
        self._clock = clock
        self._pending: deque[WindowEventTicket] = deque()
        self._last_ticket_at: float | None = None

    def record(self, tickets: Iterable[WindowEventTicket]) -> None:
        """追加票据并从末梢接收时刻重新开始合并倒计时。"""
        for ticket in tickets:
            self._pending.append(ticket)
            # 合并期限以末梢实际收到事件的时刻为准，不能假定回调线程和
            # 调用方使用同一个时钟或在同一时刻被调度。
            self._last_ticket_at = self._clock()

    def drain_ready(self, now: float | None = None) -> list[WindowEventTicket]:
        """仅在静默窗口结束后取出并清空当前批次。"""
        if not self._pending or self._last_ticket_at is None:
            return []
        now = self._clock() if now is None else now
        if now - self._last_ticket_at + 1e-9 < self._debounce_seconds:
            return []
        tickets = list(self._pending)
        self._pending.clear()
        self._last_ticket_at = None
        return tickets

    def seconds_until_ready(self, now: float | None = None) -> float | None:
        """返回当前批次距离可取出的剩余秒数；无批次时返回 ``None``。"""
        if self._last_ticket_at is None:
            return None
        now = self._clock() if now is None else now
        return max(0.0, self._debounce_seconds - (now - self._last_ticket_at))


class WindowsWindowEventSource:
    """用 ``SetWinEventHook`` 接收窗口级变化并异步投递最小票据。

    监听线程采用 ``WINEVENT_OUTOFCONTEXT`` 与 ``WINEVENT_SKIPOWNPROCESS``，
    回调只筛选顶层窗口对象并写入队列。非 Windows 平台安全降级为空事件源，
    上层仍可由低频校准完成基本事实读取。
    """

    _EVENTS = {
        0x0003: "foreground_changed",
        0x000A: "move_resize_started",
        0x000B: "move_resize_ended",
        0x0016: "minimize_started",
        0x0017: "minimize_ended",
        0x0020: "desktop_switched",
        0x8002: "shown",
        0x8003: "hidden",
        0x800B: "location_changed",
    }
    # 0x8000 段事件必须再经过 OBJID_WINDOW/CHILDID_SELF 过滤，避免子控件噪声。
    _WINEVENT_OUTOFCONTEXT = 0
    _WINEVENT_SKIPOWNPROCESS = 2
    _WM_QUIT = 0x0012
    _EVENT_OBJECT_BASE = 0x8000
    _OBJID_WINDOW = 0
    _CHILDID_SELF = 0

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._tickets: queue.Queue[WindowEventTicket] = queue.Queue()
        self._is_windows = sys.platform == "win32" and hasattr(ctypes, "windll")
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._ready = threading.Event()
        self._stop_requested = threading.Event()
        self._callback_error_count = 0
        self._startup_error: str | None = None

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    @property
    def callback_error_count(self) -> int:
        return self._callback_error_count

    @property
    def startup_error(self) -> str | None:
        return self._startup_error

    def start(self) -> bool:
        """启动专用 WinEvent 线程，并等待其完成钩子安装。"""
        if not self._is_windows:
            return False
        if self.is_running:
            return True
        self._ready.clear()
        self._stop_requested.clear()
        self._startup_error = None
        self._thread = threading.Thread(target=self._run, name="CyberSpineWindowEvents", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=2.0)
        return self.is_running and self._startup_error is None

    def stop(self) -> None:
        """请求线程退出并等待回调引用安全释放。"""
        self._stop_requested.set()
        if self._is_windows and self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, self._WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(timeout=2.0)
        self._thread = None
        self._thread_id = None

    def drain(self) -> list[WindowEventTicket]:
        """无阻塞取出当前队列中的全部票据。"""
        tickets: list[WindowEventTicket] = []
        while True:
            try:
                tickets.append(self._tickets.get_nowait())
            except queue.Empty:
                return tickets

    def wait(self, timeout: float) -> WindowEventTicket | None:
        """等待一个系统事件，不以短周期轮询替代系统阻塞等待。"""
        try:
            return self._tickets.get(timeout=max(0.0, timeout))
        except queue.Empty:
            return None

    @classmethod
    def accepts_callback(cls, event: int, object_id: int, child_id: int) -> bool:
        """只让顶层窗口自身的对象事件进入末梢。

        EVENT_OBJECT_* 也会为网页和应用内部的辅助功能对象发出；这些
        对象不是窗口目录事实，不能触发一次新的窗口采集。系统级事件
        没有这一对象层级语义，保持原样接收。
        """
        return int(event) < cls._EVENT_OBJECT_BASE or (
            int(object_id) == cls._OBJID_WINDOW and int(child_id) == cls._CHILDID_SELF)

    def _run(self) -> None:
        """安装9类 WinEvent 钩子并运行消息循环，直到收到退出请求。"""
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        handles = []
        callback_type = ctypes.WINFUNCTYPE(None, wintypes.HANDLE, wintypes.DWORD, wintypes.HWND,
                                           wintypes.LONG, wintypes.LONG, wintypes.DWORD, wintypes.DWORD)

        @callback_type
        def callback(_hook, event, hwnd, object_id, child_id, _thread_id, _event_time):
            try:
                kind = self._EVENTS.get(int(event))
                if kind and self.accepts_callback(int(event), int(object_id), int(child_id)):
                    self._tickets.put(WindowEventTicket(kind, int(hwnd or 0), self._clock()))
            except Exception:
                self._callback_error_count += 1

        try:
            self._thread_id = int(kernel32.GetCurrentThreadId())
            for event in self._EVENTS:
                handle = user32.SetWinEventHook(event, event, 0, callback, 0, 0,
                    self._WINEVENT_OUTOFCONTEXT | self._WINEVENT_SKIPOWNPROCESS)
                if not handle:
                    raise OSError(f"SetWinEventHook failed for event {event:#x}")
                handles.append(handle)
            self._ready.set()
            message = wintypes.MSG()
            while not self._stop_requested.is_set() and user32.GetMessageW(ctypes.byref(message), 0, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(message))
                user32.DispatchMessageW(ctypes.byref(message))
        except Exception as error:
            self._startup_error = str(error)
            self._ready.set()
        finally:
            for handle in handles:
                user32.UnhookWinEvent(handle)
            self._ready.set()
