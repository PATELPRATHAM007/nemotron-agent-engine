#!/usr/bin/env python3
"""
Google Engine & Nemotron 3 Ultra Connectivity Diagnostics Tool
=============================================================
Tests live communication between the local repository intelligence engine
and your Google Cloud / Google Drive inference endpoints:
  1. Ping vLLM / NVIDIA NIM OpenAI endpoint ($NEMOTRON_API_BASE/models)
  2. Test streaming inference and CoT reasoning tokens
  3. Ping Google Gemini Tier-1 API if GEMINI_API_KEY is configured
"""

import asyncio
import os
import sys
import time

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import httpx

from app.core.config import settings
from app.core.llm_gateway import llm_gateway


async def check_vllm_endpoint() -> bool:
    print("\n" + "=" * 65)
    print("📡 [1/2] CHECKING GOOGLE COMPUTE ENGINE (vLLM / NEMOTRON ENDPOINT)")
    print("=" * 65)
    print(f"Target URL:    {settings.NEMOTRON_API_BASE}")
    print(f"Model Name:    {settings.NEMOTRON_MODEL_NAME}")
    print(f"Thinking Mode: {settings.NEMOTRON_ENABLE_THINKING}")

    models_url = f"{settings.NEMOTRON_API_BASE.rstrip('/')}/models"
    t0 = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(models_url)
            elapsed_ms = (time.perf_counter() - t0) * 1000

            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("id") for m in data.get("data", [])]
                print(f"✅ Connection SUCCESSFUL in {elapsed_ms:.1f}ms!")
                print(f"   Available models on remote host: {models}")
            else:
                print(
                    f"⚠️ Server reached but returned HTTP {resp.status_code}: {resp.text}"
                )
                return False

    except httpx.ConnectError:
        print(f"❌ Connection Refused: Cannot connect to {settings.NEMOTRON_API_BASE}")
        print("   👉 If your GCP instance is running, check:")
        print(
            "      1. Is vLLM running on port 8000? (run: curl http://localhost:8000/v1/models on the VM)"
        )
        print(
            "      2. Is GCP firewall allowing port 8000? (gcloud compute firewall-rules create allow-vllm-8000 ...)"
        )
        print(
            "      3. Have you updated NEMOTRON_API_BASE in .env with your instance's external IP?"
        )
        return False
    except httpx.TimeoutException:
        print("⏳ Connection Timed Out: Remote host did not respond within 10 seconds.")
        return False
    except (httpx.HTTPError, OSError) as e:
        print(f"❌ Error testing endpoint: {e}")
        return False

    # Test Live Streaming
    print("\n⚡ Testing Live Streaming Reasoning from Nemotron...")
    test_messages = [
        {"role": "system", "content": "You are Nemotron 3 Ultra. Reply in 1 sentence."},
        {
            "role": "user",
            "content": "Ping test: confirm you are active and ready for agent missions.",
        },
    ]

    tokens_received = 0
    thoughts_received = 0
    t_start = time.perf_counter()

    async for chunk in llm_gateway.stream_nemotron_reasoning(
        test_messages, max_tokens=100
    ):
        chunk_type = chunk.get("type")
        content = chunk.get("content", "")

        if chunk_type == "thought":
            thoughts_received += 1
            sys.stdout.write(f"\033[90m{content}\033[0m")
            sys.stdout.flush()
        elif chunk_type == "token":
            tokens_received += 1
            sys.stdout.write(content)
            sys.stdout.flush()
        elif chunk_type == "error":
            print(f"\n❌ Stream Error: {content}")
            return False
        elif chunk_type == "warning":
            print(f"\n⚠️ Stream Warning: {content}")

    total_time = time.perf_counter() - t_start
    tps = tokens_received / max(0.01, total_time)
    print(
        f"\n\n✅ Stream Complete in {total_time:.2f}s ({tokens_received} tokens, {thoughts_received} thoughts, {tps:.1f} tokens/sec)"
    )

    from app.intelligence.cost import CostCalculator, PricingMode, TokenUsageBreakdown

    calc = CostCalculator()
    sample_usage = TokenUsageBreakdown(
        prompt_tokens=25,
        completion_tokens=tokens_received,
        thinking_tokens=thoughts_received,
        total_tokens=25 + tokens_received + thoughts_received,
    )
    spot_cost = calc.calculate_cost(
        sample_usage, duration_seconds=total_time, mode=PricingMode.GCP_SPOT
    )
    api_cost = calc.calculate_cost(sample_usage, mode=PricingMode.SERVERLESS_API)

    print(
        f"💰 Estimated Query Cost: ${spot_cost:.6f} (GCP Spot Amortized) | ${api_cost:.6f} (Serverless API)"
    )
    return True


async def check_gemini_endpoint() -> bool:
    print("\n" + "=" * 65)
    print("🌐 [2/2] CHECKING GOOGLE GEMINI TIER-1 FAST ROUTER")
    print("=" * 65)

    if not settings.GEMINI_API_KEY:
        print("ℹ️  GEMINI_API_KEY is not configured in .env (skipping Tier-1 check).")
        print(
            "   If you have a Google AI Studio key, add GEMINI_API_KEY=AIza... to .env."
        )
        return True

    print(f"Model: {settings.GEMINI_MODEL_NAME}")
    t0 = time.perf_counter()
    reply = await llm_gateway.run_gemini_fast_triage(
        "Respond with 'OK' if you are active."
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    if "OK" in reply or len(reply) > 0 and "error" not in reply.lower():
        print(f"✅ Gemini Tier-1 API connection SUCCESSFUL in {elapsed_ms:.1f}ms!")
        print(f"   Response: {reply.strip()[:100]}")
        return True
    else:
        print(f"❌ Gemini check returned error: {reply}")
        return False


async def main():
    print("🚀 NVIDIA NEMOTRON 3 ULTRA & GOOGLE ENGINE CONNECTIVITY CHECK")
    vllm_ok = await check_vllm_endpoint()
    gemini_ok = await check_gemini_endpoint()

    print("\n" + "=" * 65)
    print("📊 CONNECTIVITY SUMMARY")
    print("=" * 65)
    print(
        f"1. Google Compute Engine vLLM (Nemotron): {'🟢 READY' if vllm_ok else '🔴 OFFLINE / UNCONFIGURED'}"
    )
    print(
        f"2. Google Gemini Tier-1 API:             {'🟢 READY' if gemini_ok else '⚪ SKIPPED / NOT SET'}"
    )
    print("=" * 65 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
