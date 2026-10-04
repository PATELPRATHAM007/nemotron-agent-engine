#!/usr/bin/env python3
"""
CLI Query Interface for Deep Project Intelligence Knowledge Graph
==================================================================
Usage:
    python3 scripts/query_knowledge_graph.py --stats
    python3 scripts/query_knowledge_graph.py --feature autonomous_missions
    python3 scripts/query_knowledge_graph.py --rule BR-01
    python3 scripts/query_knowledge_graph.py --impact app/modules/agent/orchestrator.py
    python3 scripts/query_knowledge_graph.py --issues
    python3 scripts/query_knowledge_graph.py --query "What controls model routing?"
    python3 scripts/query_knowledge_graph.py --export-json docs/knowledge_graph.json
"""

import argparse
import json
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.modules.intelligence.graph.knowledge_graph import (
    build_complete_project_knowledge_graph,
)


def format_header(title: str):
    print("\n" + "=" * 70)
    print(f"🧠 {title}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Query the Nemotron Deep Project Intelligence Knowledge Graph"
    )
    parser.add_argument(
        "--stats", action="store_true", help="Print overall graph statistics and health"
    )
    parser.add_argument(
        "--feature", type=str, help="Extract complete semantic subgraph for a feature"
    )
    parser.add_argument(
        "--rule", type=str, help="Inspect a specific business rule and its evidence"
    )
    parser.add_argument(
        "--impact",
        type=str,
        help="Calculate blast radius / impact scope for a file or symbol",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Query the graph using natural language or keywords",
    )
    parser.add_argument(
        "--issues",
        action="store_true",
        help="List detected architectural inconsistencies and risks",
    )
    parser.add_argument(
        "--export-json",
        type=str,
        help="Export the entire knowledge graph to a JSON file",
    )

    args = parser.parse_args()

    kg = build_complete_project_knowledge_graph()

    # Default action if no flags provided
    if not any(vars(args).values()):
        args.stats = True

    if args.stats:
        report = kg.validate_health()
        format_header("PROJECT INTELLIGENCE KNOWLEDGE GRAPH HEALTH & METRICS")
        print(f"📊 Total Graph Nodes:        {report.total_nodes}")
        print(f"🔗 Total Semantic Edges:     {report.total_edges}")
        print(f"🛡️ Evidence Grounding:      {report.evidence_coverage_pct}% of nodes backed by code lines")
        print(f"⚡ Graph Version:             v{report.graph_version}")
        print(f"📑 Schema Version:            v{report.schema_version}")
        print("\n📦 Nodes by Taxonomy Layer:")
        for k, v in sorted(report.nodes_by_kind.items()):
            print(f"   - {k:22}: {v}")
        print("\n🔀 Edges by Relationship Kind:")
        for k, v in sorted(report.edges_by_kind.items()):
            print(f"   - {k:22}: {v}")
        print("\n🎯 Confidence Distribution:")
        for k, v in sorted(report.confidence_distribution.items()):
            print(f"   - {k:10}: {v}")
        if report.orphan_nodes:
            print(f"\n⚠️ Orphan Nodes ({len(report.orphan_nodes)}): {report.orphan_nodes}")
        else:
            print("\n✅ Zero Orphan Nodes detected! Fully connected graph.")

    if args.feature:
        subgraph = kg.get_feature_subgraph(args.feature)
        if "error" in subgraph:
            print(f"\n❌ {subgraph['error']}")
            sys.exit(1)

        feat = subgraph["feature"]
        format_header(f"FEATURE SUBGRAPH: {feat['name']} ({feat['id']})")
        print(f"📝 Business Purpose: {subgraph['business_purpose']}")
        print(f"📍 Evidence:         {feat.get('evidence', 'N/A')}")

        print("\n🏢 Business Capabilities Realized:")
        for cap in subgraph["capabilities"]:
            print(f"   • {cap['name']}: {cap.get('docstring', '')}")

        print("\n⚖️ Governed Business Rules:")
        for rule in subgraph["business_rules"]:
            print(f"   • [{rule['id']}] {rule['name']}: {rule.get('docstring', '')}")
            print(f"     Evidence: {rule.get('evidence', '')}")

        print("\n🌐 APIs Exposed:")
        for api in subgraph["apis"]:
            print(f"   • {api['name']}: {api.get('docstring', '')}")
            print(f"     Evidence: {api.get('evidence', '')}")

        print("\n🖥️ UI Components:")
        for comp in subgraph["ui_components"]:
            print(f"   • {comp['name']}: {comp.get('docstring', '')}")
            print(f"     File: {comp.get('file_path', '')}")

        print("\n💾 Database Entities:")
        for ent in subgraph["database_entities"]:
            print(f"   • {ent['name']}: {ent.get('docstring', '')}")

        print("\n🧪 Verification Test Suites:")
        for test in subgraph["tests"]:
            print(f"   • {test['name']}: {test.get('docstring', '')}")

    if args.rule:
        format_header(f"BUSINESS RULE INSPECTION: {args.rule}")
        target_rule = None
        for n in kg.nodes.values():
            if n.kind.value == "BUSINESS_RULE" and (
                args.rule.lower() in n.id.lower() or args.rule.lower() in n.name.lower()
            ):
                target_rule = n
                break

        if not target_rule:
            print(f"❌ Business rule '{args.rule}' not found.")
            sys.exit(1)

        print(f"⚖️ Rule ID:       {target_rule.id}")
        print(f"📛 Rule Name:     {target_rule.name}")
        print(f"📖 Invariant:     {target_rule.docstring}")
        print(f"📍 Implementation: {target_rule.evidence}")
        print(f"🧪 Test Evidence:  {target_rule.metadata.get('tested_by_evidence', 'N/A')}")

    if args.impact:
        impact = kg.calculate_impact_scope(args.impact)
        if "error" in impact:
            print(f"\n❌ {impact['error']}")
            sys.exit(1)

        target = impact["target"]
        format_header(f"CHANGE IMPACT ANALYSIS / BLAST RADIUS FOR: {target['name']}")
        print(f"🎯 Target Node:      {target['id']} ({target['kind']})")
        print(f"📁 Source Location: {target.get('file_path', 'N/A')}")
        summary = impact["impact_summary"]
        print(f"\n💥 Blast Radius Summary:")
        print(f"   • Impacted APIs:                {summary['impacted_apis_count']}")
        print(f"   • Impacted Features:            {summary['impacted_features_count']}")
        print(f"   • Governed Business Rules:      {summary['impacted_rules_count']}")
        print(f"   • Affected Frontend Components: {summary['impacted_components_count']}")
        print(f"   • Mandatory Tests to Run:       {summary['required_tests_count']}")

        if impact["impacted_apis"]:
            print("\n🌐 Affected API Endpoints:")
            for api in impact["impacted_apis"]:
                print(f"   - {api['name']} (Evidence: {api.get('evidence', '')})")

        if impact["impacted_features"]:
            print("\n🏛️ Affected Features:")
            for feat in impact["impacted_features"]:
                print(f"   - {feat['name']}")

        if impact["impacted_business_rules"]:
            print("\n⚖️ Governed Business Rules to Guard:")
            for rule in impact["impacted_business_rules"]:
                print(f"   - [{rule['id']}] {rule['name']}")

        if impact["impacted_frontend_components"]:
            print("\n🖥️ Affected Frontend UI Surfaces:")
            for comp in impact["impacted_frontend_components"]:
                print(f"   - {comp['name']} ({comp.get('file_path', '')})")

        if impact["required_tests_to_run"]:
            print("\n🧪 Mandatory Regression Test Suites:")
            for test in impact["required_tests_to_run"]:
                print(f"   - pytest {test.get('file_path', test['name'])}")

    if args.query:
        format_header(f"NATURAL LANGUAGE GRAPH SEARCH: '{args.query}'")
        results = kg.query(args.query)
        if not results:
            print("No matching entities found in knowledge graph.")
        else:
            for i, res in enumerate(results, 1):
                n = res["node"]
                print(f"\n[{i}] ({res['score']:.1f}) {n['name']} [{n['kind']}] (ID: {n['id']})")
                if n.get("docstring"):
                    print(f"    Purpose:  {n['docstring']}")
                if n.get("evidence"):
                    print(f"    Evidence: {n['evidence']}")

    if args.issues:
        format_header("DETECTED ARCHITECTURAL INCONSISTENCIES & RISKS")
        issues = [n for n in kg.nodes.values() if n.kind.value == "ISSUE"]
        for issue in issues:
            sev = issue.metadata.get("severity", "Medium")
            print(f"\n🚨 [{sev.upper()}] {issue.id}: {issue.name}")
            print(f"   Description: {issue.docstring}")
            print(f"   Evidence:    {issue.evidence}")

    if args.export_json:
        data = kg.export_json()
        with open(args.export_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\n✅ Exported complete knowledge graph ({len(data['nodes'])} nodes, {len(data['edges'])} edges) to: {args.export_json}")


if __name__ == "__main__":
    main()
