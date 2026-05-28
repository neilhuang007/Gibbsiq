# Stage 1 - Core Model Compatibility

## Goal

Accept QUBO, Ising, and BQM inputs and normalize them into one internal Ising IR.

## Deliverables

- `compile_qubo(Q)`.
- `compile_ising(h, J)`.
- `compile_bqm(bqm)` when `dimod` is installed.
- QUBO-to-Ising conversion tests.
- Deterministic variable ordering.
- Internal IR.
- Initial `SampleResult` schema.

## Exit Criteria

- Exhaustive energy equivalence passes for small QUBO/Ising/BQM fixtures.
- Offsets are preserved.
- Variable ordering is deterministic.
- IR is backend-independent.
- Result schema can later export to `dimod.SampleSet`.

## Implementation Notes

Internal convention:

```text
E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j
s_i in {-1, +1}
```

QUBO conversion:

```text
x_i = (s_i + 1) / 2
```

## References

- QUBO/BQM API note: ../02-interfaces/qubo-bqm-api.md
- THRML runtime note: ../01-architecture/thrml-runtime.md
- dimod docs: https://docs.dwavequantum.com/en/latest/ocean/api_ref_dimod/
- `dimod.Sampler.sample`: https://docs.dwavequantum.com/en/latest/ocean/api_ref_dimod/generated/dimod.Sampler.sample.html
- dimod repo: https://github.com/dwavesystems/dimod
- PyQUBO docs: https://pyqubo.readthedocs.io/en/latest/getting_started.html
- PyQUBO repo: https://github.com/recruit-communications/pyqubo
- OpenJij QUBO/Ising tutorial: https://tutorial.openjij.org/en/tutorial/001-openjij_introduction.html

