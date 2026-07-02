# Diagnostics

Diagnostics in Gibbsiq are THRML runtime telemetry. They summarize the sample distribution
and scalar traces produced by a run. They are required because a stochastic optimizer can
return a low-energy sample even when the chain is collapsed, highly autocorrelated, or stuck
in one mode. Diagnostics warn about those failure modes; they do not prove optimality.

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

Use robust truncation; do not sum noisy long-lag tails.

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

- `poor_mixing`
- `low_ess`
- `chain_disagreement`
- `mode_collapse`
- `no_recent_improvement`
- `low_feasibility`
- `bad_schedule`
- `block_stuck`
- `conversion_unverified`

## Output Schema

```python
diagnostics = {
    "energy": {...},
    "diversity": {...},
    "chains": {...},
    "constraints": {...},
    "runtime": {...},
    "flags": [...],
}
```
