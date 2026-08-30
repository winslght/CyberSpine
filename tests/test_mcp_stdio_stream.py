"""
CyberSpine MCP Stdio 进程级双向管道通信实机单元测试
真实拉起 python src/mcp/server.py 子进程，通过 stdin/stdout 管道测试 JSON-RPC 2.0 数据纯净度与握手。
"""
import sys
import os
import json
import time
import subprocess
import unittest
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent


class TestMCPStdioStream(unittest.TestCase):

    def test_stdio_handshake_and_tool_call(self):
        """测试通过真实 Stdio 管道拉起 MCP 节点并进行 initialize/tools/call"""
        python_exe = sys.executable

        # 启动 MCP Server 子进程
        proc = subprocess.Popen(
            [python_exe, "src/mcp/server.py"],
            cwd=str(repo_root),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1
        )

        try:
            # 1. 发送 initialize 请求
            init_req = {
                "jsonrpc": "2.0",
                "id": "req-init-1",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "antigravity-test-client", "version": "1.0.0"}
                }
            }
            proc.stdin.write(json.dumps(init_req) + "\n")
            proc.stdin.flush()

            # 读取第一行输出 (必须是合法的 JSON-RPC，不能有任何前缀字符如 'P' 或 '[')
            raw_init_resp = proc.stdout.readline()
            self.assertTrue(raw_init_resp, "MCP server stdout is empty on initialize")
            self.assertTrue(raw_init_resp.startswith("{"), f"Stdout does not start with '{{': {raw_init_resp[:50]}")
            init_resp = json.loads(raw_init_resp)
            self.assertEqual(init_resp.get("id"), "req-init-1")
            self.assertEqual(init_resp["result"]["serverInfo"]["name"], "cyberspine-neural-link")

            # 2. 发送 tools/list 请求
            tools_req = {
                "jsonrpc": "2.0",
                "id": "req-tools-2",
                "method": "tools/list"
            }
            proc.stdin.write(json.dumps(tools_req) + "\n")
            proc.stdin.flush()

            raw_tools_resp = proc.stdout.readline()
            tools_resp = json.loads(raw_tools_resp)
            self.assertEqual(tools_resp.get("id"), "req-tools-2")
            tools = tools_resp["result"]["tools"]
            self.assertEqual(len(tools), 6)

            # 3. 发送 tools/call cyberspine_get_world_briefing
            call_req = {
                "jsonrpc": "2.0",
                "id": "req-call-3",
                "method": "tools/call",
                "params": {
                    "name": "cyberspine_get_world_briefing",
                    "arguments": {"force_live_inference": False}
                }
            }
            proc.stdin.write(json.dumps(call_req) + "\n")
            proc.stdin.flush()

            raw_call_resp = proc.stdout.readline()
            call_resp = json.loads(raw_call_resp)
            self.assertEqual(call_resp.get("id"), "req-call-3")
            briefing_text = call_resp["result"]["content"][0]["text"]
            briefing_data = json.loads(briefing_text)

            self.assertIn("briefing", briefing_data)
            self.assertIn("escalation_decision", briefing_data)

            print("\n--- [MCP Real Subprocess Pipe Test Passed] ---")
            print(f"[PASS] 握手成功: {init_resp['result']['serverInfo']['name']}")
            print(f"[PASS] 工具列表就绪: {len(tools)} tools")
            print(f"[PASS] 实时感知简报提取成功: {briefing_data['briefing']['summary'][:40]}...")

        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except Exception:
                proc.kill()


if __name__ == '__main__':
    unittest.main()
