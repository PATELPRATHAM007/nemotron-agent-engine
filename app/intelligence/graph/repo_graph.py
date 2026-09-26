"""
Multi-Layer Repository Knowledge Graph Engine
==============================================
In-memory directed graph with cycle-safe BFS/DFS traversals, fast adjacency lookups,
and bounded feature subgraph extraction.
"""

from collections import deque

from app.intelligence.graph.schema import (
    EdgeKind,
    FeatureSubgraph,
    GraphEdge,
    GraphNode,
    NodeKind,
)


class RepoGraph:
    """Directed Multi-Layer Graph for Repository Intelligence."""

    def __init__(self):
        self.nodes: dict[str, GraphNode] = {}
        self._out_edges: dict[str, list[GraphEdge]] = {}  # source_id -> list of edges
        self._in_edges: dict[str, list[GraphEdge]] = {}  # target_id -> list of edges

    def add_node(self, node: GraphNode):
        """Add or update a node in the graph."""
        self.nodes[node.id] = node
        self._out_edges.setdefault(node.id, [])
        self._in_edges.setdefault(node.id, [])

    def add_edge(self, edge: GraphEdge):
        """Add a directed edge connecting two existing nodes."""
        self._out_edges.setdefault(edge.source_id, []).append(edge)
        self._in_edges.setdefault(edge.target_id, []).append(edge)

    def get_node(self, node_id: str) -> GraphNode | None:
        """Lookup node by ID."""
        return self.nodes.get(node_id)

    def get_nodes_by_kind(self, kind: NodeKind) -> list[GraphNode]:
        """Retrieve all nodes of a specific kind (e.g. FEATURE, SYMBOL)."""
        return [n for n in self.nodes.values() if n.kind == kind]

    def get_out_edges(
        self, node_id: str, kind: EdgeKind | None = None
    ) -> list[GraphEdge]:
        """Retrieve outgoing edges from a node, optionally filtered by edge kind."""
        edges = self._out_edges.get(node_id, [])
        if kind:
            return [e for e in edges if e.kind == kind]
        return list(edges)

    def get_in_edges(
        self, node_id: str, kind: EdgeKind | None = None
    ) -> list[GraphEdge]:
        """Retrieve incoming edges to a node, optionally filtered by edge kind."""
        edges = self._in_edges.get(node_id, [])
        if kind:
            return [e for e in edges if e.kind == kind]
        return list(edges)

    def get_neighbors(
        self, node_id: str, direction: str = "out", kind: EdgeKind | None = None
    ) -> list[GraphNode]:
        """Get neighboring nodes along outgoing or incoming edges."""
        if direction == "out":
            edges = self.get_out_edges(node_id, kind)
            target_ids = [e.target_id for e in edges]
        else:
            edges = self.get_in_edges(node_id, kind)
            target_ids = [e.source_id for e in edges]

        return [self.nodes[tid] for tid in target_ids if tid in self.nodes]

    def traverse(
        self,
        start_id: str,
        direction: str = "out",
        max_depth: int = 3,
        edge_kinds: set[EdgeKind] | None = None,
    ) -> list[tuple[GraphNode, int]]:
        """
        Cycle-safe BFS traversal from start node.
        Returns list of (GraphNode, depth) tuples.
        """
        if start_id not in self.nodes:
            return []

        visited: set[str] = {start_id}
        queue: deque = deque([(start_id, 0)])
        results: list[tuple[GraphNode, int]] = []

        while queue:
            curr_id, depth = queue.popleft()
            if depth >= max_depth:
                continue

            if direction == "out":
                edges = self._out_edges.get(curr_id, [])
            else:
                edges = self._in_edges.get(curr_id, [])

            for edge in edges:
                if edge_kinds and edge.kind not in edge_kinds:
                    continue

                next_id = edge.target_id if direction == "out" else edge.source_id
                if next_id not in visited and next_id in self.nodes:
                    visited.add(next_id)
                    next_node = self.nodes[next_id]
                    results.append((next_node, depth + 1))
                    queue.append((next_id, depth + 1))

        return results

    def extract_feature_subgraph(
        self, feature_id: str, max_depth: int = 2
    ) -> FeatureSubgraph:
        """
        Extract bounded feature subgraph connecting the feature node to all its
        primary files, symbols, tests, routes, and immediate dependencies.
        """
        feature_node = self.get_node(feature_id)
        if not feature_node:
            return FeatureSubgraph(feature_id=feature_id, feature_name=feature_id)

        # 1. Find all nodes directly linked to this feature
        linked_edges = self.get_in_edges(feature_id, EdgeKind.PART_OF_FEATURE)
        direct_node_ids = {e.source_id for e in linked_edges}
        direct_node_ids.add(feature_id)

        # Also get any tests testing this feature
        test_edges = self.get_in_edges(feature_id, EdgeKind.TESTS)
        test_node_ids = {e.source_id for e in test_edges}
        direct_node_ids.update(test_node_ids)

        subgraph_node_ids = set(direct_node_ids)
        subgraph_edges: list[GraphEdge] = []

        # 2. Add dependencies up to max_depth
        for nid in list(direct_node_ids):
            traversed = self.traverse(nid, direction="out", max_depth=max_depth)
            for node, _ in traversed:
                subgraph_node_ids.add(node.id)

        # Collect edges between nodes in subgraph
        for nid in subgraph_node_ids:
            for edge in self.get_out_edges(nid):
                if edge.target_id in subgraph_node_ids:
                    subgraph_edges.append(edge)

        subgraph_nodes = [
            self.nodes[nid] for nid in subgraph_node_ids if nid in self.nodes
        ]

        # Categorize files
        primary_files = set()
        test_files = set()
        dependency_files = set()

        for node in subgraph_nodes:
            if node.file_path:
                if node.id in direct_node_ids:
                    if node.kind == NodeKind.TEST or "test" in node.file_path.lower():
                        test_files.add(node.file_path)
                    else:
                        primary_files.add(node.file_path)
                else:
                    dependency_files.add(node.file_path)

        dependency_files = dependency_files - primary_files - test_files

        return FeatureSubgraph(
            feature_id=feature_id,
            feature_name=feature_node.name,
            nodes=subgraph_nodes,
            edges=subgraph_edges,
            primary_files=sorted(primary_files),
            dependency_files=sorted(dependency_files),
            test_files=sorted(test_files),
        )

    def total_nodes(self) -> int:
        return len(self.nodes)

    def total_edges(self) -> int:
        return sum(len(e) for e in self._out_edges.values())
