# CyberSpine 8 大页面全景工程路线图 (Roadmap & Functional Specs)

> **历史 PoC 路线图，非当前工程排期或功能规格。** 本文记录早期概念验证阶段对驾驶舱、插件商店、模型和双向 MCP 的设想，不能据此实现或承诺功能。当前正式工程主线、范围与顺序分别以 [`../current/PROJECT_DIRECTION.md`](../current/PROJECT_DIRECTION.md)、[`../current/DEMO_SCOPE.md`](../current/DEMO_SCOPE.md) 和 [`../current/DEVELOPMENT_PLAN.md`](../current/DEVELOPMENT_PLAN.md) 为准。

本文档定义 CyberSpine 系统的完整 UI/UX 与功能页面规格书。按照模块化架构，我们将逐页进行高质量演进开发。

---

## 🧭 0. 可收缩导航架构 (Collapsible WinUI 3 Navigation Rail)
- **汉堡菜单按钮 `[≡]`**：支持一键在【完整展开模式（250px）】与【紧凑图标模式（58px）】之间无缝切换；
- **材质与动效**：Windows 11 亚克力半透明磨砂 (`backdrop-filter: blur(32px)`) + 活跃项蓝色胶囊指示条 (`Active Indicator Pill`)；
- **8 大一级页面路由**：
  1. `dashboard`：中控仪表盘（首屏默认）
  2. `plugins`：神经末梢插件商店（仿 Chrome 扩展管理）
  3. `models`：端侧模型中枢与监控（Qwen2.5 @ RTX 4060 GPU）
  4. `cortex`：上层大脑链接管理（MCP Neural Link）
  5. `topology`：完整循环神经走向动态路线图
  6. `logs`：核心神经中枢软件运行日志
  7. `mcp`：双向 MCP 协议互联中枢
  8. `settings`：系统全局设置与主题

---

## 📌 Page 1: 中控仪表盘 (Neural Command Center) - 【当前开发重点】

中控仪表盘是用户启动软件后的默认首屏，汇聚了系统感知与运转的核心脉搏，包含 **5 大关键功能模块**：

### 1. 模块 1：当前 1 分钟世界全景感知 (World State Perception)
- 展示由端侧大模型（Qwen2.5 @ RTX 4060）基于过去 60 秒时序数据推演生成的约 150~200 字全景感知长文；
- 来源透明徽章：`🟢 真实 AI 神经网络推演 (Qwen2.5 @ RTX 4060)`、`🔌 MCP 网关在线`、精确采样时间戳。

### 2. 模块 2：当前意图判断与大脑介入裁决 (Current Judgement & Escalation)
- **🎯 注意力焦点**：前台活跃应用名称、具体窗口标题关键词、连续驻留秒数；
- **💼 用户工作流推演**：当前正在进行的具体工作行为画像（如编写 Python 异步代码、查阅文档、调试前端）；
- **⚡ 高级大脑介入裁决**：`escalate_to_cortex` 布尔值、紧急度（`LOW`/`MEDIUM`/`HIGH`）、裁决理由与建议提示词。

### 3. 模块 3：神经中枢运行状况 (Neural Center Status)
- **运转总时长 (Uptime)**：自软件启动以来的累计运行时间（`hh:mm:ss`）；
- **心跳总次数 (Tick Count)**：5.0s 物理自主起搏器累计跳动次数（例如 `#1,842 次跳动`）；
- **节律稳态指示**：5.0s 精确硬件起搏律动指示条与实时采样状态。

### 4. 模块 4：神经中枢 AI 总结长文 (Executive AI Briefing)
- 结构化高亮呈现端侧 AI 对当前计算机状态、软硬件健康度与下一步建议的提炼总结。

### 5. 模块 5：已启用神经末梢实时状态流水 (Active Somatic Receptors Live Feed)
- 详细呈现当前已启用的 11 大物理感官末梢实时捕获的具体消息：
  1. 👁️ `nerve.system.foreground_focus`：当前活跃进程名、窗口标题、专注驻留时长；
  2. 🧬 `nerve.system.running_apps`：活跃应用总数与分类打标画像；
  3. ⚡ `nerve.system.high_load`：CPU 瞬间峰值、内存利用率、Top 负载进程；
  4. 🫀 `nerve.system.homeostasis`：电池电量、适配器供电状态、开机时长；
  5. 🔔 `nerve.system.notifications`：Windows 通知中心未读排队消息；
  6. 🩹 `nerve.system.stability`：系统崩溃与异常闪退监控；
  7. 🌐 `nerve.network.health`：DNS 解析时延 (0.5ms)、网卡状态与 IP；
  8. 💾 `nerve.io.storage`：存储磁盘与移动 U 盘状态；
  9. 🔥 `nerve.hardware.somatic_telemetry`：GPU 温度/功耗/显存、CPU 封装温度、风扇 RPM；
  10. 🖐️ `nerve.system.input_kinetics`：键盘鼠标动量、物理空闲时间与心流阶段（连续交互/沉思/离线）；
  11. 📋 `nerve.system.clipboard_semantics`：剪贴板内容类型（代码/JSON/URL/报错）、字符数与脱敏预览。

---

## 🧩 Page 2: 神经末梢插件商店 (Receptor Plugin Store)
- 仿 Chrome 插件管理界面；
- 区分【已安装】与【未安装/待挂载】插件；
- 纯粹专注感官末梢插件的安装、卸载、热插拔 ToggleSwitch 开启/停用与参数配置，不负责实时监测。

---

## 🧠 Page 3: 端侧模型中枢与监控 (Local SLM & Ganglion Hub)
- **显存与内存体征**：显存占用 (MB/%)、内存占用 (MB/%)、服务运转时间、GPU 温度与功耗；
- **推演 I/O 历史流水**：最近几次推演的 Prompt 输入与 JSON 动作/简报输出记录；
- **底部模型管理**：模型选择 ComboBox (0.5B/1.5B/3B/7B) 与一键拉取/删除管理。

---

## 🌐 Page 4: 上层大脑链接管理 (Master Cortex Link Connector)
- 当前连接状态徽章 (Connected / Waiting / Disconnected)；
- 最近交互日志与指令记录；
- 双向互通消息流查看器（上下行神经电信号与动作审批）。

---

## 🕸️ Page 5: 完整循环神经走向动态路线图 (Dynamic Neural Loop Topology)
- 动态 SVG/Canvas 可视化路线图：感官末梢 -> 时钟缓冲器 -> 端侧小脑 -> 安全门禁 -> 运动/大脑；
- 实时信号粒子流动动画与激活节点高亮。

---

## 📜 Page 6: 核心神经中枢软件运行日志 (System Core Telemetry & Logs)
- 软件全局系统日志、心跳时序流水、调试跟踪与异常捕获。

---

## 🔌 Page 7: 双向 MCP 协议互联中枢 (Bi-directional MCP Center)
- 作为 MCP Server：一键复制客户端 JSON 配置给 Antigravity/Claude/Cursor；
- 作为 MCP Client：连接顶层模型暴露的 MCP Server，实现双向 MCP 互传与反向控制。

---

## ⚙️ Page 8: 系统全局设置 (Global Settings)
- 深色/浅色/跟随系统主题；
- 起搏器心跳周期调节 (2.0s ~ 10.0s)；
- AIDA64 守护策略与日志清理。
