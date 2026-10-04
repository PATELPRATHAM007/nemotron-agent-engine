"""
Phase 5 Test Suite: Advanced Verification, Database & Visual UI
================================================================
Tests:
  1. Browser Visual UI Verification (open, screenshot, click, type, dispatch_tool).
  2. Database EXPLAIN Plan Intelligence (sequential scan detection & index recommendations).
  3. Safe Migration Proposal Engine (reversible Alembic generation & mutation approval gate).
  4. Structured Artifact Delivery System (plan, diff, test report, screenshot artifacts).
"""

import os

import pytest

from app.modules.agent.tools.browser_tool import BrowserTool
from app.modules.agent.tools.registry import dispatch_tool
from app.modules.intelligence.database.explain_engine import ExplainPlanEngine
from app.modules.intelligence.database.migration_generator import (
    SafeMigrationGenerator,
)
from app.modules.missions.artifacts import (
    ArtifactManager,
    ArtifactType,
)

# ==============================================================================
# 1. Browser Visual UI Verification Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_browser_tool_navigation_and_screenshot(tmp_path):
    tool = BrowserTool(workspace_root=str(tmp_path))

    open_res = await tool.open("http://localhost:3000/dashboard")
    assert open_res["success"] is True
    assert open_res["url"] == "http://localhost:3000/dashboard"

    shot_res = await tool.screenshot("test_screen.png")
    assert shot_res["success"] is True
    assert shot_res["width"] == 1280
    assert shot_res["height"] == 720
    assert os.path.exists(shot_res["file_path"])
    assert len(shot_res["base64"]) > 0

    click_res = await tool.click("button#submit-form")
    assert click_res["success"] is True

    type_res = await tool.type("input#search", "billing invoices")
    assert type_res["success"] is True

    close_res = await tool.close()
    assert close_res["success"] is True


@pytest.mark.asyncio
async def test_browser_tool_dispatch():
    open_res = await dispatch_tool("browser_open", {"url": "http://localhost:5173"})
    assert open_res["success"] is True

    shot_res = await dispatch_tool("browser_screenshot", {"filename": "verify.png"})
    assert shot_res["success"] is True
    assert shot_res["format"] == "png"

    click_res = await dispatch_tool("browser_click", {"selector": "a.nav-link"})
    assert click_res["success"] is True


# ==============================================================================
# 2. Database EXPLAIN Plan Intelligence Tests
# ==============================================================================

def test_explain_plan_engine_detects_sequential_scans():
    engine = ExplainPlanEngine()

    mock_pg_plan = [
        {
            "Plan": {
                "Node Type": "Seq Scan",
                "Relation Name": "customer_invoices",
                "Startup Cost": 0.0,
                "Total Cost": 8420.50,
                "Plan Rows": 55000,
                "Filter": "(status = 'UNPAID'::text)",
            }
        }
    ]

    root = engine.parse_postgres_json_plan(mock_pg_plan)
    assert root.node_type == "Seq Scan"
    assert root.relation_name == "customer_invoices"
    assert root.plan_rows == 55000

    analysis = engine.analyze_plan_bottlenecks(root, large_table_threshold=1000)
    assert analysis["has_bottlenecks"] is True
    assert len(analysis["seq_scans"]) == 1
    assert analysis["seq_scans"][0]["table"] == "customer_invoices"
    assert any("Consider adding an index" in r for r in analysis["recommendations"])


# ==============================================================================
# 3. Safe Migration Proposal Engine Tests
# ==============================================================================

def test_safe_migration_proposal_generation():
    generator = SafeMigrationGenerator()

    ops = [
        {
            "op_type": "add_column",
            "column_name": "loyalty_points",
            "column_type": "sa.Integer()",
            "nullable": False,
        },
        {
            "op_type": "create_index",
            "column_name": "loyalty_points",
            "index_name": "ix_users_loyalty_points",
            "columns": ["loyalty_points"],
        },
    ]

    proposal = generator.propose_migration(
        revision_id="rev_001_loyalty",
        message="Add loyalty points and index to users",
        table_name="users",
        operations=ops,
    )

    assert proposal.revision_id == "rev_001_loyalty"
    assert proposal.is_reversible is True
    assert proposal.requires_human_approval is True
    assert proposal.approval_token_required == "MUTATION_APPROVAL_REQUIRED"

    script = proposal.migration_script
    assert "def upgrade() -> None:" in script
    assert "op.add_column('users', sa.Column('loyalty_points', sa.Integer(), nullable=False))" in script
    assert "op.create_index('ix_users_loyalty_points', 'users', ['loyalty_points']" in script
    assert "def downgrade() -> None:" in script
    assert "op.drop_column('users', 'loyalty_points')" in script
    assert "op.drop_index('ix_users_loyalty_points', table_name='users')" in script


def test_safe_migration_proposal_destructive_warning():
    generator = SafeMigrationGenerator()

    ops = [
        {
            "op_type": "drop_column",
            "column_name": "legacy_token",
        }
    ]

    proposal = generator.propose_migration(
        revision_id="rev_002_drop_token",
        message="Remove legacy auth token",
        table_name="accounts",
        operations=ops,
    )

    assert len(proposal.destructive_operations) == 1
    assert "irreversible data loss" in proposal.destructive_operations[0]


# ==============================================================================
# 4. Structured Artifact Delivery System Tests
# ==============================================================================

def test_structured_artifact_manager():
    manager = ArtifactManager()
    m_id = "mission-artifact-test-1"

    # 1. Plan Artifact
    plan_art = manager.save_plan_artifact(
        mission_id=m_id,
        title="Architecture Upgrade Plan",
        steps=[{"step_id": 1, "title": "Database Schema Update"}],
        summary="Upgrades database schema for subscriptions",
    )
    assert plan_art["artifact_type"] == ArtifactType.PLAN.value

    # 2. Diff Artifact
    diff_text = """--- a/service.py
+++ b/service.py
@@ -1,3 +1,4 @@
+import stripe
 def bill(): pass
"""
    diff_art = manager.save_diff_artifact(
        mission_id=m_id,
        title="Stripe billing diff",
        diff_text=diff_text,
        files_modified=["service.py"],
    )
    assert diff_art["artifact_type"] == ArtifactType.DIFF.value
    assert diff_art["data"]["additions_count"] >= 1

    # 3. Test Report Artifact
    test_art = manager.save_test_report_artifact(
        mission_id=m_id,
        title="Integration Suite Report",
        tests_passed=48,
        tests_failed=0,
        duration_seconds=3.42,
        log_output="48 passed in 3.42s",
    )
    assert test_art["artifact_type"] == ArtifactType.TEST_REPORT.value
    assert test_art["data"]["success_rate_percent"] == 100.0

    # 4. Screenshot Artifact
    shot_art = manager.save_visual_screenshot_artifact(
        mission_id=m_id,
        title="Checkout Page Verification",
        image_url_or_path="/screenshots/checkout.png",
        caption="Verified responsive checkout UI",
    )
    assert shot_art["artifact_type"] == ArtifactType.VISUAL_SCREENSHOT.value

    # 5. List all mission artifacts
    all_artifacts = manager.get_mission_artifacts(m_id)
    assert len(all_artifacts) >= 4
    types = [a["artifact_type"] for a in all_artifacts]
    assert ArtifactType.PLAN.value in types
    assert ArtifactType.DIFF.value in types
    assert ArtifactType.TEST_REPORT.value in types
    assert ArtifactType.VISUAL_SCREENSHOT.value in types
