"""Seeded, reproducible failure injection for the ATLAS demo and tests."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Fault:
    scenario: str
    seed: int
    target: str
    parameters: dict[str, Any]


SCENARIOS = ("kill_worker", "drop_connection", "delay_database", "inject_deadlock", "corrupt_batch", "duplicate_event", "drop_event", "reorder_events", "change_schema", "fill_disk", "exhaust_pool", "increase_latency", "return_invalid_row", "crash_scheduler", "corrupt_checkpoint")


def inject(scenario: str, target: str, seed: int = 42) -> Fault:
    if scenario not in SCENARIOS:
        raise ValueError(f"unsupported chaos scenario: {scenario}")
    rng = random.Random(seed)
    parameters: dict[str, Any] = {"delay_ms": rng.randrange(25, 250), "batch": rng.randrange(0, 10), "event_sequence": rng.randrange(1, 100)}
    if scenario == "drop_event":
        parameters["drop_count"] = 1 + rng.randrange(3)
    if scenario == "reorder_events":
        parameters["window"] = 2 + rng.randrange(5)
    if scenario == "change_schema":
        parameters["change"] = rng.choice(["column_added", "column_removed", "datatype_changed"])
    return Fault(scenario, seed, target, parameters)


def run_game_day(seed: int = 42) -> dict[str, Any]:
    rng = random.Random(seed)
    faults = [inject(scenario, "migration-demo", seed + index) for index, scenario in enumerate(("kill_worker", "drop_event", "duplicate_event", "change_schema", "corrupt_batch"))]
    detected = len(faults)
    auto_remediated = sum(1 for fault in faults if fault.scenario in {"kill_worker", "drop_event", "duplicate_event", "corrupt_batch"})
    return {"seed": seed, "incidents": len(faults), "detected": detected, "auto_remediated": auto_remediated, "human_approval_required": detected - auto_remediated, "unrecovered": 0, "data_loss": 0, "faults": [fault.__dict__ for fault in faults], "note": "synthetic deterministic game day; not production evidence"}
