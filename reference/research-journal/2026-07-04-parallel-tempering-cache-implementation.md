# 2026-07-04 - Parallel Tempering And Local Cache Implementation

## Paper Hook

This entry feeds the runtime-methods and artifact-quality sections. It records the first
production-code pass for opt-in parallel tempering and a degree-local cache for repeated
local-field calculations.

## Context

The implementation plan identified two near-term production changes: parallel tempering in
`THRMLSampler` and an adjacency/cache helper for repeated CPU-side local-field and
energy-delta work. The same plan also named constrained encoders, baseline adapters, and
isoenergetic cluster moves. We implemented the runtime/cache slice because it has direct
interfaces in the current codebase and leaves the THRML-first sampler contract intact.

## Hard-Parts Analysis

H1. Parallel tempering needs fixed-target samples for diagnostics. The implementation treats
`parallel_tempering_betas` as a strictly increasing hot-to-cold inverse-temperature ladder
whose final entry equals `config.beta`. `SampleResult.samples`, `traces["energy"]`, and
diagnostics use the cold beta slot. Per-beta evidence is stored under
`traces["parallel_tempering"]`.

H2. Swap transitions need raw provenance. Each swap event records chain id, read index, beta
indices, beta values, pre-swap energies, log acceptance, uniform variate, and accepted status.
Metadata records total attempts, accepts, acceptance rate, ladder, interval, and the Python
swap RNG seed convention.

H3. Fixed-beta warmup ladders and PT ladders are separate schedule modes. The config rejects
using both in one run because a combined mode needs a more explicit trace segmentation
contract before diagnostics can consume it safely.

H4. The local-field cache should not tax model construction. The model now builds indexed
linear, edge, and adjacency structures lazily. `local_field()` and `flip_energy_delta()` use
the degree-local adjacency cache; `energy()` uses an indexed edge cache after first use.

## Decisions

`SamplerConfig.parallel_tempering_betas` enables PT only when explicitly set. Existing
fixed-beta behavior remains the default.

`parallel_tempering_swap_interval` defaults to `1` recorded sample. The implementation
attempts non-overlapping adjacent swaps with alternating parity so every neighboring pair is
visited over time.

The swap acceptance rule is the standard replica-exchange Metropolis rule using the
canonical Gibbsiq energy recomputed by `IsingModel.energy()`.

`IsingModel.flip_energy_delta(variable, sample)` returns the exact single-spin flip energy
change `-2 * s_i * gamma_i`, where `gamma_i` is the audited local field.

Constrained knapsack/TSP encoders, baseline adapters, and ICM remain follow-up work. They
need new API surface, feasibility diagnostics, optional dependency handling, and oracle
tests beyond this runtime/cache slice.

## Rejected Alternatives

We did not make PT the default sampler mode. Fixed-beta Gibbs remains the audited validation
path and keeps existing tests stable.

We did not mix `warmup_beta_ladder` with `parallel_tempering_betas`. A combined mode would
need per-phase trace semantics before it is safe to report stationarity diagnostics.

We did not implement baseline solver adapters in this pass. D-Wave samplers, OpenJij,
simulated bifurcation, and MQLib use different solver semantics and belong in the baseline
layer with strict resource accounting.

We did not implement isoenergetic cluster moves in production. The local pilot supports the
idea for sparse frustrated graphs, but production ICM needs percolation guards and
fixed-beta replica-pair metadata after PT is validated in the THRML runtime.

## Sources Read / Examples Used

- Hukushima and Nemoto, exchange Monte Carlo for spin glass simulations:
  `https://arxiv.org/abs/cond-mat/9512035`; DOI `10.1143/JPSJ.65.1604`.
- Lucas 2014, constrained Ising formulations and penalty conditions:
  `https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2014.00005/full`.
- D-Wave Ocean `dwave-samplers` simulated annealing API and timing fields:
  `https://docs.dwavequantum.com/en/latest/ocean/api_ref_samplers/api_ref.html`.
- OpenJij official repository:
  `https://github.com/Jij-Inc/OpenJij`.
- Simulated bifurcation Python package:
  `https://github.com/bqth29/simulated-bifurcation-algorithm`.
- MQLib official repository and executable format:
  `https://github.com/MQLib/MQLib` and
  `https://github.com/MQLib/MQLib/blob/master/bin/README.md`.
- Extropic TSU framing and THRML block-Gibbs docs:
  `https://extropic.ai/writing/thermodynamic-computing-from-zero-to-one` and
  `https://docs.thrml.ai`.
- Zhu, Ochoa, and Katzgraber 2015 ICM reference:
  `https://arxiv.org/abs/1501.05630`.

## Measurement

Baseline artifact:

- Path: `reference/06-benchmarks/artifacts/performance-baseline-2026-07-04.json`.
- Baseline commit: `844e53b96b0f310b1faa5f3ff3ac98043942ad07`.
- Dirty at benchmark start: `false`.

Current artifact:

- Path: `reference/06-benchmarks/artifacts/performance-after-pt-cache-2026-07-04.json`.
- Final SHA-256: `f9a9433d83139151f117353d5b036bc936fd6b3bbe3f6efbd724dfe27ec08119`.
- Recorded commit: `3641844a49c79c0bdab4eed65bb1551f5d66b0ba`.
- Dirty at benchmark start: `true`.

Median comparison:

| Calculation | Baseline seconds | Current seconds | Change |
| --- | ---: | ---: | ---: |
| `compile_ising`, `n=512`, `1150` edges | `0.002127` | `0.004604` | `+116.4%` |
| `compile_qubo`, `n=512`, `1119` edges | `0.002422` | `0.004678` | `+93.2%` |
| block coloring cold, `n=2000`, `3414` edges | `0.004827` | `0.008535` | `+76.8%` |
| block coloring cached, same graph | `0.000030` | `0.000044` | `+44.2%` |
| `energy()` over `2000` samples | `0.161868` | `0.205305` | `+26.8%` |
| `local_field()` over `2000` queries | `0.093033` | `0.065356` | `-29.7%` |
| diagnostics, `2048` samples | `0.028705` | `0.080044` | `+178.8%` |
| benchmark oracle, `27` fixtures | `0.000458` | `0.001237` | `+170.1%` |
| ground-truth generation, `27` fixtures | `0.147175` | `0.396021` | `+169.1%` |

The local-field result reflects the intended degree-local optimization. The broad wall-time
comparison is contended: a post-run 3-second CPU delta sample found `cs2.exe` using
`15.312` CPU seconds, about `23.20%` of total logical CPU, with smaller consumers including
`obs64`, `claude`, `audiodg`, and `pycharm64`. The slowdown in unrelated calculations such
as diagnostics, the oracle, and ground-truth generation is therefore recorded as a machine
load caveat.

## Clean Rerun

The user asked to run the benchmark again after the contended artifact. A pre-run 3-second
CPU delta sample found no large competing workload. The largest sampled process was
`obs64.exe` at `0.453` CPU seconds, about `0.69%` of total logical CPU. A post-run sample
again found `obs64.exe` as the largest sampled process at `0.516` CPU seconds, about
`0.78%` of total logical CPU.

Command:

```powershell
py -3 tools/benchmark_performance_baseline.py --repeat 7 --out reference/06-benchmarks/artifacts/performance-after-pt-cache-2026-07-04-rerun.json
```

Artifact:

- Path: `reference/06-benchmarks/artifacts/performance-after-pt-cache-2026-07-04-rerun.json`.
- Final SHA-256: `1e38cfaeb846ca92d281788155c4accf5af776c53ae0c0fef19c5124e52d2103`.
- Recorded commit: `2d7bd9fbeb75a87e28dd8b7d5f175f1ab325fb7a`.
- Dirty at benchmark start: `true`.

Clean median comparison:

| Calculation | Baseline seconds | Rerun seconds | Change |
| --- | ---: | ---: | ---: |
| `compile_ising`, `n=512`, `1150` edges | `0.002127` | `0.002405` | `+13.0%` |
| `compile_qubo`, `n=512`, `1119` edges | `0.002422` | `0.002429` | `+0.3%` |
| block coloring cold, `n=2000`, `3414` edges | `0.004827` | `0.004518` | `-6.4%` |
| block coloring cached, same graph | `0.000030` | `0.000029` | `-3.3%` |
| `energy()` over `2000` samples | `0.161868` | `0.120978` | `-25.3%` |
| `local_field()` over `2000` queries | `0.093033` | `0.040634` | `-56.3%` |
| diagnostics, `2048` samples | `0.028705` | `0.029186` | `+1.7%` |
| benchmark oracle, `27` fixtures | `0.000458` | `0.000402` | `-12.2%` |
| ground-truth generation, `27` fixtures | `0.147175` | `0.154668` | `+5.1%` |

This rerun supersedes the contended artifact for performance interpretation. The unrelated
diagnostics, oracle, and ground-truth timings return near the baseline range, while the
targeted cached paths improve: `energy()` by `25.3%` and `local_field()` by `56.3%`.

## Verification

- Syntax check:
  `py -3 -m py_compile src/gibbsiq/model.py src/gibbsiq/thrml_runtime.py`.
- Targeted tests:
  `$env:PYTHONPATH='src'; py -3 -m unittest test_suite.tests.test_model_compatibility test_suite.tests.test_thrml_runtime`;
  result: `39` tests, `25` skipped.
- Full test suite:
  `$env:PYTHONPATH='src'; py -3 -m unittest discover -s test_suite/tests`;
  result: `273` tests, `56` skipped.
- Performance command:
  `py -3 tools/benchmark_performance_baseline.py --repeat 7 --out reference/06-benchmarks/artifacts/performance-after-pt-cache-2026-07-04.json`.
- Clean rerun command:
  `py -3 tools/benchmark_performance_baseline.py --repeat 7 --out reference/06-benchmarks/artifacts/performance-after-pt-cache-2026-07-04-rerun.json`.
- Markdown math check:
  `py -3 tools/check_markdown_math.py`; result: pass.
- Whitespace check:
  `git diff --check`; result: pass, with line-ending normalization warnings only.

The local environment does not have the optional `thrml` package installed, so PT runtime
tests were skipped locally. The implemented path is syntax-checked and covered by config
tests; the Stage 2 PT exit criterion remains pending until the optional THRML runtime tests
run in an environment with `thrml` installed.
