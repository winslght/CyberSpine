"""Registration and short-lived session issuance for already-verified manifests."""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

from .gateway_errors import GatewayRejected, GatewayRejectionCode
from .neural_message import MessageKind, PrivacyClass, utc_now
from .plugin_manifest import PluginManifest

_PRIVACY_ORDER = {PrivacyClass.PUBLIC: 0, PrivacyClass.METADATA_ONLY: 1,
                  PrivacyClass.SENSITIVE: 2, PrivacyClass.RESTRICTED: 3}


@dataclass(frozen=True)
class PluginGrant:
    plugin_id: str
    topics: frozenset[str]
    kinds: frozenset[MessageKind] = frozenset({MessageKind.STATE, MessageKind.EVENT, MessageKind.HEALTH})
    maximum_privacy: PrivacyClass = PrivacyClass.METADATA_ONLY

    @classmethod
    def create(cls, plugin_id: str, topics: Iterable[str], kinds: Iterable[MessageKind] | None = None,
               maximum_privacy: PrivacyClass = PrivacyClass.METADATA_ONLY) -> "PluginGrant":
        return cls(plugin_id, frozenset(topics), frozenset(kinds) if kinds is not None else cls.kinds,
                   maximum_privacy)


@dataclass(frozen=True)
class PluginSession:
    plugin_id: str
    instance_id: str
    session_id: str
    token: str
    manifest_digest: str
    expires_at: datetime

    def is_expired(self, now: datetime | None = None) -> bool:
        return self.expires_at <= (now or utc_now())


class RegistrationRegistry:
    """In-memory registry; persistence and process lifecycle belong to adapters."""

    def __init__(self, session_ttl_seconds: int = 300) -> None:
        if session_ttl_seconds <= 0:
            raise ValueError("session_ttl_seconds must be positive")
        self._session_ttl_seconds = session_ttl_seconds
        self._registrations: dict[str, tuple[PluginManifest, PluginGrant]] = {}
        self._sessions: dict[str, PluginSession] = {}

    def register(self, manifest: PluginManifest, grant: PluginGrant) -> None:
        if manifest.plugin_id != grant.plugin_id:
            raise GatewayRejected(GatewayRejectionCode.MANIFEST_INVALID, "grant plugin_id differs")
        if not grant.topics or not grant.topics.issubset(manifest.capabilities):
            raise GatewayRejected(GatewayRejectionCode.MANIFEST_INVALID, "grant topics exceed manifest")
        if not grant.kinds.issubset({MessageKind.STATE, MessageKind.EVENT, MessageKind.HEALTH}):
            raise GatewayRejected(GatewayRejectionCode.MANIFEST_INVALID, "peripheral kinds are invalid")
        if not isinstance(grant.maximum_privacy, PrivacyClass):
            raise GatewayRejected(GatewayRejectionCode.MANIFEST_INVALID, "unknown privacy class")
        if _PRIVACY_ORDER[grant.maximum_privacy] > _PRIVACY_ORDER[manifest.privacy.classification]:
            raise GatewayRejected(GatewayRejectionCode.MANIFEST_INVALID, "grant privacy exceeds manifest")
        self._registrations[manifest.plugin_id] = (manifest, grant)
        self._sessions = {key: value for key, value in self._sessions.items() if value.plugin_id != manifest.plugin_id}

    def registration_for(self, plugin_id: str) -> tuple[PluginManifest, PluginGrant] | None:
        return self._registrations.get(plugin_id)

    def open_session(self, plugin_id: str, instance_id: str, manifest_digest: str,
                     now: datetime | None = None) -> PluginSession:
        if not instance_id.strip():
            raise GatewayRejected(GatewayRejectionCode.SESSION_INVALID, "empty instance_id")
        registered = self._registrations.get(plugin_id)
        if registered is None or registered[0].manifest_digest != manifest_digest:
            raise GatewayRejected(GatewayRejectionCode.SESSION_INVALID, "unregistered manifest")
        current = now or utc_now()
        if any(item.plugin_id == plugin_id and item.instance_id == instance_id and not item.is_expired(current)
               for item in self._sessions.values()):
            raise GatewayRejected(GatewayRejectionCode.SESSION_INVALID, "instance already has an active session")
        session = PluginSession(plugin_id, instance_id, secrets.token_urlsafe(16), secrets.token_urlsafe(32),
                                manifest_digest, current + timedelta(seconds=self._session_ttl_seconds))
        self._sessions[session.session_id] = session
        return session

    def validate_session(self, session: PluginSession, now: datetime | None = None) -> tuple[PluginManifest, PluginGrant]:
        stored = self._sessions.get(session.session_id)
        if stored is None or not secrets.compare_digest(stored.token, session.token) or stored != session:
            raise GatewayRejected(GatewayRejectionCode.SESSION_INVALID, "unknown session")
        if stored.is_expired(now):
            self._sessions.pop(stored.session_id, None)
            raise GatewayRejected(GatewayRejectionCode.SESSION_INVALID, "expired session")
        return self._registrations[stored.plugin_id]
