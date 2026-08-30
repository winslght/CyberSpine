"""
CyberSpine 运动神经元: 工作区与目录操作器 (Workspace Actuator)
负责安全只读扫描、工程目录创建、Python 依赖预检与虚拟环境检测。
"""
import os
from pathlib import Path
from typing import Dict, Any

from src.actuators.base import BaseActuator, ActionRiskLevel, ActionResult


class WorkspaceActuator(BaseActuator):
    """工作区与工程目录控制执行器"""

    def __init__(self):
        super().__init__(actuator_id="motor.workspace", name="工作区与目录操作器")

    def evaluate_risk(self, action_name: str, params: Dict[str, Any]) -> ActionRiskLevel:
        if action_name in ("scan_directory", "preflight_check"):
            return ActionRiskLevel.READ_ONLY_SAFE
        elif action_name in ("create_project_directory", "prepare_python_venv"):
            return ActionRiskLevel.MUTATING_APPROVAL
        return ActionRiskLevel.DANGEROUS_FORBIDDEN

    def execute(self, action_name: str, params: Dict[str, Any]) -> ActionResult:
        action_id = params.get("action_id", "act_ws_unknown")
        target_path_str = params.get("target_path", "")

        if not target_path_str:
            return ActionResult(
                action_id=action_id,
                success=False,
                execution_summary="未提供有效的目标路径",
                error_message="target_path parameter is missing"
            )

        target_path = Path(target_path_str)

        # 1. 只读扫描工作区
        if action_name == "scan_directory":
            if not target_path.exists():
                return ActionResult(
                    action_id=action_id,
                    success=False,
                    execution_summary=f"目标路径 {target_path_str} 不存在",
                )
            items = list(target_path.iterdir())[:30]
            dirs = [p.name for p in items if p.is_dir()]
            files = [p.name for p in items if p.is_file()]
            return ActionResult(
                action_id=action_id,
                success=True,
                execution_summary=f"已成功扫描目录 {target_path_str}：发现 {len(dirs)} 个子目录与 {len(files)} 个文件。",
                output_data={"directories": dirs, "files": files, "total_items": len(items)},
            )

        # 2. 创建新工程目录
        elif action_name == "create_project_directory":
            try:
                target_path.mkdir(parents=True, exist_ok=True)
                return ActionResult(
                    action_id=action_id,
                    success=True,
                    execution_summary=f"已成功创建工程目录：{target_path_str}",
                    output_data={"created_path": str(target_path)},
                )
            except Exception as e:
                return ActionResult(
                    action_id=action_id,
                    success=False,
                    execution_summary=f"创建目录失败: {str(e)}",
                    error_message=str(e),
                )

        # 3. 依赖与环境预检
        elif action_name == "preflight_check":
            has_req = (target_path / "requirements.txt").exists()
            has_pyproject = (target_path / "pyproject.toml").exists()
            has_git = (target_path / ".git").exists()
            has_venv = (target_path / ".venv").exists() or (target_path / "venv").exists()

            summary = f"预检完成：Git={'[就绪]' if has_git else '[未初始化]'}, 依赖配置={'[requirements.txt]' if has_req else '[无]'}, 虚拟环境={'[已存在]' if has_venv else '[未配置]'}"
            return ActionResult(
                action_id=action_id,
                success=True,
                execution_summary=summary,
                output_data={
                    "has_git": has_git,
                    "has_requirements": has_req,
                    "has_pyproject": has_pyproject,
                    "has_venv": has_venv,
                },
            )

        return ActionResult(
            action_id=action_id,
            success=False,
            execution_summary=f"未知动作: {action_name}",
            error_message="Unsupported action",
        )
