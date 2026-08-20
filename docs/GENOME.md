# Data Genome

A Data Genome describes an ecosystem beyond its tables. It includes entities, relationships, constraints, temporal behavior, mutation velocity, distributions, identity structure, schema history, semantic types, business rules, invariants, provenance, failure history, access patterns, dependencies, and uncertainty.

The reference implementation stores this model in `atlas_core.genome.DataGenome`. `genome_distance` returns named components rather than one unexplained magic score: schema, entity, relationship, temporal, distribution, semantic, invariant, and behavioral distance. Each component includes its computation method.

Genome objects are epistemically marked. A derived genome is not a claim that every relationship or rule is observed. Archaeology findings retain confidence and counter-evidence so a user can review uncertain identity or lifecycle inferences before approving a mapping.
