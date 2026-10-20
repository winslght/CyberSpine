"""神经中枢使用的本地持久消息队列。"""
import json
import sqlite3
import threading
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from .neural_message import MessageKind, NeuralMessage, utc_now


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    RESOLVED = "resolved"
    EXPIRED = "expired"


class QueueItem(BaseModel):
    message: NeuralMessage
    status: DeliveryStatus
    created_at: datetime
    updated_at: datetime
    delivery_attempts: int = 0


class DurableEventQueue:
    """SQLite 支持的本地事件队列，提供去重、合并、确认和过期处理。"""

    _ACTIVE_STATUSES = (DeliveryStatus.PENDING.value, DeliveryStatus.DELIVERED.value)

    def __init__(self, database_path: Path | str):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS neural_messages (
                    message_id TEXT PRIMARY KEY,
                    message_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    collapse_key TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    delivery_attempts INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_neural_messages_active
                ON neural_messages (status, collapse_key)
                """
            )

    def enqueue(self, message: NeuralMessage) -> QueueItem:
        """入队消息；相同 collapse_key 的未完成消息会被最新状态合并。"""
        with self._lock:
            self.expire_messages()
            now = utc_now()
            with self._connect() as connection:
                # Only state is replaceable. Events are historical facts: a
                # repeated collapse key cannot erase a real transition unless a
                # future explicit idempotency policy authorizes that separately.
                if message.kind is MessageKind.STATE and message.collapse_key:
                    rows = connection.execute(
                        """
                        SELECT * FROM neural_messages
                        WHERE collapse_key = ? AND status IN (?, ?)
                        ORDER BY created_at ASC
                        """,
                        (message.collapse_key, *self._ACTIVE_STATUSES),
                    ).fetchall()
                    # An earlier event may share this key. It is historical and
                    # must remain untouched; only an already-stored state is a
                    # valid replacement candidate.
                    existing = next((self._row_to_item(row) for row in rows
                                     if self._row_to_item(row).message.kind is MessageKind.STATE), None)
                    if existing:
                        merged = message.model_copy(update={"message_id": existing.message.message_id})
                        connection.execute(
                            """
                            UPDATE neural_messages
                            SET message_json = ?, updated_at = ?
                            WHERE message_id = ?
                            """,
                            (self._serialize(merged), now.isoformat(), merged.message_id),
                        )
                        return QueueItem(
                            message=merged,
                            status=existing.status,
                            created_at=existing.created_at,
                            updated_at=now,
                            delivery_attempts=existing.delivery_attempts,
                        )

                item = QueueItem(
                    message=message,
                    status=DeliveryStatus.PENDING,
                    created_at=now,
                    updated_at=now,
                )
                connection.execute(
                    """
                    INSERT INTO neural_messages
                    (message_id, message_json, status, collapse_key, created_at, updated_at, delivery_attempts)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message.message_id,
                        self._serialize(message),
                        item.status.value,
                        message.collapse_key,
                        now.isoformat(),
                        now.isoformat(),
                        item.delivery_attempts,
                    ),
                )
                return item

    def get(self, message_id: str) -> Optional[QueueItem]:
        with self._lock:
            self.expire_messages()
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT * FROM neural_messages WHERE message_id = ?", (message_id,)
                ).fetchone()
            return self._row_to_item(row) if row else None

    def pending(self) -> List[QueueItem]:
        with self._lock:
            self.expire_messages()
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT * FROM neural_messages WHERE status = ? ORDER BY created_at ASC",
                    (DeliveryStatus.PENDING.value,),
                ).fetchall()
            return [self._row_to_item(row) for row in rows]

    def status_counts(self) -> dict[str, int]:
        """Read-only delivery counts; deliberately never exposes message JSON."""
        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT status, COUNT(*) AS total FROM neural_messages GROUP BY status"
                ).fetchall()
            return {row["status"]: row["total"] for row in rows}

    def mark_delivered(self, message_id: str) -> QueueItem:
        return self._change_status(message_id, DeliveryStatus.DELIVERED, increment_attempts=True)

    def acknowledge(self, message_id: str, status: DeliveryStatus) -> QueueItem:
        if status not in {
            DeliveryStatus.ACKNOWLEDGED,
            DeliveryStatus.DEFERRED,
            DeliveryStatus.REJECTED,
            DeliveryStatus.RESOLVED,
        }:
            raise ValueError("acknowledgement requires a terminal or deferred status")
        return self._change_status(message_id, status)

    def expire_messages(self, now: Optional[datetime] = None) -> int:
        """将所有超过 TTL 且未完成的消息标记为过期。"""
        now = now or utc_now()
        expired_ids: List[str] = []
        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT * FROM neural_messages WHERE status IN (?, ?)", self._ACTIVE_STATUSES
                ).fetchall()
                for row in rows:
                    item = self._row_to_item(row)
                    if item.message.is_expired(now):
                        connection.execute(
                            "UPDATE neural_messages SET status = ?, updated_at = ? WHERE message_id = ?",
                            (DeliveryStatus.EXPIRED.value, now.isoformat(), item.message.message_id),
                        )
                        expired_ids.append(item.message.message_id)
        return len(expired_ids)

    def _change_status(
        self, message_id: str, status: DeliveryStatus, increment_attempts: bool = False
    ) -> QueueItem:
        with self._lock:
            self.expire_messages()
            now = utc_now()
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT * FROM neural_messages WHERE message_id = ?", (message_id,)
                ).fetchone()
                if row is None:
                    raise KeyError(f"Unknown message: {message_id}")
                item = self._row_to_item(row)
                if item.status == DeliveryStatus.EXPIRED:
                    raise ValueError("Expired messages cannot change state")
                attempts = item.delivery_attempts + int(increment_attempts)
                connection.execute(
                    """
                    UPDATE neural_messages
                    SET status = ?, updated_at = ?, delivery_attempts = ?
                    WHERE message_id = ?
                    """,
                    (status.value, now.isoformat(), attempts, message_id),
                )
                return item.model_copy(
                    update={"status": status, "updated_at": now, "delivery_attempts": attempts}
                )

    @staticmethod
    def _serialize(message: NeuralMessage) -> str:
        return json.dumps(message.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> QueueItem:
        return QueueItem(
            message=NeuralMessage.model_validate_json(row["message_json"]),
            status=DeliveryStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            delivery_attempts=row["delivery_attempts"],
        )
