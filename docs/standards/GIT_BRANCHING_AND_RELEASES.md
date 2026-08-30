# 分支开发规范、提交指南与版本递归准则 (Git Branching & Release Policy)

**文档编号**：DOC-DEV-003  
**状态**：团队工程基准 (Approved)  
**维护者**：CyberSpine 架构委员会  

---

## 1. Git 分支管理拓扑模型 (Branching Model)

CyberSpine 采用标准的 **主干保护 + 特性分支驱动 (Feature-Driven Git Flow)** 模型：

```
  main (生产稳定受保护分支) ───●──────────────────● (v3.2.0 Release Tag)
                              ▲                  ▲
                              │                  │ Pull Request (100% Tests Pass)
  develop (集成联调分支) ────●───●──────●───────●
                              │   ▲      │       ▲
                              ▼   │      ▼       │
  feature/component-1-io ─────●───●      │       │
                                         ▼       │
  feature/component-2-pacing ────────────●───────●
```

### 1.1 分支命名规范
| 分支类型 | 命名格式 | 示例 | 说明 |
| :--- | :--- | :--- | :--- |
| **生产分支** | `main` | `main` | 仅存放已通过全量回归测试、可随时对外发布的稳定版本 |
| **集成开发** | `develop` | `develop` | 日常各组件联调与聚合分支 |
| **特性开发** | `feature/<name>` | `feature/component-2-pacing` | 新增组件、新算法或核心子系统研发 |
| **缺陷修复** | `fix/<issue-id>-<desc>` | `fix/win-gbk-encoding` | 紧急或日常 Bug 修复分支 |
| **架构与提案**| `rfc/<topic>` | `rfc/shared-memory-shm` | 架构白皮书、新协议 RFC 讨论分支 |
| **外部插件** | `plugin/<nerve-id>` | `plugin/nerve-vision-screen` | 外部独立感官插件开发分支 |

---

## 2. 规范化提交信息 (Conventional Commits)

每次 Git Commit 必须遵循规范化格式，便于自动化生成更新日志（Changelog）：

```
<type>(<scope>): <subject>

[optional body]
[optional footer]
```

### 2.1 提交类型 (Type)
* **`feat`**：新增脑区组件或核心特性（如 `feat(io): add device fingerprint sha256 registration`）；
* **`fix`**：修复缺陷与异常（如 `fix(tests): prevent gbk encoding crash on windows console`）；
* **`docs`**：仅更新文档、白皮书或架构规范（如 `docs(bnp): add bnp v1.0 protocol specification`）；
* **`test`**：新增或重构测试套件（如 `test(component-1): add 4 standalone unit tests`）；
* **`refactor`**：既不增加特性也不修复 Bug 的代码重构；
* **`perf`**：提升系统性能、降低能耗的改动；
* **`chore`**：依赖配置、构建脚本更新。

---

## 3. 语义化版本号递归准则 (Semantic Versioning 2.0.0)

CyberSpine 版本号遵循 **`v<MAJOR>.<MINOR>.<PATCH>`** 规范：

```
                    v3.2.0
                     │ │ │
     主版本号 (MAJOR) ┘ │ └ 补丁版本号 (PATCH)
      次版本号 (MINOR) ──┘
```

### 3.1 升级判定规则
1. **MAJOR (主版本号递增，如 v3.0 ➔ v4.0)**：
   * 发生了不向后兼容的重大架构重构；
   * 通用跨语言神经协议（BNP）发生破坏性版本迭代；
   * 主脑与脊髓的通信契约发生重大变更。
2. **MINOR (次版本号递增，如 v3.1 ➔ v3.2)**：
   * 完成了一个核心脑区组件的研发与测试通过（如组件 1 落地）；
   * 新增了重要的官方感官探针（如高帧率视觉差分探针上线）；
   * 向后兼容地扩展了 Pydantic 信号契约。
3. **PATCH (补丁版本号递增，如 v3.2.0 ➔ v3.2.1)**：
   * 修复跨平台兼容性 Bug（如 Windows 编码、时区告警）；
   * 细微的代码安全优化与文档订正。

---

## 4. Pull Request 审查与合并检查清单 (PR Checklist)

在发起向 `develop` 或 `main` 的 PR 之前，必须逐一确认：
- [ ] 代码严格遵循 `docs/CODING_STANDARDS.md`（强类型注解、Pydantic V2、UTC 时区）；
- [ ] 浅层探测深度 $\le 2$，单次耗时 $\le 5\text{ms}$，严禁暴力全盘遍历；
- [ ] 对应模块的独立单元测试（`tests/`）100% 执行通过；
- [ ] 关联的 `docs/` 架构与技术文档已完成同步更新；
- [ ] 提交历史干净整洁，无多余调试杂质。
