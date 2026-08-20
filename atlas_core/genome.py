"""General-purpose Data Genome representation and explainable distance."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .epistemic import EpistemicStatus, EvidenceRecord
from .fingerprint import sha256_hex


@dataclass(frozen=True)
class GenomeMetric:
    name: str
    value: float
    method: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class DataGenome:
    genome_id: str
    version: str
    entities: Mapping[str, Mapping[str, Any]]
    relationships: tuple[Mapping[str, Any], ...]
    constraints: tuple[Mapping[str, Any], ...]
    temporal_behavior: Mapping[str, Any]
    mutation_velocity: Mapping[str, float]
    distributions: Mapping[str, Mapping[str, Any]]
    identity_structure: Mapping[str, Any]
    schema_history: tuple[Mapping[str, Any], ...]
    semantic_types: Mapping[str, str]
    business_rules: tuple[Mapping[str, Any], ...]
    invariants: tuple[Mapping[str, Any], ...]
    provenance: tuple[str, ...] = ()
    failure_history: tuple[Mapping[str, Any], ...] = ()
    access_patterns: Mapping[str, Any] = field(default_factory=dict)
    dependency_graph: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    uncertainty: Mapping[str, float] = field(default_factory=dict)
    status: EpistemicStatus = EpistemicStatus.DERIVED
    fingerprint: str = ""
    evidence: tuple[EvidenceRecord, ...] = ()

    def __post_init__(self) -> None:
        if not self.fingerprint:
            payload = {
                "genome_id": self.genome_id,
                "version": self.version,
                "entities": self.entities,
                "relationships": self.relationships,
                "constraints": self.constraints,
                "semantic_types": self.semantic_types,
                "invariants": self.invariants,
            }
            object.__setattr__(self, "fingerprint", sha256_hex(payload))


def _set_distance(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    return 1.0 - len(left & right) / len(left | right)


def _numeric_distance(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    keys = set(left) | set(right)
    if not keys:
        return 0.0
    return sum(min(1.0, abs(float(left.get(key, 0.0)) - float(right.get(key, 0.0)))) for key in keys) / len(keys)


def _relationship_keys(genome: DataGenome) -> set[str]:
    return {f"{item.get('source_table')}:{item.get('source_column')}->{item.get('target_table')}:{item.get('target_column')}" for item in genome.relationships}


def _semantic_keys(genome: DataGenome) -> set[str]:
    return {f"{key}:{value}" for key, value in genome.semantic_types.items()}


def genome_distance(source: DataGenome, target: DataGenome) -> dict[str, GenomeMetric]:
    schema_left = set(source.entities) | {f"{entity}.{column}" for entity, payload in source.entities.items() for column in payload.get("columns", ())}
    schema_right = set(target.entities) | {f"{entity}.{column}" for entity, payload in target.entities.items() for column in payload.get("columns", ())}
    entity_left, entity_right = set(source.entities), set(target.entities)
    invariant_left = {str(rule.get("name", rule)) for rule in source.invariants}
    invariant_right = {str(rule.get("name", rule)) for rule in target.invariants}
    temporal_left = set(source.temporal_behavior)
    temporal_right = set(target.temporal_behavior)
    distribution_left = set(source.distributions)
    distribution_right = set(target.distributions)
    return {
        "schema": GenomeMetric("schema", _set_distance(schema_left, schema_right), "Jaccard distance over entities and columns"),
        "entity": GenomeMetric("entity", _set_distance(entity_left, entity_right), "Jaccard distance over entity names"),
        "relationship": GenomeMetric("relationship", _set_distance(_relationship_keys(source), _relationship_keys(target)), "Jaccard distance over relationship signatures"),
        "temporal": GenomeMetric("temporal", _set_distance(temporal_left, temporal_right), "Jaccard distance over temporal dimensions"),
        "distribution": GenomeMetric("distribution", _set_distance(distribution_left, distribution_right), "Jaccard distance over profiled distributions"),
        "semantic": GenomeMetric("semantic", _set_distance(_semantic_keys(source), _semantic_keys(target)), "Jaccard distance over semantic type assignments"),
        "invariant": GenomeMetric("invariant", _set_distance(invariant_left, invariant_right), "Jaccard distance over invariant names"),
        "behavioral": GenomeMetric("behavioral", _numeric_distance(source.mutation_velocity, target.mutation_velocity), "mean bounded mutation-velocity difference"),
    }


def genome_summary(genome: DataGenome) -> dict[str, Any]:
    return {
        "genome_id": genome.genome_id,
        "version": genome.version,
        "fingerprint": genome.fingerprint,
        "status": genome.status.value,
        "entity_count": len(genome.entities),
        "relationship_count": len(genome.relationships),
        "invariant_count": len(genome.invariants),
        "uncertain_components": sorted(key for key, value in genome.uncertainty.items() if value > 0.5),
        "evidence_count": len(genome.evidence),
    }
