"""
Graph-Aware Context Ranker
===========================
Ranks candidate repository nodes using hybrid scoring:
  Score = 0.40 * GraphProximity + 0.30 * ExactSymbolMatch + 0.20 * SemanticRelevance + 0.10 * LexicalMatch
Ensures that the highest-utility evidence enters the model prompt first.
"""

from app.intelligence.graph.repo_graph import RepoGraph
from app.intelligence.graph.schema import GraphNode


class ContextRanker:
    """Ranks candidate graph nodes for dynamic prompt inclusion."""

    def __init__(self, graph: RepoGraph):
        self.graph = graph

    def rank_nodes(
        self,
        query: str,
        target_feature_id: str,
        candidate_nodes: list[GraphNode],
    ) -> list[tuple[GraphNode, float]]:
        """
        Rank candidate nodes according to relevance to the task query and target feature.
        Returns sorted list of (node, score) in descending relevance order.
        """
        query_terms = set(query.lower().split())
        scored: list[tuple[GraphNode, float]] = []

        for node in candidate_nodes:
            # 1. Graph Proximity score (1.0 if part of target feature, 0.5 if neighbor, 0.1 if distant)
            proximity = 0.1
            in_edges = self.graph.get_out_edges(node.id)
            if (
                any(e.target_id == target_feature_id for e in in_edges)
                or node.id == target_feature_id
            ):
                proximity = 1.0
            elif node.file_path and target_feature_id in node.file_path:
                proximity = 0.8

            # 2. Exact Symbol Match score
            node_name_lower = node.name.lower()
            symbol_match = (
                1.0 if any(term in node_name_lower for term in query_terms) else 0.0
            )

            # 3. Lexical match in docstring / metadata
            doc = (node.docstring or "").lower()
            lexical_count = sum(1 for term in query_terms if term in doc)
            lexical = min(1.0, lexical_count / max(1, len(query_terms)))

            # Semantic placeholder (defaults to 0.5 baseline)
            semantic = 0.5

            # Hybrid Score
            total_score = (
                (0.40 * proximity)
                + (0.30 * symbol_match)
                + (0.20 * semantic)
                + (0.10 * lexical)
            )
            scored.append((node, total_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
