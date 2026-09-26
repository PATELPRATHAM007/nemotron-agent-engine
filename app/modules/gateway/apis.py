"""
Model Gateway Endpoint Handlers (Controllers)
=============================================
Processes model generation, streaming, usage auditing, and administrative management.
"""

import json
from typing import Any
from fastapi import Depends, HTTPException, Query, status
from sse_starlette.sse import EventSourceResponse

from app.modules.gateway import messages
from app.modules.gateway.schemas import (
    ModelGeneratePayload,
    ProviderCreatePayload,
    ModelCreatePayload,
    CredentialRotatePayload,
)
from app.modules.gateway.service import model_gateway, model_router
from app.security.context import AuthContext
from app.security.dependencies import get_current_auth_context
from app.security.secrets import secret_manager


async def list_authorized_models(auth: AuthContext = Depends(get_current_auth_context)):
    """List AI models authorized for current user and tenant."""
    models = model_router.list_models_for_user(auth)
    return [m.to_dict() for m in models]


async def get_model_details(model_name: str, auth: AuthContext = Depends(get_current_auth_context)):
    """Inspect model capabilities, max tokens, and pricing."""
    model = model_router.select_model(auth, requested_model=model_name)
    return model.to_dict()


async def generate_response(payload: ModelGeneratePayload, auth: AuthContext = Depends(get_current_auth_context)):
    """Execute non-streaming model generation through Model Gateway."""
    return await model_gateway.execute_generate(
        auth_context=auth,
        model_name=payload.model,
        messages=payload.messages,
        mission_id=payload.mission_id,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
    )


async def stream_response(payload: ModelGeneratePayload, auth: AuthContext = Depends(get_current_auth_context)):
    """Execute streaming inference through Model Gateway."""
    async def event_generator():
        async for chunk in model_gateway.execute_stream(
            auth_context=auth,
            model_name=payload.model,
            messages=payload.messages,
            mission_id=payload.mission_id,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        ):
            yield {"event": chunk.get("type", "message"), "data": json.dumps(chunk)}

    return EventSourceResponse(event_generator())


async def list_usage_metrics(limit: int = Query(50, ge=1, le=500), auth: AuthContext = Depends(get_current_auth_context)):
    """List recent model token usage and cost accounting."""
    return model_gateway.get_usage_history(auth.organization_id, limit=limit)


async def get_quotas(auth: AuthContext = Depends(get_current_auth_context)):
    """Retrieve tenant quota limits and current monthly spend."""
    return model_gateway.get_tenant_quota(auth.organization_id)


async def register_provider(payload: ProviderCreatePayload, auth: AuthContext = Depends(get_current_auth_context)):
    """Admin endpoint: register new external model provider."""
    if not auth.has_permission("provider.configure"):
        raise HTTPException(status_code=403, detail="Permission 'provider.configure' required")
    return {"success": True, "provider": payload.model_dump(), "message": "Provider registered"}


async def register_model(payload: ModelCreatePayload, auth: AuthContext = Depends(get_current_auth_context)):
    """Admin endpoint: add model to registry catalog."""
    if not auth.has_permission("model.configure"):
        raise HTTPException(status_code=403, detail="Permission 'model.configure' required")
    return {"success": True, "model": payload.model_dump(), "message": "Model registered"}


async def rotate_credential(credential_id: str, payload: CredentialRotatePayload, auth: AuthContext = Depends(get_current_auth_context)):
    """Admin endpoint: rotate model provider credential reference without downtime."""
    if not auth.has_permission("secret.rotate"):
        raise HTTPException(status_code=403, detail="Permission 'secret.rotate' required")
    return {
        "success": True,
        "credential_id": credential_id,
        "new_reference": payload.new_secret_reference,
        "status": "ROTATED",
        "message": messages.CREDENTIAL_ROTATED,
    }
