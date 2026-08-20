# ATLAS v1 Contracts

`domain.schema.json` is the canonical serialized vocabulary for the first stabilization release. Public API payloads use `schema_version: "1.0"`; internal implementation objects may contain richer fields but must map into these contracts at the API boundary.

Python is the reference semantics and the source of deterministic transformation/reconciliation behavior. .NET owns control-plane state and maps its domain services to these shapes. React consumes the API shapes through `apps/web-console/src/api.ts`. Rust remains a pure kernel and does not own migration lifecycle state.

Contract changes require a new schema version or an explicitly backward-compatible additive change. A change to identity, lifecycle enum, immutable fields, or required fields is breaking and must be documented in an ADR.
