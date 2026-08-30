# CyberSpine 核心研发全流程追踪日志 (Development Tracking Log)

本文档永久记录 CyberSpine 系统的各项重大架构设计、仿生器官接入、关键技术攻关与实机测试数据。

---

## 📅 2026-08-29 | 里程碑 3：AIDA64 便携共生与 11 大全身仿生末梢神经全面就绪

### 1. 核心需求背景
- **用户需求**：评估物理硬件器官的神经覆盖率，并以极低开销、零重型依赖、高隐私安全的原则，补齐缺失的高价值末梢神经；探讨并落实 AIDA64 硬件传感器套用与绿色共生模式；建立永久开发留痕日志库。
- **架构目标**：
  1. 突破普通 Python 在 Ring-3 用户态下无法读取风扇转速（Fan RPM）、CPU 封装温度、VRM 供电体温和 NVMe 硬盘温度的限制；
  2. 捕获用户键盘鼠标动量与心流节奏（沉思、稳定编码、离线）；
  3. 捕获瞬时工作记忆剪贴板语义模式（代码、JSON、URL、报错堆栈）；
  4. 保证在无 AIDA64 的环境下 100% 优雅降级为原生轻量探针。

---

### 2. 技术设计与关键攻关

#### A. AIDA64 共享内存极速解析与便携守护托管 (`src/perceptors/hardware/`)
* **共享内存机制 (Shared Memory)**：
  - AIDA64 原生支持向 Windows 共享内存 `AIDA64_SensorValues` 写入 XML 格式的实时硬件数据。
  - 使用 Python 标准库 `mmap.mmap(-1, 0x10000, "AIDA64_SensorValues", access=mmap.ACCESS_READ)` 进行微秒级内存读取（耗时 **0.05ms**，CPU 占用 **0.00%**）。
  - 解析提取：CPU Package 温度、CPU 风扇真实 RPM、GPU 核心/显存/热点温度、GPU 功耗 (W)、NVMe 硬盘温度与 VRM 供电温度。
* **便携共生与自动拉起 (`tools/aida64/` & `aida64_daemon.py`)**：
  - 提供 `tools/aida64/aida64.ini` 预置配置文件（`EnableSharedMemory=1`、`StartMinimized=1`、`HideFromTaskbar=1`）；
  - `Aida64DaemonManager` 启动时自动探测共享内存，若未运行且存在便携版可执行文件，自动通过 `/SILENT /MIN` 静默拉起；
  - 在 `.gitignore` 中忽略二进制文件，保证 Git 仓库纯净。
* **双模自适应保底**：若 AIDA64 未运行，自动调用 `psutil` 与 `nvidia-smi` 提取 RTX 4060 基础温度、功耗与显存占用，绝不报错。

#### B. 皮肤动量与心流节奏末梢 (`src/perceptors/system/input_kinetics.py`)
* **非侵入式动量统计**：
  - 调用 Windows `GetLastInputInfo` 获取毫秒级物理空闲时间差；
  - 判定心流层级：`BURST_TYPING_OR_INTERACTION`（高频交互 <3s）、`STEADY_FLOW`（稳定编码 <15s）、`DEEP_THINKING`（深度沉思 <60s）、`AWAY_FROM_KEYBOARD`（离开工位 >300s）；
  - **隐私铁律**：绝对不监听具体键位内容，仅统计时间差。

#### C. 瞬时工作记忆与剪贴板语义嗅探 (`src/perceptors/system/clipboard_semantics.py`)
* **64 位指针安全 Win32 API 适配**：
  - 显式声明 `user32.GetClipboardData.restype = c_void_p` 与 `kernel32.GlobalLock.restype = c_void_p`，彻底杜绝 64 位 Windows 下指针截断导致的内存访问崩溃；
  - 浅层语法嗅探：自动分类为 `SOURCE_CODE`、`JSON_DATA`、`URL_LINK`、`FILE_PATH`、`ERROR_STACK_TRACE` 或 `GENERAL_TEXT`；
  - 前 40 字符脱敏截断预览，杜绝敏感密钥泄露。

---

### 3. 全身 11 大神经通道拓扑总览

| 通道 ID | 生物仿生器官映射 | 采集指标与物理体征 | 采样耗时 |
|---|---|---|---|
| 👁️ `nerve.system.foreground_focus` | 视觉焦点 (Focal Vision) | 前台进程名、活动窗口标题、连续驻留秒数 | <0.2ms |
| 🧬 `nerve.system.running_apps` | 脑细胞拓扑 (Cortical Topology) | 83+ 用户进程分类画像 (IDE/浏览器/终端/工具) | <1.5ms |
| ⚡ `nerve.system.high_load` | 代谢紧绷度 (Metabolic Stress) | CPU 瞬间峰值、内存利用率、Top 3 负载应用 | <1.0ms |
| 🫀 `nerve.system.homeostasis` | 生物体温内稳态 (Homeostasis) | 电池电量、适配器供电状态、系统运行 Uptime | <0.5ms |
| 🔔 `nerve.system.notifications` | 前庭感觉 (Vestibular Alert) | Windows 通知中心未读消息队列 | <0.5ms |
| 🩹 `nerve.system.stability` | 免疫与创伤痛觉 (Nociception) | Application Error 事件、软件闪退崩溃侦测 | <1.0ms |
| 🌐 `nerve.network.health` | 远程触觉传导 (Axon Network) | 网卡链路速率、活动 IP、DNS 解析时延 (0.5ms) | <2.0ms |
| 💾 `nerve.io.storage` | 肢体外物接触 (Limb Tactile) | 移动磁盘/U盘插入拔出、SHA256 指纹、只读浅层嗅探 | <1.0ms |
| 🔥 `nerve.hardware.somatic_telemetry` | **核心内脏体温 (Visceral Thermals)** | **CPU 全核温度、风扇 RPM、GPU 功耗/显存、NVMe 体温** | **<0.1ms** |
| 🖐️ `nerve.system.input_kinetics` | **皮肤动量心流 (Kinetic Flow)** | **物理空闲秒数、心流阶段 (沉思/连续编码/离线)** | **<0.1ms** |
| 📋 `nerve.system.clipboard_semantics` | **瞬时工作记忆 (Working Memory)** | **剪贴板模式 (代码/JSON/URL/报错)、字符长度与摘要** | **<0.3ms** |

---

### 4. 自动化测试验证记录

执行测试套件：`tests/test_mcp_server.py`, `tests/test_mcp_stdio_stream.py`, `tests/test_new_somatic_perceptors.py`
- **测试结果**：**10 / 10 项单元与集成测试全部 PASS (100%)**，总执行耗时 8.568 秒。
- **实机运行数据**：
  - RTX 4060 GPU 实时体温：51.0°C ~ 56.0°C，功耗：14.5W ~ 53.9W；
  - 键盘鼠标动量采样：精准捕获连续高频交互 (`BURST_TYPING_OR_INTERACTION`)；
  - 剪贴板语义分析：精准识别报错堆栈 (`ERROR_STACK_TRACE`) 并安全截断；
  - MCP JSON-RPC 2.0 管道：11 大通道数据 100% 纯净下发，零协议乱码。

---

## 📅 2026-08-29 | 状态盘点：中枢推演引擎 (llama-server.exe) 架构核验与端侧模型切换缺口

### 1. 实机推演进程核验
- **推理后端确认**：系统当前通过 `ollama.exe`（PID 15888）拉起 CUDA 运行时 `runners/cuda_v12/llama-server.exe`（PID 22208）进行物理 AI 交互推演，全量运行于 NVIDIA GeForce RTX 4060 Laptop GPU 显存中。
- **模型库现状**：
  - 🟢 已安装并活跃：`qwen2.5:0.5b`（379.4 MB / 494M 参数，占用显存约 569 MB）；
  - ⚪ 尚未安装：`qwen2.5:3b`（约 1.9 GB）、`qwen2.5:1.5b`（约 980 MB）。

### 2. 识别到的架构与功能缺口 (Gaps Identified)
1. **引擎层缺乏显式热切换 API**：`LocalModelEngine` 目前为静态/被动初始化选择，缺少 `set_active_model(model_name)` 动态切换接口。
2. **WinUI 3 驾驶舱缺乏交互式下拉切换**：前端设置面板目前仅为静态展示卡片，未提供端侧活跃模型实时下拉选择与一键切换组件。
3. **MCP 神经协议层缺乏算力升降级工具**：高级大脑尚未拥有 `cyberspine_switch_model` 等能够根据任务复杂度动态调整端侧小脑规格的 MCP 神经指令。

---

## 📅 2026-08-29 | 里程碑 4：借鉴 WinUIonWeb 全面重构 Windows 11 Fluent 原生前端驾驶舱

### 1. 核心改进措施
- **去除杂乱 Emoji，全量替换为 Segoe Fluent SVG 矢量线框图标**；
- **实现标准的 Windows 11 Mica Alt 与卡片微光边缘**（`border-top: 1px solid rgba(255,255,255,0.14)`）；
- **集成 WinUI 3 核心控件**：
  - `winui-select` (ComboBox 下拉选择器)：支持在驾驶舱顶部与分脑页面**即时热切换端侧模型 (`qwen2.5:0.5b` ↔ `qwen2.5:3b`)**；
  - `winui-toggle-switch` (胶囊滑动开关)：支持对 11 大感官末梢进行热插拔开启与停用；
  - `winui-settings-card` (设置卡片)：标准左侧图标底盘 + 标题/副标题 + 右侧操作控件；
- **后端双向联动支持**：在 `LocalModelEngine` 与 `CyberSpineAppBridge` 增加 `set_active_model(model_name)` 与 `switch_model(model_name)`，前后端热切换秒级生效。

---

## 📅 2026-08-29 | 里程碑 5：确立 8 大页面架构并完成 Page 1【中控仪表盘】5 大模块构建

### 1. 架构确立与可收缩导航栏
- 编写 [`docs/tracking/ROADMAP.md`](file:///c:/Users/winslght/OneDrive/Desktop/Vibe%20Coding/CyberSpine/docs/tracking/ROADMAP.md) 正式确立 CyberSpine 8 大功能页面与规格定义；
- 实现 WinUI 3 汉堡按钮 `[≡]` 可收缩导航栏（展开 250px ↔ 紧凑 62px，带 Tooltips 与平滑 Bezier 过渡）。

### 2. Page 1【中控仪表盘】5 大核心模块全部就绪
1. **模块 1：当前 1 分钟世界感知 (150~200 字深度长文)**，带 Qwen2.5 @ RTX 4060 GPU 来源透明徽章与时间戳；
2. **模块 2：当前意图判断与大脑介入裁决**（注意力焦点、用户工作流推演、大脑升级裁决）；
3. **模块 3：神经中枢运行状况统计条**（连续运转总时长 Uptime、起搏心跳总数 Ticks、GPU 显存/功耗、在线末梢计数）；
4. **模块 4：神经中枢 AI 总结长文**（端侧 AI 对计算机各脏器生理稳态与安全态势的精炼总结）；
5. **模块 5：已启用神经末梢实时状态流水**（11 大感官末梢实时结构化捕获消息网格卡片，每 5.0 秒同步刷新）。



