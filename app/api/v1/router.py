from fastapi import APIRouter

from app.api.v1.endpoints import auth as auth_endpoints
from app.api.v1.endpoints import health
from app.gateway.routes import admin_router as model_admin_router
from app.gateway.routes import router as model_gateway_router
from app.modules.agent.missions_routes import router as missions_router
from app.modules.agent.routes import router as agent_router

api_router = APIRouter()

# Health check endpoints
api_router.include_router(health.router)

# Identity & Authentication endpoints
api_router.include_router(auth_endpoints.router)

# Model Gateway endpoints
api_router.include_router(model_gateway_router)
api_router.include_router(model_admin_router)

# Unified Autonomous Missions endpoints
api_router.include_router(missions_router)

# Nemotron Autonomous Agent legacy/compatible endpoints
api_router.include_router(agent_router)
