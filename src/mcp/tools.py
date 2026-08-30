"""
CyberSpine MCP 工具实现处理器 (Tool Implementation Handlers)
"""
import time
from typing import Dict, Any, Optional

from src.app.app_bridge import CyberSpineAppBridge
from src.pacing.real_pacemaker import RealAutonomousPacemaker
from src.models.local_engine import LocalModelEngine
from src.actuators.base import ProposedAction, ActionRiskLevel


class CyberSpineMCPHandlers:
    """MCP 工具执行器，单例封装与 CyberSpine 核心中枢的连接"""

    _instance = None

    def __init__(self):
        self.bridge = CyberSpineAppBridge()
        self.pacemaker = RealAutonomousPacemaker()
        self.engine = LocalModelEngine()

    @classmethod
    def get_instance(cls) -> "CyberSpineMCPHandlers":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_world_briefing(self, force_live_inference: bool = False) -> Dict[str, Any]:
        """获取最新的 1 分钟世界宏观感知简报与决策裁决"""
        if force_live_inference:
            return self.bridge.trigger_live_cognitive_cycle()

        dash = self.bridge.get_dashboard_data()
        briefing = dash.get("latest_briefing", {})
        pacemaker_status = self.pacemaker.get_live_pacemaker_status()

        return {
            "briefing": briefing,
            "pacemaker_heartbeats": pacemaker_status.get("total_heartbeats", 0),
            "current_foreground_process": pacemaker_status.get("current_process", "Desktop"),
            "current_dwell_seconds": pacemaker_status.get("current_dwell_seconds", 0.0),
            "timestamp": briefing.get("timestamp", ""),
            "escalation_decision": briefing.get("escalation_decision", {
                "escalate_to_cortex": False,
                "urgency": "LOW",
                "reason": "系统运行稳态，心流平稳",
                "suggested_cortex_prompt": "保持被动静默感知",
            }),
        }

    def get_somatic_state(self, channel_filter: Optional[str] = None) -> Dict[str, Any]:
        """获取全身 8 大物理感官神经末梢的时空拓扑"""
        topology = self.bridge.hub.get_full_somatic_topology()
        if channel_filter:
            channels = topology.get("channels", {})
            filtered = {k: v for k, v in channels.items() if channel_filter in k}
            topology["channels"] = filtered
            topology["total_channels"] = len(filtered)
        return topology

    def get_pacemaker_ticks(self, limit: int = 12) -> Dict[str, Any]:
        """获取最近 N 次物理硬件起搏器心跳流水"""
        status = self.pacemaker.get_live_pacemaker_status()
        ticks = status.get("recent_ticks", [])
        return {
            "total_heartbeats": status.get("total_heartbeats", 0),
            "interval_seconds": status.get("interval_seconds", 5.0),
            "current_process": status.get("current_process", "Desktop"),
            "current_dwell_seconds": status.get("current_dwell_seconds", 0.0),
            "recent_ticks": ticks[-limit:],
        }

    def get_cognitive_telemetry(self, limit: int = 30, category: Optional[str] = None) -> Dict[str, Any]:
        """获取结构化认知透视流"""
        frames = self.bridge.telemetry.get_recent_frames(limit=limit)
        if category:
            frames = [f for f in frames if f.get("category") == category]
        return {
            "total_frames_returned": len(frames),
            "frames": frames
        }

    def propose_motor_action(self, action_type: str, params: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """提交运动神经元控制指令"""
        actuator_id = "motor.app_control"
        if "power" in action_type:
            actuator_id = "motor.power"
        elif "workspace" in action_type or "dir" in action_type:
            actuator_id = "motor.workspace"

        action = ProposedAction(
            action_id=f"act_mcp_{int(time.time() * 1000)}",
            actuator_id=actuator_id,
            action_name=action_type,
            risk_level=ActionRiskLevel.READ_ONLY_SAFE if ("get" in action_type or "scan" in action_type) else ActionRiskLevel.MUTATING_APPROVAL,
            parameters=params,
            reason=reason,
            inquiry_message=f"【高级大脑指示】提议执行 {action_type}: {reason}"
        )
        result = self.bridge.actuator_hub.execute_action(action)
        return {
            "action_id": action.action_id,
            "action_name": action.action_name,
            "risk_level": action.risk_level.value,
            "success": result.success,
            "execution_summary": result.execution_summary,
            "output_data": result.output_data,
            "error_message": result.error_message,
        }

    def set_downward_inhibition(self, duration_seconds: int = 300, reason: str = "高级大脑设定免打扰") -> Dict[str, Any]:
        """设置下行抑制"""
        res = self.bridge.apply_quiet_mode(seconds=duration_seconds)
        return {
            "is_inhibited": True,
            "duration_seconds": duration_seconds,
            "reason": reason,
            "status": f"已成功激活 {duration_seconds} 秒下行抑制免打扰模式"
        }
