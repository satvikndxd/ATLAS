# ATLAS Support Matrix

The matrix distinguishes reference semantics, compiled subsystem status, live integration, demo behavior, and known limitations. `Tested` means a reproducible test exists and passed in the recorded environment; it does not mean production readiness.

| Feature | Python | SQL Server | PostgreSQL | .NET | Rust | Live | Demo | Tested | Known limitations |
|---|---|---|---|---|---|---|---|---|---|
| Schema profiling | Implemented reference | Metadata adapter boundary | Metadata adapter boundary | API contract only | Not applicable | No live DB in sandbox | Yes | Yes, Python/file | Vendor metadata and permissions require live fixtures |
| Migration planning | Implemented | Planned connector execution | Planned connector execution | Exposes migration state and jobs | Not applicable | Partial control-plane state | Yes | Yes, Python and .NET services | Plan execution is not yet DB-backed |
| Transform DSL | Implemented deterministic AST | Target adapter boundary | Target adapter boundary | Orchestration boundary | Not applicable | Partial | Yes | Yes, Python | Cross-language AST execution is not duplicated |
| Checkpoints | Implemented durable JSONL reference | Database persistence planned | Database persistence planned | Summary state boundary | Not applicable | Partial | Yes | Yes, Python | No distributed checkpoint store yet |
| CDC | Implemented at-least-once reference/replay | Live change capture not configured | Planned | Lag/offset API boundary | Not applicable | No | Yes | Yes, synthetic Python | Stable event IDs, deduplication, and replay are not a vendor CDC connector |
| Reconciliation | Counts, hashes, aggregates, invariants, Merkle-style reference | T-SQL artifacts; live query tests pending | Contract boundary | Reconciliation records and API | Semantic/partition kernels | Partial | Yes | Python, .NET unit | Live query plans and throughput pending |
| SQL transactions | In-memory transaction reference | Adapter implementation boundary | Adapter implementation boundary | Not applicable | Not applicable | No | Yes | In-memory contract suite | Requires vendor drivers and disposable DBs |
| Idempotent load | InMemoryConnector | SQL adapter path present but unverified live | PostgreSQL adapter path present but unverified live | Job API only | Not applicable | Partial | Yes | In-memory contract suite | DB dialect-specific upsert testing pending |
| Incidents | Python chaos/report primitives | Not applicable | Not applicable | Implemented in-memory service/API | Not applicable | Local API only | Yes | .NET unit tests | Persistent incident repository and auth pending |
| Approvals/policy | Python governance | Not applicable | Not applicable | Implemented service/API | Not applicable | Local API only | Yes | .NET unit tests | No production identity provider integration |
| Cutover precheck | Python orchestration | Not live | Not live | Policy-backed precheck endpoint | Not applicable | Local API only | Yes | Python/.NET unit | Not a zero-downtime production cutover |
| Rust fingerprints | Fallback comparison available | Not applicable | Not applicable | Not invoked by API yet | Compiled/tested/fmt/clippy | No native deployment | Yes | `cargo test`, fmt, clippy | No FFI or measured Python-vs-Rust benchmark yet |
| React operator console | Consumes fixture/reference concepts | Not applicable | Not applicable | Typed API client/live mode | Not applicable | Live mode implemented; requires API URL/auth | Demo and live explicit | Frontend build; browser demo check | Not all operator mutations are wired yet |
| Observability | Structured reference primitives | Exporter pending | Exporter pending | Scheduler logs only | Not applicable | No collector in sandbox | Synthetic metrics | Python unit | End-to-end OpenTelemetry trace pending |
| Security | Policy/RBAC reference | Deployment hardening pending | Deployment hardening pending | API-key live-mode gate, CORS | Not applicable | Local live-mode gate | Demo no credentials | Unit/smoke | Full IdP, TLS/mTLS, secret manager, DAST pending |

## Current truthful release scope

The stable release scope is a tested Python reference engine, compiled/tested Rust kernels, compiled/tested .NET control-plane services with versioned snake_case JSON, a React console with explicit demo/live behavior, and offline connector contracts. SQL Server/PostgreSQL live integration, distributed worker execution, external telemetry, and production deployment remain clearly marked as integration work.
