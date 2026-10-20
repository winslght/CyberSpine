"""Data-only contract for plugins before any runtime loads or executes them."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePath, PurePosixPath, PureWindowsPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .neural_message import PrivacyClass

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_VERSION = re.compile(r"^\d+\.\d+(?:\.\d+)?(?:[-+][0-9A-Za-z.-]+)?$")


def _is_safe_package_relative_command_part(part: str) -> bool:
    """Reject host-specific absolute paths before a runtime adapter can resolve them."""
    if not part or "\x00" in part or "://" in part or any(char in part for char in ";|&<>$"):
        return False
    paths = (PurePath(part), PurePosixPath(part), PureWindowsPath(part))
    return all(not path.is_absolute() and not path.drive and not path.root and ".." not in path.parts for path in paths)


class PluginRuntimeSpec(BaseModel):
    """Language-neutral runtime declaration; it is not an execution request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["python", "process"]
    entrypoint: str | None = None
    command: tuple[str, ...] = ()
    transport: str | None = None

    @model_validator(mode="after")
    def validate_runtime(self) -> "PluginRuntimeSpec":
        if self.kind == "python":
            if not self.entrypoint or ":" not in self.entrypoint:
                raise ValueError("python runtime requires module:object entrypoint")
            if self.command or self.transport:
                raise ValueError("python runtime cannot declare command or transport")
        else:
            if not self.command or any(not _is_safe_package_relative_command_part(part) for part in self.command):
                raise ValueError("process command must use non-empty package-relative parts")
            if self.transport != "cyberspine-jsonl@1":
                raise ValueError("process runtime requires cyberspine-jsonl@1 transport")
            if self.entrypoint:
                raise ValueError("process runtime cannot declare a python entrypoint")
        return self


class PluginPrivacySpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    classification: PrivacyClass
    never_collect: tuple[str, ...] = ()


class PluginManifest(BaseModel):
    """Verified declaration. Actual permissions are supplied separately by a grant."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plugin_id: str
    display_name: str | None = None
    version: str
    protocol_version: str
    runtime: PluginRuntimeSpec
    platforms: frozenset[str] = Field(default_factory=frozenset)
    capabilities: frozenset[str] = Field(min_length=1)
    signal_schemas: frozenset[str] = Field(min_length=1)
    permissions: frozenset[str] = Field(default_factory=frozenset)
    privacy: PluginPrivacySpec
    sensing_profile: dict[str, Any] = Field(default_factory=dict)
    manifest_digest: str

    @field_validator("plugin_id")
    @classmethod
    def validate_plugin_id(cls, value: str) -> str:
        if not _IDENTIFIER.fullmatch(value):
            raise ValueError("plugin_id must be a stable dotted identifier")
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if not _VERSION.fullmatch(value):
            raise ValueError("version must be a semantic version")
        return value

    @field_validator("protocol_version")
    @classmethod
    def validate_protocol_version(cls, value: str) -> str:
        if value != "1.0":
            raise ValueError("protocol_version is not supported")
        return value

    @field_validator("capabilities", "signal_schemas", "permissions")
    @classmethod
    def validate_identifiers(cls, values: frozenset[str]) -> frozenset[str]:
        if any(not value.strip() for value in values):
            raise ValueError("identifiers must not be empty")
        return values

    @model_validator(mode="after")
    def validate_schemas(self) -> "PluginManifest":
        schema_topics = {schema.rsplit("@", 1)[0] for schema in self.signal_schemas if "@" in schema}
        if len(schema_topics) != len(self.signal_schemas) or schema_topics != set(self.capabilities):
            raise ValueError("signal_schemas must provide exactly one schema for each capability")
        return self


def load_manifest(data: dict[str, Any]) -> PluginManifest:
    """Validate manifest data without reading files, resolving paths, or starting code."""
    if "manifest_digest" in data:
        raise ValueError("manifest_digest is computed by the gateway and must not be supplied")
    normalized = dict(data)
    if "runtime" not in normalized:
        entrypoint = normalized.pop("entrypoint", None)
        if entrypoint is not None:
            normalized["runtime"] = {"kind": "python", "entrypoint": entrypoint}
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    normalized["manifest_digest"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return PluginManifest.model_validate(normalized)
