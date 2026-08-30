"""
CyberSpine 神经末梢 7 (网络健康与链路质量感知) 独立单元测试套件
"""
import sys
import unittest

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.perceptors.network.network_health import NetworkHealthPerceptor


class TestNetworkHealthPerceptor(unittest.TestCase):

    def setUp(self):
        self.perceptor = NetworkHealthPerceptor()

    def test_01_get_baseline(self):
        """测试 1: 提取网络健康与活动网卡基线"""
        baseline = self.perceptor.get_baseline()
        self.assertIn("health", baseline)
        health = baseline["health"]
        self.assertIn("is_online", health)
        self.assertIn("latency_ms", health)
        self.assertIn("active_interfaces", health)

        print("\n--- [TEST 1: Network Health Baseline] ---")
        print(f"[PASS] 当前联网状态: {health['is_online']} (时延: {health['latency_ms']}ms)")
        print(f"[PASS] 活动物理网卡: {health['active_interfaces']}")

    def test_02_poll_signals_connectivity_change(self):
        """测试 2: 模拟网络断开与恢复电信号产生"""
        self.perceptor._last_is_online = True

        # 模拟网络断开
        fake_health = {"is_online": False, "latency_ms": 999.0, "active_interfaces": []}
        self.perceptor._check_connectivity = lambda: fake_health

        signals = self.perceptor.poll_signals()
        self.assertEqual(len(signals), 1)
        sig = signals[0]
        self.assertEqual(sig.channel, "IO_NETWORK")
        self.assertEqual(sig.event_type, "NETWORK_DISCONNECTED")

        print("\n--- [TEST 2: Network Disconnection Event] ---")
        print(f"[PASS] 捕获断网信号: ID={sig.signal_id} (时延={sig.raw_metrics.get('latency_ms')}ms)")

    def test_03_performance_metric(self):
        """测试 3: 验证网络采样耗时指标"""
        self.perceptor.poll_signals()
        summary = self.perceptor.get_performance_summary()
        self.assertLessEqual(summary["avg_duration_ms"], 500.0)

        print("\n--- [TEST 3: Network Perceptor Performance Metric] ---")
        print(f"[PASS] 单次采样平均耗时: {summary['avg_duration_ms']:.3f}ms")


if __name__ == '__main__':
    unittest.main()
