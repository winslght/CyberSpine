"""
存储介质 IO 探测器 (Storage Probe)
负责可移动存储介质 (U盘/移动硬盘/SD卡) 的插拔感知与非侵入式浅层结构嗅探 (MaxDepth=2)。
"""
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import psutil

from ...models.somatic_signals import (
    DeviceClass,
    DeviceFingerprint,
    RawSomaticSignal,
    ShallowStructureSummary,
)
from .device_db import DeviceDatabase


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StorageProbe:
    """可移动存储设备探测器"""

    # 特征文件与画像签名映射表
    SIGNATURE_RULES = {
        "PYTHON_PROJECT": {"requirements.txt", "pyproject.toml", "setup.py", "Pipfile", "main.py", ".venv", "venv"},
        "GIT_REPOSITORY": {".git"},
        "NODEJS_PROJECT": {"package.json", "node_modules", "tsconfig.json", "vite.config.ts", "vite.config.js"},
        "RUST_GO_PROJECT": {"Cargo.toml", "go.mod", "Makefile", "CMakeLists.txt"},
        "CAMERA_RAW_MEDIA": {"DCIM", "AVCHD", "PRIVATE", ".mov", ".mp4", ".raw", ".arw", ".cr3"},
        "OFFICE_DOCUMENTS": {".docx", ".xlsx", ".pptx", ".pdf", ".csv", ".md"},
        "BACKUP_ARCHIVE": {".zip", ".rar", ".7z", ".tar.gz", ".bak", ".iso"},
    }

    def __init__(self, device_db: Optional[DeviceDatabase] = None):
        self.db = device_db or DeviceDatabase()
        self._known_mounted_drives: Dict[str, DeviceFingerprint] = {}
        self.refresh_baseline()

    def refresh_baseline(self) -> None:
        """刷新当前机器上已挂载的磁盘基线"""
        current_drives = self.scan_current_drives()
        self._known_mounted_drives = {
            dev.mount_point: dev for dev in current_drives if dev.mount_point
        }

    def scan_current_drives(self) -> List[DeviceFingerprint]:
        """枚举当前系统挂载的所有磁盘与驱动器"""
        results = []
        try:
            partitions = psutil.disk_partitions(all=False)
        except Exception:
            return results

        for p in partitions:
            mount_point = p.mountpoint
            opts = p.opts.lower() if p.opts else ""
            fstype = p.fstype

            # 判断是否为可移动设备或网络/固定驱动器
            is_removable = "removable" in opts or "cdrom" in opts
            device_class = (
                DeviceClass.STORAGE_REMOVABLE if is_removable else DeviceClass.STORAGE_FIXED
            )

            total_gb = None
            free_gb = None
            try:
                usage = psutil.disk_usage(mount_point)
                total_gb = round(usage.total / (1024 ** 3), 2)
                free_gb = round(usage.free / (1024 ** 3), 2)
            except Exception:
                pass

            volume_label = p.device.replace("\\", "")

            fingerprint = self.db.get_or_register(
                device_class=device_class,
                volume_label=volume_label,
                serial_number=f"{p.device}_{fstype}",
                total_capacity_gb=total_gb,
                free_capacity_gb=free_gb,
                mount_point=mount_point,
            )
            results.append(fingerprint)

        return results

    def shallow_sniff(
        self, root_path: str, max_depth: int = 2, max_files_sampled: int = 50
    ) -> ShallowStructureSummary:
        """
        浅层结构嗅探 (安全只读模式，MaxDepth=2，耗时通常 < 5ms)
        仅识别根目录及一级子目录的特征文件，绝不触发全盘深度扫描。
        """
        start_time = time.perf_counter()
        top_dirs: List[str] = []
        top_files: List[str] = []
        detected_profiles: Set[str] = set()
        file_count = 0

        target_path = Path(root_path)
        if not target_path.exists() or not target_path.is_dir():
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ShallowStructureSummary(
                scan_duration_ms=duration_ms,
                detected_profiles=["UNACCESSIBLE_DRIVE"],
            )

        try:
            # 扫描第 1 层 (Root)
            for item in target_path.iterdir():
                file_count += 1
                if file_count > max_files_sampled:
                    break

                name = item.name
                suffix = item.suffix.lower()

                if item.is_dir():
                    top_dirs.append(name)
                    # 检查目录级签名 (如 .git, DCIM, node_modules, venv)
                    for profile, sigs in self.SIGNATURE_RULES.items():
                        if name in sigs:
                            detected_profiles.add(profile)
                else:
                    top_files.append(name)
                    # 检查文件级签名或后缀
                    for profile, sigs in self.SIGNATURE_RULES.items():
                        if name in sigs or suffix in sigs:
                            detected_profiles.add(profile)

            # 扫描第 2 层 (有限浅层采样)
            if max_depth >= 2:
                for sub_dir_name in top_dirs[:5]:  # 只采样前 5 个子目录
                    sub_dir_path = target_path / sub_dir_name
                    try:
                        if sub_dir_path.is_dir():
                            for sub_item in sub_dir_path.iterdir():
                                file_count += 1
                                if file_count > max_files_sampled:
                                    break
                                sub_name = sub_item.name
                                sub_suffix = sub_item.suffix.lower()
                                for profile, sigs in self.SIGNATURE_RULES.items():
                                    if sub_name in sigs or sub_suffix in sigs:
                                        detected_profiles.add(profile)
                    except (PermissionError, OSError):
                        continue

        except (PermissionError, OSError):
            detected_profiles.add("RESTRICTED_PERMISSION")

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # 如果没有匹配到已知工程，归类为通用数据
        if not detected_profiles:
            detected_profiles.add("GENERIC_STORAGE")

        return ShallowStructureSummary(
            scan_duration_ms=duration_ms,
            top_level_directories=top_dirs[:10],
            top_level_files=top_files[:15],
            detected_profiles=sorted(list(detected_profiles)),
            file_count_sampled=file_count,
        )

    def detect_storage_changes(self) -> List[RawSomaticSignal]:
        """
        对比当前磁盘与基线，检测驱动器挂载与卸载事件
        """
        current_drives_list = self.scan_current_drives()
        current_map = {dev.mount_point: dev for dev in current_drives_list if dev.mount_point}

        signals: List[RawSomaticSignal] = []

        # 1. 检查新挂载设备 (Attached)
        for mount_point, dev in current_map.items():
            if mount_point not in self._known_mounted_drives:
                # 仅对新设备执行只读浅层嗅探
                summary = self.shallow_sniff(mount_point)

                # 如果嗅探出明显特征，自动在记忆库补充画像标签
                if summary.detected_profiles:
                    self.db.tag_device(dev.device_id, summary.detected_profiles)
                    dev.tags = sorted(list(set(dev.tags + summary.detected_profiles)))

                signal_id = f"sig_storage_{int(time.time() * 1000)}_{dev.device_id[:8]}"
                signal = RawSomaticSignal(
                    signal_id=signal_id,
                    timestamp=utc_now(),
                    channel="IO_STORAGE",
                    event_type="DEVICE_ATTACHED",
                    source_probe="StorageProbe",
                    device_fingerprint=dev,
                    structure_summary=summary,
                    raw_metrics={
                        "mount_point": mount_point,
                        "total_gb": dev.total_capacity_gb,
                        "free_gb": dev.free_capacity_gb,
                    },
                )
                signals.append(signal)

        # 2. 检查已拔出设备 (Removed)
        for mount_point, old_dev in self._known_mounted_drives.items():
            if mount_point not in current_map:
                signal_id = f"sig_storage_rm_{int(time.time() * 1000)}_{old_dev.device_id[:8]}"
                signal = RawSomaticSignal(
                    signal_id=signal_id,
                    timestamp=utc_now(),
                    channel="IO_STORAGE",
                    event_type="DEVICE_REMOVED",
                    source_probe="StorageProbe",
                    device_fingerprint=old_dev,
                    raw_metrics={"unmounted_point": mount_point},
                )
                signals.append(signal)

        # 更新基线
        self._known_mounted_drives = current_map
        return signals
