# CyberSpine 更新日志 (Changelog)

所有重要的架构变更与功能发布均记录在此文件中。

---

## [0.3.0] - 2026-08-29
### Added
- **AIDA64 绿色便携共生模式**：新增 `tools/aida64/` 预置配置文件与静默托管器 (`src/perceptors/hardware/aida64_daemon.py`)。
- **全维硬件生理体征末梢 (`nerve.hardware.somatic_telemetry`)**：支持微秒级读取 CPU 全核温度、风扇转速 RPM、GPU 功耗与热点温度、NVMe 固态硬盘温度。
- **皮肤动量触觉末梢 (`nerve.system.input_kinetics`)**：支持毫秒级物理空闲时间差与心流阶段（深度沉思、稳定编码、离线）判定。
- **瞬时工作记忆剪贴板末梢 (`nerve.system.clipboard_semantics`)**：支持代码、JSON、URL、报错堆栈的浅层语法特征嗅探与脱敏预览。
- **开发日志留痕库**：新增 `docs/tracking/DEV_LOG.md` 永久追踪工程决策与实机基准。

### Changed
- **SomaticPerceptorHub 升级**：全身神经通道由 8 个扩充至 11 大核心感官通道。
- **MCP 服务端双流隔离架构**：重构 `src/mcp/server.py` 保证 Stdio JSON-RPC 2.0 传输 100% 纯净。
- **大模型 4 维世界感知简报**：端侧 Qwen2.5 升级为 200 字 4 维结构（电脑在干嘛、用户在做什么、注意力焦点、高级大脑介入裁决）。

### Fixed
- 修复 64 位 Windows 下剪贴板 `ctypes` 指针截断导致的内存访问崩溃问题。
- 修复 MCP 服务端标准输出流被起搏器启动日志污染导致客户端解析崩溃的问题。
- 修复 Ollama 端侧模型后台环境变量缺失导致的 RTX 4060 GPU 显存未占用问题。

---

## [0.2.0] - 2026-08-28
### Added
- 原生 Model Context Protocol (MCP) JSON-RPC 2.0 服务端模块 (`src/mcp/`)。
- 6 大 MCP 工具接口（`cyberspine_get_world_briefing` 等）。
- 5.0s 物理自主生命起搏器守护线程 (`RealAutonomousPacemaker`)。

---

## [0.1.0] - 2026-08-28
### Added
- CyberSpine 初始仓库架构建立（单一纯英文 Git 根目录）。
- WinUI 3 仿生神经驾驶舱桌面客户端。
- 7 大基础物理感官与安全三定律运动神经元执行器。
