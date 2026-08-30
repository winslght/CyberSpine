"""
CyberSpine Model Context Protocol (MCP) 服务端协议与 6 大工具单元测试套件
"""
import sys
import os
import json
import unittest
from pathlib import Path

# 确保路径
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.mcp.server import CyberSpineMCPServer
from src.mcp.schemas import CYBERSPINE_TOOLS, MCP_PROTOCOL_VERSION


class TestCyberSpineMCPServer(unittest.TestCase):

    def setUp(self):
        self.server = CyberSpineMCPServer()

    def test_01_initialize_handshake(self):
        """测试 1: MCP 握手协议 initialize 请求与响应"""
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "clientInfo": {"name": "antigravity-master-cortex", "version": "2.0.0"}
            }
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        self.assertEqual(resp["id"], 1)
        self.assertIn("result", resp)
        self.assertEqual(resp["result"]["protocolVersion"], MCP_PROTOCOL_VERSION)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "cyberspine-neural-link")

        print("\n--- [TEST 1: MCP Handshake Initialize] ---")
        print(f"[PASS] 协议版本: {resp['result']['protocolVersion']}")
        print(f"[PASS] 节点名称: {resp['result']['serverInfo']['name']}")

    def test_02_tools_list(self):
        """测试 2: MCP 列举可用神经中枢工具 tools/list"""
        req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        self.assertEqual(resp["id"], 2)
        tools = resp["result"]["tools"]
        self.assertEqual(len(tools), 6)

        tool_names = [t["name"] for t in tools]
        self.assertIn("cyberspine_get_world_briefing", tool_names)
        self.assertIn("cyberspine_get_somatic_state", tool_names)
        self.assertIn("cyberspine_get_pacemaker_ticks", tool_names)
        self.assertIn("cyberspine_get_cognitive_telemetry", tool_names)
        self.assertIn("cyberspine_propose_motor_action", tool_names)
        self.assertIn("cyberspine_set_downward_inhibition", tool_names)

        print("\n--- [TEST 2: MCP Tools List] ---")
        print(f"[PASS] 暴露工具数: {len(tools)} 个 ({', '.join(tool_names)})")

    def test_03_call_get_world_briefing(self):
        """测试 3: 调用 cyberspine_get_world_briefing 获取 4 维全景简报与升级裁决"""
        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "cyberspine_get_world_briefing",
                "arguments": {"force_live_inference": False}
            }
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        content_text = resp["result"]["content"][0]["text"]
        data = json.loads(content_text)

        self.assertIn("briefing", data)
        self.assertIn("escalation_decision", data)
        b = data["briefing"]
        self.assertIn("summary", b)
        self.assertIn("user_activity", b)
        self.assertIn("attention_focus", b)

        print("\n--- [TEST 3: MCP Tool Call - World Briefing] ---")
        print(f"[PASS] 电脑简报: {b['summary'][:60]}...")
        print(f"[PASS] 用户工作: {b['user_activity']}")
        print(f"[PASS] 注意力焦点: {b['attention_focus']}")
        print(f"[PASS] 大脑升级裁决: {data['escalation_decision']}")

    def test_04_call_get_somatic_state(self):
        """测试 4: 调用 cyberspine_get_somatic_state 获取 8 大物理感官拓扑"""
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "cyberspine_get_somatic_state",
                "arguments": {"channel_filter": "nerve.system"}
            }
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        content_text = resp["result"]["content"][0]["text"]
        data = json.loads(content_text)

        self.assertIn("channels", data)
        self.assertGreaterEqual(data["total_channels"], 1)

        print("\n--- [TEST 4: MCP Tool Call - Somatic State] ---")
        print(f"[PASS] 过滤通道数: {data['total_channels']}")
        print(f"[PASS] 通道名称: {list(data['channels'].keys())}")

    def test_05_call_set_downward_inhibition(self):
        """测试 5: 调用 cyberspine_set_downward_inhibition 设置下行抑制"""
        req = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "cyberspine_set_downward_inhibition",
                "arguments": {"duration_seconds": 120, "reason": "MCP自动化测试免打扰"}
            }
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        content_text = resp["result"]["content"][0]["text"]
        data = json.loads(content_text)

        self.assertTrue(data.get("is_inhibited"))
        self.assertEqual(data.get("duration_seconds"), 120)

        print("\n--- [TEST 5: MCP Tool Call - Downward Inhibition] ---")
        print(f"[PASS] 抑制状态: {data['status']}")


if __name__ == '__main__':
    unittest.main()
