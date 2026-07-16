# THRML Optimization Runtime

## Sources

- THRML docs: https://docs.thrml.ai/
- Architecture: https://docs.thrml.ai/en/latest/architecture
- Block sampling API: https://docs.thrml.ai/en/latest/api/block_sampling
- Spin example: https://docs.thrml.ai/en/latest/examples/02_spin_models

## Role In Gibbsiq

This implemented layer converts a Gibbsiq `IsingModel` into a THRML sampling program. It removes
the repeated work a user would otherwise do by hand: create spin nodes, build factors, color
the interaction graph, define blocks, choose a schedule, capture traces, and recompute
energies. The current correctness path supports multiple independent chains and an opt-in
parallel-tempering beta ladder; device-side vectorization and performance claims remain open.

## v0 Inputs

- canonical `IsingModel`;
- per-call `num_reads` and optional `BlockPartition`;
- `SamplerConfig` seed, initialization policy, `n_warmup`, `steps_per_sample`, and target beta;
- optional warmup beta ladder;
- independent fixed-beta chains executed with `jax.vmap` when more than one chain is active;
- optional parallel-tempering ladders on the host-loop correctness path. Device-side/vectorized
  replica exchange remains future performance work.

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
# THRML's IsingEBM log weight has the opposite sign from canonical E(s).
biases = jnp.asarray([-h[v] for v in variables])
weights = jnp.asarray([-J[e] for e in edge_order])
model = IsingEBM(nodes, edges, biases, weights, beta)
blocks = color_blocks(graph)
program = IsingSamplingProgram(model, blocks, clamped_blocks=[])
schedule = SamplingSchedule(n_warmup, n_samples, steps_per_sample)
samples = sample_states(key, program, schedule, init_state, [], [Block(nodes)])
```

The negative signs are required because THRML's Ising log weight is proportional to
`beta * (sum_i b_i s_i + sum_ij w_ij s_i s_j)`, while Gibbsiq targets `exp(-beta * E(s))`.
Analytic one- and two-spin tests independently pin this mapping.

## Trace Capture

Minimum:

- sampled states;
- final energies;
- best-so-far energy;
- schedule values;
- block metadata.
- seed and initialization metadata.

Preferred:

- energy per sample;
- block flip rates;
- local-field summaries;
- per-read best energy.
- chain id and beta/slot traces for parallel tempering.

## Optimization Direction

Fixed-temperature block Gibbs is the correctness baseline, not the final optimization
strategy. The runtime includes warmup beta schedules, batched independent chains, and an
opt-in parallel-tempering correctness path without changing the public result contract. The later
measurement hypothesis is not that Gibbs is always faster. The hypothesis is that
THRML/JAX execution, and later Thermodynamic Sampling Unit execution if available, can reduce
the cost of many-chain and many-temperature sampling on instances whose graph structure
admits useful block parallelism. That hypothesis requires fixed-work and fixed-time
benchmark evidence before it becomes a project claim.

## Tests

- QUBO/Ising energy equivalence.
- fixed-seed reproducibility.
- zero-coupling marginals.
- two-spin analytic distribution.
- tiny enumerated Boltzmann-law checks and capped exact-distribution comparisons.
- Max-Cut toy instances.
