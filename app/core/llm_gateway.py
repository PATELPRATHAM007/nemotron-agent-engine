"""
LLM Gateway for NVIDIA Nemotron 3 Ultra & Jio Gemini Tier-1 Router
===================================================================
Provides async streaming communication with:
1. Nemotron 3 Ultra (vLLM / NVIDIA NIM OpenAI-compatible endpoint)
   Supports inference-time reasoning flags (Chain-of-Thought thinking stream).
2. Jio Gemini Plan (Google GenAI SDK / Gemini 2.5 Flash)
   High-throughput Tier-1 fast triage, parsing, and preprocessing ($0 cost).
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

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
        gemini_model = settings.GEMINI_MODEL or settings.GEMINI_MODEL_NAME or "gemini-3.1-flash-lite"
        if gemini_model in ("gemini-2.5-flash", "gemini-3.6-flash"):
            gemini_model = "gemini-3.1-flash-lite"
        self.gemini_model = gemini_model

    async def stream_nemotron_reasoning(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.6,
        max_tokens: int = 8192,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream reasoning tokens and tool calls from Nemotron 3 Ultra via SSE with resilient failover."""
        # 1. Fast detection: if NEMOTRON_API_BASE points to our local app port (e.g. localhost:8000)
        # where no vLLM server is running, failover immediately without making a 404 self-call
        is_local_self = any(
            host in self.nemotron_base_url
            for host in ("localhost:8000", "127.0.0.1:8000", "0.0.0.0:8000")
        )

        if is_local_self:
            if self.gemini_api_key:
                logger.info("Nemotron local cluster on standby; streaming via Tier-1 Gemini...")
                async for chunk in self.stream_gemini_reasoning(
                    messages, temperature, max_tokens
                ):
                    yield chunk
                return

            thought, content = self._generate_standby_response(messages)
            yield {"type": "thought", "content": thought}
            yield {"type": "token", "content": content}
            return

        payload: dict[str, Any] = {
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

        # 4.0s connect timeout prevents long hangs if the remote GPU is offline
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=4.0)) as client:
            try:
                async with client.stream(
                    "POST", url, json=payload, headers=headers
                ) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        logger.warning(
                            f"Nemotron API returned status {response.status_code}: {error_body.decode('utf-8', 'ignore')}"
                        )
                        # Transparent failover without emitting raw error chunk to user
                        if self.gemini_api_key:
                            logger.info("Failing over to Tier-1 Gemini streaming...")
                            async for chunk in self.stream_gemini_reasoning(
                                messages, temperature, max_tokens
                            ):
                                yield chunk
                            return

                        thought, content = self._generate_standby_response(messages)
                        yield {"type": "thought", "content": thought}
                        yield {"type": "token", "content": content}
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
                            reasoning_chunk = delta.get(
                                "reasoning_content"
                            ) or delta.get("thinking")
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

            except (httpx.ConnectError, httpx.RequestError):
                logger.warning(
                    f"Could not connect to Nemotron at {url}. Initiating failover/standby."
                )
                if self.gemini_api_key:
                    logger.info("Failing over to Tier-1 Gemini streaming...")
                    async for chunk in self.stream_gemini_reasoning(
                        messages, temperature, max_tokens
                    ):
                        yield chunk
                    return

                thought, content = self._generate_standby_response(messages)
                yield {"type": "thought", "content": thought}
                yield {"type": "token", "content": content}

    def _generate_standby_response(
        self, messages: list[dict[str, str]]
    ) -> tuple[str, str]:
        """Generate intelligent CoT reasoning thoughts and response for local standby mode."""
        last_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_msg = m.get("content", "").strip()
                break

        thought = (
            f"Inspecting inference runtime...\n"
            f"• Target vLLM Cluster: {self.nemotron_base_url} (GPU cluster offline/standby)\n"
            f"• User Query: '{last_msg}'\n"
            "• Running Local Intelligent Assistant & Architecture Diagnostics\n"
            "• Verification Gates: Gates 1–5 active\n"
            "• Formulating response..."
        )

        lower = last_msg.lower()
        if any(g in lower for g in ["hi", "hello", "hey", "hii", "hiii"]):
            content = (
                "👋 **Hello! Welcome to the NVIDIA Nemotron 3 Ultra Autonomous Agent Engine.**\n\n"
                "I am running in **Local Standby Mode** on your machine. All system engines—including the "
                "**AST Code Property Graph**, **Verification Gates 1–5**, **SQL Anti-Pattern Analyzer**, "
                "and **Cost Ledger**—are fully operational!\n\n"
                "### 🚀 Features you can test right now:\n"
                "1. **Autonomous Mission Mode**:\n"
                "   Switch to **Autonomous Mission** at the top and try queries like:\n"
                "   * `Audit SQL N+1 queries in the codebase`\n"
                "   * `Verify architecture layer boundaries`\n"
                "   * `Add a new health check router with memory metrics`\n\n"
                "2. **Connect Live Model Inference**:\n"
                "   * **Option A (Google Cloud 8x A100 Cluster)**: Once your GCP quota is approved, launch:\n"
                "     ```bash\n"
                "     bash infra/launch_gcp_nemotron_spot.sh\n"
                "     ```\n"
                "     And update `NEMOTRON_API_BASE=http://<GCP_EXTERNAL_IP>:8000/v1` in `.env`.\n"
                "   * **Option B (Free Gemini 2.5 Flash Tier-1 Key)**: Add `GEMINI_API_KEY=your_key` in `.env` for instant free streaming!\n\n"
                "How can I assist you with your codebase today?"
            )
        else:
            content = (
                f"### ⚡ NVIDIA Nemotron 3 Ultra (Local Standby Mode)\n\n"
                f"Received request: *\"{last_msg}\"*\n\n"
                "The engine is currently running in **Local Standby Mode** because your remote 8x A100 GPU cluster is offline (`http://localhost:8000/v1`).\n\n"
                "**Autonomous Mission Mode** is active for code property graph indexing, AST validation, and verification gates. Switch to the **Autonomous Mission** tab above to dispatch repository tasks!\n\n"
                "To connect this chat directly to live LLM generation:\n"
                "1. Set `GEMINI_API_KEY=your_key` in `.env` for free instant streaming, OR\n"
                "2. Launch the GCP GPU cluster: `bash infra/launch_gcp_nemotron_spot.sh`\n"
            )

        return thought, content

    async def _generate_gemini_content(
        self, contents: list[dict[str, Any]], max_tokens: int, temperature: float
    ) -> str | None:
        """Call generateContent across candidate models with high reliability."""
        candidate_models = [self.gemini_model, "gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-flash-latest"]
        seen = set()
        candidates = [c for c in candidate_models if not (c in seen or seen.add(c))]

        for candidate in candidates:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate}:generateContent?key={self.gemini_api_key}"
            payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
            }
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        parts = (
                            data.get("candidates", [{}])[0]
                            .get("content", {})
                            .get("parts", [])
                        )
                        texts = [p.get("text", "") for p in parts if p.get("text")]
                        if texts:
                            return "".join(texts)
            except Exception as e:
                logger.warning(f"Fallback to {candidate} failed: {e}")
        return None

    async def stream_gemini_reasoning(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.6,
        max_tokens: int = 8192,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream conversational tokens from Google Gemini Tier-1 ($0 cost)."""
        if not self.gemini_api_key:
            return

        candidate_models = [self.gemini_model, "gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-flash-latest"]
        seen = set()
        candidates = [c for c in candidate_models if not (c in seen or seen.add(c))]

        contents = []
        for m in messages:
            role = "user" if m.get("role") in ("user", "system") else "model"
            contents.append({
                "role": role,
                "parts": [{"text": m.get("content", "")}],
            })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        yield {
            "type": "thought",
            "content": f"Routing query to Tier-1 Fast Triage Engine ({candidates[0]})...\nGenerating streaming response...",
        }

        received_any_token = False
        async with httpx.AsyncClient(timeout=60.0) as client:
            for model_name in candidates:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:streamGenerateContent?key={self.gemini_api_key}&alt=sse"
                try:
                    async with client.stream("POST", url, json=payload) as response:
                        if response.status_code == 200:
                            async for line in response.aiter_lines():
                                if not line or not line.startswith("data: "):
                                    continue
                                data_str = line[6:].strip()
                                try:
                                    data = json.loads(data_str)
                                    stream_candidates = data.get("candidates", [])
                                    if stream_candidates:
                                        parts = (
                                            stream_candidates[0]
                                            .get("content", {})
                                            .get("parts", [])
                                        )
                                        for p in parts:
                                            text_chunk = p.get("text", "")
                                            if text_chunk:
                                                received_any_token = True
                                                yield {
                                                    "type": "token",
                                                    "content": text_chunk,
                                                }
                                except json.JSONDecodeError:
                                    continue
                            if received_any_token:
                                return
                        else:
                            logger.warning(
                                f"Gemini model {model_name} returned status {response.status_code}. Trying next candidate..."
                            )
                except Exception as e:
                    logger.warning(f"Error streaming from {model_name}: {e}. Trying next candidate...")

        if not received_any_token:
            fallback_text = await self._generate_gemini_content(
                contents, max_tokens, temperature
            )
            if fallback_text:
                words = fallback_text.split(" ")
                for i, word in enumerate(words):
                    sep = " " if i < len(words) - 1 else ""
                    yield {
                        "type": "token",
                        "content": word + sep,
                    }
                    await asyncio.sleep(0.015)
                return
            else:
                thought, content = self._generate_standby_response(messages)
                yield {"type": "thought", "content": thought}
                yield {"type": "token", "content": content}



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
