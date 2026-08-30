"""汇总窗口感知 JSONL 日志。"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.sensing.window_activity_log import analyze_window_activity_log


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="分析 CyberSpine 窗口感知日志")
    parser.add_argument("--log", type=Path, default=ROOT / "runtime" / "logs" / "window_activity.jsonl")
    args = parser.parse_args()
    print(json.dumps(analyze_window_activity_log(args.log), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
