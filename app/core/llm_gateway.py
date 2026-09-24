"""
LLM Gateway for NVIDIA Nemotron 3 Ultra & Jio Gemini Tier-1 Router
===================================================================
Provides async streaming communication with:
1. Nemotron 3 Ultra (vLLM / NVIDIA NIM OpenAI-compatible endpoint)
   Supports inference-time reasoning flags (Chain-of-Thought thinking stream).
2. Jio Gemini Plan (Google GenAI SDK / Gemini 2.5 Flash)
   High-throughput Tier-1 fast triage, parsing, and preprocessing ($0 cost).
"""

import json
from typing import AsyncGenerator, Dict, Any, List, Optional
import httpx
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class LLMGateway:
    """Unified Gateway for Nemotron 3 Ultra & Gemini Dual-Engine Routing."""

    def __init__(self):
        self.nemotron_base_url = settings.NEMOTRON_API_BASE.rstrip("/")
        self.nemotron_api_key = settings.NEMOTRON_API_KEY
        self.nemotron_model = settings.NEMOTRON_MODEL_NAME
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.gemini_model = settings.GEMINI_MODEL_NAME

    async def stream_nemotron_reasoning(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.6,
        max_tokens: int = 8192,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream reasoning tokens and tool calls from Nemotron 3 Ultra via SSE."""
        payload: Dict[str, Any] = {
            "model": self.nemotron_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            # Enable inference-time reasoning chain-of-thought for Nemotron 3 Ultra
            "extra_body": {
                "enable_thinking": settings.NEMOTRON_ENABLE_THINKING,
            },
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.nemotron_api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.nemotron_base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=180.0) as client:
            try:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        logger.error(f"Nemotron API error ({response.status_code}): {error_body.decode('utf-8', 'ignore')}")
                        yield {
                            "type": "error",
                            "content": f"Nemotron API returned status {response.status_code}: {error_body.decode('utf-8', 'ignore')}",
                        }
                        return

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            choice = data.get("choices", [{}])[0]
                            delta = choice.get("delta", {})

                            # 1. Check for thinking / reasoning tokens
                            reasoning_chunk = delta.get("reasoning_content") or delta.get("thinking")
                            if reasoning_chunk:
                                yield {
                                    "type": "thought",
                                    "content": reasoning_chunk,
                                }

                            # 2. Check for response content tokens
                            content_chunk = delta.get("content")
                            if content_chunk:
                                yield {
                                    "type": "token",
                                    "content": content_chunk,
                                }

                            # 3. Check for tool calls
                            tool_calls = delta.get("tool_calls")
                            if tool_calls:
                                yield {
                                    "type": "tool_call_delta",
                                    "tool_calls": tool_calls,
                                }

                        except json.JSONDecodeError:
                            continue

            except httpx.ConnectError:
                # If local vLLM isn't running, yield simulated response or fallback
                logger.warning(f"Could not connect to Nemotron at {url}. Yielding standby status.")
                yield {
                    "type": "warning",
                    "content": f"[Standby] Nemotron 3 Ultra endpoint at {url} is initializing or offline.",
                }

    async def run_gemini_fast_triage(self, prompt: str) -> str:
        """Run Tier-1 fast scraping or pre-filtering using Jio Gemini ($0 cost)."""
        if not self.gemini_api_key:
            return "Gemini API key not configured; skipping Tier-1 triage."

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    return "No content returned from Gemini."
            return f"Gemini error: {resp.text}"


llm_gateway = LLMGateway()
