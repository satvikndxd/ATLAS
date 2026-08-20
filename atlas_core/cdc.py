"""Change-data-capture primitives with explicit at-least-once semantics."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .contracts import CDCEvent, Operation
from .fingerprint import sha256_hex


class CDCError(ValueError):
    pass


def make_event(table: str, primary_key: str, operation: Operation, before: Mapping[str, Any] | None, after: Mapping[str, Any] | None, sequence: int, schema_version: str = "v1", timestamp: str = "") -> CDCEvent:
    event_id = sha256_hex({"table": table, "pk": primary_key, "op": operation.value, "sequence": sequence, "after": after})
    return CDCEvent(event_id, str(sequence), table, primary_key, operation, before, after, timestamp or "", schema_version, sequence)


def normalize_events(events: Iterable[CDCEvent | Mapping[str, Any]]) -> list[CDCEvent]:
    result: list[CDCEvent] = []
    for raw in events:
        if isinstance(raw, CDCEvent):
            result.append(raw)
        else:
            result.append(
                CDCEvent(
                    event_id=str(raw["event_id"]),
                    source_position=str(raw["source_position"]),
                    table=str(raw["table"]),
                    primary_key=str(raw["primary_key"]),
                    operation=Operation(str(raw["operation"])),
                    before=raw.get("before"),
                    after=raw.get("after"),
                    timestamp=str(raw.get("timestamp", "")),
                    schema_version=str(raw.get("schema_version", "v1")),
                    sequence=int(raw["sequence"]),
                )
            )
    return sorted(result, key=lambda event: (event.sequence, event.event_id))


def deduplicate(events: Iterable[CDCEvent]) -> list[CDCEvent]:
    seen: set[str] = set()
    result: list[CDCEvent] = []
    for event in normalize_events(events):
        if event.event_id not in seen:
            seen.add(event.event_id)
            result.append(event)
    return result


def detect_gaps(events: Iterable[CDCEvent]) -> list[tuple[int, int]]:
    sequences = sorted({event.sequence for event in deduplicate(events)})
    return [(left + 1, right - 1) for left, right in zip(sequences, sequences[1:]) if right - left > 1]


def lag(captured_sequence: int, applied_sequence: int) -> int:
    return max(0, captured_sequence - applied_sequence)


def replay(initial_state: Mapping[str, Mapping[str, Any]], events: Iterable[CDCEvent], strict: bool = True) -> dict[str, dict[str, Any]]:
    """Apply events idempotently; replaying the same log twice is stable."""
    state = {str(key): dict(value) for key, value in initial_state.items()}
    seen: set[str] = set()
    for event in deduplicate(events):
        if event.event_id in seen:
            continue
        seen.add(event.event_id)
        key = str(event.primary_key)
        if event.operation == Operation.INSERT or event.operation == Operation.UPDATE:
            if event.after is None:
                if strict:
                    raise CDCError(f"{event.operation} event {event.event_id} has no after image")
                continue
            state[key] = dict(event.after)
        elif event.operation == Operation.DELETE:
            state.pop(key, None)
    return state
