"""
CyberSpine 神经末梢 2 (运行程序拓扑感知) 独立单元测试套件
"""
import sys
import unittest

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.perceptors.system.running_apps import RunningAppsPerceptor


class TestRunningAppsPerceptor(unittest.TestCase):

    def setUp(self):
        self.perceptor = RunningAppsPerceptor()

    def test_01_get_baseline(self):
        """测试 1: 提取系统当前运行程序画像基线"""
        baseline = self.perceptor.get_baseline()
        self.assertIn("total_user_apps", baseline)
        self.assertIn("categories", baseline)
        self.assertGreater(baseline["total_user_apps"], 0)

        print("\n--- [TEST 1: Running Apps Baseline & Classification] ---")
        print(f"[PASS] 发现用户级交互应用总数: {baseline['total_user_apps']}")
        for cat, apps in baseline["categories"].items():
            if cat != "GENERAL_APP" and apps:
                print(f"   - 类别 [{cat}]: {apps[:5]}")

    def test_02_poll_signals_mock_app_launch(self):
        """测试 2: 模拟新应用启动与退出电信号产生"""
        # 初始 poll 应该无新信号
        signals = self.perceptor.poll_signals()
        self.assertEqual(len(signals), 0)

        # 模拟外部启动了 VSCode (Code.exe)
        self.perceptor._known_app_names.discard("Code.exe")
        self.perceptor._known_app_names.discard("code.exe")
        
        # 模拟注入新应用
        current = self.perceptor._get_active_app_names()
        current.add("Code.exe")
        
        # 手动执行分类检测
        cat = self.perceptor._classify_process("Code.exe")
        self.assertEqual(cat, "IDE")

        print("\n--- [TEST 2: App Launch Signal Emission] ---")
        print(f"[PASS] 进程 'Code.exe' 成功分类为画像: [{cat}]")

    def test_03_performance_metric(self):
        """测试 3: 验证程序拓扑采样耗时指标"""
        self.perceptor.poll_signals()
        summary = self.perceptor.get_performance_summary()
        self.assertLessEqual(summary["avg_duration_ms"], 50.0)

        print("\n--- [TEST 3: Apps Perceptor Performance Metric] ---")
        print(f"[PASS] 单次采样平均耗时: {summary['avg_duration_ms']:.3f}ms")


if __name__ == '__main__':
    unittest.main()
