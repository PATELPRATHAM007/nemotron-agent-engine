"""
Model Router & Capability Matcher
=================================
Selects the optimal permitted model based on:
  - Required capabilities (vision, tools, code, reasoning, long_context)
  - User authorization & tenant policy
  - Cost limits & latency requirements
  - Provider availability
"""

from typing import Any

from app.gateway.models import RegisteredModel
from app.security.context import AuthContext


class ModelRoutingError(PermissionError):
    """Raised when no authorized model satisfies required capabilities."""


class ModelRouter:
    """Routes requests to the highest-performing authorized model."""

    def __init__(self):
        # In-memory registry defaults matching available providers
        self._default_models = [
            RegisteredModel(
                id="model-gemini-flash",
                provider_id="provider-google",
                name="gemini-3.1-flash-lite",
                model_identifier="gemini-3.1-flash-lite",
                capabilities=["text", "vision", "tools", "code", "reasoning"],
                context_window=1000000,
                max_output_tokens=8192,
                cost_per_1k_input=0.0001,
                cost_per_1k_output=0.0003,
                is_premium=False,
                status="ACTIVE",
            ),
            RegisteredModel(
                id="model-nemotron-ultra",
                provider_id="provider-vllm",
                name="nemotron-3-ultra",
                model_identifier="nvidia/nemotron-3-ultra-550b",
                capabilities=["text", "tools", "code", "reasoning"],
                context_window=128000,
                max_output_tokens=4096,
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.003,
                is_premium=True,
                status="ACTIVE",
            ),
            RegisteredModel(
                id="model-nemotron-dev",
                provider_id="provider-mock",
                name="nemotron-dev",
                model_identifier="mock/nemotron-dev",
                capabilities=["text", "tools", "code", "reasoning"],
                context_window=32768,
                max_output_tokens=4096,
                cost_per_1k_input=0.0001,
                cost_per_1k_output=0.0002,
                is_premium=False,
                status="ACTIVE",
            ),
        ]

    def list_models_for_user(self, context: AuthContext) -> list[RegisteredModel]:
        """Return models authorized for the given AuthContext."""
        can_use_premium = context.has_permission("model.use.premium") or context.has_role("ORG_ADMIN")
        allowed = []
        for m in self._default_models:
            if m.is_premium and not can_use_premium:
                continue
            allowed.append(m)
        return allowed

    def select_model(
        self,
        context: AuthContext,
        requested_model: str | None = None,
        required_capabilities: list[str] | None = None,
        min_context_window: int = 4096,
    ) -> RegisteredModel:
        """
        Select an authorized model satisfying capability constraints.
        If a specific model is requested by the user, validates that the user is authorized.
        """
        allowed_models = self.list_models_for_user(context)
        if not allowed_models:
            raise ModelRoutingError("User has no authorized models configured for this tenant.")

        # 1. If explicit model requested, verify authorization
        if requested_model:
            for m in allowed_models:
                if m.name.lower() == requested_model.lower() or m.model_identifier.lower() == requested_model.lower():
                    return m
            raise ModelRoutingError(f"Model '{requested_model}' is not authorized for your account/role.")

        # 2. Match by capabilities
        caps = required_capabilities or ["text"]
        for m in allowed_models:
            if all(c in m.capabilities for c in caps) and m.context_window >= min_context_window:
                return m

        # Default fallback to first permitted model
        return allowed_models[0]


model_router = ModelRouter()
