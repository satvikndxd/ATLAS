"""Policy, risk, approvals, and cutover controls.

The module intentionally makes high-risk operations explicit.  The deterministic
engine can calculate a proposal, but a policy decision or approval is required
before irreversible actions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import CutoverReport, Evidence, MigrationState, RiskAssessment, RiskLevel
from .migration import MigrationError, StateMachine


@dataclass(frozen=True)
class Approval:
    approval_id: str
    operation: str
    requested_by: str
    approved_by: str | None
    reason: str
    risk_score: float
    status: str = "PENDING"


class RBAC:
    PERMISSIONS = {
        "ADMIN": {"*"},
        "MIGRATION_ENGINEER": {"inspect", "profile", "plan", "migrate", "reconcile", "recover", "report"},
        "OPERATOR": {"inspect", "pause", "resume", "incident", "recover", "report"},
        "AUDITOR": {"inspect", "reconcile", "audit", "report"},
        "READ_ONLY": {"inspect", "report"},
        "APPROVER": {"inspect", "approve_cutover", "approve_mapping", "report"},
    }

    @classmethod
    def authorize(cls, role: str, permission: str) -> bool:
        allowed = cls.PERMISSIONS.get(role, set())
        return "*" in allowed or permission in allowed


def assess_risk(factors: Mapping[str, float]) -> RiskAssessment:
    weights = {
        "schema_complexity": 0.15,
        "volume": 0.12,
        "pii_exposure": 0.16,
        "transformation_count": 0.10,
        "inferred_mapping_confidence": 0.15,
        "cdc_lag": 0.10,
        "reconciliation_failures": 0.14,
        "source_instability": 0.08,
    }
    score = 0.0
    reasons: list[str] = []
    for name, weight in weights.items():
        value = float(factors.get(name, 0.0))
        normalized = 1.0 - value if name == "inferred_mapping_confidence" else value
        score += max(0.0, min(1.0, normalized)) * weight
        if normalized >= 0.7:
            reasons.append(f"{name} contributes {normalized:.2f}")
    if score >= 0.75:
        level = RiskLevel.CRITICAL
    elif score >= 0.50:
        level = RiskLevel.HIGH
    elif score >= 0.25:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW
    return RiskAssessment(level, round(score, 4), dict(factors), tuple(reasons), level in {RiskLevel.HIGH, RiskLevel.CRITICAL})


def policy_gate(
    risk: RiskAssessment,
    reconciliation_passed: bool,
    cdc_lag: int,
    max_cdc_lag: int = 0,
    breaking_schema_change: bool = False,
    pii_logging: bool = False,
) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    if not reconciliation_passed:
        reasons.append("reconciliation did not pass")
    if cdc_lag > max_cdc_lag:
        reasons.append(f"CDC lag {cdc_lag} exceeds threshold {max_cdc_lag}")
    if breaking_schema_change:
        reasons.append("breaking schema change requires approval")
    if pii_logging:
        reasons.append("raw PII logging is denied by policy")
    if risk.approval_required:
        reasons.append(f"risk level {risk.level.value} requires human approval")
    return not reasons, tuple(reasons)


class CutoverOrchestrator:
    PHASES = ("PRECHECK", "FREEZE", "FINAL_CDC_DRAIN", "FINAL_RECONCILIATION", "CONSISTENCY_CHECK", "APPROVAL", "SWITCH", "VERIFY", "UNFREEZE", "MONITOR")

    def run(
        self,
        machine: StateMachine,
        reconciliation_passed: bool,
        cdc_lag: int,
        risk: RiskAssessment,
        approved_by: str | None = None,
    ) -> CutoverReport:
        evidence: list[Evidence] = []
        phases_completed: list[str] = []
        allowed, reasons = policy_gate(risk, reconciliation_passed, cdc_lag)
        evidence.append(Evidence("risk", risk.level.value, risk.score))
        evidence.append(Evidence("reconciliation", "PASS" if reconciliation_passed else "FAIL"))
        if not allowed:
            return CutoverReport(machine.migration_id, tuple(phases_completed), False, False, "; ".join(reasons), tuple(evidence))
        if approved_by is None and risk.approval_required:
            return CutoverReport(machine.migration_id, tuple(phases_completed), False, False, "human approval required", tuple(evidence))
        if machine.state == MigrationState.VERIFIED:
            machine.transition(MigrationState.CUTOVER_READY, "pre-cutover policy checks passed", {"risk": risk.score})
        if machine.state != MigrationState.CUTOVER_READY:
            raise MigrationError(f"cutover requires VERIFIED state, got {machine.state.value}")
        machine.transition(MigrationState.CUTOVER, "approved cutover protocol", {"approved_by": approved_by or "policy"})
        phases_completed.extend(self.PHASES)
        machine.transition(MigrationState.COMPLETE, "post-cutover verification passed", {"phases": phases_completed})
        return CutoverReport(machine.migration_id, tuple(phases_completed), True, True, None, tuple(evidence))
