"""Epistemic primitives: ATLAS never collapses observation into truth."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable


class EpistemicStatus(str, Enum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    INFERRED = "INFERRED"
    RECONSTRUCTED = "RECONSTRUCTED"
    PREDICTED = "PREDICTED"
    SIMULATED = "SIMULATED"
    COUNTERFACTUAL = "COUNTERFACTUAL"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


class FindingStatus(str, Enum):
    KNOWN = "KNOWN"
    LIKELY = "LIKELY"
    INFERRED = "INFERRED"
    OBSERVED = "OBSERVED"
    UNKNOWN = "UNKNOWN"
    CONTRADICTED = "CONTRADICTED"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    subject: str
    claim: str
    source: str
    status: EpistemicStatus
    confidence: float
    created_at: str = ""
    last_verified_at: str | None = None
    contradicted_at: str | None = None
    superseded_at: str | None = None
    detail: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within [0, 1]")
        if not self.created_at:
            object.__setattr__(self, "created_at", now_iso())

    def age_days(self, at: str | None = None) -> float:
        reference = _parse(at) if at else datetime.now(timezone.utc)
        return max(0.0, (reference - _parse(self.last_verified_at or self.created_at)).total_seconds() / 86400)

    def decayed_confidence(self, half_life_days: float = 30.0, at: str | None = None) -> float:
        if half_life_days <= 0:
            return 0.0
        return self.confidence * (0.5 ** (self.age_days(at) / half_life_days))

    def verify(self, verified_at: str | None = None, confidence: float | None = None) -> "EvidenceRecord":
        return replace(self, last_verified_at=verified_at or now_iso(), confidence=self.confidence if confidence is None else confidence)

    def contradict(self, at: str | None = None) -> "EvidenceRecord":
        return replace(self, status=EpistemicStatus.CONTRADICTED, contradicted_at=at or now_iso())

    def supersede(self, at: str | None = None) -> "EvidenceRecord":
        return replace(self, superseded_at=at or now_iso())


@dataclass(frozen=True)
class EvidenceConflict:
    conflict_id: str
    subject: str
    claims: tuple[EvidenceRecord, ...]
    unresolved: bool
    likely_resolution: str | None = None


class EvidenceLedger:
    def __init__(self):
        self._records: dict[str, EvidenceRecord] = {}
        self._conflicts: list[EvidenceConflict] = []

    def add(self, record: EvidenceRecord) -> EvidenceRecord:
        self._records[record.evidence_id] = record
        return record

    def get(self, evidence_id: str) -> EvidenceRecord | None:
        return self._records.get(evidence_id)

    def subject(self, subject: str) -> tuple[EvidenceRecord, ...]:
        return tuple(record for record in self._records.values() if record.subject == subject)

    def refresh(self, at: str | None = None, half_life_days: float = 30.0) -> tuple[EvidenceRecord, ...]:
        return tuple(sorted(self._records.values(), key=lambda record: record.decayed_confidence(half_life_days, at), reverse=True))

    def conflict(self, conflict_id: str, subject: str, evidence_ids: Iterable[str], likely_resolution: str | None = None) -> EvidenceConflict:
        claims = tuple(self._records[evidence_id] for evidence_id in evidence_ids if evidence_id in self._records)
        result = EvidenceConflict(conflict_id, subject, claims, unresolved=likely_resolution is None, likely_resolution=likely_resolution)
        self._conflicts.append(result)
        for claim in claims:
            self._records[claim.evidence_id] = claim.contradict()
        return result

    @property
    def conflicts(self) -> tuple[EvidenceConflict, ...]:
        return tuple(self._conflicts)
