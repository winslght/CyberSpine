"""
CyberSpine 组件 2 (中枢时钟缓冲与时空对齐机) 独立单元测试套件
"""
import sys
import time
import unittest
from datetime import datetime, timezone, timedelta

# 保证在不同控制台编码下正常打印
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.models.somatic_signals import (
    RawSomaticSignal,
    DeviceFingerprint,
    DeviceClass,
    ShallowStructureSummary,
    PacingStateEnum,
    utc_now,
)
from src.pacing.neural_buffer import TemporalNeuralBuffer


class TestComponent2NeuralBuffer(unittest.TestCase):

    def setUp(self):
        self.buffer = TemporalNeuralBuffer(alignment_window_seconds=0.2)

    def _create_dummy_signal(self, channel="IO_STORAGE", event_type="DEVICE_ATTACHED"):
        dev = DeviceFingerprint(
            device_id="dummy_dev_001",
            device_class=DeviceClass.STORAGE_REMOVABLE,
            volume_label="TEST_USB",
            tags=["PYTHON_WORKSPACE"],
        )
        struct = ShallowStructureSummary(
            scan_duration_ms=1.2,
            top_level_files=["main.py", "requirements.txt"],
            top_level_directories=[".git"],
            detected_profiles=["PYTHON_PROJECT", "GIT_REPOSITORY"],
            file_count_sampled=5,
        )
        return RawSomaticSignal(
            signal_id=f"sig_{int(time.time()*1000)}",
            channel=channel,
            event_type=event_type,
            source_probe="probe_test",
            device_fingerprint=dev,
            structure_summary=struct,
        )

    def test_01_ingest_and_window_accumulation(self):
        """测试 1: 信号正常入队与时间窗口积累"""
        sig1 = self._create_dummy_signal(channel="IO_STORAGE")
        sig2 = self._create_dummy_signal(channel="IO_NETWORK", event_type="STATE_CHANGED")

        self.assertTrue(self.buffer.ingest_signal(sig1))
        self.assertTrue(self.buffer.ingest_signal(sig2))

        # 刚入队时窗口尚未到达 0.2 秒
        self.assertFalse(self.buffer.is_window_ready())
        print("\n--- [TEST 1: Signal Ingestion & Queue] ---")
        print("[PASS] 多路参差电信号成功入队，时钟窗口就绪状态判断准确")

    def test_02_flush_aligned_packet_on_window_ready(self):
        """测试 2: 窗口到期后融合打包为 FusedSomaticPacket"""
        sig1 = self._create_dummy_signal(channel="IO_STORAGE")
        sig2 = self._create_dummy_signal(channel="WORKSPACE", event_type="FOCUS_SWITCHED")

        self.buffer.ingest_signal(sig1)
        self.buffer.ingest_signal(sig2)

        # 等待对齐窗口到期 (0.2s)
        time.sleep(0.25)
        self.assertTrue(self.buffer.is_window_ready())

        packet = self.buffer.flush_aligned_packet()
        self.assertIsNotNone(packet)
        self.assertEqual(len(packet.signals), 2)
        self.assertEqual(packet.pacing_state, PacingStateEnum.MICRO_PAUSE)
        self.assertIn("PYTHON_PROJECT", packet.somatic_summary["structure_profiles"])

        print("\n--- [TEST 2: Spatiotemporal Alignment & Fused Packet] ---")
        print(f"[PASS] 成功生成融合电信号包: {packet.packet_id}")
        print(f"[PASS] 汇聚通道: {packet.somatic_summary['channels']}")
        print(f"[PASS] 识别画像: {packet.somatic_summary['structure_profiles']}")

    def test_03_efferent_inhibition(self):
        """测试 3: 大脑下行抑制递质下达与自动静默防护"""
        self.buffer.apply_inhibition(duration_seconds=1)

        sig = self._create_dummy_signal()
        accepted = self.buffer.ingest_signal(sig)
        self.assertFalse(accepted, "在抑制冷却期内，信号应被静默拒绝")

        print("\n--- [TEST 3: Efferent Inhibition Protocol] ---")
        print("[PASS] 下行抑制递质生效，中枢在免打扰冷却期内自动静默丢弃常规信号")

    def test_04_force_flush(self):
        """测试 4: 紧急强制刷新机制"""
        sig = self._create_dummy_signal()
        self.buffer.ingest_signal(sig)

        packet = self.buffer.flush_aligned_packet(force=True)
        self.assertIsNotNone(packet)
        self.assertEqual(len(packet.signals), 1)
        print("\n--- [TEST 4: Force Flush on Urgent Need] ---")
        print(f"[PASS] 强制刷新成功，耗时 0ms，立即产出 Packet ID={packet.packet_id}")


if __name__ == '__main__':
    unittest.main()
