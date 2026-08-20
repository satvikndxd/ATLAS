# ATLAS Limitation Resolution Roadmap

The limitations are not all the same type. Some are **local engineering gaps** that can be fixed immediately. Others require live databases, cloud infrastructure, credentials, security review, or measured production-like experiments. The correct approach is to remove a limitation only after the repository contains reproducible evidence for the corresponding claim.

## Resolution matrix

| Current limitation | What must be built | Evidence required before changing the wording |
|---|---|---|
| No production-scale claim | Repeatable load harness, realistic datasets, resource limits, multiple concurrency levels, long-running runs, and failure injection | Published dataset sizes, hardware, software versions, concurrency, warm/cold-cache conditions, p50/p95/p99, variance, CPU, memory, database I/O, network I/O, and reconciliation cost |
| No zero-downtime claim | Shadow migration, continuous CDC capture, source freeze protocol, final CDC drain, reconciliation, atomic traffic switch, health verification, and rollback | A live integration run showing no unplanned write gap, measured CDC lag, successful final drain, successful rollback rehearsal, and explicit supported-database scope |
| No exactly-once claim | Do not try to solve this through wording. Keep at-least-once delivery, stable event IDs, deduplication, idempotent target writes, durable offsets, and reconciliation | A formal end-to-end proof would be required for exactly-once. Until then, document at-least-once semantics and prove duplicate safety instead |
| No bank-grade security claim | Threat model, least privilege, short-lived credentials, secret manager, TLS/mTLS, PII masking, tenant isolation, approval controls, dependency scanning, SAST/DAST, penetration testing, and incident response | Security test reports, deployment configuration, key-rotation evidence, access-control tests, dependency scan results, and an external review. Do not use “bank-grade” as a substitute for these artifacts |
| No measured SQL Server throughput | Run the SQL Server connector against a real SQL Server instance. Implement parameterized extraction, bulk loading, transaction boundaries, indexes, query plans, deadlock retry, connection pooling, CDC/change tracking, and error classification | Versioned SQL Server container or managed instance, seeded dataset, exact schema and indexes, benchmark script, warm/cold cache conditions, query plans, throughput, latency, CPU, memory, I/O, deadlocks, retries, and reconciliation results |
| Public-data connector boundary | Implement one provider at a time using its official API. Start with immutable raw snapshots, request metadata, response hashes, schema versions, normalization versions, cache, retry/backoff, User-Agent, quota handling, and terms documentation | A committed provider adapter, recorded snapshot fixture, replay test that uses no network, live smoke test run with retrieval timestamp, source, endpoint, parameters, response hash, and provider policy compliance |
| React console is demo mode | Add a configurable API base URL, typed API client, authentication, loading/error states, polling or server-sent events, and views backed by `/api/v1/control/*` endpoints. Preserve demo fallback only when explicitly selected | Console integration test against the .NET service, screenshots showing live migration state, incident creation, reconciliation report, approval flow, and an explicit demo/live mode indicator |
| .NET SDK absent locally | Install the .NET 8 SDK in development or rely on the repository CI runner. Add restore/build/test commands and compile the control-plane project | Successful `dotnet restore`, `dotnet build`, and `dotnet test`; API smoke test for health, migration creation, state transition, approval, incident, reconciliation, and policy precheck |
| Rust toolchain absent / Rust not benchmarked | Install Rust/Cargo locally or use CI. Add crate tests, Criterion benchmarks, semantic fingerprint tests, reconciliation tests, and a documented Python-vs-Rust comparison harness | `cargo test`, `cargo fmt --check`, `cargo clippy -- -D warnings`, benchmark outputs with dataset size, hardware, compiler version, and methodology. Do not claim acceleration until the measured comparison exists |
| No PostgreSQL contract tests | Run PostgreSQL in Compose or CI. Implement the adapter using parameterized queries, transactions, retries, pooling, schema discovery, writes, CDC boundary, and reconciliation contract tests | The same connector contract suite passes against PostgreSQL and the in-memory reference target, with database version and configuration recorded |
| No distributed leases and queues | Pick one queue/storage implementation for a tested prototype. Implement scheduler, durable jobs, worker leases, heartbeats, timeout, retry, dead-letter queue, backpressure, draining, and recovery after worker kill | Multi-worker integration test with duplicate delivery, worker crash, lease expiry, queue backpressure, retry, dead-letter, and checkpoint resume. Document delivery semantics and failure boundaries |
| No OpenTelemetry exporters | Instrument the .NET service and Python runtime with traces, metrics, and structured logs. Propagate `migration_id`, `job_id`, `batch_id`, `trace_id`, and `worker_id`. Export to a local collector in Compose | Collector receives spans/metrics/logs; a documented dashboard or trace screenshot shows a migration across API, scheduler, worker, database operation, CDC, and reconciliation |
| No deployed control-plane/console origin | Containerize the .NET service and React console, configure HTTPS, CORS, API base URL, health checks, secret injection, non-root users, pinned images, migration strategy, and rollback | Reproducible deployment with health checks, logs, database connectivity, authentication, a console-to-API smoke test, and a documented rollback procedure |

## Recommended execution order

### 1. Make all language builds green

Install the .NET SDK and Rust toolchain in the local developer environment and CI. Add one command per language:

```bash
python3 -m pytest
cd crates/fingerprint && cargo test && cargo fmt --check && cargo clippy -- -D warnings
cd apps/control-plane-dotnet && dotnet restore && dotnet build
cd apps/web-console && pnpm install --frozen-lockfile && pnpm build
```

This should happen first because it prevents the repository from presenting source-level boundaries that have never compiled together.

### 2. Add live database contract tests

Run SQL Server and PostgreSQL in CI or an isolated integration environment. Keep the current in-memory tests as fast unit tests, but add a marked integration suite for schema discovery, extraction, transformation, idempotent load, transaction rollback, retry, deadlock classification, CDC offsets, and reconciliation. Every live test should be seeded and disposable.

### 3. Connect the console to the control plane

Create a shared TypeScript API contract for migrations, workers, incidents, reconciliation, approvals, and cutover prechecks. Add a `Demo data` / `Live control plane` switch that is truthful: demo mode uses deterministic fixture data; live mode shows connection errors instead of silently falling back. Add an API base URL environment variable and CORS configuration.

### 4. Add distributed execution only after the single-node semantics are stable

The queue, lease, and worker prototype must reuse the existing checkpoint and idempotency contracts. Do not introduce a queue merely for architectural appearance. The first distributed test should kill a worker after a committed checkpoint, let another worker acquire the lease, replay the batch, and prove that target keys are not duplicated.

### 5. Add observability before scale claims

Instrument the system before benchmarking. A benchmark without traces and resource measurements cannot explain a regression or distinguish database, network, serialization, and reconciliation cost.

### 6. Build a real benchmark matrix

Use a fixed seed and record the complete run manifest. Benchmark the Python reference, Rust kernel, and database-backed path separately. Compare naive row-by-row verification with partition fingerprints and semantic Merkle localization. Publish failures and weak results as well as successful ones.

### 7. Add security controls before external exposure

Do not expose the API publicly before authentication, authorization, secret management, TLS, audit verification, and input validation are integrated. The React console should never contain database credentials or provider API keys.

## What should remain a limitation

The phrase **exactly-once delivery** should remain a limitation unless ATLAS has a defensible end-to-end proof covering source capture, transport, checkpoint commit, target commit, retries, failover, and reconciliation. In practice, the stronger and more honest claim is:

> ATLAS supports at-least-once capture with stable event IDs, deduplication, idempotent target writes, durable checkpoints, and reconciliation evidence.

Similarly, **zero downtime**, **bank-grade security**, and **production scale** should remain out of the README until the repository contains measured, reviewed evidence for narrowly defined supported environments. The goal is not to delete the limitations quickly; it is to replace them with precise supported-scope statements.

## Definition of done for the next release

The next release can narrow the current limitations when all of the following are true:

1. Python, Rust, .NET, and React builds pass in CI.
2. SQL Server and PostgreSQL contract suites pass against disposable live databases.
3. The React console can operate against the .NET API and visibly reports live or demo mode.
4. A distributed worker prototype survives worker termination and lease expiry without duplicate canonical state.
5. OpenTelemetry traces connect API, scheduler, worker, database operation, CDC, and reconciliation.
6. Benchmark artifacts include complete methodology and resource measurements.
7. Security tests cover RBAC, input validation, secret handling, PII logging restrictions, and unauthorized cutover.
8. The README changes from broad limitations to a narrow, measured support matrix rather than broad production claims.
