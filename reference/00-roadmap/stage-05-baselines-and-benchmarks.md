# Stage 5 - Baselines and Benchmarks

**Status: Partial.** The exact public corpus, deterministic generator, strict witness oracle,
and sampler-to-oracle bridge are implemented. Classical solver adapters, matched-budget
runners, imported Tier B corpora, and comparative artifacts remain absent.

## Goal

Run reproducible comparisons against standard QUBO/Ising solvers.

## Deliverables

- `dwave-samplers` simulated-annealing wrapper.
- OpenJij wrapper.
- Simulated bifurcation wrapper.
- Small exact/bruteforce validator.
- Benchmark generators/loaders:
  - Max-Cut;
  - SK spin glass;
  - sparse Ising;
  - knapsack;
  - small TSP;
  - constraint-heavy synthetic cases.
- Fixed-seed runner.
- Fixed-work and fixed-time modes.
- Raw artifacts.

## Exit Criteria

- Solver versions and hardware recorded.
- Benchmarks reproducible from config.
- Reports include best, median, feasibility, diversity, runtime, time-to-target.
- THRML compares against at least two baselines.

The implemented exact corpus and oracle satisfy the correctness-control subset. Stage closure
requires the independent solver and resource-accounting criteria above.

## Implementation Notes

Separate:

- formulation time;
- compile time;
- sampling time;
- diagnostics time.

Do not apply MCMC-only metrics to non-MCMC solvers without labeling.

## References

- Baseline note: ../03-samplers/baseline-solvers.md
- Benchmark note: ../06-benchmarks/benchmark-plan.md
- dwave-samplers repo: https://github.com/dwavesystems/dwave-samplers
- OpenJij tutorial: https://tutorial.openjij.org/en/tutorial/001-openjij_introduction.html
- OpenJij repo: https://github.com/Jij-Inc/OpenJij
- Simulated bifurcation docs: https://simulated-bifurcation-algorithm.readthedocs.io/en/v2.0.0/
- Simulated bifurcation repo: https://github.com/bqth29/simulated-bifurcation-algorithm
- QUBO heuristic benchmark: https://www.nature.com/articles/s41598-022-06070-5
- Amplify Benchmark: https://github.com/fixstars/amplify-benchmark
