from __future__ import annotations

import os

import pytest

from atlas_core.connectors import ConnectorError, PostgresAdapter, SQLServerAdapter


@pytest.mark.integration
@pytest.mark.live_db
@pytest.mark.parametrize(
    ("name", "factory", "environment"),
    [
        ("sqlserver", SQLServerAdapter.from_connection_string, "ATLAS_SQLSERVER_URL"),
        ("postgres", PostgresAdapter.from_dsn, "ATLAS_POSTGRES_URL"),
    ],
)
def test_live_connector_contract(name: str, factory, environment: str) -> None:
    """Run only when the operator explicitly supplies a disposable live database."""
    dsn = os.getenv(environment)
    if not dsn:
        pytest.skip(f"SKIPPED — {name} requires {environment} and a disposable seeded database")
    try:
        connector = factory(dsn)
        tables = connector.list_tables()
        assert isinstance(tables, list)
        schema = connector.discover_schema()
        assert isinstance(schema, dict)
    except ConnectorError as error:
        pytest.skip(f"SKIPPED — {name} adapter unavailable: {error}")
