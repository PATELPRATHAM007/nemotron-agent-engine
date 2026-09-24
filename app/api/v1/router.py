from fastapi import APIRouter

from app.api.v1.endpoints import health, agent

api_router = APIRouter()

# Health check endpoints
api_router.include_router(health.router)

# Nemotron Autonomous Agent endpoints
api_router.include_router(agent.router)
