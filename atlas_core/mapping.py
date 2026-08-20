"""Evidence-backed field matching and immutable mapping registry."""
from __future__ import annotations

import re
from dataclasses import replace
from typing import Any, Iterable, Mapping

from .contracts import Evidence, MappingProposal, MappingStatus


def _tokens(name: str) -> set[str]:
    return {token for token in re.split(r"[_\W]+", name.lower()) if token}


def _similarity(left: str, right: str) -> float:
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def propose_mappings(source_columns: Iterable[Mapping[str, Any]], target_columns: Iterable[Mapping[str, Any]], source_table: str, target_table: str) -> tuple[MappingProposal, ...]:
    proposals: list[MappingProposal] = []
    for source in source_columns:
        best: tuple[float, Mapping[str, Any]] | None = None
        for target in target_columns:
            lexical = _similarity(str(source["name"]), str(target["name"]))
            type_score = 1.0 if source.get("data_type") == target.get("data_type") else 0.0
            confidence = 0.7 * lexical + 0.3 * type_score
            if best is None or confidence > best[0]:
                best = (confidence, target)
        if best is None:
            continue
        confidence, target = best
        status = MappingStatus.REVIEW_REQUIRED if confidence < 0.98 else MappingStatus.PROPOSED
        evidence = (Evidence("lexical_similarity", f"{source['name']} ↔ {target['name']}", round(_similarity(str(source['name']), str(target['name'])), 4)), Evidence("datatype_compatibility", f"{source.get('data_type')} ↔ {target.get('data_type')}", 1.0 if source.get("data_type") == target.get("data_type") else 0.0))
        proposals.append(MappingProposal(f"map-{source_table}-{source['name']}-{target_table}-{target['name']}", source_table, str(source["name"]), target_table, str(target["name"]), f"IDENTITY(source.{source['name']})", round(confidence, 4), evidence, ("source and target fields must be reviewed before approval",), status=status))
    return tuple(proposals)


class MappingRegistry:
    def __init__(self):
        self._versions: dict[str, list[MappingProposal]] = {}

    def add(self, proposal: MappingProposal) -> MappingProposal:
        history = self._versions.setdefault(proposal.mapping_id, [])
        if history and history[-1].status == MappingStatus.APPROVED:
            proposal = replace(proposal, version=history[-1].version + 1)
        history.append(proposal)
        return proposal

    def approve(self, mapping_id: str, approver: str) -> MappingProposal:
        if mapping_id not in self._versions or not self._versions[mapping_id]:
            raise KeyError(mapping_id)
        current = self._versions[mapping_id][-1]
        if current.status not in {MappingStatus.PROPOSED, MappingStatus.REVIEW_REQUIRED}:
            raise ValueError(f"mapping {mapping_id} is not approvable from {current.status}")
        approved = replace(current, status=MappingStatus.APPROVED, approval=approver)
        self._versions[mapping_id].append(approved)
        return approved

    def history(self, mapping_id: str) -> tuple[MappingProposal, ...]:
        return tuple(self._versions.get(mapping_id, ()))

    def approved(self) -> tuple[MappingProposal, ...]:
        return tuple(history[-1] for history in self._versions.values() if history and history[-1].status == MappingStatus.APPROVED)
