"""
CyberSpine 组件 2: 中枢时钟缓冲器与时空对齐机 (Temporal Neural Buffer & Pacing Hub)
负责汇聚多神经元参差电信号，在呼吸时间窗口内完成时空对齐与防抖打包。
"""
import time
import uuid
import threading
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from src.models.somatic_signals import (
    RawSomaticSignal,
    FusedSomaticPacket,
    PacingStateEnum,
    utc_now,
)


class TemporalNeuralBuffer:
    """
    中枢时钟缓冲器 (Temporal Neural Buffer)
    - 24 小时保持心跳节律
    - 汇聚各路末梢神经信号，在指定时间窗口内（默认 1.0~2.0s）进行时空对齐（Spatiotemporal Alignment）
    - 消除物理抖动，打包为结构化 FusedSomaticPacket 发送给脊髓神经区
    """

    def __init__(
        self,
        alignment_window_seconds: float = 1.0,
        max_buffer_size: int = 1000,
    ):
        self.alignment_window_seconds = alignment_window_seconds
        self.max_buffer_size = max_buffer_size
        self._lock = threading.Lock()
        self._signal_queue: List[RawSomaticSignal] = []
        self._window_start_time: Optional[datetime] = None
        self._is_inhibited: bool = False
        self._inhibition_until: Optional[datetime] = None
        self._device_inhibitions: Dict[str, datetime] = {}

    def ingest_signal(self, signal: RawSomaticSignal) -> bool:
        """
        接收末梢神经传入的原始电信号
        :param signal: 原始感官信号
        :return: 是否成功入队
        """
        with self._lock:
            now = utc_now()

            # 1. 检查设备定向抑制 (Device-Scoped Inhibition)
            if signal.device_fingerprint:
                dev_id = signal.device_fingerprint.device_id
                if dev_id in self._device_inhibitions:
                    if now < self._device_inhibitions[dev_id]:
                        # 该特定设备处于抑制冷却中，静默丢弃
                        return False
                    else:
                        del self._device_inhibitions[dev_id]

            # 2. 检查全局下行抑制 (Global Inhibition)
            if self._is_inhibited and self._inhibition_until:
                if now < self._inhibition_until:
                    return False
                else:
                    self._is_inhibited = False
                    self._inhibition_until = None

            # 队列长度保护
            if len(self._signal_queue) >= self.max_buffer_size:
                self._signal_queue.pop(0)

            if not self._signal_queue:
                self._window_start_time = signal.timestamp

            self._signal_queue.append(signal)
            return True

    def apply_inhibition(self, duration_seconds: int, device_id: Optional[str] = None):
        """
        应用来自前额叶大脑的下行抑制递质
        :param duration_seconds: 抑制时长 (秒)
        :param device_id: 若指定则仅对该特定设备进行定向抑制，允许其他新外设正常接入
        """
        with self._lock:
            if device_id:
                self._device_inhibitions[device_id] = utc_now() + timedelta(seconds=duration_seconds)
            else:
                self._is_inhibited = True
                self._inhibition_until = utc_now() + timedelta(seconds=duration_seconds)
            self._signal_queue.clear()
            self._window_start_time = None

    def is_inhibited(self, device_id: Optional[str] = None) -> bool:
        """
        查询当前中枢或特定设备是否处于抑制冷却状态
        :param device_id: 可选指定设备 ID
        """
        with self._lock:
            now = utc_now()
            if device_id:
                if device_id in self._device_inhibitions:
                    return now < self._device_inhibitions[device_id]
                return False
            # 全局抑制或存在任意设备抑制
            if self._is_inhibited and self._inhibition_until and now < self._inhibition_until:
                return True
            if any(now < until for until in self._device_inhibitions.values()):
                return True
            return False

    def is_window_ready(self, current_time: Optional[datetime] = None) -> bool:
        """判断当前对齐窗口是否已收集完毕并可以打包"""
        with self._lock:
            if not self._signal_queue or not self._window_start_time:
                return False
            now = current_time or utc_now()
            elapsed = (now - self._window_start_time).total_seconds()
            return elapsed >= self.alignment_window_seconds

    def flush_aligned_packet(self, force: bool = False) -> Optional[FusedSomaticPacket]:
        """
        将当前窗口内积累的所有参差电信号融合打包为一个 FusedSomaticPacket
        :param force: 是否强制立即清空并打包（无需等待时间窗口自然到期）
        """
        with self._lock:
            if not self._signal_queue:
                return None

            now = utc_now()
            if not force and self._window_start_time:
                elapsed = (now - self._window_start_time).total_seconds()
                if elapsed < self.alignment_window_seconds:
                    return None

            signals_to_fuse = list(self._signal_queue)
            self._signal_queue.clear()
            window_start = self._window_start_time or now
            self._window_start_time = None

            # 确定主导事件与拓扑摘要
            primary_signal = signals_to_fuse[0]
            primary_event = f"{primary_signal.channel}_{primary_signal.event_type}"

            somatic_summary: Dict[str, Any] = {
                "signal_count": len(signals_to_fuse),
                "channels": list({s.channel for s in signals_to_fuse}),
                "devices_involved": [
                    s.device_fingerprint.device_id
                    for s in signals_to_fuse
                    if s.device_fingerprint
                ],
                "structure_profiles": [
                    profile
                    for s in signals_to_fuse
                    if s.structure_summary
                    for profile in s.structure_summary.detected_profiles
                ],
            }

            packet = FusedSomaticPacket(
                packet_id=f"fused_pkt_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
                window_start=window_start,
                window_end=now,
                signals=signals_to_fuse,
                primary_event=primary_event,
                pacing_state=PacingStateEnum.MICRO_PAUSE,
                somatic_summary=somatic_summary,
            )
            return packet

    def clear(self):
        """清空缓冲区"""
        with self._lock:
            self._signal_queue.clear()
            self._window_start_time = None
