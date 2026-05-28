# Benchmark Plan

## Sources

- Amplify Benchmark: https://github.com/fixstars/amplify-benchmark
- Amplify formulation benchmarks: https://amplify.fixstars.com/en/docs/amplify/v1/benchmark.html
- QUBO instances: https://github.com/rliang/qubo-benchmark-instances
- MaxCut/QUBO exact survey: https://optimization-online.org/wp-content/uploads/2022/02/8782.pdf
- NeuroBench QUBO: https://github.com/NeuroBench/system_benchmarks/blob/main/QUBO.md
- Evaluation fixtures: ../08-evaluation/fixtures/README.md
- Benchmark equation audit: ../08-evaluation/equation-audit.md

## v0 Families

- Max-Cut: ER, random regular, small GSET-style.
- SK spin glass: dense random couplings.
- Sparse Ising: fixed n, edge probability, coupling distribution, seed.
- Knapsack: small penalty QUBO.
- TSP: small QUBO only.
- Constraint-heavy synthetic cases.

## Problem Metadata

```yaml
problem:
  family: maxcut
  instance_id: maxcut-er-n64-p0.1-seed7
  n_variables: 64
  source: generated
  seed: 7
  best_known_energy: null
  exact_energy: null
  formulation:
    penalty_strength: null
    offset: 0.0
```

## Run Metadata

```yaml
run:
  solver: thrml
  solver_version: unknown
  device: cpu
  seed: 123
  num_reads: 128
  schedule:
    type: geometric_beta
    beta_start: 0.1
    beta_end: 5.0
  block_strategy: greedy_coloring
```

## Metrics

- best energy;
- median energy;
- best feasible energy;
- gap to exact/best-known;
- time to best;
- time to target;
- feasibility rate;
- unique sample fraction;
- top-k mass;
- wall-clock time.

## Solver Matrix

```text
THRMLSampler       native sampler
neal SA            dimod-compatible SA
OpenJij SA/SQA     Ising/QUBO baseline
Simulated SB       non-MCMC physics baseline
Exact/bruteforce   small-instance validator
```

## Reproducibility

- store generated instances or seeds;
- store solver versions;
- store hardware metadata;
- store raw samples/traces;
- split formulation, compile, sample, diagnostics time;
- use multiple seeds per instance.

## Required First Fixtures

Before adding large benchmarks, implementations must pass:

- `../08-evaluation/fixtures/exact-small-instances.json`
- `../08-evaluation/fixtures/diagnostic-fixtures.json`

These fixtures verify energy signs, conversion offsets, Max-Cut objective mapping, Gibbs conditionals, and diagnostic failure flags.
