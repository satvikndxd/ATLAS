# ATLAS Architecture

## Purpose

ATLAS is organized as a deterministic reference engine plus replaceable integration boundaries. The reference engine is intentionally runnable without a database server so that correctness properties can be tested quickly. SQL Server, PostgreSQL, SFTP, and object-store adapters are infrastructure boundaries rather than assumptions embedded in domain logic.

## Planes

| Plane | Responsibility | Current implementation |
|---|---|---|
| Control | Migration metadata, state transitions, approvals, health | ASP.NET Core scaffold and Python state machine |
| Data | Extraction, transformation, loading, checkpoints | Python migration engine and connector contracts |
| Evidence | Reconciliation, hashes, CDC replay, audit | Python reconciliation/CDC/state modules |
| Intelligence | Profiling, relationship inference, mapping evidence | Python schema module; optional reasoning is not required |
| Operations | CLI, reports, chaos, benchmarks | Python CLI and deterministic test harness |
| Acceleration | Hashing and Merkle primitives | Rust crate boundary |

The first vertical slice prioritizes correctness and replayability. A distributed queue, remote object store, and telemetry exporter can be connected behind the same contracts later without changing the transformation or reconciliation semantics.

## Delivery semantics

ATLAS explicitly documents semantics per subsystem. CDC ingestion is at-least-once. Transformation is deterministic. The reference target is idempotent by key. Reconciliation is exact for the checks it performs. The system does not claim exactly-once distributed execution.

## State and evidence

Checkpoints and audit records are append-only JSONL in the local reference path. The checkpoint stores source position, CDC offset, target state, checksum, worker identity, and migration version. The audit ledger uses a hash chain to detect changes to the recorded sequence.

## Failure model

A failure is represented as a state transition and evidence artifact. Bad records become quarantine records with original input, failure reason, stage, batch, and checksum. A fault can be retried, replayed, or escalated based on policy. High-risk cutover is never silently authorized by a heuristic.
