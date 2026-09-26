"""
Comprehensive Security, Identity, Policy Engine, and Model Gateway Test Suite
=============================================================================
Tests:
  1. Argon2id Password Hashing & User Registration
  2. Authentication & Short-lived JWT Issuance + HttpOnly Session Cookie
  3. Refresh Token Rotation & Family Reuse Revocation (RFC 6749 / 9700)
  4. Session Lifecycle & Remote Revocation
  5. PolicyEngine Authorization (RBAC, ABAC, DENY > ASK > ALLOW Precedence, Tenant Isolation)
  6. SecretManager KMS Envelope Encryption & SecretRedactor Scrubbing
  7. SSRF Protection Filter (DNS resolution & IP range blocking)
  8. Local Execution Agent Identity & Capabilities Registration
  9. Model Gateway Routing, Capability Authorization, and Usage Accounting
 10. File Upload Safety (Magic-byte validation & Path Traversal Prevention)
"""

import base64
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import DatabaseService
from app.security.auth import auth_service
from app.security.context import AuthContext, ModelAccessContext
from app.security.policy_engine import policy_engine
from app.security.secrets import secret_manager, secret_redactor
from app.security.ssrf import ssrf_filter
from app.security.auditing import security_audit
from app.gateway.gateway import model_gateway
from app.gateway.models import ModelProvider, RegisteredModel, ModelCredential
from app.intelligence.missions.multimodal import multimodal_storage


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# =============================================================================
# 1. Argon2id Password Hashing & Registration
# =============================================================================
def test_argon2id_password_hashing():
    raw_password = "SuperSecretSecurePassword2026!"
    hashed = auth_service.hash_password(raw_password)

    # Must be standard Argon2id hash format
    assert hashed.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert auth_service.verify_password(raw_password, hashed) is True
    assert auth_service.verify_password("WrongPassword123!", hashed) is False


def test_user_registration_and_duplicate_prevention(client: TestClient):
    unique_email = f"eng_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "password": "PasswordWithLength123!",
        "full_name": "Test Engineer",
        "tenant_id": "tenant-alpha",
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json().get("data", resp.json())
    assert data["success"] is True
    assert data["email"] == unique_email
    assert "user_id" in data

    # Attempt duplicate registration with same email
    dup_resp = client.post("/api/v1/auth/register", json=payload)
    assert dup_resp.status_code == 400


# =============================================================================
# 2. Authentication, Short-lived JWT & HttpOnly Session Cookie
# =============================================================================
def test_login_success_and_cookie_issuance(client: TestClient):
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "CorrectHorseBatteryStaple1!"
    client.post("/api/v1/auth/register", json={"email": email, "password": password, "tenant_id": "tenant-alpha"})

    # Failed login
    fail_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPassword!"})
    assert fail_resp.status_code == 401

    # Successful login
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200
    data = login_resp.json().get("data", login_resp.json())
    assert data["success"] is True
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == 900  # 15 minutes short-lived

    # Verify session cookie was set
    assert "nemotron_session" in login_resp.cookies

    # Validate access token claims
    claims = auth_service.verify_access_token(data["access_token"])
    assert claims["sub"] == data["user"]["id"]
    assert claims["tenant_id"] == "tenant-alpha"
    assert "DEVELOPER" in claims["roles"]


# =============================================================================
# 3. Refresh Token Rotation & Family Reuse Detection (RFC 6749 / 9700)
# =============================================================================
def test_refresh_token_rotation_and_family_reuse_prevention(client: TestClient):
    email = f"refresh_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword123!"
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    login_data = login_resp.json().get("data", login_resp.json())
    rt1 = login_data["refresh_token"]

    # 1st rotation: rt1 -> rt2
    refresh_resp1 = client.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
    assert refresh_resp1.status_code == 200
    ref_data1 = refresh_resp1.json().get("data", refresh_resp1.json())
    rt2 = ref_data1["refresh_token"]
    assert rt2 != rt1
    assert "access_token" in ref_data1

    # 2nd rotation: rt2 -> rt3
    refresh_resp2 = client.post("/api/v1/auth/refresh", json={"refresh_token": rt2})
    assert refresh_resp2.status_code == 200
    ref_data2 = refresh_resp2.json().get("data", refresh_resp2.json())
    rt3 = ref_data2["refresh_token"]
    assert rt3 != rt2

    # Family Reuse Breach Simulation: Replay rt1 (already used!)
    # Must be rejected with 401 and trigger family revocation
    reuse_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
    assert reuse_resp.status_code == 401
    err_str = str(reuse_resp.json()).lower()
    assert "reuse" in err_str or "revoked" in err_str or "terminated" in err_str


# =============================================================================
# 4. Session Lifecycle & Remote Revocation
# =============================================================================
def test_session_listing_and_remote_revocation(client: TestClient):
    email = f"sess_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword123!"
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    data = login_resp.json().get("data", login_resp.json())
    access_token = data["access_token"]
    session_id = data["session_id"]

    headers = {"Authorization": f"Bearer {access_token}"}
    profile_resp = client.get("/api/v1/auth/me", headers=headers)
    assert profile_resp.status_code == 200
    profile = profile_resp.json().get("data", profile_resp.json())
    assert profile["session_id"] == session_id

    # Revoke session
    del_resp = client.delete(f"/api/v1/auth/sessions/{session_id}", headers=headers)
    assert del_resp.status_code == 200
    del_data = del_resp.json().get("data", del_resp.json())
    assert del_data["status"] == "REVOKED"


# =============================================================================
# 5. Policy Engine Authorization (RBAC, ABAC, DENY > ASK > ALLOW, Tenant)
# =============================================================================
def test_policy_engine_precedence_and_permissions():
    dev_context = AuthContext(
        user_id="user-dev-1",
        organization_id="org-alpha",
        project_id="proj-1",
        roles=("DEVELOPER",),
        scopes=("repository.read", "repository.write", "model.use"),
    )

    # 1. Developer is allowed repository.read on their project
    decision = policy_engine.authorize(
        subject=dev_context,
        action="repository.read",
        resource={"type": "project", "id": "proj-1", "organization_id": "org-alpha"},
    )
    assert decision.allowed is True

    # 2. Multi-tenant isolation: Developer cannot access project in org-beta
    tenant_mismatch = policy_engine.authorize(
        subject=dev_context,
        action="repository.read",
        resource={"type": "project", "id": "proj-999", "organization_id": "org-beta"},
    )
    assert tenant_mismatch.allowed is False
    assert tenant_mismatch.decision == "DENY"

    # 3. Dangerous command git.force_push is always DENIED by default
    force_push = policy_engine.authorize(
        subject=dev_context,
        action="git.force_push",
        resource={"type": "project", "id": "proj-1", "organization_id": "org-alpha"},
    )
    assert force_push.allowed is False
    assert force_push.decision == "DENY"

    # 4. Destructive production database operations require explicit human approval (ASK)
    db_drop = policy_engine.authorize(
        subject=dev_context,
        action="database.migrate",
        resource={"type": "database", "id": "prod-db", "organization_id": "org-alpha"},
        environment="production",
        is_destructive=True,
    )
    assert db_drop.decision in ("ASK", "DENY")


# =============================================================================
# 6. SecretManager KMS Envelope & SecretRedactor Scrubbing
# =============================================================================
def test_secret_manager_and_redaction():
    # Test secret storage and KMS envelope retrieval
    ref = secret_manager.store_secret("models/test/key-1", "sk-live-1234567890abcdef")
    assert ref.startswith("vault://models/test/key-1")
    resolved = secret_manager.resolve_secret(ref)
    assert resolved == "sk-live-1234567890abcdef"

    # Test SecretRedactor
    sensitive_log = (
        "Calling provider with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-ID and "
        "api_key=sk-proj-abc123456789012345678901234567890 and password='MySecretPassword!'"
    )
    redacted = secret_redactor.redact_text(sensitive_log)
    assert "sk-proj-abc123456789012345678901234567890" not in redacted
    assert "Bearer [REDACTED_TOKEN]" in redacted or "[REDACTED" in redacted
    assert "[REDACTED" in redacted

    # Dictionary redaction
    payload = {
        "user": "alice",
        "api_key": "AIzaSyD-1234567890abcdefghijklmnopqrst",
        "database_url": "postgresql://admin:secretPass@localhost:5432/proddb",
    }
    clean_dict = secret_redactor.redact_dict(payload)
    assert clean_dict["api_key"] == "[REDACTED_SECRET]"
    assert "secretPass" not in str(clean_dict["database_url"])


# =============================================================================
# 7. SSRF Protection Filter
# =============================================================================
def test_ssrf_filter_blocking_private_and_metadata_targets():
    # Loopback addresses
    assert ssrf_filter.is_safe_url("http://127.0.0.1:8000/api") is False
    assert ssrf_filter.is_safe_url("http://localhost:5000/secret") is False
    assert ssrf_filter.is_safe_url("http://0.0.0.0:80") is False

    # Cloud metadata endpoint (AWS / GCP / Azure)
    assert ssrf_filter.is_safe_url("http://169.254.169.254/latest/meta-data/") is False

    # Private RFC 1918 subnets
    assert ssrf_filter.is_safe_url("http://10.0.0.1/admin") is False
    assert ssrf_filter.is_safe_url("http://172.16.5.10/internal") is False
    assert ssrf_filter.is_safe_url("http://192.168.1.1/router") is False

    # File / Gopher / Unix socket schemes
    assert ssrf_filter.is_safe_url("file:///etc/passwd") is False
    assert ssrf_filter.is_safe_url("gopher://127.0.0.1:70") is False

    # Legitimate external HTTPS provider URLs
    assert ssrf_filter.is_safe_url("https://api.openai.com/v1/chat/completions") is True
    assert ssrf_filter.is_safe_url("https://generativelanguage.googleapis.com/v1beta/models") is True


# =============================================================================
# 8. Local Execution Agent Identity & Capabilities Registration
# =============================================================================
def test_agent_registration(client: TestClient):
    payload = {
        "name": "developer-laptop-agent",
        "project_id": "proj-core-repo",
        "device_id": f"device-{uuid.uuid4().hex[:8]}",
        "public_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExamplePublicKey...",
        "capabilities": {
            "terminal": True,
            "filesystem": True,
            "git": True,
            "docker": False,
            "browser": True,
        },
    }
    resp = client.post("/api/v1/auth/agents/register", json=payload)
    assert resp.status_code == 200
    data = resp.json().get("data", resp.json())
    assert data["success"] is True
    assert data["agent"]["name"] == "developer-laptop-agent"
    assert data["agent"]["capabilities"]["docker"] is False


# =============================================================================
# 9. Model Gateway Routing & Pipeline Execution
# =============================================================================
@pytest.mark.asyncio
async def test_model_gateway_execution_pipeline():
    auth_ctx = AuthContext(
        user_id="lead-engineer",
        organization_id="org-acme",
        project_id="proj-acme-api",
        roles=("DEVELOPER",),
        scopes=("model.use", "model.tools", "repository.read"),
    )

    # Execute stream turn through centralized Model Gateway
    events = []
    async for event in model_gateway.execute_stream(
        auth_context=auth_ctx,
        model_name="nemotron-dev",
        messages=[{"role": "user", "content": "Review the authentication middleware."}],
        mission_id="mission-sec-test",
    ):
        events.append(event)

    # Must contain token chunks and finish with complete or usage event
    assert len(events) > 0
    token_events = [e for e in events if e.get("type") in ("token", "content")]
    assert len(token_events) > 0
    assert any("response" in e.get("content", "").lower() or "audit" in str(e).lower() or len(e.get("content", "")) > 0 for e in token_events)


# =============================================================================
# 10. File Upload Safety (Magic Bytes & Path Traversal Prevention)
# =============================================================================
def test_file_upload_security():
    # 1. Path traversal sanitization: os.path.basename must sanitize ../../../../evil.png
    dirty_filename = "../../../../etc/passwd"
    sanitized = multimodal_storage.sanitize_filename(dirty_filename)
    assert "../" not in sanitized
    assert "/" not in sanitized
    assert sanitized == "passwd"

    # 2. Magic-byte verification: legitimate 1x1 PNG
    # 1x1 valid PNG base64
    valid_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    att = multimodal_storage.store_base64_attachment(
        base64_data=valid_png_b64,
        filename="screenshot.png",
        mime_type="image/png",
        mission_id="mission-upload-test",
    )
    assert att["id"] is not None
    assert att["file_size"] > 0

    # 3. Reject fake image containing executable/shell script disguised as png
    fake_png_b64 = base64.b64encode(b"#!/bin/bash\nrm -rf /").decode("utf-8")
    with pytest.raises(ValueError) as exc:
        multimodal_storage.store_base64_attachment(
            base64_data=fake_png_b64,
            filename="fake.png",
            mime_type="image/png",
        )
    assert "Invalid image file header" in str(exc.value)
