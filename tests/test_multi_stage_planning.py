from app.modules.agent.planning.multi_stage import MultiStagePlanner
from app.modules.agent.planning.review_loops import ReviewLoopEngine
from app.modules.agent.planning.schema import PlanningStage, ReviewKind


def test_multi_stage_planner_phases_a_through_h():
    planner = MultiStagePlanner(workspace_root=".")
    contract = planner.generate_plan(
        task_id="plan_test_01",
        goal="Add customer loyalty points calculation endpoint",
        target_feature="billing",
        initial_files=["app/modules/billing/service.py"],
        test_files=["tests/test_billing.py"],
        db_tables=["customers", "loyalty_points"],
        is_db_mutation=False,
    )

    # 1. Assert all 8 phases are populated
    assert PlanningStage.PHASE_A_DISCOVERY.value in contract.stage_outputs
    assert PlanningStage.PHASE_B_RETRIEVAL.value in contract.stage_outputs
    assert PlanningStage.PHASE_C_ARCHITECTURE.value in contract.stage_outputs
    assert PlanningStage.PHASE_D_IMPACT_ANALYSIS.value in contract.stage_outputs
    assert PlanningStage.PHASE_E_DATABASE_ANALYSIS.value in contract.stage_outputs
    assert PlanningStage.PHASE_F_IMPLEMENTATION_PLAN.value in contract.stage_outputs
    assert PlanningStage.PHASE_G_TEST_PLAN.value in contract.stage_outputs
    assert PlanningStage.PHASE_H_RISK_PLAN.value in contract.stage_outputs

    # 2. Assert all 6 reviews were executed and passed
    assert len(contract.review_results) == 6
    assert contract.all_reviews_passed is True
    assert contract.readiness_score == 1.0
    assert contract.permission_level_required == 2


def test_review_loop_engine_critiques():
    engine = ReviewLoopEngine()

    # 1. Performance failure on > 32k tokens
    results_perf = engine.execute_all_reviews(
        goal="Heavy task",
        target_files=["file1.py"],
        test_files=["test1.py"],
        db_tables=[],
        context_tokens=35000,
    )
    perf_rev = next(
        r for r in results_perf if r.review_kind == ReviewKind.REVIEW_4_PERFORMANCE
    )
    assert perf_rev.passed is False
    assert "exceeds the <= 32k token ceiling" in perf_rev.critique

    # 2. Correctness failure on missing tests
    results_corr = engine.execute_all_reviews(
        goal="Missing tests task",
        target_files=["file1.py"],
        test_files=[],  # Empty test files!
        db_tables=[],
    )
    corr_rev = next(
        r for r in results_corr if r.review_kind == ReviewKind.REVIEW_2_CORRECTNESS
    )
    assert corr_rev.passed is False
    assert "lacks dedicated test" in corr_rev.critique

    # 3. Security notice on DB mutation
    results_sec = engine.execute_all_reviews(
        goal="Database migration task",
        target_files=["alembic/versions/v1.py"],
        test_files=["tests/test_migration.py"],
        db_tables=["users"],
        is_db_mutation=True,
    )
    sec_rev = next(
        r for r in results_sec if r.review_kind == ReviewKind.REVIEW_3_SECURITY
    )
    assert "requires LEVEL 5 permission" in sec_rev.critique
