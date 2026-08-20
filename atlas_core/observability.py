"""Dependency-free structured observability for local-first ATLAS runs."""
from __future__ import annotations

import json
import time
import uuid
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass(frozen=True)
class Event:
    type: str
    migration_id: str
    job_id: str | None = None
    batch_id: str | None = None
    worker_id: str | None = None
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def as_json(self) -> str:
        return json.dumps(self.__dict__, sort_keys=True, default=str)


class Metrics:
    NAMES = ("rows_processed_total", "rows_failed_total", "rows_reconciled_total", "bytes_processed", "migration_duration", "batch_duration", "throughput", "cdc_lag", "retry_count", "deadlocks", "connection_failures", "worker_utilization", "queue_depth", "checkpoint_latency")

    def __init__(self):
        self.counters = Counter()
        self.gauges = defaultdict(float)
        self.samples: defaultdict[str, list[float]] = defaultdict(list)

    def inc(self, name: str, value: float = 1.0) -> None:
        self.counters[name] += value

    def set(self, name: str, value: float) -> None:
        self.gauges[name] = value

    def observe(self, name: str, value: float) -> None:
        self.samples[name].append(value)

    def snapshot(self) -> dict[str, Any]:
        output: dict[str, Any] = {"counters": dict(self.counters), "gauges": dict(self.gauges), "samples": {}}
        for name, values in self.samples.items():
            ordered = sorted(values)
            output["samples"][name] = {"count": len(values), "min": min(values), "max": max(values), "p50": ordered[len(ordered) // 2], "mean": sum(values) / len(values)} if values else {}
        return output


@contextmanager
def timed(metrics: Metrics, name: str) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        metrics.observe(name, time.perf_counter() - start)


def emit(event: Event) -> None:
    print(event.as_json())
