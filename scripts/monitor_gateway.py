# ruff: noqa: E402
"""Safe rolling terminal observer for the central neural gateway.

The observer consumes only gateway decisions and queue metadata.  It never
renders a NeuralMessage payload, session token, process identifier, or raw
exception text.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.core.event_queue import DurableEventQueue
from src.core.flow_control import RateLimitPolicy
from src.core.gateway_errors import GatewayRejected
from src.core.isolation_policy import IsolationPolicy
from src.core.neural_gateway import NeuralSignalGateway
from src.core.neural_message import MessageKind, NeuralMessage
from src.core.plugin_health import PluginHealthMonitor
from src.core.plugin_manifest import load_manifest
from src.core.plugin_registration import PluginGrant


@dataclass(frozen=True)
class GatewayView:
    pending: int
    delivered: int
    acknowledged: int
    expired: int
    authorized: int
    rejected: int
    rate_limited: int
    health: str
    rejection_count: int
    isolation: str
    audit_action: str
    audit_outcome: str
    last_topic: str


class GatewayMonitor:
    """Render an injectable, aggregate-only view of one gateway instance."""

    def __init__(self, gateway, plugin_id: str, instance_id: str, render=print) -> None:
        self.gateway = gateway
        self.plugin_id = plugin_id
        self.instance_id = instance_id
        self.render = render

    def snapshot(self) -> GatewayView:
        counts = self.gateway.queue.status_counts()
        health = self.gateway.health_for(self.plugin_id, self.instance_id)
        events = getattr(self.gateway.audit, "events", [])
        authorized = sum(event.outcome == "authorized" for event in events)
        rejected = sum(event.outcome == "rejected" for event in events)
        rate_limited = sum(event.reason == "rate_limited" for event in events)
        safe_last = next(
            (event for event in reversed(events) if event.outcome == "authorized"), None
        )
        last = events[-1] if events else None
        return GatewayView(
            pending=counts.get("pending", 0),
            delivered=counts.get("delivered", 0),
            acknowledged=counts.get("acknowledged", 0),
            expired=counts.get("expired", 0),
            authorized=authorized,
            rejected=rejected,
            rate_limited=rate_limited,
            health=health.state.value,
            rejection_count=health.rejection_count,
            isolation=IsolationPolicy().decide(health).state.value,
            audit_action=last.action if last else "none",
            audit_outcome=last.outcome if last else "none",
            last_topic=safe_last.topic if safe_last else "none",
        )

    def render_snapshot(self, *, clear_screen: bool = False) -> None:
        view = self.snapshot()
        if clear_screen:
            print("\033[2J\033[H", end="")
        self.render(
            "gateway=neural "
            f"queue=pending:{view.pending},delivered:{view.delivered},"
            f"acknowledged:{view.acknowledged},expired:{view.expired} "
            f"flow=authorized:{view.authorized},rejected:{view.rejected},"
            f"rate_limited:{view.rate_limited} "
            f"health={view.health},rejections:{view.rejection_count} "
            f"isolation={view.isolation} "
            f"audit={view.audit_action}/{view.audit_outcome} "
            f"last_topic={view.last_topic}"
        )


def _publish_and_render(
    monitor: GatewayMonitor, message: NeuralMessage, session, *, clear_screen: bool = False
) -> None:
    try:
        monitor.gateway.publish(message, session)
    except GatewayRejected:
        # The gateway has already recorded the safe reason; never echo details.
        pass
    monitor.render_snapshot(clear_screen=clear_screen)


def _governance_demo(
    gateway: NeuralSignalGateway, session, monitor: GatewayMonitor, *, clear_screen: bool = False
) -> None:
    """Exercise G1/G2 with synthetic, non-sensitive geometry facts."""
    clock = [0.0]
    gateway.flow_control = RateLimitPolicy(capacity=1, refill_per_second=1, clock=lambda: clock[0])
    gateway.health = PluginHealthMonitor(
        degraded_after_rejections=1,
        paused_after_rejections=2,
        quarantined_after_rejections=3,
        clock=lambda: clock[0],
    )
    template = NeuralMessage(
        kind=MessageKind.EVENT,
        source=session.plugin_id,
        topic="window.geometry_changed",
        payload_schema="window.geometry_changed@1",
        payload={"changes": []},
    )
    monitor.render("mode=governance-demo payload=redacted")
    for label, advance in (
        ("accepted", 0.0),
        ("rate_limited", 0.0),
        ("recovered", 1.0),
        ("paused", 0.0),
        ("isolated", 0.0),
    ):
        clock[0] += advance
        _publish_and_render(
            monitor,
            template.model_copy(update={"message_id": f"observer-{label}"}),
            session,
            clear_screen=clear_screen,
        )
    monitor.render("status=isolation decision=suppressed payload=redacted")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Observe safe central-gateway state.")
    parser.add_argument("manifest", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--window-snapshot", action="store_true")
    modes.add_argument("--governance-demo", action="store_true")
    parser.add_argument("--duration", type=float, default=0.0)
    parser.add_argument("--display-interval", type=float, default=1.0)
    parser.add_argument("--no-clear", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.duration < 0 or args.display_interval <= 0:
        parser.error("duration must be >= 0 and display interval must be positive")
    try:
        manifest = load_manifest(json.loads(args.manifest.read_text(encoding="utf-8")))
    except Exception:
        print("status=failed reason=manifest_invalid", flush=True)
        return 1
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
        gateway = NeuralSignalGateway(DurableEventQueue(Path(directory) / "signals.db"))
        gateway.register(manifest, PluginGrant.create(manifest.plugin_id, manifest.capabilities))
        session = gateway.open_session(manifest.plugin_id, "gateway-monitor", manifest.manifest_digest)
        monitor = GatewayMonitor(gateway, session.plugin_id, session.instance_id)
        peripheral = None
        try:
            if args.governance_demo:
                if "window.geometry_changed" not in manifest.capabilities:
                    parser.error("--governance-demo requires window.geometry_changed capability")
                _governance_demo(
                    gateway,
                    session,
                    monitor,
                    clear_screen=not args.no_clear and sys.stdout.isatty(),
                )
            elif args.window_snapshot:
                if manifest.plugin_id != "peripheral.window.activity":
                    parser.error("--window-snapshot requires the built-in window activity manifest")
                from src.sensing.window_activity import WindowActivityPeripheral

                peripheral = WindowActivityPeripheral()
                deadline = time.monotonic() + args.duration if args.duration else None
                while deadline is None or time.monotonic() < deadline:
                    for message in peripheral.collect_messages():
                        _publish_and_render(
                            monitor,
                            message,
                            session,
                            clear_screen=not args.no_clear and sys.stdout.isatty(),
                        )
                    time.sleep(args.display_interval)
            else:
                monitor.render_snapshot(clear_screen=not args.no_clear and sys.stdout.isatty())
        except KeyboardInterrupt:
            monitor.render("status=stopped reason=operator_interrupt")
            return_code = 0
        except Exception:
            # Never expose traceback or exception text from an untrusted plugin,
            # sensor, renderer, or manifest-derived object.
            monitor.render("status=failed reason=observer_runtime_error")
            return_code = 1
        else:
            return_code = 0
        finally:
            if peripheral is not None:
                try:
                    peripheral.stop()
                except Exception:
                    return_code = 1
                    try:
                        monitor.render("status=failed reason=observer_runtime_error")
                    except Exception:
                        pass
        # Windows can retain SQLite handles until reference cycles are collected.
        # Release the queue/gateway before TemporaryDirectory removes its files.
        del monitor, session, gateway
        gc.collect()
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
