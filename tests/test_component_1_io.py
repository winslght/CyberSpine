"""
组件 1 独立测试套件 (Component 1 Standalone Test Suite)
测试范围：IO 神经末梢、设备指纹记忆库、只读浅层结构嗅探与全机 IO 拓扑快照
"""
import os
import shutil
import sys
import tempfile
import unittest

# 确保控制台支持 UTF-8 打印
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.models.somatic_signals import DeviceClass, RawSomaticSignal
from src.perceptors.io.device_db import DeviceDatabase
from src.perceptors.io.storage_probe import StorageProbe
from src.perceptors.io.io_manager import IOPerceptorManager


class TestComponent1IO(unittest.TestCase):

    def setUp(self):
        # 创建独立测试临时目录
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_device_inventory.json")
        self.db = DeviceDatabase(db_path=self.db_path)

    def tearDown(self):
        # 清理测试临时目录
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_device_fingerprint_recognition(self):
        """测试 1：设备指纹计算与新老设备识别记忆"""
        print("\n--- [TEST 1: Device Fingerprint DB & Recognition] ---")

        # 1. 首次接入陌生设备
        dev1 = self.db.get_or_register(
            device_class=DeviceClass.STORAGE_REMOVABLE,
            volume_label="SAMSUNG_T7",
            serial_number="SN_12345678",
            total_capacity_gb=1000.0,
            free_capacity_gb=500.0,
            mount_point="E:\\",
        )
        self.assertFalse(dev1.is_known, "首次接入应被判定为陌生新设备 (is_known=False)")
        self.assertTrue(len(dev1.device_id) > 0, "应生成有效的指纹 ID")
        print(f"[PASS] 首次接入成功登记: ID={dev1.device_id}, is_known={dev1.is_known}, 卷标={dev1.volume_label}")

        # 2. 为该设备打上业务标签
        self.db.tag_device(dev1.device_id, ["WORK_PROJECT_SSD", "PYTHON_WORKSPACE"])

        # 3. 模拟拔出后再次插入同一设备
        dev2 = self.db.get_or_register(
            device_class=DeviceClass.STORAGE_REMOVABLE,
            volume_label="SAMSUNG_T7",
            serial_number="SN_12345678",
            total_capacity_gb=1000.0,
            free_capacity_gb=480.0,
            mount_point="E:\\",
        )
        self.assertTrue(dev2.is_known, "二次接入应被准确识别为已知熟客 (is_known=True)")
        self.assertEqual(dev1.device_id, dev2.device_id, "两次计算的指纹 ID 必须完全一致")
        self.assertIn("PYTHON_WORKSPACE", dev2.tags, "应成功继承历史画像标签")
        print(f"[PASS] 二次接入精准识别: ID={dev2.device_id}, is_known={dev2.is_known}, 继承标签={dev2.tags}")

    def test_02_shallow_structure_sniffing(self):
        """测试 2：只读浅层结构嗅探 (安全防杀软 + 特征识别)"""
        print("\n--- [TEST 2: Readonly Shallow Project Structure Sniffing] ---")

        # 构造模拟工程目录
        mock_usb_root = os.path.join(self.test_dir, "mock_usb_drive")
        os.makedirs(os.path.join(mock_usb_root, ".git"), exist_ok=True)
        os.makedirs(os.path.join(mock_usb_root, "src"), exist_ok=True)
        os.makedirs(os.path.join(mock_usb_root, "deep_folder", "level2", "level3"), exist_ok=True)

        with open(os.path.join(mock_usb_root, "requirements.txt"), "w") as f:
            f.write("fastapi\npsutil\n")
        with open(os.path.join(mock_usb_root, "main.py"), "w") as f:
            f.write("print('hello')\n")
        with open(os.path.join(mock_usb_root, "README.md"), "w") as f:
            f.write("# Mock Project\n")

        probe = StorageProbe(device_db=self.db)
        summary = probe.shallow_sniff(mock_usb_root, max_depth=2)

        print(f"[PASS] 嗅探耗时: {summary.scan_duration_ms:.2f}ms")
        print(f"[PASS] 采样文件数: {summary.file_count_sampled}")
        print(f"[PASS] 识别画像: {summary.detected_profiles}")

        self.assertLess(summary.scan_duration_ms, 50.0, "浅层嗅探耗时必须极低 (<50ms)")
        self.assertIn("PYTHON_PROJECT", summary.detected_profiles, "应准确识别出 Python 工程特征")
        self.assertIn("GIT_REPOSITORY", summary.detected_profiles, "应准确识别出 Git 仓库特征")

    def test_03_full_io_topology_snapshot(self):
        """测试 3：全机物理 IO 拓扑快照"""
        print("\n--- [TEST 3: Full Machine Somatic IO Snapshot] ---")

        io_mgr = IOPerceptorManager(db_path=self.db_path)
        snapshot = io_mgr.get_full_io_snapshot()

        mounted_disks = snapshot.get("mounted_storage_devices", [])
        net_ifs = snapshot.get("network_interfaces", {})

        print(f"[PASS] 当前挂载磁盘数: {len(mounted_disks)}")
        for d in mounted_disks[:3]:
            print(f"   - 盘符: {d.get('mount_point')} | 卷标: {d.get('volume_label')} | 容量: {d.get('total_capacity_gb')}GB")

        print(f"[PASS] 机器物理/虚拟网络接口数: {len(net_ifs)}")
        for if_name, info in list(net_ifs.items())[:3]:
            print(f"   - 网卡: {if_name} | 启用: {info.get('is_up')} | IP: {info.get('ipv4_addresses')}")

        self.assertGreater(len(mounted_disks), 0, "当前系统应至少检测到一个挂载磁盘 (C: 盘等)")

    def test_04_mock_event_emission(self):
        """测试 4：模拟新设备插入与原始感官电信号发射"""
        print("\n--- [TEST 4: Mock Device Insertion & Signal Emission] ---")

        mock_drive_path = os.path.join(self.test_dir, "mock_flash_drive")
        os.makedirs(mock_drive_path, exist_ok=True)
        with open(os.path.join(mock_drive_path, "Cargo.toml"), "w") as f:
            f.write("[package]\nname = 'rust_mock'\n")

        io_mgr = IOPerceptorManager(db_path=self.db_path)
        signal = io_mgr.mock_inject_storage_signal(
            mock_root_path=mock_drive_path,
            volume_label="RUST_CODE_USB",
            total_gb=64.0,
            free_gb=32.0,
            mock_serial="SN_RUST_DEV_01",
        )

        self.assertIsInstance(signal, RawSomaticSignal)
        self.assertEqual(signal.channel, "IO_STORAGE")
        self.assertEqual(signal.event_type, "DEVICE_ATTACHED")
        self.assertEqual(signal.device_fingerprint.volume_label, "RUST_CODE_USB")
        self.assertIn("RUST_GO_PROJECT", signal.structure_summary.detected_profiles)

        print(f"[PASS] 成功发射原始感官电信号:")
        print(f"   - Signal ID: {signal.signal_id}")
        print(f"   - Device ID: {signal.device_fingerprint.device_id}")
        print(f"   - 识别特征: {signal.structure_summary.detected_profiles}")
        print(f"   - 绑定标签: {signal.device_fingerprint.tags}")


if __name__ == "__main__":
    unittest.main()
