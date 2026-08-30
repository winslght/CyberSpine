"""
CyberSpine 原生 MCP JSON-RPC 2.0 Stdio 协议引擎 (Dual-Stream Isolation Architecture)
遵循 Model Context Protocol (MCP) 规范，为高级主体大脑 (Antigravity/Claude/DeepSeek) 提供零开销、零污染的实时神经连接。
"""
import sys
import os
import json
import traceback
from typing import Dict, Any, Optional
from pathlib import Path

# ================= 1. 标准输出流绝对隔离 (Dual-Stream Isolation) =================
# 立即捕获底层真实标准输出流，供 JSON-RPC 协议通道独占使用
_real_stdout = sys.stdout
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        _real_stdout = sys.stdout
    except Exception:
        pass

if hasattr(sys.stdin, "reconfigure"):
    try:
        sys.stdin.reconfigure(encoding='utf-8')
    except Exception:
        pass

if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ================= 2. 导入业务模块 =================
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.mcp.schemas import MCP_SERVER_INFO, MCP_PROTOCOL_VERSION, CYBERSPINE_TOOLS
from src.mcp.tools import CyberSpineMCPHandlers


def _log(msg: str):
    """通过 stderr 输出调试日志，MCP 宿主会将其作为后台日志接收，完全不干扰 JSON-RPC"""
    sys.stderr.write(f"[CyberSpine-MCP] {msg}\n")
    sys.stderr.flush()


class CyberSpineMCPServer:
    """CyberSpine 原生 Stdio MCP 服务端"""

    def __init__(self):
        self.handlers = CyberSpineMCPHandlers.get_instance()
        _log("CyberSpine MCP 服务引擎初始化就绪")

    def handle_request(self, req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """分发处理单个 JSON-RPC 请求"""
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if not method:
            return None

        # 1. 协议握手初始化 (initialize)
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": MCP_SERVER_INFO,
                    "instructions": "CyberSpine 是仿生端侧神经中枢系统。通过本 MCP 节点，高级大脑可以获取宿主计算机的物理感官、1分钟世界简报与注意力焦点，并可下发运动控制指令。"
                }
            }

        # 2. 初始化确认通知 (notifications/initialized)
        if method == "notifications/initialized":
            _log("高级大脑握手确认完成 (initialized)")
            return None

        # 3. 探活 ping
        if method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {}
            }

        # 4. 列举可用工具 (tools/list)
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": CYBERSPINE_TOOLS
                }
            }

        # 5. 执行工具调用 (tools/call)
        if method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})
            return self._dispatch_tool_call(req_id, tool_name, args)

        # 未知方法错误响应
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }

    def _dispatch_tool_call(self, req_id: Any, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行具体工具调用并格式化为标准 MCP Content"""
        _log(f"调用工具: {tool_name} | 参数: {json.dumps(args, ensure_ascii=False)}")
        try:
            if tool_name == "cyberspine_get_world_briefing":
                force_live = args.get("force_live_inference", False)
                res = self.handlers.get_world_briefing(force_live_inference=force_live)

            elif tool_name == "cyberspine_get_somatic_state":
                channel_filter = args.get("channel_filter")
                res = self.handlers.get_somatic_state(channel_filter=channel_filter)

            elif tool_name == "cyberspine_get_pacemaker_ticks":
                limit = args.get("limit", 12)
                res = self.handlers.get_pacemaker_ticks(limit=limit)

            elif tool_name == "cyberspine_get_cognitive_telemetry":
                limit = args.get("limit", 30)
                category = args.get("category")
                res = self.handlers.get_cognitive_telemetry(limit=limit, category=category)

            elif tool_name == "cyberspine_propose_motor_action":
                action_type = args.get("action_type", "")
                params = args.get("params", {})
                reason = args.get("reason", "")
                res = self.handlers.propose_motor_action(action_type=action_type, params=params, reason=reason)

            elif tool_name == "cyberspine_set_downward_inhibition":
                duration = args.get("duration_seconds", 300)
                reason = args.get("reason", "高级大脑设定免打扰")
                res = self.handlers.set_downward_inhibition(duration_seconds=duration, reason=reason)

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32602,
                        "message": f"Unknown tool name: {tool_name}"
                    }
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(res, default=str, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            }

        except Exception as e:
            _log(f"工具执行异常: {e}\n{traceback.format_exc()}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error executing tool {tool_name}: {str(e)}"
                        }
                    ]
                }
            }

    def run_stdio(self):
        """标准 Stdio 事件循环 (100% 独占 _real_stdout 写入 JSON-RPC)"""
        # 将全局 sys.stdout 重定向至 sys.stderr，彻底杜绝任何内部模块与 print 语句污染协议流
        sys.stdout = sys.stderr
        _log("CyberSpine Stdio MCP 传输层已启动，正在监听 stdin...")
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                resp = self.handle_request(req)
                if resp is not None:
                    json_str = json.dumps(resp, ensure_ascii=False)
                    _real_stdout.write(json_str + "\n")
                    _real_stdout.flush()
            except json.JSONDecodeError as e:
                _log(f"JSON 解析错误: {e}")
            except Exception as e:
                _log(f"请求处理异常: {e}")


if __name__ == "__main__":
    server = CyberSpineMCPServer()
    server.run_stdio()
