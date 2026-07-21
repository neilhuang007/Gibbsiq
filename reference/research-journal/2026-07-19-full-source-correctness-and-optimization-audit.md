# 2026-07-19 - Full Source Correctness And Optimization Audit

## Paper Hook

This audit supplies threats-to-validity evidence for the evaluation contract: after two
exhaustive 2026-07-15 passes, a fresh whole-tree sweep still finds a serialization regression
introduced by the post-audit commit and a typed-identity hole on a path the earlier passes
never exercised. Both defects live at boundaries between two internally consistent
conventions, which supports the paper's claim that convention seams, rather than single
formulas, are the dominant residual defect class.

## Scope And Method

The pass covers all 24 modules under `src/gibbsiq` at base
`cdd0a58` with a clean working tree. Eight bounded read-only subagents audited disjoint
module clusters: core IR and conversions; the THRML runtime; diagnostics; blocks, cluster
moves, and the reference sampler; oracle, bridge, evaluation, and exact distribution; the
thermodynamic program IR, categorical model, domain-wall lowering, and result schema;
quantization, verification, and inspector; topology, communication profile, and hardware
assessment. Each subagent treated comments, docstrings, and journal claims as hypotheses,
rederived the governing equations, and verified behavior with independent scratch-script
enumeration and purpose-built reference implementations under the session scratchpad. The
repository test suite was deliberately excluded as an evidence source. The coordinator read
the full `cdd0a58` source diff independently, reproduced every claimed defect before
accepting it, rejected one finding whose premise failed direct verification, and confirmed
the one analytic claim (the total-variation extremal) by rederivation.

## Confirmed Defects

1. `ThermodynamicProgram` serialization round-trip regression, medium severity, introduced
   by `cdd0a58` (`program.py:261-264` interacting with `program.py:292-297`). For a frozenset
   metadata value containing non-ASCII strings, `from_dict(to_dict())` raises
   `ValueError: encoded label must use its canonical typed representation`. `_encode_value`
   sorts frozenset items by `_canonical_json`, whose `json.dumps` default escapes non-ASCII,
   while the `_decode_label` canonical-representation check re-encodes through
   `encode_variable_label`, whose `_encoded_label_sort_key` keeps non-ASCII raw
   (`model.py:27-28`). Members whose escaped and raw orderings disagree (for example
   `{"é", "f"}`) produce two different item orders and the byte-equality check rejects the
   payload the same class produced. The failure is loud; no silent corruption path exists.
   Coordinator reproduction: `metadata={"tags": frozenset({"é", "f"})}` on a one-variable
   Ising program fails the round trip while the all-ASCII control passes. Fix direction:
   sort `_encode_value` frozenset items with `_encoded_label_sort_key` so the emitted order
   equals the canonical label order the decoder recomputes.

2. Structured-QUBO diagonal alias merge, medium severity (`conversions.py:271`). In the
   structured input path, a diagonal `(i, i)` entry whose label is Python-equal but
   type-distinct from an existing linear-term label folds into that label's bucket because
   `linear_terms` is a plain dict keyed by the raw label. Coordinator reproduction:
   `compile_qubo({"linear": {1: 3.0}, "quadratic": {(1.0, 1.0): 5.0}})` yields the
   one-variable model `variables=(1,)`, `linear={1: 4.0}`, `offset=4.0`; the boolean variant
   behaves identically. Exact typed-label identity requires two distinct variables or a
   rejection. The off-diagonal path fails closed for the same aliasing through
   `_resolve_variables` and the uniqueness gate, confirmed by the control
   `compile_qubo({"quadratic": {(1, 1.0): 2.0}})` raising `variables must be unique`; the
   diagonal merge happens before variable resolution, so only one label reaches the gate.
   Flat-QUBO and Ising parsing are unaffected.

## Rejected Finding

A subagent reported that `__init__.py` `__all__` fails Ruff RUF022 and framed it as a CI
mismatch. Direct verification shows `pyproject.toml` selects only `E4`, `E7`, `E9`, `F`,
and `B`, so RUF022 never runs in CI and the project-config `ruff check` passes clean. What
remains is the CLAUDE.md sorted-list convention: `PROGRAM_SCHEMA_VERSION` sits inside the
PascalCase block instead of the position a strict sort assigns. Recorded as a convention
nit, severity low.

## Observations Without Correctness Impact

- `communication_profile.py` uses the field name `paper_pair_tau_proxy_seconds` for two
  different quantities: `2*c_ab/f_comm` per pair (`communication_profile.py:509-512`) and
  the `num_colors`-scaled `_clock_proxies` value at profile level
  (`communication_profile.py:566-571`). Both values are individually correct and no code
  consumes them interchangeably; the shared name invites a reader to expect the profile
  value to equal the per-pair maximum, from which it differs by exactly the color factor.
- `quantization.py:322` reports `total_variation_upper_bound = tanh(epsilon)`. The tight
  bound under a pointwise state-energy error of at most `epsilon` is `tanh(epsilon/2)`:
  maximizing total variation over the mass fraction `a` receiving log-weight `+epsilon`
  against `1-a` receiving `-epsilon` has its extremum at `a = 1/(sqrt(r)+1)` with
  `r = exp(2*epsilon)`, giving `TV = (sqrt(r)-1)/(sqrt(r)+1) = tanh(epsilon/2)`. The
  coordinator rederived this and a 4000-model sweep confirms realized TV never exceeds
  `tanh(epsilon/2)`. The shipped bound therefore dominates every realized value and stays
  correct; tightening it requires an `equation-audit.md` change first.
- `benchmark_oracle.py:175-191` routes structurally invalid knapsack witnesses (duplicate
  index, out-of-range index, over-capacity) to the difference code `witness_not_optimal`
  rather than `invalid_witness`, which is reserved for verifier exceptions. Acceptance
  behavior is unaffected. `score_candidate` also assumes complete `expected` blocks; all 27
  shipped fixtures are complete, so the latent `KeyError` is unreachable from candidates.
- `diagnostics.py:215` and `diagnostics.py:243-252` inherit different constant-trace gates
  from arviz: ESS applies an absolute range gate at `1e-15` while split R-hat tests exact
  zero variance, so the two estimators can disagree on traces whose absolute spread lies in
  the open sliver below `1e-15`. Both ports are faithful to their sources and the
  constant-trace non-negotiable holds. Separately, a finite energy trace of magnitude near
  `1.5e154` raises `ValueError` in `_variance` because the raw variance exceeds binary64;
  the ratio paths degrade correctly and the no-NaN/Infinity serialization contract holds.
- `thrml_runtime.py:572` `_replica_exchange_log_ratio` serves only the contract tests; the
  production exchange uses the lowered per-beta log densities, which is the EVAL-EQ-014
  general form. A warmup ladder ending exactly at the target beta lowers the target program
  twice; the second call is idempotent. The post-warmup energy evaluations at
  `thrml_runtime.py:630-632` establish the list shapes the read loop assigns into by index.
- `reference_sampler.py:169-185` recomputes fields in `O(|E|)` per site by design; the
  module documents itself as an auditability-first oracle.

## Independent Re-Derivations And Negative Results

- Gibbs conditional `sigmoid(-2*beta*gamma)` confirmed three independent ways: hand
  two-branch Boltzmann ratio, 2000-state comparison against
  `model.conditional_probability` with zero deviation, and 4000-instance brute force on the
  conversions path. QUBO to Ising coefficients, offset preservation, mirrored-pair
  summation, and self-loop folding confirmed over roughly 10,000 enumerated instances at
  `1e-9` tolerance with `math.fsum` cancellation cases included.
- The production replica-exchange acceptance equals
  `(beta_left - beta_right) * (E_left - E_right)` through the lowered densities to
  `3.6e-15` over all three-spin states and four beta pairs, with offset invariance
  structural. Pairing parity, two-replica forcing, sweep accounting against both 2026-07-14
  journal fixtures, per-chain PRNG stream separation, and cold-slot retention all hold.
- The isoenergetic cluster move preserves the joint Boltzmann law: exact pushforward of the
  two-replica target under the kernel matches the target to `2.8e-17` over 30 random
  models, and the combined-energy invariant holds with general fields to `1.8e-15` over
  421 selections. DSATUR block construction is deterministic under five `PYTHONHASHSEED`
  values and 20 insertion shuffles and achieves the chromatic number on every reference
  graph tried.
- Geyer tau/ESS, plain split R-hat, and rank-normalized plus folded R-hat match
  independent references to at most `1.1e-11` (ESS accumulation noise) and `4.4e-16`
  (R-hat family), the AR(1) `phi = 0.8` chain gives `tau = 8.979` against the theoretical
  `9.0`, and multiplying every input by scale factors from `1e-14` to `1e150` leaves tau,
  ESS, and both R-hat variants bit-for-bit identical, confirming the common-scale
  cancellation is exact.
- The strict oracle and evaluator survived an adversarial battery: infeasible and
  sub-optimal witnesses fail with the documented codes, degeneracy is required in the
  strict path and optional-but-checked in the sampler path, the knapsack lexicographic rule
  rejects heavier value-optimal witnesses, unordered-list comparison is a bipartite
  maximum matching that preserves multiplicity across `1` and `1.0`, the bridge produces
  passing candidates with the `expected` block overwritten, and the CLI tolerance reaches
  both comparison paths as an absolute tolerance.
- Domain-wall lowering reproduces every categorical energy across 400 enumerated models
  with a bijection between valid words and categorical states, and invalid words carry
  exactly the declared penalty times the violation count, proven by differencing two
  penalty values over 4818 invalid words. Program projection preserves energy state-by-state
  over 120 programs including full clamping to a zero-variable model; the
  `reversed_pair_count` first-N reconstruction is consistent across `relabel_variables`,
  `to_dict`, and `from_dict` because canonicalization stores orientation only as a count.
- Quantization bounds dominate realized state-energy error (tight to `3.6e-15`) and
  realized total variation over a 4000-model sweep spanning both overflow policies and both
  rounding modes. Kernel verification catches non-stochastic rows, wrong stationary laws,
  and non-reversible kernels claimed reversible, and the three-spin even-parity
  counterexample still fails all eight full-state intervals while passing marginal, pair,
  and energy observables. Topology distances match independent BFS on seven grid shapes and
  five explicit graphs; the exact chain-order search enumerates `n!` orders, or `n!/2`
  under the losslessly reversal-symmetric pin reduction, and returns the true argmin in
  every brute-forced case; the hardware accumulator assessment feeds the post-quantization
  implemented model exactly in the branch the 2026-07-15 audit prescribed.

## Decisions And Rejected Alternatives

1. Findings enter the report only after coordinator reproduction or rederivation. One
   subagent claim (the RUF022 CI framing) failed that gate and is recorded as rejected.
2. No code changes accompany this audit. The session's instruction is detection and
   verification; the two confirmed defects and the tightening opportunity route to a
   remediation task rather than an in-audit patch.
3. The `tanh(epsilon)` bound stays as shipped for now because it is a valid dominating
   bound and its contract lives in `equation-audit.md`, which must change before the code.

## Follow-Up

- Fix the `_encode_value` frozenset item ordering to `_encoded_label_sort_key` and add a
  non-ASCII frozenset metadata round-trip regression case.
- Route structured-QUBO diagonal labels through the exact typed-label index before the
  linear fold, with alias-diagonal rejection tests mirroring the off-diagonal gate.
- Optionally tighten the quantization TV bound to `tanh(epsilon/2)` via an
  `equation-audit.md` update, rename one of the two `paper_pair_tau_proxy_seconds` fields,
  align the knapsack witness difference codes, and move `PROGRAM_SCHEMA_VERSION` to the
  strict-sort position in `__all__`.

## Verification

Coordinator reproductions executed against `src` on CPython at base `cdd0a58`: the
non-ASCII frozenset round trip fails while the ASCII control passes; the diagonal alias
merge yields `variables=(1,)`, `linear={1: 4.0}` while the off-diagonal control raises;
`ruff check src/gibbsiq/__init__.py` under the project configuration passes. Subagent
scratch scripts remain under the session scratchpad (`coreir_*`, `runtime_*`, `diag_*`,
`samp_*`, `oracle_*`, `prog_*`, `vq_*`, `topo_*`) for re-execution. No repository file
other than this journal entry was created or modified.
