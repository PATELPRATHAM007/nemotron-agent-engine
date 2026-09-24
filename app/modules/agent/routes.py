"""
Agent Endpoints with Server-Sent Events (SSE) Streaming
======================================================
Provides real-time endpoints for mission dispatch and streaming
thought tokens, tool calls, and diffs to the Next.js frontend.
"""

import json
import uuid
from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

from app.modules.agent.engine import agent_engine
from app.modules.agent.schemas import MissionRequest, MissionResponse, AgentConfigResponse
from app.core.config import settings

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post("/run", response_model=MissionResponse)
async def start_mission(request: MissionRequest):
    """Register a new autonomous agent mission."""
    mission_id = str(uuid.uuid4())
    return MissionResponse(
        success=True,
        mission_id=mission_id,
        goal=request.goal,
        stream_url=f"/api/v1/agent/stream/{mission_id}?goal={request.goal}",
    )


@router.get("/stream/{mission_id}")
async def stream_mission(
    mission_id: str,
    goal: str = Query(..., description="The objective for the agent to execute"),
    max_iterations: int = Query(15, description="Max autonomous turns"),
):
    """Real-time SSE stream of the agent's thoughts, tool actions, and responses."""

    async def event_generator():
        async for event in agent_engine.execute_mission(
            mission_id=mission_id,
            goal=goal,
            max_iterations=max_iterations,
        ):
            yield {
                "event": event.get("type", "message"),
                "data": json.dumps(event),
            }

    return EventSourceResponse(event_generator())


@router.get("/config", response_model=AgentConfigResponse)
async def get_agent_config():
    """Return model runtime configuration."""
    return AgentConfigResponse(
        nemotron_model=settings.NEMOTRON_MODEL_NAME,
        nemotron_api_base=settings.NEMOTRON_API_BASE,
        thinking_enabled=settings.NEMOTRON_ENABLE_THINKING,
        gemini_model=settings.GEMINI_MODEL_NAME,
        gemini_active=bool(settings.GEMINI_API_KEY),
    )
