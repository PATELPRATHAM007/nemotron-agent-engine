# Model Gateway Architecture & Request Verification Pipeline

## 1. Overview

The **Model Gateway** is the single authoritative broker for all AI model inference across the platform. Neither the browser frontend nor local execution agents communicate directly with third-party model providers.

```
Incoming Request
      │
      ▼
 1. Receive Request
 2. Authenticate Caller (Bearer Token / Cookie)
 3. Validate Token Signature & Expiration
 4. Validate Server-Side Session State
 5. Validate Tenant Isolation (Organization Match)
 6. Validate Mission & Project Access
 7. Authorize Model Access for User Role
 8. Authorize Required Capabilities (tools, vision, reasoning)
 9. Check Tenant Quota & Cost Limits
10. Check Rate Limits
11. Validate Input Payload
12. Apply Security & Privacy Policy (Data Classification)
13. Select Optimal Permitted Provider & Route
14. Resolve Provider Credential from Secret Vault (vault://...)
15. Dispatch Call via Provider Adapter (Google / OpenAI / vLLM / Mock)
16. Stream / Return Response with Secret Redaction
17. Record Token Usage, Cost, and Latency
18. Record Security Audit Event
```

---

## 2. Capability-Based Model Routing

Models declare structured capabilities in the catalog:
- `text`: Natural language comprehension and generation.
- `vision`: Multi-modal image, screenshot, and diagram inspection.
- `tools`: Structured function/tool calling.
- `code`: Syntactic analysis and code generation.
- `reasoning`: Multi-step chain-of-thought planning.

When a mission requires vision analysis (e.g. inspecting an uploaded UI screenshot), the router inspects the user's authorized models and selects an approved vision-capable model (e.g. `gemini-3.1-flash-lite`).

---

## 3. Provider Adapters

All provider-specific SDK logic is decoupled behind the `ModelProviderAdapter` interface:

```python
class ModelProviderAdapter(ABC):
    @abstractmethod
    async def generate(self, model: str, messages: list[dict], credential: str, **kwargs) -> dict[str, Any]:
        ...

    @abstractmethod
    async def stream(self, model: str, messages: list[dict], credential: str, **kwargs) -> AsyncGenerator[dict[str, Any], None]:
        ...

    @abstractmethod
    async def health(self, credential: str) -> bool:
        ...
```

Implemented adapters include:
1. `GoogleProviderAdapter`: Direct integration with Google Vertex / Gemini API.
2. `OpenAICompatibleAdapter`: Standardized adapter for OpenAI, Anthropic bridges, Azure OpenAI, vLLM, and Ollama.
3. `MockProviderAdapter`: Deterministic local development adapter for testing and CI pipelines.

---

## 4. Quota Enforcement & Cost Protection

- **Tenant Quotas**: Monitored via `gateway_model_quotas`. Enforces `max_daily_spend_usd`, `max_monthly_spend_usd`, and `max_requests_per_minute`.
- **Pre-Execution Check**: Rejects requests when current spend exceeds tenant quota limits with `MODEL_QUOTA_EXCEEDED`.
- **Usage Accounting**: Every completed invocation writes an immutable record to `gateway_model_usage` tracking:
  - `prompt_tokens`
  - `completion_tokens`
  - `total_tokens`
  - `cost_usd`
  - `latency_ms`
  - `status`
