"""Semantic comparison primitives for logically equivalent representations."""
from __future__ import annotations

import datetime as dt
import decimal
import re
from collections.abc import Mapping
from typing import Any

from .fingerprint import merkle_root, row_fingerprint, sha256_hex


def normalize_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
            try:
                return dt.datetime.strptime(text, fmt).replace(tzinfo=dt.timezone.utc).isoformat()
            except ValueError:
                pass
        try:
            return str(decimal.Decimal(text).normalize())
        except decimal.InvalidOperation:
            return re.sub(r"\s+", " ", text).casefold()
    if isinstance(value, (int, float, decimal.Decimal)) and not isinstance(value, bool):
        return str(decimal.Decimal(str(value)).normalize())
    return value


def semantic_row(row: Mapping[str, Any], aliases: Mapping[str, str] | None = None) -> dict[str, Any]:
    aliases = aliases or {}
    result: dict[str, Any] = {}
    for key, value in row.items():
        if str(key).startswith("_atlas_"):
            continue
        result[aliases.get(str(key), str(key))] = normalize_scalar(value)
    return dict(sorted(result.items()))


def semantic_fingerprint(row: Mapping[str, Any], aliases: Mapping[str, str] | None = None) -> str:
    return sha256_hex(semantic_row(row, aliases))


def compare_rows(source: Mapping[str, Any], target: Mapping[str, Any], aliases: Mapping[str, str] | None = None) -> dict[str, Any]:
    source_bytes = row_fingerprint(source)
    target_bytes = row_fingerprint(target)
    source_semantic = semantic_fingerprint(source, aliases)
    target_semantic = semantic_fingerprint(target, aliases)
    return {"byte_equivalent": source_bytes == target_bytes, "semantic_equivalent": source_semantic == target_semantic, "source_byte_hash": source_bytes, "target_byte_hash": target_bytes, "source_semantic_hash": source_semantic, "target_semantic_hash": target_semantic}


def semantic_merkle_root(rows: list[Mapping[str, Any]], aliases: Mapping[str, str] | None = None) -> str:
    return merkle_root([semantic_fingerprint(row, aliases) for row in rows])


def semantic_diff(source_schema: Mapping[str, list[str]], target_schema: Mapping[str, list[str]], mappings: Mapping[str, str] | None = None) -> list[dict[str, Any]]:
    mappings = mappings or {}
    changes: list[dict[str, Any]] = []
    for table in sorted(set(source_schema) | set(target_schema)):
        source_fields = set(source_schema.get(table, ()))
        target_fields = set(target_schema.get(table, ()))
        for field in sorted(source_fields - target_fields):
            mapped = mappings.get(f"{table}.{field}")
            changes.append({"kind": "REPRESENTATION_CHANGE" if mapped else "STRUCTURAL_CHANGE", "source": f"{table}.{field}", "target": mapped, "semantic_loss": mapped is None})
        for field in sorted(target_fields - source_fields):
            if f"{table}.{field}" not in mappings.values():
                changes.append({"kind": "STRUCTURAL_CHANGE", "source": None, "target": f"{table}.{field}"})
    return changes
