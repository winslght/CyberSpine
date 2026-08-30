# CyberSpine 双节奏中枢神经认知架构详细设计方案 (Two-Stage Dual-Cadence Cognition)

> **历史 PoC 设计输入，非当前主线。** 双节律、周期性推演和意图叙事曾用于验证概念，不能绕过统一消息、只读上下文与用户确认边界。当前工程先完成窗口事实和受控最小闭环。

**版本**：v3.4.0-Planning  
**核心目标**：实现用户提出的 **5s~10s 微观心跳感知** 与 **1 分钟宏观小脑意图打包推演** 的双节奏认知架构，打造毫秒级低能耗起搏与结构化意图升华引擎。

---

## 1. 仿生认知分层与双节奏设计原理

```
[全身 8 大宏观神经末梢 (IO/焦点/应用/负载/稳态/通知/稳定性/网络)]
           │
           │ (每 5s~10s 毫秒级浅层轮询)
           ▼
┌─────────────────────────────────────────────────────────────┐
│ 阶段一：微观心跳检测 (Micro-Heartbeat Loop, 5s ~ 10s 自适应) │
│ - 保持中枢生命体征节律                                       │
│ - 实时感知系统微观状态变动 (Delta Pulses)                   │
│ - 动态监控本地端侧小模型的 Token 生成速度与耗时预算          │
│ - 汇入 60s 滚动神经时空缓冲队列                             │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ (每 60s 触发宏观全感官对齐)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 阶段二：宏观小脑判断 (Macro-Cerebellar Synthesis, 1 分钟周期)│
│ - 所有末梢电信号排队等齐 (Spatiotemporal Alignment)         │
│ - 打包生成《1分钟多维神经情境包 (Fused1MinuteEpisodicPacket)》│
│ - 中枢神经小脑 AI 推演：                                     │
│   1) 过去 1 分钟内系统整体发生了什么 (System Dynamics)       │
│   2) 用户当前在干什么、推测下一步意图 (User Intent)          │
│   3) 感觉门控决策：是否上报高级前额叶大脑 (Escalation Gate) │
└──────────────────────────────┬──────────────────────────────┘
                               │ (should_escalate == True)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 阶段三：前额叶高级大脑与双手执行 (Master Cortex & Motor Hands)│
│ - 3W 认知推演、伴侣式温和卡片交互                           │
│ - 经用户审批后动用双手工具执行工作区预备/排错/整理           │
│ - 下行抑制递质传导 (Efferent Inhibition)，恢复低功耗稳态     │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 核心模块详细技术规划

### 1. 神经起搏器 (`src/pacing/dual_cadence_clock.py`)
* **5s~10s 弹性心跳引擎**：
  * 默认以 5 秒为一个心跳周期轮询 `SomaticPerceptorHub`；
  * 若端侧小模型推理耗时超出预算，起搏器自动无缝降频至 10 秒弹性心跳，确保 0 卡顿；
* **60s 宏观窗口对齐器**：
  * 在 1 分钟窗口结束时，冻结并打包该周期内的所有微观事件序列为 `Fused1MinuteEpisodicPacket`。

---

### 2. 中枢神经小脑意图推演脑 (`src/spinal_core/cerebellar_synthesizer.py`)
* **双模推演引擎**：
  * **模式 A (本地端侧小模型)**：连接 Ollama (如 Qwen2.5-3B / Llama-3.2-3B)，进行轻量语义升华与 Token 速度监测；
  * **模式 B (纯 Python 启发式规则兜底)**：在无本地 GPU 或模型离线时，100% 毫秒级规则推演，确保零环境依赖稳健运行；
* **推演产物 (`1MinuteCerebellarNarrative`)**：
  * `system_dynamics_summary`：过去 1 分钟系统动态摘要（如：前台从 VSCode 切换至终端，CPU 出现 3 次编译尖峰，网络时延平稳）；
  * `user_intent_hypothesis`：用户宏观意图假设（如：用户正在调试 Python 核心逻辑，并连续执行单元测试）；
  * `should_escalate_to_cortex`：是否需要惊扰高级大脑。

---

### 3. 数据模型扩充 (`src/models/somatic_signals.py`)
* 新增 `MicroHeartbeatPulse`（5s 心跳脉冲）；
* 新增 `Fused1MinuteEpisodicPacket`（1分钟多维情境大包）；
* 新增 `Cerebellar1MinuteNarrative`（小脑 1 分钟推演叙事）。

---

## 3. 测试与留痕保障计划

1. **测试矩阵 (`tests/`)**：
   * `tests/test_dual_cadence_clock.py`：验证 5s 心跳与 60s 宏观触发逻辑；
   * `tests/test_cerebellar_synthesizer.py`：验证 1 分钟情境打包、意图升华与降频自适应；
   * `tests/test_dual_cadence_e2e.py`：双节奏与前额叶大脑端到端全链路闭环测试；
2. **留痕日志 (`03_本地日志与监控_logs/`)**：
   * `cerebellar_1min_narratives.jsonl`：记录每 1 分钟小脑产出的宏观意图推演报告；
   * `heartbeat_metrics.log`：记录心跳耗时与 Token 生成速率指标。
