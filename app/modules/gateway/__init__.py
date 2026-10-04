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
    "get_provider_adapter",
    "model_gateway",
]
