"""
CyberSpine 神经末梢 4: 系统稳态与能耗感知探针 (System Homeostasis Perceptor)
监控电池电量、电源插拔、系统运行时钟 (Uptime) 与系统内环境稳态 (Homeostasis)。
"""
import time
import psutil
from typing import Dict, Any, List, Optional

from src.models.somatic_signals import RawSomaticSignal, utc_now
from src.perceptors.base import BasePerceptor


class SystemHomeostasisPerceptor(BasePerceptor):
    """系统内环境稳态与能耗感知器"""

    def __init__(self, low_battery_threshold: int = 20):
        super().__init__(perceptor_id="nerve.system.homeostasis", channel="HOMEOSTASIS")
        self.low_battery_threshold = low_battery_threshold
        self._last_plugged: Optional[bool] = None
        self._last_battery_percent: Optional[int] = None
        self._boot_timestamp = psutil.boot_time()
        self.refresh_baseline()

    def refresh_baseline(self) -> None:
        """初始化电池与电源基线"""
        battery = self._get_battery_info()
        if battery:
            self._last_plugged = battery["is_plugged"]
            self._last_battery_percent = battery["percent"]

    def _get_battery_info(self) -> Optional[Dict[str, Any]]:
        """获取当前电池与供电状态"""
        try:
            bat = psutil.sensors_battery()
            if bat is None:
                return None
            return {
                "percent": int(bat.percent),
                "is_plugged": bool(bat.power_plugged),
                "secs_left": bat.secsleft if bat.secsleft != psutil.POWER_TIME_UNLIMITED else -1,
            }
        except Exception:
            return None

    def poll_signals(self) -> List[RawSomaticSignal]:
        """轮询电源状态切换与低电量警告"""
        start_time = time.perf_counter()
        signals: List[RawSomaticSignal] = []

        now = utc_now()
        bat = self._get_battery_info()

        if bat is not None:
            is_plugged = bat["is_plugged"]
            percent = bat["percent"]

            # 1. 检测电源插拔变化
            if self._last_plugged is not None and self._last_plugged != is_plugged:
                sig_id = f"sig_power_switch_{int(now.timestamp() * 1000)}"
                event_type = "POWER_PLUGGED" if is_plugged else "POWER_UNPLUGGED"
                signals.append(RawSomaticSignal(
                    signal_id=sig_id,
                    timestamp=now,
                    channel=self.channel,
                    event_type=event_type,
                    source_probe=self.perceptor_id,
                    raw_metrics=bat,
                ))

            # 2. 检测低电量预警 (低于阈值且未接电源)
            if not is_plugged and percent <= self.low_battery_threshold:
                if self._last_battery_percent is None or self._last_battery_percent > self.low_battery_threshold:
                    sig_id = f"sig_battery_critical_{int(now.timestamp() * 1000)}"
                    signals.append(RawSomaticSignal(
                        signal_id=sig_id,
                        timestamp=now,
                        channel=self.channel,
                        event_type="BATTERY_CRITICAL",
                        source_probe=self.perceptor_id,
                        raw_metrics=bat,
                    ))

            self._last_plugged = is_plugged
            self._last_battery_percent = percent

        duration_ms = (time.perf_counter() - start_time) * 1000
        self.record_poll_metric(duration_ms)
        return signals

    def get_baseline(self) -> Dict[str, Any]:
        """获取当前系统稳态基线"""
        uptime_seconds = int(time.time() - self._boot_timestamp)
        return {
            "perceptor_id": self.perceptor_id,
            "uptime_seconds": uptime_seconds,
            "uptime_hours": round(uptime_seconds / 3600, 1),
            "battery_info": self._get_battery_info() or {"status": "AC_DESKTOP_NO_BATTERY"},
        }
