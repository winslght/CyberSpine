# 06：历史 PoC 管线逐层解剖

本章的目的不是否定历史代码，而是让负责人能准确说出：它做了什么、没做什么、为何不能直接被称为新中枢。所有“旧”仅指它不属于当前的新 gateway 主线，并不等于文件一定不能运行。

## 1. 历史数据模型：另一种世界语言

文件：`src/models/somatic_signals.py`。

旧链的基本单位是 `RawSomaticSignal`，而不是 `NeuralMessage`。它的 channel、event type、metadata、设备指纹与结构摘要随后由 `TemporalNeuralBuffer` 合并为 `FusedSomaticPacket`，再可交给 `SpinalIntentGate` 产生 `IntentNarrative`，最后由 `MasterCortex` 处理。

```text
old perceptor
  -> RawSomaticSignal
  -> TemporalNeuralBuffer
  -> FusedSomaticPacket
  -> SpinalIntentGate
  -> IntentNarrative
  -> MasterCortex / old app / old MCP

new peripheral
  -> NeuralMessage
  -> NeuralSignalGateway
  -> DurableEventQueue
  -> CurrentContextStore
```

这两种模型不是字段不同的同一个协议。旧链的“融合/意图”模型没有 manifest/session/queue admission；新链也不会生成旧 `FusedSomaticPacket`。任何未来 bridge 都必须明确转换位置、隐私过滤和确认语义，不能偷偷复用 dict。

## 2. `SomaticPerceptorHub`：旧链的服务定位器

文件：`src/perceptors/somatic_hub.py`。

构造函数直接创建十个旧 perceptor：焦点、运行应用、高负载、稳态/电池、通知、稳定性、网络、AIDA64 硬件、输入动力学、剪贴板语义，另建 `IOPerceptorManager`。`all_perceptors` 是一个固定 list；IO 是额外分支。

### 2.1 poll 的真实行为

`poll_all_signals()`：

```text
for enabled old perceptor:
  try poll_signals()
  except Exception: continue

if IO enabled:
  try poll_io_signals()
  except Exception: pass

if signals:
  _append_signals_trace(signals)
return signals
```

这段确实会触发各 perceptor 的真实代码路径，但它有两个不能忽略的性质：

1. **异常被吞掉。**调用者只看到少信号，不知道是哪一个探针失败、是否因为权限、网络、Win32 或数据格式。它适合“演示不中断”，不适合可观测生产 runtime。
2. **信号原样落盘。**`_append_signals_trace()` 将 `RawSomaticSignal.model_dump()` 写入 `runtime/logs/perceptors_trace.jsonl`。旧模型是否包含敏感 metadata 取决于各 perceptor；这里没有新网关那种 schema/隐私审查和 redacted audit。

`get_full_somatic_topology()` 又对每个 perceptor 调 `get_baseline()`，并加入 IO snapshot。这是驾驶舱/MCP 的旧状态来源，不是读新 `CurrentContextReader`。

## 3. 旧 perceptor 逐类事实表

| 文件 | 输入/真实 I/O | 输出/局限 |
|---|---|---|
| `system/foreground_focus.py` | 复用 `WindowActivityPeripheral` 的状态读取。 | 再封装成旧 RawSomaticSignal；这是共享末梢，不是通过 gateway。 |
| `system/running_apps.py` | `psutil` 进程枚举。 | 应用分类依赖名称/规则；不等于语义理解。 |
| `system/high_load.py` | `psutil` CPU/内存/Top process。 | 阈值告警是规则，不是诊断。 |
| `system/system_homeostasis.py` | `psutil.sensors_battery()` 等。 | 桌面无电池时只能表示无数据/默认。 |
| `system/network_health.py` | 对默认 `1.1.1.1:53` socket connect。 | 这是实际外网尝试；失败可能是代理、防火墙、离线，而非“网络故障”。 |
| `system/input_kinetics.py` | Windows `GetLastInputInfo`。 | 测量 idle 秒数，不读取具体按键。 |
| `system/queued_notifications.py` | 当前实现有内部队列和 `mock_trigger_notification()`。 | 不是已实现 Windows Action Center 实时读取。 |
| `system/system_stability.py` | 当前实现有 `mock_trigger_crash_event()`。 | 不应宣称已监听完整 Windows Event Log。 |
| `system/clipboard_semantics.py` | 文件存在并进入 old hub。 | 必须逐条检查其实现/权限；它不是新 schema 过滤下的外围插件。 |
| `io/device_db.py` | 设备指纹持久/比对辅助。 | 不是 OS 的自动通知服务。 |
| `io/storage_probe.py` | 对给定目录做有限深度、特征文件探测。 | “工程画像”是规则性分类。 |
| `io/io_manager.py` | 有 `mock_inject_storage_signal()`。 | demo/e2e 的主要存储输入是 mock，不能当 USB 热插拔守护。 |
| `hardware/aida64_perceptor.py` | 尝试 AIDA64 shared memory，失败可 native fallback。 | 依赖外部 AIDA64/平台状态；不是仓库自带硬件监控 daemon。 |

此表的关键不是“哪些类名听起来很厉害”，而是每次使用前问：代码是否真的调用 OS/API？是否可能只读取本地模拟列表？是否吞了失败？输出是否经过新隐私边界？

## 4. 时间层：`TemporalNeuralBuffer` 与旧起搏器

### 4.1 buffer

文件：`src/pacing/neural_buffer.py`。

`TemporalNeuralBuffer` 接受旧 `RawSomaticSignal`，按 alignment window 收集，形成 `FusedSomaticPacket`。它还保存 inhibition 状态，可在特定时间内抑制信号。这是历史的时序对齐机制，不是 SQLite queue：

| 新 queue | 旧 buffer |
|---|---|
| SQLite 持久化 | 内存短窗 |
| `NeuralMessage` | `RawSomaticSignal` |
| ACK/DeliveryStatus API | 面向融合的 consume/clear 行为 |
| TTL/状态折叠 | 对齐窗口/抑制 |
| 新 gateway 前置准入 | old hub 输入后的聚合 |

二者服务不同问题，不能以“都有 buffer”合并概念。

### 4.2 `RealAutonomousPacemaker`

文件：`src/pacing/real_pacemaker.py`。

它是带单例语义的后台线程。app 启动会先尝试停止已有 instance、重设 `_instance`，然后创建 bridge；bridge 自己实例化 pacemaker。节拍器定时从 `SomaticPerceptorHub` 读取旧 topology/信号，维护 `HeartbeatTickRecord`，并周期性让 `LocalModelEngine` 生成 briefing。

它的真实风险不在于“线程存在”，而在于对象生命周期不透明：MCP handler、app bridge 和 tests 都可能构造相关对象，单例与多 hub 的绑定需要人工追踪。它不管理新 session、queue worker 或 FastMCP server。

## 5. `LocalModelEngine`：可选 Ollama 与规则 fallback

文件：`src/models/local_engine.py`。

它向 `http://127.0.0.1:11434` 的 Ollama API 探活、列模型、可拉模型、生成 action/briefing。模型在线时向 `/api/generate` POST 结构化 JSON prompt；失败时捕获异常并返回启发式 `ProposedAction` 或 heuristic briefing。

因此正确描述是：**代码能够尝试调用本机 Ollama，并在调用失败时按规则退化**。不能说“本地模型已被加载”或“GPU 推理已成功”，除非该机器运行时验证过。尤其旧 briefing 会把 old focus 的 `active_title` 等数据放进 prompt；这与新窗口末梢刻意不采集 title 的隐私边界不同，是两条路线不应混用的直接证据。

`cockpit_app.py` 还会尝试寻找特定用户路径下的 `ollama.exe` 或 PATH 中的 `ollama` 并后台 `ollama serve`。这属于旧 GUI 的外部副作用；本教材没有执行它。

## 6. 旧 app：为什么它既能展示又不能当真相源

`CyberSpineAppBridge` 同时是：

- pywebview 的 JS API；
- old hub/buffer/pacemaker/model/actuator 的创建者；
- dashboard 读模型；
- 进程内插件开关表；
- 插件商店/模型/Cortex 配置的展示数据；
- telemetry 写入点；
- 旧动作调用点。

这种混合带来的可见后果：`get_dashboard_data()` 能同时返回确实从 hub/pacemaker 得到的字段和预设 `_latest_briefing`/`_plugins_state` 字段。UI 不能区分它们的来源。比如一个插件显示“installed/enabled”只说明内存 dict 状态改变；它并不走 `PluginManifest`、不创建 session、更不启动 runtime。

`CognitiveTelemetryLogger` 同样是 singleton，内存环形 buffer 上限 300，并把 telemetry JSONL 追加至 `runtime/logs/cognitive_telemetry.jsonl`。它没有新 audit 的 payload 最小化策略；日志的 details 由调用者自由给入。

## 7. 旧 MCP：协议正确性与产品安全是两回事

`src/mcp/server.py` 的强项是 stdio 分流：保存真实 stdout 用于 JSON-RPC，改 `sys.stdout = sys.stderr` 让内部 print 不污染协议流。它能回答 initialize/ping/list/call，并将 handler 返回结果包成 MCP text content。

但业务 handler `src/mcp/tools.py` 创建的是 old app bridge，获取的是 old topology/briefing/ticks，动作提议则创建 `ProposedAction` 并直接交 `MotorActuatorHub`。它不会调用新 gateway，亦不从 `CurrentContextReader` 读取。

因此，“旧 MCP 能跑”证明手写 stdio JSON-RPC 能跑；不证明新 context 的数据最小化、session、queue 或持久审计已经覆盖 MCP。

## 8. 旧执行器：到底会做什么

| 文件 | 操作 | 风险分类的真实行为 |
|---|---|---|
| `actuators/workspace.py` | 目录扫描、项目目录创建、preflight。 | risk 来自 actuator 的 `evaluate_risk()`；具体文件操作仍是系统副作用。 |
| `actuators/app_control.py` | `os.startfile()`、`subprocess.Popen()` 启动 explorer/VSCode/白名单 app。 | launch/open 需要 approval；代码仍以 `shell=True` 启动 Popen，是应复审点。 |
| `actuators/power.py` | `powercfg /getactivescheme`、`/setactive`。 | set active 需 approval；get 失败时却返回 success 和默认 balanced，可能掩盖权限/系统错误。 |
| `actuators/safety_gate.py` | 查 actuator、关键词熔断、重算 risk、可选 callback。 | 黑名单只是一层；不是完整 action policy。 |
| `actuators/actuator_hub.py` | 注册上述三类并转发到 gate。 | 不与新 queue/audit/context 相连。 |

特别注意 `MasterCortex.process_intent_narrative()`：未传入 approval callback 时，旧代码默认 `is_approved=True`。这和仓库当前安全不变量要求的明确用户确认并不等价。它是历史 PoC 行为，接管新架构时不能复制。

## 9. 旧链的输出最终去哪儿

```text
perceptors -> RawSomaticSignal
  -> runtime/logs/perceptors_trace.jsonl（若有信号）
  -> old buffer / pacemaker
  -> old briefing / tick / telemetry
  -> cockpit dashboard 或 old MCP JSON-RPC
  -> 可选 ProposedAction -> SafetyGate -> OS action
```

与新链相比，最重要的缺口是：旧输入没有统一 session/schema admission，旧输出没有通过新 `CurrentContextReader`，旧动作没有持久化的 proposal/confirmation/result audit chain。这解释了为何主线迁移不能只改 UI 名称。

