"""Shadow-world counterfactual and state reconstruction primitives."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import Evidence
from .epistemic import EpistemicStatus
from .fingerprint import sha256_hex


@dataclass(frozen=True)
class ReconstructionCandidate:
    candidate_id: str
    entity: str
    candidate_state: Mapping[str, Any]
    supporting_evidence: tuple[Evidence, ...]
    contradicting_evidence: tuple[Evidence, ...]
    confidence: float
    status: EpistemicStatus = EpistemicStatus.RECONSTRUCTED
    alternatives: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True)
class CounterfactualResult:
    scenario: str
    baseline_fingerprint: str
    counterfactual_fingerprint: str
    direct_impact: tuple[str, ...]
    secondary_impact: tuple[str, ...]
    financial_delta: Mapping[str, float]
    semantic_delta: Mapping[str, Any]
    blast_radius: Mapping[str, int]
    status: EpistemicStatus = EpistemicStatus.COUNTERFACTUAL


def reconstruct_state(entity: str, snapshots: list[Mapping[str, Any]], later_state: Mapping[str, Any] | None = None, invariants: list[str] | None = None) -> ReconstructionCandidate:
    if not snapshots and not later_state:
        return ReconstructionCandidate(f"recon-{entity}-unknown", entity, {}, (), (Evidence("absence", "no source evidence"),), 0.0)
    latest = dict(later_state or snapshots[-1])
    support = tuple(Evidence("snapshot", f"snapshot {index}", 0.6 + index / max(1, len(snapshots) * 10)) for index, _ in enumerate(snapshots))
    contradictions: list[Evidence] = []
    for invariant in invariants or []:
        if invariant not in latest:
            contradictions.append(Evidence("invariant", invariant, 0.5))
    confidence = max(0.0, min(1.0, 0.55 + 0.1 * len(snapshots) - 0.15 * len(contradictions)))
    return ReconstructionCandidate(f"recon-{entity}-{sha256_hex(latest)[:12]}", entity, latest, support, tuple(contradictions), confidence)


def counterfactual_remove_transaction(state: Mapping[str, Mapping[str, Any]], transaction_id: str, account_field: str = "account_id", amount_field: str = "amount") -> CounterfactualResult:
    baseline = {key: dict(value) for key, value in state.items()}
    removed = baseline.pop(transaction_id, None)
    if removed is None:
        return CounterfactualResult(f"remove:{transaction_id}", sha256_hex(baseline), sha256_hex(baseline), (), (), {}, {"reason": "transaction not present"}, {"records": 0})
    account = str(removed.get(account_field, "unknown"))
    try:
        amount = float(removed.get(amount_field, 0.0))
    except (TypeError, ValueError):
        amount = 0.0
    changed = [key for key, row in baseline.items() if str(row.get(account_field)) == account]
    return CounterfactualResult(f"remove:{transaction_id}", sha256_hex(state), sha256_hex(baseline), (transaction_id,), tuple(changed), {account: -amount}, {"removed_transaction": transaction_id}, {"transactions": 1, "accounts": len(changed), "unknown_downstream": 0})
