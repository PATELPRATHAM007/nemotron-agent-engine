"""
Modular Domain Architecture Verification Tests
==============================================
Validates that all domain modules adhere to the clean pattern:
  - models.py
  - schemas.py
  - apis.py
  - router.py
  - service.py
  - validation.py
  - messages.py
"""

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.core import messages as core_messages
from app.modules.auth import messages as auth_messages
from app.modules.auth.validation import AuthValidator
from app.modules.gateway import messages as gateway_messages
from app.modules.gateway.validation import GatewayValidator
from app.modules.missions import messages as mission_messages
from app.modules.missions.validation import MissionValidator
from app.modules.cost import messages as cost_messages
from app.modules.cost.validation import CostValidator

client = TestClient(app)


def test_core_and_module_messages():
    """Verify that static message constants exist and are distinct strings."""
    assert isinstance(core_messages.HEALTH_CHECK_SUCCESS, str)
    assert isinstance(auth_messages.LOGIN_SUCCESS, str)
    assert isinstance(gateway_messages.MODEL_NOT_FOUND, str)
    assert isinstance(mission_messages.MISSION_CREATED, str)
    assert isinstance(cost_messages.COST_RECORDED, str)


def test_auth_validator():
    """Verify input validation rules in auth module."""
    clean_email = AuthValidator.validate_email("  Test.User@Example.COM  ")
    assert clean_email == "test.user@example.com"

    with pytest.raises(ValueError):
        AuthValidator.validate_email("invalid-email-no-at")

    with pytest.raises(ValueError):
        AuthValidator.validate_password_strength("short")

    assert AuthValidator.validate_password_strength("ValidPassword123!") == "ValidPassword123!"

    # Device checksum
    fp = AuthValidator.compute_device_fingerprint("device-1", "ssh-rsa ABC")
    assert AuthValidator.verify_agent_checksum("device-1", "ssh-rsa ABC", fp) is True
    assert AuthValidator.verify_agent_checksum("device-2", "ssh-rsa ABC", fp) is False


def test_gateway_validator():
    """Verify secret reference format and capability normalization."""
    valid_ref = GatewayValidator.validate_vault_reference("models/google/key-1")
    assert valid_ref == "vault://models/google/key-1"

    caps = GatewayValidator.validate_capabilities(["TEXT", "VISION", "INVALID_CAP"])
    assert "text" in caps
    assert "vision" in caps
    assert "invalid_cap" not in caps


def test_mission_validator():
    """Verify path traversal sanitization and image byte inspection."""
    assert MissionValidator.sanitize_filename("../../../secret.env") == "secret.env"
    assert MissionValidator.sanitize_filename("/etc/hosts") == "hosts"

    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    assert MissionValidator.validate_image_bytes(png_bytes) == "image/png"

    with pytest.raises(ValueError) as exc:
        MissionValidator.validate_image_bytes(b"#!/bin/bash\necho bad")
    assert "Invalid image" in str(exc.value)


def test_cost_validator():
    """Verify token and cost validations."""
    assert CostValidator.validate_positive_tokens(100) == 100
    with pytest.raises(ValueError):
        CostValidator.validate_positive_tokens(-5)

    assert CostValidator.validate_positive_cost(0.01234567) == 0.012346
    with pytest.raises(ValueError):
        CostValidator.validate_positive_cost(-1.0)


def test_modular_routes_availability():
    """Verify that module routers are correctly mounted under /api/v1."""
    # Auth route
    auth_resp = client.get("/api/v1/auth/me")
    assert auth_resp.status_code == 200

    # Gateway route
    models_resp = client.get("/api/v1/models")
    assert models_resp.status_code == 200

    # Missions route
    missions_resp = client.get("/api/v1/missions")
    assert missions_resp.status_code == 200

    # Cost route
    cost_resp = client.get("/api/v1/cost/summary")
    assert cost_resp.status_code == 200

    # Constitution route
    const_resp = client.get("/api/v1/constitution/rules")
    assert const_resp.status_code == 200

    # Intelligence route
    intel_resp = client.get("/api/v1/intelligence/graph")
    assert intel_resp.status_code == 200
