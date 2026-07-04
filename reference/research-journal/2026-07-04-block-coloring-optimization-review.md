# 2026-07-04 - Block Coloring Optimization Review

## Paper Hook

Feeds the methods and limitations sections: graph-colored block construction is a runtime
preprocessing step whose objective is legal parallel variable updates for THRML block Gibbs.
The entry records why recent edge-coloring results do not replace this vertex-coloring step,
and records the measured effect of the data-structure optimization.

## Context

The Stage 2 runtime calls `color_blocks(model)` once per `sample()` when the caller does not
supply a partition. The previous implementation used deterministic DSATUR and selected the
next variable by scanning every uncolored variable at every coloring step. That scan is simple
and correct, but it makes sparse large graphs pay a Python-level quadratic preprocessing cost.
The user requested a GitHub-backed review of current graph-coloring and sampling
implementations, followed by implementation of the upgrades that fit the repository contract.

## Hard-Parts Analysis

H1. The STOC 2025 Vizing result addresses an edge-coloring primitive. Assadi, Behnezhad,
Bhattacharya, Costa, Solomon, and Zhang compute a `(Delta + 1)` edge coloring in randomized
`O(m log Delta)` time with high probability. Gibbsiq schedules spin variables, so the legal
block condition is a vertex-coloring condition: no two variables in the same block may share a
nonzero Ising coupling. Edge coloring partitions couplings into matchings. Vertex coloring
partitions variables into independent sets. The algorithmic result is important for graph
theory, but it targets a different object than THRML's current block API consumes.

H2. The repo's actual coloring bottleneck is priority maintenance. NetworkX's DSATUR
strategy recomputes saturation over uncolored nodes, while its smallest-last strategy uses a
bucket queue to avoid repeated full scans. A DSATUR-specific GitHub implementation note
describes two-level priority queues keyed first by saturation and then by residual degree.
The mechanism that maps to Gibbsiq is incremental priority maintenance, not a change in the
coloring objective.

H3. The zero-dependency core remains binding. Adding NetworkX would import a broad graph
library for one preprocessing routine. Gibbsiq already carries a standard-library DSATUR
implementation because the core package has no required runtime dependencies. The new
implementation preserves that constraint with `heapq`, `deque`, and `functools.lru_cache`.

## Decisions

We added a deterministic bipartite fast path before DSATUR. Edgeless graphs return one block.
Bipartite graphs with at least one edge return two blocks by BFS from canonical component
starts. Once a component's start color is fixed, neighbor iteration order cannot change the
two sides of a bipartite component. This gives the optimal partition for chains, grids,
trees, and even cycles in linear time.

We made coloring topology-only and cached. The block partition depends on `model.variables`
and `model.graph`, not on coefficient values. Repeated calls over the same topology reuse the
cached tuple-of-blocks and then wrap it in a fresh `BlockPartition`.

We replaced the DSATUR full scan with a lazy heap. Heap entries are keyed by negative
saturation, negative degree, and canonical variable index. When a neighbor gains a new
adjacent color, the implementation pushes a new priority entry and discards stale entries
when popped. The tie rule stays the Stage 2 rule: highest saturation, then higher static
degree, then canonical order.

We kept the public strategy string as `"dsatur-coloring"`. The external runtime contract
still records the same block strategy field, while the implementation now includes an exact
bipartite path and an optimized DSATUR fallback.

## Rejected Alternatives

Replacing vertex coloring with Vizing edge coloring is rejected because THRML block Gibbs
updates variables. An edge-colored schedule would group couplings, and the current
`IsingSamplingProgram` receives free blocks of nodes.

Adding NetworkX as a dependency is rejected because the project core deliberately has zero
required runtime dependencies. NetworkX remains useful as a source implementation for
strategy semantics and data-structure choices.

Implementing full parallel tempering from generic GitHub MCMC packages is deferred. NANOGrav
`PTMCMCSampler` and similar packages exchange temperatures across Metropolis-Hastings
replicas. Gibbsiq needs THRML block-state swap semantics, beta-segment trace accounting, and
diagnostics per constant-beta segment. The local environment also lacks the optional `thrml`
and `jax` packages, so the required runtime verification cannot run in this session.

## Sources Read / Examples Used

- Assadi et al., "Vizing's Theorem in Near-Linear Time", arXiv:2410.05240. The paper states
  the randomized `(Delta + 1)` edge-coloring result and the `O(m log Delta)` bound.
- ACM STOC 2025 proceedings entry for "Vizing's Theorem in Near-Linear Time"; the proceedings
  abstract states the same edge-coloring bound.
- Waterloo Cheriton School of Computer Science award notice, 2025-05-12; confirms the STOC
  2025 Best Paper Award and identifies the paper as edge coloring.
- NetworkX `greedy_coloring.py` on GitHub. The source exposes `strategy_saturation_largest_first`
  as DSATUR and `strategy_smallest_last` as a bucket-queue coloring strategy.
- `ronak14329/-Br-laz-s-Dsatur-algorithm` on GitHub. The README describes two-level priority
  bucket queues for DSATUR selection.
- JuliaGraphs `GraphsColoring.jl` on GitHub. The README identifies implemented greedy,
  DSATUR, and workstream graph-coloring methods.
- NANOGrav `PTMCMCSampler` on GitHub. The README describes MPI-enabled parallel-tempering
  MCMC and temperature-chain execution.

## Measurements

Timing command, before optimization, used `random.Random(seed)` Erdos-Renyi-style sparse
graphs and measured only `color_blocks(model)` after `compile_ising`:

```text
n= 100 m=   183 p=0.0400 blocks=  3 color_seconds=0.0020
n= 500 m=  1321 p=0.0100 blocks=  4 color_seconds=0.0435
n=1000 m=  1987 p=0.0040 blocks=  4 color_seconds=0.1562
n=1000 m=  9899 p=0.0200 blocks=  8 color_seconds=0.2108
n=2000 m=  3944 p=0.0020 blocks=  3 color_seconds=0.6530
n=5000 m= 10131 p=0.0008 blocks=  4 color_seconds=4.6550
```

Timing command, after optimization, used the same seeds and also measured a second cached
call:

```text
n= 100 m=   183 p=0.0400 blocks=  3 max_block=  38 color_seconds=0.0004 repeat_seconds=0.000012
n= 500 m=  1321 p=0.0100 blocks=  4 max_block= 166 color_seconds=0.0031 repeat_seconds=0.000061
n=1000 m=  1987 p=0.0040 blocks=  4 max_block= 374 color_seconds=0.0058 repeat_seconds=0.000101
n=1000 m=  9899 p=0.0200 blocks=  8 max_block= 146 color_seconds=0.0139 repeat_seconds=0.000298
n=2000 m=  3944 p=0.0020 blocks=  3 max_block= 776 color_seconds=0.0112 repeat_seconds=0.000196
n=5000 m= 10131 p=0.0008 blocks=  4 max_block=1897 color_seconds=0.0353 repeat_seconds=0.000330
```

The 5,000-variable sparse case improves from 4.6550 seconds to 0.0353 seconds for the first
coloring. A cached repeat over the same topology takes 0.000330 seconds.

## Follow-Up / Open Items

Parallel tempering remains the Stage 2 exit criterion. The next implementation must operate
on THRML block states, record swap attempts and accepted swaps, and compute diagnostics per
constant-beta collection window.

Baseline adapters remain Stage 5 work. The search confirms that `dwave-samplers`, OpenJij,
and simulated-bifurcation variants are the relevant external implementations to track, but
this session does not add a baseline layer.

## Verification

Focused partition tests:

```powershell
$env:PYTHONPATH = "src"
py -m unittest test_suite.tests.test_block_partition
```

Result: 19 tests pass.

Full suite:

```powershell
$env:PYTHONPATH = "src"
py -m unittest discover -s test_suite/tests
```

Result: 269 tests pass, 54 skipped because optional extras are absent.

Line-length scan over the touched files found no lines longer than 110 characters after the
test import cleanup.

Equivalence audit against the previous DSATUR implementation:

```powershell
$env:PYTHONPATH = "src"
# scratch script over n=1..14, 200 random graphs per n, seed 20260704
```

Result: 2,800 random graphs checked. Every non-bipartite graph produced the exact same
blocks as the previous DSATUR implementation; every bipartite graph produced a valid
partition with no more colors than the previous implementation.

Dense bipartite stress check after removing unnecessary neighbor sorting:

```text
complete_bipartite_100_100: n=200 m=10000 blocks=2 seconds=0.0044
complete_bipartite_250_250: n=500 m=62500 blocks=2 seconds=0.0240
complete_bipartite_500_500: n=1000 m=250000 blocks=2 seconds=0.1339
```

Static lint check:

```powershell
py -m ruff check src/gibbsiq/blocks.py test_suite/tests/test_block_partition.py
```

Result: blocked because `ruff` is not installed in the local Python environment.
