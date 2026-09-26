"""
Change Impact Analysis Engine
==============================
Calculates the exact blast radius of a proposed code change before any files
are modified. Traverses the knowledge graph to quantify affected callers,
impacted API routes, test suites, and cross-module dependencies.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.intelligence.graph.repo_graph import RepoGraph
from app.intelligence.graph.schema import EdgeKind, NodeKind
from app.intelligence.impact.call_graph import CallGraph


class ImpactReport(BaseModel):
    """Structured report detailing the calculated blast radius of a change."""

    target_id: str
    target_files: list[str] = Field(default_factory=list)
    direct_dependencies_count: int = 0
    indirect_dependencies_count: int = 0
    affected_callers: list[str] = Field(default_factory=list)
    affected_routes: list[dict[str, Any]] = Field(default_factory=list)
    affectedTests: list[str] = Field(
        default_factory=list, description="Tests requiring execution after modification"
    )
    affected_files: list[str] = Field(default_factory=list)
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL

    def summary(self) -> str:
        return (
            f"Impact Analysis for {self.target_id}:\n"
            f"  • Direct Callers:     {self.direct_dependencies_count}\n"
            f"  • Indirect Callers:   {self.indirect_dependencies_count}\n"
            f"  • Affected Tests:     {len(self.affectedTests)}\n"
            f"  • Affected API Routes:{len(self.affected_routes)}\n"
            f"  • Total Files Impacted:{len(self.affected_files)}\n"
            f"  • Assessed Risk Level: {self.risk_level}"
        )


class ImpactAnalyzer:
    """Analyzes the blast radius of target symbols or files."""

    def __init__(self, graph: RepoGraph):
        self.graph = graph
        self.call_graph = CallGraph(graph)

    def analyze(self, target_id: str, max_depth: int = 3) -> ImpactReport:
        """Calculate complete impact report for a target symbol or file."""
        target_node = self.graph.get_node(target_id)
        target_files: list[str] = []

        if target_node and target_node.file_path:
            target_files.append(target_node.file_path)

        # 1. Reverse Call Graph Traversal (Who calls target?)
        reverse_calls = self.call_graph.get_reverse_call_tree(
            target_id, max_depth=max_depth
        )

        direct_callers: list[str] = []
        indirect_callers: list[str] = []
        affected_files: set[str] = set(target_files)
        affected_routes: list[dict[str, Any]] = []
        affected_tests: set[str] = set()

        for node, depth in reverse_calls:
            if depth == 1:
                direct_callers.append(node.id)
            else:
                indirect_callers.append(node.id)

            if node.file_path:
                affected_files.add(node.file_path)

            # Check if caller exposes an API route
            if node.metadata.get("route"):
                affected_routes.append(
                    {
                        "symbol_id": node.id,
                        "route": node.metadata.get("route"),
                    }
                )

            # Check if caller is a test
            if node.kind == NodeKind.TEST:
                affected_tests.add(node.id)

        # 2. Check direct tests linked via TESTS edges to target or callers
        all_affected_symbols = {target_id} | set(direct_callers)
        for sym_id in all_affected_symbols:
            test_edges = self.graph.get_in_edges(sym_id, EdgeKind.TESTS)
            for te in test_edges:
                affected_tests.add(te.source_id)

        # 3. Determine Risk Level
        risk = "LOW"
        if len(affected_routes) > 0 or len(direct_callers) > 5:
            risk = "HIGH"
        elif len(direct_callers) > 10:
            risk = "CRITICAL"
        elif len(direct_callers) > 0 or len(affected_files) > 2:
            risk = "MEDIUM"

        return ImpactReport(
            target_id=target_id,
            target_files=target_files,
            direct_dependencies_count=len(direct_callers),
            indirect_dependencies_count=len(indirect_callers),
            affected_callers=direct_callers + indirect_callers,
            affected_routes=affected_routes,
            affectedTests=sorted(affected_tests),
            affected_files=sorted(affected_files),
            risk_level=risk,
        )
