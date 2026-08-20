from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

from atlas_core.reconcile import reconcile


def run(sizes: list[int]) -> dict:
    results = []
    for size in sizes:
        rows = [{"id": index, "amount": index % 97} for index in range(size)]
        started = time.perf_counter()
        report = reconcile("benchmark", "rows", rows, list(rows), "id", numeric_fields=("amount",))
        elapsed = time.perf_counter() - started
        results.append({"rows": size, "seconds": round(elapsed, 6), "rows_per_second": round(size / elapsed if elapsed else 0, 2), "passed": report.passed})
    return {"kind": "synthetic_reference_benchmark", "python": sys.version, "platform": platform.platform(), "results": results, "caveat": "local synthetic benchmark; not production performance"}


if __name__ == "__main__":
    output = run([10_000, 100_000])
    Path("benchmarks/results.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))
