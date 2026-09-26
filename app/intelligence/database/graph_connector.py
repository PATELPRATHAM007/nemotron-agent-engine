"""
Database Knowledge Graph Connector
==================================
Maps introspected database schemas (tables, columns, indexes, foreign keys)
directly into the directed Repository Knowledge Graph (RepoGraph).
Connects Features and APIs to their corresponding database tables and queries.
"""

from app.core.logging_config import get_logger
from app.intelligence.database.schema import DatabaseSchemaSnapshot
from app.intelligence.graph.repo_graph import RepoGraph
from app.intelligence.graph.schema import EdgeKind, GraphEdge, GraphNode, NodeKind

logger = get_logger(__name__)


class DatabaseGraphConnector:
    """Injects database schema topology into the Repository Knowledge Graph."""

    def __init__(self, graph: RepoGraph):
        self.graph = graph

    def connect_schema_snapshot(
        self, snapshot: DatabaseSchemaSnapshot, feature_id: str | None = None
    ) -> int:
        """
        Integrates tables, columns, indexes, and relationships into RepoGraph.
        Returns total count of database nodes created.
        """
        nodes_created = 0

        for t_name, table in snapshot.tables.items():
            table_node_id = f"table:{t_name}"
            # 1. Add Table Node
            self.graph.add_node(
                GraphNode(
                    id=table_node_id,
                    name=t_name,
                    kind=NodeKind.TABLE,
                    metadata={
                        "schema": table.schema_name,
                        "row_count_estimate": table.row_count_estimate,
                        "columns_count": len(table.columns),
                    },
                )
            )
            nodes_created += 1

            if feature_id:
                self.graph.add_edge(
                    GraphEdge(
                        source_id=feature_id,
                        target_id=table_node_id,
                        kind=EdgeKind.QUERIES_TABLE,
                    )
                )

            # 2. Add Columns
            for col_name, col in table.columns.items():
                col_node_id = f"column:{t_name}.{col_name}"
                self.graph.add_node(
                    GraphNode(
                        id=col_node_id,
                        name=col_name,
                        kind=NodeKind.COLUMN,
                        metadata={
                            "data_type": col.data_type,
                            "primary_key": col.primary_key,
                            "nullable": col.nullable,
                            "foreign_key": col.foreign_key,
                        },
                    )
                )
                nodes_created += 1

                self.graph.add_edge(
                    GraphEdge(
                        source_id=table_node_id,
                        target_id=col_node_id,
                        kind=EdgeKind.DEFINES,
                    )
                )

            # 3. Add Indexes
            for idx in table.indexes:
                idx_node_id = f"index:{idx.name}"
                self.graph.add_node(
                    GraphNode(
                        id=idx_node_id,
                        name=idx.name,
                        kind=NodeKind.INDEX,
                        metadata={
                            "columns": idx.columns,
                            "is_unique": idx.is_unique,
                            "type": idx.index_type,
                        },
                    )
                )
                nodes_created += 1

                # Link Table -> Index
                self.graph.add_edge(
                    GraphEdge(
                        source_id=table_node_id,
                        target_id=idx_node_id,
                        kind=EdgeKind.DEFINES,
                    )
                )

                # Link Index -> Indexed Columns
                for col_name in idx.columns:
                    col_node_id = f"column:{t_name}.{col_name}"
                    if col_node_id in self.graph.nodes:
                        self.graph.add_edge(
                            GraphEdge(
                                source_id=idx_node_id,
                                target_id=col_node_id,
                                kind=EdgeKind.INDEXES_COLUMN,
                            )
                        )

            # 4. Foreign Key Edges
            for fk in table.foreign_keys:
                target_table = fk.get("references", "").split(".")[0]
                target_table_node_id = f"table:{target_table}"
                self.graph.add_edge(
                    GraphEdge(
                        source_id=table_node_id,
                        target_id=target_table_node_id,
                        kind=EdgeKind.REFERENCES_TABLE,
                        metadata=fk,
                    )
                )

        logger.info(
            f"Integrated {nodes_created} database nodes into RepoGraph for database {snapshot.database_name}"
        )
        return nodes_created
