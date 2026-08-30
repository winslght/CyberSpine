"""
设备指纹记忆库 (Device Fingerprint Database)
负责存储和比对所有接入过机器的硬件外设与存储设备，识别熟客与陌生设备。
"""
import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from ...models.somatic_signals import DeviceClass, DeviceFingerprint


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DeviceDatabase:
    """本地轻量级设备指纹数据库"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            self.db_path = base_dir / "runtime" / "data" / "device_inventory.json"
        else:
            self.db_path = Path(db_path)

        self._lock = threading.Lock()
        self._ensure_db_exists()

    def _ensure_db_exists(self) -> None:
        """确保数据存储目录与文件存在"""
        os.makedirs(self.db_path.parent, exist_ok=True)
        if not self.db_path.exists():
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump({"devices": {}, "version": "1.0"}, f, indent=2, ensure_ascii=False)

    @staticmethod
    def generate_fingerprint_id(
        device_class: DeviceClass,
        serial_number: Optional[str] = None,
        volume_label: Optional[str] = None,
        total_capacity_gb: Optional[float] = None,
        vendor_id: Optional[str] = None,
        product_id: Optional[str] = None,
    ) -> str:
        """根据硬件特征计算稳定唯一哈希指纹"""
        raw_signature = (
            f"class:{device_class.value}|"
            f"sn:{serial_number or 'UNKNOWN'}|"
            f"label:{volume_label or 'UNKNOWN'}|"
            f"cap:{round(total_capacity_gb or 0.0, 1)}|"
            f"vid:{vendor_id or 'UNKNOWN'}|"
            f"pid:{product_id or 'UNKNOWN'}"
        )
        return hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()[:16]

    def _load_data(self) -> Dict:
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"devices": {}, "version": "1.0"}

    def _save_data(self, data: Dict) -> None:
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def get_or_register(
        self,
        device_class: DeviceClass,
        volume_label: Optional[str] = None,
        serial_number: Optional[str] = None,
        total_capacity_gb: Optional[float] = None,
        free_capacity_gb: Optional[float] = None,
        mount_point: Optional[str] = None,
        vendor_id: Optional[str] = None,
        product_id: Optional[str] = None,
        default_tags: Optional[List[str]] = None,
    ) -> DeviceFingerprint:
        """
        查询或登记设备指纹。
        如果设备曾接入过，返回 is_known=True 并继承历史标签；
        如果为首次接入，登记新设备并返回 is_known=False。
        """
        device_id = self.generate_fingerprint_id(
            device_class=device_class,
            serial_number=serial_number,
            volume_label=volume_label,
            total_capacity_gb=total_capacity_gb,
            vendor_id=vendor_id,
            product_id=product_id,
        )

        with self._lock:
            data = self._load_data()
            devices = data.get("devices", {})

            now = utc_now()

            if device_id in devices:
                # 已知熟客设备
                raw_dev = devices[device_id]
                raw_dev["last_seen"] = now.isoformat()
                raw_dev["mount_point"] = mount_point
                raw_dev["free_capacity_gb"] = free_capacity_gb

                self._save_data(data)

                return DeviceFingerprint(
                    device_id=device_id,
                    device_class=device_class,
                    vendor_id=vendor_id or raw_dev.get("vendor_id"),
                    product_id=product_id or raw_dev.get("product_id"),
                    volume_label=volume_label or raw_dev.get("volume_label"),
                    serial_number=serial_number or raw_dev.get("serial_number"),
                    total_capacity_gb=total_capacity_gb or raw_dev.get("total_capacity_gb"),
                    free_capacity_gb=free_capacity_gb,
                    mount_point=mount_point,
                    tags=raw_dev.get("tags", []),
                    first_seen=datetime.fromisoformat(raw_dev.get("first_seen", now.isoformat())),
                    last_seen=now,
                    is_known=True,
                )
            else:
                # 首次接入的新设备
                tags = list(default_tags or [])
                new_record = {
                    "device_id": device_id,
                    "device_class": device_class.value,
                    "vendor_id": vendor_id,
                    "product_id": product_id,
                    "volume_label": volume_label,
                    "serial_number": serial_number,
                    "total_capacity_gb": total_capacity_gb,
                    "free_capacity_gb": free_capacity_gb,
                    "mount_point": mount_point,
                    "tags": tags,
                    "first_seen": now.isoformat(),
                    "last_seen": now.isoformat(),
                }
                devices[device_id] = new_record
                data["devices"] = devices
                self._save_data(data)

                return DeviceFingerprint(
                    device_id=device_id,
                    device_class=device_class,
                    vendor_id=vendor_id,
                    product_id=product_id,
                    volume_label=volume_label,
                    serial_number=serial_number,
                    total_capacity_gb=total_capacity_gb,
                    free_capacity_gb=free_capacity_gb,
                    mount_point=mount_point,
                    tags=tags,
                    first_seen=now,
                    last_seen=now,
                    is_known=False,
                )

    def tag_device(self, device_id: str, tags: List[str]) -> bool:
        """为指定设备添加或更新画像标签"""
        with self._lock:
            data = self._load_data()
            if device_id in data.get("devices", {}):
                current_tags = set(data["devices"][device_id].get("tags", []))
                current_tags.update(tags)
                data["devices"][device_id]["tags"] = sorted(list(current_tags))
                self._save_data(data)
                return True
            return False

    def list_all_devices(self) -> List[DeviceFingerprint]:
        """列出记忆库中所有已知设备"""
        with self._lock:
            data = self._load_data()
            res = []
            for dev in data.get("devices", {}).values():
                res.append(
                    DeviceFingerprint(
                        device_id=dev["device_id"],
                        device_class=DeviceClass(dev["device_class"]),
                        vendor_id=dev.get("vendor_id"),
                        product_id=dev.get("product_id"),
                        volume_label=dev.get("volume_label"),
                        serial_number=dev.get("serial_number"),
                        total_capacity_gb=dev.get("total_capacity_gb"),
                        free_capacity_gb=dev.get("free_capacity_gb"),
                        mount_point=dev.get("mount_point"),
                        tags=dev.get("tags", []),
                        first_seen=datetime.fromisoformat(dev["first_seen"]),
                        last_seen=datetime.fromisoformat(dev["last_seen"]),
                        is_known=True,
                    )
                )
            return res
