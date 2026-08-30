# 通用跨语言神经末梢协议规范 (Biomimetic Nerve Protocol - BNP v1.0 Spec)

> **历史 PoC 协议草案，已被统一消息规范取代。** 本文用于理解早期探索，不得据此实现新插件、传输层或协议兼容。当前唯一有效的内部消息契约见 [`../current/UNIFIED_NEURAL_COMMUNICATION.md`](../current/UNIFIED_NEURAL_COMMUNICATION.md)。

**文档编号**：DOC-SPEC-001  
**协议版本**：BNP v1.0.0  
**状态**：核心协议定稿 (Approved Specification)  
**维护者**：CyberSpine 协议工作组  

---

## 1. 协议概述与设计哲学

**Biomimetic Nerve Protocol (BNP)** 是 CyberSpine 针对桌面具身智能末梢感官制定的**跨语言、沙箱化、高性能神经通信标准**。

### 1.1 核心设计目标
1. **语言中立 (Polyglot Independence)**：开发者可使用 **Python、Rust、C++、Go 或 TypeScript/Node.js** 自由编写感官探针；
2. **进程沙箱与故障隔离 (Process Sandbox Isolation)**：每个末梢神经插件作为独立操作系统子进程（Subprocess）运行，插件崩溃或内存泄漏 **0% 影响 CyberSpine 中枢**，支持自动健康检测与热重启；
3. **双通道传输 (Dual-Channel IPC Topology)**：
   * **控制面（轻量信号）**：走命名管道（Named Pipe）或 Stdio，毫秒级传输结构化 JSON 脉冲；
   * **数据面（重量级媒体）**：走 Windows 命名共享内存（`Memory-Mapped File`），实现 4K 60fps 屏幕差分画面与原始音频流的 **零拷贝（Zero-Copy）微秒级传输**；
4. **即插即拔 (Hot-Pluggable Marketplace)**：像 Chrome 扩展或 VSCode 插件一样，通过放置在 `plugins/` 目录即刻识别加载。

---

## 2. 插件元数据清单规范 (`manifest.json`)

每个神经插件根目录下必须包含且仅包含一份 UTF-8 编码的 `manifest.json`：

### 2.1 JSON Schema 契约定义
```json
{
  "$schema": "https://cyberspine.dev/schemas/bnp-manifest-v1.json",
  "nerve_id": "nerve.vision.screen_diff",
  "name": "Screen Diff Vision Perceptor",
  "version": "1.0.0",
  "author": "CyberSpine Open Source Community",
  "category": "VISION",
  "description": "基于 Rust 硬件加速的高性能屏幕差分与活跃窗口感知插件",
  "entrypoint": "bin/screen_worker.exe",
  "transport": "NAMED_PIPE",
  "ipc_pipe_name": "CyberSpine_Nerve_Vision_Screen",
  "permissions": [
    "PERM_SCREEN_CAPTURE",
    "PERM_FOREGROUND_WINDOW"
  ],
  "default_config": {
    "fps_limit": 10,
    "diff_threshold": 0.05,
    "enable_shm": true
  },
  "min_cyberspine_version": "3.0.0"
}
```

### 2.2 核心字段详细说明

| 字段 | 类型 | 是否必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `nerve_id` | String | 是 | 全局唯一插件标识，建议反向域名风格（如 `nerve.storage.io`） |
| `name` | String | 是 | 插件人类可读名称 |
| `version` | String | 是 | 符合 SemVer 规范的版本号（如 `1.0.0`） |
| `category` | String | 是 | 感官分类：`VISION`（视觉）、`AUDITION`（听觉）、`TACTILE`（触觉/外设）、`VISCERAL`（内脏/系统） |
| `entrypoint` | String | 是 | 插件可执行入口文件相对路径（支持 `.exe`、`.py`、`.js` 等） |
| `transport` | String | 是 | 通信传输方式：`STDIO`（默认轻量）或 `NAMED_PIPE`（高吞吐推荐） |
| `permissions` | Array | 是 | 声明请求的操作系统权限，用于安全审计与防止杀软误报 |
| `default_config`| Object | 否 | 插件的默认运行时参数配置字典 |

---

## 3. 双通道传输与共享内存零拷贝架构

```
┌────────────────────────────────────────────────────────────────────────┐
│               【 CyberSpine 中枢主进程 (Python 调度) 】                  │
└───────────────────▲────────────────────────────────┬───────────────────┘
                    │                                │
    【控制面 (Control Plane)】                        【数据面 (Data Plane)】
    - 传输通道：Named Pipe / Stdio                   - 传输通道：Windows 命名共享内存
    - 传输内容：SomaticPulse JSON 元数据              - 传输内容：4K 原始图像 / 音频 PCM
    - 吞吐耗时：< 0.5ms                              - 吞吐耗时：< 1.0ms (0 内存拷贝)
                    │                                │
┌───────────────────┴────────────────────────────────┴───────────────────┐
│              【 神经插件子进程沙箱 (Rust / C++ / Node / Python) 】       │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.1 零拷贝共享内存工作流
1. **插件端写入**：
   * 插件调用操作系统底层 API（Windows `CreateFileMapping` / Linux `shm_open`）开辟命名共享内存块（如 `Global\CyberSpine_SHM_Vision_01`）；
   * 将屏幕捕获的原始像素数据写入该内存；
2. **轻量脉冲通知**：
   * 插件向控制面管道发送一个仅约 100 字节的 `SomaticPulse` JSON 报文，其中携带 `shm_handle: "Global\\CyberSpine_SHM_Vision_01"` 和变动区域坐标；
3. **中枢端零拷贝读取**：
   * 中枢通过内存映射句柄按需读取，无需跨进程序列化与反序列化海量字节，**物理 CPU 占用趋近于 0**！

---

## 4. 插件生命周期与 JSON-RPC 状态机

插件与中枢之间通过标准 JSON-RPC 2.0 协议进行握手与生命周期流转：

```
       中枢 (CyberSpine Core)                       插件子进程 (Nerve Plugin)
                 │                                              │
                 │────── 1. rpc: nerve/init ───────────────────►│ (传递配置，初始化硬件句柄)
                 │◄───── 2. response: { status: "ready" } ──────│
                 │                                              │
                 │────── 3. rpc: nerve/start_stream ───────────►│ (开启感官监听循环)
                 │◄───── 4. push: nerve/pulse (SomaticPulse) ───│ (持续高频/事件驱动推送)
                 │                                              │
                 │────── 5. rpc: nerve/pause ──────────────────►│ (中枢节能调控，暂停推流)
                 │◄───── 6. response: { status: "paused" } ─────│
                 │                                              │
                 │────── 7. rpc: nerve/resume ─────────────────►│ (恢复推流)
                 │                                              │
                 │────── 8. rpc: nerve/shutdown ───────────────►│ (优雅释放资源并退出)
                 │◄───── 9. response: { status: "stopped" } ────│
```

### 4.1 标准 JSON 报文示例

#### 1. 握手初始化请求 (`nerve/init`)
```json
{
  "jsonrpc": "2.0",
  "id": "req_init_001",
  "method": "nerve/init",
  "params": {
    "config": {
      "fps_limit": 10,
      "diff_threshold": 0.05
    },
    "ipc_channel": "\\\\.\\pipe\\CyberSpine_Nerve_Vision_Screen"
  }
}
```

#### 2. 神经电信号推送 (`nerve/pulse`)
```json
{
  "jsonrpc": "2.0",
  "method": "nerve/pulse",
  "params": {
    "pulse_id": "pulse_1787851329618_001",
    "nerve_id": "nerve.vision.screen_diff",
    "channel": "VISION",
    "observed_at": "2026-08-28T01:50:00Z",
    "headline": "FOREGROUND_WINDOW_SWITCHED",
    "semantic_context": {
      "process_name": "Code.exe",
      "window_title": "storage_probe.py - CyberSpine",
      "is_fullscreen": false
    },
    "shm_handle": null
  }
}
```

---

## 5. 容错、心跳与热重启机制 (Fault Tolerance)

1. **心跳检测 (Heartbeat Ping)**：
   * 中枢每隔 15 秒向插件发送 `nerve/ping` 请求，若连续 2 次超时未响应，标记为 `UNRESPONSIVE`；
2. **崩溃热重启 (Auto Restart)**：
   * 若子进程异常退出（ExitCode != 0），中枢记录告警日志，并在 **500ms 内自动重新拉起新子进程**；
   * 若 1 分钟内连续崩溃超过 3 次，将该插件自动标记为 `DEGRADED_DISABLED`（降级隔离），绝不拖慢主系统。
