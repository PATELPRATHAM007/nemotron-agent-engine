"""
Mission Module Endpoint Handlers (Controllers)
==============================================
Controller layer for Autonomous Missions: creation, SSE streaming, message postings,
plan approvals, solution selections, and permission grants.
"""

import json
from typing import Any
import uuid

from fastapi import Depends, HTTPException, Query, status
from sse_starlette.sse import EventSourceResponse

from app.modules.missions.multimodal import multimodal_storage
from app.modules.missions.permissions import PermissionScope, mission_permissions
from app.modules.missions.repository import mission_repository
from app.modules.missions.state_machine import MissionState
from app.modules.missions import messages
from app.modules.missions.schemas import (
    CreateMissionRequest,
    ImageUploadPayload,
    MessageRequest,
    PermissionDecisionRequest,
    SelectionDecisionRequest,
)
from app.modules.missions.service import unified_mission_engine
from app.security.context import AuthContext
from app.security.dependencies import get_current_auth_context


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
        "message": messages.MISSION_CREATED,
    }


async def list_missions(
    limit: int = Query(20, ge=1, le=100),
    auth: AuthContext = Depends(get_current_auth_context),
):
    """List historical and active autonomous missions."""
    return mission_repository.list_missions(limit=limit)


async def get_mission(
    mission_id: str,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Get mission details, status, checkpoints, and messages."""
    mission = mission_repository.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=messages.MISSION_NOT_FOUND)
    msgs = mission_repository.get_messages(mission_id)
    plan = mission_repository.get_latest_plan(mission_id)
    artifacts = mission_repository.get_artifacts(mission_id)
    return {
        "mission": mission,
        "messages": msgs,
        "latest_plan": plan,
        "artifacts": artifacts,
    }


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


async def send_mission_message(
    mission_id: str,
    payload: MessageRequest,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Add a user message or follow-up instruction to an ongoing mission."""
    mission = mission_repository.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=messages.MISSION_NOT_FOUND)

    msg = mission_repository.save_message(
        mission_id=mission_id,
        role="user",
        content=payload.content,
        attachment_ids=payload.attachment_ids,
    )
    return {"success": True, "message": msg}


async def approve_plan(
    mission_id: str,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Approve proposed mission plan to begin autonomous execution."""
    plan = mission_repository.get_latest_plan(mission_id)
    if not plan:
        raise HTTPException(status_code=404, detail=messages.PLAN_NOT_FOUND)

    mission_repository.save_plan(
        mission_id=mission_id,
        steps=plan["steps"],
        summary=plan["summary"],
        status="APPROVED",
    )
    mission_repository.update_mission_status(mission_id, MissionState.EXECUTING.value)
    return {"success": True, "status": "APPROVED", "message": messages.PLAN_APPROVED}


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
    return {"success": ok, "selected_option": payload.selected_option, "message": messages.SELECTION_RECORDED}


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

    msg = messages.PERMISSION_GRANTED if status == "GRANTED" else messages.PERMISSION_DENIED
    return {"success": ok, "decision": status, "scope": scope_enum.value, "message": msg}


async def stop_mission(
    mission_id: str,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Interrupt and cancel ongoing mission execution."""
    mission_repository.update_mission_status(mission_id, MissionState.CANCELLED.value)
    return {"success": True, "status": "CANCELLED", "message": messages.MISSION_STOPPED}


async def rollback_mission(
    mission_id: str,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Revert changes back to clean Git working tree state."""
    from app.modules.agent.tools.terminal import terminal_tool
    res = await terminal_tool.execute("git checkout .")
    return {"success": res["exit_code"] == 0, "message": messages.ROLLBACK_SUCCESS}


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
        "message": messages.ATTACHMENT_UPLOADED,
    }


async def get_mission_diff(
    mission_id: str,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Retrieve current Git diff for review."""
    from app.modules.agent.tools.terminal import terminal_tool
    res = await terminal_tool.execute("git diff")
    return {"diff": res["stdout"]}


async def get_mission_artifacts(
    mission_id: str,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """List generated artifacts for the mission."""
    return mission_repository.get_artifacts(mission_id)
