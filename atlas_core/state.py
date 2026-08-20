"""Durable local state primitives for checkpoints, CDC offsets, and audit history."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, TypeVar

from .contracts import AuditEntry, Checkpoint, CDCEvent, to_dict
from .fingerprint import canonical_json, sha256_hex

T = TypeVar("T")


class JsonlStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, value: Any) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(to_dict(value)) + "\n")

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]


class CheckpointStore:
    def __init__(self, path: str | Path):
        self.store = JsonlStore(path)

    def put(self, checkpoint: Checkpoint) -> None:
        self.store.append(checkpoint)

    def latest(self, migration_id: str, table: str | None = None) -> dict[str, Any] | None:
        records = [item for item in self.store.read() if item.get("migration_id") == migration_id]
        if table is not None:
            records = [item for item in records if item.get("table") == table]
        return records[-1] if records else None


class CDCLog:
    def __init__(self, path: str | Path):
        self.store = JsonlStore(path)

    def append(self, event: CDCEvent) -> None:
        self.store.append(event)

    def events(self, after_sequence: int = -1) -> list[dict[str, Any]]:
        return [item for item in self.store.read() if int(item.get("sequence", -1)) > after_sequence]

    def deduplicated(self) -> list[dict[str, Any]]:
        seen: set[str] = set()
        result: list[dict[str, Any]] = []
        for event in sorted(self.store.read(), key=lambda item: int(item.get("sequence", 0))):
            event_id = str(event["event_id"])
            if event_id in seen:
                continue
            seen.add(event_id)
            result.append(event)
        return result

    def detect_gaps(self) -> list[tuple[int, int]]:
        sequences = sorted({int(item["sequence"]) for item in self.store.read()})
        gaps: list[tuple[int, int]] = []
        for previous, current in zip(sequences, sequences[1:]):
            if current - previous > 1:
                gaps.append((previous + 1, current - 1))
        return gaps


class AuditLedger:
    """Tamper-evident append-only ledger with hash chaining."""

    def __init__(self, path: str | Path):
        self.store = JsonlStore(path)

    def append(self, actor: str, action: str, migration_id: str, old_state: str | None, new_state: str | None, reason: str, evidence: Any) -> AuditEntry:
        previous = self.store.read()[-1] if self.store.read() else None
        previous_hash = str(previous.get("entry_hash", "")) if previous else ""
        evidence_hash = sha256_hex(evidence)
        payload = {
            "actor": actor,
            "action": action,
            "migration_id": migration_id,
            "old_state": old_state,
            "new_state": new_state,
            "reason": reason,
            "evidence_hash": evidence_hash,
            "previous_hash": previous_hash,
        }
        entry_hash = sha256_hex(payload)
        entry = AuditEntry(sha256_hex({"entry": entry_hash, "time": len(self.store.read())}), actor, action, migration_id, old_state, new_state, reason, evidence_hash, previous_hash, entry_hash)
        self.store.append(entry)
        return entry

    def verify(self) -> tuple[bool, list[str]]:
        errors: list[str] = []
        previous_hash = ""
        for index, raw in enumerate(self.store.read()):
            if raw.get("previous_hash") != previous_hash:
                errors.append(f"entry {index}: previous hash mismatch")
            payload = {key: raw.get(key) for key in ("actor", "action", "migration_id", "old_state", "new_state", "reason", "evidence_hash", "previous_hash")}
            if sha256_hex(payload) != raw.get("entry_hash"):
                errors.append(f"entry {index}: entry hash mismatch")
            previous_hash = str(raw.get("entry_hash", ""))
        return not errors, errors
