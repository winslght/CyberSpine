
# CyberSpine 逆向教学教材

> 取证范围：本教材只根据当前工作区中的 Python、批处理、清单与测试代码编写；没有把 README、设计方案或命名当作“功能已实现”的证据。最后一次已提交版本为 `d7aa42a`，但工作区还有一组未提交的网关实现。因此，本文中的“当前”指**此刻工作区**，不等于已发布或已合并版本。

## 先给负责人一句话结论

CyberSpine 不是一个已经统一运行的“桌面 AI 中枢”。它是两代系统并存的仓库：

1. **历史 PoC 管线**已经有可启动的驾驶舱、手写 stdio MCP、轮询式感知器、起搏器、启发式/可选 Ollama 简报以及执行器。这条路径能运行部分真实 Windows/`psutil` 读取，但大量产品状态、插件商店条目和若干感知事件是内存模拟或启发式结果。
2. **新生产主线的雏形**已经有较可靠的 Windows 窗口元数据末梢、统一 `NeuralMessage`、SQLite 队列、网关准入、清单/会话、结构与隐私校验、限流、健康和脱敏审计。它还没有发现/启动插件的运行时，也没有常驻 daemon，更没有把这些部件接到驾驶舱、旧 MCP 或执行器。

最容易犯的错误是把“文件存在、测试存在、文档存在”说成“端到端能力已存在”。本教材全程用下列标记避免它：

| 标记 | 含义 |
|---|---|
| **[实]** | 代码确实执行 I/O 或实现了确定的本地逻辑；是否已经被正式入口调用另说。 |
| **[装配]** | 组件可被代码实例化并串联，但没有被正式常驻入口引用。 |
| **[测]** | 测试、fake、临时数据库或合成演示中的能力。 |
| **[预留]** | 接口、状态、字段或声明存在，但当前没有完整运行链路。 |
| **[旧]** | 历史 PoC 路径；不要把它当作新架构已经接通的证据。 |

## 本教材如何阅读

1. [01-全景和目录地图.md](01-全景和目录地图.md)：先识别两代系统及每个重要文件的职责。
2. [02-从入口到输出的真实执行路径.md](02-从入口到输出的真实执行路径.md)：理解每一个可运行入口究竟会启动什么，尤其是哪些不会启动新网关。
3. [03-中枢网关逐层拆解.md](03-中枢网关逐层拆解.md)：重点章节；逐个数据结构、验证顺序、调用关系解释 G1/G2 网关。
4. [04-架构映射技术债与重新接管路线.md](04-架构映射技术债与重新接管路线.md)：把代码映射为架构概念，列出断层、债务和学习路线。
5. [05-窗口感知末梢状态机教材.md](05-窗口感知末梢状态机教材.md)：逐层讲 Windows 事件、目录、前台宽限、时间窗和七种消息如何形成。
6. [06-历史PoC管线逐层解剖.md](06-历史PoC管线逐层解剖.md)：不美化旧链，明确它的真实 I/O、模拟输入、持久化和安全边界。
7. [07-测试证据与结论审计.md](07-测试证据与结论审计.md)：区分测试覆盖、Fake 证明和本次未运行项，提供可复查的结论来源。

## 三个必须牢牢记住的事实

```text
可启动的旧驾驶舱:
start_cockpit.bat
  -> src/app/cockpit_app.py
  -> CyberSpineAppBridge
  -> SomaticPerceptorHub / RealAutonomousPacemaker / 旧 MCP
  -> 不引用 NeuralSignalGateway

可启动的新网关观察演示:
scripts/monitor_gateway.py
  -> 临时 signals.db + 读 manifest + 开 session
  -> NeuralSignalGateway
  -> 终端仅显示脱敏计数
  -> 退出即删除临时数据库；没有消费者、上下文投影或 MCP 服务

新路径装配器（没有脚本调用）:
NeuralSpinalHub
  -> WindowActivityPeripheral -> Gateway -> DurableEventQueue -> CurrentContextStore
  -> 目前由 tests/context/* 构造
```

## 当前能力清单（严格分类）

| 区域 | 代码证据 | 真实状态 |
|---|---|---|
| Windows 窗口目录、前台、几何、驻留、事件合并 | `src/sensing/window_*.py` | **[实]** Windows 上可用；不读取标题、按键内容、鼠标坐标或屏幕像素。 |
| 窗口消息统一信封 | `WindowActivityPeripheral.collect_messages()` | **[实]** 产生七类已注册 schema 的元数据消息。 |
| 新网关对窗口消息的 legacy 兼容准入 | `NeuralSignalGateway._admit_legacy()` | **[实/装配]** `NeuralSpinalHub` 和集成测试可用；正式 monitor 不走这条装配器。 |
| manifest + grant + session 插件准入 | `plugin_manifest.py`、`plugin_registration.py`、`gateway_admission.py` | **[实/测]** 核心逻辑存在，gateway monitor 可演示；没有插件发现、启动、IPC 运行时。 |
| SQLite 入队、状态折叠、确认、TTL | `event_queue.py` | **[实]** 数据库行为已实现；没有派发 worker 或消费者重试器。 |
| 脱敏上下文快照 | `CurrentContextStore` / `CurrentContextReader` | **[装配/测]** `NeuralSpinalHub.collect_window()` 可投影；没有进程把它持续提供给 MCP。 |
| FastMCP 只读上下文工具 | `adapters/mcp/context_server.py` | **[预留/测]** 工厂函数存在；没有入口创建它。 |
| 旧驾驶舱与旧 MCP | `app/`、`mcp/` | **[旧]** 可启动的 PoC，未接入新协议，且含硬编码展示状态。 |
| 旧感知器/起搏器/模型 | `perceptors/`、`pacing/`、`models/` | **[旧]** 包含真实 `psutil`/Win32/网络读取与 mocks；不是新网关输入。 |
| 执行器安全门 | `actuators/` | **[旧]** 可路由少量动作，但不是新架构的确认—审计闭环。 |

## 交付边界

本教材没有修改任何业务代码，也不宣称测试已在本次编写时运行。测试文件只用来确认作者意图、Fake 边界和被覆盖的调用契约；“通过”只能由实际执行结果证明。
