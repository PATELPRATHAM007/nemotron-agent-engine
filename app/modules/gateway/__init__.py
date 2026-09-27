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
from app.modules.gateway.service import ModelGateway, model_gateway
from app.modules.gateway.models import (
    ModelCredential,
    ModelProvider,
    ModelQuota,
    ModelUsage,
    RegisteredModel,
)


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
    "ModelGateway",
    "model_gateway",
    "router",
    "admin_router",
]
