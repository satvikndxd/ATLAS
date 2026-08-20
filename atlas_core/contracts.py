"""Canonical, serializable contracts shared by the ATLAS CLI and services.

The reference engine intentionally keeps the domain model dependency-free.  Every
important artifact is a dataclass so it can be persisted as JSON/JSONL and replayed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StrEnum(str, Enum):
    """Enum that serializes naturally to JSON."""

    def __str__(self) -> str:
        return self.value


class MappingStatus(StrEnum):
    PROPOSED = "PROPOSED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class MigrationState(StrEnum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    PLANNED = "PLANNED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVED = "APPROVED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    RECOVERING = "RECOVERING"
    RECONCILING = "RECONCILING"
    VERIFIED = "VERIFIED"
    CUTOVER_READY = "CUTOVER_READY"
    CUTOVER = "CUTOVER"
    COMPLETE = "COMPLETE"
    ABORTED = "ABORTED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Operation(StrEnum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass(frozen=True)
class Evidence:
    kind: str
    detail: str
    value: float | str | int | None = None


@dataclass(frozen=True)
class ColumnProfile:
    name: str
    data_type: str
    nullable: bool
    row_count: int
    null_count: int
    distinct_count: int
    min_value: Any = None
    max_value: Any = None
    top_values: tuple[tuple[str, int], ...] = ()
    likely_pii: bool = False
    likely_identifier: bool = False

    @property
    def null_fraction(self) -> float:
        return self.null_count / self.row_count if self.row_count else 0.0


@dataclass(frozen=True)
class SchemaFingerprint:
    source_id: str
    schema_version: str
    tables: Mapping[str, Mapping[str, Any]]
    relationships: tuple[Mapping[str, Any], ...] = ()
    fingerprint: str = ""
    created_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class InferredRelationship:
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    confidence: float
    evidence: tuple[Evidence, ...]
    status: str = "PROPOSED"


@dataclass(frozen=True)
class MappingProposal:
    mapping_id: str
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    transformation: str
    confidence: float
    evidence: tuple[Evidence, ...]
    validation: tuple[str, ...] = ()
    author: str = "atlas-deterministic-engine"
    approval: str | None = None
    version: int = 1
    timestamp: str = field(default_factory=utc_now)
    status: MappingStatus = MappingStatus.PROPOSED


@dataclass(frozen=True)
class Checkpoint:
    migration_id: str
    job_id: str
    table: str
    partition: str
    batch: int
    source_position: str
    cdc_offset: int
    target_state: str
    checksum: str
    worker: str
    migration_version: str
    timestamp: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class CDCEvent:
    event_id: str
    source_position: str
    table: str
    primary_key: str
    operation: Operation
    before: Mapping[str, Any] | None
    after: Mapping[str, Any] | None
    timestamp: str
    schema_version: str
    sequence: int


@dataclass(frozen=True)
class QuarantineRecord:
    quarantine_id: str
    original_record: Mapping[str, Any]
    transformed_record: Mapping[str, Any] | None
    failure_reason: str
    stage: str
    migration_id: str
    batch: int
    checksum: str
    timestamp: str = field(default_factory=utc_now)
    remediation_status: str = "OPEN"


@dataclass(frozen=True)
class ReconciliationReport:
    migration_id: str
    table: str
    passed: bool
    source_count: int
    target_count: int
    aggregate_deltas: Mapping[str, float]
    source_hash: str
    target_hash: str
    missing_keys: tuple[str, ...]
    unexpected_keys: tuple[str, ...]
    duplicate_keys: tuple[str, ...]
    referential_errors: tuple[str, ...]
    invariant_errors: tuple[str, ...]
    distribution_deltas: Mapping[str, float]
    sampled_mismatches: tuple[str, ...]
    earliest_divergence: str | None = None
    evidence: tuple[Evidence, ...] = ()
    created_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class MigrationConfig:
    migration_id: str
    source: str
    target: str
    workers: int = 1
    batch_size: int = 100
    checkpoint_interval: int = 1
    max_reconciliation_delta: float = 0.0
    pii_logging: bool = False
    auto_remediation: str = "limited"
    seed: int = 42


@dataclass(frozen=True)
class MigrationPlan:
    migration_id: str
    nodes: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]
    batches: int
    worker_count: int
    batch_size: int
    estimated_rows: int
    estimated_seconds: float
    estimated_bytes: int
    resource_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class AuditEntry:
    event_id: str
    actor: str
    action: str
    migration_id: str
    old_state: str | None
    new_state: str | None
    reason: str
    evidence_hash: str
    previous_hash: str
    entry_hash: str
    timestamp: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class RiskAssessment:
    level: RiskLevel
    score: float
    factors: Mapping[str, float]
    reasons: tuple[str, ...]
    approval_required: bool


@dataclass(frozen=True)
class CutoverReport:
    migration_id: str
    phases: tuple[str, ...]
    completed: bool
    verified: bool
    blocked_reason: str | None
    evidence: tuple[Evidence, ...]
    created_at: str = field(default_factory=utc_now)


def to_dict(value: Any) -> Any:
    """Convert nested dataclasses/enums/tuples into JSON-compatible values."""
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: to_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): to_dict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_dict(item) for item in value]
    return value
