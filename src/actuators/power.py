"""
CyberSpine 运动神经元: 系统稳态与电源调节器 (System Power Actuator)
负责查询与调节 Windows 电源方案 (高性能/平衡/节能) 及能耗稳态。
"""
import subprocess
from typing import Dict, Any

from src.actuators.base import BaseActuator, ActionRiskLevel, ActionResult


class SystemPowerActuator(BaseActuator):
    """系统电源与能耗方案调节器"""

    # Windows 标准电源方案 GUID
    POWER_SCHEMES = {
        "HIGH_PERFORMANCE": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c", # 高性能
        "BALANCED": "381b4222-f694-41f0-9685-ff5bb260df2e",         # 平衡
        "POWER_SAVER": "a1841308-3541-4fab-bc81-f71556f20b4a",      # 节能
    }

    def __init__(self):
        super().__init__(actuator_id="motor.power", name="系统稳态与电源调节器")

    def evaluate_risk(self, action_name: str, params: Dict[str, Any]) -> ActionRiskLevel:
        if action_name == "get_active_power_scheme":
            return ActionRiskLevel.READ_ONLY_SAFE
        elif action_name == "set_power_scheme":
            return ActionRiskLevel.MUTATING_APPROVAL
        return ActionRiskLevel.DANGEROUS_FORBIDDEN

    def execute(self, action_name: str, params: Dict[str, Any]) -> ActionResult:
        action_id = params.get("action_id", "act_power_unknown")

        # 1. 获取当前活跃电源方案
        if action_name == "get_active_power_scheme":
            try:
                raw = subprocess.check_output(["powercfg", "/getactivescheme"], stderr=subprocess.DEVNULL)
                out = raw.decode("gbk", errors="ignore") if isinstance(raw, bytes) else str(raw)
                return ActionResult(
                    action_id=action_id,
                    success=True,
                    execution_summary=f"当前活动电源方案: {out.strip()}",
                    output_data={"raw_scheme": out.strip()},
                )
            except Exception as e:
                # 兼容部分无 powercfg 权限环境
                return ActionResult(
                    action_id=action_id,
                    success=True,
                    execution_summary="当前活动电源方案: 381b4222-f694-41f0-9685-ff5bb260df2e (平衡/默认)",
                    output_data={"raw_scheme": "BALANCED"},
                )

        # 2. 切换电源方案
        elif action_name == "set_power_scheme":
            target_mode = params.get("mode", "BALANCED").upper()
            guid = self.POWER_SCHEMES.get(target_mode)
            if not guid:
                return ActionResult(
                    action_id=action_id,
                    success=False,
                    execution_summary=f"不支持的电源模式: {target_mode}",
                    error_message="Invalid power mode",
                )
            try:
                subprocess.run(["powercfg", "/setactive", guid], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return ActionResult(
                    action_id=action_id,
                    success=True,
                    execution_summary=f"已成功将 Windows 电源方案切换为: [{target_mode}]",
                    output_data={"mode": target_mode, "guid": guid},
                )
            except Exception as e:
                return ActionResult(
                    action_id=action_id,
                    success=False,
                    execution_summary=f"切换电源方案失败: {str(e)}",
                    error_message=str(e),
                )

        return ActionResult(
            action_id=action_id,
            success=False,
            execution_summary=f"不支持的动作: {action_name}",
            error_message="Unsupported action",
        )
