# Roadmap

## Status (updated 2026-06-02)

| Stage | Title | Status |
| --- | --- | --- |
| 0 | [Research and framing](stage-00-research-and-framing.md) | Complete — research pack, evaluator, strict benchmark oracle, ground-truth corpus |
| 1 | [Core model compatibility](stage-01-core-model-compatibility.md) | Complete (2026-06-01) — `compile_qubo`/`compile_ising`/`compile_bqm`, Ising IR, `SampleResult`; 55 tests pass |
| 2 | [First THRML sampler](stage-02-first-thrml-sampler.md) | Current target |
| 3 | [Diagnostics pipeline](stage-03-diagnostics-pipeline.md) | Pending |
| 4 | [Inspector and reporting](stage-04-inspector-and-reporting.md) | Pending |
| 5 | [Baselines and benchmarks](stage-05-baselines-and-benchmarks.md) | Pending |
| 6 | [Adaptive hardware-aware runtime](stage-06-adaptive-hardware-runtime.md) | Pending |

Progress follows the staged order. Stages 0–1 are complete; Stage 2 (lowering the Ising IR
into a THRML block-Gibbs run) is the current target.

Stage 1 carry-over items, tracked in the journal and not blocking Stage 2: hidden-style
metamorphic tests (variable relabel, offset shift, spin-gauge), a `to_qubo()` reverse
conversion for baseline adapters, and a `dimod` integration test in an optional environment.

## Dependencies

```text
0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6
```

Work unblocked by Stage 1 and available to start in parallel:

- diagnostics from fixtures;
- benchmark loaders;
- inspector from mock `SampleResult` artifacts (the schema exists).

