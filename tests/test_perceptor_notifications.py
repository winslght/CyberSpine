"""
CyberSpine 神经末梢 5 (排队通知感知) 独立单元测试套件
"""
import sys
import unittest

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.perceptors.system.queued_notifications import QueuedNotificationsPerceptor


class TestQueuedNotificationsPerceptor(unittest.TestCase):

    def setUp(self):
        self.perceptor = QueuedNotificationsPerceptor()

    def test_01_get_baseline(self):
        """测试 1: 提取系统通知队列基线"""
        baseline = self.perceptor.get_baseline()
        self.assertIn("unread_notifications", baseline)

        print("\n--- [TEST 1: Queued Notifications Baseline] ---")
        print(f"[PASS] 当前排队未读通知数: {baseline['unread_notifications']}")

    def test_02_poll_signals_on_new_notification(self):
        """测试 2: 模拟收到新通知并产生电信号"""
        # 模拟外部新通知到达
        self.perceptor.mock_trigger_notification(source="Feishu", title="New Task", count=2)
        signals = self.perceptor.poll_signals()

        self.assertEqual(len(signals), 1)
        sig = signals[0]
        self.assertEqual(sig.channel, "NOTIFICATIONS")
        self.assertEqual(sig.event_type, "UNREAD_NOTIFICATIONS_QUEUED")
        self.assertEqual(sig.raw_metrics.get("new_arrived"), 2)

        print("\n--- [TEST 2: Notification Signal Emission] ---")
        print(f"[PASS] 捕获排队通知信号: ID={sig.signal_id} (新增未读={sig.raw_metrics.get('new_arrived')})")

    def test_03_performance_metric(self):
        """测试 3: 验证通知采样耗时指标"""
        self.perceptor.poll_signals()
        summary = self.perceptor.get_performance_summary()
        self.assertLessEqual(summary["avg_duration_ms"], 5.0)

        print("\n--- [TEST 3: Notification Perceptor Performance Metric] ---")
        print(f"[PASS] 单次采样平均耗时: {summary['avg_duration_ms']:.3f}ms")


if __name__ == '__main__':
    unittest.main()
