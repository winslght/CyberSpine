"""基于官方 MCP Python SDK 的只读上下文适配器。"""
from src.context.read_service import CurrentContextReader


def create_context_server(context_reader: CurrentContextReader):
    """创建 MCP 服务；协议、stdio 和生命周期均由 SDK 承担。"""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as error:  # pragma: no cover - 仅在缺失运行依赖时触发
        raise RuntimeError("MCP adapter requires the 'mcp' project dependency") from error

    server = FastMCP(
        "CyberSpine Context",
        instructions=("只读访问 CyberSpine 已脱敏的当前上下文。"
                      "此服务不会采样系统、唤醒模型或执行任何动作。"),
    )

    @server.tool()
    def cyberspine_get_current_context() -> dict:
        """读取版本化、脱敏且只读的当前神经上下文。"""
        return context_reader.read_json()

    return server
