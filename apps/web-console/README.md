# ATLAS Operator and Research Console

This is the TypeScript/React console for ATLAS. It is intentionally not a generic SaaS CRUD dashboard. The interface is shaped around the questions the runtime must answer: what changed, what is known, what is inferred, what contradicted the inference, what failed, what was the blast radius, and whether the final state is certifiable.

## Visual direction

The visual system is **Stripe-inspired** rather than copied: a light workspace, restrained indigo accent, navy typography, thin borders, rounded cards, high information density, subtle charts, strong hierarchy, and compact operator controls. The UI avoids fake dramatic animations and labels synthetic/demo data explicitly.

## Views

| View | Purpose |
|---|---|
| Overview | Preservation, integrity debt, CDC lag, proof coverage, runtime state, and operator load |
| System archaeology | Evidence-backed findings, epistemic state, candidate relationships, business-rule clues, and highest-value human questions |
| Data Genome | Entity/relationship model, multidimensional distance, semantic types, invariants, and confidence |
| Migration runtime | Proof-carrying execution, pipeline phases, plan strategy, progress, shadow result, and certificate gates |
| Evidence ledger | Claims, freshness, contradictions, assumptions, and knowledge-time context |
| Incidents | Symptoms, severity, blast radius, timeline, hypothesis, and recovery actions |
| Research lab | Reproducibility, benchmark results, forecast calibration, and experiment catalog |

## Running locally

```bash
pnpm install
pnpm dev
pnpm build
```

The console currently renders deterministic demo data. The .NET control-plane API is the integration boundary for live migration state, approvals, incidents, reconciliation reports, and policy checks. Connecting the UI to a live API requires a deployment-specific origin/proxy configuration; the console does not claim live control-plane connectivity merely because the API routes exist.
