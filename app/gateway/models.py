"""
Backward compatibility re-export. Real models live in app.modules.gateway.models.
"""
from app.modules.gateway.models import (
    ModelCredential,
    ModelProvider,
    ModelQuota,
    ModelUsage,
    RegisteredModel,
    utc_now,
)

__all__ = [
    "ModelProvider",
    "RegisteredModel",
    "ModelCredential",
    "ModelUsage",
    "ModelQuota",
    "utc_now",
]
