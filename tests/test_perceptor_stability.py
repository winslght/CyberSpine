"""
CyberSpine 神经末梢 6 (系统稳定性与崩溃感知) 独立单元测试套件
"""
import sys
import unittest

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.perceptors.system.system_stability import SystemStabilityPerceptor


class TestSystemStabilityPerceptor(unittest.TestCase):

    def setUp(self):
        self.perceptor = SystemStabilityPerceptor()

    def test_01_get_baseline(self):
        """测试 1: 提取系统稳定性基线"""
        baseline = self.perceptor.get_baseline()
        self.assertIn("total_crashes_tracked", baseline)
        self.assertIn("recent_crashes", baseline)

        print("\n--- [TEST 1: System Stability Baseline] ---")
        print(f"[PASS] 当前已追踪崩溃事件数: {baseline['total_crashes_tracked']}")

    def test_02_poll_signals_on_crash_event(self):
        """测试 2: 模拟应用程序闪退与段错误异常捕获"""
        # 模拟外部捕获到 python 发生 0xc0000005 访问违规
        self.perceptor.mock_trigger_crash_event(
            process_name="python.exe",
            fault_module="ntdll.dll",
            exception_code="0xc0000005",
        )

        signals = self.perceptor.poll_signals()
        self.assertEqual(len(signals), 1)
        sig = signals[0]
        self.assertEqual(sig.channel, "STABILITY")
        self.assertEqual(sig.event_type, "PROCESS_CRASH_DETECTED")
        self.assertEqual(sig.raw_metrics.get("process_name"), "python.exe")

        print("\n--- [TEST 2: Crash Signal Emission] ---")
        print(f"[PASS] 捕获崩溃电信号: ID={sig.signal_id} (进程={sig.raw_metrics.get('process_name')}, 错误代码={sig.raw_metrics.get('exception_code')})")

    def test_03_performance_metric(self):
        """测试 3: 验证稳定性采样耗时指标"""
        self.perceptor.poll_signals()
        summary = self.perceptor.get_performance_summary()
        self.assertLessEqual(summary["avg_duration_ms"], 5.0)

        print("\n--- [TEST 3: Stability Perceptor Performance Metric] ---")
        print(f"[PASS] 单次采样平均耗时: {summary['avg_duration_ms']:.3f}ms")


if __name__ == '__main__':
    unittest.main()
