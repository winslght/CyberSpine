"""
CyberSpine 神经感知与模型认知透视日志收集器 (Cognitive Telemetry Logger)
全透明追踪记录：① 真实物理机身体感知、② 脊髓中枢确认门控、③ 本地小模型思考链与动作生成。
"""
import os
import json
import time
import threading
from typing import Dict, Any, List, Optional
from collections import deque
from pathlib import Path

from src.models.somatic_signals import utc_now


class TelemetryCategory:
    SOMATIC = "SOMATIC"   # 真实物理机身体感知 (窗口/硬件/网络/存储)
    SPINAL = "SPINAL"     # 脊髓中枢时钟对齐与感知确认
    MODEL = "MODEL"       # 本地小模型神经网络推理与思考链
    ACTION = "ACTION"     # 运动神经元双手执行与安全三定律
    SYSTEM = "SYSTEM"     # 稳态能耗与下行抑制


class TelemetryFrame:
    """单条结构化认知透视帧"""
    def __init__(
        self,
        category: str,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        latency_ms: float = 0.0,
        level: str = "INFO"
    ):
        self.id = f"tel_{int(time.time() * 1000)}_{os.urandom(2).hex()}"
        self.timestamp = utc_now().strftime("%H:%M:%S.%f")[:-3]
        self.category = category
        self.title = title
        self.message = message
        self.details = details or {}
        self.latency_ms = latency_ms
        self.level = level

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "category": self.category,
            "title": self.title,
            "message": self.message,
            "details": self.details,
            "latency_ms": self.latency_ms,
            "level": self.level,
        }


class CognitiveTelemetryLogger:
    """全透明认知透视环形缓冲与持久化日志服务"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, max_buffer_size: int = 300):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CognitiveTelemetryLogger, cls).__new__(cls)
                cls._instance._init_logger(max_buffer_size)
            return cls._instance

    def _init_logger(self, max_buffer_size: int):
        self._buffer = deque(maxlen=max_buffer_size)
        self._buffer_lock = threading.Lock()

        # 日志持久化路径 (位于仓库根目录 runtime/logs/)
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.log_file = base_dir / "runtime" / "logs" / "cognitive_telemetry.jsonl"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # 初始系统启动日志帧
        self.record(
            category=TelemetryCategory.SYSTEM,
            title="认知透视引擎初始化",
            message="CyberSpine 神经中枢与物理实机认知透视监听器已挂载就绪。",
            details={"max_buffer_size": max_buffer_size}
        )

    def record(
        self,
        category: str,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        latency_ms: float = 0.0,
        level: str = "INFO"
    ) -> TelemetryFrame:
        """记录一条透视帧"""
        frame = TelemetryFrame(
            category=category,
            title=title,
            message=message,
            details=details,
            latency_ms=latency_ms,
            level=level
        )

        with self._buffer_lock:
            self._buffer.append(frame)

        # 异步追加落盘
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(frame.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass

        return frame

    def get_recent_frames(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近的认知透视帧列表"""
        with self._buffer_lock:
            items = list(self._buffer)[-limit:]
            return [f.to_dict() for f in items]

    def clear(self):
        """清空内存环形缓冲"""
        with self._buffer_lock:
            self._buffer.clear()
            self.record(
                category=TelemetryCategory.SYSTEM,
                title="控制台清屏",
                message="用户手动清空了当前认知透视终端显示缓冲区。"
            )
