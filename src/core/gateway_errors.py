"""Stable, payload-safe rejection results for the neural gateway."""
from enum import Enum


class GatewayRejectionCode(str, Enum):
    """Reasons exposed to callers and audit sinks without echoing payload data."""

    PROTOCOL_UNSUPPORTED = "protocol_unsupported"
    MANIFEST_INVALID = "manifest_invalid"
    SESSION_INVALID = "session_invalid"
    TOPIC_NOT_GRANTED = "topic_not_granted"
    PRIVACY_EXCEEDED = "privacy_exceeded"
    SCHEMA_INVALID = "schema_invalid"
    MESSAGE_TOO_LARGE = "message_too_large"
    MESSAGE_EXPIRED = "message_expired"
    TIMESTAMP_INVALID = "timestamp_invalid"
    KIND_NOT_GRANTED = "kind_not_granted"
    SOURCE_MISMATCH = "source_mismatch"
    RATE_LIMITED = "rate_limited"
    INSTANCE_UNHEALTHY = "instance_unhealthy"
    AUDIT_UNAVAILABLE = "audit_unavailable"
    QUEUE_UNAVAILABLE = "queue_unavailable"


class GatewayRejected(ValueError):
    """A safe rejection which deliberately contains no payload representation."""

    def __init__(self, code: GatewayRejectionCode, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        message = code.value if not detail else f"{code.value}: {detail}"
        super().__init__(message)
