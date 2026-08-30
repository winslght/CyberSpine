# CyberSpine 独立后台神经中枢守护进程开发规划方案 (Daemon Architecture)

**文档编号**：DOC-ARCH-003  
**状态**：规划审阅中 (Planning Review)  
**目标**：将 CyberSpine 中枢神经系统（小而快的感觉哨兵 + 双节奏起搏器 + 小脑简报打包器）工程化封装为一个**可长期独立稳定运行于 Windows 后台的轻量级低功耗守护进程 (Autonomous Background Daemon)**，并通过标准进程间通信 (IPC/HTTP/WebSocket) 与前额叶高级大脑解耦协同。

---

## 1. 为什么神经中枢必须独立为后台守护程序？

在仿生全脑区架构中：
1. **中枢是“生物体的心跳与自主神经系统”**：即使高级大脑（如 LLM / IDE 插件 / 桌面 UI）处于休眠或未启动状态，宿主机的感知系统依然必须 7x24 小时保持微弱心跳（0% CPU 稳态）；
2. **进程隔离与故障解耦**：高级大脑思考崩溃或网络卡顿时，绝不能导致底层的硬件感知与系统监听中断；
3. **即插即用的脑机总线 (Brain-Spine Bus)**：任何前台应用（VSCode 插件、CLI 工具、Electron 伴侣悬浮窗、甚至是云端智能体）都可以随时连接中枢守护进程，订阅实时《1分钟世界状态简报》或下发控制指令。

---

## 2. 神经中枢守护进程整体架构设计

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│              CyberSpine 独立后台中枢守护进程 (cyberspine_daemon.py)              │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ 进程管理与生命周期 (Process Lifecycle & Mutex Lock)                      │   │
│   │ - Windows 命名互斥锁 (Named Mutex / PID Lock) 保证单例运行              │   │
│   │ - 优雅停机信号捕获 (SIGINT / SIGTERM / Windows Console Event)            │   │
│   │ - 日志轮转写入 (03_本地日志与监控_logs/daemon.log)                      │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │ 神经起搏主引擎 (Dual-Cadence Nervous Clock Loop)                         │   │
│   │                                                                         │   │
│   │  [微观心跳循环 (5s ~ 10s 弹性)] ──> 汇聚 8 大末梢 ──> 写入 60s 滑动窗口   │   │
│   │                                                                         │   │
│   │  [宏观小脑打包 (每 60s 等齐)]   ──> 生成《1分钟世界简报》──> 广播至通信总线 │   │
│   │                                                                         │   │
│   │  [即时紧急中断 (Emergency Fast-Path)] ──> U 盘插入/程序崩溃 ──> 毫秒级推送│   │
│   └──────────────────────────────────┬──────────────────────────────────────┘   │
│                                      │                                          │
│   ┌──────────────────────────────────┴──────────────────────────────────────┐   │
│   │ 脑-脊神经通信服务 (Brain-Spine IPC / Local Service Engine)               │   │
│   │ - 轻量 HTTP REST / WebSocket 接口 (默认 localhost:8970)                 │   │
│   │ - GET  /spine/status          -> 获取当前中枢运行指标、PID、Uptime      │   │
│   │ - GET  /spine/briefing/latest -> 获取最新的《1分钟世界状态简报》        │   │
│   │ - WS   /spine/stream          -> 实时订阅电信号与世界简报流            │   │
│   │ - POST /spine/feedback        -> 接收高级大脑回传的下行抑制递质指令     │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │ 进程间解耦通信 (IPC / WebSocket)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    前额叶高级大脑生态 (Master Cortex Ecosystem)                 │
│                                                                                 │
│  [终端 CLI 交互工具]   [VSCode 智能伴侣插件]   [桌面悬浮卡片]   [云端 Agent]    │
│  (订阅世界简报)       (3W 深度思考)          (温和人机交互)   (回传下行抑制)  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心功能模块详细设计

### 模块 1: 守护进程核心控制器 (`src/daemon/spine_daemon.py`)
* **单例保护与互斥锁**：基于系统级互斥锁（`cyberspine_daemon.lock`），确保后台仅有一个神经中枢实例在运行；
* **低能耗守护主循环**：采用 `threading.Event` 与极轻量休眠，实现无事件触发时 **0% CPU 占用，内存消耗 $\le 30\text{MB}$**；
* **健康心跳日志输出**：每小时输出一次生命体征统计，自动保存到 `03_本地日志与监控_logs/daemon.log`。

---

### 模块 2: 极速小脑简报生成引擎 (`src/spinal_core/cerebellar_gate.py`)
* **设计原则**：**小而快，不做重度复杂思考**；
* **核心动作**：
  * 对过去 1 分钟内的 12 次微观心跳数据（每 5 秒一次）进行时间轴聚合；
  * 提取出高保真的 5 维宏观状态：
    1. **工作重心变化**（如：在 VSCode 停顿 45 秒，切换终端 15 秒）；
    2. **负载压力走势**（如：CPU 平均 12%，出现 1 次瞬间编译峰值 88%）；
    3. **物理环境事件**（如：无新外设接入，网络时延稳定在 12ms）；
    4. **异常与稳定性**（如：0 崩溃事件）；
    5. **紧急中断标记**（`is_urgent: bool`）。

---

### 模块 3: 脑-脊神经轻量 IPC 服务 (`src/daemon/ipc_service.py`)
* 使用 Python 原生轻量无外部重依赖的 HTTP/Socket 服务（支持 0 额外第三方重型框架，开箱即用）；
* **开放端点契约**：
  * `GET /api/v1/health`：返回中枢健康度（`{"status": "ALIVE", "uptime_sec": 3600, "heartbeats": 720}`）；
  * `GET /api/v1/briefing/latest`：返回最新生成的 1 分钟世界简报 JSON；
  * `POST /api/v1/efferent/inhibit`：接收大脑回传的抑制指令（`{"duration_sec": 300, "device_id": "..."}`）。

---

### 模块 4: Windows 运维与控制脚本 (`04_研发工具与脚本_tools/`)
* **`start_daemon.bat`**：无窗口/后台启动中枢守护进程；
* **`stop_daemon.bat`**：安全向守护进程发送停止信号并优雅退出；
* **`status_daemon.bat`**：查看后台中枢当前的 PID、运行时间、最新心跳与简报状态；
* **`run_daemon_foreground.bat`**：前台带彩色日志窗口运行（方便研发调试）。

---

## 4. 实施阶段与测试交付规划

| 实施阶段 | 核心任务 | 涉及代码模块 | 独立测试文件 |
| :--- | :--- | :--- | :--- |
| **Phase 1** | 数据模型扩展与小脑极速简报引擎 | `src/models/somatic_signals.py`<br>`src/spinal_core/cerebellar_gate.py` | `tests/test_cerebellar_fast_gate.py` |
| **Phase 2** | 双节奏神经起搏器与事件循环 | `src/pacing/dual_cadence_clock.py` | `tests/test_dual_cadence_clock.py` |
| **Phase 3** | 后台守护进程与单例互斥锁 | `src/daemon/spine_daemon.py` | `tests/test_spine_daemon_lifecycle.py` |
| **Phase 4** | 脑-脊神经 IPC 服务与大脑对接 | `src/daemon/ipc_service.py`<br>`src/cortex/master_cortex.py` | `tests/test_brain_spine_ipc.py` |
| **Phase 5** | Windows 运维脚本与实机全链路集成 | `cyberspine_daemon.py`<br>`04_...tools/*.bat`<br>`demo_minimal_loop.py` | `tests/test_daemon_e2e_integration.py` |
