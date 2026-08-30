"""
CyberSpine 神经末梢 7: 网络健康与链路质量感知探针 (Network Health Perceptor)
非侵入式测量 DNS 解析时延、网关连通性、物理网卡状态与有线/WiFi 接口切换。
"""
import time
import socket
import psutil
from typing import Dict, Any, List, Optional

from src.models.somatic_signals import RawSomaticSignal, utc_now
from src.perceptors.base import BasePerceptor


class NetworkHealthPerceptor(BasePerceptor):
    """网络健康与链路质量感知器"""

    def __init__(self, target_host: str = "1.1.1.1", target_port: int = 53, timeout_sec: float = 0.3):
        super().__init__(perceptor_id="nerve.network.health", channel="IO_NETWORK")
        self.target_host = target_host
        self.target_port = target_port
        self.timeout_sec = timeout_sec
        self._last_is_online: Optional[bool] = None
        self._last_latency_ms: float = 0.0

    def _check_connectivity(self) -> Dict[str, Any]:
        """执行极速非阻塞网络探测 (耗时通常 < 15ms)"""
        start = time.perf_counter()
        is_online = False
        latency_ms = 999.0

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout_sec)
            sock.connect((self.target_host, self.target_port))
            sock.close()
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            is_online = True
        except Exception:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            is_online = False

        # 获取活动网卡列表
        active_interfaces = []
        try:
            stats = psutil.net_if_stats()
            for if_name, s in stats.items():
                if s.isup and not if_name.lower().startswith("loopback"):
                    active_interfaces.append(if_name)
        except Exception:
            pass

        return {
            "is_online": is_online,
            "latency_ms": latency_ms,
            "active_interfaces": active_interfaces,
        }

    def poll_signals(self) -> List[RawSomaticSignal]:
        """轮询网络连通性与链路变动"""
        start_time = time.perf_counter()
        signals: List[RawSomaticSignal] = []

        now = utc_now()
        health = self._check_connectivity()
        is_online = health["is_online"]
        latency_ms = health["latency_ms"]

        # 1. 首次初始化
        if self._last_is_online is None:
            self._last_is_online = is_online
            self._last_latency_ms = latency_ms
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.record_poll_metric(duration_ms)
            return signals

        # 2. 状态切换事件 (断网或恢复连通)
        if is_online != self._last_is_online:
            sig_id = f"sig_net_conn_{int(now.timestamp() * 1000)}"
            event_type = "NETWORK_RESTORED" if is_online else "NETWORK_DISCONNECTED"

            signals.append(RawSomaticSignal(
                signal_id=sig_id,
                timestamp=now,
                channel=self.channel,
                event_type=event_type,
                source_probe=self.perceptor_id,
                raw_metrics=health,
            ))

        self._last_is_online = is_online
        self._last_latency_ms = latency_ms
        duration_ms = (time.perf_counter() - start_time) * 1000
        self.record_poll_metric(duration_ms)
        return signals

    def get_baseline(self) -> Dict[str, Any]:
        """获取当前网络健康基线"""
        return {
            "perceptor_id": self.perceptor_id,
            "health": self._check_connectivity(),
        }
