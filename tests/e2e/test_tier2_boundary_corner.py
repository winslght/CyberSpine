"""
CyberSpine Core E2E Test Suite - Tier 2: Boundary & Corner Cases
Validates safety gate hard-fuse injections, malformed data, stress concurrency, and edge conditions.
"""
import sys
import os
import json
import time
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Dict, Any

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.app.app_bridge import CyberSpineAppBridge
from src.pacing.real_pacemaker import RealAutonomousPacemaker
from src.models.local_engine import LocalModelEngine
from src.actuators.actuator_hub import MotorActuatorHub
from src.actuators.base import ProposedAction, ActionRiskLevel, ActionResult
from src.actuators.safety_gate import SafetyGate
from src.actuators.workspace import WorkspaceActuator
from src.actuators.app_control import AppControlActuator
from src.actuators.power import SystemPowerActuator
from src.app.telemetry_logger import CognitiveTelemetryLogger, TelemetryCategory


class TestTier2BoundaryCorner(unittest.TestCase):
    """Tier 2: 极限边界、异常对抗与容错测试套件"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.app_bridge = CyberSpineAppBridge()
        self.safety_gate = self.app_bridge.actuator_hub.safety_gate
        self.local_engine = self.app_bridge.local_model
        self.telemetry = self.app_bridge.telemetry
        self.pacemaker = self.app_bridge.pacemaker

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ================= 1. 安全三定律硬熔断黑名单全量对抗注入 =================

    def test_tier2_safety_fuse_all_dangerous_keywords(self):
        """[Tier 2/Safety] 验证 SafetyGate.DANGEROUS_KEYWORDS 所有高危黑名单关键词的绝对熔断"""
        keywords = [
            "rmdir /s",
            "del /f",
            "format",
            "diskpart",
            "reg delete",
            "drop database",
            "shutdown /s",
            "taskkill /f /im explorer.exe",
        ]

        for idx, kw in enumerate(keywords):
            # 无论处于参数的哪个位置（大小写混写、拼接语句）
            malicious_param = f"test_path && {kw.upper()} D:\\important_data"
            action = ProposedAction(
                action_id=f"act_malicious_{idx}",
                actuator_id="motor.workspace",
                action_name="create_project_directory",
                risk_level=ActionRiskLevel.MUTATING_APPROVAL,
                parameters={"target_path": malicious_param, "action_id": f"act_malicious_{idx}"},
                reason="黑名单对抗测试",
                inquiry_message="恶意注入",
            )

            # 即使用户点击“同意执行 (is_user_approved=True)”，物理熔断也必须绝对拦截
            res = self.safety_gate.verify_and_execute(action, is_user_approved=True)
            self.assertFalse(res.success, f"未能拦截高危指令: {kw}")
            self.assertIn("物理安全熔断", res.execution_summary)
            self.assertIn("Hard-fuse blocked", res.error_message)

    def test_tier2_safety_gate_unregistered_and_unknown_actions(self):
        """[Tier 2/Safety] 验证未注册的执行器与未知动作名称的安全退避与错误捕获"""
        # 未注册的 Actuator
        unregistered_action = ProposedAction(
            action_id="act_ghost",
            actuator_id="motor.ghost_device",
            action_name="do_something",
            risk_level=ActionRiskLevel.READ_ONLY_SAFE,
            parameters={"action_id": "act_ghost"},
            reason="幽灵执行器",
            inquiry_message="未注册",
        )
        res_ghost = self.safety_gate.verify_and_execute(unregistered_action, is_user_approved=True)
        self.assertFalse(res_ghost.success)
        self.assertIn("未找到对应的运动神经元执行器", res_ghost.execution_summary)

        # 已注册 Actuator 但传入未知 action_name
        unknown_action = ProposedAction(
            action_id="act_unknown_name",
            actuator_id="motor.workspace",
            action_name="self_destruct_matrix",
            risk_level=ActionRiskLevel.READ_ONLY_SAFE,
            parameters={"action_id": "act_unknown_name", "target_path": str(self.temp_dir)},
            reason="非法动作",
            inquiry_message="未知动作",
        )
        res_unknown = self.safety_gate.verify_and_execute(unknown_action, is_user_approved=True)
        self.assertFalse(res_unknown.success)

    # ================= 2. 文件系统与路径极限边界测试 =================

    def test_tier2_workspace_special_characters_and_deep_paths(self):
        """[Tier 2/Workspace] 验证包含特殊 Unicode 字符、空格、中文、极深层级目录的创建与只读扫描"""
        ws_actuator = WorkspaceActuator()

        # 复杂特殊路径: 中文、空格、特殊符号
        complex_rel_path = "测试工作区 2026_@#_Vibe/深度子模块 Alpha/内部数据_★_Level3"
        target_deep_path = Path(self.temp_dir) / complex_rel_path

        # 1. 深度创建
        res_create = ws_actuator.execute("create_project_directory", {
            "action_id": "act_deep_create",
            "target_path": str(target_deep_path)
        })
        self.assertTrue(res_create.success)
        self.assertTrue(target_deep_path.exists())

        # 2. 写入 Unicode 测试文件
        unicode_file = target_deep_path / "神经电信号_📡.txt"
        unicode_file.write_text("CyberSpine 仿生神经中枢 UTF-8 编码测试", encoding="utf-8")

        # 3. 扫描该复杂目录
        res_scan = ws_actuator.execute("scan_directory", {
            "action_id": "act_deep_scan",
            "target_path": str(target_deep_path)
        })
        self.assertTrue(res_scan.success)
        self.assertIn("神经电信号_📡.txt", res_scan.output_data.get("files", []))

        # 4. 空路径与缺失参数校验
        res_empty = ws_actuator.execute("scan_directory", {"action_id": "act_err", "target_path": ""})
        self.assertFalse(res_empty.success)
        self.assertIn("未提供有效", res_empty.execution_summary)

        # 5. 不存在路径扫描
        non_existent = Path(self.temp_dir) / "ghost_folder_xyz_999"
        res_missing = ws_actuator.execute("scan_directory", {
            "action_id": "act_missing",
            "target_path": str(non_existent)
        })
        self.assertFalse(res_missing.success)
        self.assertIn("不存在", res_missing.execution_summary)

    # ================= 3. 电源与应用调度器边界测试 =================

    def test_tier2_power_invalid_schemes(self):
        """[Tier 2/Power] 验证传入非法或空白电源模式名称时的精准错误拦截"""
        power_actuator = SystemPowerActuator()

        for invalid_mode in ["SUPER_TURBO_9000", "", "INVALID_MODE", "SLEEP_FOREVER"]:
            res = power_actuator.execute("set_power_scheme", {
                "action_id": "act_bad_power",
                "mode": invalid_mode
            })
            self.assertFalse(res.success)
            self.assertIn("不支持的电源模式", res.execution_summary)
            self.assertEqual(res.error_message, "Invalid power mode")

    def test_tier2_app_control_security_whitelist(self):
        """[Tier 2/AppControl] 验证应用调度器对非白名单应用的防御拦截"""
        app_actuator = AppControlActuator()

        dangerous_apps = ["netcat.exe", "powershell_ise.exe", "curl", "mimikatz.exe", "wget"]
        for bad_app in dangerous_apps:
            res = app_actuator.execute("launch_app", {
                "action_id": "act_bad_app",
                "app_name": bad_app
            })
            self.assertFalse(res.success)
            self.assertIn("安全执行白名单", res.execution_summary)

    # ================= 4. 模型引擎畸变数据与空状态鲁棒性 =================

    def test_tier2_model_engine_empty_and_extreme_state(self):
        """[Tier 2/ModelEngine] 验证感官状态为空、极端数值（如超高/负数 CPU）时的启发式推理鲁棒性"""
        # 1. 完全空状态
        action_empty = self.local_engine._heuristic_reasoning({})
        self.assertIsNotNone(action_empty)
        self.assertEqual(action_empty.actuator_id, "motor.workspace")
        self.assertEqual(action_empty.action_name, "scan_directory")

        # 2. 极端负数与浮点数
        action_negative = self.local_engine._heuristic_reasoning({"cpu_percent": -100.0, "memory_percent": 0.0})
        self.assertEqual(action_negative.action_name, "scan_directory")

        # 3. 极端高压 CPU
        action_extreme_cpu = self.local_engine._heuristic_reasoning({"cpu_percent": 999.9})
        self.assertEqual(action_extreme_cpu.actuator_id, "motor.power")
        self.assertEqual(action_extreme_cpu.action_name, "set_power_scheme")

    # ================= 5. 起搏器并发高频脉冲与线程安全 =================

    def test_tier2_pacemaker_concurrent_pulses_stress(self):
        """[Tier 2/Pacemaker] 验证多线程并发快速触发心跳时的线程安全与数据一致性"""
        concurrency = 8
        pulses_per_thread = 5
        threads = []
        errors = []

        def worker():
            try:
                for _ in range(pulses_per_thread):
                    self.pacemaker._execute_single_physical_heartbeat()
                    time.sleep(0.01)
            except Exception as e:
                errors.append(str(e))

        for _ in range(concurrency):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"并发心跳发生异常: {errors}")
        status = self.pacemaker.get_live_pacemaker_status()
        self.assertGreaterEqual(status["total_heartbeats"], concurrency * pulses_per_thread)
        self.assertLessEqual(len(status["recent_ticks"]), 100)

    # ================= 6. 认知透视环形缓冲溢出与清空 =================

    def test_tier2_telemetry_buffer_overflow_and_limits(self):
        """[Tier 2/Telemetry] 验证超过 max_buffer_size (300) 时的安全出队与极端 limit 查询"""
        # 压入 350 条测试透视帧
        for i in range(350):
            self.telemetry.record(
                category=TelemetryCategory.SYSTEM,
                title=f"Stress Frame #{i}",
                message=f"Buffer capacity stress test index {i}",
                latency_ms=0.01
            )

        # 验证内存中维持在 300 条以内
        with self.telemetry._buffer_lock:
            buffer_len = len(self.telemetry._buffer)
        self.assertEqual(buffer_len, 300)

        # 极限 limit 测试
        frames_zero = self.telemetry.get_recent_frames(limit=0)
        self.assertEqual(len(frames_zero), 0)

        frames_large = self.telemetry.get_recent_frames(limit=5000)
        self.assertEqual(len(frames_large), 300)


if __name__ == '__main__':
    unittest.main()
