"""Assumption ledger with temporal validity and dependency impact."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Iterable

from .epistemic import EvidenceRecord


class AssumptionStatus(str, Enum):
    INFERRED = "INFERRED"
    VALIDATED = "VALIDATED"
    INVALIDATED = "INVALIDATED"
    SUPERSEDED = "SUPERSEDED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Assumption:
    assumption_id: str
    statement: str
    evidence_ids: tuple[str, ...]
    confidence: float
    status: AssumptionStatus
    created_at: str
    last_verified_at: str | None = None
    contradicted_at: str | None = None
    dependent_results: tuple[str, ...] = ()
    notes: str = ""


class AssumptionLedger:
    def __init__(self):
        self._items: dict[str, Assumption] = {}

    def add(self, assumption: Assumption) -> Assumption:
        if not 0.0 <= assumption.confidence <= 1.0:
            raise ValueError("assumption confidence must be within [0, 1]")
        self._items[assumption.assumption_id] = assumption
        return assumption

    def verify(self, assumption_id: str, evidence_ids: Iterable[str], verified_at: str) -> Assumption:
        item = self._items[assumption_id]
        updated = replace(item, evidence_ids=tuple(evidence_ids), confidence=min(1.0, item.confidence + 0.05), status=AssumptionStatus.VALIDATED, last_verified_at=verified_at)
        self._items[assumption_id] = updated
        return updated

    def invalidate(self, assumption_id: str, contradicted_at: str, reason: str) -> tuple[Assumption, tuple[str, ...]]:
        item = self._items[assumption_id]
        updated = replace(item, status=AssumptionStatus.INVALIDATED, contradicted_at=contradicted_at, confidence=0.0, notes=f"{item.notes}; contradicted: {reason}".strip("; "))
        self._items[assumption_id] = updated
        return updated, item.dependent_results

    def depend(self, assumption_id: str, result_id: str) -> Assumption:
        item = self._items[assumption_id]
        if result_id in item.dependent_results:
            return item
        updated = replace(item, dependent_results=item.dependent_results + (result_id,))
        self._items[assumption_id] = updated
        return updated

    def get(self, assumption_id: str) -> Assumption | None:
        return self._items.get(assumption_id)

    def all(self) -> tuple[Assumption, ...]:
        return tuple(self._items.values())
