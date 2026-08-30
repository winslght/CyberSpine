# 统一神经通信规范 v1.0

**状态：实现起点**  
**代码事实来源：** `src/core/neural_message.py`、`src/core/neural_gateway.py`、`src/core/event_queue.py`

CyberSpine 内部只有一条消息主干。末梢神经、神经中枢、顶层大脑和宿主适配器都使用 `NeuralMessage`；MCP、JSON Lines、WebSocket 等只是在边界上的传输适配方式。

## 消息信封

| 字段 | 规则 |
| --- | --- |
| `protocol_version` | 当前为 `1.0`。|
| `message_id` | 全局唯一消息 ID。|
| `kind` | 仅为 `state`、`event`、`directive`、`proposal`、`result`、`health` 之一。|
| `source` / `target` | 稳定组件 ID；目标可省略。|
| `topic` | 精确的语义主题，如 `window.focus_changed`。|
| `payload_schema` | 可独立演进的载荷版本，如 `window.focus_changed@1`。|
| `privacy` | `public`、`metadata_only`、`sensitive`、`restricted`。|
| `ttl_seconds` | 可选有效期；过期消息不进入队列或投递。|
| `collapse_key` | 同一未完成状态的合并键。|
| `extensions` | 可选扩展；未知字段由接收方忽略。|

## 网关准入

每个插件须先登记来源 ID、允许 topic、允许类别和最高隐私级别。网关拒绝未登记来源、不在能力范围内的 topic/类别、越权隐私和不兼容版本；通过验证的消息才会进入本地 SQLite 持久队列。

第一版刻意采用 topic 精确匹配，保证每次权限扩大都可审计。通配主题、速率限制、审计记录、跨进程路由和下行调节将在保持相同信封的前提下扩展。

## 窗口感知参考插件

`peripheral.window.activity` 是第一个参考末梢神经，当前声明七项能力：

| 消息 | topic | schema | 行为 |
| --- | --- | --- | --- |
| 状态 | `window.current_state` | `window.current_state@3` | 当前前台窗口或明确的前台不可归因状态、专注驻留时间、交互监听健康状态。|
| 状态 | `window.catalog` | `window.catalog@1` | 完整顶层窗口目录，以及基于边界、最小化状态和已知系统宿主分类得出的屏幕呈现状态与用户窗口计数。|
| 事件 | `window.focus_changed` | `window.focus_changed@2` | 首次建立基线；后续前台窗口变更时上报前后窗口事实。|
| 事件 | `window.high_interaction_changed` | `window.high_interaction_changed@1` | 指定时窗内高频交互窗口集合发生变化。|
| 状态 | `window.time_window_summary` | `window.time_window_summary@1` | 窗口末梢在有限时间窗内整合出的焦点片段、专注时长/占比、切换次数和无内容交互统计。|
| 事件 | `window.foreground_availability_changed` | `window.foreground_availability_changed@1` | 可归因前台窗口消失或恢复；恢复时附带脱敏后的实际前台窗口身份，例如任务视图等系统过渡态。|
| 事件 | `window.geometry_changed` | `window.geometry_changed@1` | 顶层窗口的位置、尺寸或关联显示器变化；鼠标按住且边界变化时仅标为拖拽/调整大小候选。|

它是窗口事实的唯一采集实现。旧 `ForegroundFocusPerceptor` 仅是到旧
`RawSomaticSignal` 的兼容适配器，不得再直接调用 User32 或维护第二套焦点状态。

窗口目录使用 Windows `EnumWindows` 和只读窗口矩形信息，不读取屏幕像素或窗口内容。键盘/鼠标活动只记录按键按下、鼠标点击和滚轮的时间点，并归因给当时前台窗口；不记录键值、键入文本、鼠标坐标或剪贴板。原始窗口标题不进入统一消息，只发送 `has_title` 标记，因此上述消息可保持 `metadata_only`。

目录中的 `presentation` 将每个窗口标记为 `foreground`、`screen_present`、`minimized`、`offscreen` 或 `system_surface`。`screen_present_user_window_count` 只计前两类用户窗口；最小化窗口仍保留在完整目录中以支持后续恢复追踪。该分类只判断窗口是否与虚拟桌面相交，不宣称知道被遮挡、透明或像素级可见比例。

每个窗口还带有 `window_state`：最大化、置顶、关联显示器及“覆盖关联显示器边界”的全屏候选。全屏候选不代表已经识别独占全屏或像素级可见性。`geometry_activity` 只反映本次目录采样所见的边界变化；仅当鼠标按键按住且边界变化时才标为移动、调整大小或两者兼有的进行中候选。它不记录鼠标坐标、按键类型或窗口内容。

前台驻留时间的字段是 `focus_dwell_seconds`：它从本插件开始观察该窗口或最近一次焦点切换开始计时，不声称知道插件启动前的历史驻留时长。默认活动观察窗为 300 秒；高频判定默认需同时达到至少 6 次交互和每分钟 12 次交互，运行时可配置。

`window.time_window_summary` 同样只从插件启动后观察到的事实计算，默认覆盖最近 1800 秒。它由窗口末梢而不是网关生成：其中 `segments` 保留按时间顺序的焦点片段，`windows` 汇总每个窗口的专注秒数、占比和交互统计，`coverage_ratio` 明确可归因观察时长占完整时间窗的程度，`unattributed_seconds` 记录任务视图、锁屏等前台不可归因的时长。它不包含窗口标题、输入内容或用户意图推断。

## 最小神经中枢上下文

`src/context/spinal_hub.py` 是当前的参考组装器：它先让窗口插件采样，再通过网关入队，只有准入成功的消息才会被写入 `src/context/current_context.py` 的只读投影。上层可读取的快照包含 `states`、有限数量的 `recent_events` 与 `health`，不包含 `directive`、`proposal`、`result`，也拒绝 `sensitive` 和 `restricted` 载荷。

同一状态消息因 `collapse_key` 被队列合并时，快照必须以最新载荷覆盖旧状态；同一事件消息则更新已有事件而不重复追加。

对上层暴露的稳定读取契约为 `cyberspine.current_context@1`。`CurrentContextReader.read_json()` 和 `NeuralSpinalHub.read_current_context()` 都返回 `{ "schema", "context" }` 的 JSON 兼容副本。读取接口不得采样、入队、唤醒模型或执行动作；未来的 MCP 工具只能适配该接口，不能绕过它读取旧轮询中枢。

旧 PIP/NCP 文档仅保留历史讨论，其中独立消息类别和信封字段不应作为新代码依据。
