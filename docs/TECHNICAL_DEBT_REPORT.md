# ATLAS Technical Debt Report

**Assessment scope:** repository inspection before stabilization work, based on the current tree, source review, CI configuration, and toolchain discovery.

## Executive assessment

ATLAS has a valuable Python reference engine and a polished React surface, but the current repository is not yet one coherent multi-language system. The most important problem is not missing feature count; it is the existence of multiple state authorities and multiple contracts that look similar but are not connected.

The stabilization priority is therefore to establish one canonical domain vocabulary, versioned serialized contracts, one real control-plane state authority, a truthful React live/demo boundary, reproducible language builds, disposable database contract tests, and one verification command that reports skipped infrastructure instead of converting it into false success.

## Findings

| ID | Finding | Evidence | Severity | Required action |
|---|---|---|---|---|
| TD-001 | The .NET project had not been compiled in the original environment | `dotnet` was absent during the repository inventory; CI used `dotnet build --no-restore` with `continue-on-error: true` | Critical | Add a reproducible .NET 8 toolchain path, remove `continue-on-error`, and run restore/build/test in CI |
| TD-002 | The .NET API contains two migration state authorities | `AtlasStore` backs `/api/v1/migrations*`; `MigrationManager` backs `/api/v1/control/migrations*` | Critical | Consolidate routes onto one application service and one canonical migration aggregate |
| TD-003 | .NET domain records are duplicated and not versioned | `Migration`, `AtlasMigration`, `Reconciliation`, `AtlasReconciliation`, `Approval`, and `AtlasApproval` coexist | Critical | Introduce versioned API contracts and map to one domain model instead of exposing ad hoc records |
| TD-004 | Required API surface is incomplete or inconsistent | Missing direct `start`, `cutover/approve`, `jobs`, migration-scoped incidents, and policy-precheck routes; health is `/health` rather than `/api/v1/health` | High | Implement the minimum functional route set with actual backing behavior |
| TD-005 | React console is fixture-driven | UI data is defined in `main.tsx`; the connection toggle only changes the label and does not call the API | Critical | Add `VITE_API_BASE_URL`, typed client, live-mode loading/error states, and no silent fixture fallback |
| TD-006 | Cross-language contracts are not canonical | Python contracts exist, C# records are independent, TypeScript types are mostly inline, Rust has no shared serialized contract | Critical | Add versioned JSON Schema/OpenAPI contracts and generated or checked DTO mappings |
| TD-007 | SQL Server and PostgreSQL connectors are boundaries, not live adapters | `connectors.py` documents optional database drivers; no disposable live DB contract suite exists | Critical | Implement connector abstraction tests and live SQL Server/PostgreSQL adapter paths behind integration markers |
| TD-008 | SQL Server artifacts are reference labs, not measured workloads | T-SQL files exist, but no live execution, query plan capture, deadlock retry test, or throughput manifest is present | High | Add disposable SQL Server integration profile and reproducible workload tests |
| TD-009 | CI only partially enforces quality | Rust CI runs `cargo test` only; .NET build is optional and lacks restore/test; frontend build job is absent; SQL integration is absent | Critical | Split fast/full/nightly CI and make required stages truthful |
| TD-010 | No reproducible toolchain declaration exists | Python/Node versions are partly implied, but no Rust toolchain file, .NET global.json, or environment schema is present | High | Add `.tool-versions` or explicit toolchain files, `global.json`, `rust-toolchain.toml`, `.env.example`, and validation |
| TD-011 | Configuration and live-mode policy are not centralized | API base URL, authentication, database URLs, and live/demo mode are not represented in a shared validated config | High | Add a config schema with safe defaults and startup rejection for missing live requirements |
| TD-012 | Default live security posture is not enforced | .NET endpoints have no authentication/authorization middleware; CORS/TLS/secret handling is deployment work | Critical before external exposure | Keep service local-only by default and add auth/RBAC/input/CORS/audit controls before public deployment |
| TD-013 | Distributed queue/lease behavior is not implemented | Redis is present only as an optional Compose service; no worker lease aggregate or crash/reassignment integration test exists | Medium for current phase | Defer expansion until single-node state/contracts are coherent; then reuse canonical jobs/checkpoints |
| TD-014 | OpenTelemetry is not integrated end to end | Python observability primitives exist, but no .NET/React/DB exporter or collector integration is present | Medium | Add a local collector profile and correlated API-to-reconciliation trace test after API coherence |
| TD-015 | Benchmarks are synthetic/local only | Existing benchmark output explicitly labels itself as local synthetic reference data | Medium | Keep caveat; add benchmark manifests and resource metrics before any scale claim |
| TD-016 | Generated artifacts are present in the working tree | `__pycache__`, React `dist`, TypeScript build metadata, and Rust `target` appeared in the inventory | Low | Ensure ignore rules work and remove generated artifacts from repository snapshots |
| TD-017 | Documentation still contains scaffold wording | README, architecture docs, CI comments, and source comments refer to scaffold/prototype status after meaningful implementation has been added | Medium | Audit wording and replace with precise implemented/scaffolded/not-configured labels |
| TD-018 | Demo and live operation are not separated at the API boundary | `atlas demo` is deterministic, but there is no explicit live command/config state contract | High | Preserve offline demo and add a separate explicitly configured live path |

## Contract mismatches to resolve first

| Concept | Python reference | Current .NET | Current React | Stabilization decision |
|---|---|---|---|---|
| Migration | `MigrationConfig`, `MigrationState` | `Migration` and `AtlasMigration` | fixture objects | Versioned `Migration` API contract mapped from one service |
| Job | implicit engine/table work | absent in primary store | runtime fixture only | Add `MigrationJob` and `MigrationBatch` contract before queue work |
| Checkpoint | durable Python checkpoint | absent | fixture only | Keep Python as reference semantics; expose summary through API |
| CDCEvent | typed Python event | absent | fixture only | Expose lag/offset summary, not a competing CDC engine |
| Reconciliation | rich Python report | thin C# records | fixture-only report | Map a stable summary contract and preserve evidence references |
| Incident | Python chaos/report concepts | new `IncidentManager` side store | static incident list | One incident API backed by the control-plane store |
| Approval | Python governance | `ApprovalEngine` side store plus old `AtlasStore` approval bag | static approval UI | One approval service and versioned approval record |
| PolicyDecision | Python `policy_gate` | .NET `PolicyEngine` | not connected | Map reason codes and decision state across languages |
| Cutover | Python orchestrator | .NET precheck only | button-only UI | Precheck route first; approval route next; no production claim |

## Baseline gaps to record

The first baseline run must capture command, environment, result, failure, reason, severity, and next action in `docs/ENGINEERING_BASELINE.md`. At minimum, it must cover Python tests/compile, Rust test/format/clippy, .NET restore/build/test, frontend frozen-lockfile build, Docker availability, and disposable database test availability.

## Stabilization exit criteria

This report is considered materially addressed when the repository has one canonical versioned contract, one .NET migration state authority, a truthful React live/demo boundary, green Python/Rust/.NET/frontend CI stages, separated database integration stages, and a one-command verifier that reports `PASS`, `SKIPPED`, or `NOT CONFIGURED` per subsystem.
