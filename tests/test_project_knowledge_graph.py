"""
Unit & Integration Tests for Deep Project Intelligence Knowledge Graph
=======================================================================
Verifies:
  1. Complete Graph Construction (Nodes & Edges)
  2. Taxonomy coverage (WHAT vs HOW layers)
  3. Evidence Grounding & Confidence rating
  4. Feature Subgraph extraction
  5. Business Rule indexing and invariants
  6. Change Impact Analysis & Blast Radius calculation
  7. Natural language query resolution
  8. Architectural issue tracking
"""

import pytest

from app.modules.intelligence.graph.knowledge_graph import (
    ProjectKnowledgeGraph,
    build_complete_project_knowledge_graph,
)
from app.modules.intelligence.graph.schema import (
    ConfidenceLevel,
    EdgeKind,
    NodeKind,
)


def test_build_complete_knowledge_graph():
    kg = build_complete_project_knowledge_graph()
    assert kg is not None
    assert len(kg.nodes) >= 80
    assert len(kg.edges) >= 80

    health = kg.validate_health()
    assert health.total_nodes == len(kg.nodes)
    assert health.evidence_coverage_pct >= 95.0
    assert len(health.orphan_nodes) == 0


def test_taxonomy_layers_distinguish_what_from_how():
    kg = build_complete_project_knowledge_graph()

    # WHAT layers
    features = [n for n in kg.nodes.values() if n.kind == NodeKind.FEATURE]
    capabilities = [n for n in kg.nodes.values() if n.kind == NodeKind.BUSINESS_CAPABILITY]
    rules = [n for n in kg.nodes.values() if n.kind == NodeKind.BUSINESS_RULE]
    flows = [n for n in kg.nodes.values() if n.kind == NodeKind.USER_FLOW]

    assert len(features) >= 8
    assert len(capabilities) >= 5
    assert len(rules) >= 8
    assert len(flows) >= 4

    # HOW layers
    apis = [n for n in kg.nodes.values() if n.kind == NodeKind.API_ENDPOINT]
    components = [n for n in kg.nodes.values() if n.kind == NodeKind.COMPONENT]
    entities = [n for n in kg.nodes.values() if n.kind == NodeKind.DATABASE_ENTITY]
    tests = [n for n in kg.nodes.values() if n.kind == NodeKind.TEST]

    assert len(apis) >= 15
    assert len(components) >= 5
    assert len(entities) >= 10
    assert len(tests) >= 8


def test_feature_subgraph_extraction():
    kg = build_complete_project_knowledge_graph()

    # Query autonomous missions feature
    subgraph = kg.get_feature_subgraph("feat.autonomous_missions")
    assert "error" not in subgraph
    assert subgraph["feature"]["id"] == "feat.autonomous_missions"
    assert len(subgraph["apis"]) > 0
    assert len(subgraph["business_rules"]) > 0
    assert len(subgraph["database_entities"]) > 0


def test_business_rules_have_evidence():
    kg = build_complete_project_knowledge_graph()
    rules = [n for n in kg.nodes.values() if n.kind == NodeKind.BUSINESS_RULE]

    for rule in rules:
        assert rule.id.startswith("rule:BR-")
        assert rule.evidence is not None and len(rule.evidence) > 0
        assert rule.confidence == ConfidenceLevel.HIGH
        assert "tested_by_evidence" in rule.metadata


def test_change_impact_analysis_for_api():
    kg = build_complete_project_knowledge_graph()

    # Check blast radius for missions API
    impact = kg.calculate_impact_scope("api:POST_/api/v1/missions")
    assert "error" not in impact
    assert impact["target"]["id"] == "api:POST_/api/v1/missions"
    summary = impact["impact_summary"]
    assert summary["impacted_features_count"] >= 1


def test_natural_language_query():
    kg = build_complete_project_knowledge_graph()

    # Search for quota or budget
    results = kg.query("budget")
    assert len(results) > 0
    top = results[0]["node"]
    assert "budget" in top["name"].lower() or "budget" in (top.get("docstring") or "").lower() or "budget" in top["id"].lower()


def test_architectural_issues_detection():
    kg = build_complete_project_knowledge_graph()
    health = kg.validate_health()

    assert len(health.architectural_issues) >= 3
    issue_ids = [issue["id"] for issue in health.architectural_issues]
    assert "issue:ISSUE-01" in issue_ids
    assert "issue:ISSUE-02" in issue_ids
