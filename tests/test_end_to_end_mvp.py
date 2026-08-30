"""
CyberSpine 最小闭环 MVP 端到端自动化集成回归测试 (End-to-End Minimal Loop Test)
串联四大核心组件：末梢感知 ➔ 时钟缓冲 ➔ 脊髓提炼 ➔ 大脑接管与双手执行 ➔ 双向抑制闭环
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

from src.models.somatic_signals import FeedbackDirective
from src.perceptors.io.io_manager import IOPerceptorManager
from src.pacing.neural_buffer import TemporalNeuralBuffer
from src.spinal_core.intent_gate import SpinalIntentGate
from src.cortex.master_cortex import MasterCortex


class TestEndToEndMinimalMVP(unittest.TestCase):

    def setUp(self):
        self.temp_root = tempfile.mkdtemp()
        self.db_path = str(Path(self.temp_root) / "test_devices.json")
        self.io_manager = IOPerceptorManager(db_path=self.db_path)
        self.buffer = TemporalNeuralBuffer(alignment_window_seconds=0.1)
        self.spinal_gate = SpinalIntentGate()
        self.master_cortex = MasterCortex(neural_buffer=self.buffer)

        # 构建模拟插入的 U 盘文件系统 (Python 研发工作盘)
        self.usb_mount = Path(self.temp_root) / "USB_DRIVE_E"
        self.usb_mount.mkdir()
        (self.usb_mount / ".git").mkdir()
        (self.usb_mount / "src").mkdir()
        (self.usb_mount / "requirements.txt").write_text("pydantic>=2.0\npsutil>=5.0\n", encoding="utf-8")
        (self.usb_mount / "main.py").write_text("print('CyberSpine MVP Loop Active')\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_full_biomimetic_loop_success(self):
        """端到端全链路闭环测试：U盘插入 ➔ 缓冲对齐 ➔ 脊髓提炼 ➔ 大脑扫描 ➔ 抑制静默"""
        print("\n=======================================================")
        print("🚀 [START] CyberSpine 仿生全脑区最小闭环 MVP 端到端自测")
        print("=======================================================")

        # === 步骤 1: 末梢感官感知 (Component 1) ===
        raw_signal = self.io_manager.mock_inject_storage_signal(
            mock_root_path=str(self.usb_mount),
            volume_label="SAMSUNG_T7_WORK",
            total_gb=500.0,
            free_gb=240.0,
        )
        self.assertIsNotNone(raw_signal)
        print(f"\n[步骤 1: 末梢感知] 成功捕获硬件接入电信号:")
        print(f"   - Signal ID: {raw_signal.signal_id}")
        print(f"   - 识别特征: {raw_signal.structure_summary.detected_profiles}")
        print(f"   - 设备指纹: {raw_signal.device_fingerprint.device_id}")

        # === 步骤 2: 中枢时钟缓冲与时空对齐 (Component 2) ===
        enqueued = self.buffer.ingest_signal(raw_signal)
        self.assertTrue(enqueued)
        fused_packet = self.buffer.flush_aligned_packet(force=True)
        self.assertIsNotNone(fused_packet)
        print(f"\n[步骤 2: 时钟缓冲] 时空对齐并完成电脉冲打包:")
        print(f"   - Packet ID: {fused_packet.packet_id}")
        print(f"   - 节律状态: {fused_packet.pacing_state.value}")
        print(f"   - 汇聚通道: {fused_packet.somatic_summary['channels']}")

        # === 步骤 3: 脊髓神经区初审与意图故事提炼 (Component 3) ===
        narrative = self.spinal_gate.evaluate_and_narrate(fused_packet)
        self.assertIsNotNone(narrative)
        self.assertTrue(narrative.should_escalate_to_cortex)
        self.assertEqual(narrative.macro_scenario, "WORKSPACE_ATTACH_PYTHON_DEV")
        print(f"\n[步骤 3: 脊髓提炼] 感觉门控通过，生成《用户意图故事》:")
        print(f"   - Narrative ID: {narrative.narrative_id}")
        print(f"   - 宏观情境: {narrative.macro_scenario} (置信度: {narrative.confidence*100:.1f}%)")
        print(f"   - 呈递奏折: {narrative.situation_story}")
        print(f"   - 意图假设: {narrative.intent_hypothesis}")

        # === 步骤 4: 前额叶大脑接管、温和交互与双手执行 (Component 4) ===
        user_inquiries = []
        def user_approve_dialog(inquiry: str) -> bool:
            user_inquiries.append(inquiry)
            print(f"\n[步骤 4: 大脑交互] 桌面弹出温和交互卡片:\n{inquiry}")
            return True  # 模拟用户点击“同意协助”

        executed, feedback = self.master_cortex.process_intent_narrative(
            narrative=narrative,
            approval_callback=user_approve_dialog,
            target_directory=str(self.usb_mount),
        )

        self.assertTrue(executed)
        self.assertEqual(feedback.directive, FeedbackDirective.SUPPRESS_AND_OBSERVE)
        self.assertEqual(feedback.cooldown_seconds, 300)
        print(f"\n[步骤 5: 双手执行] 大脑调用双手工具完成目录扫描:\n{feedback.executed_action_summary}")

        # === 步骤 5: 双向神经反馈与下行抑制闭环 ===
        self.assertTrue(self.buffer.is_inhibited())
        print(f"\n[步骤 6: 下行抑制] 传导抑制递质闭环: 缓冲器进入 {feedback.cooldown_seconds}s 静默期 (0% 能耗稳态)")
        print("\n=======================================================")
        print("🎉 [SUCCESS] CyberSpine 最小闭环 MVP 全链路 100% 验证成功！")
        print("=======================================================")


if __name__ == '__main__':
    unittest.main()
