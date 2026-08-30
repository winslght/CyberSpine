# CyberSpine

CyberSpine is engineering a Windows-local perception and controlled-context foundation from an earlier proof of concept (PoC). The new mainline turns facts within the user's authorized scope into structured context that an upper-level AI agent can read through MCP. Any desktop action requires explicit user approval.

> **Engineering status.** The retained `perceptors → pacing → app → mcp` system, cockpit, and multi-perceptor implementation are PoC material, not the production mainline. New capabilities belong only on the unified-message mainline: `sensing → core → context → adapters/apps → actions`. Legacy modules may serve only as compatibility adapters or behavioral acceptance references. See [`docs/current/PROJECT_DIRECTION.md`](docs/current/PROJECT_DIRECTION.md).

## The current engineering-demo loop

```text
Windows signals → structured context → MCP read → user approval → limited desktop action
```

The first engineering vertical slice focuses on privacy-bounded window facts. It turns the PoC product direction into a maintainable, auditable minimal loop; it is not an autonomous desktop controller.

## Quick start

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/demo_minimal_loop.py
```

Run tests:

```powershell
python -m pytest
```

The cockpit and wider sensor/model experiments remain in the repository, but are not part of the demo's release contract.

## Documentation

- [Demo scope and acceptance criteria](docs/current/DEMO_SCOPE.md)
- [Development and testing](docs/current/DEVELOPMENT.md)
- [Documentation index](docs/INDEX.md)
- [Archived historical material](docs/archive/legacy_2026-08-29/)
