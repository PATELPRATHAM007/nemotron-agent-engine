"""
Deep Project Intelligence Knowledge Graph Engine
=================================================
Constructs, indexes, validates, queries, and maintains the comprehensive semantic
knowledge graph of the Nemotron Agent Engine and Frontend ecosystem.

This engine grounds every architectural concept, business capability, user flow,
and business rule into concrete code evidence, separating WHAT the system is from
HOW it is implemented.
"""

from dataclasses import asdict, dataclass, field
import datetime
import json
import os
import re
from typing import Any

from app.modules.intelligence.graph.schema import (
    ConfidenceLevel,
    EdgeKind,
    FeatureSubgraph,
    GraphEdge,
    GraphNode,
    NodeKind,
)


@dataclass
class GraphHealthReport:
    """Quantitative validation and health metrics for the knowledge graph."""

    total_nodes: int = 0
    total_edges: int = 0
    nodes_by_kind: dict[str, int] = field(default_factory=dict)
    edges_by_kind: dict[str, int] = field(default_factory=dict)
    confidence_distribution: dict[str, int] = field(default_factory=dict)
    evidence_coverage_pct: float = 0.0
    orphan_nodes: list[str] = field(default_factory=list)
    architectural_issues: list[dict[str, Any]] = field(default_factory=list)
    graph_version: str = "2.0.0"
    schema_version: str = "2.1.0"
    generated_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


class ProjectKnowledgeGraph:
    """
    Primary Source of Truth Knowledge Graph for System Architecture,
    Business Capabilities, Rules, Data Flows, and Change Impact Analysis.
    """

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = os.path.abspath(workspace_root)
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self._out_edges: dict[str, list[GraphEdge]] = {}
        self._in_edges: dict[str, list[GraphEdge]] = {}
        self._feature_index: dict[str, str] = {}  # alias / name -> id
        self._rule_index: dict[str, str] = {}     # rule id / name -> id
        self._file_index: dict[str, str] = {}     # file path -> id

    def add_node(self, node: GraphNode) -> None:
        """Register or update a semantic node in the graph."""
        self.nodes[node.id] = node
        self._out_edges.setdefault(node.id, [])
        self._in_edges.setdefault(node.id, [])

        if node.kind == NodeKind.FEATURE:
            self._feature_index[node.id] = node.id
            self._feature_index[node.name.lower()] = node.id
        elif node.kind == NodeKind.BUSINESS_RULE:
            self._rule_index[node.id] = node.id
            self._rule_index[node.name.lower()] = node.id
        elif node.file_path:
            self._file_index[node.file_path] = node.id

    def add_edge(self, edge: GraphEdge) -> None:
        """Register a directed semantic relationship edge."""
        self.edges.append(edge)
        self._out_edges.setdefault(edge.source_id, []).append(edge)
        self._in_edges.setdefault(edge.target_id, []).append(edge)

    def get_node(self, node_id: str) -> GraphNode | None:
        """Fetch node by primary ID."""
        return self.nodes.get(node_id)

    def get_out_edges(
        self, node_id: str, kind: EdgeKind | None = None
    ) -> list[GraphEdge]:
        """Outgoing edges from a node."""
        edges = self._out_edges.get(node_id, [])
        if kind:
            return [e for e in edges if e.kind == kind]
        return list(edges)

    def get_in_edges(
        self, node_id: str, kind: EdgeKind | None = None
    ) -> list[GraphEdge]:
        """Incoming edges to a node."""
        edges = self._in_edges.get(node_id, [])
        if kind:
            return [e for e in edges if e.kind == kind]
        return list(edges)

    # --------------------------------------------------------------------------
    # Semantic Subgraph Retrieval
    # --------------------------------------------------------------------------
    def get_feature_subgraph(self, feature_id_or_name: str) -> dict[str, Any]:
        """
        Extract complete semantic subgraph for a feature:
        Capabilities, Rules, UI Components, APIs, Services, DB Entities, and Tests.
        """
        fid = self._feature_index.get(feature_id_or_name.lower(), feature_id_or_name)
        feat_node = self.get_node(fid)
        if not feat_node:
            # Try fuzzy match
            for k, v in self._feature_index.items():
                if feature_id_or_name.lower() in k:
                    fid = v
                    feat_node = self.get_node(fid)
                    break

        if not feat_node:
            return {"error": f"Feature '{feature_id_or_name}' not found in knowledge graph."}

        # Collect outgoing and incoming related nodes
        connected_node_ids = {feat_node.id}
        subgraph_edges: list[GraphEdge] = []

        # Outgoing from feature
        for edge in self.get_out_edges(feat_node.id):
            connected_node_ids.add(edge.target_id)
            subgraph_edges.append(edge)

        # Incoming to feature
        for edge in self.get_in_edges(feat_node.id):
            connected_node_ids.add(edge.source_id)
            subgraph_edges.append(edge)

        # Secondary hops for rules, tests, and database entities
        for nid in list(connected_node_ids):
            for edge in self.get_out_edges(nid):
                target = self.get_node(edge.target_id)
                if target and target.kind in (
                    NodeKind.BUSINESS_RULE,
                    NodeKind.DATABASE_ENTITY,
                    NodeKind.TEST,
                    NodeKind.API_ENDPOINT,
                ):
                    connected_node_ids.add(edge.target_id)
                    subgraph_edges.append(edge)

        subgraph_nodes = [self.nodes[nid] for nid in connected_node_ids if nid in self.nodes]

        # Partition by semantic role
        return {
            "feature": feat_node.model_dump(),
            "business_purpose": feat_node.docstring or feat_node.metadata.get("purpose", ""),
            "capabilities": [n.model_dump() for n in subgraph_nodes if n.kind == NodeKind.BUSINESS_CAPABILITY],
            "business_rules": [n.model_dump() for n in subgraph_nodes if n.kind == NodeKind.BUSINESS_RULE],
            "user_flows": [n.model_dump() for n in subgraph_nodes if n.kind == NodeKind.USER_FLOW],
            "ui_components": [n.model_dump() for n in subgraph_nodes if n.kind == NodeKind.COMPONENT],
            "apis": [n.model_dump() for n in subgraph_nodes if n.kind == NodeKind.API_ENDPOINT],
            "services_and_symbols": [n.model_dump() for n in subgraph_nodes if n.kind in (NodeKind.SYMBOL, NodeKind.FUNCTION, NodeKind.CLASS)],
            "database_entities": [n.model_dump() for n in subgraph_nodes if n.kind == NodeKind.DATABASE_ENTITY],
            "tests": [n.model_dump() for n in subgraph_nodes if n.kind == NodeKind.TEST],
            "edges": [e.model_dump() for e in subgraph_edges],
        }

    # --------------------------------------------------------------------------
    # Change Impact Analysis ("What would break if I change X?")
    # --------------------------------------------------------------------------
    def calculate_impact_scope(self, target_identifier: str) -> dict[str, Any]:
        """
        Calculate blast radius across all 6 layers:
        Target -> Calling Symbols -> Impacted APIs -> Affected Features ->
        Governed Business Rules -> Impacted Frontend Components -> Required Tests to Run.
        """
        # Resolve target node
        target_node = self.get_node(target_identifier)
        if not target_node:
            # Check by file path
            for node in self.nodes.values():
                if node.file_path and (target_identifier in node.file_path or target_identifier == node.file_path):
                    target_node = node
                    break
        if not target_node:
            # Check by symbol name
            for node in self.nodes.values():
                if node.name == target_identifier:
                    target_node = node
                    break

        if not target_node:
            return {"error": f"Identifier '{target_identifier}' not found in knowledge graph."}

        visited_ids: set[str] = {target_node.id}
        queue = [target_node.id]

        impacted_apis: set[str] = set()
        impacted_features: set[str] = set()
        impacted_rules: set[str] = set()
        impacted_components: set[str] = set()
        required_tests: set[str] = set()
        impacted_entities: set[str] = set()
        traversal_chain: list[dict[str, str]] = []

        while queue:
            curr_id = queue.pop(0)

            # Traverse incoming edges (who depends on / calls / exposes this?)
            for edge in self.get_in_edges(curr_id):
                src = self.get_node(edge.source_id)
                if not src:
                    continue

                if src.kind == NodeKind.API_ENDPOINT:
                    impacted_apis.add(src.id)
                elif src.kind == NodeKind.COMPONENT:
                    impacted_components.add(src.id)
                elif src.kind == NodeKind.TEST:
                    required_tests.add(src.id)

                if edge.source_id not in visited_ids:
                    visited_ids.add(edge.source_id)
                    queue.append(edge.source_id)
                    traversal_chain.append({
                        "from": curr_id,
                        "relation": edge.kind.value,
                        "to": edge.source_id,
                    })

            # Traverse outgoing edges (what feature / rule / DB entity does this touch?)
            for edge in self.get_out_edges(curr_id):
                tgt = self.get_node(edge.target_id)
                if not tgt:
                    continue

                if tgt.kind == NodeKind.FEATURE:
                    impacted_features.add(tgt.id)
                elif tgt.kind == NodeKind.BUSINESS_RULE:
                    impacted_rules.add(tgt.id)
                elif tgt.kind == NodeKind.DATABASE_ENTITY:
                    impacted_entities.add(tgt.id)
                elif tgt.kind == NodeKind.TEST:
                    required_tests.add(tgt.id)

                if edge.kind in (EdgeKind.PART_OF_FEATURE, EdgeKind.IMPLEMENTS_RULE, EdgeKind.CALLS):
                    if edge.target_id not in visited_ids:
                        visited_ids.add(edge.target_id)
                        queue.append(edge.target_id)

        return {
            "target": target_node.model_dump(),
            "impact_summary": {
                "impacted_apis_count": len(impacted_apis),
                "impacted_features_count": len(impacted_features),
                "impacted_rules_count": len(impacted_rules),
                "impacted_components_count": len(impacted_components),
                "required_tests_count": len(required_tests),
            },
            "impacted_apis": [self.nodes[nid].model_dump() for nid in impacted_apis if nid in self.nodes],
            "impacted_features": [self.nodes[nid].model_dump() for nid in impacted_features if nid in self.nodes],
            "impacted_business_rules": [self.nodes[nid].model_dump() for nid in impacted_rules if nid in self.nodes],
            "impacted_frontend_components": [self.nodes[nid].model_dump() for nid in impacted_components if nid in self.nodes],
            "impacted_database_entities": [self.nodes[nid].model_dump() for nid in impacted_entities if nid in self.nodes],
            "required_tests_to_run": [self.nodes[nid].model_dump() for nid in required_tests if nid in self.nodes],
            "dependency_chain_sample": traversal_chain[:15],
        }

    # --------------------------------------------------------------------------
    # Natural Language / Keyword Query Search
    # --------------------------------------------------------------------------
    def query(self, search_text: str, limit: int = 10) -> list[dict[str, Any]]:
        """Query knowledge graph by natural language intent or symbol keyword."""
        q = search_text.lower().strip()
        matches: list[tuple[float, GraphNode]] = []

        for node in self.nodes.values():
            score = 0.0
            # Direct ID match
            if q == node.id.lower():
                score += 10.0
            elif q in node.id.lower():
                score += 5.0

            # Name match
            if q in node.name.lower():
                score += 6.0

            # Docstring match
            if node.docstring and q in node.docstring.lower():
                score += 3.0

            # Metadata match
            for v in node.metadata.values():
                if isinstance(v, str) and q in v.lower():
                    score += 2.0
                elif isinstance(v, list) and any(q in str(x).lower() for x in v):
                    score += 2.0

            if score > 0:
                matches.append((score, node))

        matches.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, node in matches[:limit]:
            # Include connected context
            out_neighbors = [e.target_id for e in self.get_out_edges(node.id)[:5]]
            in_neighbors = [e.source_id for e in self.get_in_edges(node.id)[:5]]
            results.append({
                "score": score,
                "node": node.model_dump(),
                "connected_to": out_neighbors,
                "depended_on_by": in_neighbors,
            })
        return results

    # --------------------------------------------------------------------------
    # Health & Validation Reporting
    # --------------------------------------------------------------------------
    def validate_health(self) -> GraphHealthReport:
        """Run validation battery to compute graph health, coverage, and issues."""
        report = GraphHealthReport()
        report.total_nodes = len(self.nodes)
        report.total_edges = len(self.edges)

        nodes_with_evidence = 0
        orphan_nodes = []

        for nid, node in self.nodes.items():
            # Node kinds
            k_name = node.kind.value
            report.nodes_by_kind[k_name] = report.nodes_by_kind.get(k_name, 0) + 1

            # Confidence
            c_name = node.confidence.value
            report.confidence_distribution[c_name] = (
                report.confidence_distribution.get(c_name, 0) + 1
            )

            # Evidence check
            if node.evidence or node.file_path:
                nodes_with_evidence += 1

            # Orphan check (no in or out edges, except root project)
            in_count = len(self._in_edges.get(nid, []))
            out_count = len(self._out_edges.get(nid, []))
            if in_count == 0 and out_count == 0 and node.kind != NodeKind.PROJECT:
                orphan_nodes.append(nid)

        for edge in self.edges:
            e_name = edge.kind.value
            report.edges_by_kind[e_name] = report.edges_by_kind.get(e_name, 0) + 1

        if report.total_nodes > 0:
            report.evidence_coverage_pct = round(
                (nodes_with_evidence / report.total_nodes) * 100.0, 1
            )
        report.orphan_nodes = orphan_nodes

        # Collect architectural issues registered as nodes
        for node in self.nodes.values():
            if node.kind == NodeKind.ISSUE:
                report.architectural_issues.append(node.model_dump())

        return report

    # --------------------------------------------------------------------------
    # JSON Persistence & Export
    # --------------------------------------------------------------------------
    def export_json(self) -> dict[str, Any]:
        """Serialize complete knowledge graph to machine-readable JSON."""
        return {
            "metadata": {
                "graph_version": "2.0.0",
                "schema_version": "2.1.0",
                "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "workspace_root": self.workspace_root,
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
            },
            "nodes": [n.model_dump() for n in self.nodes.values()],
            "edges": [e.model_dump() for e in self.edges],
        }


# ==============================================================================
# Comprehensive Graph Populator (Grounds Evidence for the Whole Repo)
# ==============================================================================

def build_complete_project_knowledge_graph(workspace_root: str = ".") -> ProjectKnowledgeGraph:
    """
    Constructs and links the complete, multi-layered knowledge graph for both
    the backend engine and frontend Next.js applications with 100% evidence grounding.
    """
    kg = ProjectKnowledgeGraph(workspace_root=workspace_root)

    # --------------------------------------------------------------------------
    # Layer 1: Projects & Repositories
    # --------------------------------------------------------------------------
    proj_root = GraphNode(
        id="project:nemotron_dual_engine",
        name="NVIDIA Nemotron 3 Ultra Autonomous Agent System",
        kind=NodeKind.PROJECT,
        confidence=ConfidenceLevel.HIGH,
        evidence="README.md:1-50",
        last_verified="2026-10-04",
        docstring="Enterprise autonomous software engineering platform with dual-engine routing and warm sand studio UI.",
        metadata={
            "architecture": "Multi-tier agentic orchestrator with verification gates and real-time streaming",
            "backend_tech": "Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, vLLM",
            "frontend_tech": "Next.js 16, React 19, Tailwind CSS v4, TypeScript 5, SSE",
        },
    )
    kg.add_node(proj_root)

    repo_backend = GraphNode(
        id="repo:nemotron-agent-engine",
        name="nemotron-agent-engine",
        kind=NodeKind.REPOSITORY,
        file_path="app/main.py",
        confidence=ConfidenceLevel.HIGH,
        evidence="pyproject.toml / requirements.txt / app/main.py",
        last_verified="2026-10-04",
        docstring="FastAPI asynchronous agent backend, repository intelligence graph, and model gateway.",
    )
    kg.add_node(repo_backend)
    kg.add_edge(GraphEdge(source_id=proj_root.id, target_id=repo_backend.id, kind=EdgeKind.OWNS))

    repo_frontend = GraphNode(
        id="repo:nemotron-agent-frontend",
        name="nemotron-agent-frontend",
        kind=NodeKind.REPOSITORY,
        file_path="../nemotron-agent-frontend/src/app/page.tsx",
        confidence=ConfidenceLevel.HIGH,
        evidence="../nemotron-agent-frontend/package.json:1-40",
        last_verified="2026-10-04",
        docstring="Next.js 16 reactive frontend studio with Warm Sand light theme and mission control.",
    )
    kg.add_node(repo_frontend)
    kg.add_edge(GraphEdge(source_id=proj_root.id, target_id=repo_frontend.id, kind=EdgeKind.OWNS))

    # --------------------------------------------------------------------------
    # Layer 2: Business Capabilities (WHAT)
    # --------------------------------------------------------------------------
    capabilities = [
        (
            "cap:autonomous_software_engineering",
            "Autonomous Software Engineering",
            "End-to-end plan creation, tool-based file editing, test execution, bounded debugging, and git diff generation.",
            "app/modules/agent/unified_engine.py:45-120",
        ),
        (
            "cap:codebase_architectural_governance",
            "Codebase Architectural Governance",
            "Repository AST parsing, import cycle detection, layer boundary integrity, and 8-gate fail-fast verification.",
            "app/modules/agent/verification/gates.py:30-90",
        ),
        (
            "cap:multi_model_inference_routing",
            "Multi-Model Inference Routing",
            "Audited 18-step model gateway with automatic failover between Nemotron 3 Ultra, Groq, and Jio Gemini.",
            "app/modules/gateway/service.py:35-110",
        ),
        (
            "cap:financial_cost_observability",
            "Financial Cost Observability",
            "Real-time token breakdown, amortized cloud compute tracking (GCP Spot / RunPod), and budget circuit breakers.",
            "app/modules/cost/tracker.py:25-80",
        ),
        (
            "cap:identity_and_secret_management",
            "Identity & Secret Management",
            "Argon2id authentication, RFC 9700 refresh token rotation, superuser API key issuance, and SSRF filter.",
            "app/modules/auth/service.py:40-105",
        ),
        (
            "cap:realtime_developer_interaction",
            "Real-Time Developer Interaction",
            "Server-Sent Events (SSE) streaming of agent thought chains, terminal outputs, and interactive permission gates.",
            "app/modules/missions/apis.py:85-115",
        ),
    ]

    for cid, name, desc, ev in capabilities:
        cap_node = GraphNode(
            id=cid,
            name=name,
            kind=NodeKind.BUSINESS_CAPABILITY,
            confidence=ConfidenceLevel.HIGH,
            evidence=ev,
            last_verified="2026-10-04",
            docstring=desc,
        )
        kg.add_node(cap_node)
        kg.add_edge(GraphEdge(source_id=proj_root.id, target_id=cid, kind=EdgeKind.CONTAINS))

    # --------------------------------------------------------------------------
    # Layer 3: Features (Stable Domain Identities)
    # --------------------------------------------------------------------------
    features = [
        (
            "feat.autonomous_missions",
            "Autonomous Mission Lifecycle",
            "cap:autonomous_software_engineering",
            "Provides persistent mission state tracking, interactive plan approval, rollback checkpoints, and git diff review.",
            "app/modules/missions/service.py:1-40",
            ["app/modules/missions/models.py", "app/modules/missions/apis.py", "app/modules/missions/state_machine.py"],
        ),
        (
            "feat.multi_role_orchestration",
            "Multi-Role Agent Orchestrator",
            "cap:autonomous_software_engineering",
            "Coordinates specialized roles: Planner, Reviewer, Coder, Tester, and Debugger with scope containment.",
            "app/modules/agent/orchestrator.py:25-95",
            ["app/modules/agent/roles/planner.py", "app/modules/agent/roles/coder.py", "app/modules/agent/roles/tester.py"],
        ),
        (
            "feat.verification_gates",
            "8-Gate Verification Pipeline",
            "cap:codebase_architectural_governance",
            "Executes 8 fail-fast verification gates (AST syntax, imports, types, architecture, scope, tests) before commit.",
            "app/modules/agent/verification/gates.py:40-120",
            ["app/modules/agent/verification/gates.py", "app/modules/agent/verification/auto_debugger.py"],
        ),
        (
            "feat.model_gateway",
            "18-Step Audited Model Gateway",
            "cap:multi_model_inference_routing",
            "Enforces 18-step verification on every LLM call: auth, quota, tenant isolation, credentials, and usage audit.",
            "app/modules/gateway/service.py:30-100",
            ["app/modules/gateway/service.py", "app/core/llm_gateway.py", "app/modules/gateway/adapters.py"],
        ),
        (
            "feat.token_cost_analytics",
            "Cost & Token Analytics Engine",
            "cap:financial_cost_observability",
            "Tracks prompt/completion/thinking tokens, computes GCP Spot / RunPod amortization, and enforces budget guards.",
            "app/modules/cost/tracker.py:20-75",
            ["app/modules/cost/tracker.py", "app/modules/cost/pricing.py", "app/modules/cost/budget_guard.py"],
        ),
        (
            "feat.security_and_auth",
            "Identity, API Key & SSRF Security",
            "cap:identity_and_secret_management",
            "Manages users, organizations, API key issuance, refresh token families, and private subnet IP blocking.",
            "app/modules/auth/service.py:30-90",
            ["app/modules/auth/service.py", "app/modules/auth/policy_engine.py", "app/modules/auth/ssrf.py"],
        ),
        (
            "feat.repo_intelligence",
            "AST Codebase & Impact Intelligence",
            "cap:codebase_architectural_governance",
            "Extracts symbol call graphs, resolves imports, tracks file fingerprints, and computes blast radius.",
            "app/modules/intelligence/graph/repo_graph.py:20-90",
            ["app/modules/intelligence/indexing/ast_parser.py", "app/modules/intelligence/impact/impact_analyzer.py"],
        ),
        (
            "feat.agent_constitution",
            "Agent Constitutional Governance",
            "cap:codebase_architectural_governance",
            "Enforces quality rules, bootstrapping of .agent/ structure, and Architecture Decision Records (ADRs).",
            "app/modules/constitution/service.py:20-80",
            ["app/modules/constitution/service.py", "app/modules/constitution/scaffold.py"],
        ),
        (
            "feat.realtime_studio",
            "Warm Sand Agent Frontend Studio",
            "cap:realtime_developer_interaction",
            "Next.js 16 dashboard with Mission Control, Thought Stream, Terminal, and Superuser API Key Manager.",
            "../nemotron-agent-frontend/src/app/page.tsx:1-120",
            ["../nemotron-agent-frontend/src/components/agent/MissionControl.tsx", "../nemotron-agent-frontend/src/components/superuser/ApiKeyManager.tsx"],
        ),
    ]

    for fid, name, cap_id, desc, ev, files in features:
        feat_node = GraphNode(
            id=fid,
            name=name,
            kind=NodeKind.FEATURE,
            confidence=ConfidenceLevel.HIGH,
            evidence=ev,
            last_verified="2026-10-04",
            docstring=desc,
            metadata={"primary_files": files},
        )
        kg.add_node(feat_node)
        kg.add_edge(GraphEdge(source_id=fid, target_id=cap_id, kind=EdgeKind.REALIZES))

    # --------------------------------------------------------------------------
    # Layer 4: Business Rules (WHAT rules govern the system?)
    # --------------------------------------------------------------------------
    business_rules = [
        (
            "rule:BR-01",
            "Task Scope Lock & Confinement",
            "File modifications are strictly prohibited outside the authorized TaskScope whitelist. Violations halt execution.",
            "app/modules/intelligence/impact/scope_lock.py:45-75",
            "feat.multi_role_orchestration",
            "tests/test_impact_scope.py:15-40",
        ),
        (
            "rule:BR-02",
            "Bounded Self-Correction (Max 3 Fixes)",
            "Automated test-fix cycles are capped at 3 iterations. If errors persist, all changes must be rolled back.",
            "app/modules/agent/orchestrator.py:35-65",
            "feat.multi_role_orchestration",
            "tests/test_e2e_agent_mission.py:30-65",
        ),
        (
            "rule:BR-03",
            "Fail-Fast 8-Gate Pipeline Battery",
            "Sequential evaluation of Syntax -> Imports -> Types -> Architecture -> Scope -> Tests -> Lint. Halts on first failure.",
            "app/modules/agent/verification/gates.py:30-70",
            "feat.verification_gates",
            "tests/test_verification_gates.py:20-55",
        ),
        (
            "rule:BR-04",
            "18-Step Audited Model Gateway Invariant",
            "Every model request must pass 18 sequential verification checks before provider dispatch, with immutable audit logging.",
            "app/modules/gateway/service.py:40-95",
            "feat.model_gateway",
            "tests/test_security_and_gateway.py:40-80",
        ),
        (
            "rule:BR-05",
            "Quota & Token Rate Limiting",
            "Tenant request and token quotas are verified in Redis prior to model execution. Rejections emit 429 Too Many Requests.",
            "app/modules/gateway/service.py:110-140",
            "feat.model_gateway",
            "tests/test_security_and_gateway.py:90-120",
        ),
        (
            "rule:BR-06",
            "SSRF IP Denylist Filtering",
            "Outbound network calls to RFC 1918 private subnets (10.0.0.0/8, 192.168.0.0/16, 127.0.0.1, 169.254.169.254) are rejected.",
            "app/modules/auth/ssrf.py:25-70",
            "feat.security_and_auth",
            "tests/test_security_and_gateway.py:130-160",
        ),
        (
            "rule:BR-07",
            "Human-in-the-Loop Permission Gating",
            "High-risk terminal commands (rm -rf, DROP TABLE, pkill, git push -f) pause execution until explicit human authorization.",
            "app/modules/missions/permissions.py:35-85",
            "feat.autonomous_missions",
            "tests/test_unified_mission.py:45-80",
        ),
        (
            "rule:BR-08",
            "Daily Financial Budget Circuit Breaker",
            "When token expenditures exceed the configured daily budget threshold, execution is halted with CRITICAL alert level.",
            "app/modules/cost/budget_guard.py:30-65",
            "feat.token_cost_analytics",
            "tests/test_cost_analytics.py:25-60",
        ),
        (
            "rule:BR-09",
            "RFC 9700 Refresh Token Family Rotation",
            "Refresh tokens are strictly single-use. Re-use of an already consumed token revokes the entire token family.",
            "app/modules/auth/service.py:120-155",
            "feat.security_and_auth",
            "tests/test_security_and_gateway.py:50-85",
        ),
        (
            "rule:BR-10",
            "Discrete State Transition Conformance",
            "Mission state changes must strictly follow the defined VALID_TRANSITIONS graph. Illegal jumps raise InvalidStateError.",
            "app/modules/missions/state_machine.py:30-70",
            "feat.autonomous_missions",
            "tests/test_unified_mission.py:20-40",
        ),
    ]

    for rid, name, desc, ev, feat_id, test_ev in business_rules:
        rule_node = GraphNode(
            id=rid,
            name=name,
            kind=NodeKind.BUSINESS_RULE,
            confidence=ConfidenceLevel.HIGH,
            evidence=ev,
            last_verified="2026-10-04",
            docstring=desc,
            metadata={"tested_by_evidence": test_ev},
        )
        kg.add_node(rule_node)
        kg.add_edge(GraphEdge(source_id=feat_id, target_id=rid, kind=EdgeKind.CONSTRAINED_BY))

    # --------------------------------------------------------------------------
    # Layer 5: User Flows (WHAT user journeys exist?)
    # --------------------------------------------------------------------------
    user_flows = [
        (
            "flow:UF-01",
            "Autonomous Mission Execution Journey",
            "Developer submits goal in UI -> AST context gathered -> Multi-stage plan created -> Developer approves plan -> Agent executes tools -> 8-Gate verification runs -> Git diff presented.",
            "app/modules/agent/unified_engine.py:80-220",
            "feat.autonomous_missions",
        ),
        (
            "flow:UF-02",
            "Superuser API Key Provisioning",
            "Superuser logs into console -> Enters tenant details -> Backend generates Argon2id hashed key -> Returns key with role scopes.",
            "app/modules/auth/apis.py:227-250",
            "feat.security_and_auth",
        ),
        (
            "flow:UF-03",
            "Multi-Model Fast Failover Stream",
            "Client connects to SSE -> Gateway attempts Nemotron 3 Ultra -> If offline, failover to Gemini 2.5 Flash -> Stream tokens to UI.",
            "app/core/llm_gateway.py:45-110",
            "feat.model_gateway",
        ),
        (
            "flow:UF-04",
            "Mission Cost Ledger & Financial Audit",
            "Mission finishes turn -> Prompt and completion tokens tallied -> Cost amortized against Spot rates -> Written to PostgreSQL.",
            "app/modules/cost/tracker.py:60-120",
            "feat.token_cost_analytics",
        ),
        (
            "flow:UF-05",
            "Constitutional Repository Scaffolding",
            "Admin issues POST /constitution/scaffold -> Engine writes .agent/ coding standards, testing rules, and ADR templates.",
            "app/modules/constitution/service.py:40-85",
            "feat.agent_constitution",
        ),
    ]

    for ufid, name, desc, ev, feat_id in user_flows:
        flow_node = GraphNode(
            id=ufid,
            name=name,
            kind=NodeKind.USER_FLOW,
            confidence=ConfidenceLevel.HIGH,
            evidence=ev,
            last_verified="2026-10-04",
            docstring=desc,
        )
        kg.add_node(flow_node)
        kg.add_edge(GraphEdge(source_id=feat_id, target_id=ufid, kind=EdgeKind.CONTAINS))

    # --------------------------------------------------------------------------
    # Layer 6: API Endpoints (HOW services are exposed)
    # --------------------------------------------------------------------------
    api_endpoints = [
        # Missions
        ("api:POST_/api/v1/missions", "POST /api/v1/missions", "Create autonomous mission", "app/modules/missions/apis.py:32", "feat.autonomous_missions"),
        ("api:GET_/api/v1/missions/{id}", "GET /api/v1/missions/{id}", "Retrieve mission state", "app/modules/missions/apis.py:66", "feat.autonomous_missions"),
        ("api:GET_/api/v1/missions/{id}/stream", "GET /api/v1/missions/{id}/stream", "Real-time SSE event stream", "app/modules/missions/apis.py:85", "feat.autonomous_missions"),
        ("api:POST_/api/v1/missions/{id}/plan/approve", "POST /api/v1/missions/{id}/plan/approve", "Approve execution plan", "app/modules/missions/apis.py:128", "feat.autonomous_missions"),
        ("api:POST_/api/v1/missions/{id}/permissions", "POST /api/v1/missions/{id}/permissions", "Approve terminal action", "app/modules/missions/apis.py:160", "feat.autonomous_missions"),
        ("api:GET_/api/v1/missions/{id}/diff", "GET /api/v1/missions/{id}/diff", "Inspect staged git diff", "app/modules/missions/apis.py:231", "feat.autonomous_missions"),
        ("api:POST_/api/v1/missions/{id}/rollback", "POST /api/v1/missions/{id}/rollback", "Revert to checkpoint", "app/modules/missions/apis.py:199", "feat.autonomous_missions"),

        # Auth & Security
        ("api:POST_/api/v1/auth/register", "POST /api/v1/auth/register", "User registration", "app/modules/auth/apis.py:31", "feat.security_and_auth"),
        ("api:POST_/api/v1/auth/login", "POST /api/v1/auth/login", "User login & JWT issue", "app/modules/auth/apis.py:75", "feat.security_and_auth"),
        ("api:POST_/api/v1/auth/keys/generate", "POST /api/v1/auth/keys/generate", "Generate API Key", "app/modules/auth/apis.py:227", "feat.security_and_auth"),
        ("api:GET_/api/v1/auth/sessions", "GET /api/v1/auth/sessions", "List active sessions", "app/modules/auth/apis.py:173", "feat.security_and_auth"),
        ("api:DELETE_/api/v1/auth/sessions/{id}", "DELETE /api/v1/auth/sessions/{id}", "Revoke session", "app/modules/auth/apis.py:185", "feat.security_and_auth"),

        # Models & Gateway
        ("api:GET_/api/v1/models", "GET /api/v1/models", "List authorized models", "app/modules/gateway/apis.py:25", "feat.model_gateway"),
        ("api:POST_/api/v1/models/generate", "POST /api/v1/models/generate", "Synchronous model call", "app/modules/gateway/apis.py:37", "feat.model_gateway"),
        ("api:POST_/api/v1/models/stream", "POST /api/v1/models/stream", "Streamed model response", "app/modules/gateway/apis.py:49", "feat.model_gateway"),
        ("api:POST_/api/v1/admin/models", "POST /api/v1/admin/models", "Register model", "app/modules/gateway/apis.py:82", "feat.model_gateway"),

        # Cost & Ledger
        ("api:GET_/api/v1/cost/summary", "GET /api/v1/cost/summary", "Aggregated financial spend", "app/modules/cost/apis.py:13", "feat.token_cost_analytics"),
        ("api:GET_/api/v1/cost/records", "GET /api/v1/cost/records", "List mission cost records", "app/modules/cost/apis.py:30", "feat.token_cost_analytics"),
        ("api:POST_/api/v1/cost/check-budget", "POST /api/v1/cost/check-budget", "Validate budget headroom", "app/modules/cost/apis.py:66", "feat.token_cost_analytics"),

        # Intelligence
        ("api:GET_/api/v1/intelligence/graph", "GET /api/v1/intelligence/graph", "Codebase dependency graph", "app/modules/intelligence/apis.py:24", "feat.repo_intelligence"),
        ("api:POST_/api/v1/intelligence/impact", "POST /api/v1/intelligence/impact", "Calculate blast radius", "app/modules/intelligence/apis.py:35", "feat.repo_intelligence"),

        # Constitution
        ("api:GET_/api/v1/constitution/rules", "GET /api/v1/constitution/rules", "List constitutional rules", "app/modules/constitution/apis.py:25", "feat.agent_constitution"),
        ("api:POST_/api/v1/constitution/scaffold", "POST /api/v1/constitution/scaffold", "Scaffold .agent/ structure", "app/modules/constitution/apis.py:14", "feat.agent_constitution"),
    ]

    for apid, name, desc, ev, feat_id in api_endpoints:
        api_node = GraphNode(
            id=apid,
            name=name,
            kind=NodeKind.API_ENDPOINT,
            confidence=ConfidenceLevel.HIGH,
            evidence=ev,
            last_verified="2026-10-04",
            docstring=desc,
        )
        kg.add_node(api_node)
        kg.add_edge(GraphEdge(source_id=feat_id, target_id=apid, kind=EdgeKind.EXPOSES))

    # --------------------------------------------------------------------------
    # Layer 7: Frontend Components (HOW UI is presented)
    # --------------------------------------------------------------------------
    frontend_components = [
        ("comp:Navbar", "Navbar.tsx", "Header navigation, Superuser gate toggle, backend status indicator", "../nemotron-agent-frontend/src/components/navbar/Navbar.tsx:1-90", "feat.realtime_studio"),
        ("comp:MissionControl", "MissionControl.tsx", "Interactive prompt input, phase badges, stop/rollback triggers", "../nemotron-agent-frontend/src/components/agent/MissionControl.tsx:1-120", "feat.realtime_studio"),
        ("comp:ThoughtStream", "ThoughtStream.tsx", "Real-time streaming display of reasoning thoughts and CoT", "../nemotron-agent-frontend/src/components/agent/ThoughtStream.tsx:1-110", "feat.realtime_studio"),
        ("comp:ExecutionTerminal", "ExecutionTerminal.tsx", "Virtual interactive terminal showing live tool execution and test logs", "../nemotron-agent-frontend/src/components/agent/ExecutionTerminal.tsx:1-95", "feat.realtime_studio"),
        ("comp:ApiKeyManager", "ApiKeyManager.tsx", "Superuser API key generation, token revocation, and session table", "../nemotron-agent-frontend/src/components/superuser/ApiKeyManager.tsx:1-140", "feat.security_and_auth"),
        ("comp:ModelGatewayView", "ModelGatewayView.tsx", "Model registry latency ping, status indicators, and quota cards", "../nemotron-agent-frontend/src/components/superuser/ModelGatewayView.tsx:1-115", "feat.model_gateway"),
        ("comp:CostAnalyticsView", "CostAnalyticsView.tsx", "Financial token breakdown charts and historical mission cost ledger", "../nemotron-agent-frontend/src/components/superuser/CostAnalyticsView.tsx:1-125", "feat.token_cost_analytics"),
        ("comp:ConstitutionView", "ConstitutionView.tsx", "Display of 8-Gate verification battery and repository rules", "../nemotron-agent-frontend/src/components/superuser/ConstitutionView.tsx:1-110", "feat.agent_constitution"),
        ("comp:SuperuserGate", "SuperuserGate.tsx", "PIN / Passcode security barrier protecting administration views", "../nemotron-agent-frontend/src/components/superuser/SuperuserGate.tsx:1-85", "feat.security_and_auth"),
    ]

    for cid, name, desc, ev, feat_id in frontend_components:
        comp_node = GraphNode(
            id=cid,
            name=name,
            kind=NodeKind.COMPONENT,
            file_path=ev.split(":")[0],
            confidence=ConfidenceLevel.HIGH,
            evidence=ev,
            last_verified="2026-10-04",
            docstring=desc,
        )
        kg.add_node(comp_node)
        kg.add_edge(GraphEdge(source_id=feat_id, target_id=cid, kind=EdgeKind.RENDERED_BY))

    # Link Frontend Components to APIs they consume
    kg.add_edge(GraphEdge(source_id="comp:ApiKeyManager", target_id="api:GET_/api/v1/auth/sessions", kind=EdgeKind.CONSUMES))
    kg.add_edge(GraphEdge(source_id="comp:ApiKeyManager", target_id="api:POST_/api/v1/auth/keys/generate", kind=EdgeKind.CONSUMES))
    kg.add_edge(GraphEdge(source_id="comp:ModelGatewayView", target_id="api:GET_/api/v1/models", kind=EdgeKind.CONSUMES))
    kg.add_edge(GraphEdge(source_id="comp:CostAnalyticsView", target_id="api:GET_/api/v1/cost/summary", kind=EdgeKind.CONSUMES))
    kg.add_edge(GraphEdge(source_id="comp:CostAnalyticsView", target_id="api:GET_/api/v1/cost/records", kind=EdgeKind.CONSUMES))
    kg.add_edge(GraphEdge(source_id="comp:ConstitutionView", target_id="api:GET_/api/v1/constitution/rules", kind=EdgeKind.CONSUMES))
    kg.add_edge(GraphEdge(source_id="comp:MissionControl", target_id="api:POST_/api/v1/missions", kind=EdgeKind.CONSUMES))
    kg.add_edge(GraphEdge(source_id="comp:ThoughtStream", target_id="api:GET_/api/v1/missions/{id}/stream", kind=EdgeKind.CONSUMES))

    # --------------------------------------------------------------------------
    # Layer 8: Database Entities (HOW data is persisted)
    # --------------------------------------------------------------------------
    db_entities = [
        ("entity:missions", "missions", "Primary persistent mission record", "app/modules/missions/models.py:25-50", "feat.autonomous_missions"),
        ("entity:mission_messages", "mission_messages", "User and agent dialogue history", "app/modules/missions/models.py:55-80", "feat.autonomous_missions"),
        ("entity:mission_events", "mission_events", "Granular thought and execution events", "app/modules/missions/models.py:85-115", "feat.autonomous_missions"),
        ("entity:mission_plans", "mission_plans", "Multi-stage hierarchical plans", "app/modules/missions/models.py:120-145", "feat.autonomous_missions"),
        ("entity:mission_diffs", "mission_diffs", "Staged git diffs produced by agent", "app/modules/missions/models.py:150-175", "feat.autonomous_missions"),
        ("entity:mission_checkpoints", "mission_checkpoints", "Rollback snapshots before edit", "app/modules/missions/models.py:180-205", "feat.autonomous_missions"),
        ("entity:cost_records", "cost_records", "Financial spend and token audit entries", "app/modules/cost/models.py:15-45", "feat.token_cost_analytics"),
        ("entity:security_users", "security_users", "User credentials and RBAC roles", "app/modules/auth/models.py:25-50", "feat.security_and_auth"),
        ("entity:security_sessions", "security_sessions", "Active authentication sessions", "app/modules/auth/models.py:55-80", "feat.security_and_auth"),
        ("entity:refresh_tokens", "refresh_tokens", "Rotating single-use refresh token families", "app/modules/auth/models.py:85-115", "feat.security_and_auth"),
        ("entity:model_providers", "model_providers", "Model inference providers (vLLM, Groq)", "app/modules/gateway/models.py:15-40", "feat.model_gateway"),
        ("entity:registered_models", "registered_models", "Model catalog with capability flags", "app/modules/gateway/models.py:45-75", "feat.model_gateway"),
    ]

    for eid, name, desc, ev, feat_id in db_entities:
        ent_node = GraphNode(
            id=eid,
            name=name,
            kind=NodeKind.DATABASE_ENTITY,
            confidence=ConfidenceLevel.HIGH,
            evidence=ev,
            last_verified="2026-10-04",
            docstring=desc,
        )
        kg.add_node(ent_node)
        kg.add_edge(GraphEdge(source_id=feat_id, target_id=eid, kind=EdgeKind.PERSISTS_TO))

    # --------------------------------------------------------------------------
    # Layer 9: Test Suites (HOW quality is verified)
    # --------------------------------------------------------------------------
    test_suites = [
        ("test:test_ast_parser", "test_ast_parser.py", "AST parsing, functions, classes", "tests/test_ast_parser.py:1-40", "feat.repo_intelligence"),
        ("test:test_repo_graph", "test_repo_graph.py", "RepoGraph traversal and subgraphs", "tests/test_repo_graph.py:1-45", "feat.repo_intelligence"),
        ("test:test_impact_scope", "test_impact_scope.py", "TaskScope containment and blast radius", "tests/test_impact_scope.py:1-50", "feat.repo_intelligence"),
        ("test:test_verification_gates", "test_verification_gates.py", "8-Gate verification battery", "tests/test_verification_gates.py:1-55", "feat.verification_gates"),
        ("test:test_security_and_gateway", "test_security_and_gateway.py", "Argon2id, JWT, SSRF, Model Gateway", "tests/test_security_and_gateway.py:1-80", "feat.security_and_auth"),
        ("test:test_unified_mission", "test_unified_mission.py", "Mission state machine, slash commands", "tests/test_unified_mission.py:1-75", "feat.autonomous_missions"),
        ("test:test_orchestrator_roles", "test_orchestrator_roles.py", "Planner, Reviewer, Coder, Tester", "tests/test_orchestrator_roles.py:1-60", "feat.multi_role_orchestration"),
        ("test:test_cost_analytics", "test_cost_analytics.py", "Token accounting and budget guard", "tests/test_cost_analytics.py:1-55", "feat.token_cost_analytics"),
        ("test:test_cost_db", "test_cost_db.py", "PostgreSQL CostRecord persistence", "tests/test_cost_db.py:1-45", "feat.token_cost_analytics"),
        ("test:test_permissions_and_gates", "test_permissions_and_gates.py", "PermissionLevels 0-4 and approvals", "tests/test_permissions_and_gates.py:1-50", "feat.autonomous_missions"),
    ]

    for tid, name, desc, ev, feat_id in test_suites:
        test_node = GraphNode(
            id=tid,
            name=name,
            kind=NodeKind.TEST,
            file_path=ev.split(":")[0],
            confidence=ConfidenceLevel.HIGH,
            evidence=ev,
            last_verified="2026-10-04",
            docstring=desc,
        )
        kg.add_node(test_node)
        kg.add_edge(GraphEdge(source_id=tid, target_id=feat_id, kind=EdgeKind.TESTS))

    # --------------------------------------------------------------------------
    # Layer 10: Detected Architectural Issues & Risks
    # --------------------------------------------------------------------------
    architectural_issues = [
        (
            "issue:ISSUE-01",
            "Parallel Agent Endpoint Surface Duplication",
            "High",
            "The backend exposes both legacy `/api/v1/agent/*` and primary `/api/v1/missions/*`. While preserving backwards compatibility, maintenance of two parallel routing pipelines risks drift.",
            "app/modules/agent/apis.py vs app/modules/missions/apis.py",
        ),
        (
            "issue:ISSUE-02",
            "Frontend SSE Hook Targets Legacy Route",
            "Medium",
            "`useAgentStream.ts` in the frontend connects to `/api/v1/agent/stream/{id}` instead of `/api/v1/missions/{id}/stream`. Both stream events, but `/missions` supports full persistence and interactive plan approval.",
            "../nemotron-agent-frontend/src/hooks/useAgentStream.ts:38",
        ),
        (
            "issue:ISSUE-03",
            "Alembic Base Partial ORM Model Registration",
            "Medium",
            "`app/db/base.py` currently imports only `CostRecord` instead of all SQLAlchemy models (`Mission`, `User`, `RegisteredModel`), which could cause autogenerate migrations to omit mission tables.",
            "app/db/base.py:3-6",
        ),
        (
            "issue:ISSUE-04",
            "Cross-Project TaskScope Confinement Boundary",
            "Low",
            "The backend and frontend live in adjacent directories (`/nemotron-agent-engine` and `/nemotron-agent-frontend`). Backend `TaskScope` by default locks to engine root, requiring explicit cross-workspace paths for full-stack edits.",
            "app/modules/intelligence/impact/scope_lock.py:20-55",
        ),
    ]

    for iid, name, severity, desc, ev in architectural_issues:
        issue_node = GraphNode(
            id=iid,
            name=name,
            kind=NodeKind.ISSUE,
            confidence=ConfidenceLevel.HIGH,
            evidence=ev,
            last_verified="2026-10-04",
            docstring=desc,
            metadata={"severity": severity},
        )
        kg.add_node(issue_node)
        kg.add_edge(GraphEdge(source_id="project:nemotron_dual_engine", target_id=iid, kind=EdgeKind.HAS_BUG))

    return kg

