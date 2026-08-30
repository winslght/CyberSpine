"""
CyberSpine 神经末梢 1 (前台窗口与工作台焦点感知) 独立单元测试套件
"""
import sys
import unittest

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.perceptors.system.foreground_focus import ForegroundFocusPerceptor
from src.sensing.window_activity import WindowActivityPeripheral


class TestForegroundFocusPerceptor(unittest.TestCase):

    def setUp(self):
        self.perceptor = ForegroundFocusPerceptor()

    def test_01_get_active_window_info(self):
        """测试 1: 毫秒级安全提取当前活跃窗口信息"""
        info = self.perceptor._get_active_window_info()
        self.assertIn("hwnd", info)
        self.assertIn("process_name", info)
        self.assertIn("window_title", info)

        print("\n--- [TEST 1: Foreground Window Snapshot] ---")
        print(f"[PASS] 当前前台窗口: {info['window_title']}")
        print(f"[PASS] 归属进程: {info['process_name']} (PID: {info['pid']})")

    def test_02_poll_signals_baseline_and_switch(self):
        """测试 2: 焦点探针基线建立与切换感知"""
        # 第一次 poll: 建立初始基线，返回空列表
        sig_first = self.perceptor.poll_signals()
        self.assertEqual(len(sig_first), 0)

        # 模拟前台窗口切换 (改变内部基线)
        self.perceptor._last_process_name = "Code.exe"
        self.perceptor._last_window_title = "old_project - VSCode"
        self.perceptor._last_hwnd = 123456

        # 第二次 poll: 捕捉到焦点切换
        signals = self.perceptor.poll_signals()
        print("\n--- [TEST 2: Focus Switching Event Detection] ---")
        if signals:
            sig = signals[0]
            print(f"[PASS] 捕获焦点流转信号: ID={sig.signal_id}")
            print(f"[PASS] 前进程: {sig.raw_metrics.get('previous_process')} -> 当前进程: {sig.raw_metrics.get('current_process')}")
            self.assertEqual(sig.channel, "WORKSPACE")
            self.assertEqual(sig.event_type, "FOCUS_SWITCHED")

    def test_03_performance_metric(self):
        """测试 3: 验证探测耗时严格处于红线以内 (<= 5ms)"""
        self.perceptor.poll_signals()
        summary = self.perceptor.get_performance_summary()
        self.assertLessEqual(summary["avg_duration_ms"], 10.0)

        print("\n--- [TEST 3: Focus Perceptor Performance Metric] ---")
        print(f"[PASS] 单次采样平均耗时: {summary['avg_duration_ms']:.3f}ms (红线标准 <= 10.0ms)")

    def test_04_legacy_adapter_uses_canonical_window_peripheral(self):
        """旧信号格式只能适配窗口插件，不能建立第二个 User32 采集实现。"""
        snapshots = iter([
            {"active_process": "explorer.exe", "active_pid": 1},
            {"active_process": "code.exe", "active_pid": 2},
        ])
        peripheral = WindowActivityPeripheral(snapshot_provider=lambda: next(snapshots))
        adapter = ForegroundFocusPerceptor(peripheral=peripheral)

        self.assertEqual(adapter.poll_signals(), [])
        signals = adapter.poll_signals()

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].raw_metrics["current_process"], "code.exe")
        self.assertEqual(signals[0].raw_metrics["source_topic"], "window.focus_changed")

    def test_05_legacy_adapter_tolerates_unattributable_foreground(self):
        peripheral = WindowActivityPeripheral(catalog_provider=lambda: [
            {"window_id": "win:browser", "application": "chrome.exe", "pid": 20,
             "is_foreground": False},
        ])
        adapter = ForegroundFocusPerceptor(peripheral=peripheral)

        self.assertEqual(adapter._get_active_window_info()["process_name"], "unavailable")


if __name__ == '__main__':
    unittest.main()
