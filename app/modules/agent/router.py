"""
Agent Module FastAPI Router
===========================
Declares /agent routes and attaches handlers from apis.py.
"""

from fastapi import APIRouter
from app.modules.agent import apis
from app.modules.agent.schemas import AgentConfigResponse, MissionResponse

router = APIRouter(prefix="/agent", tags=["Agent"])

# Streaming conversational chat
router.add_api_route(
    "/chat/stream",
    apis.stream_chat,
    methods=["POST"],
    summary="Direct conversational chat stream with Nemotron reasoning",
)

# Autonomous mission lifecycle
router.add_api_route(
    "/run",
    apis.start_mission,
    methods=["POST"],
    response_model=MissionResponse,
    summary="Register a new autonomous agent mission",
)

router.add_api_route(
    "/stream/{mission_id}",
    apis.stream_mission,
    methods=["GET"],
    summary="Real-time SSE stream of thoughts and tool execution",
)

router.add_api_route(
    "/config",
    apis.get_agent_config,
    methods=["GET"],
    response_model=AgentConfigResponse,
    summary="Return model runtime configuration",
)

# Cost telemetry endpoints (delegating to cost module)
router.add_api_route(
    "/cost/summary",
    apis.get_cost_summary,
    methods=["GET"],
    summary="Return aggregated token and expenditure metrics",
)

router.add_api_route(
    "/cost/ledger",
    apis.get_cost_ledger,
    methods=["GET"],
    summary="Return historical mission cost records",
)

router.add_api_route(
    "/cost/mission/{mission_id}",
    apis.get_mission_cost,
    methods=["GET"],
    summary="Return cost records for a specific mission",
)
