"""In-memory, per-session/topic token-bucket flow policy."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from .gateway_errors import GatewayRejected, GatewayRejectionCode
from .neural_message import MessageKind, NeuralMessage
from .plugin_registration import PluginSession


@dataclass
class _Bucket:
    tokens: float
    updated_at: float


class RateLimitPolicy:
    def __init__(
        self, capacity: int = 30, refill_per_second: float = 5.0, clock=time.monotonic
    ) -> None:
        if capacity <= 0 or refill_per_second <= 0:
            raise ValueError("capacity and refill_per_second must be positive")
        self.capacity, self.refill_per_second, self._clock, self._buckets = (
            capacity,
            refill_per_second,
            clock,
            {},
        )
        self._lock = threading.RLock()

    def allow(self, session: PluginSession, message: NeuralMessage) -> None:
        key, now = (session.plugin_id, session.instance_id, session.session_id, message.topic), self._clock()
        with self._lock:
            bucket = self._buckets.setdefault(key, _Bucket(float(self.capacity), now))
            elapsed = max(0.0, now - bucket.updated_at)
            bucket.tokens = min(float(self.capacity), bucket.tokens + elapsed * self.refill_per_second)
            bucket.updated_at = max(bucket.updated_at, now)
            if bucket.tokens < 1:
                raise GatewayRejected(GatewayRejectionCode.RATE_LIMITED)
            bucket.tokens -= 1


class StateCollapsePolicy:
    def key_for(self, message: NeuralMessage) -> str | None:
        return message.collapse_key if message.kind is MessageKind.STATE else None
