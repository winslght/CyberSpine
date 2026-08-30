# CyberSpine 目标工程架构

本文件定义项目的长期落位规则。现有代码不因目录设计而被一次性重写；每次开发只将触及的模块迁入对应边界，并同时迁移测试。

## 仓库顶层

```text
docs/       当前文档、架构决策、参考资料和历史归档
src/        产品代码
tests/      单元、集成与端到端测试
scripts/    Demo、开发与运维入口
plugins/    扩展协议和插件示例
vendor/     随附的第三方工具
runtime/    本机数据、日志和缓存，默认不纳入 Git
```

`.git`、`.github`、`.obsidian`、`.venv` 是隐藏的版本、自动化、知识库和本机环境元数据，不属于产品代码结构。

## 目标源码边界

```text
src/
├─ core/          信号契约、网关、队列、准入与领域规则
├─ sensing/       Windows/硬件感知和末梢内可验证的初步事实整合
├─ context/       经网关投影的事实读取、跨末梢上下文与本地推理输入
├─ actions/       经过确认的受控动作
├─ adapters/      Windows、MCP、模型、WebView 等外部接口
├─ apps/          CLI Demo、驾驶舱等应用入口
└─ experimental/  未进入 Demo 主闭环的探索
```

当前的 `perceptors/`、`pacing/`、`spinal_core/`、`cortex/`、`actuators/`、`mcp/` 与 `app/` 是迁移中的实现分组。新功能必须按目标边界新增；旧模块仅在被修改时连同测试渐进迁移。

## 依赖方向

```text
apps → adapters → context / actions / sensing → core
plugins → adapters / core
experimental → 不可反向依赖 apps
```

`core` 不依赖 Windows、MCP、Ollama 或 UI；`runtime` 只由适配器或应用写入，不能承载业务规则。神经中枢与顶层大脑的协调遵循 [`../current/UNIFIED_NEURAL_COMMUNICATION.md`](../current/UNIFIED_NEURAL_COMMUNICATION.md)。

组件、插件、信号和 MCP 的具体命名遵循 [`../current/NAMING.md`](../current/NAMING.md)。

## 四层功能边界

```text
神经末梢（sensing / plugins）
  → 中枢网关（core）
  → 神经中枢（context + 本地推理适配器）
  → 顶级大脑（MCP/对话适配器）
```

神经末梢可对自身感知源进行初步整合，例如把原始窗口焦点变化整理为焦点片段、专注占比和切换统计；其输出仍必须是可追溯事实。中枢网关只保障多源信号的可靠准入、整理和转交，不承担感知业务统计或意图推理。神经中枢才可基于多种事实产生带证据、置信度和不确定性的假设；顶级大脑只负责向用户表达建议与提出动作，不能绕过确认门控。

## 迁移规则

1. 不进行仅为“好看”的跨模块搬迁。
2. 每次迁移一个能力时，同时迁移其直接测试和路径引用。
3. 对外行为不变时，迁移提交不夹带功能修改。
4. 新建功能必须有归属、隐私边界和测试层级；无法归类的先放入 `experimental/`。
5. Demo 的唯一主链始终是：感知 → 上下文 → MCP 读取 → 用户确认 → 有限动作。
