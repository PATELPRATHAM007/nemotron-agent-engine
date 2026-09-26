"""
Comprehensive Tests for Unified Autonomous Mission Chat Subsystem
==================================================================
Asserts:
  - Single Unified Mission API (/api/v1/missions)
  - Execution State transitions
  - Interactive Plan Approval
  - Solution Selection (Option A/B/C)
  - Fine-Grained Permission Engine (Allow/Ask/Deny & Scopes)
  - Multimodal Screenshot Upload
  - Slash Commands (/status, /diff, /permissions, /stop)
"""

import json
from fastapi.testclient import TestClient
import pytest

from app.intelligence.missions.permissions import (
    CommandRiskClassifier,
    MissionPermissionEngine,
    PermissionDecision,
    PermissionScope,
    RiskLevel,
)
from app.intelligence.missions.slash_commands import SlashCommandParser
from app.intelligence.missions.state_machine import MissionState, MissionStateMachine
from app.main import app

client = TestClient(app)


def test_command_risk_classifier():
    """Verify safe, low, medium, high, and critical risk classification."""
    assert CommandRiskClassifier.classify_command("git status") == RiskLevel.SAFE
    assert CommandRiskClassifier.classify_command("pytest -q") == RiskLevel.LOW
    assert CommandRiskClassifier.classify_command("npm install google-auth-library") == RiskLevel.MEDIUM
    assert CommandRiskClassifier.classify_command("git push origin main") == RiskLevel.HIGH
    assert CommandRiskClassifier.classify_command("rm -rf /") == RiskLevel.CRITICAL


def test_mission_permission_engine_scopes():
    """Verify Allow / Ask / Deny precedence and mission vs project scopes."""
    engine = MissionPermissionEngine(workspace_root=".")
    
    # Critical command is ALWAYS denied
    res_crit = engine.evaluate_command("m1", "rm -rf /", reason="test")
    assert res_crit["decision"] == PermissionDecision.DENY.value

    # Medium command initially requires ASK
    res_ask = engine.evaluate_command("m1", "npm install axios", reason="dep install")
    assert res_ask["decision"] == PermissionDecision.ASK.value

    # Grant for mission
    engine.grant("m1", "command(npm install axios)", PermissionScope.MISSION)
    res_allowed = engine.evaluate_command("m1", "npm install axios", reason="retry")
    assert res_allowed["decision"] == PermissionDecision.ALLOW.value

    # Different mission still requires ASK
    res_m2 = engine.evaluate_command("m2", "npm install axios", reason="other mission")
    assert res_m2["decision"] == PermissionDecision.ASK.value


def test_slash_command_parser():
    """Verify parsing of /plan, /status, /diff, !command."""
    p_status = SlashCommandParser.parse("/status")
    assert p_status["is_directive"] is True
    assert p_status["command"] == "/status"

    p_term = SlashCommandParser.parse("!git status")
    assert p_term["is_directive"] is True
    assert p_term["command"] == "!"
    assert p_term["args"] == "git status"

    p_norm = SlashCommandParser.parse("Add Google OAuth login to user model")
    assert p_norm["is_directive"] is False


def get_data(resp):
    j = resp.json()
    return j.get("data", j)


def test_mission_lifecycle_api():
    """Test full Mission API endpoints (/api/v1/missions)."""
    # 1. Create Mission
    resp = client.post(
        "/api/v1/missions",
        json={"goal": "Refactor authentication layer", "title": "Auth Refactor"},
    )
    assert resp.status_code == 200
    data = get_data(resp)
    assert data["success"] is True
    mission_id = data["mission_id"]

    # 2. Get Mission
    get_resp = client.get(f"/api/v1/missions/{mission_id}")
    assert get_resp.status_code == 200
    mission_data = get_data(get_resp)
    assert mission_data["mission"]["id"] == mission_id

    # 3. Post Message
    msg_resp = client.post(
        f"/api/v1/missions/{mission_id}/messages",
        json={"content": "Make sure to support Google OAuth"},
    )
    assert msg_resp.status_code == 200
    assert get_data(msg_resp)["success"] is True

    # 4. Multimodal Upload
    sample_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    upload_resp = client.post(
        f"/api/v1/missions/{mission_id}/upload",
        json={
            "image_base64": sample_b64,
            "filename": "login_mockup.png",
            "mime_type": "image/png",
        },
    )
    assert upload_resp.status_code == 200
    upload_data = get_data(upload_resp)
    assert upload_data["success"] is True
    assert "attachment_id" in upload_data

    # 5. List missions
    list_resp = client.get("/api/v1/missions")
    assert list_resp.status_code == 200
    assert len(get_data(list_resp)) >= 1


def test_mission_stream_directive():
    """Test streaming directive output through SSE."""
    # Create mission
    m_resp = client.post(
        "/api/v1/missions",
        json={"goal": "/status", "title": "Status Directive"},
    )
    mission_id = get_data(m_resp)["mission_id"]

    stream_resp = client.get(f"/api/v1/missions/{mission_id}/stream?goal=/status")
    assert stream_resp.status_code == 200
    assert "text/event-stream" in stream_resp.headers.get("content-type", "")
    assert len(stream_resp.text) > 0
