from datetime import timedelta

import pytest

from src.core.event_queue import DeliveryStatus, DurableEventQueue
from src.core.neural_message import MessageKind, NeuralMessage, utc_now


@pytest.fixture
def queue(tmp_path):
    return DurableEventQueue(tmp_path / "events.sqlite3")


def make_event(**overrides):
    values = {
        "kind": MessageKind.EVENT,
        "source": "peripheral.window.activity",
        "topic": "window.focus_changed",
        "payload_schema": "window.focus_changed@1",
        "payload": {"application": "Code.exe"},
    }
    values.update(overrides)
    return NeuralMessage(**values)


def test_enqueues_and_reloads_a_message(queue):
    item = queue.enqueue(make_event())

    restored = queue.get(item.message.message_id)

    assert restored is not None
    assert restored.status is DeliveryStatus.PENDING
    assert restored.message.topic == "window.focus_changed"


def test_collapse_key_merges_pending_events(queue):
    first = queue.enqueue(make_event(collapse_key="foreground"))
    second = queue.enqueue(
        make_event(collapse_key="foreground", payload={"application": "Terminal.exe"})
    )

    assert first.message.message_id == second.message.message_id
    assert len(queue.pending()) == 1
    assert queue.pending()[0].message.payload["application"] == "Terminal.exe"


def test_delivery_and_acknowledgement_are_persisted(queue):
    item = queue.enqueue(make_event())

    delivered = queue.mark_delivered(item.message.message_id)
    acknowledged = queue.acknowledge(item.message.message_id, DeliveryStatus.ACKNOWLEDGED)

    assert delivered.status is DeliveryStatus.DELIVERED
    assert delivered.delivery_attempts == 1
    assert acknowledged.status is DeliveryStatus.ACKNOWLEDGED
    assert queue.pending() == []


def test_expired_messages_are_not_delivered(queue):
    message = make_event(ttl_seconds=1, timestamp=utc_now() - timedelta(seconds=2))
    item = queue.enqueue(message)

    assert queue.expire_messages() == 1
    assert queue.get(item.message.message_id).status is DeliveryStatus.EXPIRED
    with pytest.raises(ValueError, match="Expired"):
        queue.mark_delivered(item.message.message_id)
