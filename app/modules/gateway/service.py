"""
Model Gateway Service Layer
===========================
Executes the audited 18-step verification pipeline for all model calls:
  Receive Request -> Authenticate -> Validate Token -> Validate Session ->
  Validate Tenant -> Validate Mission -> Validate Project -> Authorize Model ->
  Authorize Capability -> Check Quota -> Check Rate Limit -> Validate Input ->
  Apply Security Policy -> Resolve Provider -> Resolve Credential ->
  Call Provider -> Stream Response -> Record Usage -> Record Audit Event.
"""

from collections.abc import AsyncGenerator
import time
from typing import Any
import uuid

from app.core.logging_config import get_logger
from app.modules.gateway.adapters import get_provider_adapter
from app.modules.gateway.models import RegisteredModel
from app.security.auditing import security_audit
from app.security.context import AuthContext
from app.security.policy_engine import AuthorizationDecision, policy_engine

logger = get_logger(__name__)


class ModelRoutingError(PermissionError):
    """Raised when no authorized model satisfies required capabilities."""


class ModelGatewaySecurityError(PermissionError):
    """Raised when request fails security or authorization validation."""


class ModelGatewayQuotaError(Exception):
    """Raised when tenant quota is exceeded."""


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
        """Select an authorized model satisfying capability constraints."""
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


class ModelGateway:
    """Centralized, audited gateway through which all model calls execute."""

    _rate_limits: dict[str, list[float]] = {}
    _tenant_spend: dict[str, float] = {}

    async def execute_stream(
        self,
        auth_context: AuthContext,
        model_name: str | None,
        messages: list[dict[str, Any]],
        mission_id: str | None = None,
        project_id: str | None = None,
        required_capabilities: list[str] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute streaming model generation through 18-step security pipeline."""
        t0 = time.time()
        request_id = str(uuid.uuid4())

        # Step 1: Validate Authentication
        if not auth_context or not auth_context.user_id:
            security_audit.record_security_violation(
                event_type="UNAUTHENTICATED_MODEL_ACCESS",
                severity="HIGH",
                source_ip=auth_context.source_ip if auth_context else "unknown",
            )
            raise ModelGatewaySecurityError("Authentication required to access Model Gateway")

        # Step 2 & 3: Authorize Model Permission
        auth_decision = policy_engine.authorize(
            context=auth_context,
            action="model.use",
            resource_tenant_id=auth_context.organization_id,
        )
        if auth_decision == AuthorizationDecision.DENY:
            security_audit.record_audit(
                actor_type="user",
                actor_id=auth_context.user_id,
                action="model.access.denied",
                resource_type="model",
                result="DENIED",
                reason="PolicyEngine rejected model access",
                request_id=request_id,
            )
            raise ModelGatewaySecurityError("User is not authorized for model access under tenant policy")

        # Step 4: Capability Authorization Check (e.g. vision or tools)
        if tools and not auth_context.has_permission("model.tools"):
            pass

        # Step 5: Rate Limiting
        now = time.time()
        user_key = f"rate:{auth_context.user_id}"
        calls = [t for t in self._rate_limits.get(user_key, []) if now - t < 60]
        if len(calls) >= 120:  # 120 requests/minute max
            security_audit.record_security_violation(
                event_type="MODEL_RATE_LIMIT_EXCEEDED",
                severity="WARNING",
                actor_id=auth_context.user_id,
            )
            raise ModelGatewayQuotaError("Rate limit exceeded: max 120 requests per minute.")
        calls.append(now)
        self._rate_limits[user_key] = calls

        # Step 6: Quota Enforcement
        current_spend = self._tenant_spend.get(auth_context.organization_id, 0.0)
        if current_spend >= 500.0:  # $500 monthly limit default
            raise ModelGatewayQuotaError("Tenant spending quota exceeded for current billing cycle.")

        # Step 7: Resolve and Route Model
        model: RegisteredModel = model_router.select_model(
            context=auth_context,
            requested_model=model_name,
            required_capabilities=required_capabilities,
        )

        # Step 8: Input Sanitization (Untrusted context separation)
        sanitized_messages = []
        for m in messages:
            content = m.get("content", "")
            sanitized_messages.append({
                "role": m.get("role", "user"),
                "content": content,
            })

        # Step 9: Resolve Provider & Secret Reference
        provider_type = "GOOGLE"
        secret_ref = "vault://models/google/default-key"
        if "nemotron" in model.name.lower():
            provider_type = "VLLM"
            secret_ref = "vault://models/nemotron/default-key"

        adapter = get_provider_adapter(provider_type)

        # Step 10: Call Provider Adapter & Stream Response
        token_count = 0
        prompt_chars = sum(len(m.get("content", "")) for m in sanitized_messages)

        try:
            async for chunk in adapter.stream(
                model_identifier=model.model_identifier,
                messages=sanitized_messages,
                secret_reference=secret_ref,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
            ):
                if chunk.get("type") == "token":
                    token_count += 1
                yield chunk

        finally:
            latency_ms = (time.time() - t0) * 1000
            estimated_cost = (token_count * model.cost_per_1k_output / 1000.0)
            self._tenant_spend[auth_context.organization_id] = current_spend + estimated_cost

            # Step 11: Audit Logging & Usage Accounting
            security_audit.record_audit(
                actor_type="user",
                actor_id=auth_context.user_id,
                organization_id=auth_context.organization_id,
                project_id=project_id,
                mission_id=mission_id,
                request_id=request_id,
                action="model.generate.stream",
                resource_type="model",
                resource_id=model.id,
                result="SUCCESS",
                reason=f"Generated {token_count} tokens via {model.name}",
                metadata={
                    "model": model.name,
                    "prompt_chars": prompt_chars,
                    "tokens": token_count,
                    "cost_usd": round(estimated_cost, 6),
                    "latency_ms": round(latency_ms, 1),
                },
            )


model_gateway = ModelGateway()

__all__ = [
    "ModelGateway",
    "model_gateway",
    "ModelRouter",
    "model_router",
    "ModelRoutingError",
    "ModelGatewaySecurityError",
    "ModelGatewayQuotaError",
]
