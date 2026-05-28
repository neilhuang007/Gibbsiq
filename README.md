# Gibbsiq

THRML-native QUBO / Ising / BQM optimization with built-in diagnostics and inspection.

## Objective

Build a solver stack that:

- accepts QUBO, Ising, and BQM inputs;
- lowers models into THRML block-Gibbs execution;
- returns samples, energies, traces, and metadata;
- reports mixing, diversity, feasibility, and runtime diagnostics;
- compares against standard QUBO / Ising baselines.

Target API:

```python
model = compile_qubo(problem)
result = THRMLSampler(config).sample(model, num_reads=128)
Inspector.from_result(result).show()
```

## Rationale

Sampling optimizers can fail silently: high autocorrelation, mode collapse, weak feasibility, bad schedules, or poor formulation can all produce misleading best samples. Gibbsiq makes sampler health part of the default result.

Source-backed rationale: [reference/why-this-project-matters.md](reference/why-this-project-matters.md)

## Stack

1. Interface: QUBO / Ising / BQM ingestion and decoding.
2. Runtime: THRML lowering, block partitioning, schedules, seeds, initialization.
3. Diagnostics: traces, autocorrelation, ESS-style metrics, diversity, feasibility, failure flags.
4. Inspector: topology, traces, summaries, warnings, baseline comparison.
5. Benchmarks: Max-Cut, SK spin glass, sparse Ising, knapsack, TSP reductions.

## Roadmap

Each stage has goal, deliverables, exit criteria, implementation notes, and references:

0. [Research and framing](reference/00-roadmap/stage-00-research-and-framing.md)
1. [Core model compatibility](reference/00-roadmap/stage-01-core-model-compatibility.md)
2. [First THRML sampler](reference/00-roadmap/stage-02-first-thrml-sampler.md)
3. [Diagnostics pipeline](reference/00-roadmap/stage-03-diagnostics-pipeline.md)
4. [Inspector and reporting](reference/00-roadmap/stage-04-inspector-and-reporting.md)
5. [Baselines and benchmarks](reference/00-roadmap/stage-05-baselines-and-benchmarks.md)
6. [Adaptive hardware-aware runtime](reference/00-roadmap/stage-06-adaptive-hardware-runtime.md)

Roadmap index: [reference/00-roadmap/README.md](reference/00-roadmap/README.md)

## v0 Target

- solve small Max-Cut and Ising instances;
- expose dimod-like sampler methods;
- execute through THRML;
- return samples, energies, traces, metadata;
- produce first-pass diagnostics;
- compare against simulated annealing;
- export reproducible benchmark artifacts.

## References

Research pack: [reference/README.md](reference/README.md)

## Evaluation JSON

Implementations can emit candidate fixture outputs as JSON and run:

```powershell
$env:PYTHONPATH = "src"
python -m gibbsiq.evaluation .\examples\evaluation-candidate.example.json
```

The evaluator prints a JSON report and exits with status `0` only when all golden fixtures pass.
