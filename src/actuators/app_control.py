"""
CyberSpine 运动神经元: 应用程序与窗口调度器 (App Control Actuator)
负责在 Windows 下调起指定生产力应用 (VSCode, 终端, 资源管理器) 与窗口前台激活。
"""
import os
import subprocess
import ctypes
from pathlib import Path
from typing import Dict, Any

from src.actuators.base import BaseActuator, ActionRiskLevel, ActionResult


class AppControlActuator(BaseActuator):
    """应用程序与窗口控制执行器"""

    # 允许唤醒的安全白名单应用
    ALLOWED_APPS = {
        "code": "code",
        "vscode": "code",
        "explorer": "explorer",
        "terminal": "wt",
        "powershell": "powershell",
        "cmd": "cmd",
    }

    def __init__(self):
        super().__init__(actuator_id="motor.app_control", name="应用与窗口调度器")

    def evaluate_risk(self, action_name: str, params: Dict[str, Any]) -> ActionRiskLevel:
        if action_name in ("open_folder_in_explorer", "focus_window"):
            return ActionRiskLevel.READ_ONLY_SAFE
        elif action_name in ("launch_app", "open_in_vscode"):
            return ActionRiskLevel.MUTATING_APPROVAL
        return ActionRiskLevel.DANGEROUS_FORBIDDEN

    def execute(self, action_name: str, params: Dict[str, Any]) -> ActionResult:
        action_id = params.get("action_id", "act_app_unknown")

        # 1. 在 VSCode 中打开目标工作区
        if action_name == "open_in_vscode":
            target_path = params.get("target_path", ".")
            try:
                # 使用非阻塞 Popen 唤醒 VSCode
                subprocess.Popen(["code", target_path], shell=True)
                return ActionResult(
                    action_id=action_id,
                    success=True,
                    execution_summary=f"已成功在 VSCode 编辑器中拉起并打开工作区: {target_path}",
                    output_data={"app": "code", "target_path": target_path},
                )
            except Exception as e:
                return ActionResult(
                    action_id=action_id,
                    success=False,
                    execution_summary=f"唤醒 VSCode 失败: {str(e)}",
                    error_message=str(e),
                )

        # 2. 在资源管理器中定位打开文件夹
        elif action_name == "open_folder_in_explorer":
            target_path = params.get("target_path", ".")
            try:
                os.startfile(target_path)
                return ActionResult(
                    action_id=action_id,
                    success=True,
                    execution_summary=f"已在 Windows 文件资源管理器中打开: {target_path}",
                    output_data={"target_path": target_path},
                )
            except Exception as e:
                return ActionResult(
                    action_id=action_id,
                    success=False,
                    execution_summary=f"打开文件夹失败: {str(e)}",
                    error_message=str(e),
                )

        # 3. 调起通用白名单应用
        elif action_name == "launch_app":
            app_key = params.get("app_name", "").lower()
            if app_key not in self.ALLOWED_APPS:
                return ActionResult(
                    action_id=action_id,
                    success=False,
                    execution_summary=f"应用 '{app_key}' 不在安全执行白名单中",
                    error_message="App not in security whitelist",
                )
            cmd = self.ALLOWED_APPS[app_key]
            args = params.get("args", [])
            try:
                subprocess.Popen([cmd] + args, shell=True)
                return ActionResult(
                    action_id=action_id,
                    success=True,
                    execution_summary=f"已成功唤起应用程序: {app_key}",
                    output_data={"command": cmd, "args": args},
                )
            except Exception as e:
                return ActionResult(
                    action_id=action_id,
                    success=False,
                    execution_summary=f"拉起应用失败: {str(e)}",
                    error_message=str(e),
                )

        return ActionResult(
            action_id=action_id,
            success=False,
            execution_summary=f"不支持的动作: {action_name}",
            error_message="Unsupported action",
        )
