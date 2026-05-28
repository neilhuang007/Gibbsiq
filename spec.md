# Gibbsiq Spec

## Goal

Build a THRML-native combinatorial optimization solver with first-class diagnostics and inspection.

Supported user flow:

```python
model = compile_qubo(problem)
result = THRMLSampler(config).sample(model, num_reads=128)
report = Inspector.from_result(result)
report.show()
```

## Problem

Most QUBO / Ising optimizers report best samples but do not explain sampler health:

- poor mixing;
- bad schedules;
- formulation or penalty failures;
- local-mode trapping;
- mode collapse;
- compute-driven gains versus search-quality gains.

Gibbsiq treats diagnostics as part of the solver contract.

Rationale: [reference/why-this-project-matters.md](reference/why-this-project-matters.md)

## Product Layers

### 1. Interface

- QUBO, Ising, BQM ingestion.
- Deterministic variable ordering.
- QUBO/Ising conversion with offset preservation.
- Optional PyQUBO-compatible decode flow.

### 2. THRML Runtime

- Lower internal Ising IR to THRML nodes, blocks, factors, programs.
- Block Gibbs execution.
- Schedule, seed, initialization, and read controls.
- Trace hooks.

### 3. Diagnostics

- Energy and best-so-far traces.
- Autocorrelation and ESS-style estimates.
- Chain disagreement / R-hat-style scalar checks.
- Diversity, top-k mass, Hamming distances.
- Constraint feasibility and violation summaries.
- Failure flags.

### 4. Inspector

- Topology and block summaries.
- Trace plots.
- Diagnostic summaries.
- Best-state and frequency tables.
- Baseline comparison.
- Exportable artifacts.

### 5. Benchmarks

- Simulated annealing baseline.
- OpenJij baseline.
- Simulated bifurcation baseline.
- Exact/bruteforce validation for small instances.
- Fixed-seed benchmark configs and raw artifacts.

## Internal IR

Canonical energy convention:

```text
E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j
s_i in {-1, +1}
```

Minimum IR fields:

- `variables`
- `linear`
- `quadratic`
- `offset`
- `vartype`
- `graph`
- `source_format`
- `variable_order`
- `metadata`

## Result Schema

Minimum v0 result:

- `samples`
- `variables`
- `energies`
- `best_sample`
- `best_energy`
- `traces`
- `diagnostics`
- `metadata`
- `to_dimod()`

Metadata must include:

- solver/backend versions;
- device;
- seed;
- schedule;
- block strategy;
- timing;
- source model format;
- conversion offset.

## Metrics

Optimization:

- best energy;
- median energy;
- feasibility rate;
- gap to exact/best-known;
- time to target.

Sampling:

- autocorrelation;
- ESS-style estimate;
- unique sample fraction;
- top-k mass;
- Hamming-distance diversity;
- chain disagreement.

Runtime:

- compile time;
- sample time;
- diagnostics time;
- samples/sec;
- memory/device.

## Evaluation Contract

Primary evaluation reference: [reference/08-evaluation/README.md](reference/08-evaluation/README.md)

Required v0 verification:

- exact energy equivalence for small QUBO/Ising fixtures;
- manually audited equation signs from [reference/08-evaluation/equation-audit.md](reference/08-evaluation/equation-audit.md);
- golden examples in [reference/08-evaluation/fixtures/exact-small-instances.json](reference/08-evaluation/fixtures/exact-small-instances.json);
- diagnostic failure examples in [reference/08-evaluation/fixtures/diagnostic-fixtures.json](reference/08-evaluation/fixtures/diagnostic-fixtures.json);
- source and license review before copying implementation code.

## v0 Benchmarks

- Max-Cut.
- SK spin glass.
- Random sparse Ising.
- Small knapsack QUBO.
- Small TSP QUBO.
- Constraint-heavy synthetic cases.

## Roadmap

Stage files:

0. [Research and framing](reference/00-roadmap/stage-00-research-and-framing.md)
1. [Core model compatibility](reference/00-roadmap/stage-01-core-model-compatibility.md)
2. [First THRML sampler](reference/00-roadmap/stage-02-first-thrml-sampler.md)
3. [Diagnostics pipeline](reference/00-roadmap/stage-03-diagnostics-pipeline.md)
4. [Inspector and reporting](reference/00-roadmap/stage-04-inspector-and-reporting.md)
5. [Baselines and benchmarks](reference/00-roadmap/stage-05-baselines-and-benchmarks.md)
6. [Adaptive hardware-aware runtime](reference/00-roadmap/stage-06-adaptive-hardware-runtime.md)

## References

- Reference index: [reference/README.md](reference/README.md)
- Source map: [reference/source-map.md](reference/source-map.md)
- Research gaps: [reference/research-gaps.md](reference/research-gaps.md)
