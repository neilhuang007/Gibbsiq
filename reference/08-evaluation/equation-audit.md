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
Variant declaration (updated 2026-07-03): the `rhat` key is and stays the PLAIN split
R-hat; the rank-normalized + folded variant of Vehtari et al. 2021 is reported under the
SEPARATELY NAMED `rank_normalized_rhat*` keys specified in EVAL-EQ-013. The variants are
numerically different and must never share a key: frozen fixtures pin the plain value.
Cross-validated to machine precision against `arviz.rhat(method="split")`.

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

Non-finite input rule (audited 2026-07-03): the degenerate statuses above cover only FINITE
inputs. A non-finite energy value (NaN or +/-Inf) in any chain raises `ValueError` at the
input boundary (`_rectangularize`), mirroring the `finite_float` validation in the model and
config layers. Silently accepting NaN would either leak non-finite values into serialized
output (forbidden above) or, worse, produce a finite-but-meaningless ESS because NaN
comparisons silently terminate the Geyer scan. The THRML runtime cannot produce non-finite
energies (every model coefficient passes `finite_float`), so this guard protects the
baseline-adapter path where external sampler output enters `compute_diagnostics`.

Stationarity contract: R-hat (and EVAL-EQ-008 ESS) assume the recorded draws target a fixed
distribution. The THRML runtime guarantees this by construction: `warmup_beta_ladder`
anneals only during warmup and every recorded read is collected at constant `beta`. If
in-sampling schedules land (parallel tempering), these diagnostics must be computed per
constant-beta segment keyed off `traces["beta_schedule"]`, never across segments.

Magnetization chain-disagreement wiring (audited 2026-07-03): the runtime payload also runs
the chain-disagreement estimators (this equation and EVAL-EQ-013) on the per-chain
magnetization trace (EVAL-EQ-012) and reports them under the `chains.magnetization`
subsection. Rationale: degenerate optima with EQUAL energy are invisible to every statistic
of the energy trace — two chains frozen in opposite ground states of a double well produce
identical constant energy traces — while the magnetization trace separates the wells (the
zero-within-variance status or a numeric R-hat above threshold both fire). The
`chain_disagreement` flag therefore fires from EITHER the energy-trace path or the
magnetization path. The magnetization subsection contributes ONLY `chain_disagreement`;
`zero_within_chain_variance` and `insufficient_diagnostic_data` remain energy-trace-scoped
(frozen fixtures pin their energy-family semantics, and a frozen-but-agreeing sampler
already reports constant-trace statuses through the energy family). Known residual blind
spot, verified empirically: chains trapped in the SAME well are invisible to every
within-sample diagnostic; defenses are extrinsic (overdispersed inits, multi-seed, PT swap
statistics).

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

Non-finite inputs raise `ValueError` at the boundary; the statuses below cover only finite
degenerate inputs (see the non-finite input rule in EVAL-EQ-007).

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
occupancy_efficiency = num_distinct_states / min(R, 2^n)
top_k_mass      = sum of the k largest p_k                    (reported for k = 1, 3, 10)
entropy_nats    = -sum_k p_k * ln(p_k)                        (natural log, in nats)
```

`unique_fraction` remains a raw occupancy statistic. It MUST NOT drive
`low_diversity`: for a finite binary support it converges to zero as `R` grows,
even under perfect sampling. `low_diversity` uses `occupancy_efficiency` instead.
This is efficiency relative to the largest number of distinct states observable
with `R` reads, NOT the fraction of the full support covered. Constraints,
target concentration, and birthday collisions can make a low value legitimate,
so the flag remains a warning and never evidence of incorrect sampling.

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

Use: diversity section of the diagnostics contract; `mode_collapse` and
`low_diversity` warning flags.

Classification rule audited 2026-07-11: `no_recent_improvement`,
`zero_energy_variance`, and `zero_within_chain_variance` are observations, not
sampler-health flags. A flat Hamiltonian sampled exactly has constant energy and
no possible energy improvement while its states may mix perfectly. The raw
metrics and statuses remain in the payload, and the three facts are echoed in a
separate `observations` list so no evidence is discarded.

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

## EVAL-EQ-013: Rank-Normalized and Folded Split R-hat

Source: Vehtari et al. 2021 (rank normalization sec. 3.1, folding sec. 3.2); algorithm-step
port of arviz v0.21.0 `_rhat_rank` / `_z_scale` / `_backtransform_ranks`
(`arviz/stats/diagnostics.py`, cloned and audited line-by-line 2026-07-03). Reported under
the separately named keys `rank_normalized_rhat`, `rank_normalized_rhat_bulk`,
`rank_normalized_rhat_folded`, `rank_normalized_rhat_status`; the plain `rhat` key of
EVAL-EQ-007 is untouched.

```text
inputs: M raw chains of N_raw draws; gate: M >= 2 and N_raw >= 4 (RAW draws, as EVAL-EQ-007)
split:  half-split per EVAL-EQ-007 -> M' = 2 * M chains of N = N_raw // 2 draws
S = M' * N                                    (pooled split draw count)

rank:   r_j = rank of draw j within the POOLED split draws; ties take the average rank
z:      z_j = Phi^{-1}( (r_j - 3/8) / (S - 2 * 3/8 + 1) )     [Blom (1958) backtransform]
bulk:   rank_normalized_rhat_bulk = EVAL-EQ-007 core on the z-values in the M' x N layout
        (the chains are already split; the core formula is applied directly, no re-split)

fold:   zeta_j = | x_j - median(pooled split draws) |
        (even S: median is the mean of the two middle order statistics)
tail:   rank_normalized_rhat_folded = EVAL-EQ-007 core on rank-normalized zeta
        (the folded values are re-ranked and re-z-scaled from scratch)

rank_normalized_rhat = max(bulk, folded)
```

What folding adds: the plain and bulk variants compare between-chain MEAN disagreement
against within-chain variance, so chains sharing a mean but differing in SPREAD pass
undetected (pinned by the variance-only fixture data: plain split R-hat 0.9997 vs
rank-normalized 1.6935 on sd-0.1/sd-10 chains). Folding around the pooled median converts a
scale difference into a location difference, which the bulk machinery then detects. Taking
the max makes the reported value sensitive to both failure modes.

Rank ordering rule: ranks are computed on the POOLED split draws (all chains together),
never per chain — per-chain ranking erases exactly the between-chain location signal R-hat
exists to measure. Splitting happens BEFORE ranking so within-chain drift still splits into
disagreeing half-chains in rank space.

Ties and discrete traces: average-tie ranking is exact, so heavily tied inputs (an Ising
energy trace over a small model takes only a handful of distinct values) degrade gracefully:
each tie group maps to one z-value and the estimator compares level-occupancy between
chains. Ties require EXACT float equality, mirroring both the plain-variant `W == 0` checks
and arviz `rankdata` semantics.

Fold-ordering lineage (verified against R `posterior` sources 2026-07-03): arviz folds
AFTER splitting, around the median of the pooled split draws
(`abs(split_ary - median(split_ary))`); R `posterior` folds BEFORE splitting, around the
median of the raw draws (`fold_draws(x) = abs(x - median(x))`, then split). The two
orderings agree exactly whenever the per-chain raw draw count is even, because the split
array is then a reshape of the same multiset and the medians coincide. They differ for odd
raw counts: both split rules drop each chain's middle draw, arviz's median excludes those
dropped draws, and posterior's median includes them. This port pins the arviz ordering, and
every rank-variant cross-validation runs against arviz; a future cross-validation against
`posterior` must use even per-chain draw counts to be bit-comparable.

Median tie knife-edge (characterized 2026-07-03): the pooled split count `S = M' * N` is
always even, so the pooled median is the average of the two middle order statistics, and
those two draws fold to exactly equidistant values — whether they tie BIT-EXACTLY is
floating-point rounding luck. Breaking that one tie sits at the steep bottom of the normal
quantile and moves the folded component at the 1e-6 level (measured: 4e-6 on 800 gaussian
draws under an affine rescale). This is inherent to the published algorithm — arviz behaves
identically on identical bits — so invariance properties are only exact in exact arithmetic:
the bulk component is invariant under any strictly increasing transform (ranks are
preserved), the folded component only under increasing AFFINE transforms and only up to this
knife-edge. Consequence for fixtures: never pin a folded value produced from continuous data
whose two central order statistics tie; discrete/integer traces are safe.

Degenerate statuses (never NaN/Inf in serialized output; same vocabulary as EVAL-EQ-007):

```text
fewer than 2 chains or fewer than 4 raw draws per chain  -> "insufficient_data"
bulk z: W == 0 and B == 0 (constant pooled trace)        -> "undefined_constant_trace"
bulk z: W == 0 and B > 0  (chains constant at
  distinct values)                                       -> "undefined_or_infinite_zero_within_variance"
folded z: W == 0 and B > 0 (chains symmetric around the
  pooled median with distinct spreads)                   -> "undefined_or_infinite_zero_within_variance"
folded z: W == 0 and B == 0 (folding collapsed, e.g. a
  balanced two-valued trace symmetric around the pooled
  median)                                                -> "ok" with rank_normalized_rhat_folded = null
                                                            and rank_normalized_rhat = bulk alone
otherwise                                                -> "ok" with all three numeric values
```

The folded-collapse rule (`folded = null`, report bulk alone) numerically matches arviz,
whose `max(rhat_bulk, rhat_tail)` returns `rhat_bulk` when the tail component is NaN;
Gibbsiq makes that silent NaN-drop explicit and auditable. In every non-ok status the
combined `rank_normalized_rhat` is null; `rank_normalized_rhat_bulk` stays numeric in the
folded-infinite row (the bulk component alone is well defined there) and is null otherwise.

Threshold: the 1.01 threshold of EVAL-EQ-007 applies; Vehtari et al. state the 1.01
recommendation for exactly this rank-normalized diagnostic. Flag wiring: `chain_disagreement`
fires when EITHER the plain split R-hat path (EVAL-EQ-007) or this variant exceeds 1.01 or
hits the zero-within-variance status, on either the energy or the magnetization trace.

Cross-validation: agrees with `arviz.rhat(method="rank")` to 1e-8 on every fixture and
seeded sweep where both are defined (the tolerance is 1e-8 rather than 1e-9 because the
stdlib normal quantile `statistics.NormalDist.inv_cdf` (Wichura AS 241) and scipy's Cephes
`ndtri` differ at the 1e-9 to 1e-15 level in the tails; both are far more accurate than the
estimator's statistical noise).

Use: chain-disagreement warnings alongside EVAL-EQ-007, on energy and magnetization traces.
Same caveat as EVAL-EQ-007: a disagreement flag, never a convergence or optimality proof.

## EVAL-EQ-014: Replica-Exchange Acceptance Ratio

Source: derived from the fixed-beta Boltzmann law in EVAL-EQ-005 by taking the ratio of
the joint target density after and before swapping two replica states. Audited 2026-07-10.

Let the left and right temperature slots have inverse temperatures `beta_left` and
`beta_right`, and let their current states have canonical Gibbsiq energies `energy_left`
and `energy_right`. Before a proposed state swap, the two-replica density is proportional
to

```text
exp(-beta_left * energy_left - beta_right * energy_right).
```

After swapping the states (not the temperature labels), it is proportional to

```text
exp(-beta_left * energy_right - beta_right * energy_left).
```

Therefore the log Metropolis ratio `log(target_after / target_before)` is

```text
log_ratio = (beta_left - beta_right) * (energy_left - energy_right)
accept if log(U) < min(0, log_ratio), where U ~ Uniform(0, 1).
```

The implementation may use the equivalent numerically stable branch
`log_ratio >= 0 or log(U) < log_ratio`. A common sign bug is to use
`(beta_left - beta_right) * (energy_right - energy_left)`; that is the reciprocal ratio
and preferentially moves high-energy states toward the colder (larger-beta) slot.

Adding the same finite offset `c` to both energies leaves the ratio unchanged because
`(beta_left - beta_right) * ((energy_left + c) - (energy_right + c))` equals `log_ratio`.
This cancellation does not relax the project-wide requirement to preserve offsets in
reported energies.

Use: parallel-tempering swap decisions and deterministic swap-trace tests. Replica
exchange improves communication between temperature slots; its acceptance rate is sampler
health evidence, not proof of convergence or optimality.

When the backend rounds coefficients or beta, slot `k` instead targets a recorded
lowered log density `ell_k(s)`. Detailed balance then requires the general ratio

```text
log_ratio = ell_left(state_right) + ell_right(state_left)
          - ell_left(state_left)  - ell_right(state_right).
```

Using canonical host energies in that case mixes two different targets: local
moves preserve the lowered law while swaps preserve the host law. The canonical
formula above is only the special case `ell_k(s) = -beta_k E(s) + constant`.

## EVAL-EQ-015: Backend Local-Logit Error Bound

For effective (already beta-scaled) host and backend coefficients, let `delta h_i`
and `delta J_ij` be their differences. For backend unit roundoff `u`, node degree
`d_i`, and `A_i = |h_i_backend| + sum_j |J_ij_backend|`, use

```text
gamma_d = d_i * u / (1 - d_i * u)
field_error_i <= |delta h_i| + sum_j |delta J_ij| + gamma_d * A_i
logit_error_i <= 2 * field_error_i.
```

The first terms bound coefficient conversion for every neighboring spin state;
the standard `gamma_d` term conservatively bounds THRML's floating reduction and
bias addition. Reject a lowering when the maximum logit bound exceeds `1e-4`.
The rejected `1e-6` alternative was too strict for ordinary float32 sparse models
once conservative accumulation error was included; `1e-4` still bounds the
corresponding sigmoid-probability perturbation by at most `2.5e-5`. This is an
approximation guarantee, not a claim of exact sampling from the host Hamiltonian.
