# Gibbsiq Project Brief

## One-Sentence Summary

Gibbsiq is a THRML-native optimizer for QUBO, Ising, and BQM problems that does not just return answers; it also explains whether the sampling run was healthy, trustworthy, and comparable to standard baselines.

## What I Am Building

I am building a combinatorial optimization solver for problems that can be expressed as QUBO, Ising, or Binary Quadratic Models.

The solver will:

- accept familiar optimization formats;
- run problems through a THRML-backed block Gibbs sampler;
- return samples, energies, best states, traces, and metadata;
- diagnose sampler quality and failure modes;
- generate inspection reports;
- compare results against baseline solvers such as simulated annealing, OpenJij, and simulated bifurcation.

## Why This Is Different

Most optimization tools focus on the final answer. Gibbsiq focuses on both the answer and the quality of the process that produced it.

For sampling-based optimization, a result can look good while the sampler is actually unhealthy:

- samples may be highly correlated;
- chains may be stuck in local modes;
- the schedule may cool too quickly;
- the formulation may create bad penalty scaling;
- the solver may find better results only because it used more compute;
- repeated samples may collapse onto a small set of states.

Gibbsiq makes these issues visible by treating diagnostics as part of the solver, not as an optional afterthought.

## Why THRML

THRML is designed for block Gibbs sampling of probabilistic graphical models and energy-based models. That makes it a strong runtime foundation for a solver focused on Ising-style optimization and future probabilistic or thermodynamic hardware.

Gibbsiq adds the missing product layer around THRML:

- QUBO / BQM compatibility;
- conversion and result schemas;
- optimization-focused diagnostics;
- reports and visual inspection;
- baseline comparisons;
- reproducible benchmarks.

## Intended User Flow

```python
model = compile_qubo(problem)
solver = THRMLSampler(config)
result = solver.sample(model, num_reads=128)
report = Inspector.from_result(result)
report.show()
```

## Core Components

### 1. Problem Interface

Accept QUBO, Ising, and BQM inputs and convert them into one internal representation.

### 2. THRML Runtime

Lower the internal model into THRML nodes, blocks, factors, and sampling programs.

### 3. Diagnostics

Measure energy traces, autocorrelation, effective sample size, diversity, feasibility, mode collapse, stuck chains, and schedule problems.

### 4. Inspector

Generate readable reports showing topology, traces, warnings, best states, sample diversity, and baseline comparisons.

### 5. Benchmark Harness

Compare Gibbsiq against standard solvers on Max-Cut, spin glass, sparse Ising, knapsack, TSP reductions, and constraint-heavy synthetic problems.

## Version 0 Goal

Version 0 should:

- solve small Max-Cut and Ising benchmark instances;
- expose a dimod-like sampler interface;
- run through a THRML-backed execution path;
- return samples, energies, traces, and metadata;
- produce first-pass diagnostic summaries;
- compare against simulated annealing;
- export reproducible benchmark artifacts.

## Long-Term Goal

The long-term goal is to build a serious diagnostics-first optimization runtime for probabilistic computing: a bridge between today’s GPU-backed THRML execution and future hardware-aware thermodynamic sampling systems.

## In Plain English

Gibbsiq is an optimizer that tries to answer two questions at the same time:

1. What is the best solution we found?
2. Should we trust how we found it?

