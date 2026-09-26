import pytest

from app.modules.agent.orchestrator import MissionOrchestrator
from app.modules.agent.roles.base import (
    AgentState,
    TestRunOutput,
)
from app.modules.agent.roles.coder import CoderRole
from app.modules.agent.roles.debugger import DebuggerRole
from app.modules.agent.roles.planner import PlannerRole
from app.modules.agent.roles.reviewer import ReviewerRole
from app.modules.agent.roles.tester import TesterRole


def test_agent_roles_prompts_and_context():
    planner = PlannerRole()
    p_msgs = planner.build_context_prompt(
        "Add OAuth", {"feature_context": "Auth Module"}
    )
    assert len(p_msgs) == 2
    assert "Planner" in planner.name
    assert "Add OAuth" in p_msgs[1]["content"]

    reviewer = ReviewerRole()
    r_msgs = reviewer.build_context_prompt("Add OAuth", {"plan": None})
    assert len(r_msgs) == 2
    assert "Reviewer" in reviewer.name

    coder = CoderRole()
    c_msgs = coder.build_context_prompt("Fix token", {"target_files": ["auth.py"]})
    assert "auth.py" in c_msgs[1]["content"]

    tester = TesterRole()
    t_msgs = tester.build_context_prompt("Verify token", {"target_files": ["auth.py"]})
    assert "Verify token" in t_msgs[1]["content"]

    debugger = DebuggerRole(max_attempts=3)
    d_msgs = debugger.build_context_prompt(
        "Fix 500 error", {"failure_trace": "ZeroDivisionError", "attempt_number": 1}
    )
    assert "ZeroDivisionError" in d_msgs[1]["content"]


@pytest.mark.asyncio
async def test_orchestrator_clean_mission_success(tmp_path):
    orchestrator = MissionOrchestrator(workspace_root=str(tmp_path))
    events = []

    async for event in orchestrator.execute_mission_pipeline(
        mission_id="m-001",
        goal="Add health check ping endpoint",
    ):
        events.append(event)

    states = [e["to_state"] for e in events if e.get("type") == "state_transition"]
    assert states == [
        AgentState.PLANNING.value,
        AgentState.REVIEWING.value,
        AgentState.CODING.value,
        AgentState.TESTING.value,
        AgentState.COMMITTING.value,
        AgentState.COMPLETED.value,
    ]
    assert orchestrator.state == AgentState.COMPLETED


@pytest.mark.asyncio
async def test_orchestrator_debugging_recovery(tmp_path):
    orchestrator = MissionOrchestrator(workspace_root=str(tmp_path))
    events = []

    # Test runner that fails on attempt 0, passes on attempt 1
    async def mock_test_runner(attempt: int):
        if attempt == 0:
            return TestRunOutput(
                passed=False, failure_trace="AssertionError: 200 != 404"
            )
        return TestRunOutput(passed=True, total_tests=3, passed_tests=3, failed_tests=0)

    async for event in orchestrator.execute_mission_pipeline(
        mission_id="m-002",
        goal="Fix route status code",
        test_runner_fn=mock_test_runner,
    ):
        events.append(event)

    states = [e["to_state"] for e in events if e.get("type") == "state_transition"]
    assert AgentState.DEBUGGING.value in states
    assert orchestrator.state == AgentState.COMPLETED
    assert orchestrator.debug_attempts == 1


@pytest.mark.asyncio
async def test_orchestrator_bounded_rollback_on_persistent_failure(tmp_path):
    orchestrator = MissionOrchestrator(
        workspace_root=str(tmp_path),
        max_auto_fix_attempts=3,
        auto_rollback_on_failure=True,
    )
    events = []

    # Test runner that always fails
    async def always_failing_runner(attempt: int):
        return TestRunOutput(
            passed=False, failure_trace=f"Fatal error at attempt {attempt}"
        )

    async for event in orchestrator.execute_mission_pipeline(
        mission_id="m-003",
        goal="Impossible task that always fails tests",
        test_runner_fn=always_failing_runner,
    ):
        events.append(event)

    assert orchestrator.state == AgentState.ROLLED_BACK
    # Should have attempted exactly 3 times before rollback
    debug_events = [
        e
        for e in events
        if e.get("type") == "role_output" and e.get("role") == "Debugger"
    ]
    assert len(debug_events) == 3


@pytest.mark.asyncio
async def test_orchestrator_human_approval_gate_for_database_mutation(tmp_path):
    orchestrator = MissionOrchestrator(workspace_root=str(tmp_path))

    # 1. First run without approval token -> HALTED
    events_halted = []
    async for event in orchestrator.execute_mission_pipeline(
        mission_id="m-db-01",
        goal="Run destructive migration on database",
        is_db_mutation=True,
    ):
        events_halted.append(event)

    assert orchestrator.state == AgentState.FAILED
    approval_events = [e for e in events_halted if e.get("type") == "approval_required"]
    assert len(approval_events) == 1
    req_id = approval_events[0]["request"]["request_id"]

    # 2. Human reviews and grants approval token
    approval = orchestrator.approval_gates.submit_decision(
        req_id, approved=True, notes="DB changes approved."
    )
    token = approval.approval_token

    # 3. Second run with valid approval token -> PROCEEDS TO COMPLETION
    events_approved = []
    async for event in orchestrator.execute_mission_pipeline(
        mission_id="m-db-01",
        goal="Run destructive migration on database",
        is_db_mutation=True,
        human_approval_token=token,
    ):
        events_approved.append(event)

    assert orchestrator.state == AgentState.COMPLETED
