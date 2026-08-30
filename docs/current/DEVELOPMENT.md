# 开发与测试

所有新开发先遵守 [项目方向与主线开发章程](PROJECT_DIRECTION.md)：旧系统是已完成概念验证（PoC），不是待完善的生产主线；新功能只进入统一消息主干。旧代码只能作为兼容适配器或行为验收参考，不能作为新能力的直接落点。

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

# 观察窗口感知：默认由 Windows 事件冲动驱动、每 60 秒低频校准；终端每 5 秒分层刷新，并写入 runtime/logs/window_activity.jsonl
python scripts\monitor_window_activity.py

# 临时提高校准频率；--no-clear 可保留每次快照。不要将此模式作为常驻运行方式。
python scripts\monitor_window_activity.py --interval 3 --display-interval 5

# 只运行 30 秒，适合快速验收
python scripts\monitor_window_activity.py --duration 30

# 直接运行 Python 脚本时显式启用脱敏全局交互计数
python scripts\monitor_window_activity.py --duration 60 --input-monitor --activity-window 30 --high-frequency-per-minute 3 --minimum-interactions 3

# 快速验证时间窗汇总与系统过渡态（60 秒观察窗）
python scripts\monitor_window_activity.py --duration 90 --focus-window 60

# 汇总窗口感知日志：焦点变化、高频交互窗口、最近窗口目录
python scripts\analyze_window_activity_log.py

# 实时查看原始滚动 JSONL
scripts\view_window_activity_logs.ps1
```

窗口感知观察器启动时建立一次基线，之后由 Windows 窗口事件触发；连续事件会在 200ms 内合并，只有形成一次末梢冲动后才读取窗口事实。每 60 秒仍会做一次完整目录校准，以处理漏事件、桌面切换或系统外壳重启。单次拿不到前台句柄时，先显示“前台待确认”和最后确认窗口；默认 1 秒后仍未恢复则标为“前台未解析”并停止焦点归因。它明确表示末梢暂时没有可靠事实，不会伪装成“用户无前台”或“系统过渡态”；未来只有接入锁屏或安全桌面等明确系统证据，才会输出真正不可归因。终端每 5 秒更新的驻留时长仅来自本地单调时钟和已知窗口事实，不会读取 Windows、不会写入日志、不会伪装成系统事件。官方 `start_window_monitor.bat` 会显式启用脱敏全局交互计数，可追加 `--no-input-monitor` 关闭；直接运行 Python 脚本时仍需传入 `--input-monitor`。该计数只记录按键、点击与滚轮发生的时间点并归因到前台窗口，不读取键值，也不会记录输入文本、剪贴板、鼠标坐标或屏幕图像。输入法系统表面及与其同步变化的无标题 Shell 伴生表面仍更新内部几何基线，但不会触发用户窗口几何神经事件。日志达到 5 MB 时会按时间归档，并开始新的 JSONL 文件。

## 测试分层

- Demo 核心测试：验证当前上下文、MCP 读取、确认门控和单一动作。
- 实验测试：硬件遥测、模型、驾驶舱、插件与多传感器组合。

在整理完成前，实验测试失败不应掩盖或阻塞 Demo 核心闭环；但每个失败都必须被记录和分类。
