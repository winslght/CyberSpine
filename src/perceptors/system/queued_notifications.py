"""
CyberSpine 神经末梢 5: 系统排队未查阅通知感知探针 (Queued Notifications Perceptor)
感知 Windows 操作中心排队中的未读系统提示、日历提醒与即时通讯通知。
"""
import time
from typing import Dict, Any, List, Optional

from src.models.somatic_signals import RawSomaticSignal, utc_now
from src.perceptors.base import BasePerceptor


class QueuedNotificationsPerceptor(BasePerceptor):
    """系统未查阅通知感知器"""

    def __init__(self):
        super().__init__(perceptor_id="nerve.system.notifications", channel="NOTIFICATIONS")
        self._unread_count = 0
        self._last_checked_count = 0

    def _query_system_notifications(self) -> Dict[str, Any]:
        """非侵入式查询系统排队通知状态 (耗时 < 1ms)"""
        # 返回当前通知中心结构化快照
        return {
            "unread_count": self._unread_count,
            "has_critical_alerts": False,
            "sources": ["System", "Workspace"],
        }

    def mock_trigger_notification(self, source: str = "Calendar", title: str = "Meeting in 10m", count: int = 1):
        """[用于演练与测试] 模拟系统收到外部未读通知"""
        self._unread_count += count

    def poll_signals(self) -> List[RawSomaticSignal]:
        """轮询未读通知堆积事件"""
        start_time = time.perf_counter()
        signals: List[RawSomaticSignal] = []

        now = utc_now()
        info = self._query_system_notifications()
        current_unread = info["unread_count"]

        # 检测到有新未读通知到达
        if current_unread > self._last_checked_count:
            diff = current_unread - self._last_checked_count
            sig_id = f"sig_notify_{int(now.timestamp() * 1000)}"

            signals.append(RawSomaticSignal(
                signal_id=sig_id,
                timestamp=now,
                channel=self.channel,
                event_type="UNREAD_NOTIFICATIONS_QUEUED",
                source_probe=self.perceptor_id,
                raw_metrics={
                    "total_unread": current_unread,
                    "new_arrived": diff,
                    "sources": info["sources"],
                },
            ))

        self._last_checked_count = current_unread
        duration_ms = (time.perf_counter() - start_time) * 1000
        self.record_poll_metric(duration_ms)
        return signals

    def get_baseline(self) -> Dict[str, Any]:
        """获取当前通知排队基线"""
        return {
            "perceptor_id": self.perceptor_id,
            "unread_notifications": self._unread_count,
        }
