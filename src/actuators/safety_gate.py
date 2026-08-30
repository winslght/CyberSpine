"""
CyberSpine 运动神经元安全三定律门控 (Safety Gate)
严格执行“只读自动放行”、“变更必须审批”、“破坏物理熔断”三大安全铁律。
"""
from typing import Dict, Any, Callable, Optional, List

from src.actuators.base import (
    BaseActuator,
    ActionRiskLevel,
    ProposedAction,
    ActionResult,
)


class SafetyGate:
    """运动神经元安全执行门控"""

    # 严禁执行的高危黑名单关键字
    DANGEROUS_KEYWORDS = {
        "rmdir /s", "del /f", "format", "diskpart", "reg delete",
        "drop database", "shutdown /s", "taskkill /f /im explorer.exe"
    }

    def __init__(self, actuators: Optional[List[BaseActuator]] = None):
        self._actuators: Dict[str, BaseActuator] = {}
        if actuators:
            for act in actuators:
                self.register_actuator(act)

    def register_actuator(self, actuator: BaseActuator):
        self._actuators[actuator.actuator_id] = actuator

    def get_actuator(self, actuator_id: str) -> Optional[BaseActuator]:
        return self._actuators.get(actuator_id)

    def verify_and_execute(
        self,
        proposed_action: ProposedAction,
        approval_callback: Optional[Callable[[ProposedAction], bool]] = None,
        is_user_approved: bool = False,
    ) -> ActionResult:
        """
        经过安全三定律审查后执行动作
        :param proposed_action: AI 提议的动作帧
        :param approval_callback: 交互审批回调函数
        :param is_user_approved: 是否已获得前端/用户显式确认
        """
        actuator = self.get_actuator(proposed_action.actuator_id)
        if not actuator:
            return ActionResult(
                action_id=proposed_action.action_id,
                success=False,
                execution_summary=f"未找到对应的运动神经元执行器: {proposed_action.actuator_id}",
                error_message="Actuator not registered",
            )

        # 1. 物理安全熔断检查 (第三定律)
        param_str = str(proposed_action.parameters).lower()
        for dangerous in self.DANGEROUS_KEYWORDS:
            if dangerous in param_str:
                return ActionResult(
                    action_id=proposed_action.action_id,
                    success=False,
                    execution_summary=f"🛡️ [物理安全熔断] 检测到高危指令 '{dangerous}'，已被安全门控绝对拦截！",
                    error_message="Hard-fuse blocked dangerous command",
                )

        # 重新评估风险等级
        risk = actuator.evaluate_risk(proposed_action.action_name, proposed_action.parameters)

        # 2. 只读操作自动放行 (第一定律)
        if risk == ActionRiskLevel.READ_ONLY_SAFE:
            return actuator.execute(proposed_action.action_name, proposed_action.parameters)

        # 3. 变更操作必须用户审批 (第二定律)
        elif risk == ActionRiskLevel.MUTATING_APPROVAL:
            approved = is_user_approved
            if not approved and approval_callback is not None:
                approved = approval_callback(proposed_action)

            if approved:
                return actuator.execute(proposed_action.action_name, proposed_action.parameters)
            else:
                return ActionResult(
                    action_id=proposed_action.action_id,
                    success=False,
                    execution_summary="用户选择暂不执行该操作，已安全退避。",
                    error_message="User rejected or pending approval",
                )

        # 兜底拦截
        return ActionResult(
            action_id=proposed_action.action_id,
            success=False,
            execution_summary="操作未通过安全评估，已拦截。",
            error_message="Security check failed",
        )
