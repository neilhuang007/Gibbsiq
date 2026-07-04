# 2026-07-04 - Cluster Move Local Benchmark

## Paper Hook

This entry feeds the methods and limitations sections for cluster-move acceleration. It
records a local pilot benchmark for parallel tempering with isoenergetic cluster moves, with
raw traces and a checksum so the claim can be audited later.

## Context

The previous algorithm audit identified replica cluster moves as the most credible cluster
optimization for Gibbsiq-style sparse frustrated Ising instances. The user asked for local
statistics rather than literature-only evidence. We therefore added a standalone benchmark
harness under `tools/` and kept production sampler code unchanged.

The benchmark compares two pure-Python research kernels on fixed random 2D +/-J grid spin
glasses:

1. `pt`: two independent parallel-tempering ladders with heat-bath spin updates.
2. `pt_icm`: the same two ladders plus Houdayer-style isoenergetic cluster swaps between the
   two replicas at the same beta.

The target for each instance is the best energy observed by either algorithm plus a 1%
margin, with a minimum margin of 1. This is a time-to-common-observed-threshold metric, not
an exact optimum proof.

## Hard-Parts Analysis

H1. A local proof of speed requires an implemented cluster kernel. The repository did not
have one, so we built a research harness in `tools/benchmark_cluster_moves.py` rather than
adding production solver behavior to `src/gibbsiq`.

H2. The comparison needs paired instances. Each random grid instance is generated once from a
recorded seed, then both algorithms are run on that same instance. The summary computes
paired speedups from per-instance time to the same observed target.

H3. The cluster move must preserve the energy invariant. Each accepted isoenergetic move
recomputes `E(replica_a) + E(replica_b)` after the swap and accepts only if the total is
unchanged. This makes the pilot slower than an optimized implementation, but it makes the
local evidence auditable.

H4. Wall time and target time answer different questions. PT+ICM has slightly higher full-run
wall time because it performs Python graph walks and full energy checks. The useful result is
that it reaches the common threshold sooner on the larger pilot cases.

## Method

Command:

```powershell
py -3 tools/benchmark_cluster_moves.py --sizes 8 12 16 --instances 10 --sweeps 300 --beta-count 12 --out reference/06-benchmarks/artifacts/cluster-move-benchmark-2026-07-04.json
```

Configuration:

- Seed: `20260704`.
- Sizes: `8x8`, `12x12`, `16x16`.
- Instances per size: `10`.
- Sweeps per run: `300`.
- Beta ladder: `12` log-spaced values from `0.2` to `2.5`.
- ICM cadence: every `2` sweeps for beta values at least `0.8`.
- Cluster guards: minimum size `2`, maximum fraction `0.7`.
- Platform recorded by artifact: `Windows-11-10.0.26220-SP0`.
- Python recorded by artifact: `3.14.2`.

Artifact:

- Path: `reference/06-benchmarks/artifacts/cluster-move-benchmark-2026-07-04.json`.
- SHA-256: `9285587697dc676affc1c0e2b62827bbfc536969ebe40351a246ef8b131e5157`.
- Script: `tools/benchmark_cluster_moves.py`.

## Results

The table reports median wall time for the full 300-sweep run, median time to the per-instance
observed target, paired speedup values summarized by their median, and a 90% bootstrap
confidence interval for the paired median speedup. Speedup is `PT time / PT+ICM time`, so a
value greater than `1.0` favors the cluster-move kernel.

| Grid | PT wall median | PT+ICM wall median | PT target-time median | PT+ICM target-time median | Aggregate speedup | Paired median speedup | 90% bootstrap CI | Target hits | Cluster acceptance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| `8x8` | `0.635 s` | `0.664 s` | `0.0275 s` | `0.0197 s` | `1.40x` | `1.36x` | `[0.68x, 2.52x]` | PT `10/10`, PT+ICM `10/10` | `66.8%` |
| `12x12` | `1.923 s` | `1.983 s` | `0.620 s` | `0.174 s` | `3.57x` | `3.31x` | `[2.93x, 6.07x]` | PT `10/10`, PT+ICM `9/10` | `75.3%` |
| `16x16` | `3.637 s` | `3.982 s` | `1.544 s` | `0.578 s` | `2.67x` | `2.17x` | `[1.44x, 3.12x]` | PT `9/10`, PT+ICM `10/10` | `87.0%` |

The `8x8` pilot is inconclusive because the bootstrap interval crosses `1.0`. The `12x12`
and `16x16` pilots support a local speedup for time-to-threshold despite the unoptimized
Python cluster overhead. The confidence intervals for those two sizes stay above `1.0`.

Cluster sizes remained below the guard threshold. The accepted cluster mean fractions were
`0.326` for `8x8`, `0.319` for `12x12`, and `0.349` for `16x16`. This supports the specific
use case we intended to test: sparse frustrated grids where clusters do not span the whole
system.

## Hardware Contention Caveat

After the benchmark, the user reported a concurrent background process that may have consumed
substantial hardware resources during the run. We did not sample process load during the
benchmark itself, so the wall-clock timing results above are classified as a contended pilot.

A post-run 3-second process delta sample found no active `python` or `py` benchmark process.
The largest current CPU consumer was `javaw.exe` at about `67.19%` of total logical CPU, with
additional smaller consumers including `audiodg`, `WeChatAppEx`, `msedgewebview2`, `obs64`,
and several `jcef_helper` processes. This confirms that the machine can be CPU-contended.

The contention affects wall-clock fields such as `wall_seconds`, `target_time_median_seconds`,
and speedup ratios computed from elapsed seconds. It should not change the deterministic
energy traces for the fixed seeds unless process interference changes the program itself,
because the stochastic updates are driven by Python RNG streams rather than wall time. A
follow-up clean run should pause the heavy background workload, record a pre-run load sample,
and report sweep-to-target alongside seconds-to-target.

## Clean Rerun

The user stopped the heavy background workload and asked for the benchmark to be rerun. Before
the rerun, a 3-second process delta sample found no active `python` or `py` benchmark process.
The largest current CPU consumer was `WeChatAppEx` at about `1.73%` of total logical CPU,
followed by `iCloudHome` at `1.16%` and `pycharm64` at `0.88%`. After the rerun, the largest
observed consumers were three `zen` browser processes at `2.98%`, `2.79%`, and `2.75%` of
total logical CPU. This run is therefore the cleaner local measurement.

Command:

```powershell
py -3 tools/benchmark_cluster_moves.py --sizes 8 12 16 --instances 10 --sweeps 300 --beta-count 12 --out reference/06-benchmarks/artifacts/cluster-move-benchmark-2026-07-04-clean.json
```

Artifact:

- Path: `reference/06-benchmarks/artifacts/cluster-move-benchmark-2026-07-04-clean.json`.
- SHA-256: `c47f4eedd9287d076c2fc977d37500444a3794744a70e87560f541fa0392ab79`.
- The script now reports sweep-to-target in addition to seconds-to-target.

| Grid | PT wall median | PT+ICM wall median | PT target-time median | PT+ICM target-time median | PT target-sweep median | PT+ICM target-sweep median | Paired time speedup | 90% time CI | Paired sweep speedup | 90% sweep CI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `8x8` | `0.331 s` | `0.344 s` | `0.0152 s` | `0.0106 s` | `13` | `9` | `1.42x` | `[0.756x, 2.521x]` | `1.46x` | `[0.719x, 2.719x]` |
| `12x12` | `0.754 s` | `0.784 s` | `0.232 s` | `0.0671 s` | `88.5` | `26` | `3.26x` | `[1.852x, 4.502x]` | `3.38x` | `[2.070x, 4.929x]` |
| `16x16` | `1.370 s` | `1.457 s` | `0.593 s` | `0.221 s` | `128` | `41.5` | `2.44x` | `[1.265x, 3.131x]` | `2.53x` | `[1.300x, 3.250x]` |

The clean rerun confirms the earlier qualitative result. The `8x8` case remains inconclusive:
both seconds-to-target and sweeps-to-target intervals cross `1.0`. The `12x12` and `16x16`
cases support a local PT+ICM speedup, and the sweep-based intervals stay above `1.0`, which
reduces sensitivity to CPU contention.

The clean full-run wall times were lower than the contended artifact by about `1.92x` to
`2.66x` for PT and `1.93x` to `2.73x` for PT+ICM, depending on grid size. This confirms that
the background workload materially affected absolute elapsed times while leaving the
algorithmic sweep-to-target comparison stable.

## Decisions

1. Keep PT+ICM as a candidate optimization for sparse/frustrated instances. The local
   pilot shows target-time speedups of `3.31x` paired median on `12x12` and `2.17x` paired
   median on `16x16`.
2. Treat `8x8` as too small for a performance claim. Its paired median favors PT+ICM, but
   the 90% bootstrap interval includes slowdowns.
3. Preserve percolation guards in any production design. The algorithm is useful when
   clusters remain partial; dense graphs or spanning clusters should skip ICM.
4. Require a production benchmark before paper claims. This pilot uses a pure-Python harness,
   not THRML, JAX, or TSU execution.

## Rejected Alternatives

- We did not benchmark plain Swendsen-Wang or Wolff on these generic spin-glass grids. The
  direct rejection-free assumptions are weaker for mixed-sign frustrated instances.
- We did not use exact optima for these local grid sizes. The pilot measures time to a common
  observed threshold and stores raw traces for audit. Exact optimum benchmarking remains a
  separate fixture-generation task.
- We did not compare against production THRML wall time because the cluster kernel is not
  implemented in THRML yet.

## Follow-Up / Open Items

1. Port the PT skeleton into the production THRML runtime before adding cluster moves.
2. Implement ICM metadata in `SampleResult`: cluster attempts, accepted moves, skipped-large
   clusters, skipped-small clusters, beta ids, replica ids, and energy-invariant deltas.
3. Add exact small-instance checks for the ICM invariant and target-state recomputation.
4. Repeat the benchmark with a JAX-friendly connected-component kernel when the production
   prototype exists.
5. Add dense graph cases to verify that the percolation guard disables ICM when clusters
   span most variables.

## Verification

- Smoke test:
  `py -3 tools/benchmark_cluster_moves.py --sizes 6 --instances 2 --sweeps 20 --beta-count 6 --out reference/06-benchmarks/artifacts/cluster-move-benchmark-smoke.json`.
- Main benchmark:
  `py -3 tools/benchmark_cluster_moves.py --sizes 8 12 16 --instances 10 --sweeps 300 --beta-count 12 --out reference/06-benchmarks/artifacts/cluster-move-benchmark-2026-07-04.json`.
- Clean rerun:
  `py -3 tools/benchmark_cluster_moves.py --sizes 8 12 16 --instances 10 --sweeps 300 --beta-count 12 --out reference/06-benchmarks/artifacts/cluster-move-benchmark-2026-07-04-clean.json`.
- Syntax check:
  `py -3 -m py_compile tools/benchmark_cluster_moves.py`.
- Post-run process delta check showed `javaw.exe` using about `67.19%` of total logical CPU
  over a 3-second sample. This was measured after the benchmark and is recorded as a
  contention caveat rather than as a correction factor.
- Clean pre-run process delta check showed no active Python benchmark process and a largest
  observed CPU consumer of about `1.73%` of total logical CPU. Clean post-run process delta
  check showed browser processes as the largest consumers, each below `3.0%` of total logical
  CPU.
- The benchmark artifact records the run command, parameters, Python version, platform,
  raw traces, per-run timings, and summary statistics.
