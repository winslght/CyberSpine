"""统一神经信号网关：插件进入主干的唯一准入点。"""
from dataclasses import dataclass
from typing import FrozenSet, Iterable, Optional

from .event_queue import DurableEventQueue, QueueItem
from .neural_message import MessageKind, NeuralMessage, PrivacyClass


class GatewayRejected(ValueError):
    """消息不符合已登记插件的能力或隐私边界。"""


@dataclass(frozen=True)
class PeripheralRegistration:
    """一个末梢神经可发布的消息范围。topic 目前采用精确匹配。"""

    source: str
    topics: FrozenSet[str]
    kinds: FrozenSet[MessageKind] = frozenset({MessageKind.STATE, MessageKind.EVENT, MessageKind.HEALTH})
    maximum_privacy: PrivacyClass = PrivacyClass.METADATA_ONLY

    @classmethod
    def create(cls, source: str, topics: Iterable[str], kinds: Optional[Iterable[MessageKind]] = None,
               maximum_privacy: PrivacyClass = PrivacyClass.METADATA_ONLY) -> "PeripheralRegistration":
        return cls(source, frozenset(topics), frozenset(kinds) if kinds is not None else cls.kinds, maximum_privacy)


class NeuralSignalGateway:
    """验证来源能力后，将合格消息写入持久队列。"""

    _SUPPORTED_PROTOCOLS = frozenset({"1.0"})
    _PRIVACY_ORDER = {PrivacyClass.PUBLIC: 0, PrivacyClass.METADATA_ONLY: 1,
                      PrivacyClass.SENSITIVE: 2, PrivacyClass.RESTRICTED: 3}

    def __init__(self, queue: DurableEventQueue):
        self.queue = queue
        self._registrations: dict[str, PeripheralRegistration] = {}

    def register(self, registration: PeripheralRegistration) -> None:
        if not registration.source.strip() or not registration.topics:
            raise ValueError("registration requires a source and at least one topic")
        self._registrations[registration.source] = registration

    def publish(self, message: NeuralMessage) -> QueueItem:
        registration = self._registrations.get(message.source)
        if registration is None:
            raise GatewayRejected(f"unregistered source: {message.source}")
        if message.protocol_version not in self._SUPPORTED_PROTOCOLS:
            raise GatewayRejected(f"unsupported protocol version: {message.protocol_version}")
        if message.topic not in registration.topics:
            raise GatewayRejected(f"topic not granted to {message.source}: {message.topic}")
        if message.kind not in registration.kinds:
            raise GatewayRejected(f"message kind not granted to {message.source}: {message.kind.value}")
        if self._PRIVACY_ORDER[message.privacy] > self._PRIVACY_ORDER[registration.maximum_privacy]:
            raise GatewayRejected(f"privacy level exceeds grant for {message.source}")
        if message.is_expired():
            raise GatewayRejected("expired messages cannot enter the gateway")
        return self.queue.enqueue(message)
