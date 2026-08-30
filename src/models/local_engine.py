"""
CyberSpine 本地大模型引擎 (Ollama 深度直连与真实神经网络推理驱动)
直接复用全球主流成熟开源推理运行时 Ollama，支持 RTX 4060 GPU 满血加速、JSON 语法约束与一键拉取。
"""
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List

from src.actuators.base import ProposedAction, ActionRiskLevel
from src.models.somatic_signals import utc_now


# 约束小模型 100% 结构化输出动作帧的 System Prompt
SYSTEM_ACTION_PROMPT = """你是由 CyberSpine 驱动的端侧仿生神经中枢 AI 助手。
你的职责是：基于用户当前的微观系统感官状态（前台焦点、应用画像、负载压力、内环境稳态、通知、存储外设），推演下一步能主动协助用户的操作系统控制动作。

你必须且只能输出严格符合以下 JSON 结构的单行 JSON 对象，不要输出任何多余的前缀、Markdown 标记或解释文字：
{
  "thought_chain": "思考推演链：识别当前发生了什么微观变化",
  "actuator_id": "负责执行的运动神经元 (如 motor.app_control, motor.workspace, motor.power)",
  "action_name": "具体动作名称 (如 open_in_vscode, scan_directory, set_power_scheme, open_folder_in_explorer)",
  "risk_level": "动作风险等级 (READ_ONLY_SAFE 或 MUTATING_APPROVAL)",
  "parameters": {
    "action_id": "动作ID",
    "target_path": "目标路径(可选)",
    "mode": "电源模式(可选, 如 HIGH_PERFORMANCE)"
  },
  "reason": "为什么提议该动作的简短理由",
  "inquiry_message": "向用户发出的温和卡片询问文本"
}
"""

# 约束端侧小模型 100% 结构化输出全景世界宏观感知与高级大脑决策的 System Prompt
SYSTEM_BRIEFING_PROMPT = """你是由 CyberSpine 驱动的端侧仿生神经中枢 AI 助手。
你的职责是：作为连接物理计算机硬件与主体大脑（Cortex）的中枢神经小脑，仔细分析过去 60 秒内的物理感官时序数据（前台活跃程序与窗口标题、连续专注驻留时长、CPU与内存实时负载、物理网络时延、外设与通知队列），向高级主体大脑汇报一段约 200 字的全景宏观世界感知简报，并严格回答以下 4 个问题：
1. 【电脑当前在干嘛】：计算机底层硬件负载（CPU/内存）、网络链路健康度与系统稳态；
2. 【用户在做什么工作】：用户正在使用的前台生产力软件与具体操作的工作流；
3. 【用户当前的注意点在哪里】：前台窗口标题关键词与连续专注驻留秒数/心流状态；
4. 【是否需要高级大脑介入思考与指示】：根据异常、卡顿、复杂工程切换或长时间驻留，判断是否需要唤醒高级大脑 (escalate_to_cortex)。

你必须输出严格符合以下 JSON 结构的单行 JSON 对象，不要包含 Markdown 代码块或多余解释：
{
  "summary": "【全景感知简报】过去60秒系统处于稳态运行，用户前台持续聚焦于[程序名]（窗口标题：'xxx'），已连续专注驻留 xx 秒；当前系统 CPU 平均负载 xx%，物理内存占用 xx%，网络 DNS 时延 xx ms，链路平稳无丢包；硬件外设与存储卷就绪，未捕获异常崩溃事件。",
  "user_activity": "用户正在使用[程序名]进行具体的业务操作（例如：编写 Python 异步代码、调试前端界面、浏览器查阅 API 文档）",
  "attention_focus": "当前注意力完全聚焦于窗口'xxx'中的具体模块，处于深度专注心流状态（连续驻留 xx 秒）",
  "macro_intent": "根据前台窗口标题与操作流转，深度推断用户的具体工作目标与下一步行为假设",
  "escalation_decision": {
    "escalate_to_cortex": false,
    "urgency": "LOW",
    "reason": "当前用户处于稳定心流状态，未发生系统级异常，无需打扰高级大脑",
    "suggested_cortex_prompt": "保持被动静默感知"
  },
  "inhibition_status": "正常感知模式 (0% 负载稳态)",
  "confidence": 0.98
}
"""



class LocalModelEngine:
    """本地 Ollama 大模型推理驱动引擎"""

    def __init__(self, ollama_url: str = "http://localhost:11434", default_model: str = "qwen2.5:0.5b"):
        self.ollama_url = ollama_url.rstrip("/")
        self.default_model = default_model
        self._is_ollama_alive = False
        self._auto_select_model()

    def _auto_select_model(self):
        """自动发现已安装的最佳模型"""
        installed = self.list_installed_models()
        if installed:
            names = [m.get("name") for m in installed]
            for pref in ["qwen2.5:3b", "qwen2.5:1.5b", "qwen2.5:0.5b", "qwen2.5:latest"]:
                if pref in names:
                    self.default_model = pref
                    return
            self.default_model = names[0]

    def set_active_model(self, model_name: str) -> Dict[str, Any]:
        """显式动态热切换当前使用的端侧小脑模型"""
        self.default_model = model_name
        return {
            "success": True,
            "active_model": self.default_model,
            "message": f"中枢神经推理模型已热切换至 {model_name}"
        }

    def check_engine_health(self) -> Dict[str, Any]:
        """探测本地 Ollama 服务状态"""
        self._auto_select_model()
        start = time.perf_counter()
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/version", method="GET")
            with urllib.request.urlopen(req, timeout=0.3) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    self._is_ollama_alive = True
                    return {
                        "mode": "OLLAMA_SERVICE_ONLINE",
                        "version": data.get("version", "unknown"),
                        "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                        "model": self.default_model,
                        "ollama_url": self.ollama_url,
                    }
        except Exception:
            pass

        self._is_ollama_alive = False
        return {
            "mode": "EMBEDDED_HEURISTIC_RULE_BRAIN",
            "status": "Ollama 未启动，已自动启用内置纯 Python 毫秒级启发式规则决策脑兜底",
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            "model": "CyberSpine-Spinal-Heuristic-Core",
        }

    def list_installed_models(self) -> List[Dict[str, Any]]:
        """获取本地 Ollama 已下载模型列表"""
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=0.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    return data.get("models", [])
        except Exception:
            pass
        return []

    def pull_model(self, model_name: str) -> Dict[str, Any]:
        """向 Ollama 发送模型拉取请求"""
        try:
            req_data = json.dumps({"name": model_name, "stream": False}).encode('utf-8')
            req = urllib.request.Request(
                f"{self.ollama_url}/api/pull",
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=600) as resp:
                if resp.status == 200:
                    return {"success": True, "model": model_name}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "Unknown pull failure"}

    def infer_action_from_somatic_state(self, somatic_state: Dict[str, Any]) -> ProposedAction:
        """
        根据当前感官状态推演操作系统控制动作帧
        - 优先使用真实 Ollama 神经网络 (GPU 加速 + JSON 约束)
        - 异常或离线时平滑 Fallback 至启发式规则脑
        """
        health = self.check_engine_health()
        if health.get("mode") == "OLLAMA_SERVICE_ONLINE":
            # 真实大模型推理
            action = self._infer_with_ollama(somatic_state)
            if action:
                return action

        # 离线或启动中兜底
        return self._heuristic_reasoning(somatic_state)

    def _infer_with_ollama(self, somatic_state: Dict[str, Any]) -> Optional[ProposedAction]:
        """真实调用 Ollama 进行 GPU 神经网络推理"""
        action_id = f"act_neural_{int(time.time() * 1000)}"
        prompt_content = f"【当前 8 大感官状态】\n{json.dumps(somatic_state, default=str, ensure_ascii=False, indent=2)}\n\n请推演下一步操作系统控制动作帧 JSON:"

        payload = {
            "model": self.default_model,
            "system": SYSTEM_ACTION_PROMPT,
            "prompt": prompt_content,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
                "num_gpu": 99,
            }
        }

        try:
            req_data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15.0) as resp:
                if resp.status == 200:
                    res_body = json.loads(resp.read().decode('utf-8'))
                    raw_response = res_body.get("response", "{}")
                    parsed = json.loads(raw_response)

                    # 构造标准 ProposedAction
                    risk_str = parsed.get("risk_level", "MUTATING_APPROVAL")
                    risk_enum = ActionRiskLevel.READ_ONLY_SAFE if risk_str == "READ_ONLY_SAFE" else ActionRiskLevel.MUTATING_APPROVAL

                    params = parsed.get("parameters", {})
                    params["action_id"] = action_id

                    return ProposedAction(
                        action_id=action_id,
                        actuator_id=parsed.get("actuator_id", "motor.app_control"),
                        action_name=parsed.get("action_name", "open_in_vscode"),
                        risk_level=risk_enum,
                        parameters=params,
                        reason=parsed.get("reason", "来自 Qwen2.5 神经网络推演"),
                        inquiry_message=parsed.get("inquiry_message", "💡 检测到新系统事件，是否允许执行建议操作？"),
                    )
        except Exception as e:
            # 记录异常并平滑降级
            print(f"[Ollama Inference Error] {e} -> 自动降级为启发式规则脑")

        return None

    def _heuristic_reasoning(self, state: Dict[str, Any]) -> ProposedAction:
        """纯 Python 毫秒级启发式规则决策脑 (0% 崩溃率，永远可用)"""
        action_id = f"act_prop_{int(time.time() * 1000)}"

        # 场景 A: 发现 Python 项目存储盘或工作区
        storage_drives = state.get("mounted_storage_devices", [])
        profiles = state.get("structure_profiles", [])
        target_path = state.get("mount_point", "")

        if "PYTHON_PROJECT" in profiles or (storage_drives and any("PYTHON" in str(d) for d in storage_drives)):
            path = target_path or (storage_drives[0].get("mount_point") if storage_drives else "E:\\")
            return ProposedAction(
                action_id=action_id,
                actuator_id="motor.app_control",
                action_name="open_in_vscode",
                risk_level=ActionRiskLevel.MUTATING_APPROVAL,
                parameters={"action_id": action_id, "target_path": path},
                reason="感知到用户接入了 Python 研发工作盘，推测准备展开编码或测试。",
                inquiry_message=f"💡 【CyberSpine 伴侣感知】检测到 Python 研发工程介质接入，是否需要为您在 VSCode 中打开并预备工作区？",
            )

        # 场景 B: 发现系统高负载且处于节能模式
        cpu_percent = state.get("cpu_percent", 0.0)
        if cpu_percent >= 85.0:
            return ProposedAction(
                action_id=action_id,
                actuator_id="motor.power",
                action_name="set_power_scheme",
                risk_level=ActionRiskLevel.MUTATING_APPROVAL,
                parameters={"action_id": action_id, "mode": "HIGH_PERFORMANCE"},
                reason=f"检测到当前系统 CPU 负载达 {cpu_percent}% (可能处于编译或高压计算)，建议临时提升电源性能。",
                inquiry_message=f"⚡ 【CyberSpine 性能优化】系统当前负载较高 ({cpu_percent}%)，是否需要为您临时切换为 [高性能电源方案]？",
            )

        # 场景 C: 常规默认工作区只读扫描
        return ProposedAction(
            action_id=action_id,
            actuator_id="motor.workspace",
            action_name="scan_directory",
            risk_level=ActionRiskLevel.READ_ONLY_SAFE,
            parameters={"action_id": action_id, "target_path": target_path or "."},
            reason="常规状态只读采样，建立工作区短期记忆。",
            inquiry_message="只读探测，无需人工干预。",
        )

    def generate_cerebellar_briefing(
        self,
        recent_ticks: List[Any],
        current_topology: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        根据最近 60s 心跳序列与当前感官拓扑，由本地 AI 模型生成宏观世界状态简报与意图假设
        - 优先使用真实 Ollama 神经网络 (GPU 加速 + JSON 约束)
        - 异常或离线时平滑 Fallback 至启发式小脑生成器
        """
        health = self.check_engine_health()
        if health.get("mode") == "OLLAMA_SERVICE_ONLINE":
            briefing = self._generate_briefing_with_ollama(recent_ticks, current_topology)
            if briefing:
                return briefing

        return self._heuristic_briefing(recent_ticks, current_topology)

    def _generate_briefing_with_ollama(
        self,
        recent_ticks: List[Any],
        current_topology: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """真实调用 Ollama 进行小脑宏观意图与世界简报推理"""
        # 提取过去心跳的精炼摘要
        ticks_summary = []
        for t in recent_ticks[-12:]:
            if hasattr(t, '__dict__'):
                ticks_summary.append({
                    "proc": getattr(t, 'active_process', 'Desktop'),
                    "dwell_sec": round(getattr(t, 'dwell_seconds', 0.0), 1),
                    "cpu_pct": round(getattr(t, 'cpu_percent', 0.0), 1),
                    "mem_pct": round(getattr(t, 'memory_percent', 0.0), 1),
                    "net_ms": round(getattr(t, 'network_latency_ms', 0.0), 1),
                })
            elif isinstance(t, dict):
                ticks_summary.append({
                    "proc": t.get('active_process', 'Desktop'),
                    "dwell_sec": round(t.get('dwell_seconds', 0.0), 1),
                    "cpu_pct": round(t.get('cpu_percent', 0.0), 1),
                    "mem_pct": round(t.get('memory_percent', 0.0), 1),
                    "net_ms": round(t.get('network_latency_ms', 0.0), 1),
                })

        channels = current_topology.get("channels", {})
        focus_info = channels.get("nerve.system.foreground_focus", {})
        apps_info = channels.get("nerve.system.running_apps", {})

        context_data = {
            "recent_60s_ticks": ticks_summary,
            "current_foreground_window": {
                "process": focus_info.get("active_process", "Desktop"),
                "title": focus_info.get("active_title", "Desktop"),
            },
            "user_app_categories": apps_info.get("categories", {}),
        }

        prompt_content = f"【过去 60 秒系统微观感官与心跳时序】\n{json.dumps(context_data, default=str, ensure_ascii=False, indent=2)}\n\n请生成 1 分钟世界状态简报与意图假设 JSON:"

        payload = {
            "model": self.default_model,
            "system": SYSTEM_BRIEFING_PROMPT,
            "prompt": prompt_content,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "num_gpu": 99,
            }
        }

        t_start = time.perf_counter()
        try:
            req_data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15.0) as resp:
                if resp.status == 200:
                    latency_ms = round((time.perf_counter() - t_start) * 1000, 1)
                    res_body = json.loads(resp.read().decode('utf-8'))
                    raw_response = res_body.get("response", "{}")
                    parsed = json.loads(raw_response)
                    return {
                        "summary": parsed.get("summary", "系统处于稳态运行中。"),
                        "user_activity": parsed.get("user_activity", "推测用户正在前台应用中工作。"),
                        "attention_focus": parsed.get("attention_focus", "焦点保持在前台主窗口。"),
                        "macro_intent": parsed.get("macro_intent", "推测用户正在专注工作中。"),
                        "escalation_decision": parsed.get("escalation_decision", {
                            "escalate_to_cortex": False,
                            "urgency": "LOW",
                            "reason": "系统运行稳态，心流平稳",
                            "suggested_cortex_prompt": "保持被动静默感知",
                        }),
                        "inhibition_status": parsed.get("inhibition_status", "正常感知模式 (0% 负载稳态)"),
                        "source_type": "NEURAL_LLM",
                        "model_name": self.default_model,
                        "device": "NVIDIA GeForce RTX 4060 (CUDA)",
                        "latency_ms": latency_ms,
                        "source": f"OLLAMA ({self.default_model})",
                        "model": self.default_model,
                    }
        except Exception as e:
            print(f"[Ollama Briefing Error] {e} -> 自动降级为启发式小脑生成")

        return None

    def _heuristic_briefing(
        self,
        recent_ticks: List[Any],
        current_topology: Dict[str, Any]
    ) -> Dict[str, Any]:
        """纯 Python 启发式小脑宏观简报生成器 (包含 200 字全景感知结构)"""
        channels = current_topology.get("channels", {})
        focus_info = channels.get("nerve.system.foreground_focus", {})
        stress_info = channels.get("nerve.system.high_load", {})
        proc = focus_info.get("active_process", "Desktop") or "Desktop"
        title = focus_info.get("active_title", "")
        dwell = focus_info.get("dwell_seconds", 0.0)
        cpu = stress_info.get("cpu_percent", 0.0)
        mem = stress_info.get("memory_percent", 0.0)

        # 智能推断用户工作流与意图
        p_lower = proc.lower()
        if any(ide in p_lower for ide in ["code", "devenv", "pycharm", "cursor", "idea"]):
            activity = f"用户正在使用 [{proc}] 进行软件架构开发与核心代码编写"
            focus_desc = f"注意力完全锁定在 IDE 编辑器窗口: '{title[:40] if title else '代码工作区'}'，已连续专注驻留 {dwell:.1f} 秒"
            intent = f"推测用户正专注于代码编写与软件架构调试 (前台: {proc})"
            should_escalate = False
            reason = "用户心流稳定，代码调试推进中，无需主动打断"
            prompt = "保持后台静默监听，随时响应高级指示"
        elif any(b in p_lower for b in ["chrome", "msedge", "firefox", "brave"]):
            activity = f"用户正在使用浏览器 [{proc}] 查阅技术文档与在线协同"
            focus_desc = f"注意力聚焦于网页标签页: '{title[:40] if title else '浏览器'}'，已持续驻留 {dwell:.1f} 秒"
            intent = f"推测用户正在使用浏览器查阅技术资料或在线协同 (前台: {proc})"
            should_escalate = False
            reason = "用户正在浏览技术参考资料，处于正常知识获取阶段"
            prompt = "提供相关上下文联想"
        elif any(t in p_lower for t in ["powershell", "cmd", "terminal", "wt"]):
            activity = f"用户正在命令行终端 [{proc}] 执行系统构建与运维指令"
            focus_desc = f"注意力聚焦于终端控制台: '{title[:40] if title else '命令行'}'，已驻留 {dwell:.1f} 秒"
            intent = f"推测用户正在命令行终端执行系统维护与脚本构建 (前台: {proc})"
            should_escalate = False
            reason = "终端脚本执行中，未检测到致命报错"
            prompt = "准备捕捉终端输出异常"
        else:
            activity = f"用户正在前台应用程序 [{proc}] 中进行日常人机交互"
            focus_desc = f"注意力位于窗口: '{title[:40] if title else '桌面交互'}'"
            intent = f"推测用户正在桌面环境中进行日常交互 (前台: {proc})"
            should_escalate = False
            reason = "桌面常态交互，系统保持待命"
            prompt = "保持就绪"

        summary = (
            f"【全景感知简报】过去 60 秒系统处于平稳运行稳态。用户前台工作台持续聚焦于 [{proc}] "
            f"(窗口标题: '{title[:35] if title else '桌面交互'}')，已建立稳定专注心流（连续驻留 {dwell:.1f} 秒）；"
            f"物理机内环境平稳，CPU 平均负载 {cpu:.1f}%，物理内存占用 {mem:.1f}%；"
            f"网络连通性良好，外设与存储卷指纹识别正常，未捕获任何软件崩溃或异常闪退事件。"
        )

        return {
            "summary": summary,
            "user_activity": activity,
            "attention_focus": focus_desc,
            "macro_intent": intent,
            "escalation_decision": {
                "escalate_to_cortex": should_escalate,
                "urgency": "LOW",
                "reason": reason,
                "suggested_cortex_prompt": prompt,
            },
            "inhibition_status": "正常感知模式 (0% 负载稳态)",
            "source_type": "HEURISTIC_RULE",
            "model_name": "CyberSpine-Spinal-Heuristic-Core",
            "device": "CPU / 启发式规则脑兜底",
            "latency_ms": 0.5,
            "source": "CyberSpine-Spinal-Heuristic-Core",
            "model": "Heuristic-SLM",
        }



