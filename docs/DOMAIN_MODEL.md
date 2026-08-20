# ATLAS Canonical Domain Model

ATLAS has one domain vocabulary. Python is the reference semantics; .NET owns orchestration and control-plane state; Rust owns deterministic performance kernels; React consumes versioned API contracts and does not define a competing domain.

## Contract rules

Every public object includes `schema_version` and a stable identity. Immutable fields are never changed in place; mutable fields are state transitions or append-only evidence. Internal Python dataclasses may carry richer implementation fields, but API serialization uses the versioned schemas under `contracts/v1/`.

| Concept | Identity | Lifecycle | Immutable fields | Mutable fields | Invariants |
|---|---|---|---|---|---|
| Migration | `migration_id` | `DRAFT → PLANNED → RUNNING → PAUSED/RECOVERING → RECONCILING → VERIFIED → CUTOVER_READY → COMPLETED` or failure terminal | source, target, creation time, schema version | state, plan version, progress, timestamps | one active state; terminal states cannot resume without a new execution |
| MigrationPlan | `plan_id` | `PROPOSED → APPROVED → SUPERSEDED` | plan fingerprint, source/target versions, mappings, dependencies | approval metadata, supersession reference | fingerprint changes when executable content changes |
| MigrationJob | `job_id` | `QUEUED → CLAIMED → RUNNING → COMPLETED/FAILED/EXPIRED/REASSIGNED` | migration, table, partition, creation time | lease, attempt, worker, progress, status | one active lease; attempts are monotonic |
| MigrationBatch | `batch_id` | `READY → RUNNING → COMMITTED/QUARANTINED/FAILED` | source range, input fingerprint | checkpoint, target fingerprint, retry metadata | committed batch is idempotently replayable |
| Checkpoint | `checkpoint_id` | append-only | migration, job, batch, source position, checksum | none | checksum covers source position and committed target state |
| CDCEvent | `event_id` | `CAPTURED → APPLIED/DEDUPLICATED/QUARANTINED` | event id, source position, operation, payload hash | apply status, target position, error | stable event IDs and at-least-once semantics |
| Reconciliation | `reconciliation_id` | `RUNNING → PASSED/FAILED/INCONCLUSIVE` | migration, table, source/target snapshot fingerprints | gate results, evidence, completion time | PASS requires all configured gates to pass |
| Incident | `incident_id` | `OPEN → ACKNOWLEDGED → MITIGATED → RESOLVED` or `ESCALATED` | title, source, creation time | status, severity, hypothesis, actions, resolution | resolved incident remains audit evidence |
| Execution | `execution_id` | `CREATED → STARTED → PAUSED/FAILED → COMPLETED` | migration, plan fingerprint, execution mode | workers, metrics, state, timings | one execution references exactly one plan fingerprint |
| Approval | `approval_id` | `PENDING → APPROVED/REJECTED/EXPIRED` | operation, migration, requester, request time | approver, decision, reason | approval cannot authorize a different plan fingerprint |
| PolicyDecision | `decision_id` | `EVALUATED → OVERRIDDEN/EXPIRED` | policy version, inputs, decision time | override metadata | deny reasons are preserved |
| Artifact | `artifact_id` | `CREATED → VERIFIED/REJECTED/EXPIRED` | type, content hash, producer, schema version | verification metadata | content hash is immutable |
| SchemaVersion | `schema_version_id` | `DISCOVERED → APPROVED/SUPERSEDED` | source, version, fingerprint | approval, drift classification | fingerprint identifies the exact schema snapshot |
| Mapping | `mapping_id` | `PROPOSED → REVIEW_REQUIRED → APPROVED/REJECTED/SUPERSEDED` | source/target fields, transformation, evidence hash | status, confidence, approval | approved mapping references a fixed schema and plan version |
| Transformation | `transformation_id` | `DRAFT → VALIDATED → APPROVED` | AST/expression, input/output types, version | validation result, author, approval | execution is deterministic for identical input and version |
| Certification | `certification_id` | `IN_PROGRESS → CERTIFIED/REJECTED/EXPIRED` | migration, plan, gate configuration | gate results, expiry, approver | certification cannot be certified when a required gate is failed |

## State authority

The Python reference engine owns deterministic transformation, checkpoint, CDC, and reconciliation semantics. The .NET control plane owns migration/job/approval/incident orchestration state and persists it through its configured repository. The React console reads the .NET API. Rust functions are invoked as pure kernels and do not own migration state.

## Delivery semantics

ATLAS uses **at-least-once capture** with stable event IDs, deduplication, idempotent target writes, durable offsets, and reconciliation. Exactly-once distributed delivery is not part of the current contract.
