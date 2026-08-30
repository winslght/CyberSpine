# CyberSpine 插件

本目录存放末梢神经插件的清单和参考实现。当前统一消息、权限和兼容规则以 [统一神经通信规范](../docs/current/UNIFIED_NEURAL_COMMUNICATION.md) 为准；早期 BNP 示例仅供历史参考。

每个插件目录提供 `manifest.json`，声明稳定 ID、入口、能力、Schema、权限、采样方式与隐私边界。插件运行时加载器仍在后续阶段实现，因此内置插件代码当前位于 `src/sensing/`，清单位于 `plugins/builtin/`。

---

## 📂 目录结构与参考实现

```
plugins/
├── builtin/                       # 随主程序发布的插件清单
│   └── window_activity/            # 窗口感知（首个完整参考插件）
├── examples/                      # 早期参考实现与开发模版
│   └── mock_storage_nerve/        # 最小可运行的示例末梢插件
│       ├── manifest.json          # 插件元数据与权限声明
│       ├── main.py                # 插件主入口 (JSON-RPC / Stdio 通信)
│       └── README.md              # 插件说明与测试方法
└── README.md                      # [本文件] 插件生态目录说明
```

详细开发规范请参考当前文档导航中的协议、命名与开发规划。
