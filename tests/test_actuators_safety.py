"""
CyberSpine 运动神经元双手执行器与安全三定律门控单元测试套件
"""
import sys
import unittest
import tempfile
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.actuators.base import ProposedAction, ActionRiskLevel, ActionResult
from src.actuators.workspace import WorkspaceActuator
from src.actuators.app_control import AppControlActuator
from src.actuators.power import SystemPowerActuator
from src.actuators.safety_gate import SafetyGate
from src.actuators.actuator_hub import MotorActuatorHub


class TestActuatorsAndSafetyGate(unittest.TestCase):

    def setUp(self):
        self.hub = MotorActuatorHub()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_law_one_readonly_auto_execution(self):
        """测试 1: 第一定律——只读操作自动放行执行"""
        # 准备一个测试文件
        (self.work_path / "main.py").write_text("print('hello')", encoding='utf-8')

        action = ProposedAction(
            action_id="act_test_01",
            actuator_id="motor.workspace",
            action_name="scan_directory",
            risk_level=ActionRiskLevel.READ_ONLY_SAFE,
            parameters={"action_id": "act_test_01", "target_path": str(self.work_path)},
            reason="测试只读扫描",
            inquiry_message="无需审批",
        )

        # 未提供审批回调或标志，只读操作应直接自动成功执行
        result = self.hub.execute_action(action)
        self.assertTrue(result.success)
        self.assertIn("main.py", result.output_data.get("files", []))

        print("\n--- [TEST 1: Law 1 - Read-Only Auto-Execute] ---")
        print(f"[PASS] 只读操作自动放行: {result.execution_summary}")

    def test_02_law_two_mutating_requires_approval(self):
        """测试 2: 第二定律——变更操作必须用户审批"""
        action = ProposedAction(
            action_id="act_test_02",
            actuator_id="motor.workspace",
            action_name="create_project_directory",
            risk_level=ActionRiskLevel.MUTATING_APPROVAL,
            parameters={"action_id": "act_test_02", "target_path": str(self.work_path / "sub_project")},
            reason="测试创建目录",
            inquiry_message="是否允许创建子目录？",
        )

        # 1. 用户未同意 -> 拦截退避
        res_reject = self.hub.execute_action(action, is_user_approved=False)
        self.assertFalse(res_reject.success)
        self.assertIn("暂不执行", res_reject.execution_summary)

        # 2. 用户点击同意 -> 执行成功
        res_approve = self.hub.execute_action(action, is_user_approved=True)
        self.assertTrue(res_approve.success)
        self.assertTrue((self.work_path / "sub_project").exists())

        print("\n--- [TEST 2: Law 2 - Mutating Requires Approval] ---")
        print(f"[PASS] 未审批拦截: {res_reject.execution_summary}")
        print(f"[PASS] 审批后放行: {res_approve.execution_summary}")

    def test_03_law_three_dangerous_hard_fuse(self):
        """测试 3: 第三定律——高危破坏性指令物理熔断拦截"""
        action_dangerous = ProposedAction(
            action_id="act_test_03",
            actuator_id="motor.workspace",
            action_name="create_project_directory",
            risk_level=ActionRiskLevel.MUTATING_APPROVAL,
            parameters={"action_id": "act_test_03", "target_path": "C:\\ && del /f /s *.*"},
            reason="恶意注入测试",
            inquiry_message="恶意提议",
        )

        # 即使前端传入 is_user_approved=True，安全门控也必须物理熔断！
        res_blocked = self.hub.execute_action(action_dangerous, is_user_approved=True)
        self.assertFalse(res_blocked.success)
        self.assertIn("物理安全熔断", res_blocked.execution_summary)

        print("\n--- [TEST 3: Law 3 - Dangerous Action Hard-Fuse] ---")
        print(f"[PASS] 物理安全熔断拦截成功: {res_blocked.execution_summary}")

    def test_04_system_power_actuator(self):
        """测试 4: 系统电源调节器只读查询"""
        action = ProposedAction(
            action_id="act_test_04",
            actuator_id="motor.power",
            action_name="get_active_power_scheme",
            risk_level=ActionRiskLevel.READ_ONLY_SAFE,
            parameters={"action_id": "act_test_04"},
            reason="查询当前电源方案",
            inquiry_message="只读",
        )
        res = self.hub.execute_action(action)
        self.assertTrue(res.success)
        print("\n--- [TEST 4: System Power Actuator Query] ---")
        print(f"[PASS] 查询电源方案: {res.execution_summary}")


if __name__ == '__main__':
    unittest.main()
