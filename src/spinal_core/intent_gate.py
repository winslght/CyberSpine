"""
CyberSpine 组件 3: 脊髓意图门控与叙事提炼脑 (Spinal Intent Gate & Narrative Builder)
负责对时钟缓冲器送来的融合电信号进行低级初审、噪音过滤，并提炼为《用户意图故事 (Intent Narrative)》。
"""
import uuid
from typing import Optional, Dict, Any, List

from src.models.somatic_signals import (
    FusedSomaticPacket,
    IntentNarrative,
    PacingStateEnum,
    utc_now,
)


class SpinalIntentGate:
    """
    脊髓意图审查与感觉门控 (Spinal Intent Gate)
    - 过滤 99.9% 无意义硬件与系统微观噪音 (Sensory Gating)
    - 本地轻量提炼结构化《用户意图故事 (Intent Narrative)》
    - 判定是否需要呈递给前额叶高级大脑 (Escalation Gate)
    """

    def __init__(self, enable_ollama: bool = False, model_name: str = "qwen2.5:3b"):
        self.enable_ollama = enable_ollama
        self.model_name = model_name

    def evaluate_and_narrate(self, packet: Optional[FusedSomaticPacket]) -> Optional[IntentNarrative]:
        """
        审查融合电信号包，执行感觉门控过滤并提炼意图叙事
        :param packet: 来自中枢时钟缓冲器的融合信号包
        :return: 提炼出的 IntentNarrative (若判定为噪音或无包则返回 None 或 should_escalate=False)
        """
        if packet is None:
            return None

        # 1. 提取核心特征
        profiles: List[str] = packet.somatic_summary.get("structure_profiles", [])
        channels: List[str] = packet.somatic_summary.get("channels", [])
        primary_event: str = packet.primary_event

        # 2. 感觉门控低级过滤 (Sensory Gating)
        # 如果是存储事件但没有任何识别画像且无内容，判定为普通空盘或无意义插拔，直接静默过滤
        if "IO_STORAGE" in channels and not profiles:
            return IntentNarrative(
                narrative_id=f"narrative_noise_{uuid.uuid4().hex[:8]}",
                macro_scenario="GENERIC_STORAGE_NOISE",
                confidence=0.20,
                situation_story="检测到普通存储设备插入，但未发现特征工程文件，判定为无交互价值的常规存储。",
                intent_hypothesis="用户可能仅进行简单文件拷贝或备份。",
                suggested_partnership="保持完全静默，不惊扰用户。",
                should_escalate_to_cortex=False,
                evidence_snapshot=packet.somatic_summary,
            )

        # 3. 意图提炼脑：针对开发与生产力场景的语义升华
        macro_scenario = "WORKSPACE_UNKNOWN"
        situation_story = ""
        intent_hypothesis = ""
        suggested_partnership = ""
        confidence = 0.90

        # 场景 A: Python / Git 研发工程盘接入
        if "PYTHON_PROJECT" in profiles or "GIT_REPOSITORY" in profiles or "WORK_PROJECT_SSD" in str(packet.signals):
            macro_scenario = "WORKSPACE_ATTACH_PYTHON_DEV"
            confidence = 0.96
            situation_story = "感知末梢探测到用户接入了包含 Python 项目配置 (requirements.txt / main.py) 与 Git 仓库的工作盘。"
            intent_hypothesis = "推测用户准备在该工作盘开展 Python 代码开发、依赖同步或调试工作。"
            suggested_partnership = "建议前额叶大脑在用户沉思停顿点，主动询问是否需要扫描项目文件目录并预备工作环境。"

        # 场景 B: Rust / Go 底层工程盘接入
        elif "RUST_GO_PROJECT" in profiles:
            macro_scenario = "WORKSPACE_ATTACH_SYSTEMS_DEV"
            confidence = 0.95
            situation_story = "感知末梢探测到包含 Cargo.toml / go.mod 的系统级开发工程介质挂载。"
            intent_hypothesis = "推测用户准备进行高性能系统编程或编译构建。"
            suggested_partnership = "建议前额叶大脑温和提示是否需要构建依赖预检。"

        # 场景 C: 多媒体与视频素材库接入
        elif "MEDIA_CONTAINER" in profiles or "OFFICE_DOCUMENTS" in profiles:
            macro_scenario = "WORKSPACE_ATTACH_MEDIA_ASSETS"
            confidence = 0.92
            situation_story = "感知末梢探测到多媒体素材盘挂载，包含视频或设计文档。"
            intent_hypothesis = "推测用户准备导入剪辑素材或查看办公文档。"
            suggested_partnership = "建议前额叶大脑提示是否需要执行素材轻量归类。"

        else:
            macro_scenario = "SYSTEM_PERIPHERAL_ATTACHED"
            confidence = 0.75
            situation_story = f"捕获到事件 [{primary_event}]，涉及设备通道 {channels}。"
            intent_hypothesis = "常规外设或状态变动。"
            suggested_partnership = "视用户当前心流状态决定是否记录。"

        narrative = IntentNarrative(
            narrative_id=f"narrative_{int(utc_now().timestamp() * 1000)}_{uuid.uuid4().hex[:8]}",
            macro_scenario=macro_scenario,
            confidence=confidence,
            situation_story=situation_story,
            intent_hypothesis=intent_hypothesis,
            suggested_partnership=suggested_partnership,
            should_escalate_to_cortex=True,
            evidence_snapshot=packet.somatic_summary,
        )
        return narrative
