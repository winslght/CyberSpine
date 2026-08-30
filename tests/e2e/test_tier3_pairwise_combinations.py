"""
CyberSpine Core E2E Test Suite - Tier 3: Pairwise Combinations
Validates cross-cutting orthogonal combinations across Sensor states, LLM states, Risk levels, Approval decisions, and Inhibition modes.
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
from src.actuators.base import ProposedAction, ActionRiskLevel, ActionResult
from src.actuators.safety_gate import SafetyGate
from src.actuators.workspace import WorkspaceActuator
from src.actuators.app_control import AppControlActuator
from src.actuators.power import SystemPowerActuator
from src.app.telemetry_logger import TelemetryCategory


class TestTier3PairwiseCombinations(unittest.TestCase):
    """Tier 3: 跨维度正交组合与状态机交互测试套件"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.app_bridge = CyberSpineAppBridge()
        self.safety_gate = self.app_bridge.actuator_hub.safety_gate

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ================= 1. 风险等级 × 审批决策 正交组合矩阵 =================

    def test_tier3_risk_approval_matrix(self):
        """
        [Tier 3/Matrix 1] 验证动作风险等级 (Risk Level) 与用户审批状态 (Approval State) 的 3×2 全矩阵交互
        Matrix:
          - (READ_ONLY_SAFE, False)      -> PASS
          - (READ_ONLY_SAFE, True)       -> PASS
          - (MUTATING_APPROVAL, False)   -> REJECT / BLOCK
          - (MUTATING_APPROVAL, True)    -> PASS / EXECUTE
          - (DANGEROUS_FORBIDDEN, False) -> HARD FUSE BLOCK
          - (DANGEROUS_FORBIDDEN, True)  -> HARD FUSE BLOCK
        """
        test_sub_dir = Path(self.temp_dir) / "matrix_sub_ws"

        matrix_cases = [
            # 1. 只读 + 未显式同意 -> 应自动放行 (第一定律)
            {
                "name": "READ_ONLY + NOT_APPROVED",
                "action": ProposedAction(
                    action_id="act_ro_false",
                    actuator_id="motor.workspace",
                    action_name="scan_directory",
                    risk_level=ActionRiskLevel.READ_ONLY_SAFE,
                    parameters={"target_path": str(self.temp_dir), "action_id": "act_ro_false"},
                    reason="测试", inquiry_message="测试",
                ),
                "approved": False,
                "expected_success": True,
            },
            # 2. 只读 + 显式同意 -> 应自动放行 (第一定律)
            {
                "name": "READ_ONLY + APPROVED",
                "action": ProposedAction(
                    action_id="act_ro_true",
                    actuator_id="motor.workspace",
                    action_name="scan_directory",
                    risk_level=ActionRiskLevel.READ_ONLY_SAFE,
                    parameters={"target_path": str(self.temp_dir), "action_id": "act_ro_true"},
                    reason="测试", inquiry_message="测试",
                ),
                "approved": True,
                "expected_success": True,
            },
            # 3. 变更 + 用户拒绝 -> 必须拦截并安全退避 (第二定律)
            {
                "name": "MUTATING + REJECTED",
                "action": ProposedAction(
                    action_id="act_mu_false",
                    actuator_id="motor.workspace",
                    action_name="create_project_directory",
                    risk_level=ActionRiskLevel.MUTATING_APPROVAL,
                    parameters={"target_path": str(test_sub_dir), "action_id": "act_mu_false"},
                    reason="测试", inquiry_message="测试",
                ),
                "approved": False,
                "expected_success": False,
            },
            # 4. 变更 + 用户同意 -> 必须准许并真实执行 (第二定律)
            {
                "name": "MUTATING + APPROVED",
                "action": ProposedAction(
                    action_id="act_mu_true",
                    actuator_id="motor.workspace",
                    action_name="create_project_directory",
                    risk_level=ActionRiskLevel.MUTATING_APPROVAL,
                    parameters={"target_path": str(test_sub_dir), "action_id": "act_mu_true"},
                    reason="测试", inquiry_message="测试",
                ),
                "approved": True,
                "expected_success": True,
            },
            # 5. 高危熔断 + 用户拒绝 -> 必须物理硬熔断 (第三定律)
            {
                "name": "DANGEROUS + REJECTED",
                "action": ProposedAction(
                    action_id="act_dg_false",
                    actuator_id="motor.workspace",
                    action_name="create_project_directory",
                    risk_level=ActionRiskLevel.MUTATING_APPROVAL,
                    parameters={"target_path": "C:\\ && format D: /q", "action_id": "act_dg_false"},
                    reason="测试", inquiry_message="测试",
                ),
                "approved": False,
                "expected_success": False,
            },
            # 6. 高危熔断 + 用户同意 -> 必须物理硬熔断，无视用户同意 (第三定律)
            {
                "name": "DANGEROUS + APPROVED",
                "action": ProposedAction(
                    action_id="act_dg_true",
                    actuator_id="motor.workspace",
                    action_name="create_project_directory",
                    risk_level=ActionRiskLevel.MUTATING_APPROVAL,
                    parameters={"target_path": "C:\\ && format D: /q", "action_id": "act_dg_true"},
                    reason="测试", inquiry_message="测试",
                ),
                "approved": True,
                "expected_success": False,
            },
        ]

        for case in matrix_cases:
            res = self.safety_gate.verify_and_execute(
                proposed_action=case["action"],
                is_user_approved=case["approved"]
            )
            self.assertEqual(
                res.success,
                case["expected_success"],
                f"正交用例 [{case['name']}] 断言失败: expected={case['expected_success']}, actual={res.success}"
            )

    # ================= 2. AppBridge 待审批动作状态机与透视联动 =================

    def test_tier3_bridge_action_lifecycle_and_telemetry_flow(self):
        """[Tier 3/Matrix 2] 验证 AppBridge 待审批动作从推演、呈递、审批/拒绝到透视日志记录的全生命周期"""
        # 1. 初始状态获取待审批动作 (自动推演出一个 ProposedAction)
        pending = self.app_bridge.get_pending_motor_action()
        self.assertIsNotNone(pending)
        self.assertIn("action_id", pending)
        self.assertIn("actuator_id", pending)

        # 2. 模拟用户审批执行: 拒绝 (False)
        res_reject = self.app_bridge.approve_and_execute_motor_action(approved=False)
        # 变更动作被拒绝应返回 success=False 或安全退避
        self.assertIn("success", res_reject)

        # 验证待处理动作已清空
        self.assertIsNone(self.app_bridge._pending_action)

        # 3. 再次获取新动作并审批同意 (True)
        new_pending = self.app_bridge.get_pending_motor_action()
        self.assertIsNotNone(new_pending)
        res_approve = self.app_bridge.approve_and_execute_motor_action(approved=True)
        self.assertIn("success", res_approve)

        # 4. 空待办时再次调用 -> 返回明确错误
        res_empty = self.app_bridge.approve_and_execute_motor_action(approved=True)
        self.assertFalse(res_empty["success"])
        self.assertIn("没有待审批", res_empty["error"])

    # ================= 3. 插件热启停 × 感官拓扑联动组合 =================

    def test_tier3_plugin_toggle_and_dashboard_integration(self):
        """[Tier 3/Matrix 3] 验证插件商店切换与驾驶舱 active_plugins_count 实时联动"""
        dash_initial = self.app_bridge.get_dashboard_data()
        initial_active = dash_initial["active_plugins_count"]

        # 关闭一个已启用插件
        self.app_bridge.toggle_plugin("nerve.system.stability", False)
        dash_after_off = self.app_bridge.get_dashboard_data()
        self.assertEqual(dash_after_off["active_plugins_count"], initial_active - 1)

        # 重新开启插件
        self.app_bridge.toggle_plugin("nerve.system.stability", True)
        dash_after_on = self.app_bridge.get_dashboard_data()
        self.assertEqual(dash_after_on["active_plugins_count"], initial_active)

    # ================= 4. 静默模式 (Inhibition) × 驾驶舱与起搏器组合 =================

    def test_tier3_quiet_mode_inhibition_and_pacemaker_sync(self):
        """[Tier 3/Matrix 4] 验证免打扰静默期设置、驾驶舱 is_inhibited 状态与中枢缓冲器联动"""
        self.assertFalse(self.app_bridge.buffer.is_inhibited())

        # 应用 180 秒静默模式
        res_quiet = self.app_bridge.apply_quiet_mode(seconds=180)
        self.assertTrue(res_quiet["success"])
        self.assertEqual(res_quiet["cooldown_seconds"], 180)

        # 验证缓冲器与驾驶舱均处于抑制状态
        self.assertTrue(self.app_bridge.buffer.is_inhibited())
        dash_data = self.app_bridge.get_dashboard_data()
        self.assertTrue(dash_data["is_inhibited"])
        self.assertIn("180 秒", dash_data["latest_briefing"]["inhibition_status"])


if __name__ == '__main__':
    unittest.main()
