"""Pure health observations and sticky gateway health conclusions."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum


class HealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    PAUSED = "paused"
    QUARANTINED = "quarantined"


@dataclass(frozen=True)
class HealthKey:
    plugin_id: str
    instance_id: str


@dataclass(frozen=True)
class HealthAssessment:
    key: HealthKey
    state: HealthState
    last_seen_age_seconds: float
    rejection_count: int
    reason: str


class PluginHealthMonitor:
    """Derive health from gateway observations, never a plugin self-report."""

    def __init__(
        self,
        stale_after_seconds: float = 60,
        degraded_after_rejections: int = 3,
        paused_after_rejections: int = 5,
        quarantined_after_rejections: int = 8,
        clock=time.monotonic,
    ) -> None:
        if not (
            0 < stale_after_seconds
            and 0 < degraded_after_rejections <= paused_after_rejections <= quarantined_after_rejections
        ):
            raise ValueError("health thresholds must be positive and ordered")
        self.stale_after_seconds = stale_after_seconds
        self.degraded_after_rejections = degraded_after_rejections
        self.paused_after_rejections = paused_after_rejections
        self.quarantined_after_rejections = quarantined_after_rejections
        self._clock = clock
        self._seen: dict[HealthKey, float] = {}
        self._rejections: dict[HealthKey, int] = {}
        self._sticky: dict[HealthKey, HealthState] = {}
        self._lock = threading.RLock()

    def observe(self, key: HealthKey, *, accepted: bool) -> None:
        with self._lock:
            self._seen[key] = self._clock()
            if not accepted:
                self._rejections[key] = self._rejections.get(key, 0) + 1

    def pause(self, key: HealthKey) -> None:
        with self._lock:
            self._sticky[key] = HealthState.PAUSED

    def quarantine(self, key: HealthKey) -> None:
        with self._lock:
            self._sticky[key] = HealthState.QUARANTINED

    def reset(self, key: HealthKey) -> None:
        """Explicit recovery hook; authorization belongs to a later control plane."""
        with self._lock:
            self._sticky.pop(key, None)
            self._rejections[key] = 0
            self._seen[key] = self._clock()

    def assess(self, key: HealthKey) -> HealthAssessment:
        with self._lock:
            age = max(0.0, self._clock() - self._seen.get(key, float("-inf")))
            rejected = self._rejections.get(key, 0)
            sticky = self._sticky.get(key)
            if sticky is HealthState.QUARANTINED:
                state, reason = sticky, "explicit_isolation"
            elif rejected >= self.quarantined_after_rejections:
                state, reason = HealthState.QUARANTINED, "rejection_threshold"
                self._sticky[key] = state
            elif sticky is HealthState.PAUSED:
                state, reason = sticky, "explicit_isolation"
            elif rejected >= self.paused_after_rejections:
                state, reason = HealthState.PAUSED, "rejection_threshold"
                self._sticky[key] = state
            elif rejected >= self.degraded_after_rejections:
                state, reason = HealthState.DEGRADED, "rejection_threshold"
            elif age > self.stale_after_seconds:
                state, reason = HealthState.DEGRADED, "stale"
            else:
                state, reason = HealthState.HEALTHY, "fresh"
            return HealthAssessment(key, state, age, rejected, reason)
