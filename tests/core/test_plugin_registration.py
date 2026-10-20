from datetime import timedelta

import pytest

from src.core.gateway_errors import GatewayRejected, GatewayRejectionCode
from src.core.neural_message import PrivacyClass, utc_now
from src.core.plugin_manifest import load_manifest
from src.core.plugin_registration import PluginGrant, RegistrationRegistry


@pytest.fixture
def manifest():
    return load_manifest({
        "plugin_id": "peripheral.example", "version": "1.0.0", "protocol_version": "1.0",
        "runtime": {"kind": "python", "entrypoint": "example:Plugin"},
        "capabilities": ["example.changed"], "signal_schemas": ["example.changed@1"],
        "permissions": [], "privacy": {"classification": "metadata_only"},
    })


def test_registration_rejects_grant_topics_not_declared_by_manifest(manifest):
    registry = RegistrationRegistry()
    with pytest.raises(GatewayRejected) as rejected:
        registry.register(manifest, PluginGrant.create(manifest.plugin_id, {"other.topic"}))
    assert rejected.value.code is GatewayRejectionCode.MANIFEST_INVALID


def test_sessions_bind_manifest_instance_and_expiry(manifest):
    registry = RegistrationRegistry(session_ttl_seconds=1)
    registry.register(manifest, PluginGrant.create(manifest.plugin_id, {"example.changed"}))
    now = utc_now()
    session = registry.open_session(manifest.plugin_id, "instance-a", manifest.manifest_digest, now=now)

    assert registry.validate_session(session, now=now)[0] == manifest
    with pytest.raises(GatewayRejected) as rejected:
        registry.validate_session(session, now=now + timedelta(seconds=2))
    assert rejected.value.code is GatewayRejectionCode.SESSION_INVALID


def test_registration_rejects_grant_privacy_above_manifest_and_duplicate_instance(manifest):
    registry = RegistrationRegistry()
    with pytest.raises(GatewayRejected) as rejected:
        registry.register(manifest, PluginGrant.create(manifest.plugin_id, {"example.changed"},
                                                       maximum_privacy=PrivacyClass.SENSITIVE))
    assert rejected.value.code is GatewayRejectionCode.MANIFEST_INVALID

    registry.register(manifest, PluginGrant.create(manifest.plugin_id, {"example.changed"}))
    registry.open_session(manifest.plugin_id, "instance-a", manifest.manifest_digest)
    with pytest.raises(GatewayRejected) as rejected:
        registry.open_session(manifest.plugin_id, "instance-a", manifest.manifest_digest)
    assert rejected.value.code is GatewayRejectionCode.SESSION_INVALID
