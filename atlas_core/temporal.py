"""Temporal and knowledge-time helpers for as-of reconstruction."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class TemporalRecord:
    record_id: str
    event_time: str
    data_time: str
    knowledge_time: str
    payload: Mapping[str, Any]


def as_of(records: Iterable[TemporalRecord], knowledge_cutoff: str) -> list[TemporalRecord]:
    cutoff = datetime.fromisoformat(knowledge_cutoff.replace("Z", "+00:00"))
    return [record for record in records if datetime.fromisoformat(record.knowledge_time.replace("Z", "+00:00")) <= cutoff]


def temporal_order(records: Iterable[TemporalRecord]) -> list[TemporalRecord]:
    return sorted(records, key=lambda record: (record.event_time, record.data_time, record.knowledge_time, record.record_id))


def knowledge_delta(current: Iterable[TemporalRecord], historical: Iterable[TemporalRecord]) -> dict[str, Any]:
    current_ids = {record.record_id for record in current}
    historical_ids = {record.record_id for record in historical}
    return {"newly_known": sorted(current_ids - historical_ids), "not_yet_known": sorted(historical_ids - current_ids), "known_count_then": len(historical_ids), "known_count_now": len(current_ids)}
