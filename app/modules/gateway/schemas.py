"""
Model Gateway Pydantic Schemas
==============================
Request and response validation models for the Model Gateway.
"""

from typing import Any
from pydantic import BaseModel, Field


class ModelGeneratePayload(BaseModel):
    model: str = Field(..., description="Target model identifier or name")
    messages: list[dict[str, Any]] = Field(..., min_length=1, description="Message conversation history")
    mission_id: str | None = None
    temperature: float = 0.2
    max_tokens: int = 4096


class ProviderCreatePayload(BaseModel):
    name: str
    type: str  # GOOGLE, OPENAI, VLLM, OLLAMA, CUSTOM
    base_url: str = ""


class ModelCreatePayload(BaseModel):
    provider_id: str
    name: str
    model_identifier: str
    capabilities: list[str] = Field(default_factory=lambda: ["text"])
    context_window: int = 128000
    max_output_tokens: int = 4096
    cost_per_1k_input: float = 0.0001
    cost_per_1k_output: float = 0.0002
    is_premium: bool = False


class CredentialCreatePayload(BaseModel):
    provider_id: str
    secret_reference: str  # vault://models/...
    key_version: int = 1


class CredentialRotatePayload(BaseModel):
    new_secret_reference: str
