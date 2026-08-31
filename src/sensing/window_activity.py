"""窗口感知末梢的事实整合层。

本模块只输出可由 Windows 窗口元数据和本地时间证明的事实，不推断用户意图。
正常路径由 WinEvent 冲动驱动，60 秒完整目录校准负责弥补漏事件；5 秒左右的
展示脉冲只推进本地时间视图，不重新读取操作系统。所有消息都保持元数据级，
不携带窗口标题、输入文本、剪贴板、鼠标坐标或屏幕图像。
"""
from collections import deque
from collections.abc import Callable, Mapping
import json
import time
from typing import Any, Optional

from src.core.neural_message import MessageKind, NeuralMessage, PrivacyClass

from .window_interactions import WindowInteractionTracker, WindowsGlobalInputMonitor
from .window_inventory import WindowsWindowInventory
from .window_events import WindowEventTicket, WindowImpulseCoalescer, WindowsWindowEventSource

WindowSnapshotProvider = Callable[[], Mapping[str, Any]]
WindowCatalogProvider = Callable[[], list[Mapping[str, Any]]]
ScreenBoundsProvider = Callable[[], Optional[Mapping[str, Any]]]


class WindowActivityPeripheral:
    """产生窗口层事实并维护有限历史，不在插件中推断用户的具体工作。

    前台解析有三个实际运行时状态：``available``、
    ``temporarily_unresolved`` 和 ``unresolved``；``unavailable`` 是为锁屏或
    安全桌面等明确证据保留的协议状态。系统事件只提供“何时需要重新读取”的
    提示，真正的窗口事实仍由本类在调用线程中读取和整合。
    """

    source = "peripheral.window.activity"
    state_topic = "window.current_state"
    catalog_topic = "window.catalog"
    event_topic = "window.focus_changed"
    activity_topic = "window.high_interaction_changed"
    time_window_topic = "window.time_window_summary"
    availability_topic = "window.foreground_availability_changed"
    geometry_topic = "window.geometry_changed"
    _SYSTEM_SURFACE_APPLICATIONS = frozenset({"applicationframehost.exe", "textinputhost.exe"})
    _SHELL_SURFACE_APPLICATIONS = frozenset({"explorer.exe"})
    _FOREGROUND_AFFECTING_EVENT_KINDS = frozenset({"foreground_changed", "desktop_switched"})
    _FOREGROUND_TRANSITION_EVENT_KINDS = frozenset({"hidden", "minimize_started"})

    def __init__(self, snapshot_provider: Optional[WindowSnapshotProvider] = None,
                 catalog_provider: Optional[WindowCatalogProvider] = None,
                 interaction_tracker: Optional[WindowInteractionTracker] = None,
                 screen_bounds_provider: Optional[ScreenBoundsProvider] = None,
                 clock: Callable[[], float] = time.monotonic, activity_window_seconds: float = 300,
                 focus_window_seconds: float = 1800, high_frequency_per_minute: float = 12,
                 minimum_interactions: int = 6, event_source: Any = None,
                 event_debounce_seconds: float = 0.2, foreground_grace_seconds: float = 1.0,
                 event_diagnostics_enabled: bool = False):
        """建立窗口事实源、有限时间窗和事件合并器。

        ``catalog_provider``/``snapshot_provider`` 是测试与兼容入口；没有外部
        提供者时才绑定 Windows 原生目录。这样既能保持生产路径的单一事实源，
        也能让状态机在不接触真实桌面的情况下回归测试。
        """
        if activity_window_seconds <= 0 or focus_window_seconds <= 0 or foreground_grace_seconds <= 0:
            raise ValueError("activity_window_seconds, focus_window_seconds, and foreground_grace_seconds must be positive")
        self._clock = clock
        self._snapshot_provider = snapshot_provider
        self._inventory: Optional[WindowsWindowInventory] = None
        if catalog_provider is not None:
            self._catalog_provider = catalog_provider
            self._screen_bounds_provider = screen_bounds_provider or (lambda: None)
        elif snapshot_provider is not None:
            self._catalog_provider = lambda: []
            self._screen_bounds_provider = screen_bounds_provider or (lambda: None)
        else:
            inventory = WindowsWindowInventory()
            self._inventory = inventory
            self._catalog_provider = inventory.list_windows
            self._screen_bounds_provider = screen_bounds_provider or inventory.virtual_screen_bounds
        self._tracker = interaction_tracker or WindowInteractionTracker(clock)
        self._activity_window_seconds = activity_window_seconds
        self._focus_window_seconds = focus_window_seconds
        self._high_frequency_per_minute = high_frequency_per_minute
        self._minimum_interactions = minimum_interactions
        self._previous_foreground: Optional[dict[str, Any]] = None
        self._tracked_foreground_id: Optional[str] = None
        self._foreground_started_at: Optional[float] = None
        self._history_started_at: Optional[float] = None
        self._focus_segments: deque[dict[str, Any]] = deque()
        self._unattributed_intervals: deque[dict[str, Optional[float]]] = deque()
        self._foreground_available: Optional[bool] = None
        self._previous_high_interaction_ids: set[str] = set()
        self._input_monitor: Optional[WindowsGlobalInputMonitor] = None
        self._mouse_button_held = False
        self._last_geometry: dict[str, dict[str, Any]] = {}
        self._pending_geometry_changes: list[dict[str, Any]] = []
        self._catalog_cache: dict[str, dict[str, Any]] = {}
        self._last_observed_catalog: Optional[list[dict[str, Any]]] = None
        self._last_observed_foreground: Optional[dict[str, Any]] = None
        self._last_confirmed_foreground: Optional[dict[str, Any]] = None
        self._raw_foreground_missing = False
        self._foreground_unresolved_since: Optional[float] = None
        self._foreground_resolution = "unresolved"
        self._foreground_resolution_reason = "no_foreground_baseline"
        self._foreground_grace_seconds = foreground_grace_seconds
        self._foreground_observation_is_fresh = False
        self._last_published_fact_signature: Optional[str] = None
        self._event_diagnostics_enabled = event_diagnostics_enabled
        self._event_source = event_source or WindowsWindowEventSource(clock)
        self._event_coalescer = WindowImpulseCoalescer(event_debounce_seconds, clock)

    def start_input_monitor(self) -> bool:
        """启动键盘/鼠标钩子；不记录任何键值、坐标或窗口内容。"""
        if self._input_monitor is None:
            self._input_monitor = WindowsGlobalInputMonitor(self._record_hwnd_interaction,
                                                             self.record_mouse_button_state)
        return self._input_monitor.start()

    def start(self, input_monitor: bool = False) -> bool:
        """启动事件源；全局输入钩子仅在明确诊断模式中启用。"""
        event_started = self._event_source.start()
        input_started = self.start_input_monitor() if input_monitor else False
        return event_started or input_started

    def stop_input_monitor(self) -> None:
        """停止可选的全局输入钩子，并清除拖拽候选的按住状态。"""
        if self._input_monitor:
            self._input_monitor.stop()
        self._mouse_button_held = False

    def stop(self) -> None:
        """插件生命周期出口：移除事件源与可选输入钩子，不影响其他组件。"""
        self.stop_input_monitor()
        self._event_source.stop()

    @property
    def input_monitor_running(self) -> bool:
        """返回输入钩子是否实际安装并运行，而不是是否曾被请求启动。"""
        return bool(self._input_monitor and self._input_monitor.is_running)

    @property
    def input_monitor_error_count(self) -> int:
        """返回脱敏的输入回调错误计数，不暴露底层异常文本。"""
        return self._input_monitor.callback_error_count if self._input_monitor else 0

    @property
    def event_source_running(self) -> bool:
        """返回 WinEvent 线程是否仍存活。"""
        return bool(self._event_source.is_running)

    @property
    def event_source_error_count(self) -> int:
        """返回事件回调错误数量，供状态诊断使用。"""
        return int(self._event_source.callback_error_count)

    @property
    def inventory_read_error_count(self) -> int:
        """返回窗口目录读取失败次数；错误详情不进入消息。"""
        return int(getattr(self._inventory, "read_error_count", 0))

    def collect_event_messages(self) -> list[NeuralMessage]:
        """仅在合并后的系统窗口事件形成冲动时读取并发布窗口事实。"""
        self._event_coalescer.record(self._event_source.drain())
        tickets = self._event_coalescer.drain_ready()
        if not tickets:
            return []
        return self.collect_messages(event_tickets=tickets)

    def wait_for_event_messages(self, timeout: float) -> list[NeuralMessage]:
        """阻塞等待系统事件或合并期限；超时本身不产生窗口读取。"""
        ready_in = self._event_coalescer.seconds_until_ready()
        timeout = min(timeout, ready_in) if ready_in is not None else timeout
        ticket = self._event_source.wait(timeout)
        if ticket is not None:
            self._event_coalescer.record([ticket])
        return self.collect_event_messages()

    def collect_local_time_messages(self) -> list[NeuralMessage]:
        """仅以本地单调时钟刷新已知事实的驻留与时间窗，不读取操作系统。"""
        if self._last_observed_catalog is None:
            return []
        self._pending_geometry_changes = []
        now = self._clock()
        foreground, status = self._local_foreground(now)
        self._last_observed_foreground = foreground
        catalog = self._decorate_catalog(self._last_observed_catalog,
                                         foreground, now)
        messages = [self._state_message(foreground, catalog, status), self._catalog_message(catalog),
                    self._time_window_message(catalog, now, status)]
        availability = self._availability_event(foreground, status)
        if availability:
            messages.append(availability)
        return messages

    def collect_foreground_resolution_messages(self) -> list[NeuralMessage]:
        """宽限到期后只重读一次前台；成功确认或明确进入未解析。"""
        due = self.foreground_resolution_due_seconds()
        if due is None or due > 0:
            return []
        self._pending_geometry_changes = []
        now = self._clock()
        if self._inventory is None:
            catalog, raw_foreground = self._observed_catalog()
        else:
            raw_foreground = self._inventory.foreground_window()
            if raw_foreground is not None:
                normalized = self._normalize_window(raw_foreground, raw_foreground.get("z_order", 0))
                foreground_id = normalized["window_id"]
                self._catalog_cache[foreground_id] = normalized
                for window_id, item in self._catalog_cache.items():
                    item["is_foreground"] = window_id == foreground_id
            catalog = list(self._catalog_cache.values())
        foreground, status = self._resolve_foreground(raw_foreground, now)
        self._last_observed_catalog = catalog
        self._last_observed_foreground = foreground
        decorated = self._decorate_catalog(catalog, foreground, now)
        messages = [self._state_message(foreground, decorated, status), self._catalog_message(decorated),
                    self._time_window_message(decorated, now, status)]
        for event in (self._availability_event(foreground, status), self._focus_event(foreground),
                      self._activity_event(decorated), self._geometry_event()):
            if event:
                messages.append(event)
        self._last_published_fact_signature = self._fact_signature(decorated, status)
        return messages

    def foreground_resolution_due_seconds(self) -> Optional[float]:
        """返回一次前台缺失确认还需等待的时间；不是周期性采样。"""
        if self._foreground_resolution != "temporarily_unresolved" or self._foreground_unresolved_since is None:
            return None
        return max(0.0, self._foreground_grace_seconds - (self._clock() - self._foreground_unresolved_since))

    def record_interaction(self, window_id: str, at: Optional[float] = None) -> None:
        """记录一次不含键值或坐标的交互时间点，并归因给窗口 ID。"""
        self._tracker.record(window_id, at)

    def record_mouse_button_state(self, held: bool) -> None:
        """只保存鼠标按键是否按住，不保存坐标、按键类型或原始输入。"""
        self._mouse_button_held = bool(held)

    def current_state(self) -> NeuralMessage:
        """读取一次完整当前状态；事件驱动主循环通常使用 ``collect_messages``。"""
        catalog, foreground = self._observed_catalog()
        return self._state_message(foreground, self._decorate_catalog(catalog, foreground))

    def collect_messages(self, event_tickets: Optional[list[WindowEventTicket]] = None) -> list[NeuralMessage]:
        """从低频完整校准或一批事件冲动产生窗口事实消息。"""
        self._pending_geometry_changes = []
        catalog, raw_foreground = self._observed_catalog(event_tickets)
        now = self._clock()
        if self._foreground_observation_is_fresh:
            foreground, status = self._resolve_foreground(raw_foreground, now)
        else:
            foreground, status = self._last_observed_foreground, self._foreground_resolution
        self._last_observed_catalog = catalog
        self._last_observed_foreground = foreground
        decorated = self._decorate_catalog(catalog, foreground, now)
        fact_signature = self._fact_signature(decorated, status)
        if event_tickets and fact_signature == self._last_published_fact_signature:
            # 内部 UI 对象或重复 WinEvent 可能仍穿过系统队列；既然窗口层
            # 事实未变，就不把它伪装成新的神经信号或写入观察日志。
            return []
        diagnostics = self._event_diagnostics(event_tickets) if event_tickets and self._event_diagnostics_enabled else None
        messages = [self._state_message(foreground, decorated, status, diagnostics), self._catalog_message(decorated),
                    self._time_window_message(decorated, now, status)]
        for event in (self._availability_event(foreground, status), self._focus_event(foreground),
                      self._activity_event(decorated), self._geometry_event()):
            if event:
                messages.append(event)
        self._last_published_fact_signature = fact_signature
        return messages

    @staticmethod
    def _fact_signature(catalog: list[dict[str, Any]], foreground_status: str) -> str:
        """比较用户窗口事实，排除本地派生字段与瞬态系统表面噪声。

        驻留秒数、交互统计和几何活动会随展示脉冲变化，不能单独构成新的
        神经事实；输入法系统表面也不能因为候选框尺寸变化触发状态重发。
        """
        volatile_fields = {"focus_dwell_seconds", "interaction", "geometry_activity"}
        windows = [{key: value for key, value in item.items() if key not in volatile_fields}
                   for item in sorted(catalog, key=lambda item: item["window_id"])
                   if item.get("presentation", {}).get("state") != "system_surface"]
        return json.dumps({"foreground_status": foreground_status, "windows": windows},
                          sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _event_diagnostics(tickets: list[WindowEventTicket]) -> dict[str, Any]:
        """供诊断模式观察事件批次，不暴露句柄、标题或其他窗口内容。"""
        kinds = sorted({ticket.kind for ticket in tickets})
        return {"source": "win_event_hook", "ticket_count": len(tickets), "kinds": kinds,
                "window_identifiers_included": False}

    def _resolve_foreground(self, raw_foreground: Optional[dict[str, Any]], now: float) -> tuple[Optional[dict[str, Any]], str]:
        """将一次空前台读取先标为未解析，避免伪造注意力中断。

        首次缺失且没有基线时直接是 ``unresolved``；已有基线时先进入
        ``temporarily_unresolved``，在 1 秒宽限内保留最后确认窗口。宽限到期
        只允许一次真正的前台重读，仍为空才进入 ``unresolved``。
        """
        self._raw_foreground_missing = raw_foreground is None
        if raw_foreground is not None:
            self._last_confirmed_foreground = dict(raw_foreground)
            self._foreground_unresolved_since = None
            self._foreground_resolution = "available"
            self._foreground_resolution_reason = "raw_foreground_present"
            return raw_foreground, self._foreground_resolution
        if self._last_confirmed_foreground is None:
            self._foreground_resolution = "unresolved"
            self._foreground_resolution_reason = "no_foreground_baseline"
            return None, self._foreground_resolution
        if self._foreground_unresolved_since is None:
            self._foreground_unresolved_since = now
        if now - self._foreground_unresolved_since < self._foreground_grace_seconds:
            self._foreground_resolution = "temporarily_unresolved"
            self._foreground_resolution_reason = "raw_foreground_handle_missing"
            return dict(self._last_confirmed_foreground), self._foreground_resolution
        self._foreground_resolution = "unresolved"
        self._foreground_resolution_reason = "foreground_resolution_timeout"
        return None, self._foreground_resolution

    def _local_foreground(self, now: float) -> tuple[Optional[dict[str, Any]], str]:
        """返回最近一次已知前台，禁止展示脉冲推进状态机。

        ``now`` 只服务于接口对称性和调用方时序；本地脉冲不能把宽限期自动
        推进到 ``unresolved``，否则一个 UI 刷新就会伪造系统前台变化。
        """
        # 展示脉冲不读取操作系统，也不得把“待确认”自行推进为未解析；
        # 状态转换只由一次性前台重读完成。
        return self._last_observed_foreground, self._foreground_resolution

    def poll_focus_change(self) -> Optional[NeuralMessage]:
        """兼容旧调用方的单次焦点事件查询，不改变事件驱动主路径。"""
        _catalog, foreground = self._observed_catalog()
        return self._focus_event(foreground)

    def _observed_catalog(self, event_tickets: Optional[list[WindowEventTicket]] = None) -> tuple[list[dict[str, Any]], Optional[dict[str, Any]]]:
        """选择增量事件目录或完整目录，并标记本次前台事实是否新鲜。

        只有带有效窗口句柄且不是桌面切换的事件批次才走增量路径；桌面切换
        必须重新枚举，因为单窗口读取无法提供全局 Z 序和窗口增删事实。
        """
        if event_tickets and self._inventory is not None and self._catalog_cache and \
                all(ticket.hwnd and ticket.kind != "desktop_switched" for ticket in event_tickets):
            return self._event_catalog(event_tickets)
        self._foreground_observation_is_fresh = True
        catalog = [self._normalize_window(raw, index) for index, raw in enumerate(self._catalog_provider())]
        self._catalog_cache = {item["window_id"]: item for item in catalog}
        foreground = next((window for window in catalog if window["is_foreground"]), None)
        if foreground is None and self._snapshot_provider is not None:
            foreground = self._legacy_snapshot()
        return catalog, foreground

    def _event_catalog(self, tickets: list[WindowEventTicket]) -> tuple[list[dict[str, Any]], Optional[dict[str, Any]]]:
        """只更新事件影响的句柄与当前前台；完整枚举留给低频校准。

        ``preserved_foreground_id`` 是一致性护栏：后台位置、隐藏或最小化事件
        不得因为一次瞬时空读取抹掉已确认前台。事件句柄只足以定位目标窗口，
        不足以推断新的全局 Z 序，因此未受影响窗口保留目录基线。
        """
        assert self._inventory is not None
        affected_ids = {f"win:{ticket.hwnd:x}" for ticket in tickets if ticket.hwnd}
        preserved_foreground_id = next((window_id for window_id, item in self._catalog_cache.items()
                                        if item.get("is_foreground")), None)
        if preserved_foreground_id is None and self._last_observed_foreground is not None:
            preserved_foreground_id = self._last_observed_foreground["window_id"]
        foreground_refresh_required = any(ticket.kind in self._FOREGROUND_AFFECTING_EVENT_KINDS
                                          for ticket in tickets) or any(
            ticket.kind in self._FOREGROUND_TRANSITION_EVENT_KINDS and
            f"win:{ticket.hwnd:x}" == preserved_foreground_id for ticket in tickets if ticket.hwnd)
        missing_window_ids: set[str] = set()
        for ticket in tickets:
            if not ticket.hwnd:
                continue
            window_id = f"win:{ticket.hwnd:x}"
            record = self._inventory.window_for_handle(ticket.hwnd)
            if record is None:
                missing_window_ids.add(window_id)
                # 前台正隐藏、最小化或切换时，Win32 可能暂时不能以普通
                # 用户窗口形式读取它。先保留最后确认事实，等前台读取结果
                # 决定是否移除，不能把系统过渡伪装成“没有前台”。
                if window_id != preserved_foreground_id:
                    self._catalog_cache.pop(window_id, None)
            else:
                previous = self._catalog_cache.get(window_id)
                # 单窗口读取不具备完整 EnumWindows 的全局 Z 序；若事件记录
                # 本身未提供该事实，保留最近一次目录基线，避免伪造变化。
                updated = self._normalize_window(record, record.get("z_order", previous.get("z_order", 0)
                                                if previous is not None else 0))
                # 几何/显示等后台事件只能更新该窗口自身事实，不能因一次
                # 非前台查询结果而抹掉已经确认的前台标记。
                if not foreground_refresh_required:
                    updated["is_foreground"] = window_id == preserved_foreground_id
                self._catalog_cache[window_id] = updated

        self._foreground_observation_is_fresh = foreground_refresh_required
        foreground_record = self._inventory.foreground_window() if foreground_refresh_required else None
        if foreground_record is None and foreground_refresh_required:
            # GetForegroundWindow() 在某些系统过渡或宿主切换中会短暂返回 0，
            # 但前台事件本身已携带新句柄。仅使用明确的前台切换事件作补证，
            # 不把任意位置变化窗口误认为前台。
            foreground_ticket = next((ticket for ticket in reversed(tickets)
                                      if ticket.kind == "foreground_changed" and ticket.hwnd), None)
            if foreground_ticket is not None:
                foreground_record = self._inventory.window_for_handle(foreground_ticket.hwnd)
                if foreground_record is not None:
                    foreground_record["is_foreground"] = True
        foreground_id = None
        if foreground_record is not None:
            foreground = self._normalize_window(foreground_record, foreground_record.get("z_order", 0))
            foreground_id = foreground["window_id"]
            self._catalog_cache[foreground_id] = foreground
            affected_ids.add(foreground_id)
        if foreground_record is not None:
            for window_id in missing_window_ids:
                if window_id != foreground_id:
                    self._catalog_cache.pop(window_id, None)
        if foreground_record is None:
            foreground_id = preserved_foreground_id
        for window_id, item in self._catalog_cache.items():
            item["is_foreground"] = window_id == foreground_id
            if window_id not in affected_ids:
                # 缓存条目的位置等事实未重新读取；只同步本次前台标记。
                item["z_order"] = item.get("z_order", 0)
        catalog = list(self._catalog_cache.values())
        foreground = next((item for item in catalog if item["is_foreground"]), None)
        # 缓存仍保留最后确认窗口以维持目录一致性；但本次前台读取并没有
        # 新证据，因此必须让上层进入一次性宽限，而非伪造 confirmed。
        return catalog, None if foreground_refresh_required and foreground_record is None else foreground

    def _legacy_snapshot(self) -> dict[str, Any]:
        raw = self._snapshot_provider() if self._snapshot_provider else self._default_snapshot()
        return self._normalize_window(raw, 0, fallback_foreground=True)

    def _decorate_catalog(self, catalog: list[dict[str, Any]], foreground: Optional[dict[str, Any]],
                          now: Optional[float] = None) -> list[dict[str, Any]]:
        """把原始目录装饰成公开窗口事实，并维护几何与交互派生状态。

        系统表面会参与内部基线更新，却在神经事件层被降噪；这保证后续恢复
        时仍能比较真实边界，同时不会把输入法候选框当成用户窗口移动。
        """
        now = self._clock() if now is None else now
        if foreground is None:
            self._observe_unattributed(now)
            current_id, focus_dwell = None, 0.0
        else:
            self._close_unattributed(now)
            self._observe_focus(foreground, now)
            current_id = foreground["window_id"]
            focus_started_at = self._foreground_started_at if self._foreground_started_at is not None else now
            focus_dwell = max(0.0, now - focus_started_at)
        screen_bounds = self._screen_bounds()
        decorated = []
        for window in catalog or ([foreground] if foreground is not None else []):
            item = self._public_window(window)
            item["is_foreground"] = item["window_id"] == current_id
            item["presentation"] = self._presentation(item, screen_bounds)
            item["window_state"] = self._window_state(item)
            decorated.append(item)
        transient_system_bounds = [item["bounds"] for item in decorated
            if item["presentation"]["state"] == "system_surface"
            and not item["window_state"]["is_fullscreen_candidate"]]
        for item in decorated:
            if self._is_synchronized_shell_surface(item, transient_system_bounds):
                item["presentation"] = {**item["presentation"], "state": "system_surface",
                                        "is_user_presented": False}
            suppress_geometry_event = item["presentation"]["state"] == "system_surface"
            item["geometry_activity"] = self._observe_geometry(
                item, now, emit_event=not suppress_geometry_event)
            item["focus_dwell_seconds"] = round(focus_dwell, 2) if item["is_foreground"] else 0.0
            item["interaction"] = self._tracker.summary(item["window_id"], self._activity_window_seconds,
                self._high_frequency_per_minute, self._minimum_interactions, now)
        return decorated

    @classmethod
    def _is_synchronized_shell_surface(cls, window: Mapping[str, Any],
                                       system_bounds: list[Mapping[str, int]]) -> bool:
        """识别与输入法浮窗同边同步的无标题 Shell 伴生表面。

        只匹配非前台、无标题的 ``explorer.exe``，并要求左右边界近似相同且
        垂直区间重叠；普通有标题资源管理器不会被归入系统表面。
        """
        if (str(window["application"]).lower() not in cls._SHELL_SURFACE_APPLICATIONS
                or window.get("has_title", False) or window.get("is_foreground", False)):
            return False
        bounds = window["bounds"]
        for surface in system_bounds:
            same_horizontal_span = (abs(bounds["left"] - surface["left"]) <= 2
                                    and abs(bounds["width"] - surface["width"]) <= 2)
            vertical_overlap = (bounds["top"] < surface["top"] + surface["height"]
                                and bounds["top"] + bounds["height"] > surface["top"])
            if same_horizontal_span and vertical_overlap:
                return True
        return False

    @staticmethod
    def _window_state(window: Mapping[str, Any]) -> dict[str, Any]:
        """窗口样式与关联显示器的事实；全屏仅是几何候选，不识别像素或独占模式。"""
        display = window.get("display") or {}
        display_bounds = display.get("bounds") if isinstance(display, Mapping) else None
        bounds = window["bounds"]
        covers_display = bool(display_bounds and all(
            abs(int(bounds[key]) - int(display_bounds[key])) <= 2
            for key in ("left", "top", "width", "height")))
        return {"is_maximized": bool(window["is_maximized"]),
                "is_topmost": bool(window.get("is_topmost", False)),
                "is_fullscreen_candidate": bool(not window["is_minimized"] and covers_display),
                "fullscreen_detection": "covers_associated_display" if display_bounds else "display_unknown",
                "display": display or None}

    def _observe_geometry(self, window: Mapping[str, Any], now: float,
                          emit_event: bool = True) -> dict[str, Any]:
        """依据连续目录快照记录边界变化，并可选择是否投递几何事件。

        无论 ``emit_event`` 是否为真，当前边界都会写入 ``_last_geometry``；
        因而被过滤的输入法窗口不会污染下一次真实窗口变化的比较基线。鼠标
        按住只提供“可能正在拖拽”的弱证据，不代表一定发生了用户拖动。
        """
        window_id = str(window["window_id"])
        current_bounds = dict(window["bounds"])
        current_display = (window.get("window_state") or {}).get("display") or window.get("display")
        previous = self._last_geometry.get(window_id)
        self._last_geometry[window_id] = {"bounds": current_bounds, "display": current_display}
        if previous is None:
            return {"state": "stationary", "is_in_progress_candidate": False,
                    "detection_basis": "baseline"}
        moved = any(current_bounds[key] != previous["bounds"][key] for key in ("left", "top"))
        resized = any(current_bounds[key] != previous["bounds"][key] for key in ("width", "height"))
        display_changed = self._display_id(current_display) != self._display_id(previous.get("display"))
        if not moved and not resized and not display_changed:
            return {"state": "stationary", "is_in_progress_candidate": False,
                    "detection_basis": "no_geometry_change"}
        change = "moved_and_resized" if moved and resized else "moved" if moved else "resized" if resized else "display_changed"
        is_candidate = bool(self._mouse_button_held and (moved or resized))
        state = f"{change}_candidate" if is_candidate else "geometry_changed"
        observation = {"state": state, "is_in_progress_candidate": is_candidate,
                       "detection_basis": "mouse_button_held_and_geometry_change" if is_candidate
                       else "geometry_change_without_drag_evidence"}
        if emit_event:
            self._pending_geometry_changes.append({"window": self._public_window(window),
                "previous_bounds": previous["bounds"], "current_bounds": current_bounds,
                "change": change, "previous_display": previous.get("display"),
                "current_display": current_display, "is_in_progress_candidate": is_candidate,
                "detection_basis": observation["detection_basis"]})
        return observation

    @staticmethod
    def _display_id(display: Any) -> Optional[str]:
        return str(display.get("id")) if isinstance(display, Mapping) and display.get("id") else None

    def _screen_bounds(self) -> Optional[dict[str, int]]:
        """读取并校验虚拟桌面边界；失败时降级为未知显示器几何。"""
        try:
            raw = self._screen_bounds_provider()
        except Exception:
            return None
        if not raw:
            return None
        width, height = int(raw.get("width", 0)), int(raw.get("height", 0))
        if width <= 0 or height <= 0:
            return None
        return {"left": int(raw.get("left", 0)), "top": int(raw.get("top", 0)),
                "width": width, "height": height}

    @classmethod
    def _presentation(cls, window: Mapping[str, Any], screen_bounds: Optional[Mapping[str, int]]) -> dict[str, Any]:
        """基于窗口元数据判断呈现状态，不尝试判断像素可见内容或遮挡比例。"""
        bounds = window["bounds"]
        has_area = bounds["width"] > 0 and bounds["height"] > 0
        intersects = has_area if screen_bounds is None else cls._rectangles_intersect(bounds, screen_bounds)
        application = str(window["application"]).lower()
        if application in cls._SYSTEM_SURFACE_APPLICATIONS:
            state, user_presented = "system_surface", False
        elif window["is_minimized"]:
            state, user_presented = "minimized", False
        elif not intersects:
            state, user_presented = "offscreen", False
        elif window["is_foreground"]:
            state, user_presented = "foreground", True
        else:
            state, user_presented = "screen_present", True
        return {"state": state, "is_screen_present": intersects and not window["is_minimized"],
                "is_user_presented": user_presented, "display_bounds_known": screen_bounds is not None}

    @staticmethod
    def _rectangles_intersect(first: Mapping[str, int], second: Mapping[str, int]) -> bool:
        """用半开矩形区间判断相交，兼容负坐标多显示器布局。"""
        return (first["left"] < second["left"] + second["width"] and
                first["left"] + first["width"] > second["left"] and
                first["top"] < second["top"] + second["height"] and
                first["top"] + first["height"] > second["top"])

    def _observe_unattributed(self, now: float) -> None:
        """任务视图、锁屏等系统过渡态不归因给虚假的 unknown 窗口。"""
        if self._history_started_at is None:
            self._history_started_at = now
        if self._focus_segments and self._focus_segments[-1].get("ended_at") is None:
            self._focus_segments[-1]["ended_at"] = now
        self._tracked_foreground_id = None
        self._foreground_started_at = None
        if not self._unattributed_intervals or self._unattributed_intervals[-1].get("ended_at") is not None:
            self._unattributed_intervals.append({"started_at": now, "ended_at": None})
        self._prune_focus_history(now)

    def _close_unattributed(self, now: float) -> None:
        if self._unattributed_intervals and self._unattributed_intervals[-1].get("ended_at") is None:
            self._unattributed_intervals[-1]["ended_at"] = now
        self._prune_focus_history(now)

    def _observe_focus(self, foreground: Mapping[str, Any], now: float) -> None:
        """仅从本插件观察开始维护有限焦点片段，不补造启动前历史。"""
        current_id = str(foreground["window_id"])
        if self._history_started_at is None:
            self._history_started_at = now
        if self._tracked_foreground_id == current_id:
            return
        if self._focus_segments and self._focus_segments[-1].get("ended_at") is None:
            self._focus_segments[-1]["ended_at"] = now
        self._tracked_foreground_id = current_id
        self._foreground_started_at = now
        public = self._public_window(foreground)
        previous_id = self._focus_segments[-1]["window_id"] if self._focus_segments else None
        self._focus_segments.append({"window_id": current_id, "application": public["application"],
                                     "pid": public["pid"], "started_at": now, "ended_at": None,
                                     "is_focus_switch": previous_id is not None and previous_id != current_id})
        self._prune_focus_history(now)

    def _prune_focus_history(self, now: float) -> None:
        """按观察窗淘汰已结束焦点片段和未归因区间，保留活动尾段。"""
        cutoff = now - self._focus_window_seconds
        while len(self._focus_segments) > 1 and self._focus_segments[0].get("ended_at") is not None \
                and self._focus_segments[0]["ended_at"] <= cutoff:
            self._focus_segments.popleft()
        while self._unattributed_intervals and self._unattributed_intervals[0].get("ended_at") is not None \
                and self._unattributed_intervals[0]["ended_at"] <= cutoff:
            self._unattributed_intervals.popleft()

    def _state_message(self, foreground: Optional[dict[str, Any]], catalog: list[dict[str, Any]],
                       foreground_status: str = "available",
                       event_diagnostics: Optional[dict[str, Any]] = None) -> NeuralMessage:
        """生成当前状态消息；前台状态和诊断字段均保持元数据级。"""
        current = next((window for window in catalog if window["is_foreground"]), None)
        payload = {"foreground": current, "window_count": len(catalog),
            "foreground_status": foreground_status,
            "foreground_confidence": "confirmed" if foreground_status == "available" else
                "last_confirmed" if foreground_status == "temporarily_unresolved" else "none",
            "foreground_resolution_reason": self._foreground_resolution_reason,
            "last_confirmed_foreground_age_seconds": self._last_confirmed_foreground_age(),
            "interaction_observation": "global_input_hook" if self.input_monitor_running else "not_started",
            "input_monitor_callback_errors": self.input_monitor_error_count,
            "event_observation": "win_event_hook" if self.event_source_running else "low_frequency_calibration_only",
            "event_source_callback_errors": self.event_source_error_count,
            "window_inventory_read_errors": self.inventory_read_error_count}
        if event_diagnostics is not None:
            payload["event_diagnostics"] = event_diagnostics
        return NeuralMessage(kind=MessageKind.STATE, source=self.source, topic=self.state_topic,
            payload_schema="window.current_state@3", payload=payload,
            privacy=PrivacyClass.METADATA_ONLY, ttl_seconds=120, collapse_key=self.state_topic)

    def _catalog_message(self, catalog: list[dict[str, Any]]) -> NeuralMessage:
        """生成完整窗口目录消息，并区分屏幕呈现与用户呈现计数。"""
        screen_present = [item for item in catalog if item["presentation"]["is_screen_present"]]
        user_presented = [item for item in catalog if item["presentation"]["is_user_presented"]]
        return NeuralMessage(kind=MessageKind.STATE, source=self.source, topic=self.catalog_topic,
            payload_schema="window.catalog@1", payload={"windows": catalog, "window_count": len(catalog),
            "screen_present_window_count": len(screen_present),
            "screen_present_user_window_count": len(user_presented),
            "screen_present_user_window_ids": [item["window_id"] for item in user_presented]},
            privacy=PrivacyClass.METADATA_ONLY, ttl_seconds=120, collapse_key=self.catalog_topic)

    def _time_window_message(self, catalog: list[dict[str, Any]], now: float,
                             foreground_status: str = "available") -> NeuralMessage:
        """输出本插件观察窗内的时间分区事实，不包含意图解释或原始标题。

        焦点片段与未归因区间互斥，最终强制满足
        ``focus_total + unattributed == elapsed``，再计算比例，避免任何窗口
        因恢复逻辑或边界截断而获得超过 100% 的占比。
        """
        self._prune_focus_history(now)
        cutoff = now - self._focus_window_seconds
        totals: dict[str, dict[str, Any]] = {}
        segments: list[dict[str, Any]] = []
        for segment in self._focus_segments:
            started_at = max(segment["started_at"], cutoff)
            ended_at = min(segment.get("ended_at") or now, now)
            duration = max(0.0, ended_at - started_at)
            if duration == 0:
                continue
            window_id = segment["window_id"]
            item = totals.setdefault(window_id, {"window_id": window_id,
                "application": segment["application"], "pid": segment["pid"],
                "focus_seconds": 0.0, "focus_segment_count": 0})
            item["focus_seconds"] += duration
            item["focus_segment_count"] += 1
            segments.append({"window_id": window_id, "application": segment["application"],
                             "pid": segment["pid"], "duration_seconds": round(duration, 2),
                             "is_active": segment.get("ended_at") is None})
        elapsed_seconds = min(self._focus_window_seconds,
            max(0.0, now - (self._history_started_at if self._history_started_at is not None else now)))
        unattributed_seconds = sum(max(0.0, min(interval.get("ended_at") or now, now) -
            max(interval["started_at"], cutoff)) for interval in self._unattributed_intervals)
        focus_total_seconds = sum(item["focus_seconds"] for item in totals.values())
        # 焦点片段和不可归因区间必须构成一个时间分区；从焦点片段反推
        # 不可归因时长，杜绝两个账本重叠后产生超过 100% 的专注占比。
        observed_seconds = min(elapsed_seconds, focus_total_seconds)
        unattributed_seconds = max(0.0, elapsed_seconds - observed_seconds)
        for item in totals.values():
            raw_focus_seconds = item["focus_seconds"]
            item["focus_ratio"] = round(raw_focus_seconds / observed_seconds, 4) if observed_seconds else 0.0
            item["focus_seconds"] = round(raw_focus_seconds, 2)
            item["interaction"] = self._tracker.summary(item["window_id"], self._activity_window_seconds,
                self._high_frequency_per_minute, self._minimum_interactions, now)
        return NeuralMessage(kind=MessageKind.STATE, source=self.source, topic=self.time_window_topic,
            payload_schema="window.time_window_summary@1", payload={
                "period_seconds": self._focus_window_seconds,
                "elapsed_seconds": round(elapsed_seconds, 2),
                "observed_seconds": round(observed_seconds, 2),
                "unattributed_seconds": round(unattributed_seconds, 2),
                "coverage_ratio": round(observed_seconds / self._focus_window_seconds, 4),
                "focus_switch_count": sum(1 for segment in self._focus_segments
                                  if segment.get("is_focus_switch") and cutoff < segment["started_at"] <= now),
                "segments": segments,
                "windows": sorted(totals.values(), key=lambda item: (-item["focus_seconds"], item["window_id"])),
                "foreground_window_id": next((item["window_id"] for item in catalog if item["is_foreground"]), None),
                "foreground_status": foreground_status,
                "time_accounting_invariant": "focus_plus_unattributed_equals_elapsed",
            }, privacy=PrivacyClass.METADATA_ONLY, ttl_seconds=120, collapse_key=self.time_window_topic)

    def _availability_event(self, current: Optional[dict[str, Any]], foreground_status: str) -> Optional[NeuralMessage]:
        """仅在可归因能力边界变化时投递事件，不把 unresolved 伪装成锁屏。"""
        # `unresolved` 仅表示当前无法取得可靠前台事实，不能被伪装成用户
        # 进入锁屏/安全桌面等真正的不可归因状态。
        available = foreground_status in {"available", "temporarily_unresolved", "unresolved"}
        previous = self._foreground_available
        self._foreground_available = available
        if previous is None or previous == available:
            return None
        return NeuralMessage(kind=MessageKind.EVENT, source=self.source, topic=self.availability_topic,
            payload_schema="window.foreground_availability_changed@1", payload={
                "previous_status": "available" if previous else "unavailable",
                "current_status": "available" if available else "unavailable",
                "reason": self._foreground_resolution_reason,
                "recovered_foreground": self._public_window(current) if available else None},
            privacy=PrivacyClass.METADATA_ONLY, ttl_seconds=300, collapse_key=self.availability_topic)

    def _last_confirmed_foreground_age(self) -> Optional[float]:
        if self._foreground_unresolved_since is None:
            return 0.0 if self._last_confirmed_foreground is not None else None
        return round(max(0.0, self._clock() - self._foreground_unresolved_since), 3)

    def _focus_event(self, current: Optional[dict[str, Any]]) -> Optional[NeuralMessage]:
        """比较已公开的前台窗口身份，生成去标题的焦点切换事件。"""
        if current is None:
            return None
        current = self._public_window(current)
        previous = self._previous_foreground
        self._previous_foreground = dict(current)
        if previous is None or previous["window_id"] == current["window_id"]:
            return None
        return NeuralMessage(kind=MessageKind.EVENT, source=self.source, topic=self.event_topic,
            payload_schema="window.focus_changed@2", payload={"previous": previous, "current": current},
            privacy=PrivacyClass.METADATA_ONLY, ttl_seconds=300, collapse_key=self.event_topic)

    def _activity_event(self, catalog: list[dict[str, Any]]) -> Optional[NeuralMessage]:
        """只在高频交互窗口集合变化时投递一次聚合事件。"""
        current_ids = {window["window_id"] for window in catalog if window["interaction"]["is_high_frequency"]}
        if current_ids == self._previous_high_interaction_ids:
            return None
        previous = sorted(self._previous_high_interaction_ids)
        self._previous_high_interaction_ids = current_ids
        return NeuralMessage(kind=MessageKind.EVENT, source=self.source, topic=self.activity_topic,
            payload_schema="window.high_interaction_changed@1", payload={"previous_window_ids": previous,
            "current_window_ids": sorted(current_ids), "period_seconds": self._activity_window_seconds},
            privacy=PrivacyClass.METADATA_ONLY, ttl_seconds=300, collapse_key=self.activity_topic)

    def _geometry_event(self) -> Optional[NeuralMessage]:
        """把本次目录采样中未被降噪的几何变化打包成一条事件。"""
        if not self._pending_geometry_changes:
            return None
        return NeuralMessage(kind=MessageKind.EVENT, source=self.source, topic=self.geometry_topic,
            payload_schema="window.geometry_changed@1", payload={"changes": self._pending_geometry_changes},
            privacy=PrivacyClass.METADATA_ONLY, ttl_seconds=300)

    def _record_hwnd_interaction(self, hwnd: int) -> None:
        """将输入钩子提供的 HWND 转为内部窗口 ID；不保存原始输入。"""
        self.record_interaction(f"win:{hwnd:x}")

    @staticmethod
    def _default_snapshot() -> Mapping[str, Any]:
        # Do not fall back to the legacy foreground perceptor here.  This
        # peripheral is the canonical window fact source; calling the legacy
        # adapter would introduce a circular dependency and duplicate a Win32
        # read when window enumeration is unavailable.
        return {
            "hwnd": 0,
            "application": "unknown",
            "pid": 0,
            "window_title": "",
            "is_foreground": True,
        }

    @staticmethod
    def _normalize_window(raw: Mapping[str, Any], z_order: int, fallback_foreground: bool = False) -> dict[str, Any]:
        """把原生目录或兼容快照规范化为统一窗口事实结构。"""
        hwnd = int(raw.get("hwnd") or 0)
        pid = raw.get("pid") or raw.get("active_pid")
        window_id = raw.get("window_id") or (f"win:{hwnd:x}" if hwnd else f"legacy:{pid or 0}:{z_order}")
        bounds = raw.get("bounds") or {}
        return {"window_id": window_id, "application": raw.get("application") or raw.get("active_process") or raw.get("process_name") or "unknown",
            "pid": pid, "window_title": raw.get("window_title") or raw.get("active_title") or "",
            "bounds": {"left": int(bounds.get("left", 0)), "top": int(bounds.get("top", 0)), "width": int(bounds.get("width", 0)), "height": int(bounds.get("height", 0))},
            "z_order": int(raw.get("z_order", z_order)), "is_foreground": bool(raw.get("is_foreground", fallback_foreground)),
            "is_minimized": bool(raw.get("is_minimized", False)), "is_maximized": bool(raw.get("is_maximized", False)),
            "is_topmost": bool(raw.get("is_topmost", False)), "display": raw.get("display")}

    @staticmethod
    def _public_window(window: Mapping[str, Any]) -> dict[str, Any]:
        """原始标题不进入统一消息；标题是否存在是足够的窗口元数据。"""
        item = dict(window)
        title = item.pop("window_title", "")
        item["has_title"] = bool(title)
        return item
