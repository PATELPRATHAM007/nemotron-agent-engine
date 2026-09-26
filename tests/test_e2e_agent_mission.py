"""
End-to-End Autonomous Agent Mission & Repository Intelligence Test
==================================================================
Simulates a complete real-world coding mission executing across all 8 phases:
  Phase 1: Deterministic AST & Code Fingerprinting
  Phase 2: Multi-Layer Knowledge Graph
  Phase 3: Change Impact Analysis & Scope Lock
  Phase 4: Context Budget Manager
  Phase 5: Multi-Role Agent Orchestrator
  Phase 6: 8-Gate Verification Pipeline & Auto-Debugger
  Phase 7: Persistent Memory & Constitution
  Phase 8: Incremental File Watcher
"""

import pytest

from app.constitution.scaffold import ConstitutionScaffolder
from app.intelligence.context.budget_manager import ContextBudget, ContextBudgetManager
from app.intelligence.graph.repo_graph import RepoGraph
from app.intelligence.graph.schema import GraphNode, NodeKind
from app.intelligence.impact.scope_lock import ScopeViolationError, TaskScope
from app.intelligence.indexing.watcher import IncrementalFileWatcher
from app.intelligence.memory.memory_store import InstitutionalMemoryStore
from app.intelligence.memory.schema import HistoricalLesson, LessonCategory
from app.modules.agent.orchestrator import MissionOrchestrator
from app.modules.agent.roles.base import AgentState, TestRunOutput
from app.modules.agent.verification.gates import VerificationPipeline


def test_incremental_watcher_handles_whitespace_and_logic_changes(tmp_path):
    f = tmp_path / "service.py"
    f.write_text("def process():\n    return 42\n")

    watcher = IncrementalFileWatcher(str(tmp_path))

    # Initial index
    res1 = watcher.handle_file_change("service.py")
    assert res1["action"] == "reindexed_ast_and_symbols"

    # Whitespace change only
    f.write_text("def process():\n\n    # Just a comment\n    return 42\n\n")
    res2 = watcher.handle_file_change("service.py")
    assert res2["action"] == "fingerprint_updated_only"
    assert res2["reason"] == "ast_invariant_whitespace_or_comments"

    # Actual logic change
    f.write_text("def process():\n    return 100\n\ndef new_helper():\n    pass\n")
    res3 = watcher.handle_file_change("service.py")
    assert res3["action"] == "reindexed_ast_and_symbols"
    assert res3["functions_count"] == 2


@pytest.mark.asyncio
async def test_full_mission_e2e_lifecycle(tmp_path):
    # 1. Phase 7: Scaffold Constitution
    scaffolder = ConstitutionScaffolder(str(tmp_path))
    scaffold_files = scaffolder.scaffold()
    assert "coding_standards.md" in scaffold_files

    # 2. Phase 1 & 2: Setup Repo File and Knowledge Graph
    service_file = tmp_path / "payment_service.py"
    service_file.write_text(
        "class PaymentService:\n"
        "    def charge(self, amount: int) -> bool:\n"
        "        if amount <= 0:\n"
        "            raise ValueError('Invalid amount')\n"
        "        return True\n"
    )

    graph = RepoGraph()
    graph.add_node(
        GraphNode(
            id="file:payment_service.py",
            name="payment_service.py",
            kind=NodeKind.FILE,
            file_path="payment_service.py",
        )
    )
    graph.add_node(
        GraphNode(
            id="symbol:PaymentService",
            name="PaymentService",
            kind=NodeKind.SYMBOL,
            file_path="payment_service.py",
        )
    )

    # 3. Phase 3: Scope Lock
    scope = TaskScope(
        task_id="mission-billing-01",
        primary_feature="billing",
        allowed_edit_files={"payment_service.py"},
        target_test_files={"test_payment.py"},
    )
    # Permitted
    assert scope.validate_edit("payment_service.py") is True
    # Forbidden
    with pytest.raises(ScopeViolationError):
        scope.validate_edit("unrelated_auth.py")

    # 4. Phase 4: Context Budget Assembly
    budget = ContextBudgetManager(ContextBudget(max_total_tokens=4000))
    prompt_payload = budget.assemble_payload(
        system_instructions="You are Nemotron Coder.",
        task_prompt="Support discount calculation in payment service.",
        architecture_context=scaffolder.load_rule("architecture_rules"),
        feature_subgraph_str="Feature: Billing",
        target_code=service_file.read_text(),
        test_context="def test_charge(): pass",
        lessons_context="Always handle currency edge cases.",
    )
    assert prompt_payload["within_budget"] is True
    assert prompt_payload["total_tokens"] <= 4000

    # 5. Phase 5 & 6: Orchestration and Verification
    orchestrator = MissionOrchestrator(
        workspace_root=str(tmp_path),
        max_auto_fix_attempts=3,
    )

    # Mock test execution simulating 1 debug attempt and final success
    attempt_counter = [0]

    async def mock_test_runner(attempt: int):
        attempt_counter[0] += 1
        if attempt == 0:
            return TestRunOutput(
                passed=False, failure_trace="AssertionError: discount not applied"
            )
        return TestRunOutput(passed=True, total_tests=2, passed_tests=2, failed_tests=0)

    events = []
    async for event in orchestrator.execute_mission_pipeline(
        mission_id="mission-billing-01",
        goal="Add discount coupon support to PaymentService",
        initial_files=["payment_service.py"],
        test_runner_fn=mock_test_runner,
    ):
        events.append(event)

    assert orchestrator.state == AgentState.COMPLETED
    assert orchestrator.debug_attempts == 1

    # 6. Verify 8-Gate Pipeline on modified file
    pipeline = VerificationPipeline(str(tmp_path))
    report = pipeline.run_all_gates(
        modified_files=["payment_service.py"],
        scope=scope,
        skip_tests=True,
    )
    assert report.all_passed is True

    # 7. Record Historical Lesson
    memory_store = InstitutionalMemoryStore(str(tmp_path))
    memory_store.add_lesson(
        HistoricalLesson(
            lesson_id="L-DISCOUNT-01",
            category=LessonCategory.BUG_FIX,
            title="Apply discount before calculating total tax",
            description="Discount must be subtracted prior to computing percentage sales tax.",
            trigger_pattern="discount",
            resolution="Compute subtotal = original - discount before tax.",
            confidence_score=0.9,
        )
    )
    queried = memory_store.query_lessons("discount calculation")
    assert len(queried) == 1
    assert queried[0].lesson_id == "L-DISCOUNT-01"
