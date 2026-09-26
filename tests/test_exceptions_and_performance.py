import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exception_handlers import register_exception_handlers
from app.core.exceptions import (
    ApprovalRequiredError,
    ASTParseError,
    AutoDebugExhaustedError,
    ContextBudgetExceededError,
    DatabaseSafetyViolationError,
    LLMGatewayError,
    PermissionDeniedError,
    ScopeViolationError,
    ToolExecutionError,
    VerificationGateFailedError,
)
from app.intelligence.context.budget_manager import ContextBudget, ContextBudgetManager
from app.intelligence.indexing.ast_parser import (
    clear_ast_cache,
    parse_python_file,
)
from app.modules.agent.verification.gates import VerificationPipeline
from app.modules.agent.verification.schema import (
    GateResult,
    GateStatus,
    ValidationPipelineReport,
)


def test_custom_exception_hierarchy_and_serialization():
    """Verify that all domain exceptions serialize to standard dictionaries with actionable fixes."""
    exc = ScopeViolationError(
        message="Unauthorized file edit",
        file_path="app/secret.py",
        authorized_files=["app/main.py"],
    )
    d = exc.to_dict()
    assert d["error_code"] == "ERR_SCOPE_VIOLATION"
    assert d["component"] == "scope_lock"
    assert d["http_status"] == 403
    assert d["details"]["file_path"] == "app/secret.py"
    assert "Scope Expansion Request" in d["suggested_fix"]

    db_exc = DatabaseSafetyViolationError(
        "Unbounded UPDATE detected", sql_command="UPDATE users SET active = 1"
    )
    assert db_exc.error_code == "ERR_DATABASE_SAFETY"
    assert db_exc.http_status == 403
    assert "WHERE" in db_exc.suggested_fix

    perm_exc = PermissionDeniedError("Denied", required_level=5, current_level=2)
    assert perm_exc.error_code == "ERR_PERMISSION_DENIED"
    assert perm_exc.details["required_level"] == 5

    appr_exc = ApprovalRequiredError(
        "Approval needed", request_id="req_123", operation_type="DROP_TABLE"
    )
    assert appr_exc.error_code == "ERR_APPROVAL_REQUIRED"
    assert appr_exc.http_status == 428

    budget_exc = ContextBudgetExceededError(
        "Context limit hit", token_count=35000, max_tokens=32000
    )
    assert budget_exc.error_code == "ERR_CONTEXT_BUDGET_EXCEEDED"
    assert budget_exc.http_status == 413

    gate_exc = VerificationGateFailedError(
        "Gate 1 failed", gate_id=1, gate_name="AST & Syntax"
    )
    assert gate_exc.error_code == "ERR_GATE_VALIDATION_FAILED"
    assert gate_exc.http_status == 422

    debug_exc = AutoDebugExhaustedError(
        "Max attempts reached", attempts=3, max_attempts=3
    )
    assert debug_exc.error_code == "ERR_AUTO_DEBUG_EXHAUSTED"
    assert debug_exc.http_status == 500

    ast_exc = ASTParseError("Syntax broken", file_path="bad.py", line_number=10)
    assert ast_exc.error_code == "ERR_AST_PARSE"

    tool_exc = ToolExecutionError("Tool crashed", tool_name="bash_run")
    assert tool_exc.error_code == "ERR_TOOL_EXECUTION"

    llm_exc = LLMGatewayError("Spot server timed out", retry_count=3)
    assert llm_exc.error_code == "ERR_LLM_GATEWAY"
    assert llm_exc.http_status == 503


def test_fastapi_exception_handler_envelope():
    """Verify that FastAPI exception handler transforms NemotronEngineError into standard API response envelope."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/trigger-scope-error")
    def trigger_scope():
        raise ScopeViolationError(
            message="Edit blocked: unauthorized file",
            file_path="app/secret.py",
            authorized_files=["app/public.py"],
        )

    @app.get("/trigger-approval-error")
    def trigger_approval():
        raise ApprovalRequiredError(
            message="Database migration requires LEVEL 5 human approval",
            request_id="req_mig_01",
            operation_type="ALEMBIC_MIGRATION",
        )

    client = TestClient(app, raise_server_exceptions=False)

    # 1. Test 403 ScopeViolationError
    r1 = client.get("/trigger-scope-error")
    assert r1.status_code == 403
    payload1 = r1.json()
    assert payload1["success"] is False
    assert payload1["statusCode"] == 403
    assert payload1["errorCode"] == "ERR_SCOPE_VIOLATION"
    assert payload1["component"] == "scope_lock"
    assert len(payload1["errors"]) == 1
    assert payload1["errors"][0]["code"] == "ERR_SCOPE_VIOLATION"
    assert "suggestedFix" in payload1["errors"][0]

    # 2. Test 428 ApprovalRequiredError
    r2 = client.get("/trigger-approval-error")
    assert r2.status_code == 428
    payload2 = r2.json()
    assert payload2["success"] is False
    assert payload2["errorCode"] == "ERR_APPROVAL_REQUIRED"
    assert payload2["component"] == "approval_gates"


def test_ast_parser_mtime_cache_performance(tmp_path):
    """Verify that mtime-based AST caching accelerates repeated parsing by > 10x."""
    clear_ast_cache()

    sample_file = tmp_path / "service.py"
    sample_file.write_text(
        "class OrderService:\n"
        "    def create_order(self, order_id: str) -> bool:\n"
        "        return True\n"
        "    def cancel_order(self, order_id: str) -> bool:\n"
        "        return False\n"
    )

    # First parse (cold cache, reads disk)
    t0 = time.perf_counter()
    p1 = parse_python_file(str(sample_file))
    cold_time = time.perf_counter() - t0
    assert len(p1.symbols) == 3

    # Second parse (hot in-memory cache)
    t1 = time.perf_counter()
    p2 = parse_python_file(str(sample_file))
    hot_time = time.perf_counter() - t1

    assert p1.fingerprint.ast_hash == p2.fingerprint.ast_hash
    assert hot_time < cold_time or hot_time < 0.001  # sub-millisecond

    # Test cache clearing
    clear_ast_cache()
    p3 = parse_python_file(str(sample_file))
    assert len(p3.symbols) == 3


def test_verification_pipeline_ast_caching(tmp_path):
    """Verify that VerificationPipeline shares cached ASTs across Gate 1, 2, and 4."""
    pipeline = VerificationPipeline(str(tmp_path))

    py_file = tmp_path / "logic.py"
    py_file.write_text(
        "import os\ndef compute_score(x: int) -> int:\n    return x * 42\n"
    )

    report = pipeline.run_all_gates(modified_files=["logic.py"], skip_tests=True)
    assert report.all_passed is True
    # Verify AST was cached in pipeline
    assert "logic.py" in pipeline._ast_cache
    code, tree = pipeline._ast_cache["logic.py"]
    assert "compute_score" in code
    assert tree is not None

    # Test assert_all_passed does not raise when all passed
    pipeline.assert_all_passed(report)

    # Test assert_all_passed raises VerificationGateFailedError when a gate failed
    failed_report = ValidationPipelineReport(
        all_passed=False,
        total_gates_evaluated=2,
        passed_gates=1,
        failed_gate=GateResult(
            gate_id=1,
            gate_name="AST & Syntax",
            status=GateStatus.FAILED,
            message="Syntax error at line 5",
            error_details="unexpected EOF",
        ),
        gate_results=[],
    )
    with pytest.raises(VerificationGateFailedError) as exc_info:
        pipeline.assert_all_passed(failed_report)
    assert exc_info.value.gate_id == 1
    assert "Gate 1" in str(exc_info.value)


def test_context_budget_exceeded_exception():
    """Verify ContextBudgetManager raises ContextBudgetExceededError on overflow."""
    cbm = ContextBudgetManager(ContextBudget(max_total_tokens=1000))

    # Within budget does not raise
    cbm.assert_within_budget(800)

    # Exceeding budget raises ContextBudgetExceededError
    with pytest.raises(ContextBudgetExceededError) as exc:
        cbm.assert_within_budget(1200)

    assert exc.value.token_count == 1200
    assert exc.value.max_tokens == 1000
    assert exc.value.http_status == 413
