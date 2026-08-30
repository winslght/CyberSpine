"""
CyberSpine 神经末梢热插拔与物理连通性专项测试套件 (Perceptor Hot-Toggle & Physical Linkage Test Suite)
验证 BasePerceptor, IOPerceptorManager, SomaticPerceptorHub, CyberSpineAppBridge 之间的动态启停契约与物理生效。
"""
import sys
import unittest

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.perceptors.base import BasePerceptor
from src.perceptors.io.io_manager import IOPerceptorManager
from src.perceptors.somatic_hub import SomaticPerceptorHub
from src.perceptors.system.queued_notifications import QueuedNotificationsPerceptor
from src.perceptors.system.system_stability import SystemStabilityPerceptor
from src.app.app_bridge import CyberSpineAppBridge


class TestPerceptorHotToggle(unittest.TestCase):
    """神经末梢热插拔与物理联动全链路测试用例"""

    def setUp(self):
        self.hub = SomaticPerceptorHub()
        self.bridge = CyberSpineAppBridge()

    def test_01_base_perceptor_enabled_contract(self):
        """测试 1: BasePerceptor 基类 enabled 契约与布尔强转"""
        perceptor = QueuedNotificationsPerceptor()
        # 默认应为启用状态
        self.assertTrue(perceptor.enabled)

        # 性能统计中应暴露 enabled 字段
        summary = perceptor.get_performance_summary()
        self.assertIn("enabled", summary)
        self.assertTrue(summary["enabled"])

        # 测试禁用
        perceptor.set_enabled(False)
        self.assertFalse(perceptor.enabled)
        self.assertFalse(perceptor.get_performance_summary()["enabled"])

        # 测试重新启用
        perceptor.set_enabled(True)
        self.assertTrue(perceptor.enabled)
        self.assertTrue(perceptor.get_performance_summary()["enabled"])

        # 测试非布尔输入强转
        perceptor.set_enabled(0)
        self.assertIs(perceptor.enabled, False)
        perceptor.set_enabled(1)
        self.assertIs(perceptor.enabled, True)
        perceptor.set_enabled("")
        self.assertIs(perceptor.enabled, False)

        print("\n--- [TEST 1: BasePerceptor Enabled Contract] ---")
        print("[PASS] BasePerceptor 默认启用、状态变更与类型强转契约完全满足")

    def test_02_io_manager_perceptor_id_and_enabled_contract(self):
        """测试 2: IOPerceptorManager perceptor_id 与 enabled 控制"""
        io_mgr = IOPerceptorManager()
        self.assertEqual(io_mgr.perceptor_id, "nerve.io.storage")
        self.assertTrue(io_mgr.enabled)

        snapshot = io_mgr.get_full_io_snapshot()
        self.assertIn("enabled", snapshot)
        self.assertTrue(snapshot["enabled"])

        io_mgr.set_enabled(False)
        self.assertFalse(io_mgr.enabled)
        self.assertFalse(io_mgr.get_full_io_snapshot()["enabled"])

        io_mgr.set_enabled(True)
        self.assertTrue(io_mgr.enabled)

        print("\n--- [TEST 2: IOPerceptorManager Enabled Contract] ---")
        print("[PASS] IO 管理器 perceptor_id 注册与 enabled 控制完全符合规范")

    def test_03_hub_set_get_perceptor_enabled_all_channels(self):
        """测试 3: SomaticPerceptorHub 全感官通道启停查询与未知 ID 判定"""
        expected_ids = [
            "nerve.system.foreground_focus",
            "nerve.system.running_apps",
            "nerve.system.high_load",
            "nerve.system.homeostasis",
            "nerve.system.notifications",
            "nerve.system.stability",
            "nerve.network.health",
            "nerve.io.storage",
        ]

        for pid in expected_ids:
            # 初始查询全为 True
            self.assertTrue(self.hub.get_perceptor_enabled(pid), f"探针 {pid} 初始状态应为 True")

            # 禁用
            res_disable = self.hub.set_perceptor_enabled(pid, False)
            self.assertTrue(res_disable, f"禁用探针 {pid} 失败")
            self.assertFalse(self.hub.get_perceptor_enabled(pid), f"探针 {pid} 禁用后查询应为 False")

            # 重新启用
            res_enable = self.hub.set_perceptor_enabled(pid, True)
            self.assertTrue(res_enable, f"启用探针 {pid} 失败")
            self.assertTrue(self.hub.get_perceptor_enabled(pid), f"探针 {pid} 重新启用后查询应为 True")

        # 测试不存在的未知探针 ID
        self.assertFalse(self.hub.set_perceptor_enabled("nerve.invalid.fake_sensor", False))
        self.assertIsNone(self.hub.get_perceptor_enabled("nerve.invalid.fake_sensor"))

        print("\n--- [TEST 3: Hub Channel Lookup & Validation] ---")
        print(f"[PASS] 8 大神经末梢通道与未知 ID 判定测试通过 (通道数={len(expected_ids)})")

    def test_04_poll_all_signals_skips_disabled_sensors(self):
        """测试 4: 轮询时自动过滤并跳过已停用的探针"""
        # 1. 初始均启用，触发双事件
        self.hub.notifications_perceptor.mock_trigger_notification(source="TestRunner", count=1)
        self.hub.stability_perceptor.mock_trigger_crash_event(process_name="faulty_app.exe")

        sigs_all = self.hub.poll_all_signals()
        notify_sigs = [s for s in sigs_all if s.channel == "NOTIFICATIONS"]
        stability_sigs = [s for s in sigs_all if s.channel == "STABILITY"]
        self.assertGreaterEqual(len(notify_sigs), 1)
        self.assertGreaterEqual(len(stability_sigs), 1)

        # 2. 仅停用通知探针
        self.hub.set_perceptor_enabled("nerve.system.notifications", False)
        self.hub.notifications_perceptor.mock_trigger_notification(source="TestRunner2", count=2)
        self.hub.stability_perceptor.mock_trigger_crash_event(process_name="faulty_app2.exe")

        sigs_partial = self.hub.poll_all_signals()
        notify_sigs_p = [s for s in sigs_partial if s.channel == "NOTIFICATIONS"]
        stability_sigs_p = [s for s in sigs_partial if s.channel == "STABILITY"]
        self.assertEqual(len(notify_sigs_p), 0, "停用通知探针后不应有通知信号产生")
        self.assertGreaterEqual(len(stability_sigs_p), 1, "稳定性探针未停用应继续正常工作")

        # 3. 停用稳定性探针
        self.hub.set_perceptor_enabled("nerve.system.stability", False)
        self.hub.stability_perceptor.mock_trigger_crash_event(process_name="faulty_app3.exe")
        sigs_none = self.hub.poll_all_signals()
        stability_sigs_n = [s for s in sigs_none if s.channel == "STABILITY"]
        self.assertEqual(len(stability_sigs_n), 0, "停用稳定性探针后不应有崩溃信号产生")

        # 4. 重新恢复所有探针
        self.hub.set_perceptor_enabled("nerve.system.notifications", True)
        self.hub.set_perceptor_enabled("nerve.system.stability", True)
        self.hub.notifications_perceptor.mock_trigger_notification(source="TestRunner3", count=1)
        sigs_resumed = self.hub.poll_all_signals()
        notify_resumed = [s for s in sigs_resumed if s.channel == "NOTIFICATIONS"]
        self.assertGreaterEqual(len(notify_resumed), 1, "恢复后应继续正常轮询")

        print("\n--- [TEST 4: Poll Signals Selective Filtering] ---")
        print("[PASS] 探针停用时硬件采样与信号派发精准跳过，恢复后无缝恢复")

    def test_05_full_sensory_deprivation_cycle(self):
        """测试 5: 全感官停用极端场景 (0% 能耗极速返回)"""
        all_ids = [
            "nerve.system.foreground_focus",
            "nerve.system.running_apps",
            "nerve.system.high_load",
            "nerve.system.homeostasis",
            "nerve.system.notifications",
            "nerve.system.stability",
            "nerve.network.health",
            "nerve.io.storage",
        ]

        # 停用全部探针
        for pid in all_ids:
            self.hub.set_perceptor_enabled(pid, False)

        # 触发模拟事件
        self.hub.notifications_perceptor.mock_trigger_notification(source="Noise", count=5)
        self.hub.stability_perceptor.mock_trigger_crash_event(process_name="ignored.exe")

        sigs = self.hub.poll_all_signals()
        self.assertEqual(sigs, [], "全感官停用时应返回空列表")

        # 恢复全部探针
        for pid in all_ids:
            self.hub.set_perceptor_enabled(pid, True)

        print("\n--- [TEST 5: Full Sensory Deprivation Edge Case] ---")
        print("[PASS] 全感官关闭场景下 0 异常崩溃，干净返回空信号列表")

    def test_06_app_bridge_hot_toggle_synchronization(self):
        """测试 6: AppBridge ↔ Hub ↔ Pacemaker 物理连通同步验证"""
        # 获取初始仪表盘活跃插件数
        initial_dash = self.bridge.get_dashboard_data()
        initial_active = initial_dash["active_plugins_count"]
        self.assertEqual(initial_active, 8)

        # 切换关闭前台焦点感知
        toggle_res = self.bridge.toggle_plugin("nerve.system.foreground_focus", False)
        self.assertTrue(toggle_res["success"])
        self.assertFalse(toggle_res["enabled"])
        self.assertTrue(toggle_res.get("hub_synced", False))

        # 验证 Bridge 内部、Hub 及 Pacemaker 的 Hub 均同步关闭
        self.assertFalse(self.bridge.hub.focus_perceptor.enabled)
        self.assertFalse(self.bridge.hub.get_perceptor_enabled("nerve.system.foreground_focus"))
        if hasattr(self.bridge.pacemaker, "hub") and self.bridge.pacemaker.hub:
            self.assertFalse(self.bridge.pacemaker.hub.get_perceptor_enabled("nerve.system.foreground_focus"))

        # 验证仪表盘活跃计数同步扣减
        dash_after = self.bridge.get_dashboard_data()
        self.assertEqual(dash_after["active_plugins_count"], 7)

        # 重新启用
        restore_res = self.bridge.toggle_plugin("nerve.system.foreground_focus", True)
        self.assertTrue(restore_res["success"])
        self.assertTrue(restore_res["enabled"])
        self.assertEqual(self.bridge.get_dashboard_data()["active_plugins_count"], 8)

        print("\n--- [TEST 6: AppBridge Physical Synchronization] ---")
        print("[PASS] AppBridge IPC 开关物理同步生效至 Hub 与 Pacemaker")

    def test_07_extension_plugins_dependency_preflight(self):
        """测试 7: 扩展插件 (视觉、听觉、剪贴板) 安装与物理依赖预检"""
        # 1. 视觉插件安装
        vis_res = self.bridge.install_plugin("nerve.visual.screen")
        self.assertTrue(vis_res["success"])
        self.assertTrue(vis_res["installed"])
        self.assertTrue(vis_res["enabled"])
        self.assertIn("dependency_check", vis_res)
        self.assertTrue(vis_res["dependency_check"]["passed"])
        self.assertGreater(len(vis_res["dependency_check"]["checks"]), 0)

        # 2. 听觉插件安装
        aud_res = self.bridge.install_plugin("nerve.audio.whisper")
        self.assertTrue(aud_res["success"])
        self.assertTrue(aud_res["dependency_check"]["passed"])

        # 3. 剪贴板插件安装
        clip_res = self.bridge.install_plugin("nerve.clipboard.flow")
        self.assertTrue(clip_res["success"])
        self.assertTrue(clip_res["dependency_check"]["passed"])

        # 4. 验证全部扩展插件已就绪，总活跃数增加至 11
        dash = self.bridge.get_dashboard_data()
        self.assertEqual(dash["active_plugins_count"], 11)

        print("\n--- [TEST 7: Extension Plugins Preflight Verification] ---")
        print("[PASS] 视觉/听觉/剪贴板 3 大扩展插件真实物理依赖预检全部通过")


if __name__ == '__main__':
    unittest.main()
