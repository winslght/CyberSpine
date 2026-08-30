import pytest

from src.context.current_context import CurrentContextStore
from src.core.neural_message import MessageKind, NeuralMessage, PrivacyClass


def test_context_rejects_sensitive_and_non_readonly_messages():
    context = CurrentContextStore()
    with pytest.raises(ValueError, match="sensitive"):
        context.ingest(NeuralMessage(kind=MessageKind.STATE, source="peripheral.example",
                       topic="example.state", privacy=PrivacyClass.SENSITIVE))
    with pytest.raises(ValueError, match="cannot ingest"):
        context.ingest(NeuralMessage(kind=MessageKind.DIRECTIVE, source="spinal_hub", topic="sample"))


def test_context_deduplicates_message_ids():
    context = CurrentContextStore()
    message = NeuralMessage(kind=MessageKind.EVENT, source="peripheral.example", topic="example.changed")
    context.ingest(message)
    context.ingest(message)
    assert len(context.snapshot().recent_events) == 1
