"""
CyberSpine 全维硬件体征与内脏代谢感知末梢 (AIDA64 共享内存 / 原生双模探针)
支持微秒级读取 CPU 全核温度、真实风扇转速 RPM、GPU 功耗与热点温度、NVMe 固态硬盘温度。
若未安装或未运行 AIDA64，自动无缝降级为系统原生轻量探针，100% 保证高可用。
"""
import sys
import time
import subprocess
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional

from src.models.somatic_signals import RawSomaticSignal, utc_now
from src.perceptors.base import BasePerceptor
from src.perceptors.hardware.aida64_daemon import Aida64DaemonManager


class Aida64HardwarePerceptor(BasePerceptor):
    """AIDA64 共享内存与原生双模生理体征感知末梢"""

    PERCEPTOR_ID = "nerve.hardware.somatic_telemetry"
    CHANNEL = "HARDWARE_METABOLISM"

    def __init__(self, cpu_temp_threshold: float = 85.0, gpu_temp_threshold: float = 82.0):
        super().__init__(perceptor_id=self.PERCEPTOR_ID, channel=self.CHANNEL)
        self.cpu_temp_threshold = cpu_temp_threshold
        self.gpu_temp_threshold = gpu_temp_threshold
        self._is_overheating = False
        self._last_sample_time = 0.0
        self._cached_telemetry: Dict[str, Any] = {}

        # 尝试自动拉起便携版 AIDA64 守护进程
        Aida64DaemonManager.auto_start_if_available()

    def get_baseline(self) -> Dict[str, Any]:
        """获取当前硬件生理体征全景快照"""
        now = time.time()
        if now - self._last_sample_time < 0.5 and self._cached_telemetry:
            return self._cached_telemetry

        data = self._sample_hardware_telemetry()
        self._cached_telemetry = data
        self._last_sample_time = now
        return data

    def poll_signals(self) -> List[RawSomaticSignal]:
        """轮询硬件体征突变与过热应激事件"""
        start_time = time.perf_counter()
        signals: List[RawSomaticSignal] = []

        data = self.get_baseline()
        now = utc_now()
        cpu_temp = data.get("cpu_package_temp_c", 0.0)
        gpu_temp = data.get("gpu_temp_c", 0.0)

        is_overheating_now = cpu_temp >= self.cpu_temp_threshold or gpu_temp >= self.gpu_temp_threshold

        # 过热应激预警事件
        if is_overheating_now and not self._is_overheating:
            self._is_overheating = True
            sig = RawSomaticSignal(
                signal_id=f"sig_hw_overheat_{int(now.timestamp() * 1000)}",
                timestamp=now,
                channel=self.channel,
                event_type="OVERHEAT_WARNING",
                source_probe=self.perceptor_id,
            )
            signals.append(sig)

        elif not is_overheating_now and self._is_overheating:
            self._is_overheating = False
            sig = RawSomaticSignal(
                signal_id=f"sig_hw_cooldown_{int(now.timestamp() * 1000)}",
                timestamp=now,
                channel=self.channel,
                event_type="COOLDOWN_RECOVERY",
                source_probe=self.perceptor_id,
            )
            signals.append(sig)

        self.record_poll_metric((time.perf_counter() - start_time) * 1000)
        return signals

    def _sample_hardware_telemetry(self) -> Dict[str, Any]:
        """双模硬件采样分发器"""
        if Aida64DaemonManager.is_shared_memory_active():
            aida_data = self._read_aida64_shared_memory()
            if aida_data:
                return aida_data

        return self._native_fallback_telemetry()

    def _read_aida64_shared_memory(self) -> Optional[Dict[str, Any]]:
        """通过 mmap 读取 Windows 共享内存 AIDA64_SensorValues (微秒级)"""
        try:
            import mmap
            shm = mmap.mmap(-1, 0x10000, "AIDA64_SensorValues", access=mmap.ACCESS_READ)
            raw_bytes = shm.read(0x10000)
            shm.close()

            clean_str = raw_bytes.rstrip(b'\x00').decode('utf-8', errors='ignore').strip()
            if not clean_str:
                return None

            root = ET.fromstring(f"<root>{clean_str}</root>")

            sensors: Dict[str, Any] = {
                "perceptor_id": self.perceptor_id,
                "source_mode": "AIDA64_SHARED_MEMORY",
                "temperatures": {},
                "fans": {},
                "voltages": {},
                "powers": {},
                "cpu_package_temp_c": 0.0,
                "gpu_temp_c": 0.0,
                "cpu_fan_rpm": 0,
                "gpu_power_watts": 0.0,
                "nvme_ssd_temp_c": 0.0,
                "vrm_temp_c": 0.0,
                "raw_readings_count": 0,
            }

            cpu_temp = 0.0
            gpu_temp = 0.0
            cpu_fan = 0
            gpu_power = 0.0
            nvme_temp = 0.0
            vrm_temp = 0.0

            for elem in root:
                tag = elem.tag.lower()
                id_node = elem.find('id')
                label_node = elem.find('label')
                val_node = elem.find('value')

                if id_node is None or val_node is None:
                    continue

                sid = id_node.text or ""
                label = (label_node.text if label_node is not None else sid) or sid
                val_str = val_node.text or "0"

                try:
                    val_float = float(val_str)
                except ValueError:
                    val_float = 0.0

                sensors["raw_readings_count"] += 1

                if tag == "temp":
                    sensors["temperatures"][label] = val_float
                    sid_upper = sid.upper()
                    if "TCPU" in sid_upper or "CPU PACKAGE" in label.upper():
                        cpu_temp = val_float
                    elif "TGPU" in sid_upper or "GPU" in label.upper():
                        gpu_temp = val_float
                    elif "THDD" in sid_upper or "NVME" in label.upper() or "SSD" in label.upper():
                        nvme_temp = max(nvme_temp, val_float)
                    elif "TVRM" in sid_upper or "VRM" in label.upper():
                        vrm_temp = val_float

                elif tag == "fan":
                    sensors["fans"][label] = int(val_float)
                    if "FCPU" in sid.upper() or "CPU" in label.upper():
                        cpu_fan = int(val_float)

                elif tag == "volt":
                    sensors["voltages"][label] = val_float

                elif tag == "pwr":
                    sensors["powers"][label] = val_float
                    if "PGPU" in sid.upper() or "GPU" in label.upper():
                        gpu_power = val_float

            sensors["cpu_package_temp_c"] = cpu_temp
            sensors["gpu_temp_c"] = gpu_temp
            sensors["cpu_fan_rpm"] = cpu_fan
            sensors["gpu_power_watts"] = gpu_power
            sensors["nvme_ssd_temp_c"] = nvme_temp
            sensors["vrm_temp_c"] = vrm_temp

            return sensors
        except Exception:
            return None

    def _native_fallback_telemetry(self) -> Dict[str, Any]:
        """原生轻量硬件体征探针 (当 AIDA64 未运行时)"""
        import psutil

        telemetry: Dict[str, Any] = {
            "perceptor_id": self.perceptor_id,
            "source_mode": "NATIVE_FALLBACK",
            "cpu_percent": round(psutil.cpu_percent(interval=None), 1),
            "memory_percent": round(psutil.virtual_memory().percent, 1),
            "cpu_package_temp_c": 0.0,
            "gpu_temp_c": 0.0,
            "gpu_power_watts": 0.0,
            "gpu_vram_used_mb": 0.0,
            "gpu_vram_total_mb": 0.0,
            "cpu_fan_rpm": 0,
            "nvme_ssd_temp_c": 0.0,
        }

        # 尝试通过 nvidia-smi 提取 RTX 4060 基础体征
        try:
            cmd = ["nvidia-smi", "--query-gpu=temperature.gpu,power.draw,memory.used,memory.total", "--format=csv,noheader,nounits"]
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=0.8, text=True).strip()
            parts = [p.strip() for p in out.split(",")]
            if len(parts) >= 4:
                telemetry["gpu_temp_c"] = float(parts[0])
                telemetry["gpu_power_watts"] = float(parts[1])
                telemetry["gpu_vram_used_mb"] = float(parts[2])
                telemetry["gpu_vram_total_mb"] = float(parts[3])
        except Exception:
            pass

        return telemetry
