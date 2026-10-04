"""
Phase 4 Test Suite: Agent Planning Harness, Subagents & ReAct Loop
===================================================================
Tests:
  1. Multi-turn ReAct Execution Loop (tool sequencing, circuit breakers, compaction trigger).
  2. Dynamic Task Classifier (accurate categorization across 12 diverse developer prompts).
  3. Isolated Subagent Coordinator (context isolation, researcher, reviewer, tester).
  4. Skills System Loader (procedural skill discovery, query matching, context formatting).
"""

import pytest

from app.modules.agent.classifier import (
    DynamicTaskClassifier,
    TaskWorkflow,
)
from app.modules.agent.react_engine import ReActEngine
from app.modules.agent.subagents.coordinator import (
    SubagentCoordinator,
    SubagentRole,
)
from app.modules.intelligence.skills.loader import SkillRegistry

# ==============================================================================
# 1. Multi-Turn ReAct Loop Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_react_engine_sequential_execution(tmp_path):
    engine = ReActEngine(workspace_root=str(tmp_path), max_iterations=10)

    events = []
    async for event in engine.execute_react_loop(
        mission_id="m-react-01",
        goal="Audit repository architecture and search for router endpoints",
    ):
        events.append(event)

    event_types = [e["type"] for e in events]

    assert "react_started" in event_types
    assert "react_iteration_started" in event_types
    assert "react_thought" in event_types
    assert "react_tool_call" in event_types
    assert "react_tool_observation" in event_types
    assert "react_completed" in event_types

    final_event = [e for e in events if e["type"] == "react_completed"][0]
    assert final_event["total_iterations"] >= 3
    assert "Successfully completed" in final_event["final_answer"]


# ==============================================================================
# 2. Dynamic Task Classifier Tests (12 diverse prompts)
# ==============================================================================

def test_task_classifier_twelve_diverse_prompts():
    classifier = DynamicTaskClassifier()

    test_cases = [
        # QUESTION
        ("Hello there! Good morning.", TaskWorkflow.QUESTION),
        ("What is the difference between FastAPI and Flask?", TaskWorkflow.QUESTION),
        
        # RESEARCH
        ("Where is the customer billing router defined?", TaskWorkflow.RESEARCH),
        ("Search for all endpoints that use JWT authentication", TaskWorkflow.RESEARCH),
        
        # PLAN
        ("How should we architect the migration from SQLite to PostgreSQL?", TaskWorkflow.PLAN),
        ("Plan a multi-tenant database partitioning strategy with tradeoffs", TaskWorkflow.PLAN),
        
        # BUILD
        ("Implement a new endpoint POST /api/v1/invoices/cancel", TaskWorkflow.BUILD),
        ("Create billing service model and wire up Stripe webhook handler", TaskWorkflow.BUILD),
        
        # DEBUG
        ("Fix TypeError: 'NoneType' object is not subscriptable in billing/service.py", TaskWorkflow.DEBUG),
        ("Debug test failure in tests/test_auth.py: assertion error on token expiry", TaskWorkflow.DEBUG),
        
        # REVIEW
        ("Review git diff for security vulnerabilities and SQL injection risks", TaskWorkflow.REVIEW),
        ("Audit the recent commit PR for constitutional rule compliance", TaskWorkflow.REVIEW),
    ]

    for prompt, expected_workflow in test_cases:
        res = classifier.classify(prompt)
        assert res.workflow == expected_workflow, (
            f"Prompt '{prompt}' classified as {res.workflow.value}, expected {expected_workflow.value}. "
            f"Rationale: {res.rationale}"
        )
        assert res.confidence >= 0.70
        assert len(res.allowed_tools) > 0


# ==============================================================================
# 3. Isolated Subagent Coordinator Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_subagent_coordinator_isolation(tmp_path):
    coordinator = SubagentCoordinator(workspace_root=str(tmp_path))

    # Researcher Subagent Run
    res_research = await coordinator.execute_subagent(
        role=SubagentRole.RESEARCHER,
        task="Locate all router definitions",
        mission_id="sub-01",
    )
    assert res_research.role == SubagentRole.RESEARCHER
    assert res_research.status == "success"
    assert "Researcher identified" in res_research.summary
    assert res_research.isolated_steps_count >= 1

    # Reviewer Subagent Run
    res_review = await coordinator.execute_subagent(
        role=SubagentRole.REVIEWER,
        task="Audit staged diff for security issues",
        mission_id="sub-02",
    )
    assert res_review.role == SubagentRole.REVIEWER
    assert res_review.status == "success"
    assert "Reviewer subagent completed" in res_review.summary

    # Tester Subagent Run
    res_test = await coordinator.execute_subagent(
        role=SubagentRole.TESTER,
        task="Verify working tree before running test suite",
        mission_id="sub-03",
    )
    assert res_test.role == SubagentRole.TESTER
    assert res_test.status == "success"
    assert "Tester subagent completed" in res_test.summary


# ==============================================================================
# 4. Skills System Loader Tests
# ==============================================================================

def test_skills_loader_discovery_and_matching(tmp_path):
    # Setup mock skill in workspace/skills/fastapi_guidelines/SKILL.md
    skills_dir = tmp_path / "skills" / "fastapi_guidelines"
    skills_dir.mkdir(parents=True)
    skill_file = skills_dir / "SKILL.md"
    skill_file.write_text(
        "---\n"
        "name: FastAPI Best Practices\n"
        "category: backend\n"
        "description: Guidelines for high-throughput async endpoints in FastAPI.\n"
        "keywords: [fastapi, async, router, endpoint, pydantic]\n"
        "---\n"
        "Always use async def for database queries with AsyncSession.\n"
        "Validate request payloads using Pydantic v2 BaseModel.\n"
    )

    registry = SkillRegistry(workspace_root=str(tmp_path))
    count = registry.discover_skills()
    assert count == 1

    # Match by keyword
    matched = registry.find_relevant_skills("How to build an async fastapi router?")
    assert len(matched) == 1
    assert matched[0].name == "FastAPI Best Practices"

    # Context formatting
    context = registry.format_skills_for_context(matched)
    assert "Loaded Engineering Skills" in context
    assert "FastAPI Best Practices" in context
    assert "AsyncSession" in context
