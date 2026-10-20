"""Minimal, redacted audit contracts owned by the gateway core."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


@dataclass(frozen=True)
class AuditEvent:
    action: str
    outcome: str
    occurred_at: datetime
    plugin_id: str | None = None
    instance_id: str | None = None
    source: str | None = None
    topic: str | None = None
    reason: str | None = None
    policy_id: str = "gateway.g2"


class AuditSink(Protocol):
    def record(self, event: AuditEvent) -> None: ...


class MemoryAuditSink:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)


def audit_event(
    action: str,
    outcome: str,
    *,
    plugin_id: str | None = None,
    instance_id: str | None = None,
    source: str | None = None,
    topic: str | None = None,
    reason: str | None = None,
) -> AuditEvent:
    """Build an event from safe metadata only; there is intentionally no payload field."""
    return AuditEvent(
        action,
        outcome,
        datetime.now(timezone.utc),
        plugin_id,
        instance_id,
        source,
        topic,
        reason,
    )
