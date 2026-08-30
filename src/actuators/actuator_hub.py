"""
CyberSpine 运动神经元双手执行总控中心 (Motor Actuator Hub)
统一汇聚管理全身所有操作系统控制执行器，提供统一的安全执行入口。
"""
from typing import Dict, Any, List, Optional, Callable

from src.actuators.base import BaseActuator, ProposedAction, ActionResult
from src.actuators.workspace import WorkspaceActuator
from src.actuators.app_control import AppControlActuator
from src.actuators.power import SystemPowerActuator
from src.actuators.safety_gate import SafetyGate


class MotorActuatorHub:
    """运动神经元总控中心"""

    def __init__(self):
        self.workspace_actuator = WorkspaceActuator()
        self.app_actuator = AppControlActuator()
        self.power_actuator = SystemPowerActuator()

        self.safety_gate = SafetyGate(actuators=[
            self.workspace_actuator,
            self.app_actuator,
            self.power_actuator,
        ])

    def execute_action(
        self,
        proposed_action: ProposedAction,
        approval_callback: Optional[Callable[[ProposedAction], bool]] = None,
        is_user_approved: bool = False,
    ) -> ActionResult:
        """执行动作帧"""
        return self.safety_gate.verify_and_execute(
            proposed_action=proposed_action,
            approval_callback=approval_callback,
            is_user_approved=is_user_approved,
        )

    def list_capabilities(self) -> List[Dict[str, Any]]:
        """获取所有可用运动控制能力清单"""
        return [
            {"id": self.workspace_actuator.actuator_id, "name": self.workspace_actuator.name, "capabilities": ["scan_directory", "create_project_directory", "preflight_check"]},
            {"id": self.app_actuator.actuator_id, "name": self.app_actuator.name, "capabilities": ["open_in_vscode", "open_folder_in_explorer", "launch_app"]},
            {"id": self.power_actuator.actuator_id, "name": self.power_actuator.name, "capabilities": ["get_active_power_scheme", "set_power_scheme"]},
        ]
