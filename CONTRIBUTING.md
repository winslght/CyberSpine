# 欢迎参与 CyberSpine 建设 (Contributing to CyberSpine)

> **"The Biomimetic Central Nervous System for Desktop AI Agents."**  
> 感谢你关注 **CyberSpine（赛博脊椎）**！

---

## 📌 项目定位：开放式神经末梢生态 (Open Nerve Ecosystem & RFC)

CyberSpine 的核心使命，是为前额叶 AI 大脑打造一套**语言中立、即插即拔、进程沙箱隔离的末梢感官生态（Biomimetic Nerve Protocol - BNP v1.0）**。

无论你是使用 **Python、Rust、C++、Go 还是 TypeScript/Node.js**，都可以像开发 Chrome 扩展或 VSCode 插件一样，为全球 AI 智能体开发专属感官！

---

## 🧩 如何开发一个末梢神经插件 (Build a Nerve Plugin)

每个神经插件都是一个独立目录，放置在 `plugins/` 下：

```
plugins/
└── nerve_custom_sensor/
    ├── manifest.json       # 插件清单 (元数据、入口、权限声明)
    ├── main.py (或 worker.exe) # 插件可执行入口 (任意语言)
    └── README.md           # 插件说明文档
```

### 1. 编写插件清单 (`manifest.json`)
```json
{
  "nerve_id": "nerve.custom.sensor_name",
  "name": "My Custom Sensor",
  "version": "1.0.0",
  "author": "Your Name",
  "category": "TACTILE", // "VISION" | "AUDITION" | "TACTILE" | "VISCERAL"
  "description": "感知特定外设或系统状态的末梢插件",
  "entrypoint": "main.py",
  "transport": "STDIO", // "STDIO" (简单插件) | "NAMED_PIPE" (高吞吐)
  "permissions": ["PERM_HARDWARE_IO"]
}
```

### 2. 实现标准生命周期与电信号发射 (`SomaticPulse`)
无论用什么语言，插件只需在启动后监听中枢的生命周期握手，并通过 Stdio / Named Pipe 输出 JSON 格式的 `SomaticPulse` 脉冲帧：

```json
{
  "pulse_id": "pulse_1787851329618_001",
  "nerve_id": "nerve.custom.sensor_name",
  "channel": "STORAGE",
  "observed_at": "2026-08-28T01:30:00Z",
  "headline": "DEVICE_STATE_CHANGED",
  "semantic_context": {
    "device_name": "MyHardware",
    "status": "ONLINE"
  }
}
```

* 对于 **高吞吐视觉/音频插件 (4K 60fps)**：支持通过 Windows 命名共享内存（`shm_handle`）进行零拷贝图像传递，毫秒级无损传输。

---

## 🛠️ 认领官方感官插件与模块 (Claim a Nerve)

* 🧩 **触觉与外设 (Tactile)**：Windows WMI/USB 即插即用、蓝牙 BLE 外设、串口传感器
* 🧩 **内脏与系统 (Visceral)**：剪贴板语义提取器、工作区文件系统 Watcher、系统资源与电池感知
* 🧩 **视觉与工作台 (Vision)**：前台窗口重心流转 (Rust)、高帧率屏幕差分捕获
* 🧩 **听觉与语音 (Audition)**：轻量本地 VAD 语音活动检测、会议语音状态感知

---

## 📝 贡献工作流 (Workflow)

1. **Fork** 本仓库到你的 GitHub 账号；
2. 创建特性分支：`git checkout -b feature/nerve-plugin-name`；
3. 在 `plugins/` 下添加你的独立插件并附带测试用例；
4. 提交并推送 PR，我们将第一时间进行 RFC 评审与合并！

---

## 📜 行为准则与开源许可

* 本项目遵循 **[MIT License](LICENSE)** 开源协议。
* 欢迎加入讨论，共同为下一代主动式具身数字生命赋予灵敏的躯体与感官！
