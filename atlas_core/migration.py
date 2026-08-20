"""Reference migration engine: deterministic, resumable, and evidence-first."""
from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from .contracts import Checkpoint, MappingProposal, MigrationConfig, MigrationPlan, MigrationState, QuarantineRecord
from .fingerprint import row_fingerprint, sha256_hex
from .state import AuditLedger, CheckpointStore
from .transform import TransformError, evaluate


class MigrationError(RuntimeError):
    pass


_TRANSITION_GRAPH: dict[MigrationState, set[MigrationState]] = {
    MigrationState.DRAFT: {MigrationState.VALIDATING, MigrationState.ABORTED},
    MigrationState.VALIDATING: {MigrationState.PLANNED, MigrationState.FAILED, MigrationState.APPROVAL_REQUIRED},
    MigrationState.PLANNED: {MigrationState.APPROVED, MigrationState.APPROVAL_REQUIRED, MigrationState.ABORTED},
    MigrationState.APPROVAL_REQUIRED: {MigrationState.APPROVED, MigrationState.ABORTED},
    MigrationState.APPROVED: {MigrationState.RUNNING, MigrationState.ABORTED},
    MigrationState.RUNNING: {MigrationState.PAUSED, MigrationState.RECONCILING, MigrationState.FAILED, MigrationState.ABORTED},
    MigrationState.PAUSED: {MigrationState.RECOVERING, MigrationState.ABORTED},
    MigrationState.RECOVERING: {MigrationState.RUNNING, MigrationState.FAILED},
    MigrationState.RECONCILING: {MigrationState.VERIFIED, MigrationState.FAILED, MigrationState.PAUSED},
    MigrationState.VERIFIED: {MigrationState.CUTOVER_READY, MigrationState.COMPLETE},
    MigrationState.CUTOVER_READY: {MigrationState.CUTOVER, MigrationState.ABORTED},
    MigrationState.CUTOVER: {MigrationState.COMPLETE, MigrationState.ROLLED_BACK, MigrationState.FAILED},
    MigrationState.COMPLETE: set(),
    MigrationState.ABORTED: set(),
    MigrationState.FAILED: {MigrationState.RECOVERING, MigrationState.ABORTED},
    MigrationState.ROLLED_BACK: set(),
}


class StateMachine:
    def __init__(self, migration_id: str, ledger: AuditLedger, actor: str = "atlas-engine"):
        self.migration_id = migration_id
        self.ledger = ledger
        self.actor = actor
        self.state = MigrationState.DRAFT

    def transition(self, new_state: MigrationState, reason: str, evidence: Any = None) -> MigrationState:
        if new_state not in _TRANSITION_GRAPH[self.state]:
            raise MigrationError(f"illegal migration transition {self.state} -> {new_state}")
        old_state = self.state
        self.state = new_state
        self.ledger.append(self.actor, "STATE_TRANSITION", self.migration_id, old_state.value, new_state.value, reason, evidence or {})
        return self.state


def build_plan(config: MigrationConfig, table_rows: Mapping[str, int], dependencies: list[tuple[str, str]] | None = None) -> MigrationPlan:
    dependencies = dependencies or []
    tables = list(table_rows)
    edges = tuple(dependencies)
    # Kahn's algorithm produces a deterministic topological order.
    incoming = {table: 0 for table in tables}
    outgoing: dict[str, list[str]] = {table: [] for table in tables}
    for left, right in edges:
        if left not in incoming or right not in incoming:
            raise MigrationError(f"unknown DAG node in dependency {left}->{right}")
        incoming[right] += 1
        outgoing[left].append(right)
    ready = sorted([table for table, count in incoming.items() if count == 0])
    order: list[str] = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for child in sorted(outgoing[current]):
            incoming[child] -= 1
            if incoming[child] == 0:
                ready.append(child)
                ready.sort()
    if len(order) != len(tables):
        raise MigrationError("migration dependency graph contains a cycle")
    estimated_rows = sum(table_rows.values())
    batches = sum((count + config.batch_size - 1) // config.batch_size for count in table_rows.values())
    estimated_seconds = estimated_rows / max(1, config.workers * 5000)
    return MigrationPlan(config.migration_id, tuple(order), edges, batches, config.workers, config.batch_size, estimated_rows, estimated_seconds, estimated_rows * 180, ("Estimate is a local model, not a performance guarantee.",))


class InMemoryTarget:
    """Idempotent reference target used by offline demos and tests."""

    def __init__(self):
        self.tables: dict[str, list[dict[str, Any]]] = {}

    def load(self, table: str, rows: list[dict[str, Any]], key: str) -> int:
        current = {str(row.get(key)): row for row in self.tables.get(table, [])}
        for row in rows:
            current[str(row.get(key))] = dict(row)
        self.tables[table] = list(current.values())
        return len(rows)

    def read(self, table: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self.tables.get(table, [])]


class MigrationEngine:
    def __init__(self, state_dir: str | Path):
        state_dir = Path(state_dir)
        state_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = AuditLedger(state_dir / "audit.jsonl")
        self.checkpoints = CheckpointStore(state_dir / "checkpoints.jsonl")
        self.quarantine = []
        self.target = InMemoryTarget()

    def migrate_table(
        self,
        config: MigrationConfig,
        table: str,
        source_rows: list[Mapping[str, Any]],
        key: str,
        transformations: Mapping[str, str] | None = None,
        fail_after_batches: int | None = None,
        worker: str = "worker-0",
    ) -> dict[str, Any]:
        transformations = transformations or {}
        machine = StateMachine(config.migration_id, self.ledger)
        machine.transition(MigrationState.VALIDATING, "validate source and mapping contract")
        machine.transition(MigrationState.PLANNED, "table plan accepted", {"table": table, "rows": len(source_rows)})
        machine.transition(MigrationState.APPROVED, "offline demo policy approval")
        machine.transition(MigrationState.RUNNING, "start table migration")
        previous = self.checkpoints.latest(config.migration_id, table)
        start_batch = int(previous["batch"]) + 1 if previous else 0
        loaded = 0
        failed = 0
        batches = [source_rows[index : index + config.batch_size] for index in range(0, len(source_rows), config.batch_size)]
        for batch_number, batch in enumerate(batches):
            if batch_number < start_batch:
                continue
            transformed: list[dict[str, Any]] = []
            for row in batch:
                try:
                    output = dict(row)
                    lineage: dict[str, Any] = {}
                    for target_field, expression in transformations.items():
                        result = evaluate(expression, row)
                        output[target_field] = result.value
                        lineage[target_field] = {"operation": result.operation, "inputs": result.inputs, "warnings": result.warnings}
                    output["_atlas_lineage"] = lineage
                    output["_atlas_source_fingerprint"] = row_fingerprint(row)
                    transformed.append(output)
                except (TransformError, TypeError, ValueError) as exc:
                    failed += 1
                    self.quarantine.append(
                        QuarantineRecord(str(uuid.uuid4()), dict(row), None, str(exc), "TRANSFORM", config.migration_id, batch_number, row_fingerprint(row))
                    )
            self.target.load(table, transformed, key)
            loaded += len(transformed)
            checkpoint = Checkpoint(config.migration_id, f"job-{table}", table, "default", batch_number, str(batch_number), batch_number, f"loaded={loaded}", sha256_hex(transformed), worker, "v1")
            self.checkpoints.put(checkpoint)
            if fail_after_batches is not None and batch_number + 1 >= fail_after_batches:
                machine.transition(MigrationState.PAUSED, "failure injection after committed checkpoint", {"batch": batch_number})
                return {"state": machine.state.value, "loaded": loaded, "failed": failed, "checkpoint": batch_number}
        machine.transition(MigrationState.RECONCILING, "all batches committed")
        machine.transition(MigrationState.VERIFIED, "table load completed; reconciliation delegated")
        machine.transition(MigrationState.COMPLETE, "offline migration complete")
        return {"state": machine.state.value, "loaded": loaded, "failed": failed, "checkpoint": len(batches) - 1}

    def resume_table(self, config: MigrationConfig, table: str, source_rows: list[Mapping[str, Any]], key: str, transformations: Mapping[str, str] | None = None) -> dict[str, Any]:
        return self.migrate_table(config, table, source_rows, key, transformations)
