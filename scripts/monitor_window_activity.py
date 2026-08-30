"""在终端中观察窗口感知插件，并写入滚动 JSONL 日志。"""
import argparse
import sys
import time
import unicodedata
from collections import deque
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.sensing.window_activity import WindowActivityPeripheral
from src.sensing.window_activity_log import WindowActivityLog


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%H:%M:%S.%f")[:-3]


def _format_windows(summary: dict, limit: int = 4) -> str:
    windows = summary.get("windows", [])[:limit]
    if not windows:
        return "暂无可归因窗口"
    return " ｜ ".join(f"{item['application']} {item['focus_ratio']:.0%} ({item['focus_seconds']:.1f}s)"
                     for item in windows)


def _format_segments(summary: dict, limit: int = 4) -> str:
    segments = summary.get("segments", [])[-limit:]
    if not segments:
        return "暂无完整焦点片段"
    return " → ".join(f"{item['application']} {item['duration_seconds']:.1f}s"
                     for item in segments)


def _format_presented_windows(catalog: dict) -> str:
    windows = [item["application"] for item in catalog["windows"]
               if item["presentation"]["is_user_presented"]]
    return "、".join(windows) if windows else "无"


def _display_width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1 for char in text)


def _fit(text: str, width: int) -> str:
    visible, used = [], 0
    for char in text:
        char_width = _display_width(char)
        if used + char_width > width:
            break
        visible.append(char)
        used += char_width
    return "".join(visible) + " " * (width - used)


def _box_line(text: str = "", width: int = 72) -> str:
    return f"║ {_fit(text, width - 4)} ║"


def _box_header(text: str, width: int = 72) -> str:
    return f"╔═{_fit(text, width - 4)}═╗"


def _box_footer(width: int = 72) -> str:
    return f"╚{'═' * (width - 2)}╝"


def _box_divider(title: str, width: int = 72) -> str:
    label = f" {title} "
    remaining = max(0, width - 2 - _display_width(label))
    return f"╠{'═' * (remaining // 2)}{label}{'═' * (remaining - remaining // 2)}╣"


def _event_lines(messages) -> list[str]:
    lines = []
    for message in messages:
        timestamp = message.timestamp.astimezone().strftime("%H:%M:%S")
        if message.topic == "window.foreground_availability_changed":
            reason = "暂停专注归因" if message.payload["current_status"] == "unavailable" else "恢复专注归因"
            recovered = message.payload.get("recovered_foreground")
            recovered_text = (f"：{recovered['application']} (PID {recovered['pid']})"
                              if recovered else "")
            lines.append(f"{timestamp} 前台 {message.payload['previous_status']} → "
                         f"{message.payload['current_status']}；{reason}{recovered_text}")
        elif message.topic == "window.focus_changed":
            lines.append(f"{timestamp} 焦点 {message.payload['previous']['application']} → "
                         f"{message.payload['current']['application']}")
        elif message.topic == "window.high_interaction_changed":
            lines.append(f"{timestamp} 高频交互窗口={message.payload['current_window_ids'] or '无'}")
        elif message.topic == "window.geometry_changed":
            changes = message.payload["changes"]
            compact = "、".join(f"{item['window']['application']}:{item['change']}"
                                 f"{'（拖拽/调整大小候选）' if item['is_in_progress_candidate'] else ''}"
                                 for item in changes)
            lines.append(f"{timestamp} 窗口几何变化：{compact}")
    return lines


def _render_dashboard(messages, peripheral: WindowActivityPeripheral, recent_events: list[str],
                      sample_interval: float, display_interval: float) -> str:
    state = next(message for message in messages if message.topic == "window.current_state")
    catalog = next(message for message in messages if message.topic == "window.catalog")
    summary = next(message for message in messages if message.topic == "window.time_window_summary")
    payload = state.payload
    timestamp = _timestamp()
    foreground = payload["foreground"]
    active = [item["application"] for item in catalog.payload["windows"]
              if item["interaction"]["is_high_frequency"]]
    if foreground is None:
        foreground_text = "前台不可归因（系统过渡态）"
    else:
        window_state = foreground["window_state"]
        state_bits = []
        if window_state["is_fullscreen_candidate"]:
            state_bits.append("全屏候选")
        if window_state["is_topmost"]:
            state_bits.append("置顶")
        foreground_text = (f"前台={foreground['application']} pid={foreground['pid']} "
                           f"驻留={foreground['focus_dwell_seconds']:.1f}s"
                           f"{'｜' + '、'.join(state_bits) if state_bits else ''}")
    width = 72
    lines = [_box_header(f"CyberSpine · 窗口感知末梢 · {timestamp}", width),
             _box_line(f"● 当前前台  {foreground_text}", width),
             _box_line(f"◉ 屏幕窗口  {catalog.payload['screen_present_user_window_count']} 个用户窗口 / "
                       f"{catalog.payload['window_count']} 个目录窗口", width),
             _box_line(f"◌ 输入监听  {'正常' if peripheral.input_monitor_running else '未启用'} · "
                       f"回调错误 {peripheral.input_monitor_error_count} · 采样 {sample_interval:g}s / 刷新 {display_interval:g}s", width),
             _box_divider("实时窗口事实", width),
             _box_line(f"前台状态  {payload['foreground_status']}", width),
             _box_line(f"屏幕窗口  {_format_presented_windows(catalog.payload)}", width),
             _box_line(f"高频交互  {', '.join(active) if active else '无'}", width),
             _box_divider("末梢初步整合（观察时间窗）", width)]
    time_payload = summary.payload
    lines.extend([
        _box_line(f"可归因  {time_payload['observed_seconds']:.1f}s / {time_payload['period_seconds']:.0f}s "
                  f"({time_payload['coverage_ratio']:.1%}) · 未归因 {time_payload['unattributed_seconds']:.1f}s · "
                  f"焦点切换 {time_payload['focus_switch_count']}", width),
        _box_line(f"专注汇总  {_format_windows(time_payload)}", width),
        _box_line(f"焦点片段  {_format_segments(time_payload)}", width),
        _box_divider("历史变化（仅追加，不属于当前状态）", width),
        *[_box_line(f"↳ {event}", width) for event in (recent_events or ["暂无；系统正在建立观察基线"])],
        f"╠{'═' * (width - 2)}╣",
        _box_line("按 Ctrl+C 停止。日志持续写入 runtime/logs/window_activity.jsonl。", width),
        _box_line("不会记录窗口标题、输入文本、剪贴板、鼠标坐标或屏幕图像。", width),
        _box_footer(width),
    ])
    return "\n".join(lines)


def _draw_dashboard(rendered: str, clear_screen: bool) -> None:
    if clear_screen:
        print("\033[2J\033[H", end="")
    print(rendered, flush=True)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="观察 CyberSpine 窗口感知插件")
    parser.add_argument("--duration", type=float, default=0, help="运行秒数；0 表示持续运行至 Ctrl+C")
    parser.add_argument("--interval", type=float, default=10, help="窗口目录低频校准间隔（秒）")
    parser.add_argument("--display-interval", type=float, default=5, help="终端仪表盘刷新间隔（秒）")
    parser.add_argument("--input-monitor", action="store_true", help="诊断模式：启用全局键鼠交互统计，可能增加系统负担")
    parser.add_argument("--no-clear", action="store_true", help="不清屏，改为连续追加仪表盘快照")
    parser.add_argument("--log", type=Path, default=ROOT / "runtime" / "logs" / "window_activity.jsonl")
    parser.add_argument("--activity-window", type=float, default=300, help="交互统计时间窗（秒）")
    parser.add_argument("--focus-window", type=float, default=1800, help="专注汇总时间窗（秒）")
    parser.add_argument("--high-frequency-per-minute", type=float, default=12, help="高频交互阈值（次/分钟）")
    parser.add_argument("--minimum-interactions", type=int, default=6, help="高频判断所需最少交互次数")
    args = parser.parse_args()
    if (args.interval <= 0 or args.display_interval <= 0 or args.duration < 0 or args.activity_window <= 0 or args.focus_window <= 0
            or args.minimum_interactions < 1):
        parser.error("duration 必须不小于 0，interval/display-interval/activity-window/focus-window 必须大于 0，minimum-interactions 至少为 1")

    peripheral = WindowActivityPeripheral(activity_window_seconds=args.activity_window,
        focus_window_seconds=args.focus_window, high_frequency_per_minute=args.high_frequency_per_minute,
        minimum_interactions=args.minimum_interactions)
    logger = WindowActivityLog(args.log)
    peripheral.start(input_monitor=args.input_monitor)
    deadline = time.monotonic() + args.duration if args.duration else None
    last_display_at: float | None = None
    recent_events: deque[str] = deque(maxlen=6)
    clear_screen = not args.no_clear and sys.stdout.isatty()
    try:
        while deadline is None or time.monotonic() < deadline:
            messages = peripheral.collect_messages()
            logger.append(messages)
            recent_events.extend(_event_lines(messages))
            now = time.monotonic()
            if last_display_at is None or now - last_display_at >= args.display_interval:
                _draw_dashboard(_render_dashboard(messages, peripheral, list(recent_events), args.interval,
                    args.display_interval), clear_screen)
                last_display_at = now
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n已停止观察。")
    finally:
        peripheral.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
