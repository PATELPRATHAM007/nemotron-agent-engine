"""
Nemotron Autonomous Agent Module
================================
Provides the agent engine, sandboxed tool execution, schemas, and routes.
"""

from app.modules.agent.classifier import (
    DynamicTaskClassifier,
    TaskWorkflow,
    task_classifier,
)
from app.modules.agent.engine import agent_engine
from app.modules.agent.react_engine import ReActEngine
from app.modules.agent.routes import router as agent_router
from app.modules.agent.subagents.coordinator import (
    SubagentCoordinator,
    SubagentRole,
    subagent_coordinator,
)

__all__ = [
    "DynamicTaskClassifier",
    "ReActEngine",
    "SubagentCoordinator",
    "SubagentRole",
    "TaskWorkflow",
    "agent_engine",
    "agent_router",
    "subagent_coordinator",
    "task_classifier",
]

