# Stage 3 - Diagnostics Pipeline

## Goal

Compute sampler-health metrics from samples, traces, and metadata.

## Deliverables

- Energy trace summary.
- Best-so-far trace summary.
- Autocorrelation estimate.
- Integrated autocorrelation time.
- ESS-style estimate.
- R-hat-style scalar chain disagreement.
- Unique fraction, top-k mass, entropy.
- Hamming-distance metrics.
- Constraint feasibility summary.
- Failure flags.

## Exit Criteria

- Every THRML run emits diagnostics.
- Baseline outputs can use applicable diagnostics.
- Synthetic failure fixtures trigger expected flags.
- Diagnostics serialize into result artifacts.

## Implementation Notes

Use R-hat/ESS as warnings, not optimality proof.

Initial scalar traces:

- energy;
- magnetization;
- constraint violation count;
- distance to best sample;
- unpenalized objective when available.

## References

- Diagnostics note: ../04-diagnostics/mixing-quality.md
- Vehtari et al.: https://sites.stat.columbia.edu/gelman/research/published/Vehtari_etal_2020_rhat_ess.pdf
- ArviZ diagnostics: https://arviz-devs.github.io/EABM/Chapters/MCMC_diagnostics.html
- ArviZ docs: https://python.arviz.org/
- emcee autocorrelation: https://emcee.readthedocs.io/en/stable/tutorials/autocorr/
- Sampler diagnostics benchmark: https://www.auai.org/uai2018/proceedings/papers/37.pdf

