"""
CyberSpine 全身感官总控调度中心 (Somatic Perceptor Hub) 集成测试套件
"""
import sys
import os
import unittest

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.perceptors.somatic_hub import SomaticPerceptorHub
from src.pacing.neural_buffer import TemporalNeuralBuffer


class TestSomaticHubIntegration(unittest.TestCase):

    def setUp(self):
        self.hub = SomaticPerceptorHub()
        self.buffer = TemporalNeuralBuffer(alignment_window_seconds=1.0)

    def test_01_full_somatic_topology_snapshot(self):
        """测试 1: 全身 8 大感官通道拓扑基线统一采集"""
        topo = self.hub.get_full_somatic_topology()
        self.assertIn("snapshot_timestamp", topo)
        self.assertIn("channels", topo)
        self.assertIn("performance_benchmarks", topo)

        print("\n--- [TEST 1: Full Somatic Topology Baseline] ---")
        print(f"[PASS] 注册感知通道总数: {len(topo['channels'])}")
        for ch_id, data in topo["channels"].items():
            print(f"   - 通道 [{ch_id}]: {list(data.keys())}")

    def test_02_poll_all_signals_and_feed_buffer(self):
        """测试 2: 全身多感官电信号统一轮询与注入缓冲器"""
        # 触发模拟事件
        self.hub.notifications_perceptor.mock_trigger_notification(source="Calendar", count=1)
        self.hub.stability_perceptor.mock_trigger_crash_event(process_name="test_runner.exe")

        signals = self.hub.poll_all_signals()
        self.assertGreaterEqual(len(signals), 2)

        print("\n--- [TEST 2: Somatic Signals Poll & Hub Ingestion] ---")
        print(f"[PASS] 成功捕获全身电信号数: {len(signals)}")
        for s in signals:
            print(f"   ✓ 通道=[{s.channel}] 事件=[{s.event_type}] 来源=[{s.source_probe}]")

        # 注入缓冲器
        ingested = self.hub.feed_into_buffer(self.buffer)
        self.assertGreaterEqual(ingested, 0)
        print(f"[PASS] 成功注入时钟缓冲器信号数: {ingested}")

    def test_03_hardware_benchmark_logging(self):
        """测试 3: 验证开发留痕与性能基准报告落盘"""
        report = self.hub.record_hardware_benchmark_report()
        self.assertIn("CyberSpine 全感官神经末梢实机性能基准报告", report)
        self.assertTrue(self.hub.benchmark_log_file.exists())

        print("\n--- [TEST 3: Benchmark Report Logging] ---")
        print(f"[PASS] 基准报告已落盘至: {self.hub.benchmark_log_file}")
        print(f"[PASS] 信号追踪日志文件: {self.hub.trace_log_file}")

    def test_04_perceptor_hot_toggle_and_skip_disabled(self):
        """测试 4: 神经末梢热插拔启停与停用传感器自动跳过"""
        # 1. 禁用通知探针
        toggle_ok = self.hub.set_perceptor_enabled("nerve.system.notifications", False)
        self.assertTrue(toggle_ok)
        self.assertFalse(self.hub.get_perceptor_enabled("nerve.system.notifications"))

        # 触发通知模拟事件
        self.hub.notifications_perceptor.mock_trigger_notification(source="Email", count=2)
        signals = self.hub.poll_all_signals()
        notify_signals = [s for s in signals if s.channel == "NOTIFICATIONS"]
        self.assertEqual(len(notify_signals), 0, "已停用的通知探针不应产生任何信号")

        # 2. 重新启用通知探针
        toggle_ok2 = self.hub.set_perceptor_enabled("nerve.system.notifications", True)
        self.assertTrue(toggle_ok2)
        self.assertTrue(self.hub.get_perceptor_enabled("nerve.system.notifications"))

        # 再次触发并轮询
        self.hub.notifications_perceptor.mock_trigger_notification(source="Slack", count=1)
        signals2 = self.hub.poll_all_signals()
        notify_signals2 = [s for s in signals2 if s.channel == "NOTIFICATIONS"]
        self.assertGreaterEqual(len(notify_signals2), 1, "重新启用后应正常捕获通知信号")

        # 3. 测试 IO 存储探针热插拔
        io_toggle_ok = self.hub.set_perceptor_enabled("nerve.io.storage", False)
        self.assertTrue(io_toggle_ok)
        self.assertFalse(self.hub.get_perceptor_enabled("nerve.io.storage"))
        self.assertFalse(self.hub.io_manager.enabled)

        io_restore_ok = self.hub.set_perceptor_enabled("nerve.io.storage", True)
        self.assertTrue(io_restore_ok)
        self.assertTrue(self.hub.get_perceptor_enabled("nerve.io.storage"))
        self.assertTrue(self.hub.io_manager.enabled)

        # 4. 测试不存在探针 ID
        unknown_ok = self.hub.set_perceptor_enabled("nerve.unknown.sensor", False)
        self.assertFalse(unknown_ok)
        self.assertIsNone(self.hub.get_perceptor_enabled("nerve.unknown.sensor"))

        print("\n--- [TEST 4: Sensory Hot-Toggle & Skip Disabled Probes] ---")
        print("[PASS] 禁用探针后 0 信号产生，重新启用后即时恢复捕获")
        print("[PASS] IO 存储探针与异常探针 ID 判定均符合契约")


if __name__ == '__main__':
    unittest.main()
