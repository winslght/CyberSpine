# CyberSpine

CyberSpine 是一个面向 Windows 的本地感知实验 Demo：它把当前桌面工作状态整理为结构化上下文，供上层 AI Agent 通过 MCP 读取；任何桌面动作都必须经过用户确认。

## 当前 Demo 的唯一闭环

```text
Windows 状态采集 → 结构化上下文 → MCP 工具读取 → 用户确认 → 有限桌面动作
```

当前 Demo 关注的输入：

- 前台应用与窗口标题；
- CPU、内存和网络等基础系统状态；
- 存储与当前工作区的浅层信息；
- 剪贴板内容类型（不将原始敏感内容作为上下文输出）。

其目的不是自动替用户操作电脑，而是验证“本地系统感知能否安全地为上层 Agent 提供有用上下文”。

## 快速开始

使用项目独立环境：

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/demo_minimal_loop.py
```

启动现有驾驶舱（实验性界面）：

```cmd
scripts\start_cockpit.bat
```

运行测试：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest
```

> 当前测试套件仍在收敛中。以 `docs/current/DEMO_SCOPE.md` 的验收标准为准，不将旧测试的全绿状态视为发布承诺。

## 项目结构

```text
src/             核心实现：感知、上下文、MCP、动作与应用
tests/           自动化测试与端到端实验
scripts/         Demo、开发和运维脚本
docs/            当前说明、架构决策、参考资料与历史归档
plugins/         可插拔扩展与示例
vendor/          随附的外部工具，例如 AIDA64
runtime/         本机数据与日志（不纳入 Git）
```

## 文档

- [项目方向与主线开发章程](docs/current/PROJECT_DIRECTION.md)
- [Demo 范围与验收标准](docs/current/DEMO_SCOPE.md)
- [开发与测试说明](docs/current/DEVELOPMENT.md)
- [文档导航](docs/INDEX.md)
- [历史资料归档](docs/archive/legacy_2026-08-29/)

## 后续方向

在最小闭环稳定前，不扩展插件商店、复杂模型管理或多页面驾驶舱。每一个新能力都必须接入同一条“感知 → 上下文 → 确认 → 动作”链路，并配有可复现测试。
