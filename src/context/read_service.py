"""顶层大脑读取当前上下文的稳定应用接口。"""
from collections.abc import Callable
from copy import deepcopy

from pydantic import BaseModel, Field

from .current_context import CurrentContextSnapshot


CURRENT_CONTEXT_SCHEMA = "cyberspine.current_context@1"


class CurrentContextDocument(BaseModel):
    """可由 MCP、桌面控制台或其他宿主序列化的只读上下文文档。"""

    schema_id: str = Field(default=CURRENT_CONTEXT_SCHEMA, serialization_alias="schema")
    context: CurrentContextSnapshot


class CurrentContextReader:
    """将神经中枢快照稳定地暴露给上层适配器。

    此类不采样、不入队、不触发模型，也不执行动作；它仅返回已经被
    网关和隐私策略接受的上下文副本。
    """

    def __init__(self, snapshot_provider: Callable[[], CurrentContextSnapshot]):
        self._snapshot_provider = snapshot_provider

    def read(self) -> CurrentContextDocument:
        snapshot = self._snapshot_provider()
        return CurrentContextDocument(context=snapshot.model_copy(deep=True))

    def read_json(self) -> dict:
        """返回 JSON 兼容对象，供未来 MCP 工具直接使用。"""
        return deepcopy(self.read().model_dump(mode="json", by_alias=True))
