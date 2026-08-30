# 命名规范

CyberSpine 借鉴人类神经系统的分层方式，但产品与代码命名应清楚、克制、可搜索。生物学术语只用于确实对应系统层级的组件；普通能力直接说明它“感知什么”或“做什么”。

## 命名原则

1. **先说职责，再说隐喻。** `窗口感知` 比“视觉神经元”更清楚。
2. **用户界面用中文职责名；代码用稳定英文名。** 不在代码标识符中混用中英文。
3. **一个术语只表达一个层级。** 插件、信号、中枢、顶层大脑不可互相混称。
4. **避免夸张措辞。** 不使用“全脑”“赛博生命”“神经驾驶舱”“绝对”“100%”等营销式名称作为模块、API 或测试名称。
5. **外部接口优先稳定与直白。** MCP 工具名描述返回内容或动作，不绑定某个比喻。

## 系统层级

| 层级 | 中文产品名 | 英文代码/目录名 | 职责 |
| --- | --- | --- | --- |
| 扩展能力 | 末梢神经（插件） | `plugins` / `peripherals` | 独立安装、启停的感知扩展。 |
| 具体能力 | 窗口感知、输入感知、系统状态感知、网络感知、存储感知 | `window_activity`、`input_activity`、`system_status`、`network_status`、`storage_status` | 采集单一类别的本机信息。 |
| 传递单元 | 神经信号 | `Signal` / `signal` | 末梢神经上报的标准化、可序列化事件。 |
| 汇总层 | 神经中枢（脊髓） | `spinal_hub` / `context` | 汇总信号、过滤噪音、形成当前上下文；可调用本地 Ollama。 |
| 本地推理 | 本地推理服务 | `local_inference` | Ollama 或其他本地模型的适配器，不称“分脑”或“小脑”。 |
| 上层协作方 | 顶层大脑 | `top_level_brain` / `cortex_adapter` | Codex、Claude 等拥有长程推理和工具能力的外部 Agent。 |
| 受控动作 | 执行器 | `actions` / `executors` | 经过确认后执行有限的本机动作。 |
| 审批策略 | 确认门控 | `approval_gate` | 拦截未确认、高风险或越权动作。 |
| 桌面界面 | 桌面控制台 | `apps/desktop_console` | 可视化状态、配置与日志；不称“驾驶舱”。 |

## 插件和信号命名

### 展示名

- 插件商店：`插件商店`。只有需要强调扩展架构时才写作“末梢神经插件商店”。
- 插件：`窗口感知`、`键盘与鼠标感知`、`系统状态感知`、`网络状态感知`、`存储设备感知`。
- 不使用“第 N 路神经”“全身感官”“物理体征”等编号或夸张表达。

### 稳定标识符

插件 ID 使用 `peripheral.<domain>.<capability>`：

```text
peripheral.window.activity
peripheral.input.activity
peripheral.system.status
peripheral.network.status
peripheral.storage.devices
```

信号类型使用 `<domain>.<event>`，不带“nerve”前缀：

```text
window.focus_changed
input.idle_changed
system.load_changed
storage.device_connected
```

Python 文件使用 `snake_case`，类使用 `PascalCase`：

```text
window_activity.py       → WindowActivityPeripheral
system_status.py         → SystemStatusPeripheral
signal.py                → Signal
spinal_hub.py            → SpinalHub
```

## MCP 命名

MCP 工具面向顶层大脑，使用动作或资源的直白名称：

```text
cyberspine_get_current_context
cyberspine_list_peripherals
cyberspine_set_peripheral_enabled
cyberspine_propose_action
cyberspine_confirm_action
```

不使用 `get_world_briefing`、`get_somatic_state`、`set_downward_inhibition` 等只靠内部隐喻才能理解的名称。若保留旧工具，先标记为兼容接口，再在一个版本周期后移除。

## 迁移规则

1. 旧名称不一次性全改；每次修改一个模块时，同时更新展示名、内部标识和测试。
2. 对外 ID 与 MCP 工具改名必须提供兼容别名，并记录废弃时间。
3. 新功能从本规范起直接使用新名字。
4. 文档、日志和 UI 中优先使用中文产品名；源码、配置和协议中使用英文稳定标识。

插件的连接、消息和兼容规则遵循 [末梢互连协议 PIP v1.0](PERIPHERAL_PROTOCOL.md)。
