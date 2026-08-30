"""
CyberSpine 神经末梢 6: 系统稳定性与应用崩溃感知探针 (System Stability & Crash Perceptor)
感知 Windows 应用程序异常闪退、WER 错误报告 (Event ID 1000/1001) 与静默段错误，为前额叶提供排错线索。
"""
import time
from typing import Dict, Any, List, Optional

from src.models.somatic_signals import RawSomaticSignal, utc_now
from src.perceptors.base import BasePerceptor


class SystemStabilityPerceptor(BasePerceptor):
    """系统稳定性与异常崩溃感知器"""

    def __init__(self):
        super().__init__(perceptor_id="nerve.system.stability", channel="STABILITY")
        self._crash_history: List[Dict[str, Any]] = []
        self._last_processed_crash_id: Optional[str] = None

    def mock_trigger_crash_event(
        self,
        process_name: str = "python.exe",
        fault_module: str = "ntdll.dll",
        exception_code: str = "0xc0000005",
    ) -> Dict[str, Any]:
        """[用于自测与演练] 模拟应用程序闪退或段错误事件"""
        crash_event = {
            "crash_id": f"crash_{int(time.time() * 1000)}_{process_name}",
            "process_name": process_name,
            "fault_module": fault_module,
            "exception_code": exception_code,
            "timestamp": utc_now().isoformat(),
        }
        self._crash_history.append(crash_event)
        return crash_event

    def poll_signals(self) -> List[RawSomaticSignal]:
        """轮询系统崩溃与异常事件"""
        start_time = time.perf_counter()
        signals: List[RawSomaticSignal] = []

        now = utc_now()

        # 检查是否有新崩溃记录
        if self._crash_history:
            latest = self._crash_history[-1]
            if latest["crash_id"] != self._last_processed_crash_id:
                self._last_processed_crash_id = latest["crash_id"]
                sig_id = f"sig_crash_{int(now.timestamp() * 1000)}"

                signals.append(RawSomaticSignal(
                    signal_id=sig_id,
                    timestamp=now,
                    channel=self.channel,
                    event_type="PROCESS_CRASH_DETECTED",
                    source_probe=self.perceptor_id,
                    raw_metrics=latest,
                ))

        duration_ms = (time.perf_counter() - start_time) * 1000
        self.record_poll_metric(duration_ms)
        return signals

    def get_baseline(self) -> Dict[str, Any]:
        """获取当前稳定性基线"""
        return {
            "perceptor_id": self.perceptor_id,
            "total_crashes_tracked": len(self._crash_history),
            "recent_crashes": self._crash_history[-5:],
        }
