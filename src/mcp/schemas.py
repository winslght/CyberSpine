"""
CyberSpine MCP 工具规范定义 (Tool Definitions & JSON Schema)
"""
from typing import List, Dict, Any

MCP_SERVER_INFO = {
    "name": "cyberspine-neural-link",
    "version": "1.0.0",
}

MCP_PROTOCOL_VERSION = "2024-11-05"

CYBERSPINE_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "cyberspine_get_world_briefing",
        "description": "获取由端侧小脑 AI (Qwen2.5 @ RTX 4060) 生成的最新的 1 分钟世界感知宏观简报。回答 4 大核心问题：电脑硬件在干嘛、用户在做什么工作、用户当前注意力焦点在哪、是否需要高级大脑介入思考与指示。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "force_live_inference": {
                    "type": "boolean",
                    "description": "是否强制端侧大模型立即进行一次实时前向推演并返回最新简报 (默认为 False，即读取起搏器最近生成的简报)",
                    "default": False
                }
            },
            "required": []
        }
    },
    {
        "name": "cyberspine_get_somatic_state",
        "description": "获取当前全身 8 大物理感官神经末梢的完整时空拓扑（包含前台焦点软件与窗口标题、所有正在运行的进程分类、CPU/内存/供电体征、网络 DNS 时延、外设与存储卷指纹、稳定性与未处理系统通知队列）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_filter": {
                    "type": "string",
                    "description": "可选的通道过滤前缀，如 'nerve.system.foreground_focus' 或 'nerve.io.storage'",
                }
            },
            "required": []
        }
    },
    {
        "name": "cyberspine_get_pacemaker_ticks",
        "description": "获取 5.0s 真实物理生命起搏器的最近时序心跳流水 (包含前台程序、驻留秒数、CPU/内存体征及网络状态)。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "获取最近的心跳次数，默认 12 次 (即过去 60 秒数据)",
                    "default": 12
                }
            },
            "required": []
        }
    },
    {
        "name": "cyberspine_get_cognitive_telemetry",
        "description": "获取全透明结构化认知透视流帧 (包含 [SOMATIC] 身体感知、[SPINAL] 脊髓门控、[MODEL] 小模型推演思考链、[ACTION] 运动双手控制)。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "获取最近透视帧数量，默认 30 条",
                    "default": 30
                },
                "category": {
                    "type": "string",
                    "description": "按类别过滤：SOMATIC, SPINAL, MODEL, ACTION, SYSTEM",
                }
            },
            "required": []
        }
    },
    {
        "name": "cyberspine_propose_motor_action",
        "description": "向 CyberSpine 脊髓运动中枢提交操作系统控制动作建议。指令将经过安全三定律白名单与人工确认门禁后执行。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "description": "动作类型，例如 'open_app', 'open_in_vscode', 'set_power_scheme', 'switch_window', 'notify_user'",
                },
                "params": {
                    "type": "object",
                    "description": "动作参数字典，例如 {'target_path': '...', 'app_name': 'Code.exe'}",
                },
                "reason": {
                    "type": "string",
                    "description": "高级大脑提议执行该动作的推演理由",
                }
            },
            "required": ["action_type", "params", "reason"]
        }
    },
    {
        "name": "cyberspine_set_downward_inhibition",
        "description": "设置脊髓下行抑制（免打扰模式）。在指定时间内阻断自动神经反射，使 CyberSpine 保持完全静默被动感知。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "duration_seconds": {
                    "type": "integer",
                    "description": "下行抑制持续时长（秒），例如 300 表示静音 5 分钟",
                    "default": 300
                },
                "reason": {
                    "type": "string",
                    "description": "下行抑制的原因说明",
                    "default": "高级大脑主动设定免打扰专注模式"
                }
            },
            "required": ["duration_seconds"]
        }
    }
]
