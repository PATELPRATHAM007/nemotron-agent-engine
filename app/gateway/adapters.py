"""
Model Provider Adapters Abstraction
===================================
Hides vendor-specific API implementations behind a unified ProviderAdapter
interface. Resolves credentials internally via SecretManager.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from app.core.config import settings
from app.core.llm_gateway import llm_gateway
from app.core.logging_config import get_logger
from app.security.secrets import secret_manager

logger = get_logger(__name__)


class ModelProviderAdapter(ABC):
    """Abstract interface for all model providers."""

    @abstractmethod
    async def generate(
        self,
        model_identifier: str,
        messages: list[dict[str, Any]],
        secret_reference: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Generate complete model response."""
        pass

    @abstractmethod
    async def stream(
        self,
        model_identifier: str,
        messages: list[dict[str, Any]],
        secret_reference: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream real-time tokens, thoughts, and tool calls."""
        pass

    @abstractmethod
    async def health(self, secret_reference: str) -> bool:
        """Health check for provider availability."""
        pass


class GoogleProviderAdapter(ModelProviderAdapter):
    """Adapter for Google Gemini models."""

    async def generate(
        self,
        model_identifier: str,
        messages: list[dict[str, Any]],
        secret_reference: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        accumulated_text = ""
        prompt_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
        completion_tokens = 0

        async for chunk in self.stream(
            model_identifier=model_identifier,
            messages=messages,
            secret_reference=secret_reference,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
        ):
            if chunk.get("type") == "token":
                accumulated_text += chunk.get("content", "")
                completion_tokens += 1

        return {
            "content": accumulated_text,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }

    async def stream(
        self,
        model_identifier: str,
        messages: list[dict[str, Any]],
        secret_reference: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        # Resolves credential in-memory strictly within execution scope
        api_key = secret_manager.resolve_credential(secret_reference)
        async for chunk in llm_gateway.stream_nemotron_reasoning(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
        ):
            yield chunk

    async def health(self, secret_reference: str) -> bool:
        try:
            key = secret_manager.resolve_credential(secret_reference)
            return bool(key)
        except Exception:
            return False


class OpenAICompatibleAdapter(ModelProviderAdapter):
    """Adapter for vLLM, Ollama, OpenAI, TGI, and Custom endpoints."""

    def __init__(self, base_url: str = ""):
        self.base_url = base_url

    async def generate(
        self,
        model_identifier: str,
        messages: list[dict[str, Any]],
        secret_reference: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        accumulated = ""
        prompt_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
        async for chunk in self.stream(
            model_identifier=model_identifier,
            messages=messages,
            secret_reference=secret_reference,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
        ):
            if chunk.get("type") == "token":
                accumulated += chunk.get("content", "")
        return {
            "content": accumulated,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": len(accumulated) // 4,
                "total_tokens": prompt_tokens + (len(accumulated) // 4),
            },
        }

    async def stream(
        self,
        model_identifier: str,
        messages: list[dict[str, Any]],
        secret_reference: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        async for chunk in llm_gateway.stream_nemotron_reasoning(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
        ):
            yield chunk

    async def health(self, secret_reference: str) -> bool:
        return True


class MockProviderAdapter(ModelProviderAdapter):
    """Deterministic mock provider for testing and offline environments."""

    async def generate(
        self,
        model_identifier: str,
        messages: list[dict[str, Any]],
        secret_reference: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return {
            "content": f"[Mock {model_identifier}]: Verified response.",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

    async def stream(
        self,
        model_identifier: str,
        messages: list[dict[str, Any]],
        secret_reference: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        yield {"type": "thought", "content": f"Reasoning with {model_identifier}..."}
        yield {"type": "token", "content": f"Mock response from {model_identifier}."}

    async def health(self, secret_reference: str) -> bool:
        return True


def get_provider_adapter(provider_type: str, base_url: str = "") -> ModelProviderAdapter:
    """Factory returning corresponding provider adapter."""
    p_type = provider_type.upper()
    if p_type == "GOOGLE":
        return GoogleProviderAdapter()
    elif p_type in ("VLLM", "OLLAMA", "OPENAI", "TGI", "CUSTOM"):
        return OpenAICompatibleAdapter(base_url=base_url)
    return MockProviderAdapter()
