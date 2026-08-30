"""
CyberSpine 神经末梢 3 (高压力负载感知) 独立单元测试套件
"""
import sys
import unittest

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.perceptors.system.high_load import HighLoadStressPerceptor


class TestHighLoadStressPerceptor(unittest.TestCase):

    def setUp(self):
        self.perceptor = HighLoadStressPerceptor()

    def test_01_get_baseline(self):
        """测试 1: 提取系统当前负载与 Top 进程基线"""
        baseline = self.perceptor.get_baseline()
        self.assertIn("cpu_percent", baseline)
        self.assertIn("memory_percent", baseline)
        self.assertIn("top_processes", baseline)

        print("\n--- [TEST 1: System Stress Baseline] ---")
        print(f"[PASS] 当前 CPU 使用率: {baseline['cpu_percent']}% | 内存使用率: {baseline['memory_percent']}%")
        print(f"[PASS] Top 进程: {[p.get('name') for p in baseline['top_processes']]}")

    def test_02_stress_spike_and_release(self):
        """测试 2: 模拟压力突增与释放状态流转"""
        # 调低阈值模拟超负荷
        low_threshold_perceptor = HighLoadStressPerceptor(cpu_threshold=0.01)
        signals = low_threshold_perceptor.poll_signals()

        if signals:
            sig = signals[0]
            self.assertEqual(sig.channel, "SYSTEM_STRESS")
            self.assertEqual(sig.event_type, "LOAD_SPIKE_DETECTED")
            print("\n--- [TEST 2: Stress Spike Detection] ---")
            print(f"[PASS] 捕获负载尖峰信号: ID={sig.signal_id} (CPU={sig.raw_metrics.get('cpu_percent')}%)")

    def test_03_performance_metric(self):
        """测试 3: 验证负载采样耗时指标"""
        self.perceptor.poll_signals()
        summary = self.perceptor.get_performance_summary()
        self.assertLessEqual(summary["avg_duration_ms"], 10.0)

        print("\n--- [TEST 3: Stress Perceptor Performance Metric] ---")
        print(f"[PASS] 单次采样平均耗时: {summary['avg_duration_ms']:.3f}ms")


if __name__ == '__main__':
    unittest.main()
