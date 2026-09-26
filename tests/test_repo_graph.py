"""
Tests for Multi-Layer Repository Knowledge Graph & Feature Mapping (Phase 2)
"""

from app.intelligence.graph.repo_graph import RepoGraph
from app.intelligence.graph.schema import EdgeKind, GraphEdge, GraphNode, NodeKind


def test_repo_graph_add_and_query():
    graph = RepoGraph()

    node1 = GraphNode(id="file:app/main.py", name="main.py", kind=NodeKind.FILE)
    node2 = GraphNode(id="sym:app.main.app", name="app", kind=NodeKind.SYMBOL)
    edge = GraphEdge(source_id=node1.id, target_id=node2.id, kind=EdgeKind.DEFINES)

    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_edge(edge)

    assert graph.total_nodes() == 2
    assert graph.total_edges() == 1
    assert graph.get_node(node1.id) is not None
    assert graph.get_node(node1.id).name == "main.py"

    out_edges = graph.get_out_edges(node1.id)
    assert len(out_edges) == 1
    assert out_edges[0].target_id == node2.id


def test_repo_graph_cycle_safe_traversal():
    graph = RepoGraph()

    # Create a cyclic dependency: A -> B -> C -> A
    nA = GraphNode(id="A", name="A", kind=NodeKind.SYMBOL)
    nB = GraphNode(id="B", name="B", kind=NodeKind.SYMBOL)
    nC = GraphNode(id="C", name="C", kind=NodeKind.SYMBOL)

    graph.add_node(nA)
    graph.add_node(nB)
    graph.add_node(nC)

    graph.add_edge(GraphEdge(source_id="A", target_id="B", kind=EdgeKind.CALLS))
    graph.add_edge(GraphEdge(source_id="B", target_id="C", kind=EdgeKind.CALLS))
    graph.add_edge(GraphEdge(source_id="C", target_id="A", kind=EdgeKind.CALLS))

    # Invariant: BFS traversal must terminate and visit each node exactly once
    traversed = graph.traverse("A", direction="out", max_depth=10)
    visited_ids = [node.id for node, depth in traversed]

    assert len(visited_ids) == 2  # B and C (A was start)
    assert "B" in visited_ids
    assert "C" in visited_ids


def test_repo_graph_extract_feature_subgraph():
    graph = RepoGraph()

    f_auth = GraphNode(id="feat:auth", name="Authentication", kind=NodeKind.FEATURE)
    f_file = GraphNode(
        id="file:auth.py", name="auth.py", kind=NodeKind.FILE, file_path="app/auth.py"
    )
    s_login = GraphNode(
        id="sym:login", name="login", kind=NodeKind.SYMBOL, file_path="app/auth.py"
    )
    t_login = GraphNode(
        id="test:login",
        name="test_login",
        kind=NodeKind.TEST,
        file_path="tests/test_auth.py",
    )

    # Dependency outside auth
    f_db = GraphNode(
        id="file:db.py", name="db.py", kind=NodeKind.FILE, file_path="app/db.py"
    )
    s_db = GraphNode(
        id="sym:session", name="session", kind=NodeKind.SYMBOL, file_path="app/db.py"
    )

    for n in (f_auth, f_file, s_login, t_login, f_db, s_db):
        graph.add_node(n)

    graph.add_edge(
        GraphEdge(
            source_id=f_file.id, target_id=f_auth.id, kind=EdgeKind.PART_OF_FEATURE
        )
    )
    graph.add_edge(
        GraphEdge(
            source_id=s_login.id, target_id=f_auth.id, kind=EdgeKind.PART_OF_FEATURE
        )
    )
    graph.add_edge(
        GraphEdge(source_id=t_login.id, target_id=f_auth.id, kind=EdgeKind.TESTS)
    )
    graph.add_edge(
        GraphEdge(source_id=s_login.id, target_id=s_db.id, kind=EdgeKind.CALLS)
    )
    graph.add_edge(
        GraphEdge(source_id=f_db.id, target_id=s_db.id, kind=EdgeKind.DEFINES)
    )

    subgraph = graph.extract_feature_subgraph("feat:auth", max_depth=2)

    assert subgraph.feature_name == "Authentication"
    assert "app/auth.py" in subgraph.primary_files
    assert "tests/test_auth.py" in subgraph.test_files
    assert "app/db.py" in subgraph.dependency_files
