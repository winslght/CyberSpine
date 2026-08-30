# CyberSpine

CyberSpine is a Windows-local perception experiment. It turns the current desktop state into structured context that an upper-level AI agent can read through MCP. Any desktop action requires explicit user approval.

## The current demo loop

```text
Windows signals → structured context → MCP read → user approval → limited desktop action
```

The demo focuses on foreground context, basic system health, shallow workspace/storage information, and privacy-conscious clipboard classification. It validates whether local system awareness can provide useful and safe context to an AI agent; it is not an autonomous desktop controller.

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
