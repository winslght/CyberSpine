"""
CyberSpine 神经末梢 3: 高压力应用与负载尖峰感知探针 (High-Load Stress Perceptor)
毫秒级采样 CPU、内存超负荷事件 (如大型编译、4K 渲染、3A 游戏启动)，识别系统处于高压还是空闲稳态。
"""
import time
import psutil
from typing import Dict, Any, List, Optional

from src.models.somatic_signals import RawSomaticSignal, utc_now
from src.perceptors.base import BasePerceptor


class HighLoadStressPerceptor(BasePerceptor):
    """高压力与负载尖峰感知器"""

    def __init__(self, cpu_threshold: float = 85.0, mem_threshold: float = 90.0):
        super().__init__(perceptor_id="nerve.system.high_load", channel="SYSTEM_STRESS")
        self.cpu_threshold = cpu_threshold
        self.mem_threshold = mem_threshold
        self._is_in_stress = False
        self._stress_start_time = None
        # 初始化 CPU 百分比计算基线 (非阻塞)
        psutil.cpu_percent(interval=None)

    def _get_top_resource_processes(self, limit: int = 3) -> List[Dict[str, Any]]:
        """提取当前占用 CPU/内存最高的前 N 个进程 (耗时 < 2ms)"""
        procs = []
        try:
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    info = p.info
                    if info['cpu_percent'] is not None and info['name']:
                        procs.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass

        # 按 CPU 降序排序
        procs.sort(key=lambda x: x.get('cpu_percent', 0.0) or 0.0, reverse=True)
        return procs[:limit]

    def poll_signals(self) -> List[RawSomaticSignal]:
        """轮询高负载压力事件"""
        start_time = time.perf_counter()
        signals: List[RawSomaticSignal] = []

        now = utc_now()
        cpu_usage = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        mem_usage = mem.percent

        is_stressed_now = cpu_usage >= self.cpu_threshold or mem_usage >= self.mem_threshold

        # 1. 压力突增事件 (进入高压)
        if is_stressed_now and not self._is_in_stress:
            self._is_in_stress = True
            self._stress_start_time = now
            top_procs = self._get_top_resource_processes()
            sig_id = f"sig_stress_spike_{int(now.timestamp() * 1000)}"

            signals.append(RawSomaticSignal(
                signal_id=sig_id,
                timestamp=now,
                channel=self.channel,
                event_type="LOAD_SPIKE_DETECTED",
                source_probe=self.perceptor_id,
                raw_metrics={
                    "cpu_percent": cpu_usage,
                    "memory_percent": mem_usage,
                    "top_processes": top_procs,
                    "stress_cause": "CPU_OVERLOAD" if cpu_usage >= self.cpu_threshold else "MEMORY_OVERLOAD",
                },
            ))

        # 2. 压力释放事件 (恢复平稳)
        elif not is_stressed_now and self._is_in_stress:
            duration_s = round((now - (self._stress_start_time or now)).total_seconds(), 2)
            self._is_in_stress = False
            self._stress_start_time = None
            sig_id = f"sig_stress_release_{int(now.timestamp() * 1000)}"

            signals.append(RawSomaticSignal(
                signal_id=sig_id,
                timestamp=now,
                channel=self.channel,
                event_type="STRESS_RELEASED",
                source_probe=self.perceptor_id,
                raw_metrics={
                    "cpu_percent": cpu_usage,
                    "memory_percent": mem_usage,
                    "stress_duration_seconds": duration_s,
                },
            ))

        duration_ms = (time.perf_counter() - start_time) * 1000
        self.record_poll_metric(duration_ms)
        return signals

    def get_baseline(self) -> Dict[str, Any]:
        """获取当前系统负载基线"""
        mem = psutil.virtual_memory()
        return {
            "perceptor_id": self.perceptor_id,
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_percent": mem.percent,
            "is_stressed": self._is_in_stress,
            "top_processes": self._get_top_resource_processes(3),
        }
