# THRML Gibbs Sampler

## Sources

- THRML docs: https://docs.thrml.ai/
- Architecture: https://docs.thrml.ai/en/latest/architecture/
- Block sampling API: https://docs.thrml.ai/en/latest/api/block_sampling/
- Spin example: https://docs.thrml.ai/en/latest/examples/02_spin_models/

## v0 Inputs

- IsingIR.
- `num_reads`.
- `seed`.
- schedule: `n_warmup`, `n_samples`, `steps_per_sample`, beta policy.
- initialization policy.
- block strategy.

## Conditional

Internal convention:

```text
E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j
```

Local field:

```text
gamma_i = h_i + sum_j J_ij s_j
```

Under this convention:

```text
P(s_i = +1 | neighbors) = sigmoid(-2 * beta * gamma_i)
```

Verify sign against THRML with two-spin tests.

## Lowering Sketch

```python
nodes = [SpinNode() for _ in variables]
edges = [(node[u], node[v]) for (u, v) in J]
biases = jnp.asarray([h[v] for v in variables])
weights = jnp.asarray([J[e] for e in edge_order])
model = IsingEBM(nodes, edges, biases, weights, beta)
blocks = color_blocks(graph)
program = IsingSamplingProgram(model, blocks, clamped_blocks=[])
schedule = SamplingSchedule(n_warmup, n_samples, steps_per_sample)
samples = sample_states(key, program, schedule, init_state, [], [Block(nodes)])
```

Verify exact THRML imports/constructors before implementation.

## Trace Capture

Minimum:

- sampled states;
- final energies;
- best-so-far energy;
- schedule values;
- block metadata.

Preferred:

- energy per sample;
- block flip rates;
- local-field summaries;
- per-read best energy.

## Tests

- QUBO/Ising energy equivalence.
- fixed-seed reproducibility.
- zero-coupling marginals.
- two-spin analytic distribution.
- exhaustive n <= 16 fixtures.
- Max-Cut toy instances.

