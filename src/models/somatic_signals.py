"""
CyberSpine 数据契约与神经信号模型 (Pydantic V2 兼容版)
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """生成带有时区信息的当前标准 UTC 时间"""
    return datetime.now(timezone.utc)


class DeviceClass(str, Enum):
    """硬件设备分类"""
    STORAGE_REMOVABLE = "STORAGE_REMOVABLE"    # 可移动存储介质 (U盘、移动硬盘、SD卡)
    STORAGE_FIXED = "STORAGE_FIXED"            # 本地固定磁盘
    NETWORK_INTERFACE = "NETWORK_INTERFACE"    # 网络接口 (以太网、WiFi、蜂窝)
    USB_PERIPHERAL = "USB_PERIPHERAL"          # USB 通用外设 (手柄、采集卡、扩展坞)
    AUDIO_DEVICE = "AUDIO_DEVICE"              # 音频设备 (耳机、麦克风)
    BLUETOOTH_DEVICE = "BLUETOOTH_DEVICE"      # 蓝牙外设


class DeviceFingerprint(BaseModel):
    """硬件设备指纹与画像"""
    device_id: str = Field(description="全局唯一设备指纹哈希 (SHA256)")
    device_class: DeviceClass = Field(description="设备类别")
    vendor_id: Optional[str] = Field(None, description="厂商 VID")
    product_id: Optional[str] = Field(None, description="产品 PID")
    volume_label: Optional[str] = Field(None, description="卷标/名称")
    serial_number: Optional[str] = Field(None, description="硬件序列号/盘符唯一标识")
    total_capacity_gb: Optional[float] = Field(None, description="总容量 (GB)")
    free_capacity_gb: Optional[float] = Field(None, description="可用容量 (GB)")
    mount_point: Optional[str] = Field(None, description="挂载点 (如 E:\\)")
    tags: List[str] = Field(default_factory=list, description="用户或系统打标 (如 ['WORK_PYTHON_REPO'])")
    first_seen: datetime = Field(default_factory=utc_now, description="首次接入时间")
    last_seen: datetime = Field(default_factory=utc_now, description="最近活跃时间")
    is_known: bool = Field(default=False, description="是否为数据库中已认识的熟客设备")


class ShallowStructureSummary(BaseModel):
    """只读浅层结构嗅探摘要 (MaxDepth=2, 防杀软误判)"""
    scanned_at: datetime = Field(default_factory=utc_now)
    scan_duration_ms: float = Field(description="嗅探耗时 (毫秒)")
    top_level_directories: List[str] = Field(default_factory=list, description="根目录下的一级目录名")
    top_level_files: List[str] = Field(default_factory=list, description="根目录下的主要文件名")
    detected_profiles: List[str] = Field(default_factory=list, description="识别出的特征画像 (如 ['PYTHON_PROJECT', 'GIT_REPO', 'MEDIA_CONTAINER'])")
    file_count_sampled: int = Field(default=0, description="浅层采样的文件总数")


class RawSomaticSignal(BaseModel):
    """末梢神经产生的原始感官电信号"""
    signal_id: str = Field(description="信号全局唯一 UUID")
    timestamp: datetime = Field(default_factory=utc_now)
    channel: str = Field(description="感官通道: IO_STORAGE | IO_DEVICE | IO_NETWORK | WORKSPACE | CLIPBOARD")
    event_type: str = Field(description="事件动作: DEVICE_ATTACHED | DEVICE_REMOVED | STATE_CHANGED")
    source_probe: str = Field(description="产生信号的具体探针标识")
    device_fingerprint: Optional[DeviceFingerprint] = Field(None, description="关联的设备指纹")
    structure_summary: Optional[ShallowStructureSummary] = Field(None, description="浅层嗅探结构 (仅存储介质有效)")
    raw_metrics: Dict[str, Any] = Field(default_factory=dict, description="额外原始物理指标")


class PacingStateEnum(str, Enum):
    """中枢呼吸与节律状态"""
    FLOW_ACTIVE = "FLOW_ACTIVE"          # 用户正在高频连贯操作中，静默聚合不打扰
    MICRO_PAUSE = "MICRO_PAUSE"          # 关键操作后进入 3~6 秒黄金沉思停顿，最佳介入时机
    IDLE_STANDBY = "IDLE_STANDBY"        # 长时间无动作，低能耗待机稳态


class FusedSomaticPacket(BaseModel):
    """在时间窗口内对齐的多感官融合电信号包 (由中枢时钟缓冲器输出)"""
    packet_id: str = Field(description="融合包全局唯一 UUID")
    window_start: datetime = Field(description="时空对齐窗口起始时间")
    window_end: datetime = Field(description="时空对齐窗口结束时间")
    signals: List[RawSomaticSignal] = Field(default_factory=list, description="窗口内汇聚的所有末梢信号")
    primary_event: str = Field(description="主导事件类型，如 'STORAGE_DEVICE_ATTACHED'")
    pacing_state: PacingStateEnum = Field(default=PacingStateEnum.MICRO_PAUSE, description="当前呼吸节律状态")
    somatic_summary: Dict[str, Any] = Field(default_factory=dict, description="初步物理拓扑摘要")


class IntentNarrative(BaseModel):
    """脊髓端侧 3B 提炼出并呈递给大脑的《用户意图故事》"""
    narrative_id: str = Field(description="意图叙事全局唯一 UUID")
    generated_at: datetime = Field(default_factory=utc_now)
    macro_scenario: str = Field(description="宏观情境分类，如 'WORKSPACE_ATTACH_PYTHON_DEV'")
    confidence: float = Field(ge=0.0, le=1.0, description="小脑对该意图的置信度 (0.0~1.0)")
    situation_story: str = Field(description="以自然语言叙述的用户当前行为情境")
    intent_hypothesis: str = Field(description="推测用户接下来的核心诉求与目标")
    suggested_partnership: str = Field(description="建议高级大脑采取的温和协作方式")
    should_escalate_to_cortex: bool = Field(default=True, description="小脑初审判断是否需要上报前额叶大脑")
    evidence_snapshot: Dict[str, Any] = Field(default_factory=dict, description="关联的物理感官证据快照")


class FeedbackDirective(str, Enum):
    """大脑向脊髓下达的神经调节指令"""
    SUPPRESS_AND_OBSERVE = "SUPPRESS_AND_OBSERVE"  # 下行抑制：保持静默，进入观察冷却
    PROCEED_COGNITION = "PROCEED_COGNITION"        # 前额叶接管：发起对话或执行动作
    MODIFY_ATTENTION = "MODIFY_ATTENTION"          # 动态调控：调整特定感官的门控灵敏度


class CognitiveFeedbackMessage(BaseModel):
    """前额叶大脑回传给脊髓中枢的双向神经反馈信息"""
    feedback_id: str = Field(description="反馈消息全局唯一 UUID")
    target_narrative_id: str = Field(description="对应的意图叙事 ID")
    directive: FeedbackDirective = Field(description="决策指令")
    cooldown_seconds: int = Field(default=300, description="抑制冷却时长 (秒)")
    reason: str = Field(description="决策理由，如 '用户已授权并完成工作区初始化，进入免打扰'")
    executed_action_summary: Optional[str] = Field(None, description="大脑双手执行的工具结果摘要")
