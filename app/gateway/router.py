"""
Backward compatibility re-export. Real router lives in app.modules.gateway.service.
"""
from app.modules.gateway.service import (
    ModelRouter,
    ModelRoutingError,
    model_router,
)

__all__ = [
    "ModelRouter",
    "ModelRoutingError",
    "model_router",
]
