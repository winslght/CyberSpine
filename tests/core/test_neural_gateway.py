import pytest

from src.core.event_queue import DurableEventQueue
from src.core.neural_gateway import GatewayRejected, NeuralSignalGateway, PeripheralRegistration
from src.core.neural_message import MessageKind, NeuralMessage, PrivacyClass


@pytest.fixture
def gateway(tmp_path):
    result = NeuralSignalGateway(DurableEventQueue(tmp_path / "signals.db"))
    result.register(PeripheralRegistration.create("peripheral.window.activity",
                    {"window.current_state", "window.focus_changed"}))
    return result


def test_gateway_accepts_registered_window_signal(gateway):
    item = gateway.publish(NeuralMessage(kind=MessageKind.EVENT, source="peripheral.window.activity",
                           topic="window.focus_changed", payload_schema="window.focus_changed@1",
                           payload={"current": {"application": "explorer.exe"}}, privacy=PrivacyClass.METADATA_ONLY))
    assert item.message.source == "peripheral.window.activity"
    assert gateway.queue.pending()[0].message.message_id == item.message.message_id


def test_gateway_rejects_unregistered_source(gateway):
    with pytest.raises(GatewayRejected, match="unregistered"):
        gateway.publish(NeuralMessage(kind=MessageKind.EVENT, source="peripheral.unknown", topic="x"))


def test_gateway_rejects_ungranted_topic(gateway):
    with pytest.raises(GatewayRejected, match="topic not granted"):
        gateway.publish(NeuralMessage(kind=MessageKind.EVENT, source="peripheral.window.activity", topic="system.shutdown"))


def test_gateway_rejects_sensitive_data_without_grant(gateway):
    with pytest.raises(GatewayRejected, match="privacy level"):
        gateway.publish(NeuralMessage(kind=MessageKind.EVENT, source="peripheral.window.activity",
                        topic="window.focus_changed", privacy=PrivacyClass.SENSITIVE))
