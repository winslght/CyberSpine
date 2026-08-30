# 开发与测试

所有新开发先遵守 [项目方向与主线开发章程](PROJECT_DIRECTION.md)：旧 Demo 是行为参考，新功能只进入统一消息主干。

## 环境

推荐 Python 3.14，并使用项目根目录的 `.venv` 虚拟环境：

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install pytest pytest-asyncio pytest-mock pydantic psutil
```

完整 MCP 依赖仍需在其 API 范围稳定后单独锁定；不要把未锁定的最新依赖当作 Demo 的可靠基线。

## 采用边界：复用与自建

CyberSpine 不以“自己实现所有底层能力”为目标。成熟且通用的基础设施应优先采用或封装，项目只维护其真正的产品语义。

| 类别 | 决策 | 当前含义 |
| --- | --- | --- |
| MCP 传输与生命周期 | 采用 | 后续以成熟 MCP Python SDK 替换手写 JSON-RPC/stdio 循环；保留 CyberSpine 的业务工具和安全边界。|
| Ollama 调用 | 采用 | 后续以官方客户端替换裸 HTTP；保留模型选择、提示词、超时和规则降级策略。|
| Windows、文件和硬件采集 | 封装 | 优先使用稳定系统绑定或现有监控后端；不扩大为自研 OS/硬件监控平台。|
| GUI 自动化 | 可替换后端 | 未来接入成熟自动化能力，不自建完整桌面 AgentOS。|
| 插件发现与生命周期 | 采用 | 开放第三方插件前评估成熟插件框架；当前只实现协议和参考插件。|
| 统一消息、上下文隐私、调节与确认门控 | 自建 | 这是 CyberSpine 的核心语义，必须保持可审计和可测试。|

新增依赖前必须写明：替代的自研责任、封装边界、许可证、安全影响、离线降级方案和移除成本。不得让大型上游项目侵入统一消息主干。

## 常用命令

```powershell
# 最小闭环演练
python scripts/demo_minimal_loop.py

# 自动化测试
python -m pytest

# 启动实验性驾驶舱
scripts\start_cockpit.bat

# 观察窗口感知：默认每 10 秒低频校准、终端每 5 秒分层刷新，并写入 runtime/logs/window_activity.jsonl
python scripts\monitor_window_activity.py

# 临时提高校准频率；--no-clear 可保留每次快照。不要将此模式作为常驻运行方式。
python scripts\monitor_window_activity.py --interval 3 --display-interval 5

# 只运行 30 秒，适合快速验收
python scripts\monitor_window_activity.py --duration 30

# 高频交互诊断：显式启用全局输入钩子；仅短时测试，不作为默认常驻能力
python scripts\monitor_window_activity.py --duration 60 --input-monitor --activity-window 30 --high-frequency-per-minute 3 --minimum-interactions 3

# 快速验证时间窗汇总与系统过渡态（60 秒观察窗）
python scripts\monitor_window_activity.py --duration 90 --focus-window 60

# 汇总窗口感知日志：焦点变化、高频交互窗口、最近窗口目录
python scripts\analyze_window_activity_log.py

# 实时查看原始滚动 JSONL
scripts\view_window_activity_logs.ps1
```

窗口感知观察器默认只低频读取应用、PID、窗口布局和前台驻留；全局输入钩子仅在 `--input-monitor` 诊断模式中短时启用。它根本不读取窗口标题，也不会记录输入文本、剪贴板、鼠标坐标或屏幕图像。日志达到 5 MB 时会按时间归档，并开始新的 JSONL 文件。

## 测试分层

- Demo 核心测试：验证当前上下文、MCP 读取、确认门控和单一动作。
- 实验测试：硬件遥测、模型、驾驶舱、插件与多传感器组合。

在整理完成前，实验测试失败不应掩盖或阻塞 Demo 核心闭环；但每个失败都必须被记录和分类。
