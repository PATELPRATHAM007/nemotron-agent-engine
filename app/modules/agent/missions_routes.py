"""
Unified Autonomous Mission API Endpoints
========================================
Exposes the single primary conversation & engineering API:
  - POST   /api/v1/missions                 (Create or dispatch turn)
  - GET    /api/v1/missions                 (List recent missions)
  - GET    /api/v1/missions/{id}            (Get mission details & status)
  - GET    /api/v1/missions/{id}/stream     (Unified SSE event stream)
  - POST   /api/v1/missions/{id}/messages   (Post message / instruction)
  - POST   /api/v1/missions/{id}/plan/approve (Approve plan)
  - POST   /api/v1/missions/{id}/selection  (Submit solution choice)
  - POST   /api/v1/missions/{id}/permissions(Submit permission grant/deny)
  - POST   /api/v1/missions/{id}/stop       (Cancel active execution)
  - POST   /api/v1/missions/{id}/rollback   (Revert changes)
  - POST   /api/v1/missions/{id}/upload     (Multimodal image attachment)
  - GET    /api/v1/missions/{id}/diff       (Get working tree diff)
  - GET    /api/v1/missions/{id}/artifacts  (Get generated artifacts)
"""

import json
from typing import Any
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.core.logging_config import get_logger
from app.intelligence.missions.multimodal import multimodal_storage
from app.intelligence.missions.permissions import (
    PermissionScope,
    mission_permissions,
)
from app.intelligence.missions.repository import mission_repository
from app.intelligence.missions.state_machine import MissionState
from app.modules.agent.unified_engine import unified_mission_engine
from app.security.context import AuthContext
from app.security.dependencies import get_current_auth_context

logger = get_logger(__name__)

router = APIRouter(prefix="/missions", tags=["Autonomous Missions"])


# -------------------------------------------------------------
# Request & Response Schemas
# -------------------------------------------------------------
class CreateMissionRequest(BaseModel):
    goal: str = Field(..., description="The objective or question for the autonomous agent")
    title: str | None = Field(None, description="Optional mission title")
    attachment_ids: list[str] = Field(default_factory=list, description="Associated image/screenshot IDs")
    execution_policy: dict[str, Any] = Field(
        default_factory=lambda: {"autonomy": "high", "review_policy": "interactive"}
    )


class MessageRequest(BaseModel):
    content: str = Field(..., description="Follow-up instruction, question, or approval")
    attachment_ids: list[str] = Field(default_factory=list)


class SelectionDecisionRequest(BaseModel):
    selection_id: str
    selected_option: str  # e.g. "A", "B", "C"


class PermissionDecisionRequest(BaseModel):
    request_id: str
    action: str  # "ALLOW" or "DENY"
    scope: str = "ONCE"  # "ONCE", "MISSION", "PROJECT", "ALWAYS"


class ImageUploadPayload(BaseModel):
    image_base64: str
    filename: str = "screenshot.png"
    mime_type: str = "image/png"


# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------
@router.post("")
async def create_mission(
    payload: CreateMissionRequest,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Create a new Autonomous Mission."""
    mission_id = str(uuid.uuid4())
    title = payload.title or payload.goal[:40]

    mission = mission_repository.create_mission(
        mission_id=mission_id,
        title=title,
        goal=payload.goal,
        execution_policy=payload.execution_policy,
    )

    return {
        "success": True,
        "mission_id": mission_id,
        "title": title,
        "goal": payload.goal,
        "status": mission.get("status", "IDLE"),
        "stream_url": f"/api/v1/missions/{mission_id}/stream?goal={payload.goal}",
    }


@router.get("")
async def list_missions(
    limit: int = Query(20, ge=1, le=100),
    auth: AuthContext = Depends(get_current_auth_context),
):
    """List historical and active autonomous missions."""
    return mission_repository.list_missions(limit=limit)


@router.get("/{mission_id}")
async def get_mission(
    mission_id: str,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Get mission details, status, checkpoints, and messages."""
    mission = mission_repository.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    messages = mission_repository.get_messages(mission_id)
    plan = mission_repository.get_latest_plan(mission_id)
    artifacts = mission_repository.get_artifacts(mission_id)
    return {
        "mission": mission,
        "messages": messages,
        "latest_plan": plan,
        "artifacts": artifacts,
    }


@router.get("/{mission_id}/stream")
async def stream_mission(
    mission_id: str,
    goal: str = Query(..., description="The objective or question for the agent"),
    attachments: str = Query("", description="Comma-separated attachment IDs"),
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Unified Server-Sent Events stream for conversational and autonomous execution."""
    attachment_ids = [a.strip() for a in attachments.split(",") if a.strip()]

    async def event_generator():
        async for event in unified_mission_engine.execute_mission_turn(
            mission_id=mission_id,
            user_input=goal,
            attachment_ids=attachment_ids,
            auth_context=auth,
        ):
            yield {
                "event": event.get("type", "message"),
                "data": json.dumps(event),
            }

    return EventSourceResponse(event_generator())


@router.post("/{mission_id}/messages")
async def send_mission_message(
    mission_id: str,
    payload: MessageRequest,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Add a user message or follow-up instruction to an ongoing mission."""
    mission = mission_repository.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    msg = mission_repository.save_message(
        mission_id=mission_id,
        role="user",
        content=payload.content,
        attachment_ids=payload.attachment_ids,
    )
    return {"success": True, "message": msg}


@router.post("/{mission_id}/plan/approve")
async def approve_plan(
    mission_id: str,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Approve proposed mission plan to begin autonomous execution."""
    plan = mission_repository.get_latest_plan(mission_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No active plan found for mission")

    mission_repository.save_plan(
        mission_id=mission_id,
        steps=plan["steps"],
        summary=plan["summary"],
        status="APPROVED",
    )
    mission_repository.update_mission_status(mission_id, MissionState.EXECUTING.value)
    return {"success": True, "status": "APPROVED"}


@router.post("/{mission_id}/selection")
async def submit_selection(
    mission_id: str,
    payload: SelectionDecisionRequest,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Submit solution choice (Option A, B, C) to unblock execution."""
    ok = mission_repository.record_selection_answer(
        selection_id=payload.selection_id,
        selected_option=payload.selected_option,
    )
    return {"success": ok, "selected_option": payload.selected_option}


@router.post("/{mission_id}/permissions")
async def submit_permission(
    mission_id: str,
    payload: PermissionDecisionRequest,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Grant or deny fine-grained execution permission."""
    scope_enum = PermissionScope.ONCE
    if payload.scope.upper() == "MISSION":
        scope_enum = PermissionScope.MISSION
    elif payload.scope.upper() in ("PROJECT", "ALWAYS"):
        scope_enum = PermissionScope.PROJECT

    status = "GRANTED" if payload.action.upper() == "ALLOW" else "DENIED"
    ok = mission_repository.record_permission_decision(
        request_id=payload.request_id,
        status=status,
        granted_scope=scope_enum.value,
    )

    if ok and status == "GRANTED":
        mission_permissions.grant(
            mission_id=mission_id,
            action_target=f"request({payload.request_id})",
            scope=scope_enum,
        )

    return {"success": ok, "decision": status, "scope": scope_enum.value}


@router.post("/{mission_id}/stop")
async def stop_mission(
    mission_id: str,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Interrupt and cancel ongoing mission execution."""
    mission_repository.update_mission_status(mission_id, MissionState.CANCELLED.value)
    return {"success": True, "status": "CANCELLED"}


@router.post("/{mission_id}/rollback")
async def rollback_mission(
    mission_id: str,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Revert changes back to clean Git working tree state."""
    from app.modules.agent.tools.terminal import terminal_tool
    res = await terminal_tool.execute("git checkout .")
    return {"success": res["exit_code"] == 0, "message": "Working tree reverted"}


@router.post("/{mission_id}/upload")
async def upload_attachment(
    mission_id: str,
    payload: ImageUploadPayload,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Upload multimodal screenshot/image for visual-aware coding."""
    attachment = multimodal_storage.store_base64_attachment(
        base64_data=payload.image_base64,
        filename=payload.filename,
        mime_type=payload.mime_type,
        mission_id=mission_id,
    )
    return {
        "success": True,
        "attachment_id": attachment["id"],
        "filename": attachment["filename"],
        "mime_type": attachment["mime_type"],
        "file_size": attachment["file_size"],
    }


@router.get("/{mission_id}/diff")
async def get_mission_diff(
    mission_id: str,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Retrieve current Git diff for review."""
    from app.modules.agent.tools.terminal import terminal_tool
    res = await terminal_tool.execute("git diff")
    return {"diff": res["stdout"]}


@router.get("/{mission_id}/artifacts")
async def get_mission_artifacts(
    mission_id: str,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """List generated artifacts for the mission."""
    return mission_repository.get_artifacts(mission_id)
