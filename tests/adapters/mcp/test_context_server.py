import json

import pytest


@pytest.mark.asyncio
async def test_context_server_registers_only_the_read_contract():
    pytest.importorskip("mcp")
    from src.adapters.mcp.context_server import create_context_server
    from src.context.current_context import CurrentContextStore
    from src.context.read_service import CurrentContextReader

    server = create_context_server(CurrentContextReader(CurrentContextStore().snapshot))

    assert server.name == "CyberSpine Context"
    assert [tool.name for tool in await server.list_tools()] == ["cyberspine_get_current_context"]


@pytest.mark.asyncio
async def test_context_server_calls_the_versioned_reader():
    pytest.importorskip("mcp")
    from src.adapters.mcp.context_server import create_context_server
    from src.context.current_context import CurrentContextStore
    from src.context.read_service import CURRENT_CONTEXT_SCHEMA, CurrentContextReader
    from src.core.neural_message import MessageKind, NeuralMessage

    store = CurrentContextStore()
    store.ingest(NeuralMessage(kind=MessageKind.STATE, source="peripheral.window.activity",
                 topic="window.current_state", payload={"application": "code.exe"}))
    server = create_context_server(CurrentContextReader(store.snapshot))

    result = await server.call_tool("cyberspine_get_current_context", {})

    document = json.loads(result[0].text)
    assert document["schema"] == CURRENT_CONTEXT_SCHEMA
    assert document["context"]["states"]["window.current_state"]["application"] == "code.exe"
