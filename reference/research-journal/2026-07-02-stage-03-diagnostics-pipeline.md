# 2026-07-02 - Stage 3 Diagnostics Pipeline

## Paper Hook

Feeds the methods and validation sections: how Gibbsiq computes sampler-health telemetry
(ESS, split R-hat, diversity, failure flags) from THRML run output, why every metric is
anchored to external reference implementations and analytic ground truth, and why the
diagnostics contract is the layer a hardware vendor cannot credibly self-supply.

## Context

Stages 0-2 shipped the audited IR, the strict benchmark oracle, and the THRML block-Gibbs
runtime. Stage 3 adds the diagnostics layer: every `THRMLSampler.sample()` call now embeds a
full telemetry payload computed purely from the samples, traces, and metadata already in
`SampleResult`, without rerunning the sampler. The layer is pure stdlib
(`src/gibbsiq/diagnostics.py`), keeping the zero-dependency core, and is backend-portable:
it consumes plain energy chains and sample mappings, so the identical contract scores THRML
today, TSU hardware later, and any baseline sampler.

## Hard-Parts Analysis

Six points required dedicated design or engineering; the resolutions below are binding.

### H1. Inference diagnostics on optimization runs (stationarity contract)

ESS, tau, and R-hat assume chains target a fixed distribution; an annealing trace breaks
that assumption and would make split R-hat flag every healthy run. Grounding in the code
resolved it: `thrml_runtime.py` anneals only during warmup (`warmup_beta_ladder`), and every
recorded read is collected at constant `config.beta`. The stationarity precondition
therefore holds by construction. The stated contract: trace-window diagnostics assume a
constant-beta collection window; the runtime guarantees it; when in-sampling schedules land
(parallel tempering, the open Stage 2 exit criterion), diagnostics must be computed per
constant-beta segment keyed off `traces["beta_schedule"]`. With this contract, split R-hat
on the sampling trace detects unequilibrated reads (warmup too short) or multimodal
trapping, both actionable. Recorded in EVAL-EQ-007.

### H2. Flag semantics for optimizers, not posteriors

Vehtari's thresholds target posterior-expectation accuracy; an optimizer that concentrates
reads on the optimum is succeeding, not collapsing. Flags are therefore telemetry warnings
with documented optimization-context meanings, never pass/fail verdicts: `mode_collapse`
means the reads carry almost no distributional information; `no_recent_improvement` means
the second half of the read budget bought nothing; `chain_disagreement` means the reads
depend on initialization and energies should be treated as biased. Thresholds are named
constants echoed in every payload under `diagnostics["thresholds"]` so downstream consumers
can reinterpret without rerunning.

### H3. Bit-compatible reimplementation of a floating-point reference

Goldens pinned at `1e-9` require the pure-Python ESS to reproduce arviz's FFT-based
pipeline. Four tail rules caused all observed divergence: the Geyer loop bound
(`t \lt n_draw - 3`), the monotone pair-averaging clamp, the final `rho[max_t + 1]` term,
and the tau floor `1 / log10(M' N')`, plus the biased `1/N` autocovariance about per-chain
means and the raw-draws validity gate. The port is algorithm-step-level, not behavioral
approximation, and was verified three independent ways before any golden was pinned (see
Verification).

### H4. Frozen goldens as a constraint system (family scoping)

The evaluator compares `required_flags` as an exact multiset and the three frozen fixtures
predate the full metric set: a whole-orchestrator pass computes a floored-tau ESS of about
48 on the frozen zero-within-variance input and would add `low_ess`, silently breaking the
golden. The principled schema rule: a fixture's `input` block declares its telemetry family
(`sample_counts` selects diversity, `energy_trace` selects energy, `chains` selects chains);
`required_flags` is family-scoped; the runtime path unions all families under `"flags"`.
Related: population `within_chain_variances` (frozen fixture math) and the ddof-1 split-chain
`split_within_chain_variance` are distinct estimands kept as distinct keys; conflating them
is the classic R-hat implementation bug.

### H5. Pure-Python diagnostics inside every sample() call

The Geyer scan is O(M N tau); a stuck chain (tau of order N) turns that into O(M N^2). The
implementation advances a lazy per-lag autocovariance only as far as the Geyer loop demands
(well-mixed traces terminate at lag 2-6), with inner products via C-level iteration
(`sum(map(operator.mul, ...))`). Measured on the exhaustive 12000-read Stage 2 validation
configuration: `diagnostics_seconds` = 0.0255 versus `sample_seconds` = 1.262, about 2% of
sampling time. A hard lag cap remains the documented fallback and was deliberately omitted:
it would break arviz cross-checkability on exactly the high-tau inputs it truncates.

### H6. Goldens only a correct implementation can pass (mutation-kill matrix)

| Fixture / test | Kills |
| --- | --- |
| `autocorrelated_energy_trace_ar1` (tau = 12.03 pinned) | Sokal-window tau (different truncation), factor-of-2 tau convention, unbiased `1/(N-t)` autocovariance, missing monotone clamp |
| `chain_disagreement_numeric_rhat` (rhat = sqrt(627/28)) | rank-normalized R-hat, folded R-hat, unsplit R-hat (5.507 on the same input), ddof-0 split W, wrong B scaling |
| `healthy_multichain_energy_trace` (flags exactly `[]`) | always-flagging and threshold-free implementations |
| `insufficient_data_short_trace` (3 draws) | crash-on-short, NaN/Inf leaking into JSON, missing raw-draws validity gate |
| Frozen diversity fixture | log2 entropy, Hamming excluding same-state pairs |
| Metamorphic permutation test | order-blind pseudo-ESS (any sample-multiset statistic posing as ESS) |
| Adapter echo-proofing (`diagnostic_candidate_from_input` reads only `input`) | candidates that parrot `expected` blocks |

## Technical Moat

1. Audited, externally anchored verification a vendor cannot self-supply. Every metric
   traces to an equation-audit entry and is cross-validated against the Stan/ArviZ-lineage
   reference implementations, an R-`posterior` golden CSV, and analytic ground truth. A
   hardware vendor reporting its own sampler-health numbers has a structural conflict of
   interest; an independent layer whose numbers anyone can recompute does not. The moat is
   the audit trail, not the formulas.
2. The optimization-context diagnostics contract (H1/H2) is novel design space. MCMC
   diagnostics literature is inference-focused; sampler-health telemetry for annealed
   optimizers with a schedule-aware stationarity contract has no incumbent, so a precisely
   specified, fixture-pinned contract sets the de-facto semantics.
3. Echo-proof, mutation-killing evaluation (H6). The harness certifies implementations, not
   outputs: adapters read only inputs, the oracle recomputes witnesses, goldens kill named
   wrong variants. The suite itself is publishable as the roadmap's independent-verification
   artifact for Ising-machine solvers.
4. Contract-level backend portability. Diagnostics consume plain traces and samples, so the
   identical contract scores THRML, TSU hardware, and competitor samplers - the
   neutral-referee position architecturally closed to Extropic per the 2026-07-01
   positioning decision.

## Decisions

- Reported R-hat is the plain split variant (Gelman/BDA3 form on half-split chains), not
  the rank-normalized or folded variants of Vehtari et al. 2021. Optimization energy traces
  are the target quantity itself, frequently discrete and heavy-tailed by construction;
  rank normalization would change pinned values and hide the zero-variance pathologies the
  statuses surface explicitly. The three-way variant distinction (plain split /
  rank-normalized / max(rank, folded)) is documented because mixing variants across
  implementations is the top false-comparison bug.
- Geyer/Vehtari truncation for tau (initial positive sequence plus monotone clamp), not
  emcee's Sokal window (`c = 5`): the two truncations systematically disagree, Geyer is the
  Stan/ArviZ lineage rule, and the fixture pins kill the alternative.
- Tau convention is `tau = 1 + 2 sum rho` (EVAL-EQ-008), matching arviz; Sokal's
  `1/2 + sum rho` convention differs by a factor of 2 on the same summands and is a named
  kill target.
- Deliberate divergence from arviz: constant traces return explicit statuses
  (`constant_trace`, `undefined_constant_trace`) instead of arviz's healthy ESS equal to
  array size, because the Non-Negotiable Failure Cases forbid a constant trace yielding a
  healthy ESS. Same for `undefined_or_infinite_zero_within_variance` where arviz returns
  Inf, and `insufficient_data` where arviz returns NaN. Constant and degenerate inputs are
  excluded from the crosscheck for exactly this reason.
- Entropy is reported in nats; mean pairwise Hamming distance averages over all C(R,2)
  unordered read pairs including same-state pairs (scipy `pdist('hamming')` semantics,
  confirmed against the frozen fixture value 2218/8128); both pinned in EVAL-EQ-011.
- Thresholds: `RHAT_THRESHOLD = 1.01` and `LOW_ESS_THRESHOLD = 400.0` (Vehtari et al.
  2021); `MODE_COLLAPSE_TOP1_MASS_THRESHOLD = 0.9` and
  `LOW_DIVERSITY_UNIQUE_FRACTION_THRESHOLD = 0.05` (chosen so the frozen diversity fixture
  fires both flags); `POOR_MIXING_MIN_TAU_MULTIPLES = 50.0` (emcee tutorial guidance that
  estimates are untrustworthy below roughly 50 tau); `MIN_DRAWS = 4` on raw draws
  (mirrors arviz); `MIN_CHAINS_FOR_RHAT = 2`.
- Flag vocabulary v0 implements `mode_collapse`, `low_diversity`, `low_ess`, `poor_mixing`,
  `chain_disagreement`, `no_recent_improvement`, `zero_energy_variance`,
  `zero_within_chain_variance`, `insufficient_diagnostic_data`; `low_feasibility`,
  `bad_schedule`, `block_stuck`, `conversion_unverified` are reserved names for the penalty,
  schedule, and conversion layers.
- Ragged chains rectangularize by dropping empty chains and truncating to the shared
  minimum length (`num_reads \lt num_chains` yields empty trailing chains in the runtime);
  `num_chains` and `num_chains_used` are both reported.
- New traces wired into the runtime: `magnetization` and `distance_to_best` (EVAL-EQ-012),
  shaped like `traces["energy"]`; the distance trace uses the first-minimal-index tie rule
  matching `SampleResult.best_index`.
- The runtime behavioral tests reproduced fixture C's pathology in the wild: a strong
  asymmetric ferromagnetic ring at high beta traps chains in both wells, each chain constant
  at its well bottom, producing `undefined_or_infinite_zero_within_variance` plus
  `chain_disagreement` - the synthetic golden and the physical failure mode agree.

## Rejected Alternatives

- numpy as a runtime dependency: declined; the core stays zero-dependency and the direct
  summation port agrees with arviz's FFT pipeline to machine precision at these lengths.
- Sokal windowing for tau and emcee `integrated_time`: declined as the reported estimator
  (systematically different truncation); retained only as a named kill target.
- Rank-normalized R-hat as the reported value: declined for optimization traces (see
  Decisions); may join later as a separately named key.
- Whole-orchestrator fixture flags: declined; breaks frozen goldens (H4).
- arviz's constant-trace ESS short-circuit: declined; violates the evaluation contract.
- A preemptive Geyer lag cap: declined; would break crosscheckability on high-tau inputs.

## Sources Read

- Vehtari, Gelman, Simpson, Carpenter, Buerkner (2021), "Rank-normalization, folding, and
  localization: an improved R-hat for assessing convergence of MCMC", Bayesian Analysis
  16(2):667-718, arXiv:1903.08008; also the companion notebook site
  avehtari.github.io/rhat_ess (thresholds R-hat below 1.01, ESS above 400).
- Geyer (1992), "Practical Markov Chain Monte Carlo", Statistical Science 7(4):473-483
  (initial positive sequence and initial monotone sequence estimators).
- Stan Reference Manual, "Effective Sample Size" section (Geyer IPS/IMS as implemented by
  the Stan/ArviZ lineage).
- Sokal (1989/1997), "Monte Carlo Methods in Statistical Mechanics: Foundations and New
  Algorithms" (windowed tau; the factor-of-2 convention trap).
- Thompson (2010), "A Comparison of Methods for Computing Autocorrelation Time",
  arXiv:1011.0175 (analytic AR(1) tau equation 7: tau = (1+phi)/(1-phi)).
- emcee documentation, autocorrelation tutorial (Sokal window `c = 5`; the 50-tau
  trustworthiness guidance behind `POOR_MIXING_MIN_TAU_MULTIPLES`).
- ArviZ Exploratory Analysis of Bayesian Models, MCMC diagnostics chapter (trap-case
  behaviors reproduced in the metamorphic tests).
- arviz v0.21.0 source tag: `arviz/stats/diagnostics.py` (`_ess`, `_rhat`,
  `_split_chains`, `_z_scale`) and `arviz/stats/stats_utils.py` (`autocov`, `not_valid`).
  The installed runtime package is arviz 1.2.0 (which re-exports `arviz-stats`); the
  algorithm was pinned to the v0.21.0 tag because `main` refactored the implementation out
  of the repository.
- arviz v0.21.0 test data for the external anchor
  (`arviz/tests/saved_models/stan_diagnostics/`): `reference_posterior.csv` (SHA256
  `A706218948C58D2597485DBD02276D42CB2FFF01FF25984217CA6E94BE315CBA`), `blocker.1.csv`
  (SHA256 `57827A11CBEA2B9F3BC326B742C05D15A96B869240AF5B639826B427548E6D30`),
  `blocker.2.csv` (SHA256 `1955002639BE5C61A5B2BE34B7D4D1F1DEAF2346A89A4B03587F3A3A1AFD5C7F`),
  values generated with R `posterior`; arviz's own suite asserts agreement to `1e-8`.

## Examples Used

- Frozen fixtures in `reference/08-evaluation/fixtures/diagnostic-fixtures.json` as the
  binding constraint system (H4).
- The fixture C construction (repeated 2-cycles so split halves are identical) was designed
  so the split R-hat is hand-exact: chain means [1, 2, 11, 12], population within-chain
  variances [1, 1, 1, 1], unsplit B = 808/3, split W = 4/3, split B = 808/7,
  rhat = sqrt(627/28), approximately 4.7321; the unsplit value 5.507 on the same input is
  the no-split kill.
- Fixture A/B arrays generated with seeded stdlib generators (`random.Random(0)`),
  chain-major; recipes and seeds recorded in the fixture `purpose` fields and the
  cross-validation script.

## Follow-Up

- Parallel tempering remains the open Stage 2 exit criterion; when it lands, diagnostics
  move to per-constant-beta segments keyed off `traces["beta_schedule"]` (H1 contract).
- The `constraints` section reports `{"status": "not_available"}` until the penalty/one-hot
  encoding layer exists (knapsack/TSP bridge gap from Stage 1).
- Stage 4 Inspector consumes `diagnostics["thresholds"]` to render report tables without
  recomputation.
- Baseline samplers (dwave-samplers, OpenJij) can reuse the identical contract once the
  baseline layer lands; the diagnostics functions already accept plain chains.

## Verification

- arviz crosscheck: 486 seeded comparison cases (60 seeds by 8 shapes including 2x8, 1x9,
  3x4, 2x5, 4x16, 2x100, 4x250, 1x1000; AR(1) phi in {0.5, 0.9, 0.99} at 4x2000;
  deterministic 2x8; the frozen zero-within-variance input; fixture C), zero failures at
  relative `1e-9` for ESS/tau and absolute `1e-9` for R-hat.
- External anchor: the R-`posterior` blocker reference (48 parameters, 2 chains by 1000
  draws) - our `ess_mean`, unsplit `ess_raw`, and unsplit `rhat_raw` agree with the
  reference CSV on all 144 comparisons with worst relative error `4.9e-15`, tighter than
  the `1e-8` arviz itself asserts.
- Hand derivations: fixture C rhat = sqrt(627/28) exact; fixture D variance = 2/3 exact;
  frozen diversity fixture entropy and Hamming values reproduced by scipy
  (`stats.entropy`, `pdist('hamming')`) exactly.
- Analytic ground truth: AR(1) tau intervals (phi 0 to 1, 0.5 to 3, 0.9 to 19, -0.5 to 1/3)
  validated in the metamorphic suite with seeded generators and predeclared intervals.
- Performance (H5): `diagnostics_seconds` = 0.0255 on the 12000-read exhaustive validation
  configuration, about 2% of `sample_seconds` = 1.262.
- Full unit suite and `gibbsiq-evaluate` on the example candidate: 12 exact plus diagnostic
  fixtures pass; exit 1 persists only for the pre-existing 27 missing benchmark rows.
