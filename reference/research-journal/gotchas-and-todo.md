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
- **Treating generated Markdown as a faithful paper transcription.** A sentence-level audit of
  the Jelinčič derivative found invented circuitry and unit errors of at least 6 to 12 orders
  of magnitude. The primary PDF is authoritative; every derivative declares its provenance,
  and quantitative claims carry a PDF page or equation
  (`2026-07-11-primary-source-integrity-audit.md`).

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
- **Parallel-tempering correctness closed on 2026-07-14; preserve its invariants.** The
  2026-07-11 audit exposed exchange-sign, missing-local-transition, and two-replica pairing
  failures. The 2026-07-14 correction verifies EVAL-EQ-014, advances every replica between
  exchange opportunities, attempts the sole two-replica pair at every interval, and records
  cold-slot and per-beta evidence. Preserve those tests when changing the runtime
  (`2026-07-14-runtime-sampling-and-frozen-mode-correctness.md`). Device-side/vectorized
  exchange and adaptive ladder tuning are performance extensions; they require an assigned
  roadmap task before implementation.

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
- **Retained diagnostics use one target-beta collection law.** Fixed-beta warmup segments are
  discarded, and retained reads use `config.beta`. Parallel tempering evolves the full ladder,
  then returns only the cold-slot samples at `config.beta`; `compute_diagnostics` consumes
  those cold-slot interaction-energy and magnetization chains. `traces["beta_schedule"]`
  records `target_beta`, while `traces["parallel_tempering"]` stores per-beta energies and swap
  evidence. Do not pass per-beta telemetry to the current chain diagnostics as if it were a set
  of independent retained chains; such a change requires a new equation and trace contract
  (EVAL-EQ-007; `thrml_runtime.py:1135-1226`).
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

Open implementation work is selected by stable task ID from
`reference/00-roadmap/autonomous-implementation-roadmap.md` and claimed through
`reference/00-roadmap/NEXT_TASK.md`. This list names residual mechanisms. The live ledger
remains the only task queue.

- **General constraints and feasibility — `TM-LWR-001`.** Knapsack and TSP fixtures raise
  `NotImplementedError` in `benchmark_bridge.py`; diagnostics report
  `{"status": "not_available"}` until a checked encoding and unpenalized-objective contract
  exist.
- **Bulk/tail ESS and observable-specific efficiency — `TM-PROF-001`.** The current estimator
  is raw-energy Geyer ESS. Rank-normalized bulk/tail ESS requires separately named outputs,
  independent reference cases, and thresholds matched to that estimator. Joint-mode coverage
  is exercised through `TM-BENCH-002`, `TM-BENCH-003`, and `TM-BENCH-004`; scalar diagnostics
  alone cannot close it.
- **Inspector — `GQ-INSPECT-01` and `TM-REP-001`.** The artifact-only core precedes unified
  CLI, HTML, topology, profiler, and baseline integration.
- **Baselines and benchmarks — `TM-BASE-001`, `TM-BASE-002`, and `TM-BENCH-001` through
  `TM-BENCH-004`.** Solver adapters use the canonical energy and separate fixed-work from
  fixed-time budgets. Proven-optimal Tier B imports retain the BiqMac maximization sign flip.
- **Hardware-aware compiler and non-idealities — `TM-TARGET-01`, `TM-MAP-001` through
  `TM-MAP-003`, `TM-NID-001`, `TM-NID-002`, `TM-COST-001`, and `TM-PROF-001`.** These tasks own
  target topology, automatic mapping, delayed communication, calibrated cost boundaries, and
  quality-adjusted profiling. The existing Stage 6 modules provide analysis inputs rather
  than an adaptive execution layer.
- **Optional diagnostics without a stable task ID.** Nested R-hat for many short vectorized
  chains and classifier-based R\* remain research candidates. The coordinator must add a
  bounded task with dependencies, ownership, an independent oracle, and optional-dependency
  policy before an agent implements either one.
- **Device-side PT performance and upstream composition.** Stage 2 correctness is closed. The
  roadmap currently assigns no standalone device-side PT optimization task. If profiling
  demonstrates that this work is necessary, the coordinator must add a bounded task or place
  the upstream interface artifact under `TM-RFC-001` after its dependencies close.

## Closed Historical Corrections

- **Stage 2 PT corrective audit closed 2026-07-14.** The targeted invariants, optional THRML
  tests, and full-suite record are in
  `2026-07-14-runtime-sampling-and-frozen-mode-correctness.md`.
- **Stage 3 flag-taxonomy corrective audit closed 2026-07-14.** Raw-energy ESS carries no
  borrowed bulk/tail threshold; occupancy efficiency is named accurately; observable and
  progress statuses are separated from sampler failures; top-1 concentration alone yields
  `high_sample_concentration`. Remaining bulk/tail and joint-mode work is routed above.
- **Rank-normalized and folded split R-hat plus magnetization disagreement landed
  2026-07-03.** EVAL-EQ-013 and `2026-07-03-stage-03-sota-alignment.md` retain their formula and
  cross-validation evidence.
