# CDC Gap Runbook

## Trigger

A gap is detected when normalized CDC sequence numbers contain a missing interval or when target lag exceeds policy.

## Procedure

1. Pause target consumption and record an incident with migration, table, source position, and current checkpoint.
2. Confirm the last applied sequence and the first captured sequence after the gap.
3. Validate the checkpoint checksum and migration version.
4. Re-read the source change window or durable source log.
5. Deduplicate by event ID and replay events in source order.
6. Quarantine poison events rather than dropping them.
7. Reconcile row counts, hashes, referential constraints, and financial invariants.
8. Resume only after the policy gate passes or an approver records an explicit override.

## Evidence

The incident record should include the sequence interval, checkpoint, replay event IDs, reconciliation report, and actor for each state transition. A successful replay is not proof of correctness until reconciliation passes.
