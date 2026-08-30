"""
CyberSpine Milestone 1: Sensory Hot-Toggle Adversarial Stress Test Suite
Author: Challenger 2 (Empirical Challenger)
Target: BasePerceptor, IOPerceptorManager, SomaticPerceptorHub, CyberSpineAppBridge, RealAutonomousPacemaker
Focus: Concurrency, Rapid Toggling, Malformed/Unknown IDs, Full Sensory Deprivation with Active Pacemaker
"""
import sys
import time
import threading
import random
import unittest
from typing import List, Dict, Any

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.models.somatic_signals import RawSomaticSignal
from src.perceptors.base import BasePerceptor
from src.perceptors.io.io_manager import IOPerceptorManager
from src.perceptors.somatic_hub import SomaticPerceptorHub
from src.app.app_bridge import CyberSpineAppBridge
from src.pacing.real_pacemaker import RealAutonomousPacemaker, HeartbeatTickRecord


class TestChallengerSensoryHotToggleAdversarial(unittest.TestCase):
    """Milestone 1 对抗性挑战者压力测试套件"""

    def setUp(self):
        self.hub = SomaticPerceptorHub()
        self.bridge = CyberSpineAppBridge()
        self.known_plugin_ids = [
            "nerve.system.foreground_focus",
            "nerve.system.running_apps",
            "nerve.system.high_load",
            "nerve.system.homeostasis",
            "nerve.system.notifications",
            "nerve.system.stability",
            "nerve.network.health",
            "nerve.io.storage",
        ]

    def test_adv_01_rapid_back_to_back_toggle_single_thread(self):
        """[ADV-01] 高频连续极速切换 (200 次循环): 状态原子性与性能统计指标完整性"""
        for i in range(200):
            target_state = (i % 2 == 0)
            for pid in self.known_plugin_ids:
                res = self.hub.set_perceptor_enabled(pid, target_state)
                self.assertTrue(res, f"设置 {pid} -> {target_state} 失败")
                self.assertEqual(
                    self.hub.get_perceptor_enabled(pid),
                    target_state,
                    f"获取 {pid} 状态不匹配预期 {target_state}"
                )

        # 最终全部置为 True 并验证基线与性能统计
        for pid in self.known_plugin_ids:
            self.hub.set_perceptor_enabled(pid, True)
            self.assertTrue(self.hub.get_perceptor_enabled(pid))

        topo = self.hub.get_full_somatic_topology()
        self.assertEqual(len(topo["channels"]), 8)
        self.assertEqual(len(topo["performance_benchmarks"]), 7)
        for bench in topo["performance_benchmarks"]:
            self.assertIn("perceptor_id", bench)
            self.assertTrue(bench["enabled"])

    def test_adv_02_concurrent_multithreaded_rapid_toggling(self):
        """[ADV-02] 多线程高并发对抗切换 (8 线程并发启停 + 主线程高频轮询): 无死锁/无竞态崩溃"""
        stop_event = threading.Event()
        errors: List[Exception] = []

        def worker_toggle(worker_id: int):
            try:
                for _ in range(100):
                    if stop_event.is_set():
                        break
                    pid = random.choice(self.known_plugin_ids)
                    new_state = random.choice([True, False])
                    # 并发调用 Hub 与 Bridge
                    self.hub.set_perceptor_enabled(pid, new_state)
                    if worker_id % 2 == 0:
                        self.bridge.toggle_plugin(pid, new_state)
                    time.sleep(0.005)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker_toggle, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()

        # 主线程同时高频执行 poll_all_signals 与 get_dashboard_data
        poll_count = 0
        while any(t.is_alive() for t in threads):
            try:
                sigs = self.hub.poll_all_signals()
                self.assertIsInstance(sigs, list)
                dash = self.bridge.get_dashboard_data()
                self.assertIsInstance(dash, dict)
                poll_count += 1
                time.sleep(0.01)
            except Exception as e:
                errors.append(e)
                break

        for t in threads:
            t.join(timeout=3.0)

        self.assertEqual(len(errors), 0, f"并发对抗测试中捕获到异常: {errors}")
        self.assertGreaterEqual(poll_count, 5, "主线程轮询次数不足")

        # 验证测试后系统仍可恢复为完全健康状态
        for pid in self.known_plugin_ids:
            self.hub.set_perceptor_enabled(pid, True)
            self.bridge.toggle_plugin(pid, True)
        self.assertEqual(self.bridge.get_dashboard_data()["active_plugins_count"], 8)

    def test_adv_03_unknown_plugin_ids_and_malformed_inputs(self):
        """[ADV-03] 畸形与未知插件 ID 注入测试 (None, 伪造路径, SQL/脚本注入字符串, 越界类型)"""
        hashable_malformed_ids = [
            None,
            "",
            "   ",
            12345,
            3.14159,
            True,
            False,
            "nerve.invalid.fake_perceptor",
            "nerve.system.non_existent",
            "'; DROP TABLE sensors; --",
            "<script>alert(1)</script>",
            "\x00\x01\x02\xff",
            "NERVE.SYSTEM.FOREGROUND_FOCUS.UPPERCASE",
        ]

        for bad_id in hashable_malformed_ids:
            # 1. Hub set_perceptor_enabled 必须优雅返回 False，严禁抛出未捕获异常
            try:
                res_set = self.hub.set_perceptor_enabled(bad_id, True)  # type: ignore
                self.assertFalse(res_set, f"未知 ID [{bad_id}] set_perceptor_enabled 应返回 False")
            except Exception as e:
                self.fail(f"Hub.set_perceptor_enabled 在输入 [{bad_id}] 时崩溃: {e}")

            # 2. Hub get_perceptor_enabled 必须返回 None
            try:
                res_get = self.hub.get_perceptor_enabled(bad_id)  # type: ignore
                self.assertIsNone(res_get, f"未知 ID [{bad_id}] get_perceptor_enabled 应返回 None")
            except Exception as e:
                self.fail(f"Hub.get_perceptor_enabled 在输入 [{bad_id}] 时崩溃: {e}")

            # 3. Bridge toggle_plugin 必须返回 success=False 并附带错误信息
            try:
                res_toggle = self.bridge.toggle_plugin(bad_id, True)  # type: ignore
                self.assertFalse(res_toggle.get("success", True), f"Bridge toggle 应失败: {bad_id}")
                self.assertIn("error", res_toggle)
            except Exception as e:
                self.fail(f"Bridge.toggle_plugin 在输入 [{bad_id}] 时崩溃: {e}")

            # 4. Bridge install_plugin 必须返回 success=False
            try:
                res_inst = self.bridge.install_plugin(bad_id)  # type: ignore
                self.assertFalse(res_inst.get("success", True), f"Bridge install 应失败: {bad_id}")
                self.assertIn("error", res_inst)
            except Exception as e:
                self.fail(f"Bridge.install_plugin 在输入 [{bad_id}] 时崩溃: {e}")

    def test_adv_04_full_sensory_shutdown_with_active_pacemaker(self):
        """[ADV-04] 全感官极端剥夺与真实起搏器联动测试: 0 信号下心跳轮转、60s简报生成与动态恢复"""
        pacemaker = self.bridge.pacemaker
        initial_ticks = pacemaker._heartbeat_count

        # 1. 彻底关闭所有 8 大神经末梢探针
        for pid in self.known_plugin_ids:
            self.bridge.toggle_plugin(pid, False)

        dash_deprived = self.bridge.get_dashboard_data()
        self.assertEqual(dash_deprived["active_plugins_count"], 0, "全部关闭后活跃插件数必须为 0")

        # 2. 在全感官停用状态下，连续执行多次物理心跳采样循环，确保跨越 12 次心跳的小脑简报触发点
        ticks_to_boundary = 12 - (pacemaker._heartbeat_count % 12)
        if ticks_to_boundary == 0:
            ticks_to_boundary = 12
        for _ in range(ticks_to_boundary + 2):
            pacemaker._execute_single_physical_heartbeat()
            status = pacemaker.get_live_pacemaker_status()
            self.assertTrue(status["is_running"])
            self.assertGreater(status["total_heartbeats"], initial_ticks)
            
            # 校验最新一帧心跳记录
            last_tick = status["recent_ticks"][-1]
            self.assertIn("message", last_tick)
            self.assertIn("稳态心流观察中", last_tick["message"])

        # 3. 验证 60s 小脑宏观简报在全感官关闭下仍能正常聚合生成
        briefing = pacemaker.get_live_pacemaker_status()["latest_60s_briefing"]
        self.assertIn("过去 1 分钟", briefing)
        self.assertIn("系统处于稳态运行", briefing)

        # 4. 验证全感官关闭下 get_dashboard_data 与 trigger_live_cognitive_cycle 正常运行
        cycle_res = self.bridge.trigger_live_cognitive_cycle()
        self.assertTrue(cycle_res["success"])
        self.assertIn("proposed_action", cycle_res)

        # 5. 动态热恢复部分感官 (恢复通知与稳定性探针)
        self.bridge.toggle_plugin("nerve.system.notifications", True)
        self.bridge.toggle_plugin("nerve.system.stability", True)
        self.assertEqual(self.bridge.get_dashboard_data()["active_plugins_count"], 2)

        # 触发模拟事件并心跳
        self.bridge.hub.notifications_perceptor.mock_trigger_notification(source="RecoveryTest", count=3)
        pacemaker._execute_single_physical_heartbeat()
        last_tick_rec = pacemaker.get_live_pacemaker_status()["recent_ticks"][-1]
        self.assertIn("捕获到", last_tick_rec["message"])

        # 6. 完全恢复全部感官
        for pid in self.known_plugin_ids:
            self.bridge.toggle_plugin(pid, True)
        self.assertEqual(self.bridge.get_dashboard_data()["active_plugins_count"], 8)

    def test_adv_05_uninstalled_plugin_lifecycle_and_reinstall(self):
        """[ADV-05] 扩展插件生命周期对抗测试: 未安装禁止启用、安装依赖自检、重复安装幂等性"""
        ext_ids = ["nerve.visual.screen", "nerve.audio.whisper", "nerve.clipboard.flow"]

        for ext_id in ext_ids:
            # 确保初始为未安装
            self.bridge._plugins_state[ext_id]["installed"] = False
            self.bridge._plugins_state[ext_id]["enabled"] = False

            # 未安装直接启用 -> 必须拒绝
            toggle_fail = self.bridge.toggle_plugin(ext_id, True)
            self.assertFalse(toggle_fail["success"])
            self.assertIn("not installed", toggle_fail["error"])

            # 正常安装
            install_res1 = self.bridge.install_plugin(ext_id)
            self.assertTrue(install_res1["success"])
            self.assertTrue(install_res1["installed"])
            self.assertTrue(install_res1["enabled"])
            self.assertFalse(install_res1["already_installed"])
            self.assertTrue(install_res1["dependency_check"]["passed"])

            # 启用/停用循环
            tog_off = self.bridge.toggle_plugin(ext_id, False)
            self.assertTrue(tog_off["success"])
            self.assertFalse(tog_off["enabled"])

            tog_on = self.bridge.toggle_plugin(ext_id, True)
            self.assertTrue(tog_on["success"])
            self.assertTrue(tog_on["enabled"])

            # 重复安装 (幂等性) -> 应提示 already_installed=True 且不破坏已有状态
            install_res2 = self.bridge.install_plugin(ext_id)
            self.assertTrue(install_res2["success"])
            self.assertTrue(install_res2["already_installed"])
            self.assertTrue(install_res2["enabled"])

    def test_adv_06_dashboard_state_integrity_under_random_permutations(self):
        """[ADV-06] 随机开关排列组合下驾驶舱快照与数据契约一致性测试 (50 组随机排列)"""
        for trial in range(50):
            expected_enabled = 0
            for pid in self.known_plugin_ids:
                is_on = (random.random() > 0.5)
                self.bridge.toggle_plugin(pid, is_on)
                if is_on:
                    expected_enabled += 1

            dash = self.bridge.get_dashboard_data()
            self.assertEqual(
                dash["active_plugins_count"],
                expected_enabled,
                f"试验 #{trial}: 驾驶舱活跃插件数 ({dash['active_plugins_count']}) 与预期 ({expected_enabled}) 不一致"
            )
            # 验证 8 大通道基线结构全部健壮存在
            self.assertEqual(len(dash["somatic_channels"]), 8)

        # 恢复默认全开状态
        for pid in self.known_plugin_ids:
            self.bridge.toggle_plugin(pid, True)

    def test_adv_07_stress_continuous_poll_under_chaotic_toggling(self):
        """[ADV-07] 300 轮混沌启停下高频采样压力测试: 验证 0 崩溃与信号合法性"""
        for round_idx in range(300):
            # 随机挑选 1-3 个探针变更状态
            flip_targets = random.sample(self.known_plugin_ids, k=random.randint(1, 3))
            for pid in flip_targets:
                curr = self.hub.get_perceptor_enabled(pid)
                self.hub.set_perceptor_enabled(pid, not curr)

            # 偶尔注入模拟事件
            if round_idx % 20 == 0:
                self.hub.notifications_perceptor.mock_trigger_notification(source="ChaoticStress", count=1)
                self.hub.stability_perceptor.mock_trigger_crash_event(process_name="stress_test.exe")

            # 轮询
            signals = self.hub.poll_all_signals()
            self.assertIsInstance(signals, list)
            for s in signals:
                self.assertIsInstance(s, RawSomaticSignal)
                self.assertTrue(hasattr(s, "channel"))
                self.assertTrue(hasattr(s, "event_type"))
                self.assertTrue(hasattr(s, "timestamp"))

        # 测试完毕后恢复全部探针
        for pid in self.known_plugin_ids:
            self.hub.set_perceptor_enabled(pid, True)


if __name__ == '__main__':
    unittest.main()
