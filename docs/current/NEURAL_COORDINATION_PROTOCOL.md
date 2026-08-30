# 神经协调协议（NCP）v1.0

**状态：历史设计草案；已由《统一神经通信规范》取代**  
**协议版本：1.0**  
**适用对象：CyberSpine 神经中枢与顶层大脑之间的协调通信**

NCP（Neural Coordination Protocol）记录神经中枢如何把已过滤的本机上下文和需要升级处理的事件，可靠、安全地交给顶层大脑。其消息格式不再作为独立协议演进，将并入统一消息信封；它不绑定 Codex、Claude、Ollama、Windows、MCP 或任一传输方式。

PIP 负责“末梢神经如何接入神经中枢”；NCP 负责“神经中枢如何与顶层大脑协作”；MCP 是 NCP 可选的外部适配接口之一。

## 1. v1.0 范围

NCP v1.0 只定义五项能力：

1. **上下文读取**：顶层大脑读取当前结构化上下文。
2. **升级事件**：神经中枢生成值得上报的 `EscalationEvent`。
3. **订阅与投递**：顶层大脑或宿主可选择接收升级事件。
4. **确认与处置**：接收方确认、拒绝、延后或让事件过期。
5. **动作提议**：顶层大脑提出动作，但不拥有直接执行权限。

以下内容不属于 v1.0：模型推理协议、插件安装协议、跨设备同步、身份提供方、自动执行动作、强制唤醒模型。

## 2. 角色与安全边界

| 角色 | 标识 | 权限 |
| --- | --- | --- |
| 神经中枢 | `spinal_hub` | 聚合 PIP 信号、生成上下文和升级事件、持久化事件队列。 |
| 顶层大脑 | `top_level_brain` | 读取上下文、订阅升级事件、确认或提出动作。 |
| 宿主 | `host` | 承载顶层大脑，决定是否创建推理任务、展示通知或转交用户。 |
| 用户 | `user` | 最终决定是否允许唤醒和执行动作。 |

**核心规则：** NCP 的 `wake_request` 是“请求宿主注意”的事件，不是让中枢强制启动模型的远程命令。宿主必须显式协商该能力，并始终可受用户设置、静默时段和配额限制。

## 3. 能力协商

连接建立时，双方交换 `hello`，声明协议版本和能力。只允许使用共同协商的能力。

```json
{
  "protocol_version": "1.0",
  "kind": "hello",
  "source": "top_level_brain.codex",
  "body": {
    "role": "top_level_brain",
    "capabilities": {
      "context_read": true,
      "escalation_subscription": true,
      "wake_request": {
        "mode": "user_confirmed",
        "min_priority": "high",
        "max_per_hour": 3
      },
      "action_proposal": true
    }
  }
}
```

`wake_request.mode` 取值：

| 模式 | 含义 |
| --- | --- |
| `disabled` | 只允许下次读取时获取待处理事件。 |
| `user_confirmed` | 宿主通知用户；用户确认后才创建顶层大脑任务。 |
| `host_policy` | 宿主按自身策略决定是否创建受限任务；必须可审计。 |

神经中枢返回 `ready`，列出实际接受的能力、优先级阈值、配额和静默规则。未协商 `wake_request` 时，所有升级事件必须进入持久队列，等待后续读取。

## 4. 统一消息信封

所有 NCP 消息使用 UTF-8 JSON：

```json
{
  "protocol_version": "1.0",
  "message_id": "ncp_01J...",
  "timestamp": "2026-08-29T10:00:00Z",
  "kind": "escalation",
  "source": "spinal_hub",
  "target": "top_level_brain.codex",
  "correlation_id": null,
  "body": {},
  "extensions": {}
}
```

- `message_id`：全局唯一，用于去重。
- `timestamp`：ISO 8601 UTC 时间。
- `source` / `target`：稳定角色或实例 ID。
- `correlation_id`：对读取、投递、确认或动作提议的关联 ID。
- `extensions`：可选扩展；接收方必须忽略无法识别的字段。

## 5. 核心消息

| `kind` | 发送方 | 说明 |
| --- | --- | --- |
| `hello` / `ready` / `rejected` | 双方 | 生命周期、版本和能力协商。 |
| `context_request` / `context_response` | 顶层大脑 / 中枢 | 获取当前上下文或指定上下文快照。 |
| `escalation` | 中枢 | 创建或投递待升级事件。 |
| `subscription_request` / `subscription_ready` | 顶层大脑 / 中枢 | 声明订阅主题与投递策略。 |
| `acknowledgement` | 宿主或顶层大脑 | 确认、拒绝、延后或关闭事件。 |
| `action_proposal` / `action_decision` | 顶层大脑 / 中枢 | 提议动作及确认门控结果。 |
| `health` / `error` | 双方 | 健康状态和结构化错误。 |

## 6. 当前上下文

`context_response.body` 必须是脱敏后的只读快照：

```json
{
  "context_id": "ctx_01J...",
  "captured_at": "2026-08-29T10:00:00Z",
  "foreground": {
    "application": "Code.exe",
    "title": "CyberSpine"
  },
  "system": {
    "cpu_percent": 32.4,
    "memory_percent": 61.0,
    "network_status": "healthy"
  },
  "recent_signals": ["window.focus_changed"],
  "privacy": {
    "contains_sensitive_content": false,
    "redaction_applied": true
  }
}
```

原始剪贴板文本、密钥、文件内容、屏幕图像和未声明权限的数据不得默认进入上下文。

## 7. 升级事件与主动唤醒

升级事件必须先落入神经中枢的持久队列，再尝试投递。投递失败不丢失事件，也不得无限重试。

```json
{
  "event_id": "esc_01J...",
  "context_id": "ctx_01J...",
  "priority": "high",
  "reason": "当前工作区连续构建失败，且系统负载持续偏高",
  "suggested_action": "检查最新错误和资源占用",
  "requires_user_attention": true,
  "created_at": "2026-08-29T10:00:00Z",
  "expires_at": "2026-08-29T10:30:00Z"
}
```

事件状态：

```text
pending → delivered → acknowledged → resolved
   │          │             └→ deferred → pending
   │          └→ rejected
   └→ expired
```

- `pending`：所有事件的初始状态。
- `delivered`：已投递给同意订阅的宿主，但不代表模型已启动。
- `acknowledged`：宿主或顶层大脑已接收并将处理。
- `rejected`：用户或宿主拒绝处理；必须记录原因。
- `deferred`：延后到指定时间或下一次上下文读取。
- `expired`：超过有效期后不得再触发唤醒。

优先级为 `low`、`normal`、`high`、`critical`。`critical` 也不能绕过用户权限和宿主策略。

## 8. 动作提议与确认

顶层大脑只能发送 `action_proposal`：

```json
{
  "proposal_id": "act_01J...",
  "context_id": "ctx_01J...",
  "action": "workspace.open_in_editor",
  "parameters": {"path": "C:\\Projects\\CyberSpine"},
  "risk": "requires_confirmation",
  "reason": "用户正在该工作区中处理构建错误"
}
```

中枢的确认门控返回 `action_decision`。只有用户确认、权限满足且执行器允许时，动作才可执行。NCP 不定义执行器内部实现。

## 9. 传输与 MCP 映射

NCP 语义独立于传输。v1.0 的参考实现可使用本地 JSON Lines、持久事件队列和轮询；未来可增加 HTTP、WebSocket 或消息总线适配器。

对于仅支持被动 MCP 工具调用的宿主：

| NCP 能力 | MCP 适配 |
| --- | --- |
| `context_request` | `cyberspine_get_current_context` |
| 查询待处理事件 | `cyberspine_list_escalations` |
| `acknowledgement` | `cyberspine_acknowledge_escalation` |
| `action_proposal` | `cyberspine_propose_action` |

对于支持持久订阅或官方唤醒能力的宿主，新增 `WakeupAdapter`，将 `escalation` 映射为对应宿主的通知或任务创建请求。该适配器不得改变 NCP 事件语义。

## 10. 兼容与治理

1. `1.x` 只允许增加可选字段和可协商能力。
2. 改变消息语义、删除字段或改变安全规则必须升级主版本。
3. 任何新能力必须在 `capabilities` 中声明，并有 JSON Schema、错误码和兼容测试。
4. 协议提案必须包含：问题、动机、隐私影响、失败行为、示例、迁移计划和参考实现。
5. 规范、Schema、测试夹具和参考实现必须同仓维护；文档不是唯一事实来源。

## 11. v1.0 参考实现顺序

1. `context_request` / `context_response`。
2. 持久 `EscalationEvent` 队列与 `list_escalations`。
3. `acknowledgement` 和事件状态机。
4. 被动 MCP 映射。
5. 第一个宿主专属 `WakeupAdapter`。

只有前四项稳定后，才进入真实主动唤醒实验。
