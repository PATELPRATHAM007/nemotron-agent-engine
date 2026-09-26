from app.intelligence.context.budget_manager import (
    ContextBudget,
    ContextBudgetManager,
    estimate_tokens,
    truncate_to_tokens,
)
from app.intelligence.context.hierarchical import HierarchicalContextBuilder
from app.intelligence.context.ranker import ContextRanker
from app.intelligence.graph.repo_graph import RepoGraph
from app.intelligence.graph.schema import FeatureSubgraph, GraphNode, NodeKind


def test_token_estimation_and_truncation():
    empty_tokens = estimate_tokens("")
    assert empty_tokens == 0

    text = "hello world this is a test string"
    tokens = estimate_tokens(text)
    assert tokens > 0

    # Truncation test
    long_text = "word " * 1000
    truncated = truncate_to_tokens(long_text, max_tokens=50)
    assert estimate_tokens(truncated) <= 60
    assert "[truncated to fit context budget]" in truncated


def test_context_budget_assembly():
    budget = ContextBudget(max_total_tokens=1000)
    manager = ContextBudgetManager(budget)

    payload = manager.assemble_payload(
        system_instructions="You are Nemotron Coder.",
        task_prompt="Implement JWT expiration check.",
        architecture_context="Standard clean architecture.",
        feature_subgraph_str="Feature: Auth",
        target_code="def verify_jwt(): pass",
        test_context="def test_jwt(): pass",
        lessons_context="Always check expiry timestamps.",
    )

    assert payload["within_budget"] is True
    assert payload["total_tokens"] <= 1000
    assert "token_usage" in payload
    assert payload["token_usage"]["system_role"] > 0


def test_hierarchical_context_builder(tmp_path):
    # Setup test file
    target_file = tmp_path / "auth_service.py"
    target_file.write_text("class AuthService:\n    def login(self): pass\n")

    graph = RepoGraph()
    builder = HierarchicalContextBuilder(str(tmp_path), graph)

    subgraph = FeatureSubgraph(
        feature_id="feature:auth",
        feature_name="Authentication",
        primary_files=["auth_service.py"],
        dependency_files=["utils.py"],
        test_files=["test_auth.py"],
        nodes=[
            GraphNode(
                id="symbol:utils.hash_pwd",
                name="hash_pwd",
                kind=NodeKind.SYMBOL,
                file_path="utils.py",
                docstring="Hashes raw password.",
                metadata={"signature": "hash_pwd(pwd: str) -> str"},
            ),
            GraphNode(
                id="symbol:auth.login_endpoint",
                name="login_endpoint",
                kind=NodeKind.SYMBOL,
                file_path="auth_service.py",
                metadata={"route": {"http_method": "POST", "path": "/api/v1/login"}},
            ),
        ],
    )

    overview = builder.build_feature_overview(subgraph)
    assert "Authentication" in overview
    assert "auth_service.py" in overview
    assert "POST" in overview
    assert "/api/v1/login" in overview

    dep_sigs = builder.build_dependency_signatures(subgraph)
    assert "hash_pwd(pwd: str) -> str" in dep_sigs
    assert "Hashes raw password." in dep_sigs

    code = builder.build_target_source_code(subgraph)
    assert "class AuthService:" in code


def test_context_ranker():
    graph = RepoGraph()
    target_node = GraphNode(
        id="symbol:auth.login",
        name="login",
        kind=NodeKind.SYMBOL,
        file_path="auth.py",
        docstring="Authenticates user session",
    )
    unrelated_node = GraphNode(
        id="symbol:billing.charge",
        name="charge_card",
        kind=NodeKind.SYMBOL,
        file_path="billing.py",
        docstring="Processes payment",
    )

    graph.add_node(target_node)
    graph.add_node(unrelated_node)

    ranker = ContextRanker(graph)
    ranked = ranker.rank_nodes(
        query="user login authentication",
        target_feature_id="feature:auth",
        candidate_nodes=[unrelated_node, target_node],
    )

    assert len(ranked) == 2
    # target_node should rank higher due to symbol match and lexical match
    top_node, top_score = ranked[0]
    _second_node, second_score = ranked[1]
    assert top_node.name == "login"
    assert top_score > second_score
