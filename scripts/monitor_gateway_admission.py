# ruff: noqa: E402
"""A deliberately redacted terminal observer for gateway demonstrations.

Read one NeuralMessage JSON object per stdin line. Output intentionally excludes
payloads, session tokens, titles, paths, PIDs, and all other raw sensor fields.
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import tempfile
import time
from pathlib import Path

# Permit direct ``python scripts/monitor_gateway_admission.py`` invocation without
# requiring an editable installation; no sensor data is loaded at import time.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.core.event_queue import DurableEventQueue
from src.core.flow_control import RateLimitPolicy
from src.core.gateway_errors import GatewayRejected
from src.core.neural_gateway import NeuralSignalGateway
from src.core.neural_message import MessageKind, NeuralMessage
from src.core.plugin_health import PluginHealthMonitor
from src.core.plugin_manifest import load_manifest
from src.core.plugin_registration import PluginGrant


def _safe_line(status: str, message: NeuralMessage | None = None, *, code: str = "", queue_size: int = 0) -> str:
    fields = [f"status={status}"]
    if message is not None:
        fields.extend((f"topic={message.topic}", f"schema={message.payload_schema}"))
    if code:
        fields.append(f"reason={code}")
    fields.append(f"queue={queue_size}")
    return " ".join(fields)


def _publish_and_render(gateway: NeuralSignalGateway, session, message: NeuralMessage) -> None:
    """Print only protocol metadata; this observer never renders sensor payloads."""
    try:
        gateway.publish(message, session)
        print(_safe_line("accepted", message, queue_size=len(gateway.queue.pending())), flush=True)
    except GatewayRejected as error:
        print(_safe_line("rejected", message, code=error.code.value, queue_size=len(gateway.queue.pending())), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Observe gateway admission without printing signal payloads.")
    parser.add_argument("manifest", type=Path, help="manifest JSON used to create a temporary demo session")
    parser.add_argument("--window-snapshot", action="store_true",
                        help="collect real local window facts for a bounded rolling demonstration")
    parser.add_argument("--governance-demo", action="store_true",
                        help="run a bounded synthetic G2 flow-control and health demonstration")
    parser.add_argument("--duration", type=float, default=5.0,
                        help="seconds to run --window-snapshot (default: 5, must be positive)")
    args = parser.parse_args()
    if args.duration <= 0:
        parser.error("--duration must be positive")
    if args.window_snapshot and args.governance_demo:
        parser.error("choose either --window-snapshot or --governance-demo")
    manifest = load_manifest(json.loads(args.manifest.read_text(encoding="utf-8")))
    # DurableEventQueue deliberately owns no long-lived connection, but Windows
    # may defer SQLite handle cleanup. Ignore cleanup-only failures in this demo
    # observer so a completed visible result is never reported as a failure.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
        clock = [0.0]
        gateway = NeuralSignalGateway(
            DurableEventQueue(Path(directory) / "signals.db"),
            rate_limit_policy=RateLimitPolicy(capacity=1, refill_per_second=1, clock=lambda: clock[0]),
        )
        gateway.register(manifest, PluginGrant.create(manifest.plugin_id, manifest.capabilities))
        session = gateway.open_session(manifest.plugin_id, "terminal-demo", manifest.manifest_digest)
        if args.governance_demo:
            if "window.geometry_changed" not in manifest.capabilities:
                parser.error("--governance-demo requires a manifest declaring window.geometry_changed")
            gateway.health = PluginHealthMonitor(
                degraded_after_rejections=1,
                paused_after_rejections=2,
                quarantined_after_rejections=3,
                clock=lambda: clock[0],
            )
            message = NeuralMessage(
                kind=MessageKind.EVENT,
                source=session.plugin_id,
                topic="window.geometry_changed",
                payload_schema="window.geometry_changed@1",
                payload={"changes": []},
            )
            print("mode=governance-demo payload=redacted", flush=True)
            for label, advance in (("accepted", 0.0), ("rate_limited", 0.0), ("recovered", 1.0),
                                   ("paused", 0.0), ("isolated", 0.0)):
                clock[0] += advance
                attempt = message.model_copy(update={"message_id": f"governance-{label}"})
                try:
                    gateway.publish(attempt, session)
                    status = label
                except GatewayRejected as error:
                    status = error.code.value
                assessment = gateway.health_for(session.plugin_id, session.instance_id)
                print(
                    f"status={status} topic={attempt.topic} queue={len(gateway.queue.pending())} "
                    f"health={assessment.state.value} audit=recorded",
                    flush=True,
                )
            decision = "suppressed" if gateway.health_for(session.plugin_id, session.instance_id).state.value == "quarantined" else "active"
            print(f"status=isolation decision={decision} payload=redacted", flush=True)
        elif args.window_snapshot:
            if manifest.plugin_id != "peripheral.window.activity":
                parser.error("--window-snapshot requires the built-in window activity manifest")
            from src.sensing.window_activity import WindowActivityPeripheral

            peripheral = WindowActivityPeripheral()
            deadline = time.monotonic() + args.duration
            print("mode=window-snapshot payload=redacted", flush=True)
            try:
                while time.monotonic() < deadline:
                    for message in peripheral.collect_messages():
                        _publish_and_render(gateway, session, message)
                    time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
            finally:
                peripheral.stop()
        else:
            for line in sys.stdin:
                message = None
                try:
                    message = NeuralMessage.model_validate_json(line)
                    _publish_and_render(gateway, session, message)
                except ValueError:
                    print(_safe_line("rejected", code="invalid_message", queue_size=len(gateway.queue.pending())), flush=True)
        del gateway
        gc.collect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
