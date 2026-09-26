"""
Model Gateway API Endpoints
===========================
Provides authorized model discovery, capability introspection,
streaming model inference, usage tracking, and administrative controls.
"""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.gateway.gateway import model_gateway
from app.gateway.models import RegisteredModel
from app.gateway.router import model_router
from app.security.context import AuthContext
from app.security.dependencies import get_current_auth_context
from app.security.secrets import secret_manager

router = APIRouter(prefix="/models", tags=["Model Gateway"])
admin_router = APIRouter(prefix="/admin", tags=["Model Gateway Administration"])


class ModelGenerateRequest(BaseModel):
    model: str | None = Field(None, description="Optional requested model name")
    messages: list[dict[str, Any]] = Field(..., description="Chat message history")
    mission_id: str | None = Field(None, description="Associated mission ID")
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(4096, ge=1, le=128000)
    tools: list[dict[str, Any]] | None = None
    required_capabilities: list[str] | None = None


class RegisterProviderRequest(BaseModel):
    name: str
    provider_type: str  # GOOGLE, OPENAI, ANTHROPIC, VLLM, OLLAMA, CUSTOM
    base_url: str = ""


class RegisterModelRequest(BaseModel):
    provider_id: str
    name: str
    model_identifier: str
    capabilities: list[str] = ["text", "code", "tools"]
    context_window: int = 128000
    is_premium: bool = False


class CredentialRotateRequest(BaseModel):
    new_secret: str
    key_version: int = 2


@router.get("")
async def list_authorized_models(auth: AuthContext = Depends(get_current_auth_context)):
    """List AI models authorized for the current authenticated user and tenant."""
    models = model_router.list_models_for_user(auth)
    return [m.to_dict() for m in models]


@router.get("/{model_id}")
async def get_model_details(model_id: str, auth: AuthContext = Depends(get_current_auth_context)):
    """Get metadata, capabilities, context window, and pricing for a model."""
    models = model_router.list_models_for_user(auth)
    for m in models:
        if m.id == model_id or m.name == model_id:
            return m.to_dict()
    raise HTTPException(status_code=404, detail="Model not found or access denied")


@router.post("/generate")
async def generate_response(
    payload: ModelGenerateRequest,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Generate a non-streaming response via Model Gateway."""
    accumulated = ""
    async for chunk in model_gateway.execute_stream(
        auth_context=auth,
        model_name=payload.model,
        messages=payload.messages,
        mission_id=payload.mission_id,
        required_capabilities=payload.required_capabilities,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        tools=payload.tools,
    ):
        if chunk.get("type") == "token":
            accumulated += chunk.get("content", "")

    return {
        "success": True,
        "model": payload.model or "gemini-3.1-flash-lite",
        "content": accumulated,
    }


@router.post("/stream")
async def stream_model_response(
    payload: ModelGenerateRequest,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Stream model tokens, thoughts, and tool requests via SSE through Model Gateway."""

    async def event_generator():
        async for chunk in model_gateway.execute_stream(
            auth_context=auth,
            model_name=payload.model,
            messages=payload.messages,
            mission_id=payload.mission_id,
            required_capabilities=payload.required_capabilities,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            tools=payload.tools,
        ):
            yield {
                "event": chunk.get("type", "token"),
                "data": json.dumps(chunk),
            }

    return EventSourceResponse(event_generator())


@router.get("/usage")
async def get_model_usage(auth: AuthContext = Depends(get_current_auth_context)):
    """Retrieve usage and financial spend telemetry for tenant."""
    current_spend = model_gateway._tenant_spend.get(auth.organization_id, 0.0)
    return {
        "organization_id": auth.organization_id,
        "billing_cycle": "Current Month",
        "total_spend_usd": round(current_spend, 6),
        "quota_limit_usd": 500.0,
    }


@router.get("/quotas")
async def get_model_quotas(auth: AuthContext = Depends(get_current_auth_context)):
    """Retrieve rate limits and spending limits."""
    return {
        "organization_id": auth.organization_id,
        "max_monthly_spend_usd": 500.0,
        "max_daily_spend_usd": 50.0,
        "max_requests_per_minute": 120,
    }


# -----------------------------------------------------------------------------
# Admin Endpoints (Require ORG_ADMIN or SUPER_ADMIN)
# -----------------------------------------------------------------------------
@admin_router.post("/providers")
async def create_provider(
    payload: RegisterProviderRequest,
    auth: AuthContext = Depends(get_current_auth_context),
):
    if not auth.has_role("ORG_ADMIN") and not auth.has_role("SUPER_ADMIN"):
        raise HTTPException(status_code=403, detail="Requires ORG_ADMIN role")
    return {"success": True, "provider_name": payload.name, "status": "ACTIVE"}


@admin_router.post("/models")
async def register_model(
    payload: RegisterModelRequest,
    auth: AuthContext = Depends(get_current_auth_context),
):
    if not auth.has_role("ORG_ADMIN") and not auth.has_role("SUPER_ADMIN"):
        raise HTTPException(status_code=403, detail="Requires ORG_ADMIN role")
    return {"success": True, "model_name": payload.name, "status": "ACTIVE"}


@admin_router.post("/model-credentials/{credential_id}/rotate")
async def rotate_credential(
    credential_id: str,
    payload: CredentialRotateRequest,
    auth: AuthContext = Depends(get_current_auth_context),
):
    if not auth.has_role("ORG_ADMIN") and not auth.has_role("SUPER_ADMIN"):
        raise HTTPException(status_code=403, detail="Requires ORG_ADMIN role")
    # Store new secret in vault
    secret_ref = f"vault://models/{credential_id}/v{payload.key_version}"
    secret_manager.store_secret(secret_ref, payload.new_secret)
    return {
        "success": True,
        "credential_id": credential_id,
        "secret_reference": secret_ref,
        "status": "ROTATED",
    }
