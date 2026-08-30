"""Mock Storage Sensory Nerve Plugin (BNP v1.0 Reference Implementation)

This plugin demonstrates how to implement a standard Biomimetic Nerve Protocol (BNP)
compliant sensor plugin that emits JSON-RPC / SomaticPulse events via standard IO.
"""

from datetime import datetime, timezone
import json
import sys
import time


def emit_pulse(pulse_id: str, headline: str, context: dict) -> None:
    """Emit a somatic pulse formatted in BNP v1.0 specification."""
    pulse = {
        "jsonrpc": "2.0",
        "method": "nerve/pulse",
        "params": {
            "pulse_id": pulse_id,
            "nerve_id": "nerve.example.mock_storage",
            "channel": "TACTILE_STORAGE",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "headline": headline,
            "semantic_context": context,
        },
    }
    # Output to stdout with immediate flush
    sys.stdout.write(json.dumps(pulse, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> None:
    """Main lifecycle entrypoint for BNP plugin."""
    # Send ready signal
    ready_signal = {
        "jsonrpc": "2.0",
        "method": "nerve/ready",
        "params": {
            "nerve_id": "nerve.example.mock_storage",
            "status": "ACTIVE",
            "version": "1.0.0",
        },
    }
    sys.stdout.write(json.dumps(ready_signal, ensure_ascii=False) + "\n")
    sys.stdout.flush()

    # Simulate emitting a pulse
    emit_pulse(
        pulse_id=f"pulse_mock_{int(time.time()*1000)}",
        headline="MOCK_DEVICE_DISCOVERED",
        context={"device_name": "Demo SanDisk Flash Drive", "capacity_gb": 64.0, "status": "ONLINE"},
    )


if __name__ == "__main__":
    main()
