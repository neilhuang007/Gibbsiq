# Diagnostics

Diagnostics in Gibbsiq are THRML runtime telemetry. They summarize the sample distribution
and scalar traces produced by a run. They are required because a stochastic optimizer can
return a low-energy sample even when the chain is collapsed, highly autocorrelated, or stuck
in one mode. Diagnostics warn about those failure modes; they do not prove optimality.

Implemented in `src/gibbsiq/diagnostics.py` (Stage 3, 2026-07-02, pure stdlib): every
`THRMLSampler.sample()` call embeds the payload described below. The audited formulas live
in EVAL-EQ-007/008/011/012; design decisions and external anchoring are journaled in
`reference/research-journal/2026-07-02-stage-03-diagnostics-pipeline.md`.

## Stationarity Contract

Trace-window diagnostics (tau, ESS, split R-hat) assume the chains target a fixed
distribution over the recorded window. The runtime guarantees this by construction: any
annealing happens during warmup (`warmup_beta_ladder`) and every recorded read is collected
at constant `config.beta`. Under this contract, split R-hat on the sampling trace detects
unequilibrated reads (warmup too short) or multimodal trapping. When in-sampling schedules
land (parallel tempering), diagnostics must be computed per constant-beta segment keyed off
`traces["beta_schedule"]`.

## Flag Semantics for Optimization

Flags are telemetry warnings with optimization-context meanings, never pass/fail verdicts:
`mode_collapse` means the reads carry almost no distributional information (which may be
acceptable at high beta); `no_recent_improvement` means the second half of the read budget
bought nothing; `chain_disagreement` means the reads depend on initialization and energies
should be treated as biased. Every payload echoes the trigger constants under
`diagnostics["thresholds"]` so downstream consumers can reinterpret without rerunning.

| Threshold constant | Value | Source |
| --- | --- | --- |
| `RHAT_THRESHOLD` | 1.01 | Vehtari et al. 2021 |
| `LOW_ESS_THRESHOLD` | 400.0 | Vehtari et al. 2021 |
| `MODE_COLLAPSE_TOP1_MASS_THRESHOLD` | 0.9 | frozen diversity fixture fires |
| `LOW_DIVERSITY_UNIQUE_FRACTION_THRESHOLD` | 0.05 | frozen diversity fixture fires |
| `NO_RECENT_IMPROVEMENT_WINDOW_FRACTION` | 0.5 | second half of the budget |
| `POOR_MIXING_MIN_TAU_MULTIPLES` | 50.0 | emcee autocorrelation tutorial |
| `MIN_DRAWS_FOR_ESS` / `MIN_DRAWS_FOR_RHAT` | 4 raw draws | mirrors arviz validity gate |
| `MIN_CHAINS_FOR_RHAT` | 2 | definition of between-chain variance |

## Status Vocabulary

Degenerate inputs return explicit statuses instead of NaN/Inf (a deliberate divergence from
arviz, which reports a healthy ESS equal to array size on constant input): `ok`,
`constant_trace`, `undefined_constant_trace`, `undefined_or_infinite_zero_within_variance`,
`insufficient_data`, and `not_available` (constraints section until the penalty layer
exists). Precedence: insufficient data, then constancy, then numeric evaluation.

## Family Scoping

Golden diagnostic fixtures compare `required_flags` as an exact multiset, so a fixture's
`input` block declares which telemetry family it exercises: `sample_counts` selects the
diversity family, `energy_trace` the energy family, `chains` the chains family. The fixture
adapter (`diagnostic_candidate_from_input`) emits only that family's flags; the runtime path
(`compute_diagnostics`) unions all families under `"flags"`. Same family, same flags,
forever.

## Sources

- Vehtari et al.: https://sites.stat.columbia.edu/gelman/research/published/Vehtari_etal_2020_rhat_ess.pdf
- ArviZ diagnostics: https://arviz-devs.github.io/EABM/Chapters/MCMC_diagnostics.html
- ArviZ docs: https://python.arviz.org/
- emcee autocorrelation: https://emcee.readthedocs.io/en/stable/tutorials/autocorr/
- Sampler diagnostics benchmark: https://www.auai.org/uai2018/proceedings/papers/37.pdf

## v0 Metrics

Optimization:

- best energy;
- median energy;
- energy quantiles;
- gap to exact/best-known;
- time to target;
- feasibility rate.

Sampling:

- energy autocorrelation;
- integrated autocorrelation time;
- ESS-style estimate;
- unique sample fraction;
- top-k mass;
- Hamming-distance diversity;
- chain disagreement.

Runtime:

- compile time;
- sample time;
- diagnostics time;
- samples/sec;
- device/memory.

## Autocorrelation

For scalar trace `x_t`:

```text
rho_k = corr(x_t, x_{t+k})
tau = 1 + 2 * sum_{k=1..K} rho_k
ESS = N / tau
```

Use robust truncation; do not sum noisy long-lag tails. The implemented truncation is the
Geyer initial-positive-sequence rule with the monotone pair-averaging clamp on half-split
chains, exactly as pinned in EVAL-EQ-008 (the arviz v0.21.0 / Stan lineage, cross-validated
to `1e-9` and against an R-`posterior` reference to `1e-8`). Sokal windowing (emcee) is a
systematically different truncation and a named kill target of the golden fixtures; so is
the factor-of-2 tau convention (`1/2 + sum rho`).

Initial scalar traces:

- energy;
- magnetization;
- constraint violation count;
- distance to best state;
- unpenalized objective when available.

## R-hat Caveat

Use R-hat-style checks only as chain-disagreement warnings. Low R-hat does not prove optimality.

## Diversity

Report:

- unique states;
- unique fraction;
- top-1 mass;
- top-10 mass;
- entropy;
- mean pairwise Hamming distance;
- distance-to-best distribution.

## Constraint Diagnostics

Report:

- feasibility rate;
- broken constraints per sample;
- violation magnitude;
- best feasible energy;
- best infeasible energy;
- penalty contribution if available.

## Failure Flags

Implemented (v0, canonical order):

- `mode_collapse`
- `low_diversity`
- `low_ess`
- `poor_mixing`
- `chain_disagreement` (numeric R-hat above threshold, or zero within-chain variance)
- `no_recent_improvement`
- `zero_energy_variance`
- `zero_within_chain_variance`
- `insufficient_diagnostic_data`

Reserved names (schema-stable, awaiting their layers):

- `low_feasibility`
- `bad_schedule`
- `block_stuck`
- `conversion_unverified`

## Output Schema

```python
diagnostics = {
    "energy": {...},        # count/min/max/mean/variance, best, improvements, tau, ESS
    "diversity": {...},     # unique fraction, top-k mass, entropy (nats), Hamming
    "chains": {...},        # chain means/variances, unsplit B, split R-hat, ESS
    "constraints": {"status": "not_available"},  # until the penalty layer
    "runtime": {...},       # lower/sample/diagnostics seconds, reads_per_second, device
    "flags": [...],         # union across families, canonical order
    "thresholds": {...},    # echo of every trigger constant
}
```
