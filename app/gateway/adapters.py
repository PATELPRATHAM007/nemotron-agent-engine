"""
Backward compatibility re-export. Real adapters live in app.modules.gateway.adapters.
"""
from app.modules.gateway.adapters import (
    GoogleProviderAdapter,
    ModelProviderAdapter,
    OpenAICompatibleAdapter,
    get_provider_adapter,
)

__all__ = [
    "ModelProviderAdapter",
    "GoogleProviderAdapter",
    "OpenAICompatibleAdapter",
    "get_provider_adapter",
]
