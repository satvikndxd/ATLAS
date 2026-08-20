"""Deterministic fingerprints used for idempotency, audit, and reconciliation."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256_hex(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical_json(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def row_fingerprint(row: Mapping[str, Any], key_fields: Iterable[str] | None = None) -> str:
    if key_fields is None:
        value = dict(row)
    else:
        value = {field: row.get(field) for field in key_fields}
    return sha256_hex(value)


def batch_fingerprint(rows: Iterable[Mapping[str, Any]], key_fields: Iterable[str] | None = None) -> str:
    return sha256_hex([row_fingerprint(row, key_fields) for row in rows])


def merkle_root(leaves: Iterable[str]) -> str:
    """Return a deterministic binary Merkle root; duplicate the final node on odd levels."""
    nodes = [str(item) for item in leaves]
    if not nodes:
        return sha256_hex("")
    while len(nodes) > 1:
        if len(nodes) % 2:
            nodes.append(nodes[-1])
        nodes = [sha256_hex(nodes[i] + nodes[i + 1]) for i in range(0, len(nodes), 2)]
    return nodes[0]


def partition_fingerprint(rows: Iterable[Mapping[str, Any]], key: str, partitions: int = 16) -> dict[str, str]:
    buckets: dict[str, list[str]] = {str(i): [] for i in range(partitions)}
    for row in rows:
        raw_key = str(row.get(key, ""))
        bucket = str(int(sha256_hex(raw_key)[:8], 16) % partitions)
        buckets[bucket].append(row_fingerprint(row))
    return {bucket: merkle_root(values) for bucket, values in buckets.items()}
