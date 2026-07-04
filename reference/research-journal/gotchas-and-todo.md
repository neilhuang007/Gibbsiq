# Gotchas and open TODOs

A working list of the traps that have bitten this project and the work still open,
kept so an agent picking up Gibbsiq avoids re-learning each pitfall from a failing
test or a broken render. Entries point to the authoritative source rather than
restating it, so the canonical contracts stay in one place.

Keep this file live. When a pitfall costs time, add a row with the fix and a
pointer. When a TODO closes, record it in a dated journal entry and delete it here;
this file tracks what is open, the journal records what was done.

## Writing and journaling gotchas

- **A design decision was made and no journal entry was written.** Every session
  that makes a choice, runs an experiment, resolves a hard point, or shifts
  positioning leaves a dated entry under `reference/research-journal/`
  (`CLAUDE.md` -> "Research journal"). Reasoning that lives only in code and git
  history is lost to the paper.
- **Editing an old entry to reflect a new decision.** Entries are append-only: add
  a new dated entry. Refining the prose of an old entry is allowed; its facts,
  numbers, and recorded decisions stay as they were on that date (`style.md`).
- **Emoji, rhetorical `**bold**` / `*italic*`, or ALL-CAPS for emphasis.** The
  paper register uses none; a symbol is not an argument. Use status words
  ("Complete / Current target / Pending") and let precise nouns carry weight
  (`style.md`).
- **"not X but Y" framing.** State the positive fact or the required next action.
  Record the genuine rejected path under "Rejected Alternatives," not inline as a
  negation (`style.md`).
- **One-line `$$...$$` display math.** It breaks the renderer and cascades to every
  later equation in the file. Write every display equation with `$$` alone on its
  own line, use `\lt` / `\gt` for literal `<` / `>` inside math, and run
  `python tools/check_markdown_math.py` before committing (`CLAUDE.md` -> "Markdown
  LaTeX math formatting").
- **Citing a tool as a source.** Record the primary reference with an identifier
  (arXiv, DOI, `file:line`, a repository commit), not the search or extraction tool
  that surfaced it.

## Engineering gotchas

Energy convention and conversion (`CLAUDE.md` -> "Canonical conventions";
`reference/08-evaluation/equation-audit.md`):

- **Gibbs sign.** The single-site conditional is `sigmoid(-2 * beta * gamma_i)`
  with `gamma_i = h_i + sum_j J_ij s_j`. The sign is the most frequent bug class
  here; validate against the exact fixtures before anything else.
- **Offset preservation.** Carry the offset through every QUBO↔Ising conversion
  and report it in `best_energy` and metadata. Dropping it is a hard evaluation
  failure.
- **Upper-triangle quadratic terms.** Never double-count. Sum symmetric duplicate
  `(i,j)` / `(j,i)` QUBO entries before applying the upper-triangle formula, and
  fold Ising diagonal self-terms into the offset because `s_i^2 = 1`
  (`2026-06-01`, `2026-06-02`).

THRML runtime (`2026-07-01-stage-02-thrml-runtime-implementation.md`):

- **Sign mapping into THRML.** `IsingEBM` samples `exp(-E_thrml)` with
  `E_thrml = -beta (sum b_i s_i + sum w_ij s_i s_j)`, so matching Gibbsiq's
  convention requires `b = -h` and `w = -J`; boolean `True` means `+1`. Recompute
  every reported energy through `IsingModel.energy`; never read energies back from
  THRML.
- **Edgeless models raise `IndexError`.** `IsingEBM.factors` unconditionally builds
  a coupling factor and indexes `edges[0]` (`thrml/models/ising.py` line 75,
  `discrete_ebm.py` line 104), so a fields-only model crashes. Use the private
  coupling-dropping `IsingEBM` subclass.
- **Zero-dependency core.** Reproduce needed algorithms in the standard library
  (DSATUR coloring in `blocks.py`, `statistics.NormalDist().inv_cdf` in place of
  scipy `ndtri`); THRML, dimod, and arviz are optional extras. Do not add numpy,
  networkx, or scipy to the core.

Diagnostics (`2026-07-02-stage-03-diagnostics-pipeline.md`,
`2026-07-03-stage-03-sota-alignment.md`):

- **R-hat variant mixing is the top false-comparison bug.** Plain split R-hat,
  rank-normalized, and `max(rank, folded)` are distinct estimands. The reported
  `rhat` key is the frozen plain split variant; rank-normalized and folded values
  live under separate `rank_normalized_rhat*` keys (EVAL-EQ-013). Never compare a
  value from one variant against another.
- **tau factor-of-two convention.** Use `tau = 1 + 2 sum rho` (arviz, EVAL-EQ-008),
  not Sokal's `1/2 + sum rho`. The two differ by a factor of two on the same
  summands.
- **A constant trace must not yield a healthy ESS** (Non-Negotiable Failure Case).
  arviz returns array-size ESS, `Inf`, or `NaN` on constant / zero-variance /
  too-short inputs; map each to an explicit status
  (`constant_trace`, `undefined_or_infinite_zero_within_variance`,
  `insufficient_data`) and keep `NaN` / `Inf` out of serialized JSON.
- **Flag multisets are frozen goldens.** `required_flags` is compared as a family-
  scoped multiset. A whole-orchestrator pass that unions extra flags breaks the
  frozen fixtures (H4); scope each flag to the telemetry family its `input` block
  declares.
- **Constant-beta window assumption.** Trace-window diagnostics assume a constant-
  beta collection window (EVAL-EQ-007), which the runtime guarantees today. When
  parallel tempering lands, compute diagnostics per constant-beta segment keyed off
  `traces["beta_schedule"]`.
- **Folded R-hat median tie knife-edge.** Never pin a folded R-hat value produced
  from continuous data whose central order statistics tie; the folded component is
  invariant only up to a rounding-level knife-edge (`2026-07-03` H5).
- **Same-well trapping is invisible to within-sample diagnostics.** Chains stuck in
  the same well pass every within-sample metric; defenses are extrinsic
  (overdispersed inits, multi-seed, parallel-tempering swap statistics)
  (`2026-07-03` H7).

Benchmarks and scoring (`2026-05-31-ground-truth-test-set.md`):

- **Never trust candidate-reported numbers.** The oracle recomputes each witness
  objective from the input model; adapters read only the `input` block, never
  `expected`, so a candidate cannot echo proven values.
- **BiqMac / OR-Library QUBO is stated as maximization.** Gibbsiq minimizes, so any
  Tier B import must sign-flip and be re-checked against the equation audit
  (`2026-05-31` §10).
- **C₄ Max-Cut is 4, not 2.** A discarded intermediate note claimed 2; the
  closed-form cross-check would raise on it (`2026-05-31` §5).

## Open TODOs

By stage (status source: `reference/00-roadmap/README.md` and the journal
follow-up sections):

- **Stage 2 exit criterion — parallel tempering execution.** Code for opt-in
  PT landed on 2026-07-04, with cold-slot samples, swap traces, and per-beta
  energy traces. The exit criterion remains open until the optional THRML
  runtime tests run in an environment with `thrml` installed and pass. Upstream
  composition point: THRML PR #30 (beta-ladder / sampler abstraction).
- **Stage 1 bridge gap — penalty / one-hot encoding layer.** Knapsack and TSP
  fixtures raise `NotImplementedError` in `benchmark_bridge.py` until this exists;
  the diagnostics `constraints` section reports `{"status": "not_available"}`
  meanwhile.
- **Stage 4 — Inspector.** `Inspector.from_result(result).show()` for
  topology/trace/diagnostic reports and baseline comparison; consumes
  `diagnostics["thresholds"]` to render tables without recomputation.
- **Stage 5 — baselines and benchmarks.** dwave-samplers (not neal), OpenJij, and
  simulated-bifurcation adapters under the same energy convention and seeds;
  budget-minimized time-to-solution, success probability, and residual energy
  metrics; import the proven-optimal Tier B subsets (BiqMac / TSPLIB / QAPLIB) with
  the maximization sign-flip.
- **Stage 6 — adaptive hardware runtime; nested R-hat.** Nested R-hat (Margossian
  et al. 2021, arXiv:2110.13017) for the many-short-vmapped-chains regime.
- **Optional-extra tier — R\* diagnostic.** Classifier-based R\* needs a learned
  classifier, which conflicts with the zero-dependency core; admit only as an
  optional extra.

Recently closed (prune once absorbed into the roadmap): rank-normalized + folded
split R-hat (EVAL-EQ-013) and magnetization chain-disagreement wiring landed
2026-07-03; see `2026-07-03-stage-03-sota-alignment.md`.
