"""MCP 适配器；不包含内部神经通信语义。"""

from .context_server import create_context_server

__all__ = ["create_context_server"]
