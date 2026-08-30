"""
CyberSpine 组件 3 (脊髓神经区与意图提炼脑) 独立单元测试套件
"""
import sys
import unittest
from datetime import datetime, timezone

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.models.somatic_signals import (
    FusedSomaticPacket,
    RawSomaticSignal,
    DeviceFingerprint,
    DeviceClass,
    PacingStateEnum,
    utc_now,
)
from src.spinal_core.intent_gate import SpinalIntentGate


class TestComponent3SpinalGate(unittest.TestCase):

    def setUp(self):
        self.gate = SpinalIntentGate()

    def test_01_empty_storage_noise_filtering(self):
        """测试 1: 感觉门控过滤空盘噪音，绝不上报大脑"""
        packet = FusedSomaticPacket(
            packet_id="pkt_empty_001",
            window_start=utc_now(),
            window_end=utc_now(),
            primary_event="IO_STORAGE_DEVICE_ATTACHED",
            pacing_state=PacingStateEnum.MICRO_PAUSE,
            somatic_summary={
                "channels": ["IO_STORAGE"],
                "structure_profiles": [],  # 空特征
            },
        )
        narrative = self.gate.evaluate_and_narrate(packet)
        self.assertIsNotNone(narrative)
        self.assertFalse(narrative.should_escalate_to_cortex, "空盘噪音应被门控拦截，不呈报前额叶大脑")
        self.assertEqual(narrative.macro_scenario, "GENERIC_STORAGE_NOISE")

        print("\n--- [TEST 1: Sensory Gating Noise Filtering] ---")
        print(f"[PASS] 门控成功拦截空白设备: {narrative.situation_story}")
        print(f"[PASS] 上报决策: should_escalate={narrative.should_escalate_to_cortex}")

    def test_02_python_dev_intent_synthesis(self):
        """测试 2: 识别 Python 工程盘并生成高质量《意图故事》"""
        packet = FusedSomaticPacket(
            packet_id="pkt_py_002",
            window_start=utc_now(),
            window_end=utc_now(),
            primary_event="IO_STORAGE_DEVICE_ATTACHED",
            pacing_state=PacingStateEnum.MICRO_PAUSE,
            somatic_summary={
                "channels": ["IO_STORAGE"],
                "structure_profiles": ["PYTHON_PROJECT", "GIT_REPOSITORY"],
                "devices_involved": ["dev_samsung_t7"],
            },
        )
        narrative = self.gate.evaluate_and_narrate(packet)
        self.assertIsNotNone(narrative)
        self.assertTrue(narrative.should_escalate_to_cortex)
        self.assertEqual(narrative.macro_scenario, "WORKSPACE_ATTACH_PYTHON_DEV")
        self.assertGreaterEqual(narrative.confidence, 0.90)

        print("\n--- [TEST 2: Intent Story Synthesis for Python Dev] ---")
        print(f"[PASS] 意图故事 ID: {narrative.narrative_id}")
        print(f"[PASS] 宏观情境: {narrative.macro_scenario} (置信度: {narrative.confidence*100:.1f}%)")
        print(f"[PASS] 情境叙事: {narrative.situation_story}")
        print(f"[PASS] 意图假设: {narrative.intent_hypothesis}")
        print(f"[PASS] 搭档建议: {narrative.suggested_partnership}")

    def test_03_rust_go_intent_synthesis(self):
        """测试 3: 识别系统级工程盘并生成对应意图"""
        packet = FusedSomaticPacket(
            packet_id="pkt_rust_003",
            window_start=utc_now(),
            window_end=utc_now(),
            primary_event="IO_STORAGE_DEVICE_ATTACHED",
            pacing_state=PacingStateEnum.MICRO_PAUSE,
            somatic_summary={
                "channels": ["IO_STORAGE"],
                "structure_profiles": ["RUST_GO_PROJECT"],
            },
        )
        narrative = self.gate.evaluate_and_narrate(packet)
        self.assertEqual(narrative.macro_scenario, "WORKSPACE_ATTACH_SYSTEMS_DEV")
        self.assertTrue(narrative.should_escalate_to_cortex)

        print("\n--- [TEST 3: Systems Programming Intent] ---")
        print(f"[PASS] 成功提炼底层开发意图: {narrative.macro_scenario}")


if __name__ == '__main__':
    unittest.main()
