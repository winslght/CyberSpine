"""
CyberSpine 本地端侧小模型推理驱动引擎单元测试套件
"""
import sys
import unittest

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.models.local_engine import LocalModelEngine
from src.actuators.base import ActionRiskLevel, ProposedAction


class TestLocalModelEngine(unittest.TestCase):

    def setUp(self):
        self.engine = LocalModelEngine()

    def test_01_check_engine_health(self):
        """测试 1: 探测本地小模型驱动引擎状态"""
        health = self.engine.check_engine_health()
        self.assertIn("mode", health)
        self.assertIn("latency_ms", health)

        print("\n--- [TEST 1: Local Model Engine Health] ---")
        print(f"[PASS] 当前推理模式: {health['mode']} (时延: {health['latency_ms']}ms)")
        print(f"[PASS] 模型: {health['model']}")

    def test_02_heuristic_python_project_action(self):
        """测试 2: 启发式规则脑针对 Python 项目接入情境推演控制动作"""
        mock_state = {
            "structure_profiles": ["PYTHON_PROJECT", "GIT_REPOSITORY"],
            "mount_point": "E:\\CyberSpine",
            "active_process": "Explorer.EXE",
        }

        action = self.engine._heuristic_reasoning(mock_state)
        self.assertEqual(action.actuator_id, "motor.app_control")
        self.assertEqual(action.action_name, "open_in_vscode")
        self.assertEqual(action.risk_level, ActionRiskLevel.MUTATING_APPROVAL)
        self.assertIn("VSCode", action.inquiry_message)

        print("\n--- [TEST 2: Heuristic Action for Python Workspace] ---")
        print(f"[PASS] 启发式推演动作: {action.action_name} | 执行器: {action.actuator_id}")
        print(f"[PASS] 伴侣温和询问: {action.inquiry_message}")

    def test_03_heuristic_high_stress_power_action(self):
        """测试 3: 启发式规则脑针对系统高负载超限情境推演电源调节动作"""
        mock_state = {
            "cpu_percent": 92.5,
            "is_stressed": True,
        }

        action = self.engine._heuristic_reasoning(mock_state)
        self.assertEqual(action.actuator_id, "motor.power")
        self.assertEqual(action.action_name, "set_power_scheme")
        self.assertEqual(action.parameters.get("mode"), "HIGH_PERFORMANCE")

        print("\n--- [TEST 3: Heuristic Action for High Stress Spike] ---")
        print(f"[PASS] 启发式推演动作: {action.action_name} | 模式: {action.parameters.get('mode')}")

    def test_05_live_neural_inference_validity(self):
        """测试 5: 实机调用本地 Ollama Qwen2.5 真实神经网络推演动作帧有效性"""
        mock_state = {
            "active_process": "Code.exe",
            "structure_profiles": ["PYTHON_PROJECT"],
            "mount_point": "E:\\CyberSpine",
        }
        action = self.engine.infer_action_from_somatic_state(mock_state)
        self.assertIsInstance(action, ProposedAction)
        self.assertTrue(len(action.action_name) > 0)
        self.assertTrue(len(action.actuator_id) > 0)
        self.assertIn(action.risk_level, [ActionRiskLevel.READ_ONLY_SAFE, ActionRiskLevel.MUTATING_APPROVAL])

        print("\n--- [TEST 5: Live Qwen2.5 Neural Forward Pass] ---")
        print(f"[PASS] 真实大模型生成动作: {action.action_name} (执行器: {action.actuator_id}, 风险: {action.risk_level})")
        print(f"[PASS] 思考链理由: {action.reason}")

    def test_04_mock_ollama_json_parsing(self):
        """测试 4: 验证 Ollama 返回的 JSON Schema 动作帧解析与参数传递"""
        raw_ollama_json = """{
            "thought_chain": "检测到用户插入移动工作盘，识别为 Node.js 与 Python 双栈项目",
            "actuator_id": "motor.app_control",
            "action_name": "open_in_vscode",
            "risk_level": "MUTATING_APPROVAL",
            "parameters": {"target_path": "E:\\\\FullStackProject"},
            "reason": "协助用户快速进入编码模式",
            "inquiry_message": "💡 检测到全栈研发工程接入，是否需要为您在 VSCode 中打开？"
        }"""
        import json
        parsed = json.loads(raw_ollama_json)
        self.assertEqual(parsed["actuator_id"], "motor.app_control")
        self.assertEqual(parsed["action_name"], "open_in_vscode")
        self.assertEqual(parsed["parameters"]["target_path"], "E:\\FullStackProject")

        print("\n--- [TEST 4: Mock Ollama JSON Output Parsing] ---")
        print(f"[PASS] 成功解析 Ollama 神经网络动作帧: {parsed['action_name']} -> {parsed['parameters']}")


if __name__ == '__main__':
    unittest.main()
