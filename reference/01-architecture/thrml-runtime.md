# THRML Runtime

## Sources

- Docs: https://docs.thrml.ai/
- Architecture: https://docs.thrml.ai/en/latest/architecture
- Block sampling API: https://docs.thrml.ai/en/latest/api/block_sampling
- Spin example: https://docs.thrml.ai/en/latest/examples/02_spin_models
- Repo: https://github.com/extropic-ai/thrml

## THRML Concepts

- `Block`: same-type nodes updated together.
- `Factor`: interaction / energy term.
- `Program`: block/factor/sampler execution bundle.
- `SamplingSchedule`: warmup, sample count, steps per sample.
- Global state: JAX array/PyTree representation used for vectorized updates.

## Gibbsiq Boundary

Pipeline:

```text
QUBO/BQM/Ising input
-> Gibbsiq IsingModel
-> THRML nodes/blocks/factors/program
-> raw states/traces
-> SampleResult
-> diagnostics/inspector
```

THRML is the runtime substrate. It provides the probabilistic-programming primitives:
nodes hold variables, factors define energy terms, blocks define variables updated together,
programs coordinate sampling, and schedules specify warmup and sample collection. Gibbsiq
owns the optimization layer around those primitives: conversion, block strategy, schedules,
seeds, trace capture, schema, diagnostics, baselines, and reports.

## Internal Model

```python
class IsingModel:
    variables: tuple
    linear: Mapping
    quadratic: Mapping
    offset: float
    vartype: str  # "SPIN"
    source_format: str  # "qubo" | "ising" | "bqm"
    variable_order: tuple
    metadata: Mapping
```

Canonical energy:

```text
E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j
s_i in {-1, +1}
```

## Runtime Lowering Boundary

The current runtime uses private `_Lowering` artifacts containing the THRML nodes, canonical
edge positions, sign-corrected biases and weights, graph-colored free blocks, observed blocks,
lowered dtypes, and per-beta lowered targets. `_Lowering.program(beta)` constructs the THRML
energy model and sampling program for one inverse temperature. A public
`THRMLProgramBundle` remains a roadmap proposal rather than a production class.

## v0 Block Strategy

Graph coloring:

1. Build graph from nonzero `J_ij`.
2. Color graph so nodes in one color class do not interact.
3. Convert color classes to THRML blocks.

Risks:

- dense graphs produce many small blocks;
- padding can waste accelerator work;
- block strategy affects mixing and diagnostics.

## Runtime Strategy

The Stage 2 correctness path implements:

- fixed-temperature correctness tests;
- warmup beta ladders followed by fixed-target retained reads;
- vmapped independent fixed-beta chains;
- opt-in host-loop parallel tempering with cold-slot and per-beta evidence;
- deterministic graph-colored blocks, including dense and edgeless cases.

Device-side replica exchange, clamped-block execution through `ThermodynamicProgram`, and
baseline comparison remain separate roadmap work.
