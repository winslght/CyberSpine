# 工程研发路线图与里程碑 (Engineering Roadmap & Milestones)

**项目名称**：CyberSpine (赛博脊椎)  
**当前版本**：v0.1.0-alpha  

---

## 阶段规划总览

```mermaid
gantt
    title CyberSpine 研发全景甘特图
    dateFormat  YYYY-MM-DD
    section Phase 1: 立项与规范
    项目立项与白皮书落盘     :done,    p1_1, 2026-08-27, 1d
    三层架构与协议定稿       :done,    p1_2, 2026-08-27, 1d
    section Phase 2: 感知中枢 POC
    系统事件监听守护模块开发 :active,  p2_1, 2026-08-28, 3d
    本地 Ollama 3B 模型接入  :         p2_2, after p2_1, 2d
    防抖与降噪门控状态机实现 :         p2_3, after p2_2, 2d
    section Phase 3: 跨 Agent 桥接
    Webhook/消息总线通道搭建 :         p3_1, after p2_3, 3d
    MCP Server 事件适配器实现:         p3_2, after p3_1, 3d
    section Phase 4: 桌面级交互
    轻量级桌面气泡/通知中枢  :         p4_1, after p3_2, 4d
    全双工闭环体验端到端联调 :         p4_2, after p4_1, 3d
```

---

## 各阶段详细里程碑 (Milestones)

### 🚩 Milestone 1: 立项设计与协议规范 (Phase 1) - 【已完成】
* [x] 项目基础骨架创建与命名定案 (`ambient-sentinel`)
* [x] 撰写项目立项白皮书 (`PROJECT_PROPOSAL.md`)
* [x] 确立三层分工系统架构与 JSON 通信协议规范 (`ARCHITECTURE.md`)
* [x] 制定工程研发路线图 (`ROADMAP.md`)

---

### 🚩 Milestone 2: 神经末梢与本地感知核心 (Phase 2) - 【下一阶段】
* [ ] **系统事件监听器开发**：
  * [ ] 编写 Windows WMI 硬件插拔（USB/存储）监听脚本
  * [ ] 编写 `watchdog` 目录变动监听（Downloads / Workspace 监测）
  * [ ] 编写剪贴板文本格式监听与防抖处理
* [ ] **本地 SLM 推理客户端集成**：
  * [ ] 适配 Ollama / llama.cpp REST 接口
  * [ ] 调优 Qwen2.5-3B-Instruct 意图分类与 JSON 提取 Prompt
* [ ] **降噪与防疲劳门控**：
  * [ ] 实现冷却时间（Cooldown）与置信度过滤逻辑

---

### 🚩 Milestone 3: 跨 Agent 通信与主 Agent 协同 (Phase 3)
* [ ] 编写跨 Agent 消息总线适配器（支持 Ingress Webhook）
* [ ] 封装标准 **MCP (Model Context Protocol) Server**，提供系统事件流订阅
* [ ] 联调 Antigravity 主 Agent 的反应式唤醒（Reactive Wakeup）

---

### 🚩 Milestone 4: 桌面轻量交互与体验闭环 (Phase 4)
* [ ] 开发极轻量的 Windows 桌面悬浮气泡 / 系统通知栏组件
* [ ] 端到端全流程测试（U 盘插拔 $\rightarrow$ 本地 3B 感知 $\rightarrow$ 主 Agent 拟定方案 $\rightarrow$ 用户一键授权执行）
* [ ] 性能压测与空闲资源消耗优化
