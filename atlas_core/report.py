"""Certification and report artifacts."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class Gate:
    name: str
    passed: bool
    evidence: str
    required: bool = True


@dataclass(frozen=True)
class Certification:
    migration_id: str
    gates: tuple[Gate, ...]
    status: str
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "migration_id": self.migration_id,
            "gates": [gate.__dict__ for gate in self.gates],
            "status": self.status,
            "limitations": list(self.limitations),
        }


def certify(migration_id: str, gates: list[Gate], limitations: list[str] | None = None) -> Certification:
    required = [gate for gate in gates if gate.required]
    status = "CERTIFIED" if required and all(gate.passed for gate in required) else "NOT_CERTIFIED"
    return Certification(migration_id, tuple(gates), status, tuple(limitations or []))


def write_report(path: str | Path, certification: Certification, technical: Mapping[str, Any], executive: Mapping[str, Any]) -> None:
    output = {"certification": certification.as_dict(), "technical": dict(technical), "executive": dict(executive)}
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2, sort_keys=True, default=str), encoding="utf-8")
