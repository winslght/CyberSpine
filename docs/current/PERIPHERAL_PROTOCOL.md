# 末梢互连协议（PIP）v1.0

**状态：历史设计草案；已由《统一神经通信规范》取代**  
**适用对象：所有 CyberSpine 末梢神经插件与神经中枢适配器**

PIP（Peripheral Interconnect Protocol）记录末梢神经即插即用所需的能力声明、生命周期和隔离规则。其消息格式不再作为独立协议演进，将并入统一消息信封；插件之间不直接依赖，任何单个插件失败不得影响神经中枢或其他插件。

## 1. 设计原则

1. **统一插头**：所有插件使用同一份清单和消息信封。
2. **能力协商**：中枢根据插件声明的协议版本、能力和权限决定是否启用。
3. **即插即用**：安装、启用、停用、升级、卸载均不要求修改其他插件。
4. **故障隔离**：插件异常只改变自身状态；中枢记录错误并继续运行。
5. **最小权限**：插件只申请完成自身能力所需的权限；默认只上传脱敏元数据。
6. **向前兼容**：中枢必须忽略未知字段、未知能力和未知扩展，不得因此崩溃。

## 2. 插件清单

每个插件根目录必须提供 `manifest.json`：

```json
{
  "plugin_id": "peripheral.window.activity",
  "display_name": "窗口感知",
  "version": "1.0.0",
  "protocol_version": "1.0",
  "entrypoint": "main.py",
  "capabilities": ["window.focus_changed"],
  "permissions": ["window.metadata"],
  "signal_schemas": ["window.focus_changed@1"],
  "health_check": {"interval_seconds": 30}
}
```

### 必填字段

| 字段 | 规则 |
| --- | --- |
| `plugin_id` | 使用 `peripheral.<domain>.<capability>`，全局唯一。 |
| `display_name` | 面向用户的职责名称，例如“窗口感知”。 |
| `version` | 插件自身的 SemVer 版本。 |
| `protocol_version` | 当前必须为 `1.0`。 |
| `entrypoint` | 插件启动入口。 |
| `capabilities` | 可产生或可处理的能力列表。 |
| `permissions` | 所需系统权限与数据范围。 |

## 3. 统一消息信封

所有 PIP 消息使用 UTF-8 JSON；传输层在 v1.0 使用逐行 JSON（JSON Lines）。未来可增加本地套接字或 WebSocket 传输，但不得改变消息语义。

```json
{
  "protocol_version": "1.0",
  "message_id": "msg_01J...",
  "timestamp": "2026-08-29T10:00:00Z",
  "kind": "signal",
  "source": "peripheral.window.activity",
  "correlation_id": null,
  "body": {},
  "extensions": {}
}
```

| 字段 | 含义 |
| --- | --- |
| `protocol_version` | PIP 协议版本。 |
| `message_id` | 本条消息唯一 ID。 |
| `timestamp` | ISO 8601 UTC 时间。 |
| `kind` | 消息类别。 |
| `source` | 插件 ID 或 `spinal_hub`。 |
| `correlation_id` | 对请求、命令或错误的关联 ID；独立信号为 `null`。 |
| `body` | 该消息类别的标准载荷。 |
| `extensions` | 可选扩展字段；接收方必须忽略无法识别的内容。 |

## 4. 消息类别与生命周期

| `kind` | 发送方 | 用途 |
| --- | --- | --- |
| `hello` | 插件 | 插件启动并提交清单摘要。 |
| `ready` | 神经中枢 | 接受插件、返回允许的能力与配置。 |
| `rejected` | 神经中枢 | 拒绝连接，说明不兼容版本或未获权限。 |
| `signal` | 插件 | 上报神经信号。 |
| `health` | 插件 | 心跳和自身健康状态。 |
| `command` | 神经中枢 | `start`、`pause`、`resume`、`stop`、`configure`。 |
| `result` | 插件 | 对命令的结构化执行结果。 |
| `error` | 双方 | 可恢复或不可恢复错误。 |
| `goodbye` | 双方 | 正常断开。 |

插件生命周期：

```text
已安装 → hello → ready → 运行中
                     ├─ pause / resume
                     ├─ stop → goodbye → 已停用
                     └─ error → 已隔离
```

中枢对 `stop` 的默认等待时间为 5 秒；超时后标记为“已隔离”，不得阻塞其他插件或主程序退出。

## 5. 神经信号

`signal` 消息的 `body` 必须包含：

```json
{
  "type": "window.focus_changed",
  "schema": "window.focus_changed@1",
  "severity": "info",
  "privacy": {
    "classification": "metadata_only",
    "redacted": true
  },
  "payload": {
    "application": "Code.exe",
    "title": "CyberSpine"
  }
}
```

- `type` 采用 `<domain>.<event>`。
- `schema` 明确此载荷版本。
- `severity` 为 `debug`、`info`、`warning`、`error`。
- `privacy.classification` 为 `public`、`metadata_only`、`sensitive` 或 `restricted`。
- `payload` 只放该信号必要字段；原始敏感内容必须在插件内脱敏或摘要化。

## 6. 兼容与升级

1. 协议 `1.x` 中只允许新增可选字段、能力或消息类型。
2. 删除字段、改变既有字段语义或改变安全规则必须升级主版本。
3. 神经中枢必须拒绝更高主版本的插件，并返回 `rejected`。
4. 新增的插件能力不要求旧中枢理解；未知信号可被记录或丢弃。
5. 插件升级必须视作独立插件重连：旧实例停止，新实例重新 `hello`。

## 7. 安全边界

- 末梢神经只能上报信号和响应中枢命令，不能直接调用执行器。
- 末梢神经不得读取未在 `permissions` 中声明的数据源。
- 中枢向顶层大脑提供的上下文必须按隐私级别过滤。
- 顶层大脑的动作只能通过“提议 → 用户确认 → 执行器”的独立链路，不能经 PIP 直接执行。

## 8. 首个参考实现

`peripheral.window.activity`（窗口感知）是 PIP v1.0 的参考插件。后续键盘与鼠标感知、系统状态感知、网络状态感知、存储设备感知均必须复用本协议，而不是引入专用通信方式。
