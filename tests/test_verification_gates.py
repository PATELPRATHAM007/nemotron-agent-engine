from app.intelligence.impact.scope_lock import TaskScope
from app.modules.agent.verification.auto_debugger import BoundedAutoDebugger
from app.modules.agent.verification.gates import VerificationPipeline
from app.modules.agent.verification.schema import GateStatus


def test_verification_pipeline_clean_files(tmp_path):
    # Setup valid python file
    f = tmp_path / "valid_module.py"
    f.write_text("def add(a: int, b: int) -> int:\n    return a + b\n")

    pipeline = VerificationPipeline(str(tmp_path))
    scope = TaskScope(
        task_id="t1", primary_feature="math", allowed_edit_files={"valid_module.py"}
    )

    report = pipeline.run_all_gates(
        modified_files=["valid_module.py"],
        scope=scope,
        skip_tests=True,
    )

    assert report.all_passed is True
    assert report.failed_gate is None
    assert report.total_gates_evaluated == 8


def test_gate_1_fails_on_syntax_error(tmp_path):
    # Setup syntax broken file
    f = tmp_path / "broken.py"
    f.write_text("def broken_syntax(:\n    pass\n")

    pipeline = VerificationPipeline(str(tmp_path))
    report = pipeline.run_all_gates(
        modified_files=["broken.py"],
        skip_tests=True,
    )

    assert report.all_passed is False
    assert report.failed_gate is not None
    assert report.failed_gate.gate_id == 1
    assert "SyntaxError" in report.failed_gate.message
    # Early exit: subsequent gates were not evaluated
    assert report.total_gates_evaluated == 1


def test_gate_5_fails_on_scope_violation(tmp_path):
    f = tmp_path / "unauthorized.py"
    f.write_text("x = 10\n")

    pipeline = VerificationPipeline(str(tmp_path))
    scope = TaskScope(
        task_id="t2", primary_feature="auth", allowed_edit_files={"auth.py"}
    )

    report = pipeline.run_all_gates(
        modified_files=["unauthorized.py"],
        scope=scope,
        skip_tests=True,
    )

    assert report.all_passed is False
    assert report.failed_gate is not None
    assert report.failed_gate.gate_id == 5
    assert "Scope violation" in report.failed_gate.message


def test_auto_debugger_bounded_attempts_and_rollback(tmp_path):
    debugger = BoundedAutoDebugger(str(tmp_path), max_attempts=3)
    session = debugger.create_session("test_task")

    assert session.can_retry() is True

    # Setup dummy failed gate
    from app.modules.agent.verification.schema import GateResult

    dummy_failed = GateResult(
        gate_id=1,
        gate_name="AST & Syntax",
        status=GateStatus.FAILED,
        message="Syntax error",
    )

    # Attempt 1
    session.record_attempt(dummy_failed, "fix 1")
    assert session.can_retry() is True

    # Attempt 2
    session.record_attempt(dummy_failed, "fix 2")
    assert session.can_retry() is True

    # Attempt 3
    session.record_attempt(dummy_failed, "fix 3")
    assert session.can_retry() is False  # Reached max attempts!

    # Trigger rollback
    rolled_back = session.trigger_rollback()
    assert session.is_rolled_back is True
    assert rolled_back is True
