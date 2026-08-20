# Migration IR

ATLAS treats migration as compilation:

```text
source reality -> schema model -> semantic model -> mapping IR -> transformation IR -> validation IR -> execution plan -> runtime
```

`atlas_core.ir.MigrationIR` is serializable, fingerprinted, diffable, and versioned. It records mappings, constraints, validations, policies, risk, resource limits, dependencies, and approval requirements. `diff_ir` reports semantic mapping/policy/risk/dependency changes between plan versions.

The current optimizer boundary is intentionally a candidate-plan model. The runtime does not claim global optimality. Shadow execution returns `SIMULATED` and never mutates canonical state.
