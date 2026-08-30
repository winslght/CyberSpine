# Project: CyberSpine 全脑仿生神经中枢桌面系统

## Architecture
- **Host Engine**: PyWebView (Microsoft Edge WebView2 原生 WinUI 3 Fluent Design 亚克力渲染)
- **Application Bridge**: `src/app/app_bridge.py` (`CyberSpineAppBridge` 挂载为 `window.pywebview.api`)
- **Autonomic Pacing**: `src/pacing/real_pacemaker.py` (`RealAutonomousPacemaker` 5.0s 独立常驻后台守护线程)
- **Somatic Perceptors**: `src/perceptors/` (8 大物理硬件感官末梢 + 3 大扩展插件)
- **Neural Buffer**: `src/pacing/neural_buffer.py` (时空对齐机与下行抑制时钟缓冲)
- **Spinal Core**: `src/spinal_core/intent_gate.py` (感觉门控与意图叙事提炼)
- **Cognitive Cortex**: `src/cortex/master_cortex.py` (前额叶 3W 认知推演与高情商退避)
- **Local Model Engine**: `src/models/local_engine.py` (本地 Ollama RTX 4060 GPU / qwen2.5 真实推理与启发式规则脑降级)
- **Motor Hands Actuators**: `src/actuators/` (安全三定律门控 + VSCode/资源管理器/电源方案物理执行)
- **Cognitive Telemetry**: `src/app/telemetry_logger.py` (环形缓冲 + JSONL 结构化持久化)

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 5.0s 真实自主起搏器与日志追加 | 5.0s 周期后台线程采样 Win32/psutil/DNS/外设，追加写入 heartbeat_ticks.log | M1 | Survey (R1/AC1) |
| 2 | 前台心流连续驻留计时与 60s 简报 | 进程切换比对计时，12 次心跳自动生成 60s 小脑宏观世界状态简报 | M1 | Survey (R1/AC1) |
| 3 | 8 大神经感官物理采样与基线 | 前台、应用拓扑、负载、稳态、通知、稳定性、网络、IO 设备指纹物理采样 | M1 | Survey (R1/R2) |
| 4 | 神经末梢热插拔物理连通 | 插件商店开关 100% 联动 BasePerceptor.enabled 与 SomaticPerceptorHub 轮询过滤 | M1 | Gap Miner (R2) |
| 5 | 扩展插件市场安装与依赖校验 | 视觉(Qwen2-VL)、听觉(Whisper)、剪贴板流转插件安装与依赖检测 | M1 | Gap Miner (R2) |
| 6 | 本地 Ollama 真实双向通讯与版本探测 | HTTP 探测 localhost:11434，版本查询与已下载模型列表 | M2 | Survey (R3/AC2) |
| 7 | Qwen2.5 动作帧真实 GPU 前向推理 | 调用 /api/generate 强约束 JSON 动作帧，毫秒级时延计算 | M2 | Survey (R3/AC2) |
| 8 | 动态 Token/s 与 GPU 显存指标提取 | 解析 eval_count/eval_duration 计算 Token/s，查询 /api/ps 获取 VRAM | M2 | Gap Miner (R3) |
| 9 | 启发式规则脑 0 崩溃平滑降级 | Ollama 离线或异常时自动降级纯 Python 规则脑产出合规动作帧 | M2 | Survey (R3/AC2) |
| 10 | 大脑连接器配置与灵敏度调节 | Claude 3.5 Sonnet / DeepSeek-R1 / GPT-4o 端点与密钥配置 | M2 | Survey (R1/R5) |
| 11 | 运动双手：应用与窗口调度 | 调起 VSCode 工作区与 Windows 资源管理器打开目录 | M3 | Survey (R4/AC3) |
| 12 | 运动双手：VSCode 路径自适应兼容 | 自动探测 PATH 及 LocalAppData 默认安装路径，增强唤起兼容性 | M3 | Gap Miner (R4) |
| 13 | 运动双手：工程工作区创建与预检 | 扫描目录、创建多级工程目录、检查 Python/Git 依赖 | M3 | Survey (R4/AC3) |
| 14 | 运动双手：Windows 电源方案动态调节 | powercfg 查询与切换高性能/平衡/节能模式 | M3 | Survey (R4/AC3) |
| 15 | 安全三定律门控 (Safety Gate) | 只读自动放行、变更强制审批、高危破坏物理硬熔断拦截 | M3 | Survey (R4/AC3) |
| 16 | 4 阶段全链路即时感知推演 | 身体采样 ➔ 脊髓时钟对齐 ➔ GPU 模型推理 ➔ 动作推演 | M4 | Survey (R5) |
| 17 | 认知透视帧分类与 JSONL 持久化 | 环形缓冲记录 SOMATIC/SPINAL/MODEL/ACTION/SYSTEM 日志并异步持久化 | M4 | Survey (R5) |
| 18 | 一键启动与诊断批处理脚本 | 便捷启动驾驶舱、环境校验与日志监听 | M3 | Survey (R5) |
| 19 | 全量 18 组测试套件 100% 绿灯回归 | 56+ 测试用例全部通过，验证 R1-R5 与 AC1-AC4 物理闭环 | M4 | Survey (AC4) |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 神经感官与插件热插拔物理连通 | Features 1, 2, 3, 4, 5: BasePerceptor enabled 物理联动, Hub 轮询过滤, 插件安装与依赖检测 | None | PLANNED |
| M2 | 本地 Ollama GPU 神经网络与动态度量 | Features 6, 7, 8, 9, 10: Ollama 真实推理, eval_count/eval_duration 动态 Token/s, /api/ps VRAM 采集 | None | PLANNED |
| M3 | 运动神经双手执行器强化与启动工具 | Features 11, 12, 13, 14, 15, 18: VSCode 自适应路径查找, 安全三定律, 一键脚本 | None | PLANNED |
| M4 | 6 大核心视图端到端物理闭环与全量绿灯交付 | Features 16, 17, 19: 6 大视图集成验证, 18 组测试套件 100% 绿灯, 挑战者与审计门禁 | M1, M2, M3 | PLANNED |

## Interface Contracts
### `SomaticPerceptorHub` ↔ `BasePerceptor`
- `BasePerceptor.enabled`: `bool` (default True)
- `BasePerceptor.set_enabled(enabled: bool) -> None`
- `SomaticPerceptorHub.set_perceptor_enabled(perceptor_id: str, enabled: bool) -> bool`
- `SomaticPerceptorHub.poll_all_signals()`: 必须跳过 `enabled=False` 的探针

### `LocalModelEngine` ↔ `CyberSpineAppBridge`
- `LocalModelEngine._infer_with_ollama()`: 返回字典需包含 `tokens_per_sec: float` (由 `eval_count / (eval_duration / 1e9)` 动态计算)
- `LocalModelEngine.get_gpu_vram_info() -> Dict[str, Any]`: 查询 `/api/ps` 返回真实已加载显存
- `CyberSpineAppBridge.get_ganglion_status()`: 动态注入实时 `token_per_sec` 与 `vram_mb`

### `AppControlActuator` ↔ Windows OS
- `AppControlActuator._find_vscode_executable() -> str`: 优先使用 PATH 中的 `code`，若未找到则自动扫描 `%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe`

## Code Layout
- `cyberspine_cockpit.py`: 桌面应用启动入口
- `src/app/`: 桌面应用宿主、IPC Bridge (`app_bridge.py`)、认知透视日志 (`telemetry_logger.py`)
- `src/pacing/`: 物理起搏器 (`real_pacemaker.py`)、神经时钟缓冲 (`neural_buffer.py`)
- `src/perceptors/`: 8 大神经末梢 (`base.py`, `somatic_hub.py`, `system/`, `network/`, `io/`)
- `src/models/`: 本地模型引擎 (`local_engine.py`)、神经电信号数据契约 (`somatic_signals.py`)
- `src/cortex/`: 前额叶认知主脑 (`master_cortex.py`)
- `src/spinal_core/`: 脊髓中枢门控 (`intent_gate.py`)
- `src/actuators/`: 运动神经双手 (`actuator_hub.py`, `safety_gate.py`, `app_control.py`, `workspace.py`, `power.py`)
- `src/ui/`: WebView2 前端资源 (`index.html`, `js/app.js`, `styles/winui3.css`)
- `tests/`: 18 组单元与端到端测试套件
- `03_本地日志与监控_logs/`: 物理心跳与认知透视日志落盘目录
