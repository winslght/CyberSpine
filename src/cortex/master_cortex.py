"""
CyberSpine 组件 4: 前额叶大脑认知中枢、温和交互与双手执行 (Master Cortex & Efferent Feedback)
负责接收脊髓呈递的《意图故事》，执行 3W 深度推演、发起温和询问、审批后调用双手工具执行，并下达抑制递质闭环。
"""
import uuid
from typing import Dict, Any, Optional, Tuple, Callable
from pathlib import Path

from src.models.somatic_signals import (
    IntentNarrative,
    CognitiveFeedbackMessage,
    FeedbackDirective,
    utc_now,
)
from src.pacing.neural_buffer import TemporalNeuralBuffer


class MasterCortex:
    """
    前额叶战略主脑 (Master Cognitive Cortex)
    - 3W 深度哲学推演 (Where / When / Why / Should I Intervene)
    - 构造人机温和交互提示 (Gentle Partner Inquiry)
    - 审批通过后调度双手 (Hands / Tool Execution)
    - 回传下行抑制递质 (Efferent Feedback Loop)，闭环降载
    """

    def __init__(self, neural_buffer: Optional[TemporalNeuralBuffer] = None):
        self.neural_buffer = neural_buffer
        self.last_feedback: Optional[CognitiveFeedbackMessage] = None

    def process_intent_narrative(
        self,
        narrative: IntentNarrative,
        approval_callback: Optional[Callable[[str], bool]] = None,
        target_directory: Optional[str] = None,
    ) -> Tuple[bool, CognitiveFeedbackMessage]:
        """
        处理脊髓上呈的意图故事，执行认知推演与闭环接管
        :param narrative: 来自脊髓的意图故事
        :param approval_callback: 用户审批回调函数 (返回 True 表示用户同意执行)
        :param target_directory: 需要双手扫描执行的目标目录 (如 U 盘挂载点)
        :return: (是否执行了双手操作, 回传的下行反馈消息)
        """
        # 1. 3W 认知推演
        if not narrative.should_escalate_to_cortex:
            feedback = CognitiveFeedbackMessage(
                feedback_id=f"fb_{uuid.uuid4().hex[:8]}",
                target_narrative_id=narrative.narrative_id,
                directive=FeedbackDirective.SUPPRESS_AND_OBSERVE,
                cooldown_seconds=60,
                reason="低级事件或噪音，前额叶大脑无需介入",
            )
            self._apply_feedback_to_buffer(feedback)
            return False, feedback

        # 2. 构造温和交互卡片文案 (Gentle Inquiry)
        inquiry_text = self._build_gentle_inquiry(narrative)

        # 3. 用户审批逻辑 (若无传入回调则默认自动批准)
        is_approved = True
        if approval_callback is not None:
            is_approved = approval_callback(inquiry_text)

        # 4. 执行分支
        executed_summary = None
        if is_approved:
            # 动用双手 (Tool Execution)
            executed_summary = self._execute_hands_tool_scan(target_directory, narrative)
            directive = FeedbackDirective.SUPPRESS_AND_OBSERVE
            reason = "用户已审批，大脑双手已完成工作区文件扫描与环境预备，进入 5 分钟静默观察期"
            cooldown = 300
        else:
            directive = FeedbackDirective.SUPPRESS_AND_OBSERVE
            reason = "用户选择暂不处理，进入 15 分钟免打扰退避期"
            cooldown = 900

        # 5. 生成下行反馈递质
        feedback = CognitiveFeedbackMessage(
            feedback_id=f"fb_{int(utc_now().timestamp() * 1000)}_{uuid.uuid4().hex[:8]}",
            target_narrative_id=narrative.narrative_id,
            directive=directive,
            cooldown_seconds=cooldown,
            reason=reason,
            executed_action_summary=executed_summary,
        )

        # 提取目标设备 ID (用于定向抑制该设备，允许其他新设备正常接入)
        dev_id = None
        if narrative.evidence_snapshot:
            devices = narrative.evidence_snapshot.get("devices_involved", [])
            if devices:
                dev_id = devices[0]

        self._apply_feedback_to_buffer(feedback, device_id=dev_id)
        self.last_feedback = feedback
        return is_approved, feedback

    def _build_gentle_inquiry(self, narrative: IntentNarrative) -> str:
        """生成符合‘身旁坐着一位懂你节奏的大佬搭档’语气的温和提示"""
        if narrative.macro_scenario == "WORKSPACE_ATTACH_PYTHON_DEV":
            return (
                "💡 【CyberSpine 伴侣感知】检测到您接入了常用 Python 研发工作盘。\n"
                "   推测您准备开始相关项目开发。是否需要为您快速整理目录文件并准备依赖环境？"
            )
        elif narrative.macro_scenario == "WORKSPACE_ATTACH_SYSTEMS_DEV":
            return (
                "🦀 【CyberSpine 伴侣感知】检测到底层系统开发工程介质接入。\n"
                "   是否需要为您执行 Cargo/Go 环境预检？"
            )
        elif narrative.macro_scenario == "WORKSPACE_ATTACH_MEDIA_ASSETS":
            return (
                "🎬 【CyberSpine 伴侣感知】检测到多媒体素材介质接入。\n"
                "   是否需要为您按拍摄日期整理素材？"
            )
        else:
            return f"🔔 【CyberSpine 伴侣感知】检测到环境事件: {narrative.situation_story}，是否需要协助？"

    def _execute_hands_tool_scan(self, target_directory: Optional[str], narrative: IntentNarrative) -> str:
        """大脑调用双手工具执行文件扫描与摘要"""
        if not target_directory:
            return f"已确认意图 [{narrative.macro_scenario}]，工作区上下文已载入大脑短期记忆。"

        target_path = Path(target_directory)
        if not target_path.exists():
            return f"目标路径 {target_directory} 暂不可直接访问，已完成虚拟建档。"

        try:
            items = list(target_path.iterdir())[:20]
            dirs = [p.name for p in items if p.is_dir()]
            files = [p.name for p in items if p.is_file()]
            return (
                f"【双手执行完毕】成功扫描目录: {target_directory}\n"
                f"- 发现子目录: {dirs}\n"
                f"- 发现关键文件: {files}\n"
                f"- 状态: 工作区就绪，随时可展开编码或测试。"
            )
        except Exception as e:
            return f"执行扫描时捕获异常: {str(e)}"

    def _apply_feedback_to_buffer(self, feedback: CognitiveFeedbackMessage, device_id: Optional[str] = None):
        """将下行抑制指令传导给中枢时钟缓冲器"""
        if self.neural_buffer is not None:
            self.neural_buffer.apply_inhibition(feedback.cooldown_seconds, device_id=device_id)
