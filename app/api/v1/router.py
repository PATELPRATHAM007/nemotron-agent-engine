from fastapi import APIRouter

from app.api.v1.endpoints import health
from app.modules.auth.router import router as auth_router
from app.modules.cost.router import router as cost_router
from app.modules.gateway.router import admin_router as model_admin_router
from app.modules.gateway.router import router as model_gateway_router
from app.modules.missions.router import router as missions_router
from app.modules.agent.router import router as agent_router

api_router = APIRouter()

# Health check
api_router.include_router(health.router)

# Domain Modules
api_router.include_router(auth_router)
api_router.include_router(model_gateway_router)
api_router.include_router(model_admin_router)
api_router.include_router(missions_router)
api_router.include_router(cost_router)

# Agent Legacy / Direct compatibility
api_router.include_router(agent_router)
