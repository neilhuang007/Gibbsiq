# 2026-07-11 - Diagnostics Semantics Audit

## Paper Hook

This entry feeds the diagnostic-methods and limitations sections. It separates correctly
implemented statistics from unsupported threshold interpretations and distinguishes measured
trace facts from sampler-health failures.

## Context

Stage 3 implemented plain and rank-normalized split R-hat, raw-energy Geyer ESS/tau,
diversity metrics, and family-scoped flags. The formula implementations carry external
cross-checks. This audit evaluates the meanings assigned to those values and the conditions
under which a flag is justified.

## Hard-Parts Analysis

### H1. The 400 recommendation does not apply to the implemented ESS

Vehtari et al. 2021 recommend ESS greater than 400 for rank-normalized bulk and tail ESS in
MCMC reporting. Gibbsiq currently computes Geyer ESS on the raw energy trace. These estimators
answer different questions and can have different values on the same draws. Applying
`LOW_ESS_THRESHOLD = 400` to the raw-energy result imports a threshold without its estimator.

### H2. Unique fraction necessarily falls with repeated healthy draws

`unique_fraction = distinct_states / num_reads` is useful occupancy telemetry. It is not a
mixing-quality score on a finite state space. A sampler that visits all four states of a
two-spin model in 100 reads has `unique_fraction = 0.04`, below the previous 0.05 threshold,
despite complete observed support. The previous `low_diversity` rule therefore false-flags a
simple healthy case.

### H3. The first normalization repair used an inaccurate name

The concurrent repair proposed

```text
distinct_states / min(num_reads, 2^num_variables)
```

and named it `support_coverage`. When `num_reads < 2^num_variables`, the denominator is the
maximum number of distinct states observable in that read budget rather than the binary state
support. For example, 100 unique reads from a 100-spin model yield 1.0 while covering only
`100 / 2^100` of the binary support. The quantity is an occupancy efficiency, not support
coverage. Publication-facing names and claims must preserve that distinction.

### H4. Constant objective traces are compatible with correct sampling

A flat Hamiltonian has constant energy and no possible best-energy improvement. An exact
sampler on that target therefore produces `zero_energy_variance` and
`no_recent_improvement`. Identical facts also arise from a frozen chain, so they are useful
observations but not failures without state-space or chain evidence. Likewise,
`zero_within_chain_variance` becomes a health failure only when coupled with between-chain
disagreement; the disagreement path already emits `chain_disagreement`.

## Decisions

- Raw-energy ESS and tau remain telemetry with explicit degenerate statuses.
- The rank-normalized `ESS > 400` recommendation will not trigger a raw-energy `low_ess` flag.
  A future implementation must expose separately named rank-normalized bulk and tail ESS before
  applying that recommendation.
- `no_recent_improvement`, `zero_energy_variance`, and `zero_within_chain_variance` move to a
  separately ordered `observations` list. Their raw metrics remain in the payload.
- `unique_fraction` remains as raw occupancy telemetry and no longer drives `low_diversity`.
- Any replacement diversity normalization must use a name that matches its denominator.
  The equation audit and implementation report `distinct / min(R, 2^n)` as
  `occupancy_efficiency`; literal support coverage is `distinct / 2^n` only when the
  unconstrained binary support is the intended denominator.
- Stage 3 remains implemented and under corrective semantic audit until the code, equation
  audit, thresholds echo, fixtures, and tests agree on these rules.

## Rejected Alternatives

- Retaining `ESS < 400` as a generic conservative warning was rejected because it attaches a
  primary-source recommendation to the wrong estimator.
- Treating every constant energy trace as a sampler failure was rejected because a flat target
  is a direct counterexample.
- Keeping `unique_fraction <= 0.05` as `low_diversity` was rejected because increasing the
  read count eventually triggers it on every finite support.
- Calling `distinct / min(R, 2^n)` support coverage was rejected because the value can be 1.0
  while the observed set covers a negligible fraction of the state support.
- Deleting observations from the result was rejected because diagnostic evidence must remain
  available even when it is insufficient to justify a failure flag.

## Sources Read

- Vehtari et al., "Rank-normalization, folding, and localization: an improved R-hat for
  assessing convergence of MCMC," Bayesian Analysis 16(2), 2021.
- D-Wave dimod ESS documentation:
  https://docs.dwavequantum.com/en/latest/ocean/api_ref_dimod/ess.html
- Gibbsiq EVAL-EQ-007, EVAL-EQ-008, and EVAL-EQ-011.
- `src/gibbsiq/diagnostics.py` and the diagnostic golden fixtures.

## Verification State

Counterexample fixtures must cover a fully observed two-spin support with more than 80 reads,
a flat Hamiltonian whose state samples mix, a frozen single-state chain, and the estimator-name
boundary for raw versus rank-normalized ESS. The implementation now removes `low_ess`, uses
`occupancy_efficiency`, and emits the three constant/progress facts under `observations`.
The coordinating audit records final test results after concurrent fixture and test edits
stabilize.

## Follow-Up: Top-1 Concentration Is Not Mode Collapse

### Counterexample

For one spin with `h = 1` and `beta = ln(19) / 2`, the canonical distribution is

```text
P(s = -1) = exp(beta) / [exp(beta) + exp(-beta)] = 19 / 20 = 0.95.
```

An exact sampler therefore has population top-1 mass 0.95, above the former 0.9
`mode_collapse` threshold. The threshold could flag a correct kernel even with arbitrarily
many reads; this is semantic invalidity, not finite-sample uncertainty.

### Decision And Contract

- `top1_mass` remains unchanged as raw evidence.
- `top1_mass >= 0.9` now emits `high_sample_concentration` under `observations`.
- `mode_collapse` is removed from generic diversity flags. A future collapse diagnosis must
  compare against target-aware evidence (such as an exact small-model distribution) or use an
  independently justified mixing failure.
- The threshold echo is renamed from `mode_collapse_top1_mass` to
  `high_sample_concentration_top1_mass`. The Python constant receives the corresponding name;
  the old constant remains a compatibility alias for import stability.
- The 0.9 value is retained to avoid changing both classification and sensitivity in one
  repair. Sensitivity: any cutoff in `(0, 1]` can be exceeded by a legitimate sufficiently
  concentrated Boltzmann target, so no cutoff makes top-1 mass a generic failure criterion.

### Rejected Alternatives

- Keeping `mode_collapse` but calling it a warning was rejected because the name still asserts
  a failed sampling mode that the statistic cannot establish.
- Requiring top-1 mass plus low occupancy efficiency was rejected because both are functions
  of the same sample counts and both can arise under an exactly sampled concentrated target.
- Removing the threshold and concentration evidence entirely was rejected because high top-1
  mass remains useful telemetry when interpreted with the model and beta.
- Calibrating against the exact target in the generic diagnostics function was deferred: exact
  normalization is exponential and unavailable for the large models this layer must support.

### Verification

Deterministic regression coverage includes the analytic one-spin 95% counterexample, the
inclusive 0.9 observation boundary, golden fixture/candidate agreement, and the frozen THRML
end-to-end path. No stochastic parameter search or generated artifact was used.

Commands run from `E:\\projects\\Gibbsiq` with `PYTHONPATH=src`:

```powershell
.\.venv\Scripts\python.exe -m unittest test_suite.tests.test_diagnostics `
  test_suite.tests.test_diagnostics_ground_truth `
  test_suite.tests.test_diagnostic_fixtures `
  test_suite.tests.test_evaluation_harness `
  test_suite.tests.test_stage3_end_to_end_validation
# 98 tests, OK

.\.venv\Scripts\ruff.exe check src/gibbsiq/diagnostics.py src/gibbsiq/__init__.py `
  test_suite/tests/test_diagnostics.py test_suite/tests/test_diagnostics_ground_truth.py `
  test_suite/tests/test_diagnostic_fixtures.py `
  test_suite/tests/test_stage3_end_to_end_validation.py
# All checks passed

.\.venv\Scripts\python.exe -m unittest discover -s test_suite/tests -q
# 327 tests, OK; one expected upstream ArviZ warning on a degenerate R-hat fixture

.\.venv\Scripts\mypy.exe src/gibbsiq
# Success: no issues found in 11 source files

.\.venv\Scripts\ruff.exe format --check src/gibbsiq/diagnostics.py src/gibbsiq/__init__.py `
  test_suite/tests/test_diagnostics.py test_suite/tests/test_diagnostics_ground_truth.py `
  test_suite/tests/test_diagnostic_fixtures.py `
  test_suite/tests/test_stage3_end_to_end_validation.py
# 6 files already formatted
```

One earlier command named nonexistent module `test_suite.tests.test_evaluation_cli` and failed
with `ModuleNotFoundError`; replacing it with the repository's actual
`test_suite.tests.test_evaluation_harness` module produced the passing result above.
Running the example candidate through `python -m gibbsiq.evaluation` returned exit code 1:
all 12 example entries, including `mode_collapse_counts_n4_reads128`, passed, but the example
does not include the 27 benchmark fixtures now in the corpus. This is an existing incomplete
example-candidate condition, not evidence that the diagnostic contract failed.

Updated golden artifact:
`E:\\projects\\Gibbsiq\\reference\\08-evaluation\\fixtures\\diagnostic-fixtures.json`,
SHA-256 `4468E364ABBC1CD1435945D7E6E3A6D6294E59ABAC33BD8D05EB9F7082427C41`.

**Paper hook:** This counterexample supplies a worked anti-false-positive case for the
diagnostic-taxonomy and limitations sections: an observable may be valid while its generic
failure interpretation is not.
