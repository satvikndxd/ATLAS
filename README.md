# ATLAS

## Autonomous Enterprise Data Migration, Verification, Recovery & Cutover Fabric

ATLAS is a correctness-first reference implementation for migrating heterogeneous legacy data while the source system continues changing. It is designed to answer a hard systems question:

> **How can a migration system produce continuously measurable evidence of correctness while remaining resumable and diagnosable under failure?**

ATLAS is deliberately not presented as production-ready software. The repository contains a runnable deterministic reference engine, a .NET control-plane boundary, a Rust accelerator boundary, SQL Server artifacts, synthetic banking fixtures, tests, failure-injection primitives, and technical design documents. Database-specific adapters and distributed deployment are explicit extension points rather than hidden claims.

## What is implemented

| Area | Reference implementation |
|---|---|
| Deterministic migration | Batch transforms, idempotent in-memory loading, checkpoints, quarantine, resumable execution |
| Schema intelligence | Profiling, PII/identifier heuristics, schema fingerprints, drift classification, relationship proposals with evidence |
| Transformations | Bounded AST-backed DSL: `TRIM`, `UPPER`, `PARSE_DATE`, `DECIMAL`, `MAP_ENUM`, `SPLIT_NAME`, `COALESCE`, and currency normalization |
| CDC | Typed `INSERT`/`UPDATE`/`DELETE` events, deduplication, ordering, gap detection, lag measurement, deterministic replay |
| Verification | Counts, aggregates, hashes, key coverage, duplicate detection, referential checks, financial invariants, distributions, samples, Merkle-style partition localization |
| Recovery | Durable JSONL checkpoints, explicit state machine, quarantine records, seeded chaos scenarios, audit hash chain |
| Governance | Risk factors, policy gates, RBAC permissions, approval-aware cutover orchestration, PII logging denial |
| Interfaces | Python CLI, OpenAPI-oriented ASP.NET Core control-plane scaffold, file and DB connector boundaries |
| Database evidence | SQL Server legacy/target schemas, indexes, stored procedure and reconciliation artifacts, isolation/deadlock lab scripts |
| Performance boundary | Rust fingerprint/Merkle crate with a narrow FFI-compatible surface; Python remains the reference baseline |

## Architecture

```text
                         +---------------------------+
                         | ASP.NET Core Control Plane |
                         | health / migrations / API  |
                         +-------------+-------------+
                                       |
                                       v
+-------------+       +---------------+----------------+
| CLI / Demo  +------>+ Deterministic Migration Engine |
+-------------+       | planner, transforms, checkpoints |
                      +------+------------------+-------+
                             |                  |
                 +-----------v----+     +-------v--------+
                 | Connectors     |     | Evidence Layer |
                 | SQL Server     |     | reconcile      |
                 | Postgres / CSV |     | CDC / replay   |
                 | JSON / SFTP    |     | audit / reports|
                 +-----------+----+     +-------+--------+
                             |                  |
                +------------v------------------v---------+
                | Source / Target / Event / Artifact State |
                | JSONL reference store; DB adapters optional|
                +------------------------------------------+

 Python data intelligence    Rust deterministic accelerator
 profiling, schema inference hashing, fingerprints, Merkle roots
```

The reference engine uses at-least-once CDC semantics, deterministic transformations, idempotent target writes, exact reconciliation checks, and append-only audit evidence. It does not claim exactly-once distributed delivery.

## Quick start

The minimal reference path requires Python 3.11 or newer.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
python -m pytest
python -m apps.cli.atlas_cli demo --customers 25 --batch-size 10
```

The demo generates a seeded banking estate, profiles and transforms legacy-style records, executes resumable batches, persists checkpoints and audit entries, performs reconciliation, calculates a risk assessment, and prints machine-readable evidence. All generated state is placed under `.atlas/` and is safe to delete.

Useful commands:

```bash
python -m apps.cli.atlas_cli generate --seed 42 --customers 100 --output golden-datasets/generated
python -m apps.cli.atlas_cli inspect golden-datasets/generated
python -m apps.cli.atlas_cli profile golden-datasets/generated
python -m apps.cli.atlas_cli benchmark --rows 10000
python -m apps.cli.atlas_cli chaos worker-crash --seed 42
python -m apps.cli.atlas_cli chaos cdc-gap --seed 42
```

The CLI entry point is also exposed as `atlas` when the project is installed with pip.

## SQL Server reference environment

The primary enterprise reference is Microsoft SQL Server. The `sqlserver/` directory includes a deliberately inconsistent legacy schema, a normalized target schema, stored procedure patterns, reconciliation views, indexes, a deadlock lab, and transaction-isolation experiments. The SQL files are intentionally documented as reference artifacts; they have not been represented as a claim that a SQL Server instance is available in this build environment.

A future integration run should execute the scripts against SQL Server and add contract tests for the adapter. The Python engine remains usable without SQL Server.

## Correctness and evidence model

ATLAS separates a proposal from authorization. A schema relationship or mapping can be inferred with confidence and evidence, but the inference does not become a production constraint automatically. A high-risk cutover is blocked when reconciliation fails, CDC lag exceeds policy, a breaking schema change is present, raw PII logging is enabled, or approval is missing.

Every important action is designed to leave evidence:

```text
observation -> evidence -> inference -> decision -> validation -> audit record
```

The audit ledger is JSONL and hash-chained. Checkpoints include migration, job, table, batch, source position, CDC offset, target state, checksum, worker, and migration version. Quarantine records preserve the original and transformed context rather than silently dropping bad rows.

## Failure and recovery model

The reference engine supports deterministic failure injection for worker crashes, dropped events, duplicate events, schema changes, and corrupt batches. The implementation separates `PAUSED`, `RECOVERING`, `FAILED`, `ABORTED`, `ROLLED_BACK`, `VERIFIED`, and `COMPLETE`. A worker failure after a committed checkpoint can be resumed without duplicating committed target keys in the idempotent reference target.

This is a local reference model. Network partitions, SQL Server deadlock reproduction, distributed leases, queue backpressure, and multi-node scheduling require integration environments and are documented as next-stage work.

## Repository map

```text
atlas_core/                         Python reference domain engine
apps/cli/                           CLI and deterministic demo
apps/control-plane-dotnet/           ASP.NET Core control-plane scaffold
crates/fingerprint/                  Rust fingerprint/Merkle boundary
sqlserver/                           T-SQL schema, procedures, views, labs
connectors/                          Adapter boundary directories
infrastructure/                      Compose and container assets
tests/                               Unit and invariant tests
docs/                                Technical design documents
adr/                                 Architecture decision records
chaos/                               Failure scenarios and runbooks
benchmarks/                          Reproducible benchmark harness
```

## Honest limitations

This repository does not claim production scale, zero downtime, exactly-once delivery, bank-grade security, or measured SQL Server throughput. The default demo is synthetic and local. The Rust crate currently provides a narrow deterministic hashing boundary rather than a complete native accelerator. The .NET control plane is a scaffold because the build environment used for the reference verification does not include the .NET SDK. SQL Server and PostgreSQL adapters are optional and require their vendor drivers and live databases.

The project earns credibility by publishing those limitations. The next engineering priorities are SQL Server integration tests, distributed leases and queues, real CDC adapters, OpenTelemetry exporters, a web incident console, contract-version migration, and full security integration.

## License

Apache-2.0. See `LICENSE`.
