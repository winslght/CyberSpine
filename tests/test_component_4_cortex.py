"""
CyberSpine 组件 4 (前额叶大脑认知中枢与双向闭环) 独立单元测试套件
"""
import sys
import shutil
import tempfile
import unittest
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.models.somatic_signals import (
    IntentNarrative,
    CognitiveFeedbackMessage,
    FeedbackDirective,
    utc_now,
)
from src.pacing.neural_buffer import TemporalNeuralBuffer
from src.cortex.master_cortex import MasterCortex


class TestComponent4MasterCortex(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.buffer = TemporalNeuralBuffer()
        self.cortex = MasterCortex(neural_buffer=self.buffer)

        # 构建模拟项目目录
        (Path(self.temp_dir) / "src").mkdir()
        (Path(self.temp_dir) / "requirements.txt").write_text("pydantic>=2.0\npsutil>=5.0\n", encoding="utf-8")
        (Path(self.temp_dir) / "main.py").write_text("print('CyberSpine Active')\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_master_cortex_approval_and_hands_execution(self):
        """测试 1: 意图奏折呈递 ➔ 用户审批 ➔ 双手工具扫描 ➔ 下行抑制递质生效"""
        narrative = IntentNarrative(
            narrative_id="narrative_test_001",
            macro_scenario="WORKSPACE_ATTACH_PYTHON_DEV",
            confidence=0.96,
            situation_story="用户接入了 Python 工程工作盘。",
            intent_hypothesis="用户准备开展代码开发。",
            suggested_partnership="提示是否需要梳理工作目录。",
            should_escalate_to_cortex=True,
            evidence_snapshot={},
        )

        inquiry_recorded = []
        def mock_user_approval(inquiry: str) -> bool:
            inquiry_recorded.append(inquiry)
            return True  # 模拟用户点击“同意”

        executed, feedback = self.cortex.process_intent_narrative(
            narrative=narrative,
            approval_callback=mock_user_approval,
            target_directory=self.temp_dir,
        )

        self.assertTrue(executed)
        self.assertEqual(len(inquiry_recorded), 1)
        self.assertIn("Python 研发工作盘", inquiry_recorded[0])
        self.assertEqual(feedback.directive, FeedbackDirective.SUPPRESS_AND_OBSERVE)
        self.assertEqual(feedback.cooldown_seconds, 300)
        self.assertIn("requirements.txt", feedback.executed_action_summary)

        # 验证中枢缓冲器已进入抑制状态
        self.assertTrue(self.buffer._is_inhibited)

        print("\n--- [TEST 1: Cortex 3W Reasoning & Hands Execution] ---")
        print(f"[PASS] 温和交互卡片文案:\n{inquiry_recorded[0]}")
        print(f"[PASS] 双手工具执行摘要:\n{feedback.executed_action_summary}")
        print(f"[PASS] 下行抑制状态: cooldown={feedback.cooldown_seconds}s, buffer_inhibited={self.buffer._is_inhibited}")

    def test_02_user_rejection_anti_fatigue_backoff(self):
        """测试 2: 用户拒绝 ➔ 触发 15 分钟高情商指数退避与静默"""
        narrative = IntentNarrative(
            narrative_id="narrative_test_002",
            macro_scenario="WORKSPACE_ATTACH_PYTHON_DEV",
            confidence=0.96,
            situation_story="用户接入工作盘。",
            intent_hypothesis="开发意图。",
            suggested_partnership="询问协助。",
            should_escalate_to_cortex=True,
            evidence_snapshot={},
        )

        def mock_user_reject(inquiry: str) -> bool:
            return False  # 模拟用户选择“暂不处理”

        executed, feedback = self.cortex.process_intent_narrative(
            narrative=narrative,
            approval_callback=mock_user_reject,
            target_directory=self.temp_dir,
        )

        self.assertFalse(executed)
        self.assertEqual(feedback.directive, FeedbackDirective.SUPPRESS_AND_OBSERVE)
        self.assertEqual(feedback.cooldown_seconds, 900)
        self.assertTrue(self.buffer._is_inhibited)

        print("\n--- [TEST 2: Anti-Fatigue High EQ Silence on Rejection] ---")
        print(f"[PASS] 拒绝后抑制决策: {feedback.reason} (冷却时长: {feedback.cooldown_seconds}s)")


if __name__ == '__main__':
    unittest.main()
