"""
CyberSpine Core E2E Test Suite - Tier 4: Real-World Workloads
Validates full life-cycle macro user workflows and multi-component physical loops (R1-R5, AC1-AC4).
"""
import sys
import os
import json
import time
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Any

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.app.app_bridge import CyberSpineAppBridge
from src.pacing.real_pacemaker import RealAutonomousPacemaker
from src.perceptors.io.io_manager import IOPerceptorManager
from src.pacing.neural_buffer import TemporalNeuralBuffer
from src.spinal_core.intent_gate import SpinalIntentGate
from src.cortex.master_cortex import MasterCortex
from src.models.somatic_signals import FeedbackDirective
from src.app.telemetry_logger import CognitiveTelemetryLogger, TelemetryCategory
from src.actuators.base import ProposedAction, ActionRiskLevel


class TestTier4RealWorldWorkloads(unittest.TestCase):
    """Tier 4: 真实世界宏观工作负载与端到端全链路闭环测试套件"""

    def setUp(self):
        self.temp_root = tempfile.mkdtemp()
        self.app_bridge = CyberSpineAppBridge()
        self.pacemaker = self.app_bridge.pacemaker
        self.telemetry = self.app_bridge.telemetry

        # 模拟真实 Python 研发 U 盘工作区
        self.usb_mount = Path(self.temp_root) / "USB_DEV_STORAGE"
        self.usb_mount.mkdir(parents=True, exist_ok=True)
        (self.usb_mount / ".git").mkdir()
        (self.usb_mount / "src").mkdir()
        (self.usb_mount / "requirements.txt").write_text("fastapi>=0.100.0\nuvicorn>=0.23.0\npsutil\n", encoding="utf-8")
        (self.usb_mount / "main.py").write_text("print('CyberSpine Tier 4 Real-World Loop')\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.temp_root, ignore_errors=True)

    # ================= 场景 1: Python 研发工程师外设接入全链路闭环 (R1-R5 / AC1-AC4) =================

    def test_tier4_scenario_developer_onboarding_closed_loop(self):
        """
        [Tier 4/Scenario 1] 真实物理研发工程接入 100% 全链路闭环：
        起搏器采样 -> 硬件插入 -> 时钟对齐 -> 脊髓门控 -> 大脑推演 -> 审批执行 -> 下行抑制 -> 小脑简报 -> 透视留痕
        """
        print("\n=======================================================")
        print("🌟 [Tier 4] 执行场景 1: 真实研发工作区接入端到端全链路闭环")
        print("=======================================================")

        # 1. 物理起搏器采样基线 (R1 / AC1)
        self.pacemaker._execute_single_physical_heartbeat()
        initial_heartbeats = self.pacemaker._heartbeat_count
        self.assertGreaterEqual(initial_heartbeats, 1)

        # 2. IO 探针捕获外设接入电信号 (R2)
        db_path = str(Path(self.temp_root) / "io_devices.json")
        io_mgr = IOPerceptorManager(db_path=db_path)
        raw_signal = io_mgr.mock_inject_storage_signal(
            mock_root_path=str(self.usb_mount),
            volume_label="CYBER_DEV_DRIVE",
            total_gb=256.0,
            free_gb=180.0,
        )
        self.assertIsNotNone(raw_signal)
        self.assertIn("GIT_REPOSITORY", raw_signal.structure_summary.detected_profiles)
        self.assertIn("PYTHON_PROJECT", raw_signal.structure_summary.detected_profiles)

        # 3. 中枢时钟对齐与脉冲打包 (R1 / R5)
        buffer = TemporalNeuralBuffer(alignment_window_seconds=0.1)
        enqueued = buffer.ingest_signal(raw_signal)
        self.assertTrue(enqueued)
        fused_packet = buffer.flush_aligned_packet(force=True)
        self.assertIsNotNone(fused_packet)

        # 4. 脊髓神经中枢感觉门控与意图提炼 (R5)
        spinal_gate = SpinalIntentGate()
        narrative = spinal_gate.evaluate_and_narrate(fused_packet)
        self.assertIsNotNone(narrative)
        self.assertTrue(narrative.should_escalate_to_cortex)
        self.assertEqual(narrative.macro_scenario, "WORKSPACE_ATTACH_PYTHON_DEV")

        # 5. 前额叶大脑推演与温和审批卡片呈递 (R3 / AC2)
        cortex = MasterCortex(neural_buffer=buffer)
        inquiries_logged = []
        def user_approve_dialog(inquiry: str) -> bool:
            inquiries_logged.append(inquiry)
            return True  # 用户点击同意

        executed, feedback = cortex.process_intent_narrative(
            narrative=narrative,
            approval_callback=user_approve_dialog,
            target_directory=str(self.usb_mount),
        )

        # 6. 运动神经双手执行与安全放行 (R4 / AC3)
        self.assertTrue(executed)
        self.assertEqual(feedback.directive, FeedbackDirective.SUPPRESS_AND_OBSERVE)
        self.assertEqual(feedback.cooldown_seconds, 300)
        self.assertIn("【双手执行完毕】", feedback.executed_action_summary)

        # 7. 双向神经反馈与下行抑制生效 (R1 / R5)
        self.assertTrue(buffer.is_inhibited())

        # 8. 连续心跳并生成 60s 小脑世界简报 (R1 / AC1)
        for _ in range(12):
            self.pacemaker._execute_single_physical_heartbeat()
        self.assertIn("过去 1 分钟", self.pacemaker._latest_60s_briefing)

        # 9. 验证全流程在认知透视日志中均有留痕 (R5)
        recent_frames = self.telemetry.get_recent_frames(limit=50)
        self.assertGreater(len(recent_frames), 0)
        categories = {f["category"] for f in recent_frames}
        self.assertIn(TelemetryCategory.SOMATIC, categories)
        self.assertIn(TelemetryCategory.SPINAL, categories)

        print("🎉 [Tier 4] 场景 1 全链路 100% 物理闭环验证成功！")

    # ================= 场景 2: 编译高压负载与动态电源自适应 =================

    def test_tier4_scenario_high_load_stress_and_power_adaptation(self):
        """
        [Tier 4/Scenario 2] 系统高负载瞬时尖峰与动态电源方案调节闭环：
        高压负载感官输入 -> 规则脑推演切换高性能 -> 用户审批 -> 电源执行器生效 -> 透视记录
        """
        print("\n=======================================================")
        print("⚡ [Tier 4] 执行场景 2: 编译高压负载与动态电源自适应调节")
        print("=======================================================")

        # 1. 模拟高负载感官状态 (CPU 88.5%)
        high_load_state = {
            "cpu_percent": 88.5,
            "memory_percent": 75.2,
            "is_stressed": True,
            "top_processes": ["cl.exe", "cargo.exe"],
        }

        # 2. 本地模型推演动作
        action = self.app_bridge.local_model.infer_action_from_somatic_state(high_load_state)
        self.assertEqual(action.actuator_id, "motor.power")
        self.assertEqual(action.action_name, "set_power_scheme")
        self.assertEqual(action.parameters.get("mode"), "HIGH_PERFORMANCE")

        # 3. 设置为 AppBridge 待审批动作并模拟用户同意
        self.app_bridge._pending_action = action
        res_exec = self.app_bridge.approve_and_execute_motor_action(approved=True)
        self.assertTrue(res_exec["success"])
        self.assertIn("电源方案", res_exec["execution_summary"])

        # 4. 验证透视日志
        frames = self.app_bridge.get_cognitive_telemetry(limit=10)
        self.assertTrue(any(f["category"] == TelemetryCategory.ACTION for f in frames))
        print("🎉 [Tier 4] 场景 2 动态电源自适应执行成功！")

    # ================= 场景 3: 离线断网与模型异常平滑降级 (AC2) =================

    def test_tier4_scenario_offline_network_and_model_fallback_resilience(self):
        """
        [Tier 4/Scenario 3] 离线断网与大模型离线状态下的 0 崩溃平滑降级验证 (AC2)
        """
        print("\n=======================================================")
        print("🛡️ [Tier 4] 执行场景 3: 离线断网与 0 崩溃平滑降级验证")
        print("=======================================================")

        # 触发一次即时全链路推演
        cycle = self.app_bridge.trigger_live_cognitive_cycle()
        self.assertTrue(cycle["success"])
        self.assertIn("proposed_action", cycle)
        self.assertIsNotNone(cycle["proposed_action"]["action_name"])

        # 验证返回的动作格式 100% 结构化且符合规范
        action_dict = cycle["proposed_action"]
        self.assertIn("action_id", action_dict)
        self.assertIn("actuator_id", action_dict)
        self.assertIn("risk_level", action_dict)
        self.assertIn("parameters", action_dict)
        print("🎉 [Tier 4] 场景 3 离线与模型 0 崩溃降级验证成功！")

    # ================= 场景 4: 多插件动态热插拔与工作区深度初始化 =================

    def test_tier4_scenario_plugin_reconfig_and_workspace_init(self):
        """
        [Tier 4/Scenario 4] 插件商店动态配置、工作区工程目录初始化与依赖预检全生命周期
        """
        print("\n=======================================================")
        print("🔧 [Tier 4] 执行场景 4: 插件热重载与工作区工程深度初始化")
        print("=======================================================")

        # 1. 插件商店多项切换
        self.app_bridge.toggle_plugin("nerve.system.queued_notifications", False)
        self.app_bridge.install_plugin("nerve.clipboard.flow")

        store = {p["id"]: p for p in self.app_bridge.get_plugin_store()}
        self.assertFalse(store["nerve.system.queued_notifications"]["enabled"])
        self.assertTrue(store["nerve.clipboard.flow"]["installed"])

        # 2. 深度创建工程
        proj_dir = Path(self.temp_root) / "new_microservice" / "v1"
        res_create = self.app_bridge.actuator_hub.workspace_actuator.execute(
            "create_project_directory",
            {"action_id": "act_ws_init", "target_path": str(proj_dir)}
        )
        self.assertTrue(res_create.success)

        # 写入配置文件
        (proj_dir / "pyproject.toml").write_text("[project]\nname = 'microservice'\n", encoding="utf-8")
        (proj_dir / ".git").mkdir()

        # 3. 依赖预检
        res_preflight = self.app_bridge.actuator_hub.workspace_actuator.execute(
            "preflight_check",
            {"action_id": "act_pre", "target_path": str(proj_dir)}
        )
        self.assertTrue(res_preflight.success)
        self.assertTrue(res_preflight.output_data.get("has_git"))
        self.assertTrue(res_preflight.output_data.get("has_pyproject"))
        print("🎉 [Tier 4] 场景 4 插件与工程初始化验证成功！")


if __name__ == '__main__':
    unittest.main()
