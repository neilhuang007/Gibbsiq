# Equation Audit

Status: manually checked on 2026-05-28 against the downloaded PDFs and current primary docs.

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

