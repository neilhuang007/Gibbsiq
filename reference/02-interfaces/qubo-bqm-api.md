# QUBO / BQM API

## Sources

- dimod docs: https://docs.dwavequantum.com/en/latest/ocean/api_ref_dimod/
- `dimod.Sampler.sample`: https://docs.dwavequantum.com/en/latest/ocean/api_ref_dimod/generated/dimod.Sampler.sample.html
- dimod repo: https://github.com/dwavesystems/dimod
- PyQUBO docs: https://pyqubo.readthedocs.io/en/latest/getting_started.html
- PyQUBO repo: https://github.com/recruit-communications/pyqubo
- OpenJij tutorial: https://tutorial.openjij.org/en/tutorial/001-openjij_introduction.html

## Public API

```python
model = compile_qubo(Q)
result = THRMLSampler(config).sample(model, num_reads=128)
sampleset = result.to_dimod()
```

Sampler methods:

```python
class THRMLSampler:
    def __init__(self, config: SamplerConfig | None = None): ...
    def sample(self, model, *, num_reads=1, partition=None): ...
    def sample_qubo(self, Q, *, num_reads=1, **compile_kwargs): ...
    def sample_ising(self, h, J=None, *, num_reads=1, **compile_kwargs): ...
```

## Parameters

`SamplerConfig` controls one run:

- `beta`
- `n_warmup`
- `steps_per_sample`
- `num_chains`
- `seed`
- `init`
- `warmup_beta_ladder`
- `parallel_tempering_betas`
- `parallel_tempering_swap_interval`

`sample()` accepts an already compiled `IsingModel`, `num_reads`, and an optional validated
`BlockPartition`. It constructs a deterministic coloring when the partition is omitted.
`sample_qubo()` and `sample_ising()` accept conversion keyword arguments and then enter the
same model path. Per-call seed, arbitrary initial-state arrays, trace toggles, and a generic
schedule object are not current API parameters.

## QUBO Conversion

QUBO:

```text
minimize x^T Q x
x_i in {0, 1}
```

Spin mapping:

```text
x_i = (s_i + 1) / 2
s_i in {-1, +1}
```

Implementation requirements:

- diagonal QUBO entries become binary linear terms;
- preserve offset;
- deterministic variable order;
- exhaustive energy-equivalence tests for small models.

## Result Schema

```python
class SampleResult:
    samples: tuple[Mapping[Variable, int], ...]
    variables: tuple[Variable, ...]
    energies: tuple[float, ...]
    interaction_energies: tuple[float, ...]
    best_sample: dict
    best_energy: float
    vartype: str
    traces: Mapping
    diagnostics: Mapping
    metadata: Mapping
    num_states: Mapping[Variable, int] | None

    def to_dimod(self): ...
```

Metadata:

- source format;
- conversion offset;
- variable order;
- solver/backend versions;
- seed;
- schedule;
- block strategy;
- device;
- timing.

## Lossless Machine Serialization

`IsingModel.to_dict()` and `SampleResult.to_dict()` never stringify arbitrary labels into JSON
object keys. Schema v1 is retained only for comma-free string labels, where the legacy linear
and `"left,right"` quadratic mappings are injective. Models or results with typed or
delimiter-bearing labels use schema v2:

- variables are encoded with explicit type tags;
- linear coefficients and samples are positional in the recorded variable order;
- quadratic rows store integer endpoint positions and a coefficient;
- duplicate positional rows and malformed typed labels are rejected during model decoding.

Supported serialized label types are `None`, Boolean, integer, finite float, string, bytes,
tuple, and frozenset. Opaque labels remain usable with an explicit in-memory variable order but
fail serialization explicitly rather than falling back to process-specific `repr()` output.
Metadata mappings retain ordinary JSON-object shape and therefore require string keys; sets are
serialized in deterministic typed order. `compile_ising(model.to_dict())` accepts both model
wire schemas.
