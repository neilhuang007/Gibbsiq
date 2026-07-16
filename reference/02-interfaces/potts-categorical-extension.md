# Potts / Categorical Extension

## Sources

- Extropic hardware primitives (PBIT, PDIT, PMODE, PMOG): https://extropic.ai/hardware
- Extropic codon optimization on thermodynamic hardware (Ising/Potts sampling): arXiv:2606.17327 (June 2026)
- Third-party Potts-machine Max-k-Cut study: arXiv:2605.06425
- THRML heterogeneous node types: https://docs.thrml.ai/

## Motivation

The Ising IR restricts variables to two states. The hardware Gibbsiq targets does not:
Extropic documents categorical sampling primitives (PDIT, PMOG) alongside binary PBITs, and
two relevant 2026 optimization workloads are k-ary: codon design (arXiv:2606.17327) and
Max-k-Cut (arXiv:2605.06425) are natively Potts problems. Encoding one k-ary variable into a
binary one-hot QUBO uses k binary variables plus a one-hot constraint penalty. Those extra
variables and couplings change graph density and the sampling landscape; their effect on
mixing requires direct diagnostics rather than a universal inference from the encoding. A
binary-only result schema would require a breaking change before native categorical execution
could be represented.

## Audited Energy Convention

The implemented finite pairwise categorical model generalizes the audited Ising convention.
Each variable takes a value from an explicitly ordered finite domain $D_i$, with unary terms and
pairwise interaction tables:

$$
E(\mathbf{x}) = \mathrm{offset} + \sum_i h_i(x_i) + \sum_{i \lt j} J_{ij}(x_i, x_j)
$$

The standard Potts model is the special case $J_{ij}(a, b) = -J \, \delta_{ab}$, and a
two-category table can represent an Ising factor after an explicit category-to-spin mapping.
EVAL-EQ-020 audits this energy and its domain-wall lowering. Domain membership is exact in both
type and equality: Python aliases such as `True == 1` or `1.0 == 1` do not change a categorical
identity. Unary and pairwise tables must cover the exact typed domain product.

## Implemented Now

The result schema accepts k-ary samples so a future categorical runtime is an additive
change, not a breaking one:

- `ResultVartype` extends the result-level vartype to `SPIN | BINARY | CATEGORICAL`
  (`src/gibbsiq/result.py`); dimod's `DISCRETE` is accepted as an input alias and used on
  `to_dimod()` export.
- `SampleResult` gains `num_states`: an integer broadcast to all variables or a
  per-variable mapping (heterogeneous domains, as in codon design). Values are validated
  against `range(k)` per variable, and `num_states` is rejected for spin/binary results.
- `to_dict()` serializes `num_states` (null for spin/binary), keeping the JSON schema stable.
- The model layer stays binary: `sample_to_spin` and `normalize_vartype` reject categorical
  vartypes explicitly, so an `IsingModel` can never silently consume k-ary samples.
- Tests: `test_suite/tests/test_categorical_result.py`.
- `CategoricalModel` implements immutable ordered domains, complete unary/pairwise tables,
  canonical pair orientation, finite energies, offsets, and exact typed membership.
- `compile_domain_wall()` lowers pairwise categorical models into the canonical QUBO/Ising path,
  preserving every valid-state energy and offset. It uses $k_i-1$ adjacent wall variables for a
  domain of size $k_i$; that is minimal for this wall construction, not for unrestricted binary
  encodings.
- `ThermodynamicProgram` supports exact categorical clamps and same-type projected models.
- Tests: `test_categorical_model.py`, `test_domain_wall_encoding.py`, and
  `test_thermodynamic_program.py`.

## Deferred

- One-hot QUBO reduction bridge (both directions) for baseline comparison.
- THRML lowering to categorical node types and categorical block construction.
- Diagnostics generalization: Hamming distance, diversity, concentration observations, and
  target-aware collapse checks over k-ary state spaces.
- A native categorical Gibbs conditional/kernel verifier and analytic fixtures.

## Non-Claims

- No native categorical THRML sampler exists in this repository yet; the categorical IR,
  clamping, and binary domain-wall lowering are analysis/compiler capabilities.
- No claim is made that categorical THRML execution is faster than one-hot binary encoding
  until measured under the Stage 5 fixed-work and fixed-time protocol.
