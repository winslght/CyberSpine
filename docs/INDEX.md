# CyberSpine 文档导航

## 当前有效文档

- [Demo 范围与验收标准](current/DEMO_SCOPE.md)：唯一的当前产品范围与完成定义。
- [项目方向与主线开发章程](current/PROJECT_DIRECTION.md)：原型机到新主干的目标、模块边界、阶段交付与变更准入规则。
- [人格层、记忆与本机高上下文信任模式](current/MEMORY_AND_PERSONA.md)：内部人格代号、三层记忆与 Turbo 的安全设计约束。
- [开发与测试说明](current/DEVELOPMENT.md)：本地环境、启动方式和测试分层。
- [当前开发规划](current/DEVELOPMENT_PLAN.md)：统一消息主干、仿生调节、MCP 适配和唤醒能力的实施顺序。
- [统一神经通信规范](current/UNIFIED_NEURAL_COMMUNICATION.md)：当前唯一有效的消息信封、网关准入与窗口感知参考实现。
- [命名规范](current/NAMING.md)：产品、插件、信号、MCP 与代码的统一命名规则。
- [末梢互连草案](current/PERIPHERAL_PROTOCOL.md)：历史设计输入，已由统一规范取代。
- [中枢协调草案](current/NEURAL_COORDINATION_PROTOCOL.md)：历史设计输入，已由统一规范取代。
- [目标工程架构](architecture/TARGET_ARCHITECTURE.md)：长期目录边界与渐进迁移规则。
- [历史归档](archive/legacy_2026-08-29/)：早期平台化设计、重复顶层文档与旧路线图，仅供参考，不代表当前承诺。

**文档判定规则：** `current/` 与 `architecture/TARGET_ARCHITECTURE.md` 描述正式工程主线；其余 `architecture/`、`vision/` 和 `tracking/` 材料大多记录早期 PoC 的愿景、方案或历史事实，不能据此新增正式功能。旧代码与旧文档都不是“待继续完善的主线”。

## 保留的专题资料

- `architecture/`：除 `TARGET_ARCHITECTURE.md` 外，均为 PoC 期间的探索方案或历史设计输入。
- `vision/`：PoC 愿景和外部项目调研，不是功能规格。
- `standards/`：编码、测试、流程与版本管理规范。
- `tracking/`：历史研发日志、缺陷记录和 PoC 路线图，不是当前排期。

这些资料不会驱动当前 Demo 的实现；若其内容与 `current/` 下的文档冲突，以 `current/` 为准。
