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
    def sample(self, bqm_or_model, *, num_reads=1, seed=None, schedule=None, **kwargs): ...
    def sample_qubo(self, Q, *, num_reads=1, seed=None, **kwargs): ...
    def sample_ising(self, h, J, *, num_reads=1, seed=None, **kwargs): ...
```

## Parameters

Required v0:

- `num_reads`
- `seed`
- `n_warmup`
- `n_samples`
- `steps_per_sample`
- `beta` or `beta_schedule`
- `initial_states`
- `block_strategy`
- `trace`

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
    samples: np.ndarray
    variables: list
    energies: np.ndarray
    best_sample: dict
    best_energy: float
    vartype: str
    traces: dict
    diagnostics: dict
    metadata: dict

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

