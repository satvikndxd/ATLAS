"""Deterministic schema intelligence for legacy row-oriented datasets."""
from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

from .contracts import ColumnProfile, Evidence, InferredRelationship, SchemaFingerprint
from .fingerprint import sha256_hex

_PII_NAME = re.compile(r"(^|_)(email|phone|address|ssn|tax|gov|passport|card|account|customer|dob)(_|$)", re.I)
_IDENTIFIER_NAME = re.compile(r"(^|_)(id|no|number|code|key|ref)(_|$)", re.I)


def infer_type(values: Iterable[Any]) -> str:
    observed = [value for value in values if value is not None]
    if not observed:
        return "unknown"
    if all(isinstance(value, bool) for value in observed):
        return "boolean"
    if all(isinstance(value, int) and not isinstance(value, bool) for value in observed):
        return "integer"
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in observed):
        return "number"
    return "string"


def profile_table(rows: list[Mapping[str, Any]]) -> tuple[ColumnProfile, ...]:
    fields = sorted({field for row in rows for field in row})
    profiles: list[ColumnProfile] = []
    for field in fields:
        values = [row.get(field) for row in rows]
        non_null = [value for value in values if value is not None]
        counts = Counter(str(value) for value in non_null)
        ordered_top = tuple(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:5])
        try:
            min_value = min(non_null) if non_null else None
            max_value = max(non_null) if non_null else None
        except TypeError:
            min_value = max_value = None
        profiles.append(
            ColumnProfile(
                name=field,
                data_type=infer_type(values),
                nullable=any(value is None for value in values),
                row_count=len(rows),
                null_count=len(values) - len(non_null),
                distinct_count=len(counts),
                min_value=min_value,
                max_value=max_value,
                top_values=ordered_top,
                likely_pii=bool(_PII_NAME.search(field)),
                likely_identifier=bool(_IDENTIFIER_NAME.search(field)),
            )
        )
    return tuple(profiles)


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right) if left | right else 0.0


def infer_relationships(
    tables: Mapping[str, list[Mapping[str, Any]]],
    min_confidence: float = 0.75,
) -> tuple[InferredRelationship, ...]:
    proposals: list[InferredRelationship] = []
    profiles = {name: profile_table(rows) for name, rows in tables.items()}
    for source_table, source_rows in tables.items():
        for target_table, target_rows in tables.items():
            if source_table == target_table:
                continue
            for source_profile in profiles[source_table]:
                source_values = {str(row.get(source_profile.name)) for row in source_rows if row.get(source_profile.name) is not None}
                if not source_values:
                    continue
                for target_profile in profiles[target_table]:
                    target_values = {str(row.get(target_profile.name)) for row in target_rows if row.get(target_profile.name) is not None}
                    if not target_values:
                        continue
                    def normalize_identifier(name: str) -> str:
                        normalized = name.lower()
                        for suffix in ("_ref", "_id", "_no", "_number", "_key"):
                            if normalized.endswith(suffix):
                                normalized = normalized[: -len(suffix)]
                                break
                        return normalized
                    name_score = 1.0 if normalize_identifier(source_profile.name) == normalize_identifier(target_profile.name) else 0.0
                    type_score = 1.0 if source_profile.data_type == target_profile.data_type else 0.0
                    overlap = len(source_values & target_values) / len(source_values)
                    coverage = min(overlap, 1.0)
                    confidence = 0.45 * name_score + 0.20 * type_score + 0.35 * coverage
                    evidence = (
                        Evidence("naming", f"{source_profile.name} ↔ {target_profile.name}", name_score),
                        Evidence("type", f"{source_profile.data_type} ↔ {target_profile.data_type}", type_score),
                        Evidence("value_overlap", f"{len(source_values & target_values)} shared values", coverage),
                    )
                    if confidence >= min_confidence:
                        proposals.append(
                            InferredRelationship(source_table, source_profile.name, target_table, target_profile.name, confidence, evidence)
                        )
    return tuple(sorted(proposals, key=lambda item: item.confidence, reverse=True))


def fingerprint_schema(source_id: str, tables: Mapping[str, list[Mapping[str, Any]]], schema_version: str = "v1") -> SchemaFingerprint:
    table_payload: dict[str, dict[str, Any]] = {}
    for table_name, rows in sorted(tables.items()):
        profiles = profile_table(rows)
        table_payload[table_name] = {
            "row_count": len(rows),
            "columns": [
                {
                    "name": profile.name,
                    "type": profile.data_type,
                    "nullable": profile.nullable,
                    "distinct_count": profile.distinct_count,
                    "likely_pii": profile.likely_pii,
                }
                for profile in profiles
            ],
        }
    relationships = tuple(item.__dict__ for item in infer_relationships(tables))
    digest = sha256_hex({"source_id": source_id, "schema_version": schema_version, "tables": table_payload, "relationships": relationships})
    return SchemaFingerprint(source_id, schema_version, table_payload, relationships, digest)


def compare_fingerprints(before: SchemaFingerprint, after: SchemaFingerprint) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    before_tables = set(before.tables)
    after_tables = set(after.tables)
    for table in sorted(after_tables - before_tables):
        changes.append({"table": table, "kind": "TABLE_ADDED", "severity": "SAFE"})
    for table in sorted(before_tables - after_tables):
        changes.append({"table": table, "kind": "TABLE_REMOVED", "severity": "CRITICAL"})
    for table in sorted(before_tables & after_tables):
        old_cols = {item["name"]: item for item in before.tables[table]["columns"]}
        new_cols = {item["name"]: item for item in after.tables[table]["columns"]}
        for column in sorted(new_cols.keys() - old_cols.keys()):
            changes.append({"table": table, "column": column, "kind": "COLUMN_ADDED", "severity": "SAFE"})
        for column in sorted(old_cols.keys() - new_cols.keys()):
            changes.append({"table": table, "column": column, "kind": "COLUMN_REMOVED", "severity": "BREAKING"})
        for column in sorted(old_cols.keys() & new_cols.keys()):
            if old_cols[column]["type"] != new_cols[column]["type"]:
                severity = "CRITICAL" if {old_cols[column]["type"], new_cols[column]["type"]} == {"number", "string"} else "WARNING"
                changes.append({"table": table, "column": column, "kind": "DATATYPE_CHANGED", "severity": severity})
    return changes
