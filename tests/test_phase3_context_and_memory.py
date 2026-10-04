"""
Phase 3 Test Suite: Context Engine & Three-Tier Memory Architecture
===================================================================
Tests:
  1. L0-L10 Layered Context Budget Allocator (critical preservation, progressive trimming, prompt assembly).
  2. Automated Context Compactor (pressure levels, tool summarization, snapshot generation, validation).
  3. Three-Tier Memory Architecture (Session, Project, User) and MemoryDurabilityGate.
"""


from app.modules.intelligence.context.budget_allocator import (
    ContextBudgetAllocator,
    ContextLayer,
    LayeredContextBudgetConfig,
    LayerQuotas,
)
from app.modules.intelligence.context.compactor import (
    ContextCompactor,
    ContextPressureLevel,
    ToolResultPolicy,
)
from app.modules.intelligence.memory.schema import (
    MemoryCandidate,
)
from app.modules.intelligence.memory.three_tier_store import (
    MemoryDurabilityGate,
    ThreeTierMemoryStore,
)

# ==============================================================================
# 1. Context Budget Allocator Tests
# ==============================================================================

def test_context_budget_allocator_within_budget():
    allocator = ContextBudgetAllocator()
    layers = {
        ContextLayer.L0_SYSTEM: "You are an autonomous AI coding agent powered by Nemotron 3 Ultra.",
        ContextLayer.L1_CONSTITUTION: "Never push untested code. Always follow repo conventions.",
        ContextLayer.L2_PROJECT: "FastAPI + SQLAlchemy + PostgreSQL stack.",
        ContextLayer.L3_TASK: "Add customer subscription cancellation webhook.",
        ContextLayer.L4_REPO_MAP: "class WebhookRouter:\n  def handle_cancel(): pass",
        ContextLayer.L5_CODE: "def cancel_subscription(user_id: str): pass",
        ContextLayer.L6_DOCS_ADR: "ADR-005: Use idempotency keys for stripe webhooks.",
        ContextLayer.L7_TURNS: "User: Please implement the cancellation webhook.\nAssistant: I will inspect the schema.",
        ContextLayer.L8_TOOL_LOGS: "git status: On branch main, nothing to commit.",
        ContextLayer.L9_WORKING_MEM: "Active file: app/webhooks/stripe.py",
    }

    result = allocator.allocate(layers)

    assert result.within_budget is True
    assert result.total_prompt_tokens > 0
    assert result.output_reservation == 4000
    assert result.total_effective_tokens <= 32000
    assert len(result.trimmed_layers) == 0

    prompt = allocator.assemble_prompt_string(result)
    assert "=== SYSTEM & CORE PRINCIPLES ===" in prompt
    assert "=== CONSTITUTIONAL RULES & INVARIANTS ===" in prompt
    assert "=== CURRENT TASK OBJECTIVE ===" in prompt
    assert "=== PRIMARY CODE SNIPPETS & SYMBOLS ===" in prompt
    assert "cancel_subscription" in prompt


def test_context_budget_allocator_progressive_trimming_preserves_critical():
    # Configure tight prompt budget: max prompt = 500 tokens
    config = LayeredContextBudgetConfig(
        max_context_window=4500,
        quotas=LayerQuotas(L10_OUTPUT_RES=4000),  # leaves 500 tokens for prompt
    )
    allocator = ContextBudgetAllocator(config)

    # Bloat L8 (Tool logs) and L6 (Docs) with huge text
    huge_log = "Error in line: test failed. Detailed traceback line: foo\n" * 200
    huge_doc = "Standard API architecture guidelines documentation.\n" * 150
    critical_code = "def critical_implementation():\n    return True\n"
    critical_task = "Fix failing integration test in auth pipeline."

    layers = {
        ContextLayer.L0_SYSTEM: "Nemotron Core System Prompt.",
        ContextLayer.L1_CONSTITUTION: "Invariant: Zero regressions allowed.",
        ContextLayer.L2_PROJECT: "Nemotron Agent Engine backend.",
        ContextLayer.L3_TASK: critical_task,
        ContextLayer.L4_REPO_MAP: "repo map snippet",
        ContextLayer.L5_CODE: critical_code,
        ContextLayer.L6_DOCS_ADR: huge_doc,
        ContextLayer.L7_TURNS: "turn 1\nturn 2",
        ContextLayer.L8_TOOL_LOGS: huge_log,
        ContextLayer.L9_WORKING_MEM: "notes",
    }

    result = allocator.allocate(layers)

    # Total prompt tokens should be clamped within effective budget
    assert result.total_prompt_tokens <= 500 or result.within_budget is True
    # Non-critical layers should be trimmed
    assert ContextLayer.L8_TOOL_LOGS.value in result.trimmed_layers or ContextLayer.L6_DOCS_ADR.value in result.trimmed_layers
    # Critical layers MUST be preserved
    assert critical_code in result.layers[ContextLayer.L5_CODE.value]
    assert critical_task in result.layers[ContextLayer.L3_TASK.value]


# ==============================================================================
# 2. Context Compactor Tests
# ==============================================================================

def test_context_compactor_pressure_evaluation():
    compactor = ContextCompactor(compaction_threshold_ratio=0.75, default_max_window=10000)

    assert compactor.evaluate_pressure(3000, 10000) == ContextPressureLevel.GREEN
    assert compactor.evaluate_pressure(6500, 10000) == ContextPressureLevel.YELLOW
    assert compactor.evaluate_pressure(7800, 10000) == ContextPressureLevel.ORANGE
    assert compactor.evaluate_pressure(8800, 10000) == ContextPressureLevel.RED
    assert compactor.evaluate_pressure(9500, 10000) == ContextPressureLevel.CRITICAL

    # Threshold checks
    assert compactor.should_compact(7000, 10000) is False
    assert compactor.should_compact(7500, 10000) is True
    assert compactor.should_compact(8500, 10000) is True


def test_context_compactor_tool_classification_and_summarization():
    compactor = ContextCompactor()

    # Short output should be kept
    assert compactor.classify_tool_result("git_status", "clean working tree") == ToolResultPolicy.KEEP

    # Massive command output should be summarized
    huge_output = "Line info...\n" * 500 + "AssertionError: Expected 200 got 500\n" + "Line info...\n" * 500
    assert compactor.classify_tool_result("run_process", huge_output) == ToolResultPolicy.SUMMARIZE

    summary = compactor.summarize_tool_output("run_process", huge_output, max_lines=15)
    assert "AssertionError" in summary
    assert "lines summarized" in summary
    assert len(summary.splitlines()) <= 25


def test_context_compactor_snapshot_generation_and_validation():
    compactor = ContextCompactor()

    turns = [
        {"role": "user", "content": "Please implement the new billing/invoices.py service and wire it to app/main.py."},
        {"role": "assistant", "content": "I have created app/modules/billing/invoices.py. Decision: decided to use UUIDv7 for invoice IDs.\nDone: created app/modules/billing/invoices.py"},
        {"role": "user", "content": "Run tests now."},
        {"role": "assistant", "content": "Error: database connection timeout during test setup in billing/test_invoices.py"},
    ]
    tool_results = [
        {"tool_name": "apply_diff_patch", "file_path": "app/modules/billing/invoices.py", "output": "Patch applied successfully."},
        {"tool_name": "run_process", "exit_code": 1, "output": "pytest failed: ConnectionRefusedError: 5432"},
    ]

    snapshot = compactor.generate_compaction_snapshot(
        mission_id="m-890",
        goal="Implement billing invoice service",
        turns=turns,
        tool_results=tool_results,
        existing_state={"pending_steps": ["Mount invoice router in app/main.py", "Run pytest"]},
    )

    assert snapshot.mission_id == "m-890"
    assert snapshot.goal == "Implement billing invoice service"
    assert "app/modules/billing/invoices.py" in snapshot.files_modified
    assert any("invoice" in d.lower() or "decid" in d.lower() for d in snapshot.key_decisions)
    assert any("ConnectionRefusedError" in e or "timeout" in e for e in snapshot.active_errors)
    assert len(snapshot.pending_steps) == 2
    assert snapshot.token_count_before > 0
    assert snapshot.token_count_after > 0

    # Validation pass
    is_valid = compactor.validate_compaction(snapshot, previous_state={"files_modified": ["app/modules/billing/invoices.py"]})
    assert is_valid is True

    # Formatting verification
    md = compactor.format_snapshot_as_context(snapshot)
    assert "[CONTEXT COMPACTION SNAPSHOT: ACTIVE TASK STATE]" in md
    assert "app/modules/billing/invoices.py" in md
    assert "Mount invoice router" in md


# ==============================================================================
# 3. Three-Tier Memory Store & Durability Gate Tests
# ==============================================================================

def test_memory_durability_gate():
    # Transient candidates that MUST be rejected
    rejected_cases = [
        MemoryCandidate(title="Typo fix", content="fixed typo on line 42", category="bug_fix"),
        MemoryCandidate(title="UI tweak", content="changed button color to red", category="ui"),
        MemoryCandidate(title="Temporary test", content="temp debug print statement", category="debug"),
        MemoryCandidate(title="Too short", content="hello", category="general"),
        MemoryCandidate(title="Low confidence", content="Always use pytest fixtures", confidence=0.4),
    ]

    for cand in rejected_cases:
        is_durable, reason = MemoryDurabilityGate.evaluate_candidate(cand)
        assert is_durable is False, f"Expected {cand.title} to be rejected, but was accepted: {reason}"

    # Durable candidates that MUST be accepted
    accepted_cases = [
        MemoryCandidate(
            title="FastAPI Async Database Sessions",
            content="Always use AsyncSession with async context manager to prevent database connection leaks.",
            category="database",
            confidence=0.9,
        ),
        MemoryCandidate(
            title="Pydantic V2 Migration Rule",
            content="Never use .dict() on Pydantic v2 models; always use .model_dump() instead.",
            category="convention",
            confidence=0.85,
        ),
        MemoryCandidate(
            title="PostgreSQL Column Naming Standard",
            content="All relational database columns must follow snake_case naming conventions.",
            category="architecture",
            confidence=0.95,
        ),
    ]

    for cand in accepted_cases:
        is_durable, reason = MemoryDurabilityGate.evaluate_candidate(cand)
        assert is_durable is True, f"Expected {cand.title} to be accepted, but was rejected: {reason}"


def test_three_tier_memory_store_lifecycle(tmp_path):
    user_mem_path = str(tmp_path / "user_memory.json")
    store = ThreeTierMemoryStore(workspace_root=str(tmp_path), user_storage_path=user_mem_path)

    # 1. Tier 1: Session Memory (Ephemeral)
    session = store.get_session_memory("mission-42")
    session.active_files = ["app/auth/jwt.py"]
    session.active_errors = ["JWT expired signature error"]
    session.scratchpad = "Investigating token expiry clock drift."
    store.save_session_memory(session)

    # Read back session memory
    reloaded_session = store.get_session_memory("mission-42")
    assert reloaded_session.active_files == ["app/auth/jwt.py"]
    assert reloaded_session.active_errors == ["JWT expired signature error"]

    # 2. Tier 2: Project Memory (Durable)
    cand_rejected = MemoryCandidate(
        title="button style",
        content="changed button color to green",
        category="ui",
    )
    saved_rej, reason_rej = store.add_project_memory(cand_rejected)
    assert saved_rej is False

    cand_accepted = MemoryCandidate(
        title="Pytest Fixture Scope Convention",
        content="Always set scope='function' on database session fixtures to ensure test isolation.",
        category="convention",
        confidence=0.9,
    )
    saved_acc, reason_acc = store.add_project_memory(cand_accepted)
    assert saved_acc is True
    assert "PM-001" in reason_acc

    # Query project memories
    queried = store.query_project_memories("database fixtures")
    assert len(queried) == 1
    assert queried[0].title == "Pytest Fixture Scope Convention"

    # 3. Tier 3: User Memory (Developer Preferences)
    store.set_user_preference("commit_style", "conventional_commits", category="git")
    store.set_user_preference("tab_size", "4", category="editor")

    assert store.get_user_preference("commit_style") == "conventional_commits"
    all_prefs = store.get_all_user_preferences()
    assert all_prefs["tab_size"] == "4"

    # 4. Context Assembly across all 3 tiers
    context_str = store.assemble_memory_context("mission-42", query="fixtures")
    assert "Active Session Working Memory" in context_str
    assert "app/auth/jwt.py" in context_str
    assert "Repository Conventions & Knowledge" in context_str
    assert "Pytest Fixture Scope Convention" in context_str
    assert "Developer Preferences" in context_str
    assert "conventional_commits" in context_str

    # 5. Clear Session Memory on mission completion
    store.clear_session_memory("mission-42")
    cleared_session = store.get_session_memory("mission-42")
    assert cleared_session.active_files == []
    # But Project & User memories remain durable!
    assert len(store.get_project_memories()) == 1
    assert store.get_user_preference("commit_style") == "conventional_commits"
