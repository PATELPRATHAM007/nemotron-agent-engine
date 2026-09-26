"""
Database Schema Introspection Engine
====================================
Performs deterministic, read-only reflection of relational, NoSQL, and vector database structures.
Extracts tables, columns, data types, primary keys, foreign keys, unique constraints, and indexes.
"""

from typing import Any

from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging_config import get_logger
from app.intelligence.database.schema import (
    ColumnMetadata,
    DatabaseSchemaSnapshot,
    DatabaseType,
    IndexMetadata,
    TableMetadata,
    VectorCollectionMetadata,
)

logger = get_logger(__name__)


class DatabaseIntrospectionEngine:
    """Introspects live database connections and ORM metadata models."""

    def introspect_relational_engine(
        self,
        engine_or_url: Any,
        db_type: DatabaseType = DatabaseType.SQLITE,
        db_name: str = "main",
    ) -> DatabaseSchemaSnapshot:
        """
        Inspect live SQLAlchemy engine or connection URL into a deterministic DatabaseSchemaSnapshot.
        Guaranteed read-only reflection.
        """
        if isinstance(engine_or_url, str):
            engine = create_engine(engine_or_url)
        else:
            engine = engine_or_url

        inspector = inspect(engine)
        tables: dict[str, TableMetadata] = {}

        schema_names = (
            inspector.get_schema_names()
            if hasattr(inspector, "get_schema_names")
            else ["public"]
        )
        target_schemas = [
            s
            for s in schema_names
            if s not in ("information_schema", "pg_catalog", "pg_toast")
        ] or ["public"]

        for schema in target_schemas:
            try:
                table_names = inspector.get_table_names(schema=schema)
            except (SQLAlchemyError, TypeError, AttributeError):
                table_names = inspector.get_table_names()

            for t_name in table_names:
                cols_meta: dict[str, ColumnMetadata] = {}
                fks_meta: list[dict[str, str]] = []
                idx_meta: list[IndexMetadata] = []

                # Columns
                pk_constraint = inspector.get_pk_constraint(t_name, schema=schema)
                pk_cols = set(pk_constraint.get("constrained_columns", []))

                for col in inspector.get_columns(t_name, schema=schema):
                    c_name = col["name"]
                    cols_meta[c_name] = ColumnMetadata(
                        name=c_name,
                        data_type=str(col["type"]),
                        primary_key=c_name in pk_cols,
                        nullable=col.get("nullable", True),
                        default=str(col.get("default", ""))
                        if col.get("default") is not None
                        else None,
                    )

                # Foreign Keys
                for fk in inspector.get_foreign_keys(t_name, schema=schema):
                    referred_table = fk.get("referred_table", "")
                    for constrained, referred in zip(
                        fk.get("constrained_columns", []),
                        fk.get("referred_columns", []),
                        strict=False,
                    ):
                        target_str = f"{referred_table}.{referred}"
                        if constrained in cols_meta:
                            cols_meta[constrained].foreign_key = target_str
                        fks_meta.append(
                            {"column": constrained, "references": target_str}
                        )

                # Indexes
                for idx in inspector.get_indexes(t_name, schema=schema):
                    idx_meta.append(
                        IndexMetadata(
                            name=idx.get("name", ""),
                            columns=idx.get("column_names", []),
                            is_unique=idx.get("unique", False),
                            index_type=idx.get("type", "BTREE") or "BTREE",
                        )
                    )

                tables[t_name] = TableMetadata(
                    table_name=t_name,
                    schema_name=schema,
                    columns=cols_meta,
                    indexes=idx_meta,
                    foreign_keys=fks_meta,
                )

        return DatabaseSchemaSnapshot(
            database_type=db_type,
            database_name=db_name,
            tables=tables,
        )

    def introspect_vector_collection(
        self,
        collection_name: str,
        dimension: int = 1536,
        distance_metric: str = "COSINE",
        index_type: str = "HNSW",
        vector_column: str = "embedding",
        metadata_fields: list[str] | None = None,
    ) -> VectorCollectionMetadata:
        """Constructs vector database collection metadata representation."""
        return VectorCollectionMetadata(
            collection_name=collection_name,
            dimension=dimension,
            distance_metric=distance_metric.upper(),
            index_type=index_type.upper(),
            vector_column=vector_column,
            metadata_fields=metadata_fields
            or ["document_id", "source_url", "timestamp"],
        )
