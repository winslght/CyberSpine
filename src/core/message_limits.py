"""Pure structural limits applied before a message enters durable storage."""

from __future__ import annotations

import json
from typing import Any

from .gateway_errors import GatewayRejected, GatewayRejectionCode
from .neural_message import NeuralMessage


class MessageLimits:
    def __init__(
        self,
        maximum_bytes: int = 65_536,
        maximum_depth: int = 8,
        maximum_items: int = 128,
        maximum_string_bytes: int = 8_192,
    ) -> None:
        self.maximum_bytes, self.maximum_depth = maximum_bytes, maximum_depth
        self.maximum_items, self.maximum_string_bytes = maximum_items, maximum_string_bytes

    def validate_size(self, message: NeuralMessage) -> None:
        self._validate_value(message.payload)
        try:
            encoded = json.dumps(
                message.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")
            )
        except (TypeError, ValueError) as error:
            raise GatewayRejected(
                GatewayRejectionCode.SCHEMA_INVALID, "message is not JSON-compatible"
            ) from error
        if len(encoded.encode("utf-8")) > self.maximum_bytes:
            raise GatewayRejected(GatewayRejectionCode.MESSAGE_TOO_LARGE)

    def _validate_value(self, value: Any, depth: int = 0) -> None:
        if depth > self.maximum_depth:
            raise GatewayRejected(
                GatewayRejectionCode.MESSAGE_TOO_LARGE, "payload nesting exceeds limit"
            )
        if isinstance(value, str):
            if len(value.encode("utf-8")) > self.maximum_string_bytes:
                raise GatewayRejected(
                    GatewayRejectionCode.MESSAGE_TOO_LARGE, "string exceeds limit"
                )
        elif value is None or isinstance(value, (bool, int, float)):
            return
        elif isinstance(value, dict):
            if len(value) > self.maximum_items:
                raise GatewayRejected(GatewayRejectionCode.MESSAGE_TOO_LARGE)
            for key, item in value.items():
                if not isinstance(key, str):
                    raise GatewayRejected(GatewayRejectionCode.SCHEMA_INVALID)
                self._validate_value(key, depth + 1)
                self._validate_value(item, depth + 1)
        elif isinstance(value, (list, tuple)):
            if len(value) > self.maximum_items:
                raise GatewayRejected(GatewayRejectionCode.MESSAGE_TOO_LARGE)
            for item in value:
                self._validate_value(item, depth + 1)
        else:
            raise GatewayRejected(GatewayRejectionCode.SCHEMA_INVALID)
