# Mock Storage Sensory Nerve (BNP v1.0 Reference Implementation)

这是一个官方参考示例插件，展示如何基于 **BNP v1.0 规范** 编写跨语言神经末梢插件。

---

## 🚀 运行与测试

可以直接通过 Python 运行该插件观察输出的 JSON-RPC 格式脉冲信号：

```bash
python main.py
```

### 预期标准输出 (Stdout Stream)
```json
{"jsonrpc": "2.0", "method": "nerve/ready", "params": {"nerve_id": "nerve.example.mock_storage", "status": "ACTIVE", "version": "1.0.0"}}
{"jsonrpc": "2.0", "method": "nerve/pulse", "params": {"pulse_id": "pulse_mock_...", "nerve_id": "nerve.example.mock_storage", "channel": "TACTILE_STORAGE", "observed_at": "...", "headline": "MOCK_DEVICE_DISCOVERED", "semantic_context": {"device_name": "Demo SanDisk Flash Drive", "capacity_gb": 64.0, "status": "ONLINE"}}}
```
