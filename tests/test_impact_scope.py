"""
Tests for Change Impact Analysis and Task Scope Lock (Phase 3)
"""

import pytest

from app.intelligence.graph.repo_graph import RepoGraph
from app.intelligence.graph.schema import EdgeKind, GraphEdge, GraphNode, NodeKind
from app.intelligence.impact.impact_analyzer import ImpactAnalyzer
from app.intelligence.impact.scope_lock import ScopeViolationError, TaskScope


def test_impact_analyzer_calculates_blast_radius():
    graph = RepoGraph()

    # Target symbol: AuthService.login
    s_target = GraphNode(
        id="sym:AuthService.login",
        name="login",
        kind=NodeKind.SYMBOL,
        file_path="app/auth.py",
    )
    # Caller 1: Route endpoint
    s_route = GraphNode(
        id="sym:login_endpoint",
        name="login_endpoint",
        kind=NodeKind.SYMBOL,
        file_path="app/routes.py",
        metadata={"route": {"http_method": "POST", "path": "/login"}},
    )
    # Caller 2: Internal helper calling route
    s_client = GraphNode(
        id="sym:test_client",
        name="test_client",
        kind=NodeKind.TEST,
        file_path="tests/test_auth.py",
    )

    graph.add_node(s_target)
    graph.add_node(s_route)
    graph.add_node(s_client)

    # s_route CALLS s_target
    graph.add_edge(
        GraphEdge(source_id=s_route.id, target_id=s_target.id, kind=EdgeKind.CALLS)
    )
    # s_client CALLS s_route
    graph.add_edge(
        GraphEdge(source_id=s_client.id, target_id=s_route.id, kind=EdgeKind.CALLS)
    )
    # s_client TESTS s_target
    graph.add_edge(
        GraphEdge(source_id=s_client.id, target_id=s_target.id, kind=EdgeKind.TESTS)
    )

    analyzer = ImpactAnalyzer(graph)
    report = analyzer.analyze("sym:AuthService.login", max_depth=3)

    assert report.target_id == "sym:AuthService.login"
    assert report.direct_dependencies_count == 1  # s_route directly calls s_target
    assert (
        report.indirect_dependencies_count == 1
    )  # s_client indirectly calls s_target via s_route
    assert len(report.affected_routes) == 1
    assert report.affected_routes[0]["route"]["path"] == "/login"
    assert "tests/test_auth.py" in report.affected_files
    assert report.risk_level in ("HIGH", "CRITICAL")


def test_scope_lock_permits_authorized_files():
    scope = TaskScope(
        task_id="task-123",
        primary_feature="Authentication",
        allowed_edit_files={"app/auth/service.py", "app/auth/router.py"},
        target_test_files={"tests/test_auth.py"},
    )

    assert scope.validate_edit("app/auth/service.py") is True
    assert scope.validate_edit("tests/test_auth.py") is True


def test_scope_lock_blocks_unauthorized_files():
    scope = TaskScope(
        task_id="task-123",
        primary_feature="Authentication",
        allowed_edit_files={"app/auth/service.py"},
        target_test_files={"tests/test_auth.py"},
    )

    # Attempting to edit an unauthorized file must raise ScopeViolationError
    with pytest.raises(ScopeViolationError) as exc_info:
        scope.validate_edit("app/billing/payments.py")

    assert "Scope Lock Violation" in str(exc_info.value)
    assert "app/billing/payments.py" in str(exc_info.value)


def test_scope_lock_bounded_expansion():
    scope = TaskScope(
        task_id="task-123",
        primary_feature="Authentication",
        allowed_edit_files={"app/auth/service.py"},
        max_expansions=1,
    )

    # First expansion request should succeed
    success = scope.request_expansion(
        "app/auth/config.py",
        reason="Timeout config is stored here",
        evidence="import in service.py",
    )
    assert success is True
    assert "app/auth/config.py" in scope.allowed_edit_files

    # Second expansion request must be rejected (capped at max_expansions = 1)
    second_success = scope.request_expansion(
        "app/billing/payments.py", reason="Another expansion", evidence=""
    )
    assert second_success is False
