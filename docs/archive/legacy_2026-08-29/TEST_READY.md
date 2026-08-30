# E2E Test Suite Ready

## Test Runner
- Command: `python -m unittest discover -s tests/e2e -p "test_tier*.py" -v`
- Full Suite: `python -m unittest discover -s tests -p "test_*.py" -v`
- Expected: all tests pass with exit code 0

## Coverage Summary
| Tier | Count | Description |
|------|------:|-------------|
| 1. Feature Coverage | 12 | R1-R5 / F1-F18 核心功能与接口契约隔离测试 |
| 2. Boundary & Corner | 8 | 恶意注入熔断、畸变 JSON 降级、极限路径、并发脉冲与缓冲溢出 |
| 3. Cross-Feature | 6 | 感官状态 × 推理引擎 × 风险等级 × 审批决策 × 抑制节律组合 |
| 4. Real-World Application | 4 | 真实研发接入闭环、高压能耗调节、断网韧性、插件动态扩展 |
| **Total** | **30** | **4-Tier 全景端到端测试套件** |

## Feature Checklist
| Feature | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---------|:------:|:------:|:------:|:------:|
| F1: 5.0s 物理起搏器与日志追加 | ✓ | ✓ | ✓ | ✓ |
| F2: 前台驻留计时与 60s 简报 | ✓ | ✓ | ✓ | ✓ |
| F3: 8 大感官物理采样与基线 | ✓ | ✓ | ✓ | ✓ |
| F4: 神经末梢热插拔物理连通 | ✓ | ✓ | ✓ | ✓ |
| F5: 扩展插件安装与依赖校验 | ✓ | ✓ | ✓ | ✓ |
| F6: Ollama 双向通讯与探测 | ✓ | ✓ | ✓ | ✓ |
| F7: Qwen2.5 动作帧真实推理 | ✓ | ✓ | ✓ | ✓ |
| F8: 动态 Token/s 与 GPU 显存 | ✓ | ✓ | ✓ | ✓ |
| F9: 启发式规则脑 0 崩溃降级 | ✓ | ✓ | ✓ | ✓ |
| F10: 大脑连接器配置与灵敏度 | ✓ | ✓ | ✓ | ✓ |
| F11: 运动双手应用与窗口调度 | ✓ | ✓ | ✓ | ✓ |
| F12: VSCode 路径自适应兼容 | ✓ | ✓ | ✓ | ✓ |
| F13: 工程工作区创建与预检 | ✓ | ✓ | ✓ | ✓ |
| F14: Windows 电源方案动态调节 | ✓ | ✓ | ✓ | ✓ |
| F15: 安全三定律门控硬熔断 | ✓ | ✓ | ✓ | ✓ |
| F16: 4 阶段即时感知推演 | ✓ | ✓ | ✓ | ✓ |
| F17: 认知透视帧与 JSONL 持久化 | ✓ | ✓ | ✓ | ✓ |
| F18: 一键启动批处理脚本 | ✓ | ✓ | ✓ | ✓ |
| F19: 全量测试套件 100% 绿灯 | ✓ | ✓ | ✓ | ✓ |
