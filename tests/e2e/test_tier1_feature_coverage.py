"""
CyberSpine Core E2E Test Suite - Tier 1: Feature Coverage & Interface Contracts
Validates requirements R1-R5 and Features F1-F18 in isolation.
"""
import sys
import os
import json
import time
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Any

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.app.app_bridge import CyberSpineAppBridge
from src.pacing.real_pacemaker import RealAutonomousPacemaker, HeartbeatTickRecord
from src.perceptors.somatic_hub import SomaticPerceptorHub
from src.models.local_engine import LocalModelEngine
from src.actuators.actuator_hub import MotorActuatorHub
from src.actuators.base import ProposedAction, ActionRiskLevel, ActionResult
from src.actuators.app_control import AppControlActuator
from src.actuators.workspace import WorkspaceActuator
from src.actuators.power import SystemPowerActuator
from src.actuators.safety_gate import SafetyGate
from src.app.telemetry_logger import CognitiveTelemetryLogger, TelemetryCategory


class TestTier1FeatureCoverage(unittest.TestCase):
    """Tier 1: 核心功能与接口契约全覆盖测试套件 (R1-R5 / F1-F18)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.app_bridge = CyberSpineAppBridge()
        self.pacemaker = self.app_bridge.pacemaker
        self.hub = self.app_bridge.hub
        self.local_engine = self.app_bridge.local_model
        self.telemetry = self.app_bridge.telemetry
        self.actuator_hub = self.app_bridge.actuator_hub

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ================= R1: 物理起搏器与神经驾驶舱 (F1, F2) =================

    def test_r1_f1_pacemaker_heartbeat_execution_and_log(self):
        """[R1/F1] 验证 5.0s 物理自主心跳单次执行、计数递增与日志真实写入"""
        initial_count = self.pacemaker._heartbeat_count
        log_file = self.pacemaker.ticks_log_file

        # 手动触发一次真实心跳
        self.pacemaker._execute_single_physical_heartbeat()

        self.assertEqual(self.pacemaker._heartbeat_count, initial_count + 1)
        self.assertTrue(log_file.exists(), f"心跳日志文件不存在: {log_file}")

        # 验证日志文件最新行包含心跳序号与时间戳
        with open(log_file, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        self.assertGreaterEqual(len(lines), 1)
        latest_line = lines[-1]
        self.assertIn(f"HEARTBEAT #{self.pacemaker._heartbeat_count:04d}", latest_line)
        self.assertIn("5.0s物理心跳", latest_line)

        # 验证获取实时状态快照快照结构
        status = self.pacemaker.get_live_pacemaker_status()
        self.assertIn("total_heartbeats", status)
        self.assertIn("current_process", status)
        self.assertIn("current_dwell_seconds", status)
        self.assertIn("latest_60s_briefing", status)
        self.assertIn("recent_ticks", status)

    def test_r1_f2_cerebellar_60s_briefing_generation(self):
        """[R1/F2] 验证小脑 12 次心跳（60s）宏观世界简报聚合与落盘"""
        # 模拟注入 12 条心跳采样数据
        for i in range(12):
            self.pacemaker._execute_single_physical_heartbeat()

        briefing = self.pacemaker._latest_60s_briefing
        self.assertIsNotNone(briefing)
        self.assertIn("过去 1 分钟", briefing)
        self.assertIn("宏观简报", briefing)

    def test_r1_f2_cockpit_dashboard_data_sync(self):
        """[R1/F2] 验证神经驾驶舱 API 数据结构完整性与心跳同步"""
        dash_data = self.app_bridge.get_dashboard_data()
        expected_keys = [
            "uptime_seconds", "uptime_formatted", "heartbeat_count",
            "somatic_channels", "latest_briefing", "is_inhibited",
            "active_plugins_count", "total_plugins_count", "pacemaker"
        ]
        for key in expected_keys:
            self.assertIn(key, dash_data, f"驾驶舱返回缺失关键字段: {key}")

        self.assertIsInstance(dash_data["somatic_channels"], dict)
        self.assertGreater(dash_data["total_plugins_count"], 0)
        self.assertGreaterEqual(dash_data["active_plugins_count"], 1)

    # ================= R2: 插件商店与神经末梢热插拔 (F3, F4, F5) =================

    def test_r2_f3_somatic_sensors_baseline_topology(self):
        """[R2/F3] 验证 8 大神经末梢通道基线拓扑快照与性能摘要"""
        topology = self.hub.get_full_somatic_topology()
        self.assertIn("channels", topology)
        self.assertIn("performance_benchmarks", topology)

        channels = topology["channels"]
        required_channels = [
            "nerve.system.foreground_focus",
            "nerve.system.running_apps",
            "nerve.system.high_load",
            "nerve.system.homeostasis",
            "nerve.system.notifications",
            "nerve.system.stability",
            "nerve.network.health",
            "nerve.io.storage",
        ]
        for ch in required_channels:
            self.assertIn(ch, channels, f"拓扑快照缺失通道: {ch}")

        # 验证每个探针性能基准
        benchmarks = topology["performance_benchmarks"]
        self.assertGreaterEqual(len(benchmarks), 7)
        for bm in benchmarks:
            self.assertIn("perceptor_id", bm)
            self.assertIn("avg_duration_ms", bm)

    def test_r2_f4_plugin_hot_toggle(self):
        """[R2/F4] 验证插件商店 8 大神经末梢开关热切换"""
        store = self.app_bridge.get_plugin_store()
        self.assertIsInstance(store, list)
        self.assertGreaterEqual(len(store), 8)

        target_plugin = "nerve.system.high_load"
        # 1. 切换为禁用
        res_off = self.app_bridge.toggle_plugin(target_plugin, False)
        self.assertTrue(res_off["success"])
        self.assertFalse(res_off["enabled"])

        # 2. 验证状态已更新
        updated_store = {p["id"]: p for p in self.app_bridge.get_plugin_store()}
        self.assertFalse(updated_store[target_plugin]["enabled"])

        # 3. 恢复为启用
        res_on = self.app_bridge.toggle_plugin(target_plugin, True)
        self.assertTrue(res_on["success"])
        self.assertTrue(res_on["enabled"])

        # 4. 测试不存在的插件切换
        res_err = self.app_bridge.toggle_plugin("invalid.plugin.id", True)
        self.assertFalse(res_err["success"])

    def test_r2_f5_extension_plugins_install(self):
        """[R2/F5] 验证扩展插件（视觉、听觉、剪贴板）安装与启用流转"""
        ext_plugin = "nerve.visual.screen"
        res_install = self.app_bridge.install_plugin(ext_plugin)
        self.assertTrue(res_install["success"])

        updated_store = {p["id"]: p for p in self.app_bridge.get_plugin_store()}
        self.assertTrue(updated_store[ext_plugin]["installed"])
        self.assertTrue(updated_store[ext_plugin]["enabled"])

    # ================= R3: 端侧小模型与分脑协同 (F6, F7, F8, F9, F10) =================

    def test_r3_f6_local_engine_health_and_models(self):
        """[R3/F6] 验证本地模型引擎健康探测与模型发现"""
        health = self.local_engine.check_engine_health()
        self.assertIn("mode", health)
        self.assertIn("latency_ms", health)
        self.assertIn("model", health)
        self.assertIn(health["mode"], ["OLLAMA_SERVICE_ONLINE", "EMBEDDED_HEURISTIC_RULE_BRAIN"])

        models = self.local_engine.list_installed_models()
        self.assertIsInstance(models, list)

    def test_r3_f7_f9_heuristic_rule_brain_fallback(self):
        """[R3/F7/F9] 验证启发式规则脑 0 崩溃推演与动作帧生成"""
        # 场景 A: Python 研发工程接入
        somatic_dev = {
            "structure_profiles": ["PYTHON_PROJECT", "GIT_REPOSITORY"],
            "mount_point": str(self.temp_dir),
        }
        action_dev = self.local_engine._heuristic_reasoning(somatic_dev)
        self.assertEqual(action_dev.actuator_id, "motor.app_control")
        self.assertEqual(action_dev.action_name, "open_in_vscode")
        self.assertEqual(action_dev.risk_level, ActionRiskLevel.MUTATING_APPROVAL)
        self.assertIn(str(self.temp_dir), action_dev.parameters.get("target_path", ""))

        # 场景 B: 高压负载场景
        somatic_load = {"cpu_percent": 92.5}
        action_load = self.local_engine._heuristic_reasoning(somatic_load)
        self.assertEqual(action_load.actuator_id, "motor.power")
        self.assertEqual(action_load.action_name, "set_power_scheme")
        self.assertEqual(action_load.parameters.get("mode"), "HIGH_PERFORMANCE")

        # 场景 C: 常规只读扫描
        somatic_normal = {"mount_point": str(self.temp_dir)}
        action_norm = self.local_engine._heuristic_reasoning(somatic_normal)
        self.assertEqual(action_norm.actuator_id, "motor.workspace")
        self.assertEqual(action_norm.action_name, "scan_directory")
        self.assertEqual(action_norm.risk_level, ActionRiskLevel.READ_ONLY_SAFE)

    def test_r3_f8_ganglion_hub_status(self):
        """[R3/F8] 验证分脑状态与小模型指标获取"""
        status = self.app_bridge.get_ganglion_status()
        self.assertIn("engine_health", status)
        self.assertIn("models", status)
        self.assertIn("midbrain", status)
        self.assertIn("visual", status)
        self.assertIn("auditory", status)

    def test_r3_f10_cortex_configuration_rw(self):
        """[R3/F10] 验证高级大脑连接器配置读取与持久修改"""
        cfg = self.app_bridge.get_cortex_config()
        self.assertIn("provider", cfg)
        self.assertIn("temperature", cfg)

        new_config = {"temperature": 0.45, "resonance_sensitivity": 92}
        res = self.app_bridge.save_cortex_config(new_config)
        self.assertTrue(res["success"])

        updated_cfg = self.app_bridge.get_cortex_config()
        self.assertEqual(updated_cfg["temperature"], 0.45)
        self.assertEqual(updated_cfg["resonance_sensitivity"], 92)

    # ================= R4: 运动神经元双手与安全三定律 (F11, F12, F13, F14, F15) =================

    def test_r4_f11_f12_app_control_actuator(self):
        """[R4/F11/F12] 验证应用与窗口调度执行器"""
        actuator = AppControlActuator()
        
        # 风险评估契约
        self.assertEqual(actuator.evaluate_risk("open_folder_in_explorer", {}), ActionRiskLevel.READ_ONLY_SAFE)
        self.assertEqual(actuator.evaluate_risk("open_in_vscode", {}), ActionRiskLevel.MUTATING_APPROVAL)
        self.assertEqual(actuator.evaluate_risk("launch_app", {}), ActionRiskLevel.MUTATING_APPROVAL)
        self.assertEqual(actuator.evaluate_risk("unauthorized_exec", {}), ActionRiskLevel.DANGEROUS_FORBIDDEN)

        # 安全白名单拦截
        res_blocked = actuator.execute("launch_app", {"app_name": "malicious_virus.exe"})
        self.assertFalse(res_blocked.success)
        self.assertIn("白名单", res_blocked.execution_summary)

    def test_r4_f13_workspace_actuator(self):
        """[R4/F13] 验证工程工作区创建、只读扫描与依赖预检"""
        actuator = WorkspaceActuator()
        target_sub = Path(self.temp_dir) / "test_project" / "inner"

        # 1. 创建多级工程目录
        res_create = actuator.execute("create_project_directory", {"target_path": str(target_sub)})
        self.assertTrue(res_create.success)
        self.assertTrue(target_sub.exists())

        # 创建测试文件与 requirements.txt
        (target_sub / "requirements.txt").write_text("pytest>=7.0\n", encoding="utf-8")
        (target_sub / "main.py").write_text("print('test')\n", encoding="utf-8")

        # 2. 只读扫描目录
        res_scan = actuator.execute("scan_directory", {"target_path": str(target_sub)})
        self.assertTrue(res_scan.success)
        self.assertIn("main.py", res_scan.output_data.get("files", []))
        self.assertIn("requirements.txt", res_scan.output_data.get("files", []))

        # 3. 依赖与环境预检
        res_preflight = actuator.execute("preflight_check", {"target_path": str(target_sub)})
        self.assertTrue(res_preflight.success)
        self.assertTrue(res_preflight.output_data.get("has_requirements"))

    def test_r4_f14_power_actuator(self):
        """[R4/F14] 验证 Windows 电源方案调节器"""
        actuator = SystemPowerActuator()
        self.assertEqual(actuator.evaluate_risk("get_active_power_scheme", {}), ActionRiskLevel.READ_ONLY_SAFE)
        self.assertEqual(actuator.evaluate_risk("set_power_scheme", {}), ActionRiskLevel.MUTATING_APPROVAL)

        # 查询当前方案
        res_query = actuator.execute("get_active_power_scheme", {})
        self.assertTrue(res_query.success)
        self.assertIn("当前活动电源方案", res_query.execution_summary)

    def test_r4_f15_safety_gate_three_laws(self):
        """[R4/F15] 验证运动神经元安全三定律全景执行"""
        safety_gate = self.actuator_hub.safety_gate
        test_ws = Path(self.temp_dir) / "safe_sandbox"

        # 第一定律：只读操作自动放行
        read_action = ProposedAction(
            action_id="act_test_read",
            actuator_id="motor.workspace",
            action_name="scan_directory",
            risk_level=ActionRiskLevel.READ_ONLY_SAFE,
            parameters={"action_id": "act_test_read", "target_path": str(self.temp_dir)},
            reason="只读测试",
            inquiry_message="只读",
        )
        res_read = safety_gate.verify_and_execute(read_action, is_user_approved=False)
        self.assertTrue(res_read.success)

        # 第二定律：变更操作必须审批 (未审批被拦截)
        mutate_action = ProposedAction(
            action_id="act_test_mutate",
            actuator_id="motor.workspace",
            action_name="create_project_directory",
            risk_level=ActionRiskLevel.MUTATING_APPROVAL,
            parameters={"action_id": "act_test_mutate", "target_path": str(test_ws)},
            reason="创建测试目录",
            inquiry_message="是否允许创建？",
        )
        res_unapproved = safety_gate.verify_and_execute(mutate_action, is_user_approved=False)
        self.assertFalse(res_unapproved.success)
        self.assertIn("暂不执行", res_unapproved.execution_summary)

        # 第二定律：用户显式审批后放行
        res_approved = safety_gate.verify_and_execute(mutate_action, is_user_approved=True)
        self.assertTrue(res_approved.success)
        self.assertTrue(test_ws.exists())

        # 第三定律：高危破坏性指令物理硬熔断
        danger_action = ProposedAction(
            action_id="act_test_danger",
            actuator_id="motor.workspace",
            action_name="create_project_directory",
            risk_level=ActionRiskLevel.MUTATING_APPROVAL,
            parameters={"action_id": "act_test_danger", "target_path": "C:\\ && rmdir /s /q System32"},
            reason="恶意注入测试",
            inquiry_message="危险指令",
        )
        res_fuse = safety_gate.verify_and_execute(danger_action, is_user_approved=True)
        self.assertFalse(res_fuse.success)
        self.assertIn("物理安全熔断", res_fuse.execution_summary)

    # ================= R5: 认知透视终端与诊断流水线 (F16, F17, F18) =================

    def test_r5_f16_live_cognitive_cycle(self):
        """[R5/F16] 验证 4 阶段全链路即时感知推演"""
        cycle_res = self.app_bridge.trigger_live_cognitive_cycle()
        self.assertTrue(cycle_res["success"])
        self.assertIn("total_latency_ms", cycle_res)
        self.assertIn("somatic_latency_ms", cycle_res)
        self.assertIn("model_latency_ms", cycle_res)
        self.assertIn("proposed_action", cycle_res)
        self.assertIsInstance(cycle_res["proposed_action"], dict)

    def test_r5_f17_telemetry_logging_and_persistence(self):
        """[R5/F17] 验证认知透视帧记录、分类与 JSONL 持久化"""
        test_frame = self.telemetry.record(
            category=TelemetryCategory.SOMATIC,
            title="E2E Tier1 测试透视帧",
            message="验证透视日志落盘与提取",
            details={"e2e_tier": 1, "test_mode": "feature_coverage"},
            latency_ms=1.23,
            level="INFO"
        )
        self.assertIsNotNone(test_frame.id)
        self.assertTrue(self.telemetry.log_file.exists())

        # 读取最新帧
        recent = self.telemetry.get_recent_frames(limit=10)
        self.assertGreaterEqual(len(recent), 1)
        found = any(f["id"] == test_frame.id for f in recent)
        self.assertTrue(found, "新记录的透视帧未在 recent_frames 中检索到")

    def test_r5_f18_telemetry_clear_action(self):
        """[R5/F18] 验证透视终端清屏操作"""
        res = self.app_bridge.clear_cognitive_telemetry()
        self.assertTrue(res["success"])
        frames = self.app_bridge.get_cognitive_telemetry(limit=50)
        # 清屏后应只有一条系统清屏日志
        self.assertEqual(len(frames), 1)
        self.assertIn("控制台清屏", frames[0]["title"])


if __name__ == '__main__':
    unittest.main()
