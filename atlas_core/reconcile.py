"""Evidence-producing reconciliation and divergence localization."""
from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

from .contracts import Evidence, ReconciliationReport
from .fingerprint import batch_fingerprint, merkle_root, row_fingerprint, sha256_hex


def _numeric(rows: Iterable[Mapping[str, Any]], field: str) -> list[float]:
    result: list[float] = []
    for row in rows:
        value = row.get(field)
        try:
            if value is not None:
                result.append(float(value))
        except (TypeError, ValueError):
            continue
    return result


def _aggregate(rows: list[Mapping[str, Any]], fields: Iterable[str]) -> dict[str, float]:
    output: dict[str, float] = {}
    for field in fields:
        values = _numeric(rows, field)
        if values:
            output[f"{field}.sum"] = sum(values)
            output[f"{field}.min"] = min(values)
            output[f"{field}.max"] = max(values)
            output[f"{field}.avg"] = sum(values) / len(values)
    return output


def _quantiles(values: list[float]) -> tuple[float, float, float] | None:
    if not values:
        return None
    ordered = sorted(values)
    def q(percentile: float) -> float:
        position = (len(ordered) - 1) * percentile
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        fraction = position - lower
        return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction
    return q(0.5), q(0.95), q(0.99)


def _business_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not str(key).startswith("_atlas_")}


def _key_map(rows: Iterable[Mapping[str, Any]], key: str) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    mapping: dict[str, Mapping[str, Any]] = {}
    duplicates: list[str] = []
    for raw in rows:
        row = _business_row(raw)
        value = str(row.get(key))
        if value in mapping:
            duplicates.append(value)
        else:
            mapping[value] = row
    return mapping, duplicates


def _financial_invariants(rows: list[Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    for row in rows:
        if {"opening_balance", "credits", "debits", "adjustments", "closing_balance"}.issubset(row):
            try:
                expected = float(row["opening_balance"]) + float(row["credits"]) - float(row["debits"]) + float(row["adjustments"])
                actual = float(row["closing_balance"])
                if not math.isclose(expected, actual, abs_tol=0.0001):
                    errors.append(f"account {row.get('account_id', row.get('id'))}: balance invariant {expected} != {actual}")
            except (TypeError, ValueError):
                errors.append(f"account {row.get('account_id', row.get('id'))}: non-numeric balance fields")
    return errors


def reconcile(
    migration_id: str,
    table: str,
    source_rows: list[Mapping[str, Any]],
    target_rows: list[Mapping[str, Any]],
    key: str,
    numeric_fields: Iterable[str] = (),
    referential_checks: Iterable[tuple[str, set[str]]] = (),
    sample_size: int = 25,
    seed: int = 42,
) -> ReconciliationReport:
    source_map, source_duplicates = _key_map(source_rows, key)
    target_map, target_duplicates = _key_map(target_rows, key)
    source_keys = set(source_map)
    target_keys = set(target_map)
    missing = sorted(source_keys - target_keys)
    unexpected = sorted(target_keys - source_keys)
    aggregate_source = _aggregate(source_rows, numeric_fields)
    aggregate_target = _aggregate(target_rows, numeric_fields)
    aggregate_deltas = {field: aggregate_target.get(field, 0.0) - value for field, value in aggregate_source.items()}
    source_hash = batch_fingerprint(sorted((_business_row(row) for row in source_rows), key=lambda row: str(row.get(key))), [key])
    target_hash = batch_fingerprint(sorted((_business_row(row) for row in target_rows), key=lambda row: str(row.get(key))), [key])
    sampled = random.Random(seed).sample(sorted(source_keys & target_keys), min(sample_size, len(source_keys & target_keys)))
    mismatches = [item for item in sampled if row_fingerprint(source_map[item]) != row_fingerprint(target_map[item])]
    referential_errors: list[str] = []
    for field, valid_keys in referential_checks:
        for row in target_rows:
            if row.get(field) is not None and str(row[field]) not in valid_keys:
                referential_errors.append(f"{key}={row.get(key)} references missing {field}={row.get(field)}")
    distribution_deltas: dict[str, float] = {}
    for field in numeric_fields:
        source_quantiles = _quantiles(_numeric(source_rows, field))
        target_quantiles = _quantiles(_numeric(target_rows, field))
        if source_quantiles and target_quantiles:
            for label, left, right in zip(("p50", "p95", "p99"), source_quantiles, target_quantiles):
                distribution_deltas[f"{field}.{label}"] = right - left
    invariant_errors = _financial_invariants(target_rows)
    passed = not (
        missing
        or unexpected
        or source_duplicates
        or target_duplicates
        or mismatches
        or referential_errors
        or invariant_errors
        or any(abs(delta) > 0.0001 for delta in aggregate_deltas.values())
    )
    evidence = (
        Evidence("row_count", f"source={len(source_rows)} target={len(target_rows)}", len(target_rows) - len(source_rows)),
        Evidence("hash", f"source={source_hash[:16]} target={target_hash[:16]}"),
        Evidence("key_coverage", f"missing={len(missing)} unexpected={len(unexpected)} duplicates={len(source_duplicates) + len(target_duplicates)}"),
    )
    return ReconciliationReport(migration_id, table, passed, len(source_rows), len(target_rows), aggregate_deltas, source_hash, target_hash, tuple(missing), tuple(unexpected), tuple(sorted(set(source_duplicates + target_duplicates))), tuple(referential_errors), tuple(invariant_errors), distribution_deltas, tuple(mismatches), missing[0] if missing else (mismatches[0] if mismatches else None), evidence)


def merkle_compare(source_rows: list[Mapping[str, Any]], target_rows: list[Mapping[str, Any]], key: str, partitions: int = 16) -> dict[str, Any]:
    def partition(rows: list[Mapping[str, Any]]) -> dict[str, list[str]]:
        buckets: dict[str, list[str]] = {str(index): [] for index in range(partitions)}
        for row in rows:
            bucket = str(int(sha256_hex(str(row.get(key)))[:8], 16) % partitions)
            buckets[bucket].append(row_fingerprint(row))
        return buckets
    left, right = partition(source_rows), partition(target_rows)
    differing = []
    for bucket in sorted(left):
        if merkle_root(left[bucket]) != merkle_root(right[bucket]):
            differing.append(bucket)
    return {"source_root": merkle_root([merkle_root(left[key]) for key in sorted(left)]), "target_root": merkle_root([merkle_root(right[key]) for key in sorted(right)]), "differing_partitions": differing}
