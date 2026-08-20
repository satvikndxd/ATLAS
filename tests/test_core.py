from __future__ import annotations

from pathlib import Path

import pytest

from atlas_core.cdc import detect_gaps, make_event, replay
from atlas_core.chaos import inject, run_game_day
from atlas_core.archaeology import archaeologize
from atlas_core.assumptions import Assumption, AssumptionLedger, AssumptionStatus
from atlas_core.counterfactual import counterfactual_remove_transaction, reconstruct_state
from atlas_core.epistemic import EvidenceLedger, EvidenceRecord, EpistemicStatus
from atlas_core.genome import DataGenome, genome_distance
from atlas_core.ir import IRMapping, compile_ir, diff_ir
from atlas_core.semantic import compare_rows, semantic_merkle_root
from atlas_core.contracts import MigrationConfig, MigrationState, Operation
from atlas_core.fingerprint import merkle_root, row_fingerprint
from atlas_core.governance import RBAC, assess_risk, policy_gate
from atlas_core.migration import MigrationEngine, MigrationError, build_plan
from atlas_core.mapping import MappingRegistry, propose_mappings
from atlas_core.reconcile import merkle_compare, reconcile
from atlas_core.schema import compare_fingerprints, fingerprint_schema, infer_relationships, profile_table
from atlas_core.synthetic import generate_legacy_bank, modernize_bank
from atlas_core.transform import TransformError, evaluate


def test_transformations_are_deterministic():
    row = {"name": "  alice  ", "balance": "12.3456", "dob": "31/12/2020"}
    assert evaluate("TRIM(source.name)", row).value == "alice"
    assert evaluate("DECIMAL(source.balance, scale=2)", row).value == "12.35"
    assert evaluate('PARSE_DATE(source.dob, "DD/MM/YYYY")', row).value == "2020-12-31"


def test_bad_date_is_quarantinable():
    with pytest.raises(TransformError):
        evaluate('PARSE_DATE(source.dob, "DD/MM/YYYY")', {"dob": "31/02/2020"})


def test_schema_profile_and_relationships():
    tables = {"customers": [{"customer_id": "C1", "name": "A"}], "accounts": [{"account_id": "A1", "customer_id": "C1"}]}
    profile = profile_table(tables["customers"])
    assert profile[0].distinct_count == 1
    relationships = infer_relationships(tables)
    assert relationships
    assert fingerprint_schema("source", tables).fingerprint


def test_schema_drift_classification():
    before = fingerprint_schema("source", {"t": [{"id": 1, "amount": 2}]})
    after = fingerprint_schema("source", {"t": [{"id": "1", "amount": 2}]})
    assert any(change["kind"] == "DATATYPE_CHANGED" for change in compare_fingerprints(before, after))


def test_reconciliation_pass_and_failure():
    source = [{"id": "1", "amount": 10}, {"id": "2", "amount": 20}]
    assert reconcile("m", "t", source, list(source), "id", numeric_fields=("amount",)).passed
    failed = reconcile("m", "t", source, [{"id": "1", "amount": 10}], "id", numeric_fields=("amount",))
    assert not failed.passed and failed.missing_keys == ("2",)


def test_merkle_localizes_partition():
    source = [{"id": i, "value": i} for i in range(20)]
    target = list(source)
    target[7] = {"id": 7, "value": 999}
    result = merkle_compare(source, target, "id", partitions=8)
    assert result["source_root"] != result["target_root"]
    assert result["differing_partitions"]


def test_cdc_replay_is_idempotent_and_detects_gaps():
    events = [make_event("t", "1", Operation.INSERT, None, {"id": "1", "v": 1}, 0), make_event("t", "1", Operation.UPDATE, {"id": "1", "v": 1}, {"id": "1", "v": 2}, 2)]
    assert detect_gaps(events) == [(1, 1)]
    final = replay({}, events + [events[1]])
    assert final == {"1": {"id": "1", "v": 2}}


def test_checkpoint_resume_without_duplicate_rows(tmp_path: Path):
    engine = MigrationEngine(tmp_path)
    config = MigrationConfig("m1", "s", "t", batch_size=2)
    rows = [{"id": str(index), "value": index} for index in range(5)]
    first = engine.migrate_table(config, "rows", rows, "id", fail_after_batches=1)
    assert first["state"] == "PAUSED"
    resumed = engine.resume_table(config, "rows", rows, "id")
    assert resumed["state"] == "COMPLETE"
    assert len(engine.target.read("rows")) == 5


def test_illegal_state_transition(tmp_path: Path):
    engine = MigrationEngine(tmp_path)
    from atlas_core.migration import StateMachine
    machine = StateMachine("m", engine.ledger)
    with pytest.raises(MigrationError):
        machine.transition(MigrationState.COMPLETE, "skip gates")


def test_plan_is_topological():
    config = MigrationConfig("m", "s", "t")
    plan = build_plan(config, {"customers": 1, "accounts": 2, "transactions": 3}, [("customers", "accounts"), ("accounts", "transactions")])
    assert plan.nodes == ("customers", "accounts", "transactions")


def test_policy_and_rbac():
    risk = assess_risk({"pii_exposure": 0.9, "inferred_mapping_confidence": 0.4})
    allowed, reasons = policy_gate(risk, False, 2)
    assert not allowed and reasons
    assert RBAC.authorize("READ_ONLY", "inspect")
    assert not RBAC.authorize("READ_ONLY", "migrate")


def test_mapping_registry_requires_explicit_approval():
    proposals = propose_mappings([{"name": "acct_bal", "data_type": "number"}], [{"name": "balance", "data_type": "number"}], "legacy", "modern")
    registry = MappingRegistry()
    registry.add(proposals[0])
    approved = registry.approve(proposals[0].mapping_id, "approver-1")
    assert approved.approval == "approver-1"
    assert len(registry.history(proposals[0].mapping_id)) == 2


def test_seeded_chaos_is_reproducible():
    assert inject("change_schema", "m", 42) == inject("change_schema", "m", 42)
    assert run_game_day(42) == run_game_day(42)


def test_genome_distance_is_explainable():
    left = DataGenome("left", "v1", {"accounts": {"columns": ["id", "balance"]}}, (), (), {"event_time": "present"}, {"accounts": 0.1}, {"balance": {"mean": 10}}, {}, (), {"balance": "money"}, ({"name": "account_conservation"},), (), (), {}, {"accounts": ("transactions",)}, {"semantic": 0.1})
    right = DataGenome("right", "v1", {"accounts": {"columns": ["id", "balance"]}, "transactions": {"columns": ["id"]}}, (), (), {"event_time": "present"}, {"accounts": 0.2}, {"balance": {"mean": 10}}, {}, (), {"balance": "money"}, ({"name": "account_conservation"},), (), (), {}, {"accounts": ("transactions",)}, {"semantic": 0.1})
    distance = genome_distance(left, right)
    assert distance["entity"].value > 0
    assert distance["invariant"].value == 0


def test_archaeology_labels_findings_without_promoting_truth():
    report = archaeologize("source", {"accounts": [{"account_id": "A1", "balance": "10.00", "status": "CLOSED", "closed_at": "2026-01-01"}]})
    assert report.by_category("identifier")
    assert all(item.status.value in {"KNOWN", "LIKELY", "INFERRED", "OBSERVED"} for item in report.findings)


def test_evidence_decay_and_conflict():
    ledger = EvidenceLedger()
    record = EvidenceRecord("e1", "account.status", "closed means inactive", "fixture", EpistemicStatus.OBSERVED, 0.9, created_at="2020-01-01T00:00:00+00:00")
    ledger.add(record)
    assert ledger.refresh(at="2020-02-01T00:00:00+00:00")[0].decayed_confidence(at="2020-02-01T00:00:00+00:00") < 0.9
    conflict = ledger.conflict("c1", "account.status", ["e1"])
    assert conflict.unresolved and ledger.get("e1").status == EpistemicStatus.CONTRADICTED


def test_assumption_invalidation_identifies_dependents():
    ledger = AssumptionLedger()
    ledger.add(Assumption("a1", "timestamps are UTC", (), 0.9, AssumptionStatus.INFERRED, "2026-01-01T00:00:00+00:00", dependent_results=("mapping-v1",)))
    _, dependents = ledger.invalidate("a1", "2026-01-02T00:00:00+00:00", "offset evidence contradicted assumption")
    assert dependents == ("mapping-v1",)


def test_semantic_equivalence_separates_bytes_from_meaning():
    result = compare_rows({"event_time": "2026-08-21 10:00:00"}, {"event_time": "2026-08-21T10:00:00Z"})
    assert not result["byte_equivalent"]
    assert result["semantic_equivalent"]
    assert semantic_merkle_root([{"value": "10.0"}]) == semantic_merkle_root([{"value": 10}])


def test_ir_is_diffable_and_counterfactual_is_labeled():
    left = compile_ir("s1", "t1", [IRMapping("accounts", "balance", "accounts", "balance", "IDENTITY(source.balance)")])
    right = compile_ir("s1", "t1", [IRMapping("accounts", "balance", "accounts", "balance", "DECIMAL(source.balance, scale=2)")])
    assert diff_ir(left, right)["mapping_changes"]
    counterfactual = counterfactual_remove_transaction({"T1": {"account_id": "A1", "amount": 10}}, "T1")
    assert counterfactual.status == EpistemicStatus.COUNTERFACTUAL
    reconstruction = reconstruct_state("A1", [{"balance": 100}], later_state={"balance": 110})
    assert reconstruction.status == EpistemicStatus.RECONSTRUCTED and reconstruction.confidence > 0


def test_synthetic_bank_contains_controlled_defects():
    legacy = generate_legacy_bank(42, customers=20, accounts_per_customer=1, transactions_per_account=2)
    modern = modernize_bank(legacy)
    assert len(legacy["legacy_customers"]) >= 20
    assert len(modern["customers"]) == len(legacy["legacy_customers"])
    assert any(row["acct_ref"] == "A-MISSING" for row in legacy["legacy_transactions"])
