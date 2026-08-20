# ATLAS Operations Notes

## CDC

CDC events use typed `INSERT`, `UPDATE`, and `DELETE` operations and carry an event ID, source position, table, primary key, before image, after image, schema version, timestamp, and sequence. Ingestion is at-least-once. Duplicate event IDs are removed before replay. Sequence gaps are surfaced instead of being interpreted as successful continuity. Lag is `captured_sequence - applied_sequence`, bounded below by zero.

## Reconciliation

The engine checks row counts, aggregates, deterministic fingerprints, primary-key coverage, duplicates, selected referential relationships, configurable financial invariants, numeric distribution deltas, and deterministic samples. Merkle-style partition digests localize where a large comparison diverges. A passing report means the configured checks passed; it is not a universal proof that every possible business rule is correct.

## Recovery

A migration can pause after a committed batch. The checkpoint is durable before the failure result is returned. Resume starts after the latest checkpoint and idempotently upserts committed keys. Quarantined rows remain available for revalidation or replay.

## Cutover

Cutover passes through precheck, freeze, CDC drain, final reconciliation, consistency check, approval, switch, verify, unfreeze, and monitor. Policy blocks the operation when reconciliation fails, CDC lag exceeds threshold, a breaking schema change exists, raw PII logging is enabled, or risk requires approval that has not been provided.

## Observability

Structured events carry migration, job, batch, trace, and worker identity. Metrics are collected as counters, gauges, and samples. The default reference path prints JSON events and stores audit/checkpoint JSONL; OpenTelemetry export is a documented integration boundary.
