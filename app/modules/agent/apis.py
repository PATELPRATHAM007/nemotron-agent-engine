"""
Agent Module Controllers (API Endpoints)
========================================
Implements:
  - Streaming conversational reasoning tokens
  - Mission execution triggering & SSE output stream
  - Runtime configuration introspection
  - Forwarding cost accounting queries
"""

import json
import uuid
from fastapi import Query
from sse_starlette.sse import EventSourceResponse

from app.core.config import settings
from app.core.llm_gateway import llm_gateway
from app.modules.agent.engine import agent_engine
from app.modules.agent.schemas import (
    AgentConfigResponse,
    ChatStreamRequest,
    MissionRequest,
    MissionResponse,
)
from app.modules.agent.validation import AgentValidator


async def stream_chat(payload: ChatStreamRequest):
    """Direct conversational chat stream with Nemotron 3 Ultra reasoning tokens."""
    formatted_messages = [
        {"role": m.role, "content": m.content} for m in payload.messages
    ]

    async def chat_generator():
        async for chunk in llm_gateway.stream_nemotron_reasoning(
            messages=formatted_messages,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        ):
            yield {
                "event": chunk.get("type", "message"),
                "data": json.dumps(chunk),
            }

    return EventSourceResponse(chat_generator())


async def start_mission(request: MissionRequest):
    """Register a new autonomous agent mission."""
    AgentValidator.validate_goal(request.goal)
    mission_id = str(uuid.uuid4())
    return MissionResponse(
        success=True,
        mission_id=mission_id,
        goal=request.goal,
        stream_url=f"/api/v1/agent/stream/{mission_id}?goal={request.goal}",
    )


async def stream_mission(
    mission_id: str,
    goal: str = Query(..., description="The objective for the agent to execute"),
    max_iterations: int = Query(15, description="Max autonomous turns"),
):
    """Real-time SSE stream of the agent's thoughts, tool actions, and responses."""
    AgentValidator.validate_goal(goal)
    AgentValidator.validate_iterations(max_iterations)

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


async def get_agent_config():
    """Return model runtime configuration."""
    return AgentConfigResponse(
        nemotron_model=settings.NEMOTRON_MODEL_NAME,
        nemotron_api_base=settings.NEMOTRON_API_BASE,
        thinking_enabled=settings.NEMOTRON_ENABLE_THINKING,
        gemini_model=settings.GEMINI_MODEL_NAME,
        gemini_active=bool(settings.GEMINI_API_KEY),
    )


async def get_cost_summary():
    """Return aggregated token and expenditure metrics across all missions."""
    from app.modules.cost.apis import get_cost_summary as modular_cost_summary
    return await modular_cost_summary()


async def get_cost_ledger(
    limit: int = Query(10, description="Max historical missions to retrieve"),
):
    """Return historical mission cost records."""
    from app.modules.cost.apis import list_cost_records as modular_list_records
    return await modular_list_records(limit=limit)


async def get_mission_cost(mission_id: str):
    """Return cost records for a specific mission."""
    from app.modules.cost.apis import get_mission_cost as modular_mission_cost
    return await modular_mission_cost(mission_id)
