"""
Two-Way Call Graph Engine
==========================
Constructs forward call trees (what does X call) and reverse call trees
(who calls X) from the RepoGraph to trace control flow.
"""

from app.intelligence.graph.repo_graph import RepoGraph
from app.intelligence.graph.schema import EdgeKind, GraphNode


class CallGraph:
    """Computes forward and reverse call trees across indexed symbols."""

    def __init__(self, graph: RepoGraph):
        self.graph = graph

    def get_forward_call_tree(
        self, symbol_id: str, max_depth: int = 3
    ) -> list[tuple[GraphNode, int]]:
        """
        Trace forward call tree: All symbols invoked directly or indirectly by symbol_id.
        Returns list of (callee_node, depth).
        """
        return self.graph.traverse(
            start_id=symbol_id,
            direction="out",
            max_depth=max_depth,
            edge_kinds={EdgeKind.CALLS},
        )

    def get_reverse_call_tree(
        self, symbol_id: str, max_depth: int = 3
    ) -> list[tuple[GraphNode, int]]:
        """
        Trace reverse call tree: All callers that directly or indirectly invoke symbol_id.
        Returns list of (caller_node, depth).
        """
        return self.graph.traverse(
            start_id=symbol_id,
            direction="in",
            max_depth=max_depth,
            edge_kinds={EdgeKind.CALLS},
        )
