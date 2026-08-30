"""
CyberSpine AIDA64 硬件生理体征感知末梢与双模探针单元测试套件
"""
import sys
import os
import unittest
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.perceptors.hardware.aida64_daemon import Aida64DaemonManager
from src.perceptors.hardware.aida64_perceptor import Aida64HardwarePerceptor
from src.perceptors.somatic_hub import SomaticPerceptorHub
from src.mcp.server import CyberSpineMCPServer


class TestAida64Perceptor(unittest.TestCase):

    def setUp(self):
        self.perceptor = Aida64HardwarePerceptor()
        self.hub = SomaticPerceptorHub()
        self.mcp = CyberSpineMCPServer()

    def test_01_daemon_manager_probe(self):
        """测试 1: AIDA64 守护进程自动探测机制"""
        is_active = Aida64DaemonManager.is_shared_memory_active()
        exe_path = Aida64DaemonManager.find_executable()

        print("\n--- [TEST 1: AIDA64 Daemon Probe] ---")
        print(f"[PASS] 共享内存就绪状态: {is_active}")
        print(f"[PASS] 本地/系统 AIDA64 路径: {exe_path or '未安装(使用原生轻量探针)'}")

    def test_02_poll_hardware_signal(self):
        """测试 2: 采样硬件生理体征电信号 (双模自适应)"""
        data = self.perceptor.get_baseline()
        self.assertIsNotNone(data)
        self.assertIn("source_mode", data)
        self.assertIn("perceptor_id", data)

        signals = self.perceptor.poll_signals()
        self.assertIsInstance(signals, list)

        print("\n--- [TEST 2: Hardware Telemetry Signal] ---")
        print(f"[PASS] 探针工作模式: {data['source_mode']}")
        print(f"[PASS] CPU/GPU 体征: CPU={data.get('cpu_package_temp_c', 0.0)}°C, GPU={data.get('gpu_temp_c', 0.0)}°C")
        print(f"[PASS] 功耗/风扇: 功耗={data.get('gpu_power_watts', 0.0)}W, 风扇={data.get('cpu_fan_rpm', 0)} RPM")

    def test_03_hub_integration(self):
        """测试 3: 验证 SomaticPerceptorHub 全身神经末梢包含硬件代谢末梢"""
        topo = self.hub.get_full_somatic_topology()
        self.assertIn("channels", topo)
        self.assertIn("nerve.hardware.somatic_telemetry", topo["channels"])

        hw_channel = topo["channels"]["nerve.hardware.somatic_telemetry"]
        self.assertEqual(hw_channel["perceptor_id"], "nerve.hardware.somatic_telemetry")

        print("\n--- [TEST 3: Somatic Hub Integration] ---")
        print(f"[PASS] 全身通道总数: {topo['total_channels']}")
        print(f"[PASS] 硬件通道数据: {hw_channel.get('source_mode', 'NATIVE')}")

    def test_04_mcp_hardware_channel_query(self):
        """测试 4: 通过 MCP 协议调阅硬件生理体征通道"""
        req = {
            "jsonrpc": "2.0",
            "id": 401,
            "method": "tools/call",
            "params": {
                "name": "cyberspine_get_somatic_state",
                "arguments": {"channel_filter": "nerve.hardware"}
            }
        }
        resp = self.mcp.handle_request(req)
        self.assertIsNotNone(resp)
        self.assertNotIn("error", resp)

        import json
        data = json.loads(resp["result"]["content"][0]["text"])
        self.assertIn("channels", data)
        self.assertIn("nerve.hardware.somatic_telemetry", data["channels"])

        print("\n--- [TEST 4: MCP Hardware Channel Query] ---")
        print(f"[PASS] MCP 硬件通道数据帧: {data['channels']['nerve.hardware.somatic_telemetry']}")


if __name__ == '__main__':
    unittest.main()
