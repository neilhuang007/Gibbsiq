# 2026-07-03 - Stage 3 SOTA Alignment: Rank-Normalized R-hat and Magnetization Wiring

## Paper Hook

Feeds the methods and validation sections: how the two blind spots characterized during the
2026-07-03 validation sweep were closed the same day — the variance-only chain-disagreement
gap via the Vehtari et al. 2021 rank-normalized + folded split R-hat under separately named
keys, and the equal-energy double-well gap via magnetization chain-disagreement wiring — and
why both changes keep every frozen golden bit-identical. Also documents a previously
uncharacterized floating-point knife-edge in the published folding algorithm.

## Context

The 2026-07-03 validation session left two documented blind spots pinned by characterization
tests written to flip when the fixes landed:
`test_plain_rhat_blind_to_variance_only_disagreement_known_limitation` (plain split R-hat
reports 0.9997 on four zero-mean chains whose standard deviations differ by a factor of
100) and `DegenerateDoubleWellBlindSpotTests` (two chains frozen in opposite ground states
of equal energy produce identical constant energy traces, so every energy-trace statistic is
blind while the captured magnetization trace carries the signal). Both fixes shipped today:
`rank_normalized_split_rhat` (EVAL-EQ-013) and the `chains.magnetization` subsection
(EVAL-EQ-007 magnetization wiring). Both characterization tests were flipped per their
embedded instructions. Deferred by prior decision: nested R-hat (Margossian et al.,
arXiv:2110.13017; published as Bayesian Analysis 20(4):1587-1614, 2025,
doi:10.1214/24-BA1453) to Stage 6 with the many-short-vmapped-chains regime; success
probability / residual energy / budget-minimized TTS to Stage 5 with the baselines; R*
(classifier-based, Lambert and Vehtari, Bayesian Analysis 17(2), 2022) to an optional-extra
tier because it requires a learned classifier and conflicts with the zero-dependency core.

## Hard-Parts Analysis

### H1. Port the implementation lineage, never the paper prose

The paper and the shipped reference implementations differ in load-bearing details, so the
port copies arviz v0.21.0 line-by-line (repo cloned locally; `_rhat_rank`, `_z_scale`,
`_backtransform_ranks` in `arviz/stats/diagnostics.py` audited side by side). Binding order
of operations: half-split first, then rank the pooled split draws (per-chain ranking would
erase the between-chain location signal), average ranks on exact-equality ties, Blom
backtransform `(r - 3/8) / (S - 2*(3/8) + 1)`, normal quantile, EVAL-EQ-007 core on the
z-values. The folded component recomputes ranks from scratch on `|x - median(pooled split
draws)|` and the reported value is `max(bulk, folded)`. Same lineage discipline as the
Stage 3 ESS port; recorded as EVAL-EQ-013 before the code changed.

### H2. Stdlib normal quantile at cross-check precision

The zero-dependency core forbids scipy, so the port uses `statistics.NormalDist().inv_cdf`
(Wichura AS 241) where arviz calls Cephes `ndtri`. The audit budgets 1e-8 for the
difference; measured agreement on every fixture, the 60-case seeded gaussian sweep, and the
tie-heavy discrete sweeps is at most 2.2e-16 — the two quantile implementations agree to
machine precision over the rank-bounded argument range, which excludes extreme tails by
construction (arguments lie in `[(1 - 3/8)/(S + 1/4), (S - 3/8)/(S + 1/4)]`).

### H3. Degenerate statuses where arviz returns NaN, inf, or float dust

arviz's rank R-hat returns NaN below the validity gate, NaN on constant arrays, inf when
every split chain is constant at distinct values, and — measured on the double-well
magnetization trace — 9.8e15 of floating-point dust where the exact answer is an infinite
R-hat. Gibbsiq maps each branch to the existing EVAL-EQ-007 status vocabulary
(`insufficient_data`, `undefined_constant_trace`,
`undefined_or_infinite_zero_within_variance`), keeping NaN/Inf out of serialized output. One
branch needed a new rule: when folding collapses to a constant (a balanced two-valued trace
symmetric around the pooled median — a real Ising regime, e.g. an antithetic magnetization
trace), arviz computes `max(bulk, NaN)`, which silently returns the bulk because NaN
comparisons are false. Gibbsiq makes that explicit: `rank_normalized_rhat_folded = null`,
combined value = bulk, status `ok` — numerically identical to arviz on the same bits, and
auditable instead of accidental.

### H4. Heavy ties are the operating regime, not an edge case

An energy or magnetization trace over a small Ising model takes a handful of distinct
values, so almost every draw is tied — far from the continuous posteriors the estimator was
designed for. Average-tie ranking is exact arithmetic, so the estimator degrades gracefully
into a level-occupancy comparison between chains. Cross-checks pin machine-precision
agreement with arviz on two-, three-, and four-level discrete chains, and the iid binary
control (maximally tied input) recovers a healthy near-1 value.

### H5. The median tie knife-edge (new characterization)

Testing affine invariance exposed a property of the published algorithm that neither the
paper nor the reference implementations document: the pooled split count `S = M' * N` is
always even, the pooled median is therefore the average of the two middle order statistics,
and those two draws always fold to exactly equidistant values. Whether they tie bit-exactly
is rounding luck; breaking the tie moves both draws' folded ranks at the steep bottom of the
normal quantile and shifts the folded component at the 1e-6 level (measured: 4e-6 on 800
gaussian draws under `x -> 3.5x - 11`). arviz behaves identically on identical bits, so the
cross-check is unaffected. Binding consequences, recorded in EVAL-EQ-013: the bulk component
is invariant under any strictly increasing transform, the folded component only under
increasing affine maps and only up to the knife-edge, and fixtures must never pin a folded
value produced from continuous data whose central order statistics tie.

### H6. Frozen goldens as the safety rail

Two facts had to be established before any code changed. First, the evaluator's deep-compare
iterates over expected keys only, so new candidate keys are invisible to frozen fixtures.
Second, the flag multisets had to survive: `arviz.rhat(method="rank")` was run on every
frozen chain fixture before implementation — `healthy_multichain_energy_trace` reports
0.9971 (quiet, flags stay `[]`), and both disagreement fixtures fire through the rank path
exactly where the plain path already fired. All seven frozen fixture flag multisets verified
unchanged post-implementation; the evaluator exits 0 on the full 39-fixture run.

### H7. Magnetization wiring scope discipline

The wiring reuses the existing estimators on the already-captured EVAL-EQ-012 trace (zero
new estimator code): `compute_diagnostics` accepts `magnetization_chains`, the runtime
passes `traces["magnetization"]`, and the payload gains a `chains.magnetization` subsection
holding both R-hat variants. Scope rule, recorded in EVAL-EQ-007: the subsection contributes
only `chain_disagreement`; `zero_within_chain_variance` and `insufficient_diagnostic_data`
stay energy-trace-scoped, so a frozen-but-agreeing sampler keeps its exact pinned flag list
(the frozen-sampler end-to-end test still passes with its exact five-flag expectation).
Honest residual caveat, also recorded: chains trapped in the same well remain invisible to
every within-sample diagnostic; defenses are extrinsic (overdispersed inits, multi-seed,
parallel-tempering swap statistics).

## SOTA Currency (independent research sweep, 2026-07-03)

A parallel research sweep over the primary sources (arviz v0.21.0 `diagnostics.py` /
`stats_utils.py`; R `posterior` `convergence.R` / `split_chains.R`; Vehtari et al. 2021,
Bayesian Analysis 16(2):667-718; Stan reference documentation) returned after the
implementation landed and confirmed every load-bearing choice independently: split-then-rank
over the pooled split draws, Blom `c = 3/8` backtransform `(r - 3/8)/(S + 1/4)`, average-tie
ranks, fold-then-re-rank-normalize, `max(bulk, folded)`, validity gate on the pre-split
array (at least 2 chains and 4 raw draws), and constant arrays resolving to an undefined
value through the `0/0` branch in both reference implementations. Rank-normalized + folded
split R-hat at threshold 1.01 with bulk/tail ESS above 400 remains the shipping default
across Stan, arviz, and posterior as of mid-2026; nested R-hat, R*, and local R-hat (Moins
et al., arXiv:2205.06694) are published complements, and none supersedes the default.

The sweep surfaced one fact the port had to record: arviz and posterior fold in DIFFERENT
orders. arviz folds after splitting around the split-array median; posterior folds before
splitting around the raw-draw median. The orderings coincide exactly for even per-chain draw
counts (the split is a reshape of the same multiset) and diverge for odd counts (both drop
each chain's middle draw; only posterior's median includes it). The port pins the arviz
ordering and all rank-variant cross-validation targets arviz, so no shipped number is
affected; the constraint — even draw counts for any future posterior cross-check — is
recorded in EVAL-EQ-013. The sweep also found no upstream issue reports on heavily tied or
discrete inputs; average-tie ranking is documented by the paper as the deliberate mechanism
for conserving the unique values of discrete quantities, with the known consequence that k
distinct trace values give k distinct z-levels (coarse but correct for gross disagreement)
and folding roughly halves the distinct-level count again by collapsing values symmetric
around the median.

## Decisions

1. Separately named keys (`rank_normalized_rhat`, `_bulk`, `_folded`, `_status`); the plain
   `rhat` key keeps its exact meaning and value forever. Both variants share the 1.01
   threshold — Vehtari et al. state that threshold for the rank-normalized diagnostic.
2. `chain_disagreement` fires when either variant on either trace (energy, magnetization)
   exceeds the threshold or hits the zero-within-variance status.
3. The characterization tests were flipped in place with comments recording the flip date
   and the original name, so the history of the blind spot stays greppable.
4. Deferred items unchanged: nested R-hat (Stage 6), success probability / residual energy /
   budget-minimized TTS (Stage 5), R* (optional-extra tier at most).

## Verification

- 265 tests pass (up from 248), including THRML end-to-end; evaluator exits 0 on all 39
  fixtures; `tools/check_markdown_math.py` clean.
- Cross-validation vs `arviz.rhat(method="rank")` at most 2.2e-16 on every defined case:
  frozen fixtures, 60-shape seeded gaussian sweep, AR(1), discrete two/three/four-level
  chains, the variance-only disagreement case, and the folded-collapse case.
- Hand-computed exact values with zero external dependencies: the tied alternating-chain
  case reduces algebraically to `rank_normalized_rhat = sqrt(1/2)` with folded collapse, and
  a shifted tied case recomputes bulk and folded from hand-listed ranks through the audited
  EVAL-EQ-007 core.
- End-to-end on the real sampler: the frustrated-triangle run (validated against exhaustive
  enumeration) reports healthy values on both variants and both traces; the seeded
  double-well run now fires `chain_disagreement` from the payload itself.
