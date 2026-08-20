"""Public-data time capsules: immutable snapshots first, live providers optional."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

from .fingerprint import sha256_hex


@dataclass(frozen=True)
class RawSnapshot:
    snapshot_id: str
    provider: str
    endpoint: str
    request_parameters: Mapping[str, Any]
    retrieved_at: str
    effective_at: str | None
    schema_version: str
    normalization_version: str
    response_hash: str
    payload: Any
    status: str = "OBSERVED"


class PublicSourceConnector(Protocol):
    provider: str
    def fetch(self, endpoint: str, parameters: Mapping[str, Any]) -> RawSnapshot: ...


class SnapshotStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, snapshot: RawSnapshot) -> Path:
        path = self.root / f"{snapshot.snapshot_id}.json"
        path.write_text(json.dumps(snapshot.__dict__, indent=2, sort_keys=True, default=str), encoding="utf-8")
        return path

    def get(self, snapshot_id: str) -> RawSnapshot:
        payload = json.loads((self.root / f"{snapshot_id}.json").read_text(encoding="utf-8"))
        return RawSnapshot(**payload)

    def list(self) -> list[str]:
        return sorted(path.stem for path in self.root.glob("*.json"))


def make_snapshot(provider: str, endpoint: str, request_parameters: Mapping[str, Any], payload: Any, retrieved_at: str, effective_at: str | None = None, schema_version: str = "v1", normalization_version: str = "v1") -> RawSnapshot:
    response_hash = sha256_hex(payload)
    snapshot_id = f"{provider.lower()}-{response_hash[:16]}"
    return RawSnapshot(snapshot_id, provider, endpoint, dict(request_parameters), retrieved_at, effective_at, schema_version, normalization_version, response_hash, payload)


def replay_public_data(store: SnapshotStore, snapshot_id: str) -> dict[str, Any]:
    snapshot = store.get(snapshot_id)
    return {"snapshot": snapshot.__dict__, "replayed": True, "status": "OBSERVED", "note": "replayed from immutable local snapshot; no live provider call"}
