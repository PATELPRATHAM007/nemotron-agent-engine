"""
Model Gateway Subsystem
=======================
Centralized AI model registry, capability router, credential resolver,
and usage accounting gateway.
"""

from app.gateway.adapters import (
    GoogleProviderAdapter,
    ModelProviderAdapter,
    OpenAICompatibleAdapter,
    get_provider_adapter,
)
from app.gateway.gateway import ModelGateway, model_gateway
from app.gateway.models import (
    ModelCredential,
    ModelProvider,
    ModelQuota,
    ModelUsage,
    RegisteredModel,
)
from app.gateway.router import ModelRouter, ModelRoutingError, model_router


def __getattr__(name: str):
    if name in ("router", "admin_router"):
        from app.modules.gateway.router import admin_router, router
        if name == "router":
            return router
        return admin_router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ModelProvider",
    "RegisteredModel",
    "ModelCredential",
    "ModelUsage",
    "ModelQuota",
    "ModelProviderAdapter",
    "GoogleProviderAdapter",
    "OpenAICompatibleAdapter",
    "get_provider_adapter",
    "ModelRouter",
    "ModelRoutingError",
    "model_router",
    "ModelGateway",
    "model_gateway",
    "router",
    "admin_router",
]
