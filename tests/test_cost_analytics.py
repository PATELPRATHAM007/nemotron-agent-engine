import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import CostBudgetExceededError
from app.intelligence.cost import (
    BudgetGuard,
    CostAlertLevel,
    CostBudgetConfig,
    CostCalculator,
    CostLedger,
    CostTracker,
    MissionCostReport,
    PricingMode,
    PricingModel,
    TokenUsageBreakdown,
)
from app.main import app


def test_cost_calculator_formulas():
    pricing = PricingModel(
        gcp_hourly_rate_usd=12.80,
        input_cost_per_million=2.00,
        output_cost_per_million=6.00,
        reasoning_cost_per_million=4.00,
        tier1_cost_per_million=0.075,
    )
    calc = CostCalculator(pricing)

    usage = TokenUsageBreakdown(
        prompt_tokens=10_000,
        completion_tokens=2_000,
        thinking_tokens=3_000,
        total_tokens=15_000,
    )

    # 1. Serverless API calculation
    # (10k / 1M * 2.0) = 0.02
    # (2k / 1M * 6.0)  = 0.012
    # (3k / 1M * 4.0)  = 0.012
    # Total = 0.044
    api_cost = calc.calculate_cost(usage, mode=PricingMode.SERVERLESS_API)
    assert abs(api_cost - 0.044) < 1e-5

    # 2. GCP Spot calculation for 36 seconds
    # (36 / 3600) * 12.80 = 0.128
    spot_cost = calc.calculate_cost(
        usage, duration_seconds=36.0, mode=PricingMode.GCP_SPOT
    )
    assert abs(spot_cost - 0.128) < 1e-5

    # 3. Tier-1 Gemini savings for 50,000 offloaded tokens
    # Nemotron: 50k / 1M * 2.00 = $0.10
    # Gemini:   50k / 1M * 0.075 = $0.00375
    # Savings:  $0.09625
    savings = calc.calculate_tier1_savings(offloaded_prompt_tokens=50_000)
    assert abs(savings - 0.09625) < 1e-4

    # 4. Report Generation
    report = calc.build_report(
        mission_id="m_test_01",
        target_feature="billing",
        usage=usage,
        duration_seconds=10.0,
        offloaded_tokens=20_000,
        mode=PricingMode.SERVERLESS_API,
    )
    assert report.mission_id == "m_test_01"
    assert report.total_cost_usd > 0.0
    assert report.estimated_savings_usd > 0.0


def test_cost_tracker_token_accounting():
    tracker = CostTracker()

    # Prompt tokens
    p_tokens = tracker.record_prompt(
        "Implement user login flow with JWT validation", role="Planner"
    )
    assert p_tokens > 0
    assert tracker.prompt_tokens == p_tokens

    # Streaming chunks
    tracker.record_chunk(
        "thought", "Analyzing database schema for users table...", role="Debugger"
    )
    tracker.record_chunk("token", "def authenticate_user(): return True", role="Coder")

    breakdown = tracker.get_breakdown()
    assert breakdown.prompt_tokens == p_tokens
    assert breakdown.thinking_tokens > 0
    assert breakdown.completion_tokens > 0
    assert (
        breakdown.total_tokens
        == breakdown.prompt_tokens
        + breakdown.completion_tokens
        + breakdown.thinking_tokens
    )
    assert "Planner" in breakdown.role_breakdown
    assert "Debugger" in breakdown.role_breakdown
    assert "Coder" in breakdown.role_breakdown

    # Report generation
    report = tracker.generate_report(
        mission_id="mission_tracker_01", target_feature="auth"
    )
    assert report.mission_id == "mission_tracker_01"
    assert report.duration_seconds >= 0.0


def test_budget_guard_circuit_breaker():
    config = CostBudgetConfig(
        max_mission_budget_usd=0.05,
        max_daily_budget_usd=0.10,
        warn_threshold_pct=0.80,
        stop_on_budget_exceeded=True,
    )
    guard = BudgetGuard(config)
    tracker = CostTracker(PricingModel(mode=PricingMode.SERVERLESS_API))

    # Low usage -> NORMAL
    tracker.record_exact_usage(
        prompt_tokens=1000, completion_tokens=500, thinking_tokens=200
    )
    status_normal = guard.check_mission_budget(tracker, mode=PricingMode.SERVERLESS_API)
    assert status_normal == CostAlertLevel.NORMAL

    # High usage triggering mission limit -> CostBudgetExceededError
    # 25,000 completion tokens * $6.00 / 1M = $0.15 (exceeds $0.05 limit)
    tracker.record_exact_usage(
        prompt_tokens=10_000, completion_tokens=25_000, thinking_tokens=5_000
    )
    with pytest.raises(CostBudgetExceededError) as exc_info:
        guard.check_mission_budget(tracker, mode=PricingMode.SERVERLESS_API)
    assert exc_info.value.http_status == 402
    assert exc_info.value.current_cost_usd > 0.05

    # Daily limit exceeded check
    tracker_small = CostTracker(PricingModel(mode=PricingMode.SERVERLESS_API))
    tracker_small.record_exact_usage(prompt_tokens=100, completion_tokens=100)
    with pytest.raises(CostBudgetExceededError):
        guard.check_mission_budget(
            tracker_small, mode=PricingMode.SERVERLESS_API, daily_accumulated_spend=0.15
        )


def test_cost_ledger_persistence(tmp_path):
    ledger = CostLedger(workspace_root=str(tmp_path))
    assert len(ledger._records) == 0

    report1 = MissionCostReport(
        mission_id="m1",
        target_feature="auth",
        pricing_mode=PricingMode.SERVERLESS_API,
        usage=TokenUsageBreakdown(
            prompt_tokens=5000, completion_tokens=1000, total_tokens=6000
        ),
        duration_seconds=5.0,
        total_cost_usd=0.016,
        estimated_savings_usd=0.005,
    )
    report2 = MissionCostReport(
        mission_id="m2",
        target_feature="payments",
        pricing_mode=PricingMode.SERVERLESS_API,
        usage=TokenUsageBreakdown(
            prompt_tokens=8000, completion_tokens=2000, total_tokens=10000
        ),
        duration_seconds=12.0,
        total_cost_usd=0.028,
        estimated_savings_usd=0.010,
    )

    ledger.record_mission(report1)
    ledger.record_mission(report2)

    # Verify reload from disk (JSON file persistence)
    reloaded_ledger = CostLedger(workspace_root=str(tmp_path))
    assert len(reloaded_ledger._records) == 2

    # Verify JSON records directly (avoid DB cross-contamination in shared test runs)
    total_tokens = sum(r.usage.total_tokens for r in reloaded_ledger._records)
    total_spend = sum(r.total_cost_usd for r in reloaded_ledger._records)
    total_saved = sum(r.estimated_savings_usd for r in reloaded_ledger._records)
    assert total_tokens == 16000
    assert abs(total_spend - 0.044) < 1e-4
    assert abs(total_saved - 0.015) < 1e-4

    recent = reloaded_ledger.get_recent_missions(limit=1)
    assert len(recent) == 1


def test_cost_api_endpoints():
    client = TestClient(app)

    # 1. Test /api/v1/agent/cost/summary
    resp1 = client.get("/api/v1/agent/cost/summary")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["success"] is True
    assert "total_missions" in data1["data"]
    assert "total_spend_usd" in data1["data"]
    assert "daily_spend_usd" in data1["data"]

    # 2. Test /api/v1/agent/cost/ledger
    resp2 = client.get("/api/v1/agent/cost/ledger?limit=5")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["success"] is True
    assert isinstance(data2["data"], list)
