"""
全机 IO 神经末梢总控管理器 (IO Perceptor Manager)
负责管理所有机器底层 IO 探测器 (存储、网络、外设)，输出全局 IO 拓扑快照并派发原始神经电信号。
"""
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import psutil

from ...models.somatic_signals import (
    DeviceClass,
    DeviceFingerprint,
    RawSomaticSignal,
    ShallowStructureSummary,
)
from .device_db import DeviceDatabase
from .storage_probe import StorageProbe


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IOPerceptorManager:
    """全机 IO 神经末梢总控管理器"""

    def __init__(self, db_path: Optional[str] = None):
        self.perceptor_id = "nerve.io.storage"
        self.enabled: bool = True
        self.db = DeviceDatabase(db_path=db_path)
        self.storage_probe = StorageProbe(device_db=self.db)
        self._last_network_states: Dict[str, bool] = {}
        self._init_network_baseline()

    def set_enabled(self, enabled: bool) -> None:
        """动态启用/停用 IO 存储感知探针"""
        self.enabled = bool(enabled)

    def _init_network_baseline(self) -> None:
        """初始化网络接口基线状态"""
        try:
            stats = psutil.net_if_stats()
            self._last_network_states = {if_name: s.isup for if_name, s in stats.items()}
        except Exception:
            self._last_network_states = {}

    def get_full_io_snapshot(self) -> Dict[str, Any]:
        """
        获取机器当前完整的全身物理 IO 拓扑快照
        包含：挂载的全部磁盘、活动网络接口、记忆库已知设备数
        """
        # 1. 磁盘存储拓扑
        drives = self.storage_probe.scan_current_drives()

        # 2. 网络接口拓扑
        net_info = {}
        try:
            stats = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()
            for if_name, s in stats.items():
                ip_list = []
                if if_name in addrs:
                    for a in addrs[if_name]:
                        if a.family.name == "AF_INET":
                            ip_list.append(a.address)
                net_info[if_name] = {
                    "is_up": s.isup,
                    "speed_mbps": s.speed,
                    "ipv4_addresses": ip_list,
                }
        except Exception:
            pass

        # 3. 记忆库统计
        known_devices = self.db.list_all_devices()

        return {
            "snapshot_timestamp": utc_now().isoformat(),
            "enabled": self.enabled,
            "mounted_storage_devices": [d.model_dump() for d in drives],
            "network_interfaces": net_info,
            "total_known_devices_in_memory": len(known_devices),
        }

    def poll_io_signals(self) -> List[RawSomaticSignal]:
        """
        轮询并捕获所有底层 IO 变动产生的原始感官电信号
        """
        signals: List[RawSomaticSignal] = []

        # 1. 存储变动
        storage_signals = self.storage_probe.detect_storage_changes()
        signals.extend(storage_signals)

        # 2. 网络状态变动
        try:
            current_stats = psutil.net_if_stats()
            for if_name, s in current_stats.items():
                old_state = self._last_network_states.get(if_name)
                if old_state is not None and old_state != s.isup:
                    sig_id = f"sig_net_{int(time.time() * 1000)}_{if_name}"
                    event_type = "DEVICE_ATTACHED" if s.isup else "DEVICE_REMOVED"
                    sig = RawSomaticSignal(
                        signal_id=sig_id,
                        timestamp=utc_now(),
                        channel="IO_NETWORK",
                        event_type=event_type,
                        source_probe="NetworkProbe",
                        raw_metrics={"interface": if_name, "is_up": s.isup, "speed": s.speed},
                    )
                    signals.append(sig)
                self._last_network_states[if_name] = s.isup
        except Exception:
            pass

        return signals

    def mock_inject_storage_signal(
        self,
        mock_root_path: str,
        volume_label: str = "MOCK_WORK_SSD",
        total_gb: float = 128.0,
        free_gb: float = 64.0,
        mock_serial: str = "SN_MOCK_9988",
    ) -> RawSomaticSignal:
        """
        [用于自测与演练] 模拟接入指定目录作为新移动存储
        """
        fingerprint = self.db.get_or_register(
            device_class=DeviceClass.STORAGE_REMOVABLE,
            volume_label=volume_label,
            serial_number=mock_serial,
            total_capacity_gb=total_gb,
            free_capacity_gb=free_gb,
            mount_point=mock_root_path,
        )

        summary = self.storage_probe.shallow_sniff(mock_root_path)
        if summary.detected_profiles:
            self.db.tag_device(fingerprint.device_id, summary.detected_profiles)
            fingerprint.tags = sorted(list(set(fingerprint.tags + summary.detected_profiles)))

        signal_id = f"sig_mock_storage_{int(time.time() * 1000)}_{fingerprint.device_id[:8]}"
        return RawSomaticSignal(
            signal_id=signal_id,
            timestamp=utc_now(),
            channel="IO_STORAGE",
            event_type="DEVICE_ATTACHED",
            source_probe="StorageProbeMock",
            device_fingerprint=fingerprint,
            structure_summary=summary,
            raw_metrics={
                "mount_point": mock_root_path,
                "total_gb": total_gb,
                "free_gb": free_gb,
                "is_mock": True,
            },
        )
