"""
Progressive Hierarchical Context Expander
==========================================
Constructs layered context from the Feature Subgraph:
  - Level 1: Feature overview & route declarations
  - Level 2: Caller/callee signatures & docstrings for dependency files (saves 80% tokens)
  - Level 3: Full source code strictly for primary target files
"""

import os

from app.intelligence.graph.repo_graph import RepoGraph
from app.intelligence.graph.schema import FeatureSubgraph, NodeKind


class HierarchicalContextBuilder:
    """Builds progressive multi-tier context from a FeatureSubgraph."""

    def __init__(self, workspace_root: str, graph: RepoGraph):
        self.workspace_root = os.path.abspath(workspace_root)
        self.graph = graph

    def build_feature_overview(self, subgraph: FeatureSubgraph) -> str:
        """Level 1: High-level feature overview and connected files."""
        routes = [n for n in subgraph.nodes if n.metadata.get("route") is not None]

        lines = [
            f"# Feature Context: {subgraph.feature_name}",
            f"**Feature ID**: `{subgraph.feature_id}`",
            "",
            "## Primary Feature Files (In-Scope for Modification):",
        ]
        for f in subgraph.primary_files:
            lines.append(f"  - `{f}`")

        if subgraph.test_files:
            lines.append("\n## Associated Test Files:")
            for t in subgraph.test_files:
                lines.append(f"  - `{t}`")

        if routes:
            lines.append("\n## Exposed API Routes:")
            for r in routes:
                rt = r.metadata["route"]
                lines.append(
                    f"  - **{rt.get('http_method', 'GET')}** `{rt.get('path', '/')}` (`{r.name}`)"
                )

        return "\n".join(lines)

    def build_dependency_signatures(self, subgraph: FeatureSubgraph) -> str:
        """Level 2: Compact signatures and docstrings of dependencies (no full bodies)."""
        dep_files = set(subgraph.dependency_files)
        if not dep_files:
            return "No external dependencies in feature subgraph."

        lines = ["## External Dependency Signatures (Reference Only):"]
        for node in subgraph.nodes:
            if node.file_path in dep_files and node.kind in (
                NodeKind.SYMBOL,
                NodeKind.TEST,
            ):
                sig = node.metadata.get("signature", node.name)
                doc = f" - *{node.docstring.strip()}*" if node.docstring else ""
                lines.append(f"  - `{sig}` ({node.file_path}){doc}")

        return "\n".join(lines)

    def build_target_source_code(self, subgraph: FeatureSubgraph) -> str:
        """Level 3: Full source code strictly for primary files."""
        lines = []
        for rel_path in subgraph.primary_files:
            full_path = os.path.join(self.workspace_root, rel_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                        code = f.read()
                    lines.append(f"### File: `{rel_path}`\n```python\n{code}\n```\n")
                except OSError as e:
                    lines.append(
                        f"### File: `{rel_path}`\n*(Error reading file: {e})*\n"
                    )

        return "\n".join(lines)
