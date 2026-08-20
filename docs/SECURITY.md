# ATLAS Security and AI Safety

## Security objectives

ATLAS handles schemas, identifiers, account data, transaction data, and migration controls. The reference implementation therefore treats source metadata and row content as untrusted. Raw PII is not allowed in structured debug output by policy. Database identifiers are validated before interpolation, while values must be parameterized by vendor adapters.

## Roles

The reference RBAC model defines `ADMIN`, `MIGRATION_ENGINEER`, `OPERATOR`, `AUDITOR`, `READ_ONLY`, and `APPROVER`. Authorization is checked before sensitive operations; approval is separate from authorization. A user who can plan a migration does not automatically have permission to force cutover.

## AI boundary

ATLAS can later accept optional model suggestions for schema mapping or incident explanation, but the model must produce a typed proposal. The proposal passes deterministic validation and policy before any approved tool is called. Schema comments, data fields, documentation, and operator notes are treated as untrusted text and cannot authorize SQL, deletion, or cutover.

```text
untrusted metadata -> proposal -> typed contract -> deterministic validator -> policy -> approved operation
```

There is no direct `LLM -> arbitrary SQL -> production` path.

## Threat model

The documented attack surfaces are the source DB, target DB, control API, workers, queues, artifact storage, audit storage, operator interface, optional AI provider, prompts, and migration configuration. Important threats include credential theft, SQL injection, malicious schemas, poisoned data, prompt injection, privilege escalation, replay attacks, audit tampering, unauthorized cutover, and data exfiltration.

## Production gaps

Short-lived credentials, mTLS, external secret management, signed plans, database-level tenant isolation, and a complete web console require deployment-specific integration. This repository does not claim those controls are complete merely because the domain model names them.
