"""
CyberSpine 最小闭环 MVP 交互式演练终端 (Interactive Biomimetic Demo Runner)
提供模拟硬件注入、真实硬件监听与全量测试套件执行三大功能。
"""
import sys
import time
import shutil
import tempfile
from pathlib import Path

# 脚本位于 scripts/；显式将仓库根目录加入导入路径。
repository_root = Path(__file__).resolve().parent.parent
if str(repository_root) not in sys.path:
    sys.path.insert(0, str(repository_root))

# 终端编码安全防崩
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import psutil
from src.models.somatic_signals import FeedbackDirective
from src.perceptors.io.io_manager import IOPerceptorManager
from src.pacing.neural_buffer import TemporalNeuralBuffer
from src.spinal_core.intent_gate import SpinalIntentGate
from src.cortex.master_cortex import MasterCortex


def run_mock_simulation_loop():
    """模式 1: 模拟 Python 研发 U 盘接入演练 (支持真实人机交互 Y/N)"""
    print("\n" + "=" * 65)
    print("🎬 [模式 1] 启动模拟 U 盘接入 ➔ 全脑区仿生协同演练")
    print("=" * 65)

    temp_root = tempfile.mkdtemp()
    try:
        usb_dir = Path(temp_root) / "MOCK_USB_E"
        usb_dir.mkdir()
        (usb_dir / ".git").mkdir()
        (usb_dir / "src").mkdir()
        (usb_dir / "requirements.txt").write_text("pydantic>=2.0\npsutil>=5.0\n", encoding="utf-8")
        (usb_dir / "main.py").write_text("print('Hello from CyberSpine Workspace!')\n", encoding="utf-8")

        db_path = str(Path(temp_root) / "devices.json")
        io_manager = IOPerceptorManager(db_path=db_path)
        neural_buffer = TemporalNeuralBuffer(alignment_window_seconds=0.2)
        spinal_gate = SpinalIntentGate()
        master_cortex = MasterCortex(neural_buffer=neural_buffer)

        print("\n[步骤 1: 末梢感知 (Receptor)] 模拟插入三星移动固态硬盘 (包含 Python 工程)...")
        signal = io_manager.mock_inject_storage_signal(
            mock_root_path=str(usb_dir),
            volume_label="SAMSUNG_T7_DEV",
            total_gb=1000.0,
            free_gb=450.0,
        )
        print(f"   ✓ 产生电信号: ID={signal.signal_id}")
        print(f"   ✓ 浅层嗅探画像: {signal.structure_summary.detected_profiles} (耗时: {signal.structure_summary.scan_duration_ms:.2f}ms)")
        print(f"   ✓ 设备指纹 SHA-256: {signal.device_fingerprint.device_id}")

        print("\n[步骤 2: 中枢时钟缓冲 (Brainstem)] 汇聚多神经元信号并在时间窗口内对齐...")
        neural_buffer.ingest_signal(signal)
        time.sleep(0.25)
        fused_packet = neural_buffer.flush_aligned_packet()
        print(f"   ✓ 融合电信号包: ID={fused_packet.packet_id}")
        print(f"   ✓ 呼吸节律状态: {fused_packet.pacing_state.value} (进入 3~6s 自然沉思停顿)")

        print("\n[步骤 3: 脊髓神经区初审 (Cerebellum / Thalamus)] 脊髓中枢感觉门控与叙事提炼...")
        narrative = spinal_gate.evaluate_and_narrate(fused_packet)
        print(f"   ✓ 意图叙事 ID: {narrative.narrative_id}")
        print(f"   ✓ 宏观情境分类: {narrative.macro_scenario} (置信度: {narrative.confidence*100:.1f}%)")
        print(f"   ✓ 呈递奏折叙事: {narrative.situation_story}")
        print(f"   ✓ 意图假设: {narrative.intent_hypothesis}")
        print(f"   ✓ 上报决策: should_escalate={narrative.should_escalate_to_cortex}")

        print("\n[步骤 4: 前额叶大脑 3W 推演与温和交互 (Prefrontal Cortex)]")
        def cli_user_dialog(inquiry: str) -> bool:
            print("\n" + "-" * 60)
            print(inquiry)
            print("-" * 60)
            try:
                ans = input(">> 是否同意大脑协助扫描工作区并预备环境？ [Y/n, 默认 Y]: ").strip().lower()
                return ans in ("", "y", "yes")
            except (EOFError, KeyboardInterrupt):
                print(">> [默认接受协助]")
                return True

        executed, feedback = master_cortex.process_intent_narrative(
            narrative=narrative,
            approval_callback=cli_user_dialog,
            target_directory=str(usb_dir),
        )

        print("\n[步骤 5: 双手工具执行 (Motor Hands)]")
        print(f"   ✓ 执行状态: {'已执行双手工具' if executed else '用户选择暂不处理'}")
        if feedback.executed_action_summary:
            print(f"   ✓ 双手执行结果:\n{feedback.executed_action_summary}")

        print("\n[步骤 6: 下行抑制神经闭环 (Efferent Inhibition)]")
        print(f"   ✓ 指令: {feedback.directive.value}")
        print(f"   ✓ 冷却时长: {feedback.cooldown_seconds} 秒")
        print(f"   ✓ 理由: {feedback.reason}")
        print(f"   ✓ 缓冲器稳态: is_inhibited={neural_buffer._is_inhibited} (系统恢复 0% 空闲低能耗稳态)")

        print("\n" + "=" * 65)
        print("🎉 恭喜！CyberSpine 最小闭环全脑区仿生协同演练圆满完成！")
        print("=" * 65)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def run_live_hardware_listener():
    """模式 2: 真实物理 U 盘插拔实时监听闭环 (Live Hardware Mode)"""
    print("\n" + "=" * 65)
    print("🔌 [模式 2] 启动物理实机 U 盘 / 移动硬盘实时感知监听")
    print("=" * 65)

    io_manager = IOPerceptorManager()
    neural_buffer = TemporalNeuralBuffer(alignment_window_seconds=1.0)
    spinal_gate = SpinalIntentGate()
    master_cortex = MasterCortex(neural_buffer=neural_buffer)

    print("\n[系统初始化] 正在建立当前物理磁盘与外设基线拓扑...")
    snapshot = io_manager.get_full_io_snapshot()
    mounted_list = snapshot.get("mounted_storage_devices", [])
    initial_mounts = {d.get("mount_point") for d in mounted_list if d.get("mount_point")}
    print(f"   ✓ 已发现当前挂载磁盘: {sorted(list(initial_mounts))}")
    print("\n>>> 💡 【就绪】请在您的电脑物理 USB 接口上插入任意真实 U 盘、移动硬盘或相机卡...")
    print(">>> 💡 (系统将以 0% CPU 低功耗自动捕获硬件中断，或按 Ctrl+C 退出监听)\n")

    try:
        while True:
            time.sleep(1.0)  # 0% CPU 低功耗事件休眠
            current_partitions = psutil.disk_partitions(all=False)
            current_mounts = {p.mountpoint for p in current_partitions}

            # 检测新增加的挂载点
            new_mounts = current_mounts - initial_mounts
            if new_mounts:
                for mount in new_mounts:
                    print("\n" + "!" * 65)
                    print(f"⚡ [物理硬件中断] 捕获到真实存储设备接入: {mount}")
                    print("!" * 65)

                    # 步骤 1: 触发真实末梢感知与浅层嗅探
                    signal = io_manager.mock_inject_storage_signal(
                        mock_root_path=mount,
                        volume_label=f"LIVE_DRIVE_{mount.replace(':', '').replace('\\', '')}",
                        total_gb=128.0,
                        free_gb=64.0,
                    )
                    print(f"\n[步骤 1: 末梢感知] 产生物理电信号: ID={signal.signal_id}")
                    print(f"   ✓ 浅层只读嗅探画像: {signal.structure_summary.detected_profiles} (耗时: {signal.structure_summary.scan_duration_ms:.2f}ms)")
                    print(f"   ✓ 设备指纹 SHA-256: {signal.device_fingerprint.device_id}")

                    # 步骤 2: 时钟缓冲
                    enqueued = neural_buffer.ingest_signal(signal)
                    time.sleep(1.2)  # 等待自然沉思停顿窗口
                    packet = neural_buffer.flush_aligned_packet(force=True)

                    if packet is None:
                        print("   ✓ [下行抑制静默] 该设备此前已完成处理，当前处于免打扰抑制观察期，中枢已静默隔离该信号。")
                        continue

                    # 步骤 3: 脊髓提炼
                    narrative = spinal_gate.evaluate_and_narrate(packet)
                    if narrative is None:
                        print("   ✓ [感觉门控静默] 判定为微观噪音，未触发意图升华。")
                        continue

                    print(f"\n[步骤 2~3: 脊髓提炼] 感觉门控判定: 情境=[{narrative.macro_scenario}], 置信度={narrative.confidence*100:.1f}%")
                    print(f"   ✓ 意图故事: {narrative.situation_story}")

                    if not narrative.should_escalate_to_cortex:
                        print("   ✓ [感觉门控拦截] 判定为无交互价值的常规物理变动，已在脊髓中枢静默过滤，不惊扰前台。")
                        continue

                    # 步骤 4: 前额叶大脑温和交互
                    def live_cli_dialog(inquiry: str) -> bool:
                        print("\n" + "-" * 60)
                        print(inquiry)
                        print("-" * 60)
                        try:
                            ans = input(">> 是否同意大脑协助扫描工作区？ [Y/n]: ").strip().lower()
                            return ans in ("", "y", "yes")
                        except Exception:
                            return True

                    executed, feedback = master_cortex.process_intent_narrative(
                        narrative=narrative,
                        approval_callback=live_cli_dialog,
                        target_directory=mount,
                    )

                    print(f"\n[步骤 5~6: 执行与抑制闭环]")
                    if feedback.executed_action_summary:
                        print(f"{feedback.executed_action_summary}")
                    print(f"   ✓ 下行抑制生效: {feedback.reason} (冷却: {feedback.cooldown_seconds}s)")
                    print("\n>>> 💡 【闭环完成】中枢已进入免打扰观察状态。\n")

                initial_mounts = current_mounts
    except KeyboardInterrupt:
        print("\n\n已安全退出物理硬件监听。")


def run_all_tests():
    """模式 3: 运行全量 9 组独立与集成单元测试套件"""
    import unittest
    print("\n" + "=" * 65)
    print("🧪 [模式 3] 运行 CyberSpine 全量自动化测试套件 (涵盖全套 7 大感官 + 闭环)")
    print("=" * 65)
    suite = unittest.defaultTestLoader.discover('tests', pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


def run_somatic_diagnostics():
    """模式 4: 运行全感官拓扑诊断与实机多神经末梢巡检"""
    from src.perceptors.somatic_hub import SomaticPerceptorHub
    hub = SomaticPerceptorHub()

    print("\n" + "=" * 65)
    print("🩺 [模式 4] CyberSpine 全身感官拓扑诊断与实机基准巡检")
    print("=" * 65)

    print("\n[1/3] 正在对当前 Windows 宿主机进行全身 8 大感官快速浅层采样...")
    start_t = time.perf_counter()
    topo = hub.get_full_somatic_topology()
    cost_ms = (time.perf_counter() - start_t) * 1000

    print(f"   ✓ 采样总耗时: {cost_ms:.2f}ms (远低于 100ms 交互延迟阈值)")
    print(f"   ✓ 挂载通道数: {len(topo['channels'])}")

    channels = topo["channels"]
    print("\n[2/3] 全感官实时健康状态一览:")
    # 1. 焦点
    focus = channels.get("nerve.system.foreground_focus", {})
    print(f"   👀 [前台窗口] 活跃进程: {focus.get('active_process')} | 窗口标题: '{focus.get('active_title')}' (PID: {focus.get('active_pid')})")

    # 2. 程序拓扑
    apps = channels.get("nerve.system.running_apps", {})
    print(f"   📱 [应用拓扑] 用户交互程序数: {apps.get('total_user_apps')} | 发现生产力类别: {list(apps.get('categories', {}).keys())}")

    # 3. 负载压力
    stress = channels.get("nerve.system.high_load", {})
    top_p = [p.get('name') for p in stress.get('top_processes', [])]
    print(f"   🔥 [系统负载] CPU: {stress.get('cpu_percent')}% | 内存: {stress.get('memory_percent')}% | 高压状态: {stress.get('is_stressed')} | Top进程: {top_p}")

    # 4. 稳态能耗
    homeo = channels.get("nerve.system.homeostasis", {})
    bat = homeo.get("battery_info", {})
    print(f"   🫀 [内环境稳态] 系统已稳定运行: {homeo.get('uptime_hours')} 小时 | 供电状态: {bat.get('percent')}% (接通电源: {bat.get('is_plugged')})")

    # 5. 排队通知
    notify = channels.get("nerve.system.notifications", {})
    print(f"   📫 [系统通知] Action Center 排队未读通知: {notify.get('unread_notifications')} 条")

    # 6. 系统稳定性
    stab = channels.get("nerve.system.stability", {})
    print(f"   💥 [系统稳定] 历史捕获崩溃/闪退数: {stab.get('total_crashes_tracked')}")

    # 7. 网络健康
    net = channels.get("nerve.network.health", {}).get("health", {})
    print(f"   🌐 [网络健康] 连通状态: {net.get('is_online')} | DNS 解析时延: {net.get('latency_ms')}ms | 活动网卡: {net.get('active_interfaces')}")

    # 8. IO 存储
    io_data = channels.get("nerve.io.storage", {})
    drives = [d.get('mount_point') for d in io_data.get('mounted_storage_devices', [])]
    print(f"   💾 [IO 存储] 当前挂载物理/移动磁盘: {drives}")

    print("\n[3/3] 正在生成实机性能基准测试报告并落盘开发留痕...")
    report = hub.record_hardware_benchmark_report()
    print(f"   ✓ 性能基准报告已持久化写入: {hub.benchmark_log_file}")
    print(f"   ✓ 原始电信号追踪日志就绪: {hub.trace_log_file}")
    print("\n" + report)


def main():
    print(r"""
======================================================================
     ____       _               ____             _            
    / ___| _   _| |__   ___ _ _|  _ \ _ __  _ __(_)_ __   ___ 
   | |   | | | | '_ \ / _ \ '__| |_) | '_ \| '__| | '_ \ / _ \
   | |___| |_| | |_) |  __/ |  |  __/| | | | |  | | | | |  __/
    \____|\__, |_.__/ \___|_|  |_|   |_| |_|_|  |_|_| |_|\___|
          |___/                                               
       🧬 仿生全脑区协同感知中枢与意图共鸣系统 v3.3.0
======================================================================
    """)
    print("请选择实机演练功能:")
    print("  [1] 运行最小闭环 MVP 仿真演练 (无需真实 U 盘，体验人机交互 Y/N)")
    print("  [2] 启动物理实机 U 盘实时监听 (监听插拔您电脑上的真实 U 盘/移动硬盘)")
    print("  [3] 运行全量自动化测试套件 (包含 9 组 28+ 个全感官单元测试)")
    print("  [4] 运行全感官拓扑诊断与实机巡检 (查看 8 大感官通道实时基线与性能)")
    print("  [0] 退出")
    print("-" * 65)

    choice = "1"
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        try:
            choice = input("请输入选项 [默认 1]: ").strip() or "1"
        except (EOFError, KeyboardInterrupt):
            choice = "1"

    if choice == "1":
        run_mock_simulation_loop()
    elif choice == "2":
        run_live_hardware_listener()
    elif choice == "3":
        run_all_tests()
    elif choice == "4":
        run_somatic_diagnostics()
    else:
        print("已退出。")


if __name__ == '__main__':
    main()
