"""
CyberSpine 原生 WinUI 桌面应用程序 IPC 桥接层单元测试套件
"""
import sys
import unittest

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.app.app_bridge import CyberSpineAppBridge


class TestCyberSpineAppBridge(unittest.TestCase):

    def setUp(self):
        self.bridge = CyberSpineAppBridge()

    def test_01_get_dashboard_data(self):
        """测试 1: 获取神经驾驶舱实时数据快照"""
        data = self.bridge.get_dashboard_data()
        self.assertIn("uptime_seconds", data)
        self.assertIn("heartbeat_count", data)
        self.assertIn("somatic_channels", data)
        self.assertIn("latest_briefing", data)
        self.assertGreaterEqual(data["active_plugins_count"], 1)

        print("\n--- [TEST 1: Desktop App Dashboard Data IPC] ---")
        print(f"[PASS] 驾驶舱数据提取成功: Uptime={data['uptime_formatted']}, 活跃插件={data['active_plugins_count']}/{data['total_plugins_count']}")
        print(f"[PASS] 8大通道数: {len(data['somatic_channels'])}")

    def test_02_plugin_store_operations(self):
        """测试 2: 插件商店列表提取与物理一键启停/安装/依赖校验"""
        plugins = self.bridge.get_plugin_store()
        self.assertGreater(len(plugins), 0)

        # 1. 测试物理启停 (停用前台焦点探针)
        res = self.bridge.toggle_plugin("nerve.system.foreground_focus", False)
        self.assertTrue(res["success"])
        self.assertFalse(res["enabled"])
        self.assertTrue(res.get("hub_synced", False))
        # 物理验证 Hub 探针状态同步被停用
        self.assertFalse(self.bridge.hub.get_perceptor_enabled("nerve.system.foreground_focus"))
        self.assertFalse(self.bridge.hub.focus_perceptor.enabled)

        # 重新启用
        res_on = self.bridge.toggle_plugin("nerve.system.foreground_focus", True)
        self.assertTrue(res_on["success"])
        self.assertTrue(res_on["enabled"])
        self.assertTrue(self.bridge.hub.get_perceptor_enabled("nerve.system.foreground_focus"))
        self.assertTrue(self.bridge.hub.focus_perceptor.enabled)

        # 2. 测试未安装插件禁止直接启用
        toggle_uninstalled = self.bridge.toggle_plugin("nerve.audio.whisper", True)
        self.assertFalse(toggle_uninstalled["success"])
        self.assertIn("not installed", toggle_uninstalled["error"])

        # 3. 测试安装视觉神经节扩展插件 (包含真实物理依赖校验)
        inst_visual = self.bridge.install_plugin("nerve.visual.screen")
        self.assertTrue(inst_visual["success"])
        self.assertIn("dependency_check", inst_visual)
        self.assertTrue(inst_visual["dependency_check"]["passed"])
        self.assertGreater(len(inst_visual["dependency_check"]["checks"]), 0)

        # 4. 测试安装听觉与剪贴板扩展插件
        inst_audio = self.bridge.install_plugin("nerve.audio.whisper")
        self.assertTrue(inst_audio["success"])
        self.assertTrue(inst_audio["dependency_check"]["passed"])

        inst_clip = self.bridge.install_plugin("nerve.clipboard.flow")
        self.assertTrue(inst_clip["success"])
        self.assertTrue(inst_clip["dependency_check"]["passed"])

        # 5. 测试未知插件安装与启停
        unknown_toggle = self.bridge.toggle_plugin("nerve.unknown.plugin", True)
        self.assertFalse(unknown_toggle["success"])

        unknown_install = self.bridge.install_plugin("nerve.unknown.plugin")
        self.assertFalse(unknown_install["success"])

        print("\n--- [TEST 2: Plugin Store Physical Toggle & Dependency Preflight] ---")
        print(f"[PASS] 物理联动启停成功: Hub 同步={res.get('hub_synced')}")
        print(f"[PASS] 视觉插件依赖校验: {inst_visual['dependency_check']['summary']}")
        print(f"[PASS] 听觉插件依赖校验: {inst_audio['dependency_check']['summary']}")
        print(f"[PASS] 剪贴板插件依赖校验: {inst_clip['dependency_check']['summary']}")

    def test_03_ganglion_and_cortex_configs(self):
        """测试 3: 分脑模型状态与大脑配置持久化"""
        ganglions = self.bridge.get_ganglion_status()
        self.assertIn("midbrain", ganglions["models"])
        self.assertIn("visual", ganglions["models"])

        cortex = self.bridge.get_cortex_config()
        self.assertIn("provider", cortex)

        save_res = self.bridge.save_cortex_config({"provider": "DeepSeek-R1", "resonance_sensitivity": 90})
        self.assertTrue(save_res["success"])

        print("\n--- [TEST 3: Ganglion Hub & Cortex Config IPC] ---")
        print(f"[PASS] 中脑模型: {ganglions['models']['midbrain']['name']} ({ganglions['models']['midbrain']['token_per_sec']} Token/s)")
        print(f"[PASS] 大脑更新配置: DeepSeek-R1, 灵敏度 90%")

    def test_04_pulse_and_quiet_mode(self):
        """测试 4: 手动即时巡检与一键免打扰抑制"""
        pulse_res = self.bridge.trigger_manual_pulse()
        self.assertTrue(pulse_res["success"])

        quiet_res = self.bridge.apply_quiet_mode(300)
        self.assertTrue(quiet_res["success"])
        self.assertTrue(self.bridge.buffer.is_inhibited())

        print("\n--- [TEST 4: Manual Pulse & Downward Inhibition IPC] ---")
        print(f"[PASS] 手动即时巡检捕获电信号: {pulse_res['signals_count']} 个")
        print(f"[PASS] 成功激活 300s 免打扰下行抑制: is_inhibited={self.bridge.buffer.is_inhibited()}")

    def test_05_plugin_telemetry_audit(self):
        """测试 5: 插件启停与安装动作写入认知透视审计日志"""
        initial_count = len(self.bridge.telemetry.get_recent_frames())
        self.bridge.toggle_plugin("nerve.system.high_load", False)
        frames = self.bridge.telemetry.get_recent_frames()
        self.assertGreater(len(frames), initial_count)
        last_frame = frames[-1]
        self.assertIn("插件状态变更", last_frame["title"])
        self.assertIn("nerve.system.high_load", last_frame["message"])

        print("\n--- [TEST 5: Plugin Telemetry Audit Frames] ---")
        print(f"[PASS] 成功捕获透视日志帧: {last_frame['title']} | {last_frame['message']}")


if __name__ == '__main__':
    unittest.main()
