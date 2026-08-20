from __future__ import annotations

from pathlib import Path

from atlas_core.connectors import FileConnector, InMemoryConnector


def assert_connector_contract(connector, table: str) -> None:
    assert connector.list_tables() == [table]
    schema = connector.discover_schema()
    assert table in schema
    rows = connector.read_rows(table)
    assert rows
    tx = connector.begin_transaction()
    connector.write_rows(table, [{"id": "2", "value": "new"}], "id")
    assert connector.read_rows(table)[-1]["id"] == "2"
    connector.rollback()
    assert not any(row["id"] == "2" for row in connector.read_rows(table))
    connector.begin_transaction()
    connector.write_rows(table, [{"id": "2", "value": "committed"}], "id")
    connector.commit()
    assert any(row["id"] == "2" for row in connector.read_rows(table))
    report = connector.reconcile("migration-contract", table, [{"id": "1", "value": "one"}, {"id": "2", "value": "committed"}], "id")
    assert report.passed


def test_in_memory_connector_contract() -> None:
    assert_connector_contract(InMemoryConnector({"records": [{"id": "1", "value": "one"}]}), "records")


def test_file_connector_schema_and_reads(tmp_path: Path) -> None:
    (tmp_path / "records.json").write_text('[{"id": "1", "value": "one"}]', encoding="utf-8")
    connector = FileConnector(tmp_path)
    assert connector.list_tables() == ["records"]
    assert connector.read_rows("records")[0]["id"] == "1"
    assert connector.discover_schema()["records"]["rows"] == 1
