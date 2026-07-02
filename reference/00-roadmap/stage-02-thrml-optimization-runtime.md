# Stage 2 - THRML Optimization Runtime

**Status: Complete (2026-07-01).** Stage 1 provided the canonical Ising model and `SampleResult`.
Stage 2 has connected that model to THRML. The runtime lowers an Ising instance into THRML
nodes, factors, graph-colored blocks, sampling schedules, initialization state, and a
sampling program, returning a `SampleResult` containing raw samples, recomputed energies,
traces, and metadata. Implemented: `THRMLSampler.sample`, `THRMLSampler.sample_qubo`,
`THRMLSampler.sample_ising`; audited IR-to-THRML lowering with verified sign mapping;
deterministic DSATUR graph-coloring block partitioner with validation and density metadata; seed, initialization,
schedule, and `num_reads` support; independent energy evaluator; trace capture with per-chain
identifiers and beta schedules; runtime metadata (THRML/JAX versions, device, timing split,
block stats). Exhaustive small-instance empirical-vs-analytic validation passes in the test
suite (four-variable dense instance, full state space against analytic Boltzmann
probabilities). Open exit criterion: parallel-tempering execution.

The immediate validation target is a tiny Ising run whose empirical frequencies match
analytic Boltzmann probabilities within a declared statistical interval. This test checks
both the lowering and the conditional sign before larger optimization claims are made.

## Goal

Run small Ising/BQM problems through THRML using audited lowering, graph-aware block
construction, explicit schedule and seed control, trace capture, and canonical energy
recomputation.

## Deliverables

- `THRMLSampler.sample`.
- `THRMLSampler.sample_qubo`.
- `THRMLSampler.sample_ising`.
- IR-to-THRML lowering.
- Graph-coloring block partitioner.
- Seed, initialization, schedule, and `num_reads` support.
- Independent energy evaluator.
- Minimal trace capture: sampled states, energies, best-so-far energy, schedule values, and
  block metadata.
- THRML runtime metadata in `SampleResult`: THRML version, device, seed, beta policy,
  initialization policy, block strategy, compile/sample timing, and source model metadata.
- API surface for batched multi-chain execution and parallel tempering. The implementation
  may initially run one chain and one beta, but the result schema must be able to record chain
  and beta identifiers later.

## Exit Criteria

- Small Max-Cut and random Ising run through THRML.
- Fixed seed is reproducible.
- Returned energies match internal convention.
- Multiple reads return stable schema.
- Exhaustive small-instance validation passes.
- Two-spin conditional sign is verified against THRML behavior.
- Output artifacts contain enough raw data for Stage 3 diagnostics without rerunning THRML.

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

Schedule policy is part of the runtime, not a caller-side afterthought. Fixed-temperature
block Gibbs is useful for correctness tests, but hard optimization instances often require
cooling schedules, multiple chains, or replica exchange. The Stage 2 configuration and result
schema must therefore avoid assumptions that there is only one chain, one beta, or one final
sample.

Dense graph behavior must be recorded. Graph coloring gives useful block parallelism on
sparse graphs; on dense QUBOs the chromatic number can approach the number of variables,
which reduces the advantage of block-parallel updates. Record graph density, color count,
block sizes, and any fallback behavior in metadata.

## References

- THRML runtime note: ../03-samplers/thrml-optimization-runtime.md
- Runtime note: ../01-architecture/thrml-runtime.md
- THRML docs: https://docs.thrml.ai/
- THRML architecture: https://docs.thrml.ai/en/latest/architecture
- Block sampling API: https://docs.thrml.ai/en/latest/api/block_sampling
- Spin models example: https://docs.thrml.ai/en/latest/examples/02_spin_models
- THRML repo: https://github.com/extropic-ai/thrml
