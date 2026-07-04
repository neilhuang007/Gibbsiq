# 2026-07-04 - Core Performance Baseline

## Paper Hook

Feeds the methods and artifact-quality sections. This entry records the current performance
baseline for core Gibbsiq calculations so future optimizer changes can be compared against a
fixed commit, command, and JSON artifact.

## Context

The user requested a concrete baseline after the algorithm audit. We first committed the
current dirty tree as `1db24b5` so coworker and prior-agent changes were preserved. We then
added a dedicated stdlib benchmark harness in `tools/benchmark_performance_baseline.py` and
committed it as `844e53b`. The baseline run starts from that clean commit and writes an
artifact under `reference/06-benchmarks/artifacts/`.

## Baseline Artifact

Command:

```powershell
py -3 tools/benchmark_performance_baseline.py --repeat 7 --out reference/06-benchmarks/artifacts/performance-baseline-2026-07-04.json
```

Artifact:

- Path: `reference/06-benchmarks/artifacts/performance-baseline-2026-07-04.json`
- Final SHA-256: `01f458e7f6bd5712f587f52ae3608bdd52f76944b6114877852caef1713cae39`
- Payload SHA-256 before checksum field:
  `d3cc8fda194830cdabb9f19c6e89b3688f2ef73202a6d42f45b79a9360d4ec2a`
- Commit recorded by artifact: `844e53b96b0f310b1faa5f3ff3ac98043942ad07`
- Dirty at benchmark start: `false`
- Python recorded by artifact: `3.14.2`
- Platform recorded by artifact: `Windows-11-10.0.26220-SP0`

## Baseline Medians

All times are wall-clock seconds from `time.perf_counter()` and are local to this machine.
They are comparison anchors, not portable performance claims.

| Calculation | Case | Median seconds | Check |
| --- | ---: | ---: | --- |
| `compile_ising` | `n=64`, `87` edges | `0.000202` | `64` variables |
| `compile_ising` | `n=256`, `597` edges | `0.001077` | `256` variables |
| `compile_ising` | `n=512`, `1150` edges | `0.002127` | `512` variables |
| `compile_qubo` | `n=64`, `77` edges | `0.000187` | `64` variables |
| `compile_qubo` | `n=256`, `569` edges | `0.001209` | `256` variables |
| `compile_qubo` | `n=512`, `1119` edges | `0.002422` | `512` variables |
| block coloring cold | `n=500`, `1152` edges | `0.001294` | `4` blocks |
| block coloring cold | `n=1000`, `1730` edges | `0.002098` | `3` blocks |
| block coloring cold | `n=2000`, `3414` edges | `0.004827` | `3` blocks |
| block coloring cached | `n=2000`, `3414` edges | `0.000030` | topology cache |
| energy evaluation | `2000` samples, `256` variables, `586` edges | `0.161868` | direct IR energy |
| local field queries | `2000` queries, `256` variables, `586` edges | `0.093033` | direct coupler scan |
| diagnostics assembly | `4` chains x `512` draws, `2048` samples | `0.028705` | flags `low_ess`, `chain_disagreement` |
| benchmark oracle | `27` fixtures | `0.000458` | `0` failures |
| ground-truth generation | `27` fixtures | `0.147175` | checksum `afb035eeeae7e0f8cff71846457ff750e14e3455fa72214efd63656f8a5f40fe` |

## What This Baseline Shows

Block coloring is no longer the main local bottleneck for the measured sparse graphs. Cold
coloring for the `2000`-variable case takes `0.004827` seconds, and cached coloring takes
`0.000030` seconds.

The main pure-Python hotspot in this baseline is repeated direct energy and local-field work.
Energy evaluation over `2000` samples takes `0.161868` seconds on a `256`-variable,
`586`-edge model. Local-field queries take `0.093033` seconds because the current
`IsingModel.local_field` scans all couplers on every query. This is acceptable for audit
paths but a poor CPU-side hot loop if future preprocessing, inspector, or fallback samplers
call it repeatedly.

Diagnostics assembly is measurable but not dominant at this scale. The current stdlib path
takes `0.028705` seconds for `2048` samples and multi-chain traces. It remains a candidate
for optional array acceleration on longer traces.

The oracle and fixture generator are fast enough for the current public corpus. They remain
independent correctness checks rather than optimization targets.

## Decisions

Use `performance-baseline-2026-07-04.json` as the comparison artifact for future optimizer
branches. A future branch should rerun the same command before and after the change and
compare medians, not single timings.

Keep the cluster-move benchmark separate. The core benchmark measures repository
calculations; the cluster harness measures a research sampler idea on synthetic grid spin
glasses.

## Rejected Alternatives

Using only the cluster-move benchmark as the baseline is rejected because it does not measure
the repository's current production calculations.

Adding NumPy or benchmark dependencies is rejected for this harness. The project core is
stdlib-first, and the baseline should run in the same minimal environment as the public
tests.

## Verification

- Current-code snapshot commit: `1db24b5` (`Capture optimization audit baseline`).
- Harness commit: `844e53b` (`Add core performance baseline harness`).
- Script syntax check:
  `py -3 -m py_compile tools/benchmark_performance_baseline.py`; result: pass.
- Ruff check attempt:
  `py -3 -m ruff check tools/benchmark_performance_baseline.py`; result: blocked because
  `ruff` is not installed in the local Python environment.
- Baseline command: shown above; result: artifact written with final SHA-256
  `01f458e7f6bd5712f587f52ae3608bdd52f76944b6114877852caef1713cae39`.
