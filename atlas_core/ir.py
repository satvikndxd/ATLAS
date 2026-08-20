"""Migration compiler intermediate representation."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Mapping

from .fingerprint import sha256_hex


@dataclass(frozen=True)
class IRMapping:
    source_entity: str
    source_field: str
    target_entity: str
    target_field: str
    expression: str
    mapping_version: str = "v1"


@dataclass(frozen=True)
class MigrationIR:
    ir_id: str
    source_version: str
    target_version: str
    mappings: tuple[IRMapping, ...]
    constraints: tuple[Mapping[str, Any], ...] = ()
    validations: tuple[Mapping[str, Any], ...] = ()
    policies: tuple[Mapping[str, Any], ...] = ()
    risk: Mapping[str, float] = field(default_factory=dict)
    resource_limits: Mapping[str, float] = field(default_factory=dict)
    dependencies: tuple[tuple[str, str], ...] = ()
    approvals_required: tuple[str, ...] = ()
    version: str = "v1"

    @property
    def fingerprint(self) -> str:
        return sha256_hex(asdict(self))

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["fingerprint"] = self.fingerprint
        return payload


def diff_ir(left: MigrationIR, right: MigrationIR) -> dict[str, Any]:
    left_map = {(item.source_entity, item.source_field): item for item in left.mappings}
    right_map = {(item.source_entity, item.source_field): item for item in right.mappings}
    changed: list[dict[str, Any]] = []
    for key in sorted(set(left_map) | set(right_map)):
        before = left_map.get(key)
        after = right_map.get(key)
        if before != after:
            changed.append({"source": key, "before": asdict(before) if before else None, "after": asdict(after) if after else None})
    return {"left": left.fingerprint, "right": right.fingerprint, "mapping_changes": changed, "policy_changed": left.policies != right.policies, "risk_changed": left.risk != right.risk, "dependencies_changed": left.dependencies != right.dependencies}


def compile_ir(source_version: str, target_version: str, mappings: list[IRMapping], constraints: list[Mapping[str, Any]] | None = None, validations: list[Mapping[str, Any]] | None = None, policies: list[Mapping[str, Any]] | None = None, risk: Mapping[str, float] | None = None, resource_limits: Mapping[str, float] | None = None, dependencies: list[tuple[str, str]] | None = None, approvals_required: list[str] | None = None) -> MigrationIR:
    provisional = MigrationIR("", source_version, target_version, tuple(mappings), tuple(constraints or ()), tuple(validations or ()), tuple(policies or ()), dict(risk or {}), dict(resource_limits or {}), tuple(dependencies or ()), tuple(approvals_required or ()))
    return MigrationIR(f"ir-{provisional.fingerprint[:16]}", provisional.source_version, provisional.target_version, provisional.mappings, provisional.constraints, provisional.validations, provisional.policies, provisional.risk, provisional.resource_limits, provisional.dependencies, provisional.approvals_required, provisional.version)
