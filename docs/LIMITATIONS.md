# ATLAS Limitations

ATLAS is a research-grade runnable reference implementation, not a production deployment.

| Area | Status |
|---|---|
| Python reference engine | Implemented and tested locally; canonical behavior for the current vertical slice |
| Data Genome, archaeology, epistemic ledger, semantic comparison, Migration IR | Implemented as deterministic reference primitives with unit coverage |
| React console | Implemented, built, and browser-checked in demo mode; live API wiring remains deployment work |
| .NET control plane | Production-shaped service boundaries and API routes are present; not compiled in this environment because the .NET SDK is absent |
| Rust kernels | Source-level fingerprint, semantic, and reconciliation boundaries are present; not benchmarked in this environment because the Rust toolchain is absent |
| SQL Server | Reference T-SQL schemas, stored procedure patterns, and labs are present; live integration tests require SQL Server |
| Public data | Immutable snapshot contracts are present; no live provider ingestion is claimed by default |
| Distributed runtime | Scheduler/control-plane shapes exist; no tested multi-node queue/lease deployment is claimed |
| Security | RBAC/policy and input-boundary primitives exist; TLS/mTLS, external secrets, and deployment hardening require integration |
| Benchmarks | Local synthetic reference numbers are clearly labeled; they are not production throughput claims |

Failures and gaps should become issues, regression fixtures, or new ADRs rather than being hidden behind optimistic status labels.
