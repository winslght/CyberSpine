"""
CyberSpine 真实物理自主起搏器守护线程单元测试套件
"""
import sys
import os
import time
import unittest

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.pacing.real_pacemaker import RealAutonomousPacemaker
from src.app.app_bridge import CyberSpineAppBridge


class TestRealAutonomousPacemaker(unittest.TestCase):

    def setUp(self):
        self.pacemaker = RealAutonomousPacemaker(interval_seconds=1.0)
        self.bridge = CyberSpineAppBridge()

    def test_01_execute_physical_heartbeat(self):
        """测试 1: 真实执行单次物理硬件心跳采样与日志追加"""
        initial_count = self.pacemaker._heartbeat_count
        self.pacemaker._execute_single_physical_heartbeat()
        
        self.assertGreater(self.pacemaker._heartbeat_count, initial_count)
        self.assertTrue(os.path.exists(self.pacemaker.ticks_log_file))

        status = self.pacemaker.get_live_pacemaker_status()
        self.assertIn("total_heartbeats", status)
        self.assertIn("current_process", status)
        self.assertIn("current_dwell_seconds", status)
        self.assertGreater(len(status["recent_ticks"]), 0)

        print("\n--- [TEST 1: Real Physical Heartbeat Execution] ---")
        print(f"[PASS] 心跳计数: {status['total_heartbeats']} 次")
        print(f"[PASS] 当前前台: {status['current_process']} (驻留: {status['current_dwell_seconds']:.1f}s)")
        print(f"[PASS] 物理日志文件: {status['log_file_path']}")

    def test_02_cerebellar_60s_briefing_aggregation(self):
        """测试 2: 验证 12 次心跳后小脑自动生成 1 分钟世界简报"""
        for _ in range(12):
            self.pacemaker._execute_single_physical_heartbeat()

        status = self.pacemaker.get_live_pacemaker_status()
        self.assertIn("过去 1 分钟", status["latest_60s_briefing"])

        print("\n--- [TEST 2: Cerebellar 60s Briefing Generation] ---")
        print(f"[PASS] 小脑简报内容: {status['latest_60s_briefing']}")

    def test_03_bridge_pacemaker_integration(self):
        """测试 3: 验证 AppBridge 驾驶舱数据与真实起搏器无缝集成"""
        dash = self.bridge.get_dashboard_data()
        self.assertIn("pacemaker", dash)
        self.assertIn("total_heartbeats", dash["pacemaker"])
        self.assertEqual(dash["heartbeat_count"], dash["pacemaker"]["total_heartbeats"])

        print("\n--- [TEST 3: App Bridge Pacemaker Integration] ---")
        print(f"[PASS] 驾驶舱心跳同步: {dash['heartbeat_count']} 次")


if __name__ == '__main__':
    unittest.main()
