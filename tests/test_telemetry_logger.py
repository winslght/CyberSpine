"""
CyberSpine 神经感知与认知透视日志服务单元测试套件
"""
import sys
import unittest

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.app.telemetry_logger import CognitiveTelemetryLogger, TelemetryCategory
from src.app.app_bridge import CyberSpineAppBridge


class TestCognitiveTelemetryLogger(unittest.TestCase):

    def setUp(self):
        self.logger = CognitiveTelemetryLogger(max_buffer_size=50)
        self.bridge = CyberSpineAppBridge()

    def test_01_record_and_retrieve_frames(self):
        """测试 1: 记录与提取各类别认知透视帧"""
        frame1 = self.logger.record(
            category=TelemetryCategory.SOMATIC,
            title="前台焦点捕获",
            message="前台处于 Code.exe (VSCode 编码心流)",
            latency_ms=1.2
        )
        frame2 = self.logger.record(
            category=TelemetryCategory.SPINAL,
            title="中枢感觉确认",
            message="感觉门控判定: 确认用户进入深度编程心流 (置信度 96%)",
            latency_ms=0.5
        )
        frame3 = self.logger.record(
            category=TelemetryCategory.MODEL,
            title="本地大模型思维链推演",
            message="Qwen2.5 GPU 推演动作: open_in_vscode",
            latency_ms=45.0
        )

        frames = self.logger.get_recent_frames(10)
        self.assertGreaterEqual(len(frames), 3)

        categories = [f["category"] for f in frames]
        self.assertIn("SOMATIC", categories)
        self.assertIn("SPINAL", categories)
        self.assertIn("MODEL", categories)

        print("\n--- [TEST 1: Record & Retrieve Telemetry Frames] ---")
        print(f"[PASS] 成功提取透视帧: 类别分布={set(categories)}, 最新帧={frames[-1]['title']}")

    def test_02_bridge_live_cognitive_cycle(self):
        """测试 2: 通过 IPC 桥接层触发完整物理采样与模型推演透视"""
        res = self.bridge.trigger_live_cognitive_cycle()
        self.assertTrue(res["success"])
        self.assertIn("proposed_action", res)
        self.assertGreater(res["total_latency_ms"], 0)

        logs = self.bridge.get_cognitive_telemetry(10)
        self.assertGreater(len(logs), 0)

        print("\n--- [TEST 2: Bridge Live Cognitive Cycle] ---")
        print(f"[PASS] 全链路透视耗时: 总耗时={res['total_latency_ms']}ms (物理采样={res['somatic_latency_ms']}ms, 模型推演={res['model_latency_ms']}ms)")
        print(f"[PASS] 提议动作: {res['proposed_action']['action_name']}")


if __name__ == '__main__':
    unittest.main()
