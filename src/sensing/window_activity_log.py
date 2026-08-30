"""窗口感知观察器的滚动 JSONL 日志与离线分析。"""
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable

from src.core.neural_message import NeuralMessage


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class WindowActivityLog:
    """仅追加的本地 JSONL 日志；达到上限时按时间归档。"""

    def __init__(self, path: Path | str, max_bytes: int = 5_000_000):
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, messages: Iterable[NeuralMessage]) -> int:
        lines = [json.dumps({"observed_at": _now_iso(), "message": message.model_dump(mode="json")}, ensure_ascii=False)
                 for message in messages]
        if not lines:
            return 0
        payload = ("\n".join(lines) + "\n").encode("utf-8")
        self._rotate_if_needed(len(payload))
        with self.path.open("ab") as handle:
            handle.write(payload)
        return len(lines)

    def _rotate_if_needed(self, incoming_bytes: int) -> None:
        if not self.path.exists() or self.path.stat().st_size + incoming_bytes <= self.max_bytes:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive = self.path.with_name(f"{self.path.stem}.{timestamp}{self.path.suffix}")
        index = 1
        while archive.exists():
            archive = self.path.with_name(f"{self.path.stem}.{timestamp}.{index}{self.path.suffix}")
            index += 1
        self.path.rename(archive)


def analyze_window_activity_log(path: Path | str) -> dict[str, Any]:
    """从一份 JSONL 日志提取人可读的窗口与交互概览。"""
    log_path = Path(path)
    summary: dict[str, Any] = {"log_path": str(log_path), "records": 0, "focus_changes": 0,
                               "high_interaction_changes": 0, "latest_foreground": None,
                               "visible_window_count": 0, "high_interaction_windows": [],
                               "latest_time_window": None, "foreground_availability_changes": 0,
                               "first_observed_at": None, "last_observed_at": None}
    if not log_path.exists():
        return summary
    latest_catalog: dict[str, Any] | None = None
    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
                message = record["message"]
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
            summary["records"] += 1
            observed_at = record.get("observed_at")
            summary["first_observed_at"] = summary["first_observed_at"] or observed_at
            summary["last_observed_at"] = observed_at or summary["last_observed_at"]
            topic = message.get("topic")
            if topic == "window.current_state":
                summary["latest_foreground"] = message.get("payload", {}).get("foreground")
            elif topic == "window.catalog":
                latest_catalog = message.get("payload", {})
            elif topic == "window.focus_changed":
                summary["focus_changes"] += 1
            elif topic == "window.high_interaction_changed":
                summary["high_interaction_changes"] += 1
            elif topic == "window.time_window_summary":
                summary["latest_time_window"] = message.get("payload", {})
            elif topic == "window.foreground_availability_changed":
                summary["foreground_availability_changes"] += 1
    if latest_catalog:
        windows = latest_catalog.get("windows", [])
        summary["visible_window_count"] = latest_catalog.get("window_count", len(windows))
        summary["high_interaction_windows"] = [
            {"window_id": item.get("window_id"), "application": item.get("application"),
             "pid": item.get("pid"), "events_per_minute": item.get("interaction", {}).get("events_per_minute"),
             "event_count": item.get("interaction", {}).get("event_count")}
            for item in windows if item.get("interaction", {}).get("is_high_frequency")
        ]
    return summary
