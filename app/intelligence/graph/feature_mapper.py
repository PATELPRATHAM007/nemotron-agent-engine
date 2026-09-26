"""
Feature Mapper & Graph Construction Engine
===========================================
Transforms parsed SymbolIndex and AST metadata into the 8-layer Repository Knowledge Graph.
Discovers and clusters business features, mapping them to files, routes, models, and tests.
"""

import os

from app.intelligence.graph.repo_graph import RepoGraph
from app.intelligence.graph.schema import EdgeKind, GraphEdge, GraphNode, NodeKind
from app.intelligence.indexing.ast_parser import SymbolDefinition
from app.intelligence.indexing.symbol_extractor import SymbolIndex


class FeatureMapper:
    """Constructs the complete RepoGraph from indexed modules and symbols."""

    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)

    def build_graph(self, index: SymbolIndex) -> RepoGraph:
        """Build full multi-layer knowledge graph from SymbolIndex."""
        graph = RepoGraph()

        # 1. Root Repository Node
        repo_name = os.path.basename(self.workspace_root)
        repo_node = GraphNode(
            id=f"repo:{repo_name}",
            name=repo_name,
            kind=NodeKind.REPOSITORY,
            metadata={"workspace_root": self.workspace_root},
        )
        graph.add_node(repo_node)

        # 2. Add File & Symbol Nodes
        modules_seen = set()
        features_map: dict[str, str] = {}  # feature_name -> feature_id

        for file_path, parsed in index.modules.items():
            rel_file = os.path.relpath(file_path, self.workspace_root)
            file_node_id = f"file:{rel_file}"

            # File Node
            file_node = GraphNode(
                id=file_node_id,
                name=os.path.basename(rel_file),
                kind=NodeKind.FILE,
                file_path=rel_file,
                metadata={
                    "module_path": parsed.module_path,
                    "file_hash": parsed.fingerprint.file_hash,
                    "ast_hash": parsed.fingerprint.ast_hash,
                },
            )
            graph.add_node(file_node)

            # Module Node
            mod_parts = parsed.module_path.split(".")
            if len(mod_parts) > 1:
                pkg_name = mod_parts[0]
                mod_node_id = f"module:{pkg_name}"
                if mod_node_id not in modules_seen:
                    modules_seen.add(mod_node_id)
                    mod_node = GraphNode(
                        id=mod_node_id,
                        name=pkg_name,
                        kind=NodeKind.MODULE,
                    )
                    graph.add_node(mod_node)
                    graph.add_edge(
                        GraphEdge(
                            source_id=repo_node.id,
                            target_id=mod_node_id,
                            kind=EdgeKind.DEPENDS_ON,
                        )
                    )

                graph.add_edge(
                    GraphEdge(
                        source_id=mod_node_id,
                        target_id=file_node_id,
                        kind=EdgeKind.DEFINES,
                    )
                )

            # Symbols in this file
            for sym in parsed.symbols:
                sym_node_id = f"sym:{sym.id}"
                kind = (
                    NodeKind.TEST
                    if ("test" in sym.name.lower() or "tests/" in rel_file)
                    else NodeKind.SYMBOL
                )
                sym_node = GraphNode(
                    id=sym_node_id,
                    name=sym.name,
                    kind=kind,
                    file_path=rel_file,
                    line_start=sym.line_start,
                    line_end=sym.line_end,
                    docstring=sym.docstring,
                    metadata={
                        "signature": sym.signature,
                        "is_async": sym.is_async,
                        "route": sym.route_info,
                    },
                )
                graph.add_node(sym_node)
                graph.add_edge(
                    GraphEdge(
                        source_id=file_node_id,
                        target_id=sym_node_id,
                        kind=EdgeKind.DEFINES,
                    )
                )

                # Feature discovery from route or module conventions
                discovered_feature = self._discover_feature(rel_file, sym)
                if discovered_feature:
                    feat_id = f"feat:{discovered_feature.lower().replace(' ', '_')}"
                    if feat_id not in features_map:
                        features_map[discovered_feature] = feat_id
                        feat_node = GraphNode(
                            id=feat_id,
                            name=discovered_feature,
                            kind=NodeKind.FEATURE,
                            metadata={"entry_point": sym.name},
                        )
                        graph.add_node(feat_node)
                        graph.add_edge(
                            GraphEdge(
                                source_id=repo_node.id,
                                target_id=feat_id,
                                kind=EdgeKind.PART_OF_FEATURE,
                            )
                        )

                    # Connect symbol & file to feature
                    graph.add_edge(
                        GraphEdge(
                            source_id=sym_node_id,
                            target_id=feat_id,
                            kind=EdgeKind.PART_OF_FEATURE,
                        )
                    )
                    graph.add_edge(
                        GraphEdge(
                            source_id=file_node_id,
                            target_id=feat_id,
                            kind=EdgeKind.PART_OF_FEATURE,
                        )
                    )

        # 3. Add Call Edges (SYMBOL -> SYMBOL)
        for file_path, parsed in index.modules.items():
            rel_file = os.path.relpath(file_path, self.workspace_root)
            for sym in parsed.symbols:
                source_sym_id = f"sym:{sym.id}"
                for called_name in sym.calls:
                    # Look up if called_name matches any symbol in the index
                    matching_targets = index.find_by_name(called_name)
                    for target in matching_targets:
                        target_sym_id = f"sym:{target.id}"
                        if graph.get_node(target_sym_id):
                            graph.add_edge(
                                GraphEdge(
                                    source_id=source_sym_id,
                                    target_id=target_sym_id,
                                    kind=EdgeKind.CALLS,
                                )
                            )

        # 4. Add Test Edges (TEST -> SYMBOL / FEATURE)
        for node in graph.nodes.values():
            if node.kind == NodeKind.TEST:
                # Infer target symbol from test name (e.g. test_login -> login)
                clean_test_name = node.name.replace("test_", "")
                candidates = index.find_by_name(clean_test_name)
                for cand in candidates:
                    cand_sym_id = f"sym:{cand.id}"
                    if graph.get_node(cand_sym_id):
                        graph.add_edge(
                            GraphEdge(
                                source_id=node.id,
                                target_id=cand_sym_id,
                                kind=EdgeKind.TESTS,
                            )
                        )

        return graph

    def _discover_feature(self, file_path: str, sym: SymbolDefinition) -> str | None:
        """Infer business feature name from file path or route metadata."""
        # 1. From FastAPI route info
        if sym.route_info:
            path = sym.route_info.get("path", "")
            parts = [
                p
                for p in path.split("/")
                if p and not p.startswith("{") and p not in ("api", "v1", "v2")
            ]
            if parts:
                return parts[0].capitalize()

        # 2. From directory path
        p_lower = file_path.lower()
        if "auth" in p_lower:
            return "Authentication"
        elif "agent" in p_lower:
            return "Agent Engine"
        elif "infra" in p_lower or "cloud" in p_lower:
            return "Cloud Infrastructure"
        elif "tool" in p_lower:
            return "Agent Tools"
        elif "logger" in p_lower or "logging" in p_lower:
            return "Observability & Logging"

        return None
