"""
CyberSpine 神经末梢: 皮肤动量与输入节奏感知探针 (Input Kinetics & Flow Cadence Perceptor)
毫秒级检测键盘/鼠标物理动量与空闲停顿时间差，精准推断用户此刻是处于“高速编码心流”、“沉思停顿”还是“离开工位”。
【隐私铁律】：绝对不记录任何击键具体内容与字符，仅统计物理输入时间差与动量强度。
"""
import time
import sys
import ctypes
from typing import Dict, Any, List, Optional
from ctypes import Structure, c_uint, sizeof, byref

from src.models.somatic_signals import RawSomaticSignal, utc_now
from src.perceptors.base import BasePerceptor


class LASTINPUTINFO(Structure):
    _fields_ = [
        ("cbSize", c_uint),
        ("dwTime", c_uint)
    ]


class InputKineticsPerceptor(BasePerceptor):
    """皮肤动量触觉与输入心流节奏感知器"""

    PERCEPTOR_ID = "nerve.system.input_kinetics"
    CHANNEL = "INPUT_KINETICS"

    def __init__(self, idle_threshold_sec: float = 60.0):
        super().__init__(perceptor_id=self.PERCEPTOR_ID, channel=self.CHANNEL)
        self.idle_threshold_sec = idle_threshold_sec
        self._last_state = "ACTIVE"
        self._state_start_time = utc_now()
        self._last_tick_count = 0

    def _get_idle_seconds(self) -> float:
        """调用 Windows GetLastInputInfo 获取毫秒级物理输入空闲时间"""
        if sys.platform != "win32":
            return 0.0
        try:
            lii = LASTINPUTINFO()
            lii.cbSize = sizeof(LASTINPUTINFO)
            if ctypes.windll.user32.GetLastInputInfo(byref(lii)):
                millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
                return max(0.0, millis / 1000.0)
        except Exception:
            pass
        return 0.0

    def _classify_flow_state(self, idle_sec: float) -> str:
        """根据空闲秒数判定心流阶段"""
        if idle_sec < 3.0:
            return "BURST_TYPING_OR_INTERACTION"  # 高频连续交互中
        elif idle_sec < 15.0:
            return "STEADY_FLOW"                  # 稳定心流 (短暂停顿阅读)
        elif idle_sec < 60.0:
            return "DEEP_THINKING"                # 深度沉思构思中
        elif idle_sec < 300.0:
            return "IDLE_SHORT"                   # 短暂离开 / 待命
        else:
            return "AWAY_FROM_KEYBOARD"           # 已离开工位

    def get_baseline(self) -> Dict[str, Any]:
        """获取当前输入动量基线快照"""
        idle_sec = self._get_idle_seconds()
        flow_state = self._classify_flow_state(idle_sec)

        return {
            "perceptor_id": self.perceptor_id,
            "idle_seconds": round(idle_sec, 1),
            "flow_state": flow_state,
            "is_user_active": idle_sec < self.idle_threshold_sec,
        }

    def poll_signals(self) -> List[RawSomaticSignal]:
        """轮询用户活跃状态跃迁事件"""
        start_time = time.perf_counter()
        signals: List[RawSomaticSignal] = []

        now = utc_now()
        idle_sec = self._get_idle_seconds()
        current_state = "IDLE" if idle_sec >= self.idle_threshold_sec else "ACTIVE"

        if current_state != self._last_state:
            event_type = "USER_WENT_IDLE" if current_state == "IDLE" else "USER_RESUMED_ACTIVITY"
            self._last_state = current_state
            self._state_start_time = now

            sig = RawSomaticSignal(
                signal_id=f"sig_kinetics_{int(now.timestamp() * 1000)}",
                timestamp=now,
                channel=self.channel,
                event_type=event_type,
                source_probe=self.perceptor_id,
            )
            signals.append(sig)

        self.record_poll_metric((time.perf_counter() - start_time) * 1000)
        return signals
