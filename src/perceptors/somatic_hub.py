"""
CyberSpine 全身感官总控调度中心 (Somatic Perceptor Hub)
统一挂载管理全套 7 大宏观神经末梢 + IO 存储探针，负责全身电信号汇聚、实机基准性能统计与结构化开发留痕。
"""
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.models.somatic_signals import RawSomaticSignal, utc_now
from src.pacing.neural_buffer import TemporalNeuralBuffer
from src.perceptors.base import BasePerceptor
from src.perceptors.io.io_manager import IOPerceptorManager
from src.perceptors.system.foreground_focus import ForegroundFocusPerceptor
from src.perceptors.system.running_apps import RunningAppsPerceptor
from src.perceptors.system.high_load import HighLoadStressPerceptor
from src.perceptors.system.system_homeostasis import SystemHomeostasisPerceptor
from src.perceptors.system.queued_notifications import QueuedNotificationsPerceptor
from src.perceptors.system.system_stability import SystemStabilityPerceptor
from src.perceptors.network.network_health import NetworkHealthPerceptor
from src.perceptors.hardware.aida64_perceptor import Aida64HardwarePerceptor
from src.perceptors.system.input_kinetics import InputKineticsPerceptor
from src.perceptors.system.clipboard_semantics import ClipboardSemanticsPerceptor


class SomaticPerceptorHub:
    """全身神经末梢总控调度器"""

    def __init__(self, log_dir: Optional[str] = None):
        # 初始化 10 大核心系统与硬件神经末梢
        self.focus_perceptor = ForegroundFocusPerceptor()
        self.apps_perceptor = RunningAppsPerceptor()
        self.stress_perceptor = HighLoadStressPerceptor()
        self.homeostasis_perceptor = SystemHomeostasisPerceptor()
        self.notifications_perceptor = QueuedNotificationsPerceptor()
        self.stability_perceptor = SystemStabilityPerceptor()
        self.network_perceptor = NetworkHealthPerceptor()
        self.hardware_perceptor = Aida64HardwarePerceptor()
        self.kinetics_perceptor = InputKineticsPerceptor()
        self.clipboard_perceptor = ClipboardSemanticsPerceptor()

        # 初始化 IO 外设探针
        self.io_manager = IOPerceptorManager()

        self.all_perceptors: List[BasePerceptor] = [
            self.focus_perceptor,
            self.apps_perceptor,
            self.stress_perceptor,
            self.homeostasis_perceptor,
            self.notifications_perceptor,
            self.stability_perceptor,
            self.network_perceptor,
            self.hardware_perceptor,
            self.kinetics_perceptor,
            self.clipboard_perceptor,
        ]

        # 确定日志持久化路径 (runtime/logs/)
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            workspace_root = Path(__file__).resolve().parent.parent.parent
            self.log_dir = workspace_root / "runtime" / "logs"

        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.trace_log_file = self.log_dir / "perceptors_trace.jsonl"
        self.benchmark_log_file = self.log_dir / "hardware_benchmarks.log"

    def set_perceptor_enabled(self, perceptor_id: str, enabled: bool) -> bool:
        """
        动态设置指定神经探针的启用/停用状态 (热插拔控制)
        :param perceptor_id: 探针唯一标识 (如 'nerve.system.foreground_focus' 或 'nerve.io.storage')
        :param enabled: True 启用 / False 停用
        :return: 是否找到并成功设置
        """
        for perceptor in self.all_perceptors:
            if perceptor.perceptor_id == perceptor_id:
                perceptor.set_enabled(enabled)
                return True

        if perceptor_id in ("nerve.io.storage", getattr(self.io_manager, "perceptor_id", None)):
            if hasattr(self.io_manager, "set_enabled"):
                self.io_manager.set_enabled(enabled)
            else:
                self.io_manager.enabled = bool(enabled)
            return True

        return False

    def get_perceptor_enabled(self, perceptor_id: str) -> Optional[bool]:
        """获取指定探针当前的启用状态"""
        for perceptor in self.all_perceptors:
            if perceptor.perceptor_id == perceptor_id:
                return perceptor.enabled
        if perceptor_id in ("nerve.io.storage", getattr(self.io_manager, "perceptor_id", None)):
            return getattr(self.io_manager, "enabled", True)
        return None

    def poll_all_signals(self) -> List[RawSomaticSignal]:
        """
        统一轮询全身所有感官探针产生的原始电信号
        注意：自动跳过 enabled=False 的停用探针
        并自动将新电信号落盘记录到 perceptors_trace.jsonl 进行开发留痕
        """
        all_signals: List[RawSomaticSignal] = []

        # 1. 轮询所有注册的系统/网络探针 (跳过未启用的探针)
        for perceptor in self.all_perceptors:
            if not getattr(perceptor, "enabled", True):
                continue
            try:
                sigs = perceptor.poll_signals()
                all_signals.extend(sigs)
            except Exception:
                continue

        # 2. 轮询 IO 存储探针 (跳过未启用的探针)
        if getattr(self.io_manager, "enabled", True):
            try:
                io_sigs = self.io_manager.poll_io_signals()
                all_signals.extend(io_sigs)
            except Exception:
                pass

        # 3. 开发留痕落盘 (写入 trace 日志)
        if all_signals:
            self._append_signals_trace(all_signals)

        return all_signals

    def feed_into_buffer(self, buffer: TemporalNeuralBuffer) -> int:
        """
        将当前全身捕获的电信号自动注入到中枢时钟缓冲器中
        :return: 成功入队的信号数量
        """
        signals = self.poll_all_signals()
        ingested_count = 0
        for sig in signals:
            if buffer.ingest_signal(sig):
                ingested_count += 1
        return ingested_count

    def get_full_somatic_topology(self) -> Dict[str, Any]:
        """
        获取全身 8 大通道的当前完整基线拓扑快照
        """
        topology = {
            "snapshot_timestamp": utc_now().isoformat(),
            "channels": {},
            "performance_benchmarks": [],
        }

        # 采集每个感官的基线
        for perceptor in self.all_perceptors:
            topology["channels"][perceptor.perceptor_id] = perceptor.get_baseline()
            topology["performance_benchmarks"].append(perceptor.get_performance_summary())

        # 采集 IO 基线
        topology["channels"]["nerve.io.storage"] = self.io_manager.get_full_io_snapshot()
        topology["total_channels"] = len(topology["channels"])

        return topology

    def record_hardware_benchmark_report(self) -> str:
        """生成并落盘实机性能基准测试报告"""
        topo = self.get_full_somatic_topology()
        lines = [
            f"=======================================================",
            f"CyberSpine 全感官神经末梢实机性能基准报告",
            f"采样时间: {topo['snapshot_timestamp']}",
            f"=======================================================",
        ]

        for p in topo["performance_benchmarks"]:
            lines.append(
                f"探针: {p['perceptor_id']:<35} | 通道: {p['channel']:<15} | "
                f"总采样: {p['total_polls']} 次 | 平均耗时: {p['avg_duration_ms']:.3f} ms"
            )

        report = "\n".join(lines) + "\n"
        try:
            with open(self.benchmark_log_file, "a", encoding="utf-8") as f:
                f.write(report)
        except Exception:
            pass

        return report

    def _append_signals_trace(self, signals: List[RawSomaticSignal]):
        """将信号结构化追加到 trace.jsonl"""
        try:
            with open(self.trace_log_file, "a", encoding="utf-8") as f:
                for sig in signals:
                    f.write(json.dumps(sig.model_dump(), default=str, ensure_ascii=False) + "\n")
        except Exception:
            pass
