# Stage 6 - Adaptive Hardware-Aware Runtime

**Status: Partial analysis foundation; adaptive execution absent.** The current package exports
a provenanced abstract `TSUSpec`, coefficient quantization with exact small-law comparison,
logical target admissibility, and supplied-partition chain-communication proxies. It does not
automatically partition, place, route, calibrate costs, adapt a running sampler, or execute a
physical TSU. The broader ThermoMap compiler sequence is defined in
`autonomous-implementation-roadmap.md`.

## Goal

Add adaptive schedules, topology-aware blocks, restarts, and hardware-aligned metadata.

This stage is one runtime component of the ThermoMap capability track inside Gibbsiq. The
Python package remains `gibbsiq`.

## Deliverables

- Schedule search.
- Adaptive schedule controls.
- Topology-aware block partitioning.
- Warm starts.
- Restart policies.
- Sparse/dense execution strategies.
- Hardware/topology metadata.
- Benchmark studies for adaptive controls.

## Exit Criteria

- Adaptive controls improve at least one benchmark family.
- Block/schedule metadata explains run behavior.
- Topology constraints are separate from problem semantics.
- Public QUBO/BQM interface remains stable.

## Implementation Notes

Adaptive signals:

- no improvement window;
- high autocorrelation;
- low block flip rate;
- chain disagreement;
- low diversity;
- feasibility plateau.

Controls:

- restart chains;
- reheat / slow cooling;
- adjust `steps_per_sample`;
- change block order;
- change partition strategy;
- use baseline warm starts.

## References

- Runtime note: ../01-architecture/thrml-runtime.md
- THRML runtime note: ../03-samplers/thrml-optimization-runtime.md
- Theory note: ../05-theory/probabilistic-computing-and-pbits.md
- THRML docs: https://docs.thrml.ai/
- THRML architecture: https://docs.thrml.ai/en/latest/architecture
- Extropic thermodynamic computing: http://extropic.ai/writing/thermodynamic-computing-from-zero-to-one
- pc-COP: https://arxiv.org/html/2504.04543v1
- p-Bits for PSL: https://arxiv.org/abs/1809.04028
