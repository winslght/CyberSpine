# CyberSpine Core 端到端测试基础设施与 4-Tier 验证架构 (TEST_INFRA.md)

## 1. 架构愿景与测试哲学 (Vision & Philosophy)

CyberSpine 作为全脑仿生神经中枢桌面系统，融合了真实物理硬件采样（Win32 窗口、psutil、DNS 探测、USB 即插即用）、端侧 RTX 4060 GPU 神经网络推理（Ollama / Qwen2.5）、安全三定律门控以及操作系统级运动神经双手控制（VSCode、资源管理器、电源方案）。

为了确保从物理末梢感官到高阶大脑认知推演、再到双手安全执行的全链路 100% 物理闭环与工业级可靠性，本工程采用 **4-Tier 全景分层验证方法学 (4-Tier Testing Methodology)**：

```
+-------------------------------------------------------------------------+
|  Tier 4: 真实世界宏观工作负载与完整全生命周期 (Real-World Workloads)         |
|  - 跨组件端到端全链路闭环 (从硬件接入 -> 时钟对齐 -> 意图提炼 -> 双手执行 -> 抑制) |
+-------------------------------------------------------------------------+
|  Tier 3: 跨维度正交组合与状态机交互 (Pairwise Combinations)                |
|  - 感官通道状态 × 大脑推理引擎 × 动作风险等级 × 用户审批决策 × 节律抑制状态       |
+-------------------------------------------------------------------------+
|  Tier 2: 极限边界、异常容错与对抗防御 (Boundary & Corner Cases)            |
|  - 恶意指令注入熔断、畸变 JSON 容错、网络中断降级、超限缓冲区、特殊字符路径        |
+-------------------------------------------------------------------------+
|  Tier 1: 核心功能全覆盖与接口契约 (Feature Coverage & Interface Contracts)|
|  - R1-R5 需求与 F1-F18 特征点的独立黑盒/不透明箱体功能性验证               |
+-------------------------------------------------------------------------+
```

---

## 2. 4-Tier 测试分层规范 (The 4-Tier Methodology)

### Tier 1: 特征全覆盖与接口契约测试 (Feature Coverage)
- **目标**: 针对 `PROJECT.md` 与 `ORIGINAL_REQUEST.md` 中定义的 R1~R5 及 Feature 1~18，验证每个核心功能模块在独立/标准上下文中的正确性与接口契约合规性。
- **覆盖范围**:
  1. **R1 / F1-F2 (物理起搏器与神经驾驶舱)**: 5.0s 周期后台采样、日志追加落盘 (`heartbeat_ticks.log`)、前台驻留计时、12 次心跳（60s）小脑宏观世界简报自动生成、驾驶舱 API 同步。
  2. **R2 / F3-F5 (全身感官与插件热插拔)**: 8 大物理感官基线拓扑快照、插件状态热启停 (`toggle_plugin`)、插件商店市场安装 (`install_plugin`) 与依赖校验。
  3. **R3 / F6-F10 (本地 SLM 与分脑协同)**: Ollama 真实双向通讯与版本探测、Qwen2.5 动作帧 JSON 强约束推理、动态 Token/s 与 GPU 显存采集、启发式规则脑 0 崩溃平滑降级、大脑连接器配置读写。
  4. **R4 / F11-F15 (运动双手与安全三定律)**: VSCode 路径自适应兼容查找与唤起、工作区目录扫描/创建/预检、Windows 电源方案查询与切换、安全三定律（只读放行、变更审批、破坏熔断）。
  5. **R5 / F16-F18 (认知透视终端与诊断)**: 5 大分类透视帧持久化 (`cognitive_telemetry.jsonl`)、4 阶段全链路即时感知推演 (`trigger_live_cognitive_cycle`)、诊断批处理与环形缓冲。
- **测试文件**: `tests/e2e/test_tier1_feature_coverage.py`

### Tier 2: 极限边界、异常对抗与容错测试 (Boundary & Corner Cases)
- **目标**: 验证系统在极端输入、异常网络环境、恶意命令注入及文件系统异常情况下的鲁棒性与绝对安全。
- **覆盖范围**:
  1. **安全三定律硬熔断对抗**: 针对包含 `rmdir /s /q`、`format C:`、`del /f /q`、`taskkill /f /im explorer.exe`、`reg delete` 等破坏性指令的动作参数，验证安全门控百分之百物理熔断拦截。
  2. **畸变 JSON 与模型超时平滑降级**: 当本地模型输出非 JSON 格式、截断文本或响应超时时，验证系统平滑降级至纯 Python 启发式规则脑，保证 0 崩溃。
  3. **异常与极端路径处理**: 测试包含 Unicode 特殊字符、中文空格、深度嵌套多级目录、不存在驱动器路径以及只读目录的扫描与创建。
  4. **并发与高频脉冲压力**: 连续高频触发手动心跳脉冲 (`trigger_manual_pulse`)，验证线程锁竞争、环形缓冲区越界处理与日志写入一致性。
  5. **认知透视缓冲溢出与清屏**: 测试超过最大容量 (`max_buffer_size`) 的高频透视帧入队与即时清屏。
- **测试文件**: `tests/e2e/test_tier2_boundary_corner.py`

### Tier 3: 跨维度正交组合与状态交互测试 (Pairwise Combinations)
- **目标**: 验证系统在多维度状态交织组合下的行为正确性与状态机迁移一致性。
- **正交测试矩阵**:
  - **维度 A (感官末梢状态)**: 全量启用 / 部分禁用 / 仅 IO 外设活跃
  - **维度 B (认知推理引擎)**: Ollama 真实 GPU 在线 / 启发式规则脑兜底
  - **维度 C (动作风险等级)**: `READ_ONLY_SAFE` (只读) / `MUTATING_APPROVAL` (变更) / `DANGEROUS_FORBIDDEN` (高危)
  - **维度 D (用户审批交互)**: 用户点击同意 (`True`) / 用户点击拒绝 (`False`) / 自动静默
  - **维度 E (神经抑制节律)**: 正常感知活跃 / 静默抑制期 (Cooldown Mode)
- **关键交互验证**:
  1. `[全感官 + 规则脑 + 变更动作 + 用户同意]` -> 成功执行并自动进入下行抑制。
  2. `[部分感官禁用 + 规则脑 + 变更动作 + 用户拒绝]` -> 安全退避，不执行物理操作，记录 WARN 级透视帧。
  3. `[任何感官 + 任何引擎 + 高危动作 + 用户同意]` -> 安全门控强制熔断，无视用户同意。
  4. `[静默抑制期 + 连续心跳]` -> 抑制状态持续保持，防止对用户产生重复打扰。
- **测试文件**: `tests/e2e/test_tier3_pairwise_combinations.py`

### Tier 4: 真实世界宏观工作负载与全生命周期测试 (Real-World Workloads)
- **目标**: 模拟用户在日常操作系统中的典型全链路操作场景，验证从硬件物理感知到中枢意图提炼、大脑推演、审批执行和反馈抑制的端到端真实闭环。
- **覆盖场景**:
  1. **场景 1: Python 研发工程师外设接入全链路闭环 (R1-R5 宏观工作流)**:
     - 用户接入包含 Git 与 Python 工程的存储介质；
     - 物理起搏器与 IO 探针捕获特征电信号；
     - 时钟缓冲器进行时间窗口对齐与融合打包；
     - 脊髓中枢门控判定为 `WORKSPACE_ATTACH_PYTHON_DEV`；
     - 大脑生成 `open_in_vscode` 动作建议；
     - 用户通过 AppBridge 审批同意；
     - 运动双手完成工作区探测；
     - 中枢触发 300s 下行神经抑制闭环；
     - 累计 12 次心跳生成 60s 小脑宏观世界简报；
     - 全程在 `cognitive_telemetry.jsonl` 与 `heartbeat_ticks.log` 真实留痕。
  2. **场景 2: 编译高压负载尖峰与动态电源方案调节**:
     - 模拟 CPU 瞬时负载超过 85%；
     - 神经中枢推演 `set_power_scheme` (HIGH_PERFORMANCE)；
     - 用户审批后安全执行电源策略切换；
     - 记录性能透视日志。
  3. **场景 3: 离线断网与模型中断情况下的自主平滑降级**:
     - 模拟断网与模型离线；
     - 触发即时感知推演；
     - 系统 0 崩溃无缝降级为内置启发式规则脑并产出有效动作帧。
  4. **场景 4: 多插件动态热插拔与工作区深度初始化**:
     - 插件商店动态切换与扩展插件安装；
     - 动态创建工程目录多级树并执行依赖预检 (`preflight_check`)。
- **测试文件**: `tests/e2e/test_tier4_real_world_workloads.py`

---

## 3. 需求追溯与覆盖率矩阵 (Traceability Matrix)

| 需求 ID | 需求描述 | 对应特性 | Tier 1 (功能) | Tier 2 (边界) | Tier 3 (组合) | Tier 4 (实机) |
|---|---|---|---|---|---|---|
| **R1** | 真实自主起搏器与神经驾驶舱 100% 实机闭环 | F1, F2 | `test_tier1_r1_*` | `test_tier2_r1_*` | `test_tier3_r1_*` | `test_tier4_scenario_developer_loop` |
| **R2** | 插件商店与神经末梢热插拔 100% 物理生效 | F3, F4, F5 | `test_tier1_r2_*` | `test_tier2_r2_*` | `test_tier3_r2_*` | `test_tier4_scenario_plugin_reconfig` |
| **R3** | 端侧小模型与分脑协同 100% 真实 GPU/规则降级 | F6, F7, F8, F9, F10 | `test_tier1_r3_*` | `test_tier2_r3_*` | `test_tier3_r3_*` | `test_tier4_scenario_offline_resilience` |
| **R4** | 运动神经元双手与安全三定律物理执行 | F11, F12, F13, F14, F15 | `test_tier1_r4_*` | `test_tier2_r4_*` | `test_tier3_r4_*` | `test_tier4_scenario_developer_loop` |
| **R5** | 认知透视终端与诊断流水线 | F16, F17, F18 | `test_tier1_r5_*` | `test_tier2_r5_*` | `test_tier3_r5_*` | `test_tier4_scenario_developer_loop` |
| **AC1** | 真实物理心跳与日志连续性 | F1, F2 | `test_tier1_r1_heartbeat_log_append` | `test_tier2_r1_rapid_pulse_stress` | `test_tier3_r1_inhibition_preservation` | `test_tier4_scenario_developer_loop` |
| **AC2** | 本地大模型真实推理有效性与 0 崩溃降级 | F7, F9 | `test_tier1_r3_model_inference_and_fallback` | `test_tier2_r3_malformed_json_fallback` | `test_tier3_r3_engine_risk_combinations` | `test_tier4_scenario_offline_resilience` |
| **AC3** | 运动神经元物理执行有效性 | F11, F13, F14 | `test_tier1_r4_motor_execution` | `test_tier2_r4_safety_fuse_injection` | `test_tier3_r4_approval_matrix` | `test_tier4_scenario_developer_loop` |
| **AC4** | 自动化回归测试 100% 绿灯 | F19 | 全部 Tier 1 用例 | 全部 Tier 2 用例 | 全部 Tier 3 用例 | 全部 Tier 4 用例 |

---

## 4. 运行与验证指令 (Execution Commands)

### 1. 全量运行 4-Tier 端到端测试套件
```powershell
uv run python -m unittest discover -s tests/e2e -p "test_tier*.py" -v
```

### 2. 运行单层测试套件
```powershell
# Tier 1: 功能覆盖
uv run python -m unittest tests.e2e.test_tier1_feature_coverage -v

# Tier 2: 边界异常与对抗
uv run python -m unittest tests.e2e.test_tier2_boundary_corner -v

# Tier 3: 正交组合
uv run python -m unittest tests.e2e.test_tier3_pairwise_combinations -v

# Tier 4: 宏观实机工作负载
uv run python -m unittest tests.e2e.test_tier4_real_world_workloads -v
```

### 3. 全项目单元 + 端到端回归测试
```powershell
uv run python -m unittest discover tests -v
```

---

## 5. 测试数据与环境隔离准则 (Data & Isolation Guidelines)
1. **独立临时工作目录 (`tempfile.mkdtemp()`)**: 所有文件系统操作（如 U 盘挂载模拟、工程目录创建、测试设备库）均在各自独立的临时目录中执行，并在 `tearDown()` 中安全清除，不污染宿主机。
2. **物理日志追加安全隔离**: 起搏器日志与认知透视日志在测试中验证真实追加写入能力，同时保障多线程并发安全。
3. **真实/模拟平滑双轨**: 针对外部硬件与网络依赖（如未连接的物理 U 盘、未启动的 Ollama GPU 服务），测试套件内置严格的确定性验证与断言，既能验证真实在线行为，也能验证离线优雅降级。
