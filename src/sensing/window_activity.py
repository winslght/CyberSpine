"""窗口感知末梢神经：窗口目录、前台驻留、交互强度与时间窗事实整合。"""
from collections import deque
from collections.abc import Callable, Mapping
import time
from typing import Any, Optional

from src.core.neural_message import MessageKind, NeuralMessage, PrivacyClass

from .window_interactions import WindowInteractionTracker, WindowsGlobalInputMonitor
from .window_inventory import WindowsWindowInventory

WindowSnapshotProvider = Callable[[], Mapping[str, Any]]
WindowCatalogProvider = Callable[[], list[Mapping[str, Any]]]
ScreenBoundsProvider = Callable[[], Optional[Mapping[str, Any]]]


class WindowActivityPeripheral:
    """产生窗口层面的事实，不在插件中推断用户的具体工作。"""

    source = "peripheral.window.activity"
    state_topic = "window.current_state"
    catalog_topic = "window.catalog"
    event_topic = "window.focus_changed"
    activity_topic = "window.high_interaction_changed"
    time_window_topic = "window.time_window_summary"
    availability_topic = "window.foreground_availability_changed"
    geometry_topic = "window.geometry_changed"
    _SYSTEM_SURFACE_APPLICATIONS = frozenset({"applicationframehost.exe", "textinputhost.exe"})

    def __init__(self, snapshot_provider: Optional[WindowSnapshotProvider] = None,
                 catalog_provider: Optional[WindowCatalogProvider] = None,
                 interaction_tracker: Optional[WindowInteractionTracker] = None,
                 screen_bounds_provider: Optional[ScreenBoundsProvider] = None,
                 clock: Callable[[], float] = time.monotonic, activity_window_seconds: float = 300,
                 focus_window_seconds: float = 1800, high_frequency_per_minute: float = 12,
                 minimum_interactions: int = 6):
        if activity_window_seconds <= 0 or focus_window_seconds <= 0:
            raise ValueError("activity_window_seconds and focus_window_seconds must be positive")
        self._clock = clock
        self._snapshot_provider = snapshot_provider
        if catalog_provider is not None:
            self._catalog_provider = catalog_provider
            self._screen_bounds_provider = screen_bounds_provider or (lambda: None)
        elif snapshot_provider is not None:
            self._catalog_provider = lambda: []
            self._screen_bounds_provider = screen_bounds_provider or (lambda: None)
        else:
            inventory = WindowsWindowInventory()
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

    def start_input_monitor(self) -> bool:
        """启动键盘/鼠标钩子；不记录任何键值、坐标或窗口内容。"""
        if self._input_monitor is None:
            self._input_monitor = WindowsGlobalInputMonitor(self._record_hwnd_interaction,
                                                             self.record_mouse_button_state)
        return self._input_monitor.start()

    def start(self, input_monitor: bool = False) -> bool:
        """插件生命周期入口；全局输入钩子仅在明确诊断模式中启用。"""
        return self.start_input_monitor() if input_monitor else False

    def stop_input_monitor(self) -> None:
        if self._input_monitor:
            self._input_monitor.stop()
        self._mouse_button_held = False

    def stop(self) -> None:
        """插件生命周期出口：移除输入钩子，不影响其他组件。"""
        self.stop_input_monitor()

    @property
    def input_monitor_running(self) -> bool:
        return bool(self._input_monitor and self._input_monitor.is_running)

    @property
    def input_monitor_error_count(self) -> int:
        return self._input_monitor.callback_error_count if self._input_monitor else 0

    def record_interaction(self, window_id: str, at: Optional[float] = None) -> None:
        self._tracker.record(window_id, at)

    def record_mouse_button_state(self, held: bool) -> None:
        """只保存鼠标按键是否按住，不保存坐标、按键类型或原始输入。"""
        self._mouse_button_held = bool(held)

    def current_state(self) -> NeuralMessage:
        catalog, foreground = self._observed_catalog()
        return self._state_message(foreground, self._decorate_catalog(catalog, foreground))

    def collect_messages(self) -> list[NeuralMessage]:
        """以同一次枚举产生前台、窗口目录和活动变化消息。"""
        self._pending_geometry_changes = []
        catalog, foreground = self._observed_catalog()
        now = self._clock()
        decorated = self._decorate_catalog(catalog, foreground, now)
        messages = [self._state_message(foreground, decorated), self._catalog_message(decorated),
                    self._time_window_message(decorated, now)]
        for event in (self._availability_event(foreground), self._focus_event(foreground),
                      self._activity_event(decorated), self._geometry_event()):
            if event:
                messages.append(event)
        return messages

    def poll_focus_change(self) -> Optional[NeuralMessage]:
        _catalog, foreground = self._observed_catalog()
        return self._focus_event(foreground)

    def _observed_catalog(self) -> tuple[list[dict[str, Any]], Optional[dict[str, Any]]]:
        catalog = [self._normalize_window(raw, index) for index, raw in enumerate(self._catalog_provider())]
        foreground = next((window for window in catalog if window["is_foreground"]), None)
        if foreground is None and self._snapshot_provider is not None:
            foreground = self._legacy_snapshot()
        return catalog, foreground

    def _legacy_snapshot(self) -> dict[str, Any]:
        raw = self._snapshot_provider() if self._snapshot_provider else self._default_snapshot()
        return self._normalize_window(raw, 0, fallback_foreground=True)

    def _decorate_catalog(self, catalog: list[dict[str, Any]], foreground: Optional[dict[str, Any]],
                          now: Optional[float] = None) -> list[dict[str, Any]]:
        now = self._clock() if now is None else now
        if foreground is None:
            self._observe_unattributed(now)
            current_id, focus_dwell = None, 0.0
        else:
            self._close_unattributed(now)
            self._observe_focus(foreground, now)
            current_id = foreground["window_id"]
            focus_dwell = max(0.0, now - (self._foreground_started_at or now))
        screen_bounds = self._screen_bounds()
        decorated = []
        for window in catalog or ([foreground] if foreground is not None else []):
            item = self._public_window(window)
            item["is_foreground"] = item["window_id"] == current_id
            item["presentation"] = self._presentation(item, screen_bounds)
            item["window_state"] = self._window_state(item)
            item["geometry_activity"] = self._observe_geometry(item, now)
            item["focus_dwell_seconds"] = round(focus_dwell, 2) if item["is_foreground"] else 0.0
            item["interaction"] = self._tracker.summary(item["window_id"], self._activity_window_seconds,
                self._high_frequency_per_minute, self._minimum_interactions, now)
            decorated.append(item)
        return decorated

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

    def _observe_geometry(self, window: Mapping[str, Any], now: float) -> dict[str, Any]:
        """依据连续目录快照记录边界变化；拖拽/调整大小只在鼠标按住时作为候选。"""
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
        if self._focus_segments:
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
        cutoff = now - self._focus_window_seconds
        while len(self._focus_segments) > 1 and self._focus_segments[0].get("ended_at") is not None \
                and self._focus_segments[0]["ended_at"] <= cutoff:
            self._focus_segments.popleft()
        while self._unattributed_intervals and self._unattributed_intervals[0].get("ended_at") is not None \
                and self._unattributed_intervals[0]["ended_at"] <= cutoff:
            self._unattributed_intervals.popleft()

    def _state_message(self, foreground: Optional[dict[str, Any]], catalog: list[dict[str, Any]]) -> NeuralMessage:
        current = next((window for window in catalog if window["is_foreground"]), None)
        return NeuralMessage(kind=MessageKind.STATE, source=self.source, topic=self.state_topic,
            payload_schema="window.current_state@3", payload={"foreground": current, "window_count": len(catalog),
            "foreground_status": "available" if foreground is not None else "unavailable",
            "interaction_observation": "global_input_hook" if self.input_monitor_running else "not_started",
            "input_monitor_callback_errors": self.input_monitor_error_count},
            privacy=PrivacyClass.METADATA_ONLY, ttl_seconds=120, collapse_key=self.state_topic)

    def _catalog_message(self, catalog: list[dict[str, Any]]) -> NeuralMessage:
        screen_present = [item for item in catalog if item["presentation"]["is_screen_present"]]
        user_presented = [item for item in catalog if item["presentation"]["is_user_presented"]]
        return NeuralMessage(kind=MessageKind.STATE, source=self.source, topic=self.catalog_topic,
            payload_schema="window.catalog@1", payload={"windows": catalog, "window_count": len(catalog),
            "screen_present_window_count": len(screen_present),
            "screen_present_user_window_count": len(user_presented),
            "screen_present_user_window_ids": [item["window_id"] for item in user_presented]},
            privacy=PrivacyClass.METADATA_ONLY, ttl_seconds=120, collapse_key=self.catalog_topic)

    def _time_window_message(self, catalog: list[dict[str, Any]], now: float) -> NeuralMessage:
        """输出窗口末梢本地整合出的时间窗事实；不包含意图解释或原始标题。"""
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
        observed_seconds = max(0.0, elapsed_seconds - unattributed_seconds)
        for item in totals.values():
            item["focus_seconds"] = round(item["focus_seconds"], 2)
            item["focus_ratio"] = round(item["focus_seconds"] / observed_seconds, 4) if observed_seconds else 0.0
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
                "foreground_status": "available" if any(item["is_foreground"] for item in catalog) else "unavailable",
            }, privacy=PrivacyClass.METADATA_ONLY, ttl_seconds=120, collapse_key=self.time_window_topic)

    def _availability_event(self, current: Optional[dict[str, Any]]) -> Optional[NeuralMessage]:
        available = current is not None
        previous = self._foreground_available
        self._foreground_available = available
        if previous is None or previous == available:
            return None
        return NeuralMessage(kind=MessageKind.EVENT, source=self.source, topic=self.availability_topic,
            payload_schema="window.foreground_availability_changed@1", payload={
                "previous_status": "available" if previous else "unavailable",
                "current_status": "available" if available else "unavailable",
                "reason": "no_attributable_foreground" if not available else "foreground_recovered",
                "recovered_foreground": self._public_window(current) if available else None},
            privacy=PrivacyClass.METADATA_ONLY, ttl_seconds=300, collapse_key=self.availability_topic)

    def _focus_event(self, current: Optional[dict[str, Any]]) -> Optional[NeuralMessage]:
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
        if not self._pending_geometry_changes:
            return None
        return NeuralMessage(kind=MessageKind.EVENT, source=self.source, topic=self.geometry_topic,
            payload_schema="window.geometry_changed@1", payload={"changes": self._pending_geometry_changes},
            privacy=PrivacyClass.METADATA_ONLY, ttl_seconds=300)

    def _record_hwnd_interaction(self, hwnd: int) -> None:
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
