from __future__ import annotations

import json
from pathlib import Path

from atlas_core.api_contracts import migration_payload, policy_payload, reconciliation_payload


ROOT = Path(__file__).parents[1]


def test_v1_domain_schema_is_parseable_and_declares_core_definitions() -> None:
    schema = json.loads((ROOT / "contracts/v1/domain.schema.json").read_text(encoding="utf-8"))
    assert schema["$schema"].endswith("2020-12/schema")
    assert {"Migration", "MigrationJob", "Checkpoint", "CDCEvent", "Reconciliation", "Approval", "PolicyDecision"} <= set(schema["definitions"])


def test_python_api_payloads_use_versioned_wire_contract() -> None:
    migration = migration_payload("m-1", "legacy", "modern", "DRAFT")
    policy = policy_payload("decision-1", "policy-v1", False, ["reconciliation_failed"])
    reconciliation = reconciliation_payload("rec-1", "m-1", "accounts", "FAILED", source_count=2, target_count=1)
    assert migration["schema_version"] == policy["schema_version"] == reconciliation["schema_version"] == "1.0"
    assert migration["type"] == "Migration"
    assert policy["reasons"] == ["reconciliation_failed"]
    assert reconciliation["target_count"] == 1
