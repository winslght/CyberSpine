"""
CyberSpine 新增神经末梢 (AIDA64 硬件体征、键盘鼠标动量、剪贴板语义) 全量单元测试套件
"""
import sys
import os
import unittest
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.perceptors.hardware.aida64_perceptor import Aida64HardwarePerceptor
from src.perceptors.system.input_kinetics import InputKineticsPerceptor
from src.perceptors.system.clipboard_semantics import ClipboardSemanticsPerceptor
from src.perceptors.somatic_hub import SomaticPerceptorHub


class TestNewSomaticPerceptors(unittest.TestCase):

    def setUp(self):
        self.hub = SomaticPerceptorHub()

    def test_01_input_kinetics_perceptor(self):
        """测试 1: 键盘鼠标动量与心流节奏感知器"""
        p = InputKineticsPerceptor()
        base = p.get_baseline()
        self.assertIn("idle_seconds", base)
        self.assertIn("flow_state", base)
        self.assertIn("is_user_active", base)

        print("\n--- [TEST 1: Input Kinetics Perceptor] ---")
        print(f"[PASS] 物理空闲时长: {base['idle_seconds']}s")
        print(f"[PASS] 心流状态判定: {base['flow_state']}")
        print(f"[PASS] 用户活跃标志: {base['is_user_active']}")

    def test_02_clipboard_semantics_perceptor(self):
        """测试 2: 瞬时工作记忆剪贴板语义模式嗅探"""
        p = ClipboardSemanticsPerceptor()
        base = p.get_baseline()
        self.assertIn("content_type", base)
        self.assertIn("length", base)
        self.assertIn("preview", base)

        # 模式分类函数测试
        self.assertEqual(p._classify_text_pattern("https://github.com/cyberspine"), "URL_LINK")
        self.assertEqual(p._classify_text_pattern("def calculate_energy(x): return x * 2"), "SOURCE_CODE")
        self.assertEqual(p._classify_text_pattern('{"status": "ok", "value": 100}'), "JSON_DATA")

        print("\n--- [TEST 2: Clipboard Semantics Perceptor] ---")
        print(f"[PASS] 当前剪贴板类型: {base['content_type']}")
        print(f"[PASS] 字符长度/预览: {base['length']} 字符 | '{base['preview']}'")

    def test_03_hardware_telemetry_perceptor(self):
        """测试 3: AIDA64 / 原生双模硬件内脏体征感知器"""
        p = Aida64HardwarePerceptor()
        base = p.get_baseline()
        self.assertIn("source_mode", base)
        self.assertIn("cpu_package_temp_c", base)
        self.assertIn("gpu_temp_c", base)

        print("\n--- [TEST 3: Hardware Telemetry Perceptor] ---")
        print(f"[PASS] 探针运行模式: {base['source_mode']}")
        print(f"[PASS] GPU 核心体征: {base.get('gpu_temp_c', 0.0)}°C, 功耗 {base.get('gpu_power_watts', 0.0)}W")

    def test_04_full_somatic_topology(self):
        """测试 4: 全身神经拓扑完整性验证 (11 大神经通道)"""
        topo = self.hub.get_full_somatic_topology()
        channels = topo["channels"]

        self.assertIn("nerve.system.foreground_focus", channels)
        self.assertIn("nerve.system.running_apps", channels)
        self.assertIn("nerve.system.high_load", channels)
        self.assertIn("nerve.system.homeostasis", channels)
        self.assertIn("nerve.system.notifications", channels)
        self.assertIn("nerve.system.stability", channels)
        self.assertIn("nerve.network.health", channels)
        self.assertIn("nerve.hardware.somatic_telemetry", channels)
        self.assertIn("nerve.system.input_kinetics", channels)
        self.assertIn("nerve.system.clipboard_semantics", channels)
        self.assertIn("nerve.io.storage", channels)

        self.assertEqual(topo["total_channels"], 11)

        print("\n--- [TEST 4: Full Somatic Topology (11 Channels)] ---")
        print(f"[PASS] 全身感官总数: {topo['total_channels']} 个通道")
        for ch_id in channels:
            print(f"  [√] 通道: {ch_id}")


if __name__ == '__main__':
    unittest.main()
