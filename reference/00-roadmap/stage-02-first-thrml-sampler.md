# Stage 2 - First THRML Sampler

## Goal

Run small Ising/BQM problems through THRML and return `SampleResult`.

## Deliverables

- `THRMLSampler.sample`.
- `THRMLSampler.sample_qubo`.
- `THRMLSampler.sample_ising`.
- IR-to-THRML lowering.
- Graph-coloring block partitioner.
- Seed, initialization, schedule, and `num_reads` support.
- Independent energy evaluator.
- Minimal trace capture.

## Exit Criteria

- Small Max-Cut and random Ising run through THRML.
- Fixed seed is reproducible.
- Returned energies match internal convention.
- Multiple reads return stable schema.
- Exhaustive small-instance validation passes.

## Implementation Notes

Verify installed THRML APIs before coding. Official examples reference:

- `SpinNode`
- `Block`
- `SamplingSchedule`
- `sample_states`
- `IsingEBM`
- `IsingSamplingProgram`
- `hinton_init`

Initial block strategy:

1. Build graph from nonzero couplings.
2. Color graph.
3. Map color classes to THRML blocks.

## References

- THRML sampler note: ../03-samplers/thrml-gibbs-implementation.md
- Runtime note: ../01-architecture/thrml-runtime.md
- THRML docs: https://docs.thrml.ai/
- THRML architecture: https://docs.thrml.ai/en/latest/architecture/
- Block sampling API: https://docs.thrml.ai/en/latest/api/block_sampling/
- Spin models example: https://docs.thrml.ai/en/latest/examples/02_spin_models/
- THRML repo: https://github.com/extropic-ai/thrml

