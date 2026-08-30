"""最小神经中枢：把参考末梢神经接入网关与只读上下文。"""
from pathlib import Path
from typing import Optional

from src.core.event_queue import DurableEventQueue, QueueItem
from src.core.neural_gateway import NeuralSignalGateway, PeripheralRegistration
from src.sensing.window_activity import WindowActivityPeripheral

from .current_context import CurrentContextSnapshot, CurrentContextStore
from .read_service import CurrentContextReader


class NeuralSpinalHub:
    """当前仅承载窗口感知，刻意不接管旧的全量轮询中枢。"""

    def __init__(self, database_path: Path | str, window_peripheral: Optional[WindowActivityPeripheral] = None):
        self.queue = DurableEventQueue(database_path)
        self.gateway = NeuralSignalGateway(self.queue)
        self.context = CurrentContextStore()
        self.context_reader = CurrentContextReader(self.current_context)
        self.window = window_peripheral or WindowActivityPeripheral()
        self.gateway.register(PeripheralRegistration.create(self.window.source,
                              {self.window.state_topic, self.window.catalog_topic,
                               self.window.event_topic, self.window.activity_topic,
                               self.window.time_window_topic, self.window.availability_topic}))

    def collect_window(self) -> list[QueueItem]:
        """采样窗口感知并以“网关成功后才投影上下文”的顺序处理。"""
        items = []
        for message in self.window.collect_messages():
            item = self.gateway.publish(message)
            self.context.ingest(item.message)
            items.append(item)
        return items

    def current_context(self) -> CurrentContextSnapshot:
        return self.context.snapshot()

    def read_current_context(self) -> dict:
        """供外部适配器调用的 JSON 兼容只读上下文接口。"""
        return self.context_reader.read_json()
