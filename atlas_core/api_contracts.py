"""Canonical v1 API payload mappings.

Python remains the reference semantics; these functions define the stable boundary
consumed by the .NET control plane and React console.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Mapping

SCHEMA_VERSION = "1.0"


def _json(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _json(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(item) for item in value]
    return value


def versioned(kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    result = {"schema_version": SCHEMA_VERSION, "type": kind, **_json(payload)}
    return result


def migration_payload(migration_id: str, source: str, target: str, state: str, plan_version: str = "plan-v1", progress: float = 0.0, created_at: str | None = None, updated_at: str | None = None) -> dict[str, Any]:
    from .contracts import utc_now
    created = created_at or utc_now()
    return versioned("Migration", {"migration_id": migration_id, "source": source, "target": target, "state": state, "plan_version": plan_version, "progress": progress, "created_at": created, "updated_at": updated_at or created})


def job_payload(job_id: str, migration_id: str, state: str, attempt: int = 0, table: str | None = None, partition: str | None = None, worker_id: str | None = None, lease_id: str | None = None, lease_expiry: str | None = None, progress: float = 0.0) -> dict[str, Any]:
    return versioned("MigrationJob", {"job_id": job_id, "migration_id": migration_id, "table": table, "partition": partition, "state": state, "worker_id": worker_id, "lease_id": lease_id, "lease_expiry": lease_expiry, "attempt": attempt, "progress": progress})


def reconciliation_payload(reconciliation_id: str, migration_id: str, table: str, status: str, source_count: int = 0, target_count: int = 0, byte_equivalent: bool | None = None, semantic_equivalent: bool | None = None, missing_keys: list[str] | None = None, unexpected_keys: list[str] | None = None, invariant_errors: list[str] | None = None, created_at: str | None = None) -> dict[str, Any]:
    from .contracts import utc_now
    return versioned("Reconciliation", {"reconciliation_id": reconciliation_id, "migration_id": migration_id, "table": table, "status": status, "byte_equivalent": byte_equivalent, "semantic_equivalent": semantic_equivalent, "source_count": source_count, "target_count": target_count, "missing_keys": missing_keys or [], "unexpected_keys": unexpected_keys or [], "invariant_errors": invariant_errors or [], "created_at": created_at or utc_now()})


def policy_payload(decision_id: str, policy_version: str, allowed: bool, reasons: list[str], evaluated_at: str | None = None) -> dict[str, Any]:
    from .contracts import utc_now
    return versioned("PolicyDecision", {"decision_id": decision_id, "policy_version": policy_version, "allowed": allowed, "reasons": reasons, "evaluated_at": evaluated_at or utc_now()})
