"""从统一消息构建只读当前上下文。"""
from copy import deepcopy
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from src.core.neural_message import MessageKind, NeuralMessage, PrivacyClass, utc_now


class ContextEvent(BaseModel):
    message_id: str
    topic: str
    timestamp: datetime
    payload_schema: str
    payload: dict[str, Any]


class CurrentContextSnapshot(BaseModel):
    """提供给顶层大脑的只读快照，不含待执行指令或敏感载荷。"""

    context_id: str = Field(default_factory=lambda: f"ctx_{uuid4().hex}")
    captured_at: datetime = Field(default_factory=utc_now)
    states: dict[str, dict[str, Any]] = Field(default_factory=dict)
    recent_events: list[ContextEvent] = Field(default_factory=list)
    health: dict[str, dict[str, Any]] = Field(default_factory=dict)
    privacy: PrivacyClass = PrivacyClass.METADATA_ONLY


class CurrentContextStore:
    """内存中的当前上下文投影；只接收可对上层公开的只读消息。"""

    _ALLOWED_KINDS = {MessageKind.STATE, MessageKind.EVENT, MessageKind.HEALTH}

    def __init__(self, event_limit: int = 32):
        if event_limit < 1:
            raise ValueError("event_limit must be positive")
        self._event_limit = event_limit
        self._states: dict[str, dict[str, Any]] = {}
        self._health: dict[str, dict[str, Any]] = {}
        self._events: list[ContextEvent] = []
        self._event_positions: dict[str, int] = {}

    def ingest(self, message: NeuralMessage) -> None:
        if message.kind not in self._ALLOWED_KINDS:
            raise ValueError(f"context cannot ingest {message.kind.value} messages")
        if message.privacy not in {PrivacyClass.PUBLIC, PrivacyClass.METADATA_ONLY}:
            raise ValueError("sensitive messages require an explicit redaction adapter")
        if message.kind == MessageKind.STATE:
            self._states[message.topic] = dict(message.payload)
        elif message.kind == MessageKind.HEALTH:
            self._health[message.topic] = dict(message.payload)
        else:
            event = ContextEvent(message_id=message.message_id, topic=message.topic,
                                 timestamp=message.timestamp, payload_schema=message.payload_schema,
                                 payload=dict(message.payload))
            position = self._event_positions.get(message.message_id)
            if position is None:
                self._events.append(event)
            else:
                self._events[position] = event
            self._events = self._events[-self._event_limit:]
            self._event_positions = {event.message_id: index for index, event in enumerate(self._events)}

    def snapshot(self) -> CurrentContextSnapshot:
        return CurrentContextSnapshot(states=deepcopy(self._states), recent_events=deepcopy(self._events),
                                      health=deepcopy(self._health))
