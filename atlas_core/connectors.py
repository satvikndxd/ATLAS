"""Connector contracts and dependency-light local adapters.

Database-specific connectors are intentionally optional.  The reference engine
runs offline through the in-memory and file adapters, while SQL Server/Postgres
adapters expose the queries and lifecycle expected by the control plane.
"""
from __future__ import annotations

import csv
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable, Mapping


class ConnectorError(RuntimeError):
    pass


class SourceConnector(ABC):
    @abstractmethod
    def list_tables(self) -> list[str]: ...

    @abstractmethod
    def read_table(self, table: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    def fingerprint(self, table: str) -> dict[str, Any]: ...


class TargetConnector(SourceConnector):
    @abstractmethod
    def write_table(self, table: str, rows: list[Mapping[str, Any]], key: str) -> int: ...


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


class DBConnector(SourceConnector):
    """Optional DB-API connector; accepts an injected connection factory."""

    def __init__(self, connection_factory: Any):
        self.connection_factory = connection_factory

    def list_tables(self) -> list[str]:
        with self.connection_factory() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
            return sorted(str(row[0]) for row in cursor.fetchall())

    def read_table(self, table: str) -> list[dict[str, Any]]:
        if not table.replace("_", "").isalnum():
            raise ConnectorError("unsafe table identifier")
        with self.connection_factory() as connection:
            cursor = connection.cursor()
            cursor.execute(f"SELECT * FROM [{table}]")
            names = [column[0] for column in cursor.description]
            return [dict(zip(names, row)) for row in cursor.fetchall()]

    def fingerprint(self, table: str) -> dict[str, Any]:
        rows = self.read_table(table)
        return {"table": table, "rows": len(rows), "columns": sorted({key for row in rows for key in row})}


class SQLServerAdapter(DBConnector):
    """SQL Server adapter boundary; uses pyodbc only when installed by the caller."""

    @classmethod
    def from_connection_string(cls, connection_string: str) -> "SQLServerAdapter":
        def connect() -> Any:
            try:
                import pyodbc  # type: ignore
            except ImportError as exc:
                raise ConnectorError("install pyodbc to use SQLServerAdapter") from exc
            return pyodbc.connect(connection_string)
        return cls(connect)


class PostgresAdapter(DBConnector):
    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresAdapter":
        def connect() -> Any:
            try:
                import psycopg  # type: ignore
            except ImportError as exc:
                raise ConnectorError("install psycopg to use PostgresAdapter") from exc
            return psycopg.connect(dsn)
        return cls(connect)
