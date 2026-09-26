import pytest
from sqlalchemy import create_engine, text

from app.intelligence.database.explain_engine import ExplainPlanEngine
from app.intelligence.database.graph_connector import DatabaseGraphConnector
from app.intelligence.database.performance_baseline import DatabasePerformanceBaseline
from app.intelligence.database.query_analyzer import QueryAnalyzer
from app.intelligence.database.safety_guard import (
    DatabaseSafetyGuard,
    DatabaseSafetyViolationError,
)
from app.intelligence.database.schema import DatabaseType, QueryRiskLevel
from app.intelligence.database.schema_introspect import DatabaseIntrospectionEngine
from app.intelligence.graph.repo_graph import RepoGraph


def test_database_introspection_sqlite(tmp_path):
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}")

    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE);"
            )
        )
        conn.execute(
            text("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                amount REAL,
                FOREIGN KEY(customer_id) REFERENCES customers(id)
            );
        """)
        )
        conn.execute(text("CREATE INDEX idx_orders_customer ON orders(customer_id);"))
        conn.commit()

    introspector = DatabaseIntrospectionEngine()
    snapshot = introspector.introspect_relational_engine(
        engine, db_type=DatabaseType.SQLITE, db_name="test_sqlite"
    )

    assert "customers" in snapshot.tables
    assert "orders" in snapshot.tables

    # Check customers columns
    cust = snapshot.tables["customers"]
    assert cust.columns["id"].primary_key is True
    assert cust.columns["name"].data_type.startswith("TEXT")

    # Check orders foreign key & index
    ord_table = snapshot.tables["orders"]
    assert any(fk["column"] == "customer_id" for fk in ord_table.foreign_keys)
    assert any(idx.name == "idx_orders_customer" for idx in ord_table.indexes)


def test_query_analyzer_anti_patterns():
    analyzer = QueryAnalyzer()

    # 1. SELECT * anti-pattern
    r1 = analyzer.analyze_query("SELECT * FROM customers WHERE id = 1;")
    assert "SELECT_STAR" in r1.detected_anti_patterns
    assert r1.risk_level == QueryRiskLevel.WARNING

    # 2. Unbounded UPDATE
    r2 = analyzer.analyze_query("UPDATE users SET is_active = 0;")
    assert "UNBOUNDED_UPDATE" in r2.detected_anti_patterns
    assert r2.risk_level == QueryRiskLevel.BLOCKED

    # 3. Deep OFFSET pagination
    r3 = analyzer.analyze_query(
        "SELECT id, name FROM logs ORDER BY created_at OFFSET 5000 LIMIT 50;"
    )
    assert "DEEP_OFFSET_PAGINATION" in r3.detected_anti_patterns
    assert r3.risk_level == QueryRiskLevel.WARNING

    # 4. Non-sargable predicate
    r4 = analyzer.analyze_query(
        "SELECT id FROM users WHERE UPPER(email) = 'TEST@EXAMPLE.COM';"
    )
    assert "NON_SARGABLE_PREDICATE" in r4.detected_anti_patterns

    # 5. ORM N+1 loop detection
    code = """
for customer in customer_list:
    orders = customer.orders
    print(orders)
"""
    findings = analyzer.detect_orm_n_plus_one(code)
    assert len(findings) == 1
    assert findings[0]["type"] == "POTENTIAL_ORM_N_PLUS_ONE"


def test_explain_plan_engine():
    engine = ExplainPlanEngine()
    mock_postgres_plan = [
        {
            "Plan": {
                "Node Type": "Seq Scan",
                "Relation Name": "large_events",
                "Startup Cost": 0.0,
                "Total Cost": 12500.0,
                "Plan Rows": 500000,
                "Filter": "(status = 'PROCESSED'::text)",
            }
        }
    ]

    root = engine.parse_postgres_json_plan(mock_postgres_plan)
    assert root.node_type == "Seq Scan"
    assert root.plan_rows == 500000

    analysis = engine.analyze_plan_bottlenecks(root, large_table_threshold=1000)
    assert analysis["has_bottlenecks"] is True
    assert len(analysis["sequential_scans_on_large_tables"]) == 1
    assert "Consider adding an index" in analysis["recommendations"][0]


def test_database_safety_guard():
    guard = DatabaseSafetyGuard()

    # 1. Level 0 Read-Only blocks mutations
    with pytest.raises(DatabaseSafetyViolationError) as exc_info:
        guard.validate_query_execution(
            "INSERT INTO users(name) VALUES ('Alice');", permission_level=0
        )
    assert "LEVEL 5 (Database Mutation) is required" in str(exc_info.value)

    # 2. Level 5 allows mutation with approval token
    assert (
        guard.validate_query_execution(
            "INSERT INTO users(name) VALUES ('Alice');",
            permission_level=5,
            human_approval_token="valid_human_token_123",
        )
        is True
    )

    # 3. Unbounded DELETE without WHERE is blocked even at Level 5 with token
    with pytest.raises(DatabaseSafetyViolationError) as exc_info2:
        guard.validate_query_execution(
            "DELETE FROM users;",
            permission_level=5,
            human_approval_token="valid_human_token_123",
        )
    assert "Unbounded DELETE without WHERE" in str(exc_info2.value)


def test_database_graph_connector():
    from app.intelligence.database.schema import (
        ColumnMetadata,
        DatabaseSchemaSnapshot,
        IndexMetadata,
        TableMetadata,
    )

    snapshot = DatabaseSchemaSnapshot(
        database_type=DatabaseType.POSTGRESQL,
        database_name="billing_db",
        tables={
            "invoices": TableMetadata(
                table_name="invoices",
                columns={
                    "id": ColumnMetadata(name="id", data_type="uuid", primary_key=True),
                    "amount": ColumnMetadata(name="amount", data_type="numeric"),
                },
                indexes=[
                    IndexMetadata(name="idx_invoices_amount", columns=["amount"]),
                ],
            )
        },
    )

    graph = RepoGraph()
    connector = DatabaseGraphConnector(graph)
    nodes_created = connector.connect_schema_snapshot(
        snapshot, feature_id="feature:billing"
    )

    assert nodes_created == 4  # 1 table + 2 columns + 1 index
    assert "table:invoices" in graph.nodes
    assert "column:invoices.amount" in graph.nodes
    assert "index:idx_invoices_amount" in graph.nodes


def test_database_performance_baseline(tmp_path):
    baseline = DatabasePerformanceBaseline(str(tmp_path))
    res = baseline.record_query_metric(
        query_template="SELECT * FROM large_table WHERE status = ?",
        execution_time_ms=350.0,
        rows_examined=50000,
        rows_returned=10,
    )
    assert res["is_slow"] is True
    assert res["is_inefficient_scan"] is True
    assert res["ratio_examined_to_returned"] == 5000.0
