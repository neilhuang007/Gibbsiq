# Roadmap

## Status (updated 2026-07-02)

The roadmap is THRML-first. Gibbsiq is the optimization infrastructure and trust layer above
THRML. Diagnostics, dimod compatibility, and baseline adapters exist to make THRML-backed
optimization auditable and comparable; they do not replace the THRML execution path. The
durable contribution is independent verification and diagnostics, which a hardware vendor
cannot credibly supply for its own device; the `SampleResult` schema, diagnostic inputs, and
benchmark oracle are kept backend-portable at the architectural level as a hedge, without
changing the THRML-first execution target. The 2026-07-01 positioning decision is journaled in
`reference/research-journal/2026-07-01-trust-layer-positioning.md`.

| Stage | Title | Status |
| --- | --- | --- |
| 0 | [Research and framing](stage-00-research-and-framing.md) | Complete — research pack, evaluator, strict benchmark oracle, ground-truth corpus |
| 1 | [Core model compatibility](stage-01-core-model-compatibility.md) | Complete (2026-06-01) — `compile_qubo`/`compile_ising`/`compile_bqm`, Ising IR, `SampleResult`; 55 tests passed at completion; current suite has 149 tests |
| 2 | [THRML optimization runtime](stage-02-thrml-optimization-runtime.md) | Complete (2026-07-01) — `THRMLSampler`, audited lowering, deterministic DSATUR graph-coloring blocks, schedule/seed/init control, vmapped multi-chain traces, independent energy recomputation, exhaustive small-instance validation; remaining: parallel-tempering execution |
| 3 | [Diagnostics pipeline](stage-03-diagnostics-pipeline.md) | Complete (2026-07-02; SOTA-aligned 2026-07-03) — `src/gibbsiq/diagnostics.py` (pure stdlib): Geyer ESS/tau and split R-hat cross-validated against arviz (486 cases, `1e-9`) and an R-`posterior` reference (`4.9e-15` worst rel. err.), rank-normalized + folded split R-hat under separate keys (EVAL-EQ-013, arviz `method="rank"` parity at machine precision), magnetization chain-disagreement wiring closing the equal-energy double-well blind spot, diversity/energy/chain sections, family-scoped failure flags, thresholds echo, magnetization and distance-to-best traces, every `sample()` call embeds the payload; 4 new golden fixtures with a mutation-kill matrix |
| 4 | [Inspector and reporting](stage-04-inspector-and-reporting.md) | Pending |
| 5 | [Baselines and benchmarks](stage-05-baselines-and-benchmarks.md) | Pending |
| 6 | [Adaptive hardware-aware runtime](stage-06-adaptive-hardware-runtime.md) | Pending |

Progress follows the staged order. Stages 0–3 are complete. Stage 3 (diagnostics) landed on
2026-07-02: every THRML run emits the full telemetry payload, synthetic failure fixtures
trigger their expected flags, and the ESS/R-hat implementations are anchored to external
references (journal: `2026-07-02-stage-03-diagnostics-pipeline.md`). The 2026-07-03
validation sweep characterized and same-day closed two blind spots — variance-only chain
disagreement (rank-normalized + folded split R-hat, EVAL-EQ-013) and equal-energy
double-well trapping (magnetization chain-disagreement wiring) — with all frozen goldens
bit-identical (journal: `2026-07-03-stage-03-sota-alignment.md`). Stage 4 (inspector and
reporting) is the current target. Parallel-tempering execution remains the open Stage 2 exit
criterion; when it lands, diagnostics move to per-constant-beta segments per the EVAL-EQ-007
stationarity contract.

Stage 1 carry-over items, tracked in the journal and not blocking Stage 2: hidden-style
metamorphic tests (variable relabel, offset shift, spin-gauge), a `to_qubo()` reverse
conversion for baseline adapters, and a `dimod` integration test in an optional environment.

## Dependencies

```text
0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6
```

Work unblocked by Stage 1 and available to start in parallel, provided it supports the
THRML-first direction:

- diagnostics from fixtures and THRML-style traces;
- benchmark loaders;
- inspector from mock `SampleResult` artifacts (the schema exists).

## Adoption and ecosystem

Adoption surface is an explicit parallel-track concern alongside the numbered stages, not a
new stage in the dependency chain. Three workstreams run in parallel with Stage 2 and later
stages:

- Flagship examples that reproduce third-party THRML optimization results with Gibbsiq
  diagnostics attached: the portfolio index-tracking setup of arXiv:2601.07792 (Jan 2026) and
  the Max-k-Cut Potts study of arXiv:2605.06425. Each example runs the published instance
  through the Gibbsiq path and reports sampler-health diagnostics and witness-verified
  objectives.
- Upstream THRML contributions, focused on the parallel-tempering and sampler-abstraction
  area under discussion in THRML PR #30, so that the beta-ladder and multi-chain composition
  Gibbsiq depends on is available in the substrate.
- Publishing the ground-truth corpus (Tier A proven optima) as a standalone independent
  verification suite for Ising-machine solvers, usable outside the THRML path.

These items support the THRML-first direction and the independent-verification moat; they are
sequenced opportunistically rather than gated on the Stage 2-6 order.

