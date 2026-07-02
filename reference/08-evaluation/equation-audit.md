# Equation Audit

Status: manually checked on 2026-05-28 against the downloaded PDFs and current primary docs.
Diagnostics entries (EVAL-EQ-007, EVAL-EQ-008, EVAL-EQ-011, EVAL-EQ-012) extended on
2026-07-02 for the Stage 3 pipeline and cross-validated against arviz (v0.21.0 algorithm
source) and analytic AR(1) results; see
`reference/research-journal/2026-07-02-stage-03-diagnostics-pipeline.md`.

The raw transcript files are useful for search, but not for math. The equations below are the formulas that Gibbsiq evaluation fixtures may depend on.

## EVAL-EQ-001: Gibbsiq Ising Energy Convention

Source: project spec.

```text
E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j
s_i in {-1, +1}
```

Use: internal IR, exact enumerator, sampler energy checks.

Verification note: Lucas 2014 page 1, eq. 3 uses the physics sign convention `H = -sum J_ij s_i s_j - sum h_i s_i`. Gibbsiq intentionally uses the opposite explicit coefficient convention above. Do not copy Lucas signs directly into Gibbsiq tests.

## EVAL-EQ-002: Binary-to-Spin Mapping

Source: Lucas 2014 PDF, page 4, eq. 12.

```text
x_i = (s_i + 1) / 2
s_i = 2 x_i - 1
```

Use: QUBO/BQM conversion tests.

## EVAL-EQ-003: Upper-Triangle QUBO to Ising Conversion

Source: derived from EVAL-EQ-001 and EVAL-EQ-002; verified by exhaustive table in `fixtures/exact-small-instances.json`.

For the term convention:

```text
E_Q(x) = offset + sum_i q_i x_i + sum_{i<j} q_ij x_i x_j
```

the equivalent Gibbsiq Ising coefficients are:

```text
J_ij = q_ij / 4
h_i = q_i / 2 + sum_{j != i} q_ij / 4
offset_ising = offset + sum_i q_i / 2 + sum_{i<j} q_ij / 4
```

Use: `compile_qubo`, `compile_bqm`, `SampleResult.metadata.conversion_offset`.

Important: this is not the dense symmetric matrix convention. If users pass a symmetric matrix with both `(i, j)` and `(j, i)`, normalize it before applying this fixture convention.

## EVAL-EQ-004: Gibbs Conditional Under Gibbsiq Convention

Source: derived from EVAL-EQ-001.

For local field:

```text
gamma_i = h_i + sum_j J_ij s_j
```

the single-site conditional at inverse temperature `beta` is:

```text
P(s_i = +1 | s_-i) = sigmoid(-2 * beta * gamma_i)
```

Use: THRML sign tests and two-spin analytic sampler tests.

## EVAL-EQ-005: Boltzmann Probability

Source: standard Gibbs/Boltzmann distribution; used by THRML-style Gibbs samplers.

```text
P(s) = exp(-beta * E(s)) / Z
Z = sum_s exp(-beta * E(s))
```

Use: exact small Boltzmann fixtures.

## EVAL-EQ-006: Cut Indicator and Max-Cut Energy

Source: Lucas 2014 PDF, page 4, eq. 9 verifies the edge cut indicator form.

For an edge `(u, v)`:

```text
cut_edge(s) = (1 - s_u s_v) / 2
```

For unweighted Max-Cut:

```text
cut_value(s) = sum_(u,v) cut_edge(s)
E_cut(s) = sum_(u,v) s_u s_v
cut_value(s) = (num_edges - E_cut(s)) / 2
```

Use: exact Max-Cut fixtures. Minimizing `E_cut` is equivalent to maximizing `cut_value`.

## EVAL-EQ-007: Split R-hat Core

Source: Vehtari et al. PDF, pages 5-6, eqs. 1-4.

```text
B = N / (M - 1) * sum_m (theta_.m - theta_..)^2
W = (1 / M) * sum_m s_m^2
var_hat_plus = ((N - 1) / N) * W + (1 / N) * B
Rhat = sqrt(var_hat_plus / W)
```

Use: chain-disagreement warnings only.

Important: optimization runs are not posterior inference. Gibbsiq should not claim convergence or optimality from low R-hat. It may use R-hat-style values as a disagreement flag over energy, magnetization, violation count, or distance-to-best features.

Split application (Stage 3, audited 2026-07-02): the reported `rhat` applies the core
formula to half-split chains. Each raw chain of `N_raw` draws contributes its first
`N_raw // 2` and last `N_raw // 2` draws as two chains (the middle draw is dropped when
`N_raw` is odd), so the formula runs with `M = 2 * M_raw` chains of `N = N_raw // 2` draws.
Variant declaration: Gibbsiq reports the PLAIN split R-hat, not the rank-normalized or
folded variants of Vehtari et al. 2021; the three are numerically different and must not be
mixed. Cross-validated to machine precision against `arviz.rhat(method="split")`.

Estimator conventions (two variance quantities coexist and are distinct keys):

```text
s_m^2 in W uses ddof = 1 (divide by N - 1) on split chains
within_chain_variances (reported per raw chain) uses population variance (divide by N_raw)
between_chain_variance (reported) is B computed on UNSPLIT raw chains
```

The unsplit `between_chain_variance = 96.0` in the frozen
`chain_disagreement_zero_within_variance` fixture pins the unsplit-B convention; the
`rhat` value itself is always split-based. Conflating these is the classic R-hat
implementation bug.

Degenerate statuses (never NaN/Inf in serialized output):

```text
fewer than 2 chains or fewer than 4 raw draws per chain -> rhat_status = "insufficient_data"
W == 0 and B == 0 (identical constant chains)           -> rhat_status = "undefined_constant_trace"
W == 0 and B > 0                                        -> rhat_status = "undefined_or_infinite_zero_within_variance"
otherwise                                               -> rhat_status = "ok" with numeric rhat
```

The 4-raw-draw minimum is checked on raw (pre-split) draws, matching arviz's validity gate.

Stationarity contract: R-hat (and EVAL-EQ-008 ESS) assume the recorded draws target a fixed
distribution. The THRML runtime guarantees this by construction: `warmup_beta_ladder`
anneals only during warmup and every recorded read is collected at constant `beta`. If
in-sampling schedules land (parallel tempering), these diagnostics must be computed per
constant-beta segment keyed off `traces["beta_schedule"]`, never across segments.

## EVAL-EQ-008: Effective Sample Size Core

Source: Vehtari et al. PDF, pages 6-8, eqs. 7 and 11-13.

Single-chain ideal form:

```text
N_eff = N / (1 + 2 * sum_{t=1..infinity} rho_t)
```

Combined-chain truncated form:

```text
S_eff = N * M / tau_hat
tau_hat = 1 + 2 * sum_{t=1..T} rho_hat_t
```

Use: ESS-style sampler health checks.

Threshold note: Vehtari et al. recommend rank-normalized ESS greater than 400 and R-hat less than 1.01 for MCMC reporting. Gibbsiq v0 should report these as diagnostic context, not as optimizer pass/fail proof.

Convention warning (factor of 2): Gibbsiq's `tau_hat = 1 + 2 * sum rho_t` follows
Vehtari/Geyer/Stan. Sokal's lecture-notes convention defines `tau_int = 1/2 + sum rho_t`
(half of ours in the large-tau limit) and the emcee package additionally uses a different
(Sokal window) truncation rule. Values from those sources are not comparable at fixture
tolerance; do not copy them into fixtures.

Exact truncation and estimator (Stage 3, audited 2026-07-02; matches arviz
`_ess`/`stats_utils.autocov` at the algorithm-step level so goldens cross-check to 1e-9):

```text
inputs: M raw chains of N_raw draws each; require N_raw >= 4 (checked on RAW draws)
split:  half-split as in EVAL-EQ-007 -> M' = 2 * M chains of N = N_raw // 2 draws

acov_m(t) = (1 / N) * sum_{i=1..N-t} (x_m,i - mean_m) * (x_m,i+t - mean_m)   [biased, per-chain mean]
mean_var  = mean_m acov_m(0) * N / (N - 1)
var_plus  = mean_var * (N - 1) / N            [+ var(chain_means, ddof=1) when M' > 1]

rho_0 = 1
rho_t = 1 - (mean_var - mean_m acov_m(t)) / var_plus          for t >= 1

Geyer initial positive sequence:
  t = 1; even = rho_0; odd = rho_1; all higher rho start at 0
  while t < N - 3 and (even + odd) > 0:
      even = rho_{t+1}; odd = rho_{t+2}
      if even + odd >= 0: keep rho_{t+1} and rho_{t+2} (else both stay 0)
      t += 2
  max_t = t - 2
  if even > 0: keep rho_{max_t+1} = even                      [improve-estimation term]

Geyer initial monotone sequence (pair-averaging clamp), t = 1, 3, ... while t <= max_t - 2:
  if rho_{t+1} + rho_{t+2} > rho_{t-1} + rho_t:
      rho_{t+1} = (rho_{t-1} + rho_t) / 2; rho_{t+2} = rho_{t+1}

tau_hat = -1 + 2 * sum_{t=0..max_t} rho_t + rho_{max_t+1}
tau_hat = max(tau_hat, 1 / log10(M' * N))                     [tau floor]
ESS     = M' * N / tau_hat
```

Edge case: when `N < 5` the positive-sequence loop never runs (`max_t = -1`) and `tau_hat`
collapses to the floor; the implementation must return a numeric value there, not crash.

Degenerate statuses (deliberate divergence from arviz): arviz returns `ESS = array size`
for a constant array, which is a healthy-looking ESS on a frozen sampler and violates the
Non-Negotiable Failure Cases. Gibbsiq instead returns
`autocorrelation_status = "constant_trace"` and `ess_status = "undefined_constant_trace"`.
Below 4 raw draws both statuses are `"insufficient_data"`. Statuses replace NaN/Inf in all
serialized output.

The stationarity contract in EVAL-EQ-007 applies identically here.

## EVAL-EQ-009: Benchmark Performance Score

Source: Bernal Neira et al. 2024 PDF, page 9.

For a higher-is-better solution quality:

```text
performance_score = (best_found_solution - random_solution)
                    / (optimal_solution - random_solution)
```

For Gibbsiq's lower-is-better energy convention, use the equivalent cost form:

```text
performance_score = (random_energy - best_found_energy)
                    / (random_energy - optimal_energy)
```

Use: benchmark scorecards where an exact or planted optimum and a random baseline are known.

## EVAL-EQ-010: Benchmark Resource Accounting

Source: Bernal Neira et al. 2024 PDF, pages 1-3 and 9.

Rules for Gibbsiq:

```text
reported_resources = formulation_time
                   + parameter_tuning_time
                   + compile_time
                   + sample_time
                   + diagnostics_time
```

Use fixed-time and fixed-work comparisons separately. If parameters are tuned, report the tuning budget and include it in resource accounting when claiming operational performance.

## EVAL-EQ-011: Sample Diversity Metrics

Source: standard definitions (Shannon entropy; Hamming distance), pinned by the frozen
`mode_collapse_counts_n4_reads128` fixture and cross-validated exactly against
`scipy.stats.entropy` and `scipy.spatial.distance.pdist(metric="hamming")` on 2026-07-02.

For `R` reads over `n` variables with distinct-state counts `c_k` (`sum_k c_k = R`,
frequencies `p_k = c_k / R`):

```text
unique_fraction = num_distinct_states / R
top_k_mass      = sum of the k largest p_k                    (reported for k = 1, 3, 10)
entropy_nats    = -sum_k p_k * ln(p_k)                        (natural log, in nats)
```

Mean pairwise Hamming distance is averaged over ALL C(R, 2) unordered read pairs, including
pairs of reads that landed in the same state (which contribute distance 0). With
`d(a, b)` the number of differing variables between states `a` and `b`:

```text
mean_pairwise_hamming_distance = [ sum_{k < l} c_k * c_l * d(a_k, a_l) ] / C(R, 2)
normalized_mean_pairwise_hamming_distance = mean_pairwise_hamming_distance / n
```

`mean_pairwise_hamming_distance` is in variable units (average number of differing
variables per pair). Frozen-fixture pins (n = 4, R = 128):
entropy_nats = 0.3096046315802033,
mean_pairwise_hamming_distance = 0.27288385826771655 (= 2218 / 8128), and
normalized_mean_pairwise_hamming_distance = 0.06822096456692914. Common wrong variants that
these pins kill: log2 entropy, distinct-state-only Hamming (excluding same-state pairs),
and ordered-pair denominators.

Use: diversity section of the diagnostics contract; `mode_collapse` and `low_diversity`
flags.

## EVAL-EQ-012: Magnetization and Distance-to-Best Traces

Source: standard Ising magnetization; distance-to-best defined by the Stage 3 contract.

For read `t` with spins `s_i(t)` over `n` variables:

```text
magnetization_t = (1 / n) * sum_i s_i(t)
distance_to_best_t = Hamming distance between read t and the run's best sample
```

The best sample is the read with minimal energy; ties resolve to the FIRST minimal index in
flat read order, matching `SampleResult.best_index`. Both traces are per-chain
lists-of-lists with the same shape as `traces["energy"]`. Degenerate optima make
`distance_to_best` depend on the tie rule, which is why the rule is pinned here.

Use: trace capture in the THRML runtime; Stage 4 inspector plots.

