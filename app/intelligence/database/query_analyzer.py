"""
Query and ORM Intelligence Analyzer
====================================
Analyzes SQL queries and ORM access patterns for anti-patterns:
  - N+1 query loops
  - SELECT * overuse
  - Full table scans on missing/unindexed columns
  - Non-sargable predicates (e.g., functions on filtered columns)
  - Inefficient OFFSET pagination on large datasets
  - Unbounded DML operations (UPDATE / DELETE without WHERE)
"""

import re
from typing import Any

from app.intelligence.database.schema import (
    QueryAnalysisReport,
    QueryRiskLevel,
    TableMetadata,
)


class QueryAnalyzer:
    """Detects performance bottlenecks, anti-patterns, and hazards in database queries."""

    # Regex patterns for static query analysis
    SELECT_STAR_PATTERN = re.compile(r"\bSELECT\s+\*\s+FROM\b", re.IGNORECASE)
    OFFSET_PATTERN = re.compile(r"\bOFFSET\s+(\d+)\b", re.IGNORECASE)
    NON_SARGABLE_PATTERN = re.compile(
        r"\bWHERE\s+([A-Za-z_]+\s*\([^)]+\))\s*(=|<|>|LIKE)", re.IGNORECASE
    )
    UNBOUNDED_UPDATE_PATTERN = re.compile(
        r"^\s*UPDATE\s+[^\s]+(?!\s+WHERE\b)", re.IGNORECASE
    )
    UNBOUNDED_DELETE_PATTERN = re.compile(
        r"^\s*DELETE\s+FROM\s+[^\s]+(?!\s+WHERE\b)", re.IGNORECASE
    )
    DESTRUCTIVE_PATTERN = re.compile(r"\b(DROP|TRUNCATE|ALTER)\b", re.IGNORECASE)

    def analyze_query(
        self,
        query: str,
        table_metadata: TableMetadata | None = None,
        estimated_table_rows: int = 0,
    ) -> QueryAnalysisReport:
        """
        Analyze SQL query string for anti-patterns, performance risks, and safety hazards.
        """
        clean_query = query.strip()
        issues: list[str] = []
        recommendations: list[str] = []
        anti_patterns: list[str] = []
        affected_tables: list[str] = []

        # Extract table name heuristic
        from_match = re.search(
            r"\b(?:FROM|INTO|UPDATE)\s+([A-Za-z0-9_]+)", clean_query, re.IGNORECASE
        )
        if from_match:
            affected_tables.append(from_match.group(1))

        # Check for destructive commands
        if self.DESTRUCTIVE_PATTERN.search(clean_query):
            issues.append("Destructive DDL statement detected (DROP/TRUNCATE/ALTER).")
            recommendations.append(
                "Destructive schema operations require explicit LEVEL 5 approval and interactive confirmation."
            )
            return QueryAnalysisReport(
                sql_query=clean_query,
                risk_level=QueryRiskLevel.BLOCKED,
                is_read_only=False,
                issues=issues,
                recommendations=recommendations,
                detected_anti_patterns=["DESTRUCTIVE_DDL"],
                affected_tables=affected_tables,
            )

        # Check for unbounded UPDATE or DELETE
        if "UPDATE" in clean_query.upper() and not re.search(
            r"\bWHERE\b", clean_query, re.IGNORECASE
        ):
            issues.append(
                "Unbounded UPDATE statement without WHERE clause: will modify ALL rows in table."
            )
            recommendations.append("Add explicit WHERE condition or partition filter.")
            return QueryAnalysisReport(
                sql_query=clean_query,
                risk_level=QueryRiskLevel.BLOCKED,
                is_read_only=False,
                issues=issues,
                recommendations=recommendations,
                detected_anti_patterns=["UNBOUNDED_UPDATE"],
                affected_tables=affected_tables,
            )

        if "DELETE" in clean_query.upper() and not re.search(
            r"\bWHERE\b", clean_query, re.IGNORECASE
        ):
            issues.append(
                "Unbounded DELETE statement without WHERE clause: will delete ALL rows in table."
            )
            recommendations.append(
                "Add explicit WHERE condition to restrict deletion scope."
            )
            return QueryAnalysisReport(
                sql_query=clean_query,
                risk_level=QueryRiskLevel.BLOCKED,
                is_read_only=False,
                issues=issues,
                recommendations=recommendations,
                detected_anti_patterns=["UNBOUNDED_DELETE"],
                affected_tables=affected_tables,
            )

        is_read_only = clean_query.upper().startswith(
            "SELECT"
        ) or clean_query.upper().startswith("EXPLAIN")

        # 1. Check SELECT *
        if self.SELECT_STAR_PATTERN.search(clean_query):
            anti_patterns.append("SELECT_STAR")
            issues.append(
                "Use of 'SELECT *' fetches unnecessary columns, prevents covering index scans, and inflates network I/O."
            )
            recommendations.append(
                "Specify only the exact columns required by the application model."
            )

        # 2. Check Large OFFSET Pagination
        offset_match = self.OFFSET_PATTERN.search(clean_query)
        if offset_match:
            offset_val = int(offset_match.group(1))
            if offset_val > 500 or estimated_table_rows > 10000:
                anti_patterns.append("DEEP_OFFSET_PAGINATION")
                issues.append(
                    f"Deep OFFSET pagination (OFFSET {offset_val}) forces the database to scan and discard {offset_val} rows."
                )
                recommendations.append(
                    "Adopt keyset/cursor-based pagination (e.g. 'WHERE id > :last_id ORDER BY id ASC LIMIT :page_size')."
                )

        # 3. Check Non-Sargable Predicates
        if self.NON_SARGABLE_PATTERN.search(clean_query):
            anti_patterns.append("NON_SARGABLE_PREDICATE")
            issues.append(
                "Function call on filtered column in WHERE clause prevents the database optimizer from using B-Tree indexes."
            )
            recommendations.append(
                "Rewrite predicate to keep the column expression bare, or create a functional/expression index."
            )

        # 4. Check Unindexed Filter Columns
        if table_metadata and "WHERE" in clean_query.upper():
            indexed_columns: set[str] = set()
            for idx in table_metadata.indexes:
                indexed_columns.update(idx.columns)

            # Find columns referenced in WHERE clause
            where_part = clean_query.split("WHERE", 1)[1]
            for col_name in table_metadata.columns:
                if (
                    re.search(rf"\b{col_name}\b", where_part)
                    and col_name not in indexed_columns
                ):
                    anti_patterns.append(f"UNINDEXED_FILTER_{col_name.upper()}")
                    issues.append(
                        f"Column '{col_name}' used in filter predicate lacks an index in table '{table_metadata.table_name}'."
                    )
                    recommendations.append(
                        f"Consider creating index 'idx_{table_metadata.table_name}_{col_name}' to avoid sequential scan."
                    )

        # Determine overall risk
        if any("UNBOUNDED" in ap for ap in anti_patterns):
            risk = QueryRiskLevel.BLOCKED
        elif len(issues) >= 2 or "DEEP_OFFSET_PAGINATION" in anti_patterns or issues:
            risk = QueryRiskLevel.WARNING
        else:
            risk = QueryRiskLevel.SAFE

        return QueryAnalysisReport(
            sql_query=clean_query,
            risk_level=risk,
            is_read_only=is_read_only,
            issues=issues,
            recommendations=recommendations,
            detected_anti_patterns=anti_patterns,
            affected_tables=affected_tables,
        )

    def detect_orm_n_plus_one(self, code_snippet: str) -> list[dict[str, Any]]:
        """
        Analyze code snippet AST for N+1 query loops.
        Flags relationships accessed inside for-loops without prefetch_related / selectinload.
        """
        findings: list[dict[str, Any]] = []
        # Regex heuristic detecting relationship access inside loops
        loop_pattern = re.compile(
            r"for\s+([A-Za-z0-9_]+)\s+in\s+([A-Za-z0-9_]+)\s*:\s*\n(?:\s+.*\n)*?\s+.*\b\1\.([A-Za-z0-9_]+)\b",
            re.MULTILINE,
        )
        for match in loop_pattern.finditer(code_snippet):
            item_var, list_var, rel_attr = match.groups()
            findings.append(
                {
                    "type": "POTENTIAL_ORM_N_PLUS_ONE",
                    "loop_target": list_var,
                    "accessed_attribute": rel_attr,
                    "message": f"Potential N+1 query loop: relationship '{rel_attr}' accessed on iterator '{item_var}' in loop over '{list_var}'.",
                    "recommendation": "Use eager loading: `selectinload` or `joinedload` in SQLAlchemy, or `select_related`/`prefetch_related` in Django.",
                }
            )
        return findings
