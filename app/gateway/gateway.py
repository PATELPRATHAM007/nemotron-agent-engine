"""
Backward compatibility re-export. Real service lives in app.modules.gateway.service.
"""
from app.modules.gateway.service import (
    ModelGateway,
    ModelGatewayQuotaError,
    ModelGatewaySecurityError,
    model_gateway,
)

__all__ = [
    "ModelGateway",
    "model_gateway",
    "ModelGatewaySecurityError",
    "ModelGatewayQuotaError",
]
