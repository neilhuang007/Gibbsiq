# Potts / Categorical Extension

## Sources

- Extropic hardware primitives (PBIT, PDIT, PMODE, PMOG): https://extropic.ai/hardware
- Extropic codon optimization on thermodynamic hardware (Ising/Potts sampling): arXiv:2606.17327 (June 2026)
- Third-party Potts-machine Max-k-Cut study: arXiv:2605.06425
- THRML heterogeneous node types: https://docs.thrml.ai/

## Motivation

The Ising IR restricts variables to two states. The hardware Gibbsiq targets does not:
Extropic documents categorical sampling primitives (PDIT, PMOG) alongside binary PBITs, and
the strongest optimization workloads demonstrated on THRML-style sampling in 2026 are
k-ary — codon design (arXiv:2606.17327) and Max-k-Cut (arXiv:2605.06425) are natively
Potts problems. Encoding k-ary variables into binary one-hot QUBO form inflates the variable
count by a factor of k and adds penalty terms that create exactly the frustrated landscapes
where Gibbs sampling mixes poorly. A library that can only represent binary results would
require a breaking schema change at the moment categorical support matters most.

## Target Energy Convention

The planned categorical model generalizes the audited Ising convention. Each variable takes
values $x_i \in \{0, \ldots, k_i - 1\}$ with per-state linear terms and pairwise interaction
tables:

$$
E(\mathbf{x}) = \mathrm{offset} + \sum_i h_i(x_i) + \sum_{i \lt j} J_{ij}(x_i, x_j)
$$

The standard Potts model is the special case $J_{ij}(a, b) = -J \, \delta_{ab}$, and the
Ising convention is recovered at $k_i = 2$. This convention is a design target, not yet an
audited contract: before any `PottsModel` IR lands, the convention and its single-site
conditional must be added to `reference/08-evaluation/equation-audit.md` and covered by
analytic fixtures, exactly as was done for the Ising path.

## Implemented Now (Schema Readiness)

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

## Deferred

- `PottsModel` / categorical IR with deterministic state ordering and offset preservation.
- One-hot QUBO reduction bridge (both directions) for baseline comparison.
- THRML lowering to categorical node types and categorical block construction.
- Diagnostics generalization: Hamming distance, diversity, concentration observations, and
  target-aware collapse checks over k-ary state spaces.
- Equation-audit entries and analytic fixtures for the categorical conditional.

## Non-Claims

- No categorical sampler exists in this repository yet; only the result contract is ready.
- No claim is made that categorical THRML execution is faster than one-hot binary encoding
  until measured under the Stage 5 fixed-work and fixed-time protocol.
