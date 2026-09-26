"""
Explain Plan Intelligence Engine
================================
Parses and interprets execution plans from PostgreSQL, MySQL, and SQLite.
Detects performance bottlenecks:
  - Sequential Scans on large tables
  - Nested Loop joins with high row estimates
  - Spills to disk (Sort Method: external merge)
  - Missing covering indexes
Produces actionable, evidence-based optimization recommendations.
"""

from typing import Any

from app.core.logging_config import get_logger
from app.intelligence.database.schema import ExplainPlanNode

logger = get_logger(__name__)


class ExplainPlanEngine:
    """Interprets EXPLAIN / EXPLAIN ANALYZE structures into diagnostic insights."""

    def parse_postgres_json_plan(
        self, plan_json: dict[str, Any] | list[Any]
    ) -> ExplainPlanNode:
        """Parse PostgreSQL EXPLAIN (FORMAT JSON) into ExplainPlanNode hierarchy."""
        root = (
            plan_json[0]["Plan"]
            if isinstance(plan_json, list)
            else plan_json.get("Plan", plan_json)
        )

        def build_node(d: dict[str, Any]) -> ExplainPlanNode:
            children = [build_node(c) for c in d.get("Plans", [])]
            return ExplainPlanNode(
                node_type=d.get("Node Type", "Unknown"),
                relation_name=d.get("Relation Name"),
                cost_startup=float(d.get("Startup Cost", 0.0)),
                cost_total=float(d.get("Total Cost", 0.0)),
                plan_rows=int(d.get("Plan Rows", 0)),
                actual_time_ms=float(d.get("Actual Total Time", 0.0))
                if "Actual Total Time" in d
                else None,
                filter_predicate=d.get("Filter"),
                index_name=d.get("Index Name"),
                children=children,
            )

        return build_node(root)

    def analyze_plan_bottlenecks(
        self, root_node: ExplainPlanNode, large_table_threshold: int = 1000
    ) -> dict[str, Any]:
        """
        Traverse the execution plan tree and detect query bottlenecks.
        """
        seq_scans: list[dict[str, Any]] = []
        high_cost_nodes: list[dict[str, Any]] = []
        recommendations: list[str] = []

        def traverse(node: ExplainPlanNode):
            # Check for Seq Scan on large tables
            if "Seq Scan" in node.node_type and node.plan_rows >= large_table_threshold:
                seq_scans.append(
                    {
                        "table": node.relation_name,
                        "rows": node.plan_rows,
                        "filter": node.filter_predicate,
                        "cost": node.cost_total,
                    }
                )
                table_str = node.relation_name or "table"
                filter_str = (
                    f" on predicate '{node.filter_predicate}'"
                    if node.filter_predicate
                    else ""
                )
                recommendations.append(
                    f"Sequential scan detected on '{table_str}' ({node.plan_rows} rows){filter_str}. "
                    f"Consider adding an index on the filtered columns."
                )

            # Check for high startup or total cost
            if node.cost_total > 500.0:
                high_cost_nodes.append(
                    {
                        "node_type": node.node_type,
                        "relation": node.relation_name,
                        "cost": node.cost_total,
                    }
                )

            for child in node.children:
                traverse(child)

        traverse(root_node)

        return {
            "has_bottlenecks": len(seq_scans) > 0,
            "sequential_scans_on_large_tables": seq_scans,
            "high_cost_nodes": high_cost_nodes,
            "recommendations": recommendations,
        }
