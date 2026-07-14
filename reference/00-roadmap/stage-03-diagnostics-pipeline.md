# Stage 3 - Diagnostics Pipeline

**Status: Core complete; statistical and constraint extensions open (2026-07-14).** The pipeline is
implemented in `src/gibbsiq/diagnostics.py` and wired into `THRMLSampler.sample`; the recorded
ESS/R-hat formula cross-checks remain valid. The corrective patch removes the unsupported
raw-ESS threshold, reports occupancy efficiency under an accurate name, and separates
finite-support or constant-objective observations from sampler failures. Targeted fixtures and
the full suite passed in the 2026-07-14 verification record. Rank-normalized bulk/tail ESS and
complete joint-mode coverage remain absent. The constraint
feasibility summary reports `not_available`
until the penalty/one-hot encoding layer exists, and the unpenalized-objective trace waits on
the same layer.

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
- Constraint feasibility summary with explicit `not_available` status until the encoding
  contract exists.
- Failure flags.

## Exit Criteria

- Every THRML run emits diagnostics.
- Baseline outputs can use applicable diagnostics when the data semantics match.
- Synthetic failure fixtures trigger expected flags.
- Diagnostics serialize into result artifacts.
- Diagnostics consume the raw samples and traces emitted by Stage 2 without rerunning the
  sampler.
- Thresholds name and match their estimator variant; raw-energy ESS does not use the
  rank-normalized bulk/tail ESS recommendation.
- Observable and progress statuses are separated from sampler-failure flags on flat objectives
  and fully explored small state spaces.

The implemented core meets these criteria with the documented `not_available` constraint
state. Rank-normalized bulk/tail ESS, nested R-hat for many short chains, and broader
joint-mode checks are follow-on statistical work.

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
