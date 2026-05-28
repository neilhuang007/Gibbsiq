# THRML Runtime

## Sources

- Docs: https://docs.thrml.ai/
- Architecture: https://docs.thrml.ai/en/latest/architecture/
- Block sampling API: https://docs.thrml.ai/en/latest/api/block_sampling/
- Spin example: https://docs.thrml.ai/en/latest/examples/02_spin_models/
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
-> Gibbsiq IsingIR
-> THRML nodes/blocks/factors/program
-> raw states/traces
-> SampleResult
-> diagnostics/inspector
```

THRML is the runtime substrate. Gibbsiq owns conversion, schema, diagnostics, baselines, reports.

## Internal IR

```python
class IsingIR:
    variables: list
    linear: dict
    quadratic: dict
    offset: float
    vartype: str  # "SPIN"
    graph: object
    source_format: str  # "qubo" | "ising" | "bqm"
    variable_order: list
    metadata: dict
```

Canonical energy:

```text
E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j
s_i in {-1, +1}
```

## THRML Bundle

```python
class THRMLProgramBundle:
    nodes: list
    variable_to_node: dict
    node_to_variable: dict
    free_blocks: list
    clamped_blocks: list
    model: object
    program: object
```

## v0 Block Strategy

Graph coloring:

1. Build graph from nonzero `J_ij`.
2. Color graph so nodes in one color class do not interact.
3. Convert color classes to THRML blocks.

Risks:

- dense graphs produce many small blocks;
- padding can waste accelerator work;
- block strategy affects mixing and diagnostics.

