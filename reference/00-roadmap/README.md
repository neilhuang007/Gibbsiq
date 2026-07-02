# Roadmap

## Status (updated 2026-07-01)

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
| 1 | [Core model compatibility](stage-01-core-model-compatibility.md) | Complete (2026-06-01) — `compile_qubo`/`compile_ising`/`compile_bqm`, Ising IR, `SampleResult`; 55 tests passed at completion; current suite has 128 tests |
| 2 | [THRML optimization runtime](stage-02-thrml-optimization-runtime.md) | Complete (2026-07-01) — `THRMLSampler`, audited lowering, deterministic DSATUR graph-coloring blocks, schedule/seed/init control, vmapped multi-chain traces, independent energy recomputation, exhaustive small-instance validation; remaining: parallel-tempering execution |
| 3 | [Diagnostics pipeline](stage-03-diagnostics-pipeline.md) | Pending |
| 4 | [Inspector and reporting](stage-04-inspector-and-reporting.md) | Pending |
| 5 | [Baselines and benchmarks](stage-05-baselines-and-benchmarks.md) | Pending |
| 6 | [Adaptive hardware-aware runtime](stage-06-adaptive-hardware-runtime.md) | Pending |

Progress follows the staged order. Stages 0–2 are complete. Stage 2 (lowering the Ising IR
into THRML programs with block construction, schedule control, seeds, and trace capture) landed
on 2026-07-01 with exhaustive small-instance validation and parallel-tempering execution as
open exit criteria; Stage 3 (diagnostics) is the current target.

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

