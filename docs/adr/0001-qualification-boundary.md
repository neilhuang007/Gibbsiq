# ADR 0001: Separate execution from qualification

Status: accepted.

Backend adapters execute workloads and return typed observations. Gibbsiq owns
acceptance contracts, statistical decisions, evidence, and regression comparison.

Discrete sampling retains the integer-valued `SampleResult` API. Model
activations use a separate observation schema with explicit dtype, shape, and
axes. This lets both workflows share evaluation tools while preserving their
data semantics.
