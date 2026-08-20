"""System archaeology over unknown row-oriented datasets."""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .epistemic import EvidenceRecord, EpistemicStatus, FindingStatus
from .schema import infer_type, infer_relationships, profile_table

_DATE = re.compile(r"(^|_)(date|time|timestamp|created|updated|closed|opened|effective|event)(_|$)", re.I)
_MONEY = re.compile(r"(^|_)(amount|balance|price|fee|debit|credit|value|revenue|cost)(_|$)", re.I)
_PII = re.compile(r"(^|_)(name|email|phone|address|ssn|tax|passport|dob|birth)(_|$)", re.I)
_STATUS = re.compile(r"(^|_)(status|state|type|stage|phase)(_|$)", re.I)


@dataclass(frozen=True)
class ArchaeologyFinding:
    finding_id: str
    category: str
    subject: str
    status: FindingStatus
    confidence: float
    evidence: tuple[EvidenceRecord, ...]
    counter_evidence: tuple[str, ...] = ()
    detail: str = ""


@dataclass(frozen=True)
class ArchaeologyReport:
    source_id: str
    findings: tuple[ArchaeologyFinding, ...]
    tables: tuple[str, ...]
    unknowns: tuple[str, ...]

    def by_category(self, category: str) -> tuple[ArchaeologyFinding, ...]:
        return tuple(item for item in self.findings if item.category == category)


def _finding(table: str, field: str, category: str, status: FindingStatus, confidence: float, detail: str, evidence: str) -> ArchaeologyFinding:
    record = EvidenceRecord(f"evidence-{table}-{field}-{category}", f"{table}.{field}", detail, "deterministic-archaeologist", status=EpistemicStatus.DERIVED, confidence=confidence, detail=evidence)
    return ArchaeologyFinding(f"finding-{table}-{field}-{category}", category, f"{table}.{field}", status, confidence, (record,), detail=detail)


def archaeologize(source_id: str, tables: Mapping[str, list[Mapping[str, Any]]]) -> ArchaeologyReport:
    findings: list[ArchaeologyFinding] = []
    unknowns: list[str] = []
    for table, rows in tables.items():
        profiles = profile_table(list(rows))
        for profile in profiles:
            field = profile.name
            if profile.likely_identifier:
                uniqueness = profile.distinct_count / profile.row_count if profile.row_count else 0.0
                status = FindingStatus.KNOWN if uniqueness >= 0.99 else FindingStatus.LIKELY
                findings.append(_finding(table, field, "identifier", status, uniqueness, "candidate stable identifier", f"name heuristic and uniqueness={uniqueness:.3f}"))
            if profile.likely_pii or _PII.search(field):
                findings.append(_finding(table, field, "pii", FindingStatus.LIKELY, 0.85, "candidate personally identifiable field", "field-name heuristic; content not exported"))
            if _DATE.search(field):
                findings.append(_finding(table, field, "temporal", FindingStatus.LIKELY, 0.82, "candidate event/knowledge/effective time field", "field-name heuristic"))
            if _MONEY.search(field):
                findings.append(_finding(table, field, "monetary", FindingStatus.LIKELY, 0.80, "candidate monetary or financial value field", "field-name heuristic and numeric profile"))
            if _STATUS.search(field):
                values = sorted({str(row.get(field)) for row in rows if row.get(field) is not None})
                findings.append(_finding(table, field, "categorical", FindingStatus.OBSERVED, 0.95, "observed categorical/state field", f"distinct values={values[:12]}"))
            if profile.data_type == "unknown":
                unknowns.append(f"{table}.{field}: type unknown")
        if not rows:
            unknowns.append(f"{table}: empty table prevents inference")
    for relationship in infer_relationships(tables, min_confidence=0.6):
        findings.append(_finding(relationship.source_table, relationship.source_column, "relationship", FindingStatus.INFERRED, relationship.confidence, f"candidate relationship to {relationship.target_table}.{relationship.target_column}", "; ".join(item.detail for item in relationship.evidence)))
    for table, rows in tables.items():
        for field in sorted({key for row in rows for key in row}):
            if _STATUS.search(field):
                values = {str(row.get(field)).upper() for row in rows if row.get(field) is not None}
                if {"CLOSED", "OPEN", "ACTIVE"} & values:
                    findings.append(_finding(table, field, "business_rule", FindingStatus.INFERRED, 0.55, "candidate lifecycle state rule requires review", f"observed state values={sorted(values)}"))
    return ArchaeologyReport(source_id, tuple(findings), tuple(tables), tuple(sorted(set(unknowns))))
