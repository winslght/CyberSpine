"""
CyberSpine 神经末梢统一基类与接口契约 (Base Somatic Perceptor)
所有感官探针统一继承此基类，遵守只读非侵入式探测与 0% 空闲能耗铁律。
"""
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from src.models.somatic_signals import RawSomaticSignal, utc_now


class BasePerceptor(ABC):
    """神经末梢抽象基类"""

    def __init__(self, perceptor_id: str, channel: str):
        self.perceptor_id = perceptor_id
        self.channel = channel
        self.enabled: bool = True
        self._last_poll_time = utc_now()
        self._total_polls = 0
        self._total_duration_ms = 0.0

    def set_enabled(self, enabled: bool) -> None:
        """
        动态设置探针启用/停用状态 (热插拔控制)
        :param enabled: True 启用 / False 停用
        """
        self.enabled = bool(enabled)
        if self.enabled:
            # 重新启用时刷新基线时间，防止虚假增量抖动
            self._last_poll_time = utc_now()

    @abstractmethod
    def poll_signals(self) -> List[RawSomaticSignal]:
        """
        执行非阻塞浅层快速采样 (单次执行耗时严格 <= 5ms)
        :return: 触发的新神经电信号列表
        """
        pass

    @abstractmethod
    def get_baseline(self) -> Dict[str, Any]:
        """
        获取当前感官基线拓扑快照
        """
        pass

    def record_poll_metric(self, duration_ms: float):
        """记录单次探测耗时性能指标"""
        self._total_polls += 1
        self._total_duration_ms += duration_ms
        self._last_poll_time = utc_now()

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取探针运行性能统计"""
        avg_ms = (
            round(self._total_duration_ms / self._total_polls, 3)
            if self._total_polls > 0
            else 0.0
        )
        return {
            "perceptor_id": self.perceptor_id,
            "channel": self.channel,
            "enabled": self.enabled,
            "total_polls": self._total_polls,
            "avg_duration_ms": avg_ms,
            "last_poll_time": self._last_poll_time.isoformat(),
        }
