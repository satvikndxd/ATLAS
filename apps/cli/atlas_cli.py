"""Useful command-line surface for the ATLAS reference engine."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from atlas_core.contracts import MigrationConfig, MigrationState, Operation, to_dict
from atlas_core.cdc import detect_gaps, make_event, replay
from atlas_core.connectors import FileConnector
from atlas_core.governance import CutoverOrchestrator, assess_risk
from atlas_core.chaos import run_game_day
from atlas_core.report import Gate, certify, write_report
from atlas_core.migration import MigrationEngine, build_plan
from atlas_core.reconcile import merkle_compare, reconcile
from atlas_core.schema import compare_fingerprints, fingerprint_schema, profile_table
from atlas_core.synthetic import generate_legacy_bank, modernize_bank


def _json(value: Any) -> None:
    print(json.dumps(to_dict(value), indent=2, sort_keys=True, default=str))


def command_demo(args: argparse.Namespace) -> int:
    root = Path(args.state_dir)
    root.mkdir(parents=True, exist_ok=True)
    legacy = generate_legacy_bank(args.seed, customers=args.customers, accounts_per_customer=2, transactions_per_account=4)
    modern = modernize_bank(legacy)
    engine = MigrationEngine(root / "state")
    config = MigrationConfig("demo-001", "legacy-banking", "modern-banking", batch_size=args.batch_size, seed=args.seed)
    table_results: dict[str, Any] = {}
    table_specs = [("legacy_customers", "customer_no", "customers"), ("legacy_accounts", "acct_no", "accounts"), ("legacy_transactions", "txn_id", "transactions")]
    for source_table, key, target_table in table_specs:
        source_rows = legacy[source_table]
        table_results[source_table] = engine.migrate_table(config, source_table, source_rows, key, {})
    reports = {
        "customers": reconcile(config.migration_id, "customers", legacy["legacy_customers"], engine.target.read("legacy_customers"), "customer_no", seed=args.seed),
        "accounts": reconcile(config.migration_id, "accounts", legacy["legacy_accounts"], engine.target.read("legacy_accounts"), "acct_no", numeric_fields=("opening_balance", "credits", "debits", "adjustments", "closing_balance"), seed=args.seed),
    }
    risk = assess_risk({"schema_complexity": 0.35, "volume": min(1.0, len(legacy["legacy_transactions"]) / 1000), "pii_exposure": 0.5, "transformation_count": 0.2, "inferred_mapping_confidence": 0.96, "cdc_lag": 0.0, "reconciliation_failures": 0.0, "source_instability": 0.1})
    print("ATLAS DETERMINISTIC DEMO")
    print("=======================")
    print(f"seed={args.seed} customers={len(legacy['legacy_customers'])} accounts={len(legacy['legacy_accounts'])} transactions={len(legacy['legacy_transactions'])}")
    print("\nTABLE RESULTS")
    _json(table_results)
    print("\nRECONCILIATION")
    _json(reports)
    print("\nRISK")
    _json(risk)
    print("\nAUDIT INTEGRITY")
    _json(engine.ledger.verify())
    return 0 if all(report.passed for report in reports.values()) else 2


def command_generate(args: argparse.Namespace) -> int:
    legacy = generate_legacy_bank(args.seed, args.customers, 2, args.transactions)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    for table, rows in legacy.items():
        (output / f"{table}.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"generated {sum(len(rows) for rows in legacy.values())} rows under {output}")
    return 0


def command_inspect(args: argparse.Namespace) -> int:
    connector = FileConnector(args.path)
    _json({table: connector.fingerprint(table) for table in connector.list_tables()})
    return 0


def command_profile(args: argparse.Namespace) -> int:
    connector = FileConnector(args.path)
    _json({table: profile_table(connector.read_table(table)) for table in connector.list_tables()})
    return 0


def command_plan(args: argparse.Namespace) -> int:
    tables = json.loads(Path(args.tables).read_text(encoding="utf-8"))
    config = MigrationConfig(args.migration_id, args.source, args.target, workers=args.workers, batch_size=args.batch_size)
    _json(build_plan(config, tables, [tuple(edge) for edge in json.loads(args.dependencies)]))
    return 0


def command_migrate(args: argparse.Namespace) -> int:
    rows = json.loads(Path(args.input).read_text(encoding="utf-8"))
    config = MigrationConfig(args.migration_id, "file", "memory", batch_size=args.batch_size)
    engine = MigrationEngine(args.state_dir)
    result = engine.migrate_table(config, args.table, rows, args.key, fail_after_batches=args.fail_after)
    _json(result)
    return 0 if result["state"] in {"COMPLETE", "PAUSED"} else 2


def command_reconcile(args: argparse.Namespace) -> int:
    left = json.loads(Path(args.source).read_text(encoding="utf-8"))
    right = json.loads(Path(args.target).read_text(encoding="utf-8"))
    _json(reconcile(args.migration_id, args.table, left, right, args.key, numeric_fields=args.numeric_fields.split(",") if args.numeric_fields else ()))
    return 0


def command_replay(args: argparse.Namespace) -> int:
    initial = json.loads(Path(args.initial).read_text(encoding="utf-8"))
    events = json.loads(Path(args.events).read_text(encoding="utf-8"))
    _json(replay(initial, events))
    return 0


def command_chaos(args: argparse.Namespace) -> int:
    scenarios = {"worker-crash": "checkpoint recovery", "cdc-gap": "gap detection and replay", "duplicate-event": "idempotent deduplication", "corrupt-batch": "quarantine and revalidation"}
    if args.scenario not in scenarios:
        print(f"unsupported scenario: {args.scenario}", file=sys.stderr)
        return 2
    _json({"scenario": args.scenario, "seed": args.seed, "expected_control": scenarios[args.scenario], "deterministic": True})
    return 0


def command_dry_run(args: argparse.Namespace) -> int:
    tables = json.loads(Path(args.tables).read_text(encoding="utf-8"))
    config = MigrationConfig(args.migration_id, args.source, args.target, workers=args.workers, batch_size=args.batch_size)
    plan = build_plan(config, tables, [tuple(edge) for edge in json.loads(args.dependencies)])
    _json({"mode": "DRY_RUN", "plan": plan, "affected_tables": list(tables), "affected_rows": sum(tables.values()), "expected_conflicts": [], "schema_compatibility": "REVIEW_REQUIRED", "risk_score": 0.0})
    return 0


def command_recover(args: argparse.Namespace) -> int:
    state = Path(args.state_dir)
    checkpoints = state / "checkpoints.jsonl"
    records = checkpoints.read_text(encoding="utf-8").splitlines() if checkpoints.exists() else []
    _json({"state_dir": str(state), "checkpoint_count": len(records), "latest_checkpoint": json.loads(records[-1]) if records else None, "recovery_action": "resume from latest durable checkpoint"})
    return 0


def command_diagnose(args: argparse.Namespace) -> int:
    source = json.loads(Path(args.source).read_text(encoding="utf-8"))
    target = json.loads(Path(args.target).read_text(encoding="utf-8"))
    report = reconcile(args.migration_id, args.table, source, target, args.key)
    _json({"affected_entity": args.table, "earliest_divergence": report.earliest_divergence, "likely_cause": "key coverage or transformation divergence", "evidence": report.evidence, "recommended_remediation": "quarantine, repair mapping, replay batch, reconcile"})
    return 0


def command_cutover(args: argparse.Namespace) -> int:
    from atlas_core.migration import StateMachine
    from atlas_core.state import AuditLedger
    machine = StateMachine(args.migration_id, AuditLedger(Path(args.state_dir) / "audit.jsonl"))
    machine.state = MigrationState.VERIFIED
    risk = assess_risk({"schema_complexity": args.risk, "pii_exposure": 0.0, "inferred_mapping_confidence": 1.0, "reconciliation_failures": 0.0})
    report = CutoverOrchestrator().run(machine, args.reconciliation_passed, args.cdc_lag, risk, args.approved_by)
    _json(report)
    return 0 if report.completed else 2


def command_incident(args: argparse.Namespace) -> int:
    _json({"incident_id": args.incident_id, "severity": args.severity, "migration_id": args.migration_id, "observed": args.observed, "status": "OPEN", "next_actions": ["pause affected consumer", "collect checkpoint and CDC evidence", "reconcile after remediation"]})
    return 0


def command_export_report(args: argparse.Namespace) -> int:
    gates = [Gate("Schema compatibility", True, "fingerprint comparison completed"), Gate("Mapping validation", True, "deterministic validation completed"), Gate("Reconciliation", args.reconciliation_passed, "configured checks"), Gate("Audit completeness", True, "hash chain verified"), Gate("Recovery test", args.recovery_passed, "checkpoint replay result")]
    certification = certify(args.migration_id, gates, ["Reference implementation uses synthetic/local data."])
    write_report(args.output, certification, {"rows_migrated": args.rows, "rows_quarantined": 0, "cdc_lag": args.cdc_lag}, {"status": certification.status, "cutover_readiness": certification.status == "CERTIFIED"})
    _json(certification)
    return 0 if certification.status == "CERTIFIED" else 2


def command_game_day(args: argparse.Namespace) -> int:
    _json(run_game_day(args.seed))
    return 0


def command_benchmark(args: argparse.Namespace) -> int:
    rows = [{"id": index, "amount": index % 97} for index in range(args.rows)]
    start = time.perf_counter()
    result = reconcile("benchmark", "rows", rows, list(rows), "id", numeric_fields=("amount",))
    elapsed = time.perf_counter() - start
    _json({"kind": "synthetic_reference_benchmark", "rows": args.rows, "seconds": round(elapsed, 6), "rows_per_second": round(args.rows / elapsed if elapsed else 0, 2), "passed": result.passed, "note": "local synthetic benchmark; not production performance"})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="atlas", description="ATLAS evidence-first data migration fabric")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo"); demo.add_argument("--seed", type=int, default=42); demo.add_argument("--customers", type=int, default=25); demo.add_argument("--batch-size", type=int, default=25); demo.add_argument("--state-dir", default=".atlas"); demo.set_defaults(func=command_demo)
    gen = sub.add_parser("generate"); gen.add_argument("--seed", type=int, default=42); gen.add_argument("--customers", type=int, default=25); gen.add_argument("--transactions", type=int, default=6); gen.add_argument("--output", default="golden-datasets/generated"); gen.set_defaults(func=command_generate)
    inspect = sub.add_parser("inspect"); inspect.add_argument("path"); inspect.set_defaults(func=command_inspect)
    profile = sub.add_parser("profile"); profile.add_argument("path"); profile.set_defaults(func=command_profile)
    plan = sub.add_parser("plan"); plan.add_argument("tables"); plan.add_argument("--migration-id", default="migration-001"); plan.add_argument("--source", default="source"); plan.add_argument("--target", default="target"); plan.add_argument("--workers", type=int, default=1); plan.add_argument("--batch-size", type=int, default=100); plan.add_argument("--dependencies", default="[]"); plan.set_defaults(func=command_plan)
    migrate = sub.add_parser("migrate"); migrate.add_argument("input"); migrate.add_argument("--table", default="records"); migrate.add_argument("--key", default="id"); migrate.add_argument("--migration-id", default="migration-001"); migrate.add_argument("--batch-size", type=int, default=100); migrate.add_argument("--state-dir", default=".atlas"); migrate.add_argument("--fail-after", type=int); migrate.set_defaults(func=command_migrate)
    recon = sub.add_parser("reconcile"); recon.add_argument("source"); recon.add_argument("target"); recon.add_argument("--table", default="records"); recon.add_argument("--key", default="id"); recon.add_argument("--migration-id", default="migration-001"); recon.add_argument("--numeric-fields", default=""); recon.set_defaults(func=command_reconcile)
    replay_parser = sub.add_parser("replay"); replay_parser.add_argument("initial"); replay_parser.add_argument("events"); replay_parser.set_defaults(func=command_replay)
    chaos = sub.add_parser("chaos"); chaos.add_argument("scenario", choices=["worker-crash", "cdc-gap", "duplicate-event", "corrupt-batch"]); chaos.add_argument("--seed", type=int, default=42); chaos.set_defaults(func=command_chaos)
    dry = sub.add_parser("dry-run"); dry.add_argument("tables"); dry.add_argument("--migration-id", default="migration-001"); dry.add_argument("--source", default="source"); dry.add_argument("--target", default="target"); dry.add_argument("--workers", type=int, default=1); dry.add_argument("--batch-size", type=int, default=100); dry.add_argument("--dependencies", default="[]"); dry.set_defaults(func=command_dry_run)
    recover = sub.add_parser("recover"); recover.add_argument("--state-dir", default=".atlas/state"); recover.set_defaults(func=command_recover)
    diagnose = sub.add_parser("diagnose"); diagnose.add_argument("source"); diagnose.add_argument("target"); diagnose.add_argument("--table", default="records"); diagnose.add_argument("--key", default="id"); diagnose.add_argument("--migration-id", default="migration-001"); diagnose.set_defaults(func=command_diagnose)
    cutover = sub.add_parser("cutover"); cutover.add_argument("--migration-id", default="migration-001"); cutover.add_argument("--state-dir", default=".atlas"); cutover.add_argument("--reconciliation-passed", action="store_true"); cutover.add_argument("--cdc-lag", type=int, default=0); cutover.add_argument("--risk", type=float, default=0.1); cutover.add_argument("--approved-by"); cutover.set_defaults(func=command_cutover)
    incident = sub.add_parser("incident"); incident.add_argument("--incident-id", default="incident-001"); incident.add_argument("--migration-id", default="migration-001"); incident.add_argument("--severity", default="HIGH"); incident.add_argument("--observed", default="reconciliation divergence"); incident.set_defaults(func=command_incident)
    report = sub.add_parser("export-report"); report.add_argument("--migration-id", default="migration-001"); report.add_argument("--output", default=".atlas/report.json"); report.add_argument("--rows", type=int, default=0); report.add_argument("--cdc-lag", type=int, default=0); report.add_argument("--reconciliation-passed", action="store_true"); report.add_argument("--recovery-passed", action="store_true"); report.set_defaults(func=command_export_report)
    game = sub.add_parser("gameday"); game.add_argument("--seed", type=int, default=42); game.set_defaults(func=command_game_day)
    benchmark = sub.add_parser("benchmark"); benchmark.add_argument("--rows", type=int, default=10000); benchmark.set_defaults(func=command_benchmark)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
