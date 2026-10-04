"""
Model Gateway Module
====================
Provides model registry, capability matching, provider adapters, and audited execution.
"""
from app.modules.gateway.adapters import (
    GoogleProviderAdapter,
    ModelProviderAdapter,
    OpenAICompatibleAdapter,
    get_provider_adapter,
)
from app.modules.gateway.models import (
    ModelCredential,
    ModelProvider,
    ModelQuota,
    ModelUsage,
    RegisteredModel,
)
from app.modules.gateway.service import ModelGateway, model_gateway


def __getattr__(name: str):
    if name in ("router", "admin_router"):
        from app.modules.gateway.router import admin_router, router
        if name == "router":
            return router
        return admin_router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "GoogleProviderAdapter",
    "ModelCredential",
    "ModelGateway",
    "ModelProvider",
    "ModelProviderAdapter",
    "ModelQuota",
    "ModelUsage",
    "OpenAICompatibleAdapter",
    "RegisteredModel",
    "admin_router",
    "get_provider_adapter",
    "model_gateway",
    "router",
]
