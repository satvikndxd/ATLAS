# Semantic Preservation and Epistemic Time

## Byte versus semantic equivalence

ATLAS reports byte equivalence separately from semantic equivalence. A timestamp or monetary value can change representation while preserving normalized meaning. Semantic normalization is explicit and deterministic; it does not erase timezone ambiguity or silently choose an exchange rate.

`semantic_fingerprint` normalizes whitespace, case, numeric representation, and selected timestamp formats. `semantic_merkle_root` composes semantic row fingerprints into a dataset-level root. The implementation is a reference baseline, not a universal ontology for every domain.

## Knowledge time

A temporal record carries event time, data time, and knowledge time. `atlas asof` filters by knowledge time to answer what the system could have known at a historical cutoff. It does not rewrite history using today’s knowledge.

## Uncertainty

Contradiction is represented as an evidence conflict. An assumption can be invalidated and its dependent mappings or results identified. The correct result can be `UNKNOWN` or `INCONCLUSIVE`; ATLAS does not manufacture a value to make a certificate pass.
