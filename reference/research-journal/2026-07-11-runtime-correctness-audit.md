# 2026-07-11 - Runtime Correctness Audit

## Paper Hook

This entry feeds the methods, numerical-validity, and limitations sections. It records the
failure modes that made the parallel-tempering path and float32 lowering scientifically
unsafe, together with the invariants required to close the audit.

## Context

The fixed-beta runtime had analytic small-instance coverage. The opt-in parallel-tempering
path and host-to-JAX lowering boundary had less independent coverage. A line-by-line audit of
the transition flow, exchange ratio, JAX representation, and diagnostics allocation found
failures that could return plausible traces while sampling the wrong process.

## Hard-Parts Analysis

### H1. The replica-exchange ratio had the reciprocal sign

For adjacent slots, the audited log ratio is

```text
(beta_left - beta_right) * (energy_left - energy_right)
```

The previous implementation used `energy_right - energy_left`. That reciprocal ratio favors
moving a higher-energy state toward a colder slot. The correction is recorded as EVAL-EQ-014
and tested through a standalone pure function, including invariance to a common offset.

### H2. One requested local sweep could execute zero transitions

THRML 0.1.3 `sample_states` runs warmup first and records that state as sample zero. Its
`n_samples <= 1` branch returns at `block_sampling.py:466-468`; `steps_per_sample` is applied
only while collecting samples after the first. The previous helper encoded `sweeps = 1` as
`n_warmup = 0, n_samples = 1`, so the default PT configuration performed no local Gibbs
transition between exchange opportunities. The corrected helper places all requested sweeps
in `n_warmup` before reading the returned state.

### H3. Alternating parity skips half of the only edge for two replicas

Odd-even adjacent exchange is valid for ladders with at least three replicas. A two-replica
ladder has one edge, so alternating parity produces an empty pair set every second round. The
pair scheduler now attempts `(0, 1)` on every two-replica exchange round while preserving
non-overlapping odd-even rounds for larger ladders.

### H4. Per-coefficient float32 checks miss cancellation

The P0 counterexample uses `h_a = 2^24 + 1`, `J_ab = -2^24`, `beta = 1`, and neighbor state
`s_b = +1`. The exact local field for `a` is `gamma_a = 1`. Float32 rounds `2^24 + 1` to
`2^24`, so the lowered local field is `0`. The intended conditional is `sigmoid(-2)`,
approximately `0.119202922`; the lowered conditional is `sigmoid(0) = 0.5`. Each individual
coefficient has relative error below `1e-6`, so elementwise relative checks alone accept this
model.

The first correction considered a state-uniform coefficient-conversion bound on every local
Gibbs logit:

```text
2 * (abs(delta(beta * h_i)) + sum_j abs(delta(beta * J_ij)))
```

The triangle inequality makes this component valid for every neighboring spin assignment and
catches conversion cancellation without enumerating states. It does not bound rounding inside
the backend reduction.

An exact-coefficient counterexample exposes the second component. Let node `a` have three
incident terms `-2^24`, `-1`, and `+2^24`, with every neighboring spin up. Each coefficient is
exactly representable in float32 and the exact field is `-1`. A JAX float32 reduction can
return `0`, changing `sigmoid(2)` to `sigmoid(0)`. The conversion-only error is zero.

EVAL-EQ-015 therefore adds the standard floating-summation term. For unit roundoff `u`, degree
`d_i`, and `A_i = abs(h_i_backend) + sum_j abs(J_ij_backend)`, the enforced bound is:

```text
gamma_d = d_i * u / (1 - d_i * u)
field_error_i <= abs(delta(beta * h_i))
                 + sum_j abs(delta(beta * J_ij))
                 + gamma_d * A_i
logit_error_i <= 2 * field_error_i
max_i logit_error_i <= 1e-4
```

The exact-coefficient counterexample produces a conservative bound of approximately 12 and is
rejected. Since the logistic sigmoid has derivative at most `1/4`, the accepted `1e-4` logit
bound limits conditional-probability perturbation to at most `2.5e-5`.

### H5. Finite Python floats can become different JAX models

With JAX x64 disabled, values such as `1e40` can become nonfinite and values near `1e-50` can
become zero. Float32 subnormals can remain nonzero while carrying material relative error.
Reported energies are recomputed from the host model, so a backend mismatch can otherwise be
masked by apparently correct result energies.

## Decisions

- The exchange decision uses EVAL-EQ-014 and offset-free interaction energies. Removing the
  common offset before subtraction avoids cancellation while preserving the exact ratio.
- Every PT sampling interval performs exactly `steps_per_sample` local sweeps before exchange.
- Two-replica ladders attempt their sole edge at every exchange opportunity.
- A warmup ladder must end at the sampling `beta`, preventing an unrecorded temperature jump
  before the first retained read.
- Host-to-JAX coefficient and beta lowering rejects a nonzero source value that becomes
  nonfinite or zero, or whose relative error exceeds `1e-6`.
- The per-value host-to-JAX relative-error limit remains `1e-6`.
- The state-uniform local-logit error bound is `1e-4` and includes both coefficient conversion
  and EVAL-EQ-015 `gamma_d` accumulation error. The probability perturbation bound is
  `2.5e-5`.
- Seeds are restricted to JAX's unsigned 32-bit key domain, `0 <= seed <= 2^32 - 1`, preventing
  silent aliases at the backend boundary.
- Runtime provenance labels the execution backend `THRML JAX simulator` and records JAX x64,
  lowered dtypes, Python, OS, and device information. Fixed-beta runs use JAX key splitting;
  PT additionally uses Python `random.Random` for exchange uniforms, so PT metadata must name
  both RNG paths and the per-chain swap-seed derivation.
- Reads use `divmod` allocation across chains, so chain lengths differ by at most one and
  diagnostics discard the minimum possible number of retained reads.

## Rejected Alternatives

- Keeping the old exchange expression and changing only trace labels was rejected because the
  Markov kernel itself was wrong.
- Encoding one sweep as `n_samples = 1` was rejected after direct inspection of THRML 0.1.3's
  early-return branch.
- Applying odd-even parity unchanged to two replicas was rejected because it deterministically
  deletes half the requested exchange opportunities.
- Checking only overflow and underflow was rejected because float32 subnormals can survive with
  material distortion.
- Checking only per-coefficient relative error was rejected because the exact-`gamma = 1`
  conversion counterexample passes that test while rounding the local field to zero.
- Checking only coefficient deltas was rejected because the exactly representable
  `(-2^24, -1, +2^24)` terms can lose `-1` during float32 accumulation.
- A `1e-6` total-logit limit was rejected after adding the conservative accumulation term. It
  rejects ordinary sparse float32 models; `1e-4` retains a maximum probability perturbation of
  `2.5e-5`.
- Enabling JAX x64 implicitly was rejected because global JAX configuration is an environment
  choice. The runtime instead rejects an unsafe lowering and tells the caller to enable x64 or
  rescale.
- Recording generic `THRML` backend metadata was rejected because it could be misread as a TSU
  hardware execution record. Recording only the JAX RNG was also rejected for PT because the
  exchange decisions use a separate Python RNG stream.

## Sources And Code Read

- Gibbsiq equation audit, EVAL-EQ-005, EVAL-EQ-014, and EVAL-EQ-015.
- THRML 0.1.3 `.venv/Lib/site-packages/thrml/block_sampling.py:449-498`.
- THRML official architecture documentation: https://docs.thrml.ai/en/latest/architecture/
- Gibbsiq runtime, model, diagnostics, and runtime contract tests.

## Verification State

The source inspection command was:

```powershell
rg -n "def sample_states|n_samples|n_warmup|steps_per_sample|scan" .venv/Lib/site-packages/thrml/block_sampling.py
```

Required targeted checks cover the exchange sign, common-offset invariance, two/three/four
replica pair schedules, exact sweep forwarding, float32 overflow/underflow/subnormal rejection,
the conversion and accumulation cancellation counterexamples, warmup endpoint validation, seed
range, backend metadata, and balanced read allocation. A PT provenance check must assert both
RNG descriptions and the swap-seed derivation. This entry does not claim those tests pass. The
coordinating audit records final commands, counts, skips, and failures after concurrent source
edits stabilize.
