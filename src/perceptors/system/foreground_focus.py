"""旧感知主干的窗口焦点兼容适配器。

窗口事实由 ``peripheral.window.activity`` 唯一采集；本模块只把其中的
``window.focus_changed`` 事件映射为旧 ``RawSomaticSignal``，以便旧起搏器
在迁移期保持可用。
"""
import time
from typing import Any, Dict, List, Optional

from src.models.somatic_signals import RawSomaticSignal
from src.perceptors.base import BasePerceptor
from src.sensing.window_activity import WindowActivityPeripheral


class ForegroundFocusPerceptor(BasePerceptor):
    """前台窗口与工作台重心流转感知器"""

    def __init__(self, peripheral: Optional[WindowActivityPeripheral] = None):
        super().__init__(perceptor_id="nerve.system.foreground_focus", channel="WORKSPACE")
        self._peripheral = peripheral or WindowActivityPeripheral()

    def _get_active_window_info(self) -> Dict[str, Any]:
        """从规范窗口插件读取当前前台元数据，不再直接调用 User32。"""
        foreground = self._peripheral.current_state().payload["foreground"] or {}
        window_id = str(foreground.get("window_id", ""))
        try:
            hwnd = int(window_id.removeprefix("win:"), 16) if window_id.startswith("win:") else 0
        except ValueError:
            hwnd = 0
        return {
            "hwnd": hwnd,
            "process_name": foreground.get("application", "unavailable"),
            # The canonical plugin intentionally never exposes a title.
            "window_title": "",
            "pid": foreground.get("pid", 0),
        }

    def poll_signals(self) -> List[RawSomaticSignal]:
        """轮询前台焦点变动"""
        start_time = time.perf_counter()
        signals: List[RawSomaticSignal] = []

        event = self._peripheral.poll_focus_change()
        if event is not None:
            previous = event.payload["previous"]
            current = event.payload["current"]
            signals.append(RawSomaticSignal(
                signal_id=f"sig_focus_{int(event.timestamp.timestamp() * 1000)}",
                timestamp=event.timestamp,
                channel=self.channel,
                event_type="FOCUS_SWITCHED",
                source_probe=self.perceptor_id,
                raw_metrics={
                    "previous_process": previous.get("application", "unknown"),
                    "previous_dwell_seconds": previous.get("focus_dwell_seconds", 0.0),
                    "current_process": current.get("application", "unknown"),
                    "pid": current.get("pid", 0),
                    "source_topic": event.topic,
                },
            ))

        duration_ms = (time.perf_counter() - start_time) * 1000
        self.record_poll_metric(duration_ms)
        return signals

    def get_baseline(self) -> Dict[str, Any]:
        """获取当前工作台焦点基线"""
        info = self._get_active_window_info()
        return {
            "perceptor_id": self.perceptor_id,
            "active_process": info["process_name"],
            "active_title": info["window_title"],
            "active_pid": info["pid"],
        }
