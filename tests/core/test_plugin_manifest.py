import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.core.plugin_manifest import load_manifest


def test_window_manifest_is_accepted_as_a_data_only_python_manifest():
    root = Path(__file__).resolve().parents[2]
    data = json.loads((root / "plugins" / "builtin" / "window_activity" / "manifest.json").read_text(encoding="utf-8"))

    manifest = load_manifest(data)

    assert manifest.plugin_id == "peripheral.window.activity"
    assert manifest.runtime.kind == "python"
    assert manifest.runtime.entrypoint == data["entrypoint"]
    assert "window.geometry_changed" in manifest.capabilities
    assert len(manifest.manifest_digest) == 64


@pytest.mark.parametrize("command", [["../evil"], ["C:\\plugin.exe"], ["C:plugin.exe"],
                                      ["\\\\server\\share\\plugin.exe"], ["/plugin"],
                                      ["https://example.invalid/plugin.exe"], ["plugin.exe;evil"],
                                      ["plugin.exe|evil"]])
def test_process_manifest_rejects_host_absolute_or_parent_traversal_command(command):
    data = {
        "plugin_id": "peripheral.example",
        "version": "1.0.0",
        "protocol_version": "1.0",
        "runtime": {"kind": "process", "command": command, "transport": "cyberspine-jsonl@1"},
        "capabilities": ["example.changed"],
        "signal_schemas": ["example.changed@1"],
        "permissions": [],
        "privacy": {"classification": "metadata_only"},
    }

    with pytest.raises(ValidationError, match="package-relative"):
        load_manifest(data)


def test_manifest_digest_is_computed_and_cannot_be_supplied():
    data = {
        "plugin_id": "peripheral.example", "version": "1.0.0", "protocol_version": "1.0",
        "runtime": {"kind": "python", "entrypoint": "example:Plugin"},
        "capabilities": ["example.changed"], "signal_schemas": ["example.changed@1"],
        "permissions": [], "privacy": {"classification": "metadata_only"}, "manifest_digest": "forged",
    }
    with pytest.raises(ValueError, match="computed"):
        load_manifest(data)


def test_manifest_requires_schema_for_every_declared_capability():
    data = {
        "plugin_id": "peripheral.example",
        "version": "1.0.0",
        "protocol_version": "1.0",
        "runtime": {"kind": "python", "entrypoint": "example:Plugin"},
        "capabilities": ["example.one", "example.two"],
        "signal_schemas": ["example.one@1"],
        "permissions": [],
        "privacy": {"classification": "metadata_only"},
    }

    with pytest.raises(ValidationError, match="exactly one schema"):
        load_manifest(data)
