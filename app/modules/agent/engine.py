"""
Autonomous Agent Engine for NVIDIA Nemotron 3 Ultra
===================================================
Executes the autonomous loop:
  Plan -> Reason -> Call Tool -> Observe -> Self-Correct -> Generate Output
Yields structured events for real-time Server-Sent Events (SSE) streaming.
"""

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from app.core.llm_gateway import llm_gateway
from app.core.logging_config import get_logger
from app.modules.agent.tools.registry import TOOLS_SCHEMA, dispatch_tool

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an elite autonomous software engineering and reasoning agent powered by NVIDIA Nemotron 3 Ultra (550B LatentMoE).
Your strengths include frontier multi-step reasoning, repo-level code modification, tool use, and self-correction.

Rules:
1. Always analyze the situation deeply in your reasoning thoughts before calling tools.
2. Break down complex tasks into clear, executable steps.
3. When modifying code, review diffs to ensure no unintended breaking changes occur.
4. If a tool execution fails or produces an error, carefully inspect the stack trace, reason about the root cause, and correct your approach.
5. Provide clear, concise final summaries when goals are accomplished.
"""


class AgentEngine:
    """Orchestrates autonomous multi-turn reasoning and tool execution loops."""

    async def execute_mission(
        self,
        mission_id: str,
        goal: str,
        max_iterations: int = 15,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Run an autonomous mission and yield real-time SSE event objects."""
        logger.info(f"Starting mission {mission_id}: {goal[:100]}")

        # Yield mission started event
        yield {
            "type": "mission_started",
            "mission_id": mission_id,
            "goal": goal,
        }

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": goal},
        ]

        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            yield {
                "type": "iteration_start",
                "iteration": iteration,
                "max_iterations": max_iterations,
            }

            accumulated_content = ""
            tool_calls_detected: list[dict[str, Any]] = []

            # 1. Stream Nemotron reasoning & token generation
            async for chunk in llm_gateway.stream_nemotron_reasoning(
                messages=messages,
                tools=TOOLS_SCHEMA,
            ):
                chunk_type = chunk.get("type")

                if chunk_type == "thought":
                    yield {
                        "type": "thought",
                        "content": chunk.get("content", ""),
                    }

                elif chunk_type == "token":
                    content = chunk.get("content", "")
                    accumulated_content += content
                    yield {
                        "type": "token",
                        "content": content,
                    }

                elif chunk_type == "tool_call_delta":
                    deltas = chunk.get("tool_calls", [])
                    for d in deltas:
                        idx = d.get("index", 0)
                        if idx >= len(tool_calls_detected):
                            tool_calls_detected.append(
                                {
                                    "id": d.get("id", str(uuid.uuid4())),
                                    "name": d.get("function", {}).get("name", ""),
                                    "arguments": "",
                                }
                            )
                        func = d.get("function", {})
                        if func.get("name"):
                            tool_calls_detected[idx]["name"] = func.get("name")
                        if func.get("arguments"):
                            tool_calls_detected[idx]["arguments"] += func.get(
                                "arguments"
                            )

                elif chunk_type == "warning" or chunk_type == "error":
                    yield chunk

            # Append assistant response to message history
            messages.append({"role": "assistant", "content": accumulated_content})

            # If no tool calls were requested, mission has produced its final response
            if not tool_calls_detected:
                yield {
                    "type": "mission_completed",
                    "mission_id": mission_id,
                    "final_response": accumulated_content,
                }
                break

            # 2. Execute requested tools in sandbox
            for tool in tool_calls_detected:
                tool_name = tool.get("name", "")
                args_str = tool.get("arguments", "{}")
                try:
                    tool_args = json.loads(args_str) if args_str else {}
                except json.JSONDecodeError:
                    tool_args = {}

                yield {
                    "type": "tool_start",
                    "tool": tool_name,
                    "arguments": tool_args,
                }

                # Dispatch tool
                observation = await dispatch_tool(tool_name, tool_args)

                yield {
                    "type": "tool_observation",
                    "tool": tool_name,
                    "observation": observation,
                }

                # Feed observation back to Nemotron context
                messages.append(
                    {
                        "role": "user",
                        "content": f"[Tool Observation for {tool_name}]: {json.dumps(observation)}",
                    }
                )


agent_engine = AgentEngine()
