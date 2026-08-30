from src.context.current_context import CurrentContextStore
from src.context.read_service import CURRENT_CONTEXT_SCHEMA, CurrentContextReader
from src.core.neural_message import MessageKind, NeuralMessage


def test_reader_returns_versioned_json_safe_copy():
    store = CurrentContextStore()
    store.ingest(NeuralMessage(kind=MessageKind.STATE, source="peripheral.window.activity",
                 topic="window.current_state", payload={"application": "code.exe"}))
    reader = CurrentContextReader(store.snapshot)

    document = reader.read_json()
    document["context"]["states"]["window.current_state"]["application"] = "mutated"

    assert document["schema"] == CURRENT_CONTEXT_SCHEMA
    assert store.snapshot().states["window.current_state"]["application"] == "code.exe"


def test_hub_exposes_same_versioned_read_contract(tmp_path):
    from src.context.spinal_hub import NeuralSpinalHub
    from src.sensing.window_activity import WindowActivityPeripheral

    hub = NeuralSpinalHub(tmp_path / "signals.db", WindowActivityPeripheral(
        lambda: {"active_process": "explorer.exe", "active_title": "Desktop", "active_pid": 1}
    ))
    hub.collect_window()

    document = hub.read_current_context()

    assert document["schema"] == CURRENT_CONTEXT_SCHEMA
    assert document["context"]["states"]["window.current_state"]["foreground"]["application"] == "explorer.exe"
