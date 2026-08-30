"""
CyberSpine 神经末梢 2: 运行程序拓扑感知探针 (Running Apps Topology Perceptor)
感知当前操作系统上活跃的用户交互软件拓扑分布与应用分类画像 (IDE, 浏览器, 终端, 通讯, 创作, 游戏)。
"""
import time
import psutil
from typing import Dict, Any, List, Set, Optional

from src.models.somatic_signals import RawSomaticSignal, utc_now
from src.perceptors.base import BasePerceptor


class RunningAppsPerceptor(BasePerceptor):
    """当前运行程序拓扑感知器"""

    # 常见应用语义分类画像字典
    APP_CATEGORIES = {
        "IDE": {"code.exe", "pycharm64.exe", "idea64.exe", "devenv.exe", "cursor.exe", "sublime_text.exe", "clion64.exe"},
        "BROWSER": {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"},
        "TERMINAL": {"powershell.exe", "cmd.exe", "windowsterminal.exe", "wt.exe", "conemu64.exe", "git-bash.exe"},
        "COMMUNICATION": {"wechat.exe", "dingtalk.exe", "feishu.exe", "slack.exe", "discord.exe", "telegram.exe", "qq.exe"},
        "CREATIVE": {"photoshop.exe", "premiere.exe", "afterfx.exe", "blender.exe", "illustrator.exe", "obs64.exe"},
        "GAMING": {"steam.exe", "epicgameslauncher.exe", "genshinimpact.exe", "league of legends.exe"},
    }

    # 忽略的纯系统底层守护进程 (降噪)
    SYSTEM_IGNORE = {
        "system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "services.exe",
        "lsass.exe", "svchost.exe", "fontdrvhost.exe", "dwm.exe", "memory compression",
        "spoolsv.exe", "runtimebroker.exe", "sihost.exe", "taskhostw.exe", "explorer.exe"
    }

    def __init__(self):
        super().__init__(perceptor_id="nerve.system.running_apps", channel="APPS_TOPOLOGY")
        self._known_app_names: Set[str] = set()
        self.refresh_baseline()

    def _classify_process(self, proc_name: str) -> str:
        """对进程名进行语义画像分类"""
        lower = proc_name.lower()
        for cat, names in self.APP_CATEGORIES.items():
            if lower in names:
                return cat
        return "GENERAL_APP"

    def refresh_baseline(self) -> None:
        """初始化运行应用基线"""
        current_apps = self._get_active_app_names()
        self._known_app_names = current_apps

    def _get_active_app_names(self) -> Set[str]:
        """获取当前活跃的用户态应用进程名集合 (执行耗时 < 3ms)"""
        apps: Set[str] = set()
        try:
            for p in psutil.process_iter(['name']):
                try:
                    name = p.info['name']
                    if name:
                        lower = name.lower()
                        if lower not in self.SYSTEM_IGNORE and not lower.startswith("service"):
                            apps.add(name)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        return apps

    def poll_signals(self) -> List[RawSomaticSignal]:
        """轮询应用启动与退出事件"""
        start_time = time.perf_counter()
        signals: List[RawSomaticSignal] = []

        current_apps = self._get_active_app_names()
        now = utc_now()

        # 1. 发现新启动应用
        new_launched = current_apps - self._known_app_names
        for app in new_launched:
            cat = self._classify_process(app)
            # 仅对特征明显的生产力或用户应用发射电信号
            if cat != "GENERAL_APP":
                sig_id = f"sig_app_launch_{int(now.timestamp() * 1000)}_{app}"
                signals.append(RawSomaticSignal(
                    signal_id=sig_id,
                    timestamp=now,
                    channel=self.channel,
                    event_type="APP_LAUNCHED",
                    source_probe=self.perceptor_id,
                    raw_metrics={
                        "app_name": app,
                        "category": cat,
                        "total_running_apps": len(current_apps),
                    },
                ))

        # 2. 发现退出应用
        terminated = self._known_app_names - current_apps
        for app in terminated:
            cat = self._classify_process(app)
            if cat in ("IDE", "CREATIVE", "GAMING"):
                sig_id = f"sig_app_exit_{int(now.timestamp() * 1000)}_{app}"
                signals.append(RawSomaticSignal(
                    signal_id=sig_id,
                    timestamp=now,
                    channel=self.channel,
                    event_type="APP_TERMINATED",
                    source_probe=self.perceptor_id,
                    raw_metrics={
                        "app_name": app,
                        "category": cat,
                        "total_running_apps": len(current_apps),
                    },
                ))

        self._known_app_names = current_apps
        duration_ms = (time.perf_counter() - start_time) * 1000
        self.record_poll_metric(duration_ms)
        return signals

    def get_baseline(self) -> Dict[str, Any]:
        """获取当前运行程序画像基线"""
        current_apps = self._get_active_app_names()
        categorized: Dict[str, List[str]] = {}
        for app in current_apps:
            cat = self._classify_process(app)
            categorized.setdefault(cat, []).append(app)

        return {
            "perceptor_id": self.perceptor_id,
            "total_user_apps": len(current_apps),
            "categories": categorized,
        }
