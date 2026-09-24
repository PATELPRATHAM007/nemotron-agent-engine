from fastapi import APIRouter

from app.api.v1.endpoints import health
from app.modules.agent.routes import router as agent_router

api_router = APIRouter()

# Health check endpoints
api_router.include_router(health.router)

# Nemotron Autonomous Agent module endpoints
api_router.include_router(agent_router)
