# Stage 3 - Diagnostics Pipeline

**Status: complete (2026-07-02).** Implemented in `src/gibbsiq/diagnostics.py` and wired
into `THRMLSampler.sample`; audited in EVAL-EQ-007/008/011/012; journaled in
`reference/research-journal/2026-07-02-stage-03-diagnostics-pipeline.md`. The constraint
feasibility summary reports `not_available` until the penalty/one-hot encoding layer exists,
and the unpenalized-objective trace waits on the same layer. When parallel tempering lands
(open Stage 2 exit criterion), diagnostics move to per-constant-beta segments.

## Goal

Compute sampler-health metrics from THRML-backed samples, traces, and metadata. Diagnostics
summarize whether the Markov chains produced useful evidence. They do not certify
optimality; exact or independently verified oracles do that for benchmark instances.

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
- Baseline outputs can use applicable diagnostics when the data semantics match.
- Synthetic failure fixtures trigger expected flags.
- Diagnostics serialize into result artifacts.
- Diagnostics consume the raw samples and traces emitted by Stage 2 without rerunning the
  sampler.

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
