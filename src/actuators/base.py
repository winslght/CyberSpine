"""
CyberSpine 运动神经元统一抽象基类与动作契约 (Motor Actuator Base)
所有操作系统控制动作执行器统一继承此基类，遵守运动神经元安全三定律。
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from src.models.somatic_signals import utc_now


class ActionRiskLevel(str, Enum):
    READ_ONLY_SAFE = "READ_ONLY_SAFE"       # 只读安全操作 (自动放行)
    MUTATING_APPROVAL = "MUTATING_APPROVAL" # 变更操作 (必须用户审批)
    DANGEROUS_FORBIDDEN = "DANGEROUS_FORBIDDEN" # 高危操作 (物理熔断拦截)


class ProposedAction(BaseModel):
    """AI 提议执行的操作系统控制动作帧"""
    action_id: str = Field(description="动作唯一标识")
    actuator_id: str = Field(description="负责执行的运动神经元标识")
    action_name: str = Field(description="动作人类可读名称")
    risk_level: ActionRiskLevel = Field(default=ActionRiskLevel.MUTATING_APPROVAL)
    parameters: Dict[str, Any] = Field(default_factory=dict, description="动作参数")
    reason: str = Field(description="AI 提议执行该动作的推演意图与理由")
    inquiry_message: str = Field(description="呈递给用户的温和卡片询问文本")
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())


class ActionResult(BaseModel):
    """运动神经元执行结果"""
    action_id: str
    success: bool
    execution_summary: str
    output_data: Dict[str, Any] = Field(default_factory=dict)
    executed_at: str = Field(default_factory=lambda: utc_now().isoformat())
    error_message: Optional[str] = None


class BaseActuator(ABC):
    """运动神经元执行器抽象基类"""

    def __init__(self, actuator_id: str, name: str):
        self.actuator_id = actuator_id
        self.name = name

    @abstractmethod
    def evaluate_risk(self, action_name: str, params: Dict[str, Any]) -> ActionRiskLevel:
        """评估动作风险等级"""
        pass

    @abstractmethod
    def execute(self, action_name: str, params: Dict[str, Any]) -> ActionResult:
        """执行具体操作系统控制逻辑"""
        pass
