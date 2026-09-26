"""
Graph Storage & Persistence Engine
===================================
Persists RepoGraph to atomic JSON files in .agent/graph/ and reloads on startup.
Provides clean interface for future PostgreSQL + pgvector or Neo4j backends.
"""

import json
import os

from app.intelligence.graph.repo_graph import RepoGraph
from app.intelligence.graph.schema import GraphEdge, GraphNode


class GraphStorage:
    """Manages atomic serialization and loading of RepoGraph."""

    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)
        self.graph_dir = os.path.join(self.workspace_root, ".agent", "graph")
        self.nodes_file = os.path.join(self.graph_dir, "nodes.json")
        self.edges_file = os.path.join(self.graph_dir, "edges.json")

    def save(self, graph: RepoGraph):
        """Atomically save graph nodes and edges to disk."""
        os.makedirs(self.graph_dir, exist_ok=True)

        nodes_data = [node.model_dump() for node in graph.nodes.values()]
        edges_data = []
        for edge_list in graph._out_edges.values():
            for edge in edge_list:
                edges_data.append(edge.model_dump())

        # Atomic write nodes
        tmp_nodes = self.nodes_file + ".tmp"
        with open(tmp_nodes, "w", encoding="utf-8") as f:
            json.dump(nodes_data, f, indent=2)
        os.replace(tmp_nodes, self.nodes_file)

        # Atomic write edges
        tmp_edges = self.edges_file + ".tmp"
        with open(tmp_edges, "w", encoding="utf-8") as f:
            json.dump(edges_data, f, indent=2)
        os.replace(tmp_edges, self.edges_file)

    def load(self) -> RepoGraph | None:
        """Load graph from disk if files exist."""
        if not os.path.exists(self.nodes_file) or not os.path.exists(self.edges_file):
            return None

        try:
            with open(self.nodes_file, "r", encoding="utf-8") as f:
                nodes_data = json.load(f)
            with open(self.edges_file, "r", encoding="utf-8") as f:
                edges_data = json.load(f)

            graph = RepoGraph()
            for n_dict in nodes_data:
                graph.add_node(GraphNode(**n_dict))
            for e_dict in edges_data:
                graph.add_edge(GraphEdge(**e_dict))

            return graph
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            return None
