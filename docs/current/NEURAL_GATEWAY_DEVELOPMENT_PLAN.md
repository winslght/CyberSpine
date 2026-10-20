# 中枢神经网关开发规划

**状态：已批准的开发规划；实现按阶段另行授权。**  
**适用范围：** `src/core/` 的信号准入、可靠传递、健康治理、审计与受限下行边界；并规定其与插件运行时、神经中枢、前端适配器的协作接口。  
**上位依据：** [项目方向与主线开发章程](PROJECT_DIRECTION.md)、[统一神经通信规范](UNIFIED_NEURAL_COMMUNICATION.md) 与 [安全准则](SECURITY_GUARDRAILS.md)。

## 1. 目标与非目标

中枢神经网关是所有末梢神经进入正式主干的唯一入口。它将经过验证、授权且可追溯的末梢事实变成可可靠消费的事实流；它不是感知器、意图引擎、模型调度器、执行器或插件商店本身。

```text
插件安装与信任管理 → 插件运行时 → 中枢神经网关 → 神经中枢上下文
                                      ↓                  ↓
                                队列、审计、订阅      外部适配器
```

网关不得：

- 重新采样窗口或其他末梢事实；
- 计算特定末梢的业务统计，或推断用户意图；
- 让插件直接执行本机动作、访问顶层大脑或绕过确认门控；
- 将远程插件商店、更新器或 UI 依赖放进 `core`。

## 2. 模块与依赖边界

`src/core/` 保持与 Windows、MCP、Ollama、UI 和网络实现无关；插件目录扫描、子进程、IPC、远程更新和商店 API 均为可替换适配器。

| 模块 | 职责 | 不负责 |
| --- | --- | --- |
| 信号契约 | `NeuralMessage`、Schema 标识、类别、TTL、隐私、关联与幂等语义 | 具体感知业务含义 |
| 网关准入 | 身份、会话、版本、topic、类别、权限、隐私、大小、速率和过期校验 | 解析未被声明的业务内容 |
| 持久队列 | 状态合并、事件去重、投递、确认、过期和可恢复读取 | 推断事件优先级 |
| 审计与健康 | 拒绝、节流、隔离、更新、授权和运行状态的脱敏证据 | 保存原始敏感感知内容 |
| 运行时协作接口 | 向受控运行时授予会话、配额和下行指令 | 启动进程、扫描目录或安装更新 |
| 上下文交接接口 | 通知 `context/` 有新的已准入事实可消费 | 组装上下文帧或产生意图结论 |

## 3. 插件接入、安装与热插拔

插件接入采用“发现 → 验证 → 安装 → 启用”四步；安装和启用必须分离。

1. **发现**：读取内置目录、本地已安装目录和用户明确配置的可信源。
2. **验证**：检查 manifest 的稳定 ID、版本、协议、入口、能力、Schema、权限、隐私、平台、采样方式和健康声明。
3. **安装**：将每个版本放入独立目录；安装包不自动获得运行资格。
4. **启用**：只有用户授权、宿主策略、协议兼容和信任检查均通过后，运行时才创建实例并授予本次会话能力。

实例状态机：

```text
discovered → verified → installed → disabled / enabled
enabled → starting → healthy ↔ degraded → quarantined
healthy / degraded / quarantined → stopping → stopped
```

热启用时，插件先发送 `hello`，网关返回已授权的 topic、资源配额、允许控制项和短期会话令牌；只有 `ready` 后才可发布事实。热停用时，网关先关闭新业务消息入口，再下发有超时的 `stop`；超时实例进入隔离而不阻塞其他插件或主程序。

内置低风险插件可先以受控同进程适配运行；第三方或高风险插件应进入独立子进程，并使用本地受认证 IPC。插件崩溃不得影响网关和其他插件。

## 4. 统一上行消息主干

每条上行消息必须经过以下固定顺序：

```text
安装包身份与会话
→ 协议与 Schema
→ 权限、隐私和载荷边界
→ TTL、大小、速率和资源预算
→ 幂等、状态合并或事件去重
→ 本地持久化
→ 脱敏审计
→ 上下文交接与订阅分发
```

- `state` 是最新可替换事实，使用稳定的 `collapse_key` 合并。
- `event` 是变化历史，仅按明确幂等键或 message ID 去重，不得误合并真实连续变化。
- `health` 与业务事实独立限流和存储，避免故障风暴挤占事实通道。
- 感知插件只允许发布在 manifest 与本次授权中声明的 `state`、`event`、`health`；`directive`、`proposal` 与 `result` 不得伪装成上行感知消息。

首个接入验收项是 manifest—注册一致性：窗口插件所声明的全部 `window.*` topic（包括 `window.geometry_changed`）必须与网关授权和测试夹具一致。

## 5. 健康、降级与病态信号抑制

健康检查不是单一 ping，而是四项独立结论：

| 维度 | 网关观测 |
| --- | --- |
| 存活 | 心跳、新鲜度、进程/线程状态、启动和退出超时 |
| 正确 | Schema 拒绝、权限越界、逻辑矛盾和重复异常 |
| 质量 | 延迟、事件速率、丢弃率、队列积压、校准成功率 |
| 安全 | 签名失效、资源超额、反复崩溃和异常 IPC 行为 |

插件自报的 `health` 只能作为输入；最终健康状态由网关的独立观测得出。处理按最小干预逐级升级：

```text
healthy → degraded（降频或只保留状态） → paused → quarantined
```

节流、拒绝、暂停和隔离均应产生脱敏审计/健康事件。神经中枢收到的是“该事实源不健康或不可用”的事实，不能将其推断为用户没有相关活动。

## 6. 上下文帧与窗口期递交

网关只转交事实；`context/` 将已准入消息投影为不可变、版本化、可追溯的只读上下文帧。上下文帧不复制无限原始事件，而引用有限的消息和时间窗口事实。

```json
{
  "schema": "cyberspine.context_frame@1",
  "context_id": "ctx_...",
  "captured_at": "...",
  "facts": {},
  "freshness": {},
  "provenance": {"sources": [], "message_refs": []},
  "limitations": []
}
```

窗口事实至少分为三个时间尺度：即时帧（当前前台）、短窗口（5–15 分钟的切换与交互统计）和历史窗口（如 30 分钟焦点片段与占比）。每项应携带来源、新鲜度、覆盖率和不确定性。窗口标题、输入内容、剪贴板、坐标和屏幕像素不得进入默认帧。

神经中枢可以基于多源帧产生带证据、置信度与不确定性的假设；网关和上下文投影不得把假设写成事实。

## 7. 下行控制面

上行事实流与下行控制流必须隔离：

```text
上行：插件 → 网关 → 队列 / 上下文
下行：中枢策略 → 网关 → 已授权插件
```

下行仅允许版本化且受 Schema 限制的 `directive`，例如 `sampling.configure`、`peripheral.pause`、`peripheral.resume`、`health.probe`，以及在用户明确授权的范围内开启诊断。每条 directive 必须绑定目标实例、声明过的控制能力、参数边界、TTL、关联策略、审批来源和审计 ID。

暂停末梢属于资源调节；移动窗口、读写文件、改变系统设置等行为属于受控动作，必须走“提议 → 用户确认 → 执行器 → result”的独立链路。

## 8. 更新与插件商店的供应链边界

远程版本检查、下载和商店不是网关核心，也不是第一阶段目标。它们必须作为适配器实现，并遵循分级演进：

1. 随主程序发布的内置插件，固定版本、离线可用、可审计。
2. 用户配置可信源后的手动更新，展示版本、兼容性、权限变化、发布说明和回滚路径。
3. 仅对用户明确订阅的通道提供受控自动更新；下载、验证、沙箱自检和原子切换均成功后才可替换，失败则保留旧版本。

远程检查只能发送完成更新协商所需的最小元数据，例如插件 ID、当前版本、协议版本和系统架构；不得上传感知事实、窗口内容、用户名、路径或完整工作上下文。

更新体系必须采用成熟供应链安全模型，而非“下载版本 JSON 后直接覆盖文件”：版本化、带过期时间和分角色信任的元数据可抵抗仓库或密钥局部失陷；安装包还应验证来源身份、签名和完整性。每个商店版本应逐步具备发布者身份、许可证、权限差异、兼容范围、SBOM、签名、撤销和安全公告。

## 9. 不可绕过的安全不变量

- 插件、manifest、IPC、商店元数据、更新包和 MCP 输入全部按不可信输入处理。
- 插件身份绑定安装包完整性、可信发布者和短期会话令牌，不能只相信 `source` 字符串。
- 每个插件拥有独立权限、资源预算、保留期和故障域。
- 边界消息必须限制大小、嵌套深度、频率、Schema、时间戳和可接受的扩展字段。
- 插件不得写入敏感上下文、绕过网关调用执行器，或篡改自身审计记录。
- 更新不得静默扩大权限、提高隐私级别、启用新能力或替换未通过验证的版本。
- 审计记录可追溯但需脱敏、最短保留，并对插件不可写。

## 10. 渐进实施顺序与验收

| 阶段 | 可验收产物 | 暂不做 |
| --- | --- | --- |
| G1 | manifest 驱动注册、会话与消息准入；窗口插件全 topic 一致性测试 | 动态下载、第三方运行时 |
| G2 | Schema/载荷限额、限流、审计、健康模型、降级与隔离 | 意图推理与动作执行 |
| G3 | 多插件只读上下文帧、投影和订阅接口 | 主动唤醒模型 |
| G4 | 受限下行 directive 与回执 | 任意系统操作 |
| G5 | 子进程插件运行时、热插拔与资源预算 | 远程商店自动安装 |
| G6 | 签名安装包、手动可信源更新与回滚 | 默认自动更新 |
| G7 | 商店治理和用户明确订阅的受控自动更新 | 未经授权的第三方自动执行 |

每阶段完成前必须具备：公开契约、隐私与失败行为、单元测试、至少一条集成测试、可检查的脱敏运行记录，以及旧 PoC 链路未成为新的事实源的证明。

## 11. 部门边界与所有权

“中枢神经网关”是一个逻辑部门，不是所有中间层能力的统称。下表是正式所有权；模块只能通过明确接口跨部门协作。

| 部门 | 代码落点 | 拥有的事实与决定 | 明确不拥有 |
| --- | --- | --- | --- |
| 末梢神经 | `src/sensing/`、第三方插件包 | 单一感知源的采集、脱敏、可验证的本地统计 | 跨源解释、网关绕过、动作执行 |
| 插件运行时与生态适配 | `src/adapters/plugin_runtime/`、`src/adapters/plugin_store/` | 目录扫描、子进程、IPC、安装、签名验证、更新、回滚 | 消息语义、权限最终裁决、上下文推理 |
| **中枢神经网关** | `src/core/` | 信号契约、准入、可靠队列、流量治理、健康结论、审计、受限 directive 裁决 | Windows 采样、进程启动、上下文帧、意图推理、UI |
| 神经中枢 | `src/context/`、后续本地推理适配器 | 多源事实投影、时间窗口、上下文帧、假设、升级事件和认知触发策略 | 改写末梢原始事实、绕过网关、执行未经确认的动作 |
| 外部适配与前端 | `src/adapters/`、`src/apps/` | MCP/IPC/Web 前端映射、状态展示、用户授权请求 | 直接读写插件进程、绕过网关修改队列或确认状态 |
| 受控动作 | `src/actions/` | 动作提议、确认、策略校验、执行和结果回写 | 把网关 directive 当作本机动作授权 |

上下文部门与网关的唤醒分界必须固定：网关只发出轻量的“已准入事实发生变化”通知；`context/` 负责短时间合并、生成 `ContextFrame`；神经中枢再决定是否值得进行认知评估或创建升级事件。网关不得因单条消息直接启动模型。

## 12. 跨语言末梢互操作标准

### 12.1 基本承诺

Python 是窗口感知参考实现的语言，不是插件协议的语言。任何语言只要满足本节的包、生命周期、传输和消息要求，都必须能以同样的启停、健康、隔离和权限体验接入。未来 Rust、C++、Go、Node.js、Java 和 .NET 插件不得依赖 Python 进程、Python 对象或 Pydantic 模型。

第一版跨语言运行时采用“独立子进程 + UTF-8 JSON Lines”：标准输入用于下行消息，标准输出只用于协议消息，标准错误只用于受控诊断。命名管道或本地 socket 可以作为后续等价传输适配器，但不得改变语义。

### 12.2 插件包与 manifest

第三方插件包的最低结构：

```text
<plugin-root>/
├─ manifest.json
├─ bin/ or entrypoint/       # 可执行文件、脚本或运行时入口
├─ schemas/                  # 该插件对外 payload Schema
├─ README.md
└─ LICENSE
```

manifest 必须能描述语言无关的进程入口。内置 Python 模块可由 Python 适配器承载，但不能成为第三方插件的唯一入口形式。

```json
{
  "plugin_id": "peripheral.system.status",
  "version": "1.0.0",
  "protocol_version": "1.0",
  "runtime": {
    "kind": "process",
    "command": ["bin/system-status-plugin.exe"],
    "transport": "cyberspine-jsonl@1"
  },
  "capabilities": ["system.resource_snapshot"],
  "signal_schemas": ["system.resource_snapshot@1"],
  "permissions": ["system.resource_metadata"],
  "privacy": {"classification": "metadata_only"},
  "health_check": {"heartbeat_seconds": 30}
}
```

`runtime.command` 必须是包内相对路径，禁止从 manifest 执行 shell 字符串、远程 URL、用户目录推断或未声明的参数。真实权限来自网关保存的本机 grant，而非插件自行声明的 `permissions`。

### 12.3 生命周期与 JSON Lines

跨语言生命周期固定如下：

```text
runtime 启动实例
→ plugin hello
→ gateway ready（会话、已授权 topic、配额、可用 directive）
→ state / event / health
→ pause / resume / configure / stop
→ result / goodbye
```

- 每一行必须是一个完整 UTF-8 JSON 对象；禁止在 stdout 输出日志、横幅或调试文本。
- `hello` 必须包含插件 ID、版本、协议版本、实例 ID 和 manifest 摘要哈希。
- `ready` 必须包含短期会话 ID、允许 topic、最大隐私级别、速率与消息大小限制、允许的下行能力和到期时间。
- 运行中的上行消息必须携带该会话 ID，并映射为 `NeuralMessage`。
- `stop` 必须可幂等；插件在规定超时内返回 `goodbye`，否则运行时终止其进程并由网关标记隔离。
- `health` 是插件自报输入；最终健康结论由网关独立产生。

### 12.4 稳定消息接口

跨语言边界以 JSON Schema 为准，Python 的 Pydantic 模型只是网关内部实现。所有协议字段使用 JSON 标准类型；时间使用 UTC RFC 3339 字符串；整数不得依赖语言私有数值类型；未知可选扩展字段的接受或拒绝必须由 Schema 明确。

| 消息 | 允许发布者 | 目的 |
| --- | --- | --- |
| `state` | 已授权末梢 | 最新可替换的单源事实 |
| `event` | 已授权末梢 | 有限、可追溯的变化事实 |
| `health` | 已授权末梢和网关 | 健康输入或网关健康结论 |
| `directive` | 网关 | 暂停、恢复、配置、健康探针等受限下行控制 |
| `result` | 目标插件 | 对 directive 的结构化回执 |
| `proposal` | 非感知插件 | 保留给动作提议链路，末梢不得发布 |

最小错误码族：`protocol_unsupported`、`manifest_invalid`、`session_invalid`、`topic_not_granted`、`privacy_exceeded`、`schema_invalid`、`message_too_large`、`rate_limited`、`message_expired`、`directive_not_granted`、`instance_unhealthy`。错误必须脱敏，不得回显原始敏感 payload。

## 13. G1/G2 文件级开发蓝图

本节是开始实现前的固定蓝图。除非经新的架构讨论，G1/G2 不新增未列出的职责；内部私有辅助函数可随测试发现最小化增加，但不得改变公开接口和不变量。

### 13.1 G1：manifest 驱动的准入与会话

| 文件 | 公开类型 / 函数 | 职责与关键规则 |
| --- | --- | --- |
| `src/core/neural_message.py` | `NeuralMessage`、`MessageKind`、`PrivacyClass` | 保持唯一信封；增加字段只能遵循协议兼容规则，不放 IPC 或进程代码。 |
| `src/core/plugin_manifest.py` | `PluginManifest`、`PluginRuntimeSpec`、`load_manifest(data)` | 验证稳定 ID、版本、能力、Schema、权限、隐私和跨语言 `runtime` 描述；只处理数据，不读磁盘、不启动进程。 |
| `src/core/plugin_registration.py` | `PluginGrant`、`PluginSession`、`RegistrationRegistry.register(manifest, grant)`、`open_session(plugin_id, instance_id, manifest_digest)` | 将声明与本机授权分离；创建有到期时间、不可伪造的会话。 |
| `src/core/gateway_errors.py` | `GatewayRejectionCode`、`GatewayRejected` | 提供稳定、可审计且不泄露 payload 的拒绝码。 |
| `src/core/gateway_admission.py` | `AdmissionPolicy.admit(message, session)` | 校验协议、会话、source、topic、kind、隐私、TTL、载荷大小和 Schema；成功返回原消息，不修改业务 payload。 |
| `src/core/neural_gateway.py` | `NeuralSignalGateway.register(...)`、`publish(message, session)`、`issue_directive(...)` | 只编排注册、准入、队列和审计接口；不组装上下文、不读 Windows。 |
| `src/core/event_queue.py` | `DurableEventQueue.enqueue/get/pending/acknowledge/expire_messages` | 延续持久化、状态合并与投递状态；不引入插件发现逻辑。 |
| `src/context/fact_projection.py` | `FactProjection.ingest(accepted_item)`、`snapshot()` | 消费已接受消息并形成事实投影；本文件属于中枢部门，不属于网关。 |
| `src/adapters/plugin_runtime/jsonl_protocol.py` | `decode_line(line)`、`encode_message(message)` | JSON Lines 编解码与行长度保护；不得判断业务授权。 |
| `src/adapters/plugin_runtime/process_host.py` | `PluginProcessHost.start(spec)`、`send(command)`、`stop(timeout)` | 启动、监控、停止子进程；不得自行接受或持久化神经事实。 |

G1 测试文件与最低断言：

| 文件 | 覆盖范围 |
| --- | --- |
| `tests/core/test_plugin_manifest.py` | 合法 Python/进程入口、缺字段、危险命令、版本不兼容、权限格式错误。 |
| `tests/core/test_plugin_registration.py` | grant 与声明不一致、会话过期、实例 ID 重放、同插件多实例。 |
| `tests/core/test_gateway_admission.py` | source/topic/kind/privacy/TTL/Schema/大小的接受与拒绝码。 |
| `tests/core/test_neural_gateway.py` | 准入成功后才入队；失败不污染队列或事实投影。 |
| `tests/adapters/plugin_runtime/test_jsonl_protocol.py` | UTF-8、单行 JSON、非法日志、行过长、未知字段。 |
| `tests/integration/test_window_gateway_contract.py` | 已完成的窗口末梢全部 manifest topic（含 `window.geometry_changed`）均可按 grant 接入。 |
| `tests/integration/test_non_python_plugin_contract.py` | 使用固定 JSON Lines 测试夹具模拟非 Python 进程，验证不依赖 Python 对象。 |

### 13.2 G2：流量治理、健康、审计与隔离

| 文件 | 公开类型 / 函数 | 职责与关键规则 |
| --- | --- | --- |
| `src/core/message_limits.py` | `MessageLimits`、`validate_size(message)` | 限制序列化后消息大小、payload 深度、字符串长度和集合长度。 |
| `src/core/flow_control.py` | `RateLimitPolicy.allow(session, message)`、`StateCollapsePolicy.key_for(message)` | 每插件/每 topic 限流；状态合并不能丢失 event。 |
| `src/core/plugin_health.py` | `HealthState`、`HealthAssessment`、`PluginHealthMonitor.observe(...)`、`assess(instance_id)` | 根据心跳、新鲜度、拒绝率、崩溃与资源额度得出网关健康结论。 |
| `src/core/isolation_policy.py` | `IsolationDecision`、`IsolationPolicy.decide(assessment)` | 输出 healthy/degraded/paused/quarantined；不直接杀进程。 |
| `src/core/audit.py` | `AuditEvent`、`AuditSink.record(event)` | 记录最小化、脱敏的安全和运行决定；存储实现由适配器提供。 |
| `src/core/neural_gateway.py` | `publish(...)` 的治理编排、`health_for(instance_id)`、`directive` 授权检查 | 将 G2 政策串入 G1 准入成功后的路径；不改变窗口业务 Schema。 |
| `src/adapters/plugin_runtime/process_host.py` | `pause(instance_id)`、`resume(instance_id)`、`terminate_isolated(instance_id)` | 执行已获授权的运行时操作并回传结果；最终隔离决定仍来自 `core`。 |

G2 测试必须证明：高频 `state` 被合并、真实 `event` 不被误合并、病态插件不能拖垮健康插件、隔离产生审计事件、旧消息不会被当作新鲜事实、下行 directive 不能超出 manifest/grant 范围。

### 13.3 G3 及以后：只冻结接口，不提前锁死内部函数

- G3 在 `src/context/` 增加 `ContextFrame`、`ContextFrameBuilder`、`ContextUpdateCoordinator`、`ContextTriggerPolicy`；它消费网关已接受消息并产生 `ContextFrameReady` 通知。
- G4 在 `src/core/` 扩展版本化 directive 与回执，在 `src/actions/` 单独实现用户确认和执行结果；两者不得混合。
- G5/G6/G7 的安装、商店、更新、签名与回滚落在 `src/adapters/plugin_runtime/`、`src/adapters/plugin_store/`；进入各阶段前需重新选择成熟组件并完成许可证、安全、离线和替换成本审查。
