# ATLAS Engineering Baseline

**Baseline date:** 2026-08-20 (sandbox environment)

This baseline was run before stabilization changes. A result is only marked `PASS` when the command actually ran successfully. Missing toolchains and unavailable integration infrastructure are recorded as `NOT CONFIGURED` or `SKIPPED`, not as successful tests.

| Command / subsystem | Environment | Result | Failure / reason | Severity | Next action |
|---|---|---|---|---|---|
| `python3 -m compileall -q .` | Python 3.12.3 | PASS | None | — | Keep in fast CI |
| `python3 -m pytest` | Python 3.12.3, 20 tests | PASS | None | — | Add stabilization regression tests |
| `cargo test` | Cargo/rustc 1.75.0 | PASS | 1 unit test passed | — | Add tests for semantic and reconciliation modules |
| `cargo fmt --check` | Cargo/rustc 1.75.0 | NOT CONFIGURED | `cargo-fmt` component is not installed | Medium | Install rustfmt in local/CI toolchain |
| `cargo clippy -- -D warnings` | Cargo/rustc 1.75.0 | NOT CONFIGURED | `cargo-clippy` component is not installed | Medium | Install clippy in local/CI toolchain |
| `dotnet restore` | .NET SDK absent | NOT CONFIGURED | `dotnet: command not found` | Critical | Install/pin .NET 8 SDK and compile control plane |
| `dotnet build` | .NET SDK absent | NOT CONFIGURED | `dotnet: command not found` | Critical | Same as above |
| `dotnet test` | .NET SDK absent | NOT CONFIGURED | `dotnet: command not found` | Critical | Add test project and run in CI |
| `pnpm install --frozen-lockfile` | Node 22.13.0, pnpm 11.21.0 | PASS | Lockfile accepted | — | Keep frozen install in CI |
| `pnpm build` | Node 22.13.0, pnpm 11.21.0 | PASS | Vite/TypeScript build completed | — | Add live API contract tests |
| `docker --version` | Docker absent | NOT CONFIGURED | `docker: command not found` | Critical for DB/Compose | Install Docker or use CI service containers |
| `docker compose config` | Docker absent | NOT CONFIGURED | `docker: command not found` | High | Validate Compose in CI |
| SQL Server integration | Docker absent; no live DB | SKIPPED | No disposable SQL Server instance available | Critical for connector claims | Add live-db CI profile |
| PostgreSQL integration | Docker absent; no live DB | SKIPPED | No disposable PostgreSQL instance available | High | Add connector contract suite and CI profile |

## Toolchain summary

| Tool | Detected version / state |
|---|---|
| Python | 3.12.3 |
| Rust compiler | 1.75.0 |
| Cargo | 1.75.0 |
| Rustfmt | Not installed |
| Clippy | Not installed |
| .NET SDK | Not installed |
| Node.js | v22.13.0 |
| pnpm | 11.21.0 |
| Docker | Not installed |

## Interpretation

The Python reference engine, Rust crate test path, and React build are reproducible in the current sandbox. The .NET control plane has not yet earned a local build claim. Database integration has not run. Rust test success does not imply Rust formatting or lint success because those Cargo subcommands are unavailable in the baseline environment.
