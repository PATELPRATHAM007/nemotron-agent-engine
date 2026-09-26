"""
Test Suite for Cost Database Persistence
=========================================
Tests the CostRecord ORM model, CostRepository CRUD operations,
dual-write CostLedger, and DB-backed API endpoints.
"""

import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.intelligence.cost.models import CostRecord
from app.intelligence.cost.repository import CostRepository
from app.intelligence.cost.schema import (
    MissionCostReport,
    PricingMode,
    TokenUsageBreakdown,
)
from app.main import app


@pytest.fixture
def db_session(tmp_path):
    """Create an isolated SQLite session for testing."""
    db_url = f"sqlite:///{tmp_path}/test_cost.db"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def sample_report():
    """Generate a sample MissionCostReport for testing."""
    return MissionCostReport(
        mission_id="test_mission_001",
        target_feature="authentication",
        pricing_mode=PricingMode.SERVERLESS_API,
        usage=TokenUsageBreakdown(
            prompt_tokens=5000,
            completion_tokens=1500,
            thinking_tokens=800,
            total_tokens=7300,
            role_breakdown={"Planner": 5000, "Coder": 1500, "Debugger": 800},
        ),
        duration_seconds=8.5,
        total_cost_usd=0.0236,
        estimated_savings_usd=0.0045,
        effective_rate_per_1k_tokens_usd=0.003233,
        timestamp=time.time(),
    )


def test_cost_record_model_creation(db_session):
    """Test that CostRecord ORM model can be created and queried."""
    record = CostRecord(
        mission_id="m_test_model",
        target_feature="billing",
        model_engine="gemini-3.8-flash",
        pricing_mode="serverless_api",
        prompt_tokens=1000,
        completion_tokens=500,
        thinking_tokens=200,
        total_tokens=1700,
        duration_seconds=3.0,
        total_cost_usd=0.008,
        estimated_savings_usd=0.002,
        effective_rate_per_1k=0.0047,
        alert_level="NORMAL",
    )
    db_session.add(record)
    db_session.commit()

    result = db_session.query(CostRecord).filter_by(mission_id="m_test_model").first()
    assert result is not None
    assert result.mission_id == "m_test_model"
    assert result.model_engine == "gemini-3.8-flash"
    assert result.total_tokens == 1700
    assert result.total_cost_usd == 0.008
    assert result.created_at is not None


def test_repository_save_and_retrieve(db_session, sample_report):
    """Test CostRepository save_record and get_recent_records."""
    repo = CostRepository(db_session)

    # Save
    saved = repo.save_record(sample_report, model_engine="nemotron-3-ultra")
    assert saved.id is not None
    assert saved.mission_id == "test_mission_001"
    assert saved.total_tokens == 7300

    # Retrieve
    records = repo.get_recent_records(limit=5)
    assert len(records) == 1
    assert records[0]["mission_id"] == "test_mission_001"
    assert records[0]["model_engine"] == "nemotron-3-ultra"
    assert records[0]["total_cost_usd"] == 0.0236


def test_repository_summary_aggregation(db_session):
    """Test CostRepository get_summary SQL aggregations."""
    repo = CostRepository(db_session)

    # Insert multiple records
    for i in range(3):
        report = MissionCostReport(
            mission_id=f"m_agg_{i}",
            target_feature="testing",
            pricing_mode=PricingMode.GCP_SPOT,
            usage=TokenUsageBreakdown(
                prompt_tokens=1000 * (i + 1),
                completion_tokens=500 * (i + 1),
                total_tokens=1500 * (i + 1),
            ),
            total_cost_usd=0.01 * (i + 1),
            estimated_savings_usd=0.002 * (i + 1),
        )
        repo.save_record(report, model_engine="nemotron-3-ultra")

    summary = repo.get_summary()
    assert summary.total_missions == 3
    assert summary.total_tokens == 1500 + 3000 + 4500  # 9000
    assert abs(summary.total_spend_usd - 0.06) < 1e-4  # 0.01 + 0.02 + 0.03
    assert abs(summary.total_saved_usd - 0.012) < 1e-4  # 0.002 + 0.004 + 0.006


def test_repository_daily_spend(db_session, sample_report):
    """Test CostRepository get_daily_spend for today's date."""
    repo = CostRepository(db_session)
    repo.save_record(sample_report)

    daily = repo.get_daily_spend()
    assert daily == 0.0236


def test_repository_mission_lookup(db_session, sample_report):
    """Test CostRepository get_records_by_mission."""
    repo = CostRepository(db_session)
    repo.save_record(sample_report)

    records = repo.get_records_by_mission("test_mission_001")
    assert len(records) == 1
    assert records[0]["target_feature"] == "authentication"

    empty = repo.get_records_by_mission("nonexistent")
    assert len(empty) == 0


def test_dual_write_ledger_persists_to_json_and_db(tmp_path):
    """Test CostLedger dual-write stores to both JSON file and (attempts) DB."""
    from app.intelligence.cost.ledger import CostLedger

    ledger = CostLedger(workspace_root=str(tmp_path))
    report = MissionCostReport(
        mission_id="dual_write_test",
        target_feature="payments",
        usage=TokenUsageBreakdown(
            prompt_tokens=2000, completion_tokens=800, total_tokens=2800
        ),
        total_cost_usd=0.015,
        estimated_savings_usd=0.003,
    )

    ledger.record_mission(report, model_engine="gemini-3.8-flash")

    # Verify JSON persistence
    assert len(ledger._records) == 1
    reloaded = CostLedger(workspace_root=str(tmp_path))
    assert len(reloaded._records) == 1
    assert reloaded._records[0].mission_id == "dual_write_test"


def test_cost_api_endpoints_with_db():
    """Test the /cost/summary, /cost/ledger, and /cost/mission endpoints."""
    client = TestClient(app)

    # 1. Cost summary
    resp = client.get("/api/v1/agent/cost/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "total_missions" in data["data"]
    assert "total_spend_usd" in data["data"]

    # 2. Cost ledger
    resp2 = client.get("/api/v1/agent/cost/ledger?limit=5")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["success"] is True
    assert isinstance(data2["data"], list)

    # 3. Mission-specific cost
    resp3 = client.get("/api/v1/agent/cost/mission/nonexistent-id")
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["success"] is True
