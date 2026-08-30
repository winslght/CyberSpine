"""
CyberSpine 真实物理自主神经起搏器 (Real Autonomous Pacemaker Daemon)
100% 真实物理硬件执行：独立后台常驻线程、精确 5.0s 物理感官采样、真实前台驻留计时与 60s 小脑简报聚合。
"""
import os
import time
import threading
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.models.somatic_signals import utc_now
from src.perceptors.somatic_hub import SomaticPerceptorHub
from src.pacing.neural_buffer import TemporalNeuralBuffer
from src.app.telemetry_logger import CognitiveTelemetryLogger, TelemetryCategory
from src.models.local_engine import LocalModelEngine


class HeartbeatTickRecord:
    """单次真实物理心跳记录帧"""
    def __init__(
        self,
        heartbeat_index: int,
        timestamp: str,
        active_process: str,
        dwell_seconds: float,
        cpu_percent: float,
        memory_percent: float,
        network_latency_ms: float,
        signals_caught: int,
        is_steady: bool,
        message: str
    ):
        self.heartbeat_index = heartbeat_index
        self.timestamp = timestamp
        self.active_process = active_process
        self.dwell_seconds = dwell_seconds
        self.cpu_percent = cpu_percent
        self.memory_percent = memory_percent
        self.network_latency_ms = network_latency_ms
        self.signals_caught = signals_caught
        self.is_steady = is_steady
        self.message = message

    def to_log_line(self) -> str:
        return f"[{self.timestamp}] [HEARTBEAT #{self.heartbeat_index:04d}] 🫀 5.0s物理心跳: 前台[{self.active_process} (驻留 {self.dwell_seconds:.1f}s)] | CPU {self.cpu_percent:.1f}% | 内存 {self.memory_percent:.1f}% | 网延 {self.network_latency_ms:.1f}ms | 捕获电信号: {self.signals_caught} | {self.message}"


class RealAutonomousPacemaker:
    """真实自主起搏守护器 (后台独立线程常驻)"""

    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls, interval_seconds: float = 5.0, hub: Optional[SomaticPerceptorHub] = None):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(RealAutonomousPacemaker, cls).__new__(cls)
                cls._instance._init_pacemaker(interval_seconds, hub=hub)
            elif hub is not None:
                cls._instance.hub = hub
            return cls._instance

    def _init_pacemaker(self, interval_seconds: float, hub: Optional[SomaticPerceptorHub] = None):
        self.interval_seconds = interval_seconds
        self.hub = hub if hub is not None else SomaticPerceptorHub()
        self.buffer = TemporalNeuralBuffer(alignment_window_seconds=1.0)
        self.telemetry = CognitiveTelemetryLogger()
        self.local_model = LocalModelEngine()

        self._heartbeat_count = 0
        self._is_running = False
        self._thread: Optional[threading.Thread] = None

        # 前台焦点驻留追踪器
        self._last_active_process = "Desktop"
        self._process_dwell_seconds = 0.0

        # 最近心跳历史环形记录
        self._recent_ticks: List[HeartbeatTickRecord] = []
        self._ticks_lock = threading.Lock()

        # 最新 1 分钟世界简报结构化数据
        self._latest_briefing_data = {
            "timestamp": utc_now().strftime("%H:%M:%S"),
            "summary": "起搏器正在收集微观数据以生成首份 1 分钟世界状态简报...",
            "macro_intent": "推测用户正在桌面环境中工作与系统构建。",
            "inhibition_status": "正常感知模式 (0% 负载稳态)",
            "source": "Initializing",
            "model": "Qwen2.5 / Heuristic",
        }
        self._latest_60s_briefing = self._latest_briefing_data["summary"]
        self._cognitive_lock = threading.Lock()
        self._is_inferring = False

        # 物理日志文件 (位于仓库根目录 runtime/logs/)
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.ticks_log_file = base_dir / "runtime" / "logs" / "heartbeat_ticks.log"
        self.ticks_log_file.parent.mkdir(parents=True, exist_ok=True)

        # 启动后台守护线程
        self.start()

    def start(self):
        """启动自主起搏后台线程"""
        if self._is_running:
            return
        self._is_running = True
        self._thread = threading.Thread(target=self._pacemaker_loop, name="CyberSpine-Pacemaker-Daemon", daemon=True)
        self._thread.start()

        # 记录启动日志（使用 UTF-8 安全输出到 stderr，绝不污染 stdout 通信流）
        init_msg = f"CyberSpine 真实自主生命起搏器已于后台物理启动 (精确周期: {self.interval_seconds}s)"
        try:
            import sys
            if hasattr(sys.stderr, "buffer"):
                sys.stderr.buffer.write(f"[Pacemaker Daemon] {init_msg}\n".encode("utf-8"))
                sys.stderr.buffer.flush()
        except Exception:
            pass
        self._append_to_file(f"[{utc_now().strftime('%Y-%m-%d %H:%M:%S')}] [DAEMON_START] {init_msg}")

    def stop(self):
        """停止自主起搏器"""
        self._is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        try:
            import sys
            if hasattr(sys.stderr, "buffer"):
                sys.stderr.buffer.write(b"[Pacemaker Daemon] Stopped.\n")
                sys.stderr.buffer.flush()
        except Exception:
            pass

    def _pacemaker_loop(self):
        """物理起搏主循环 (每 5.0 秒精准执行一次)"""
        while self._is_running:
            start_time = time.monotonic()
            try:
                self._execute_single_physical_heartbeat()
            except Exception as e:
                print(f"[Pacemaker Error] 物理心跳执行异常: {e}")

            # 精确时间对齐休眠
            elapsed = time.monotonic() - start_time
            sleep_time = max(0.1, self.interval_seconds - elapsed)
            time.sleep(sleep_time)

    def _execute_single_physical_heartbeat(self):
        """执行单次 100% 真实物理心跳硬件采样与门控确认"""
        self._heartbeat_count += 1
        now_str = utc_now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. 真实物理感官采样
        t_start = time.perf_counter()
        signals = self.hub.poll_all_signals()
        topo = self.hub.get_full_somatic_topology()
        sample_latency_ms = round((time.perf_counter() - t_start) * 1000, 2)

        # 提取真实物理参数
        channels = topo.get("channels", {})
        focus_info = channels.get("nerve.system.foreground_focus", {})
        current_proc = focus_info.get("active_process", "Desktop") or "Desktop"
        stress_info = channels.get("nerve.system.high_load", {})
        cpu_pct = stress_info.get("cpu_percent", 0.0)
        mem_pct = stress_info.get("memory_percent", 0.0)
        net_info = channels.get("nerve.network.health", {}).get("health", {})
        net_latency = net_info.get("latency_ms", 0.0)

        # 2. 真实计算前台心流驻留时间
        focus_changed = current_proc.lower() != self._last_active_process.lower()
        if not focus_changed:
            self._process_dwell_seconds += self.interval_seconds
        else:
            self._last_active_process = current_proc
            self._process_dwell_seconds = self.interval_seconds

        # 3. 脊髓感觉门控比对 (判断是否为稳态)
        is_steady = len(signals) == 0 and not stress_info.get("is_stressed", False)
        status_msg = "稳态心流观察中 (0% 能耗)" if is_steady else f"捕获到 {len(signals)} 个物理电信号突变"

        # 4. 生成真实心跳记录
        record = HeartbeatTickRecord(
            heartbeat_index=self._heartbeat_count,
            timestamp=now_str,
            active_process=current_proc,
            dwell_seconds=self._process_dwell_seconds,
            cpu_percent=cpu_pct,
            memory_percent=mem_pct,
            network_latency_ms=net_latency,
            signals_caught=len(signals),
            is_steady=is_steady,
            message=status_msg
        )

        with self._ticks_lock:
            self._recent_ticks.append(record)
            if len(self._recent_ticks) > 100:
                self._recent_ticks.pop(0)

        # 5. 真实追加写入本地物理日志文件
        log_line = record.to_log_line()
        self._append_to_file(log_line)

        # 6. 同时注入认知透视终端流 (身体物理心跳)
        self.telemetry.record(
            category=TelemetryCategory.SOMATIC,
            title=f"物理心跳 #{self._heartbeat_count:04d}",
            message=f"前台: [{current_proc}] (驻留 {self._process_dwell_seconds:.1f}s) | CPU {cpu_pct:.1f}% | 内存 {mem_pct:.1f}% | 网延 {net_latency:.1f}ms | 状态: {status_msg}",
            details={"heartbeat_index": self._heartbeat_count, "dwell_seconds": self._process_dwell_seconds},
            latency_ms=sample_latency_ms
        )

        # 7. AI 神经中枢自主认知调度 (首跳、每12跳/60秒、或重大突变事件)
        should_infer_briefing = (self._heartbeat_count == 1 or self._heartbeat_count % 12 == 0)
        should_infer_event = focus_changed or (len(signals) > 0 and not self._is_inferring)

        if should_infer_briefing:
            # 即时同步生成基线宏观简报，保障 0 延迟契约与测试同步
            fast_brief = self.local_model._heuristic_briefing(self._recent_ticks, topo)
            fast_brief["timestamp"] = utc_now().strftime("%H:%M:%S")
            self._latest_briefing_data = fast_brief
            self._latest_60s_briefing = fast_brief.get("summary", "")

        if should_infer_briefing or should_infer_event:
            self._trigger_async_cognitive_cycle(topo, is_60s_briefing=should_infer_briefing)


    def _trigger_async_cognitive_cycle(self, topo: Dict[str, Any], is_60s_briefing: bool = False):
        """非阻塞后台线程触发 AI 神经中枢认知推理，绝不拖慢 5.0s 物理心跳"""
        if self._is_inferring:
            return

        def _worker():
            with self._cognitive_lock:
                self._is_inferring = True
                try:
                    now_str = utc_now().strftime("%H:%M:%S")
                    
                    # 1. 脊髓中枢多感官时空对齐与感觉确认
                    pkt_id = f"pkt_align_{int(time.time() * 1000)}"
                    self.telemetry.record(
                        category=TelemetryCategory.SPINAL,
                        title="脊髓感觉确认与时空对齐",
                        message=f"时空电脉冲已对齐 (ID: {pkt_id})。当前状态：前台焦点 [{self._last_active_process}]，正在激活端侧小模型认知通道...",
                        details={"packet_id": pkt_id, "proc": self._last_active_process}
                    )

                    # 2. 真实调用本地大模型 (Ollama Qwen2.5) 生成 1 分钟宏观世界简报与意图假设
                    with self._ticks_lock:
                        ticks_copy = list(self._recent_ticks)

                    t_start_model = time.perf_counter()
                    briefing = self.local_model.generate_cerebellar_briefing(ticks_copy, topo)
                    
                    # 3. 大模型推演控制动作帧
                    action = self.local_model.infer_action_from_somatic_state(topo.get("channels", {}))
                    model_latency_ms = round((time.perf_counter() - t_start_model) * 1000, 2)

                    briefing["timestamp"] = now_str
                    self._latest_briefing_data = briefing
                    self._latest_60s_briefing = briefing.get("summary", "")

                    # 4. 记录日志与透视
                    brief_log = f"[{utc_now().strftime('%Y-%m-%d %H:%M:%S')}] [AI_NEURAL_BRIEFING] 🧠 {briefing['summary']} | 意图: {briefing.get('macro_intent', '')}"
                    self._append_to_file(brief_log)

                    self.telemetry.record(
                        category=TelemetryCategory.MODEL,
                        title=f"AI神经中枢认知推演完成 ({briefing.get('model', 'Qwen2.5')})",
                        message=f"【意图假设】{briefing.get('macro_intent', '')} | 【推演动作】{action.action_name} ({action.reason})",
                        details={"briefing": briefing, "action": action.model_dump(mode='json'), "latency_ms": model_latency_ms},
                        latency_ms=model_latency_ms
                    )

                except Exception as e:
                    print(f"[Pacemaker AI Cognitive Error] {e}")
                finally:
                    self._is_inferring = False

        threading.Thread(target=_worker, name="CyberSpine-AI-Cognitive-Worker", daemon=True).start()

    def _append_to_file(self, line: str):
        """向物理磁盘日志追加一行"""
        try:
            with open(self.ticks_log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def get_live_pacemaker_status(self) -> Dict[str, Any]:
        """获取当前起搏器物理实机运行状态快照"""
        with self._ticks_lock:
            recent_list = [
                {
                    "heartbeat_index": r.heartbeat_index,
                    "timestamp": r.timestamp,
                    "active_process": r.active_process,
                    "dwell_seconds": r.dwell_seconds,
                    "cpu_percent": r.cpu_percent,
                    "memory_percent": r.memory_percent,
                    "network_latency_ms": r.network_latency_ms,
                    "message": r.message,
                }
                for r in self._recent_ticks[-15:]
            ]

        return {
            "is_running": self._is_running,
            "interval_seconds": self.interval_seconds,
            "total_heartbeats": self._heartbeat_count,
            "current_process": self._last_active_process,
            "current_dwell_seconds": self._process_dwell_seconds,
            "latest_60s_briefing": self._latest_60s_briefing,
            "latest_briefing_data": self._latest_briefing_data,
            "recent_ticks": recent_list,
            "log_file_path": str(self.ticks_log_file),
        }
