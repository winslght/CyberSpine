"""统一神经通信规范的基础消息模型。"""
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MessageKind(str, Enum):
    """同一通信主干上的六种语义类别。"""

    STATE = "state"
    EVENT = "event"
    DIRECTIVE = "directive"
    PROPOSAL = "proposal"
    RESULT = "result"
    HEALTH = "health"


class MessagePriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class PrivacyClass(str, Enum):
    PUBLIC = "public"
    METADATA_ONLY = "metadata_only"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"


class NeuralMessage(BaseModel):
    """所有组件经过神经信号网关时使用的统一消息信封。"""

    protocol_version: str = "1.0"
    message_id: str = Field(default_factory=lambda: f"msg_{uuid4().hex}")
    timestamp: datetime = Field(default_factory=utc_now)
    kind: MessageKind
    source: str
    target: Optional[str] = None
    topic: str
    priority: MessagePriority = MessagePriority.NORMAL
    privacy: PrivacyClass = PrivacyClass.METADATA_ONLY
    ttl_seconds: Optional[int] = Field(default=None, gt=0)
    correlation_id: Optional[str] = None
    payload_schema: str = "generic@1"
    payload: Dict[str, Any] = Field(default_factory=dict)
    extensions: Dict[str, Any] = Field(default_factory=dict)
    collapse_key: Optional[str] = None
    requires_ack: bool = False

    @field_validator("source", "topic", "payload_schema")
    @classmethod
    def require_nonempty_identifier(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("identifier must not be empty")
        return value

    @property
    def expires_at(self) -> Optional[datetime]:
        if self.ttl_seconds is None:
            return None
        return self.timestamp + timedelta(seconds=self.ttl_seconds)

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        expires_at = self.expires_at
        return expires_at is not None and expires_at <= (now or utc_now())

