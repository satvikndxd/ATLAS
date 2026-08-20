"""Connector contracts and optional database adapters.

The reference engine uses the same conceptual connector contract as live adapters:
`discover_schema`, `read_rows`, `write_rows`, transaction lifecycle, and reconcile.
Database drivers remain optional and are only invoked in explicitly configured live
integration tests.
"""
from __future__ import annotations

import csv
import json
from contextlib import contextmanager
from abc import ABC, abstractmethod
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping

from .reconcile import reconcile


class ConnectorError(RuntimeError):
    pass


class SourceConnector(ABC):
    @abstractmethod
    def list_tables(self) -> list[str]: ...

    @abstractmethod
    def read_table(self, table: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    def fingerprint(self, table: str) -> dict[str, Any]: ...

    def discover_schema(self) -> dict[str, Any]:
        return {table: self.fingerprint(table) for table in self.list_tables()}

    def read_rows(self, table: str) -> list[dict[str, Any]]:
        return self.read_table(table)


class TargetConnector(SourceConnector):
    @abstractmethod
    def write_table(self, table: str, rows: list[Mapping[str, Any]], key: str) -> int: ...

    def write_rows(self, table: str, rows: list[Mapping[str, Any]], key: str) -> int:
        return self.write_table(table, rows, key)

    def begin_transaction(self) -> Any:
        return self

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def reconcile(self, migration_id: str, table: str, source_rows: list[Mapping[str, Any]], key: str) -> Any:
        return reconcile(migration_id, table, source_rows, self.read_rows(table), key)


class FileConnector(SourceConnector):
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _path(self, table: str) -> Path:
        for suffix in (".json", ".jsonl", ".csv"):
            candidate = self.root / f"{table}{suffix}"
            if candidate.exists():
                return candidate
        raise ConnectorError(f"table {table!r} not found beneath {self.root}")

    def list_tables(self) -> list[str]:
        return sorted({path.stem for path in self.root.glob("*") if path.suffix in {".json", ".jsonl", ".csv"}})

    def read_table(self, table: str) -> list[dict[str, Any]]:
        path = self._path(table)
        if path.suffix == ".csv":
            with path.open(newline="", encoding="utf-8") as handle:
                return [dict(row) for row in csv.DictReader(handle)]
        if path.suffix == ".jsonl":
            return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, list) else list(raw.values())

    def fingerprint(self, table: str) -> dict[str, Any]:
        rows = self.read_table(table)
        return {"table": table, "rows": len(rows), "columns": sorted({key for row in rows for key in row})}


class InMemoryConnector(TargetConnector):
    def __init__(self, tables: Mapping[str, list[Mapping[str, Any]]] | None = None):
        self.tables = {name: [dict(row) for row in rows] for name, rows in (tables or {}).items()}
        self._transaction_snapshot: dict[str, list[dict[str, Any]]] | None = None

    def list_tables(self) -> list[str]:
        return sorted(self.tables)

    def read_table(self, table: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self.tables.get(table, [])]

    def fingerprint(self, table: str) -> dict[str, Any]:
        rows = self.read_table(table)
        return {"table": table, "rows": len(rows), "columns": sorted({key for row in rows for key in row})}

    def write_table(self, table: str, rows: list[Mapping[str, Any]], key: str) -> int:
        existing = {str(row.get(key)): dict(row) for row in self.tables.get(table, [])}
        for row in rows:
            existing[str(row.get(key))] = dict(row)
        self.tables[table] = list(existing.values())
        return len(rows)

    def begin_transaction(self) -> "InMemoryConnector":
        if self._transaction_snapshot is not None:
            raise ConnectorError("nested transactions are not supported")
        self._transaction_snapshot = deepcopy(self.tables)
        return self

    def commit(self) -> None:
        self._transaction_snapshot = None

    def rollback(self) -> None:
        if self._transaction_snapshot is not None:
            self.tables = self._transaction_snapshot
            self._transaction_snapshot = None


class DBConnector(TargetConnector):
    """DB-API connector with safe identifiers and explicit transaction handles."""

    placeholder = "?"
    quote_start = "["
    quote_end = "]"

    def __init__(self, connection_factory: Any):
        self.connection_factory = connection_factory
        self._active_connection: Any | None = None

    @contextmanager
    def _connection(self):
        if self._active_connection is not None:
            yield self._active_connection
            return
        connection = self.connection_factory()
        try:
            yield connection
            connection.commit()
        except Exception:
            try:
                connection.rollback()
            finally:
                raise
        finally:
            close = getattr(connection, "close", None)
            if close is not None:
                close()

    def begin_transaction(self) -> "DBConnector":
        if self._active_connection is not None:
            raise ConnectorError("nested transactions are not supported")
        self._active_connection = self.connection_factory()
        return self

    def commit(self) -> None:
        if self._active_connection is None:
            raise ConnectorError("no active transaction")
        try:
            self._active_connection.commit()
        finally:
            close = getattr(self._active_connection, "close", None)
            if close is not None:
                close()
            self._active_connection = None

    def rollback(self) -> None:
        if self._active_connection is None:
            raise ConnectorError("no active transaction")
        try:
            self._active_connection.rollback()
        finally:
            close = getattr(self._active_connection, "close", None)
            if close is not None:
                close()
            self._active_connection = None

    def _quote(self, identifier: str) -> str:
        if not identifier.replace("_", "").isalnum():
            raise ConnectorError(f"unsafe identifier: {identifier}")
        return f"{self.quote_start}{identifier}{self.quote_end}"

    def list_tables(self) -> list[str]:
        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
            return sorted(str(row[0]) for row in cursor.fetchall())

    def discover_schema(self) -> dict[str, Any]:
        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS ORDER BY TABLE_NAME, ORDINAL_POSITION")
            schema: dict[str, list[dict[str, Any]]] = {}
            for table, column, data_type, nullable in cursor.fetchall():
                schema.setdefault(str(table), []).append({"name": str(column), "data_type": str(data_type), "nullable": str(nullable).upper() == "YES"})
            return schema

    def read_table(self, table: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(f"SELECT * FROM {self._quote(table)}")
            names = [column[0] for column in cursor.description]
            return [dict(zip(names, row)) for row in cursor.fetchall()]

    def fingerprint(self, table: str) -> dict[str, Any]:
        rows = self.read_table(table)
        return {"table": table, "rows": len(rows), "columns": sorted({key for row in rows for key in row})}

    def write_table(self, table: str, rows: list[Mapping[str, Any]], key: str) -> int:
        if not rows:
            return 0
        columns = sorted({column for row in rows for column in row})
        placeholders = ", ".join(self.placeholder for _ in columns)
        column_sql = ", ".join(self._quote(column) for column in columns)
        table_sql = self._quote(table)
        update_columns = [column for column in columns if column != key]
        with self._connection() as connection:
            cursor = connection.cursor()
            if update_columns:
                assignments = ", ".join(f"{self._quote(column)} = source.{self._quote(column)}" for column in update_columns)
                source_columns = ", ".join(f"{self.placeholder} AS {self._quote(column)}" for column in columns)
                merge_sql = f"MERGE INTO {table_sql} AS target USING (SELECT {source_columns}) AS source ON target.{self._quote(key)} = source.{self._quote(key)} WHEN MATCHED THEN UPDATE SET {assignments} WHEN NOT MATCHED THEN INSERT ({column_sql}) VALUES ({', '.join(f'source.{self._quote(column)}' for column in columns)});"
                cursor.executemany(merge_sql, [tuple(row.get(column) for column in columns) for row in rows])
            else:
                cursor.executemany(f"INSERT INTO {table_sql} ({column_sql}) VALUES ({placeholders})", [tuple(row.get(column) for column in columns) for row in rows])
            return len(rows)


class SQLServerAdapter(DBConnector):
    """SQL Server adapter; requires pyodbc and a live SQL Server connection string."""

    @classmethod
    def from_connection_string(cls, connection_string: str) -> "SQLServerAdapter":
        def connect() -> Any:
            try:
                import pyodbc  # type: ignore
            except ImportError as exc:
                raise ConnectorError("install pyodbc to use SQLServerAdapter") from exc
            return pyodbc.connect(connection_string, autocommit=False)
        return cls(connect)


class PostgresAdapter(DBConnector):
    """PostgreSQL adapter; requires psycopg and a live PostgreSQL DSN."""
    placeholder = "%s"
    quote_start = '"'
    quote_end = '"'

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresAdapter":
        def connect() -> Any:
            try:
                import psycopg  # type: ignore
            except ImportError as exc:
                raise ConnectorError("install psycopg to use PostgresAdapter") from exc
            return psycopg.connect(dsn)
        return cls(connect)
