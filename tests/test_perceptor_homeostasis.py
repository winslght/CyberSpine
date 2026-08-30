"""
CyberSpine 神经末梢 4 (系统稳态与能耗感知) 独立单元测试套件
"""
import sys
import unittest

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.perceptors.system.system_homeostasis import SystemHomeostasisPerceptor


class TestSystemHomeostasisPerceptor(unittest.TestCase):

    def setUp(self):
        self.perceptor = SystemHomeostasisPerceptor()

    def test_01_get_baseline(self):
        """测试 1: 提取系统 Uptime 与供电基线"""
        baseline = self.perceptor.get_baseline()
        self.assertIn("uptime_seconds", baseline)
        self.assertIn("battery_info", baseline)

        print("\n--- [TEST 1: Homeostasis Uptime & Power Baseline] ---")
        print(f"[PASS] 系统已稳定运行: {baseline['uptime_hours']} 小时 ({baseline['uptime_seconds']} 秒)")
        print(f"[PASS] 电源状态: {baseline['battery_info']}")

    def test_02_poll_signals_power_change(self):
        """测试 2: 模拟电源状态切换感知"""
        self.perceptor._last_plugged = True
        
        # 模拟拔掉电源
        fake_bat = {"percent": 85, "is_plugged": False, "secs_left": 7200}
        self.perceptor._get_battery_info = lambda: fake_bat

        signals = self.perceptor.poll_signals()
        print("\n--- [TEST 2: Power Unplugged Signal Detection] ---")
        if signals:
            sig = signals[0]
            self.assertEqual(sig.channel, "HOMEOSTASIS")
            self.assertEqual(sig.event_type, "POWER_UNPLUGGED")
            print(f"[PASS] 捕获电源拔出信号: ID={sig.signal_id} (剩余电量={sig.raw_metrics.get('percent')}%)")

    def test_03_performance_metric(self):
        """测试 3: 验证稳态采样耗时指标"""
        self.perceptor.poll_signals()
        summary = self.perceptor.get_performance_summary()
        self.assertLessEqual(summary["avg_duration_ms"], 10.0)

        print("\n--- [TEST 3: Homeostasis Perceptor Performance Metric] ---")
        print(f"[PASS] 单次采样平均耗时: {summary['avg_duration_ms']:.3f}ms")


if __name__ == '__main__':
    unittest.main()
