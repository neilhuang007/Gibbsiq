# Gibbsiq

**QUBO and Ising optimization on THRML, with exact oracles and mixing diagnostics.**

Gibbsiq compiles discrete optimization problems such as the traveling salesman
problem into Ising models, samples them with block Gibbs on a standard-library
reference sampler or on Extropic's THRML runtime, and reports whether the answer
can be trusted. A penalty certificate shows that the constraint weights are
adequate, exact enumeration proves the optimum on small instances, and effective
sample size and split R-hat say whether the chains mixed.

A sampler that returns the right tour once is not evidence that it will again.
Gibbsiq records the model, the seed, the backend, and the diagnostics with each
result, so a run can be repeated, compared, and audited.

- **Compile:** build QUBO and Ising models from coefficients, constraints, TSP,
  and knapsack formulations, with penalty certificates and domain-wall encodings.
- **Sample:** run block Gibbs with the reference sampler or the THRML backend,
  with parallel tempering and cluster moves.
- **Verify:** compare samples with exact Boltzmann distributions and with ground
  states obtained by enumeration.
- **Diagnose:** compute effective sample size, split R-hat, autocorrelation, and
  mixing flags for every result.
- **Qualify:** compare stochastic executions with a reference using confidence
  intervals and regression checks through the `gibbsiq` command.

## Install

Requires Python 3.10 or newer. Install from a checkout:

```console
git clone https://github.com/neilhuang007/Gibbsiq.git
cd Gibbsiq
python -m pip install .
```

The core uses the Python standard library. Optional integrations add NumPy,
dimod, NetworkX, THRML, Torx, and Z1T.
See [installation](https://github.com/neilhuang007/Gibbsiq/blob/master/docs/installation.md) for environment recipes.

## Solve a TSP

```console
python examples/tsp_qubo_ground_state.py
```

The script compiles a four-city tour as a QUBO, prints the penalty certificate,
enumerates all 65,536 spin states to prove that the optimum tour has length 18,
samples the model with a seeded reference run, and reports the effective sample
size, split R-hat, and mixing flags. Add `--backend thrml` to sample on THRML;
this needs the `thrml` extra and enables 64-bit JAX so that the audited logit
error stays within tolerance.

## Python API

```python
from gibbsiq import ReferenceGibbsSampler, ReferenceSamplerConfig, SampleResult, compile_tsp

distances = ((0, 2, 9, 10), (2, 0, 6, 4), (9, 6, 0, 3), (10, 4, 3, 0))
encoding = compile_tsp(distances)
print(encoding.penalty_policy.status)

config = ReferenceSamplerConfig(beta=1.0, n_warmup=300, steps_per_sample=2, num_chains=4, seed=7)
raw = ReferenceGibbsSampler(config).sample(encoding.ising_model, num_reads=400)
samples = [dict(zip(raw.variables, state)) for state in raw.samples]
result = SampleResult.from_model(encoding.ising_model, samples, vartype="SPIN")
print(min(result.energies))
```

Exact references are available for small models:

```python
from gibbsiq import compile_ising, exact_boltzmann_distribution

model = compile_ising({"a": 0.25, "b": -0.5}, {("a", "b"): 1.0})
distribution = exact_boltzmann_distribution(model, beta=1.0)
```

The [TSP example](https://github.com/neilhuang007/Gibbsiq/blob/master/examples/tsp_qubo_ground_state.py)
shows the exact ground-state check and the diagnostics call. Sign and counting
conventions are defined in
[model conventions](https://github.com/neilhuang007/Gibbsiq/blob/master/docs/model-conventions.md).

## Stochastic qualification

The `gibbsiq` command compares a stochastic execution with a reference and
evaluates the difference against a declared tolerance:

```console
gibbsiq qualify --example spin-conditional --output runs/baseline
gibbsiq inspect runs/baseline --verify
gibbsiq qualify --example spin-conditional --candidate sign-reversed --runs 256 --output runs/defect
gibbsiq compare runs/baseline runs/defect --candidate-change spin-conditional-sign-reversed-v1
```

The defective experiment and its regression comparison return exit code 1. The
Python API exposes `qualify`, `inspect_bundle`, `compare_bundles`, and
`run_search`; see the
[qualification quickstart](https://github.com/neilhuang007/Gibbsiq/blob/master/src/gibbsiq/data/qualification/QUICKSTART.md)
and the [Python workflow](https://github.com/neilhuang007/Gibbsiq/blob/master/docs/qualification/workflow-contract.md).

## Documentation

- [User guide](https://github.com/neilhuang007/Gibbsiq/blob/master/docs/README.md)
- [Model conventions](https://github.com/neilhuang007/Gibbsiq/blob/master/docs/model-conventions.md)
- [TSP example](https://github.com/neilhuang007/Gibbsiq/blob/master/examples/tsp_qubo_ground_state.py)
- [Qualification quickstart](https://github.com/neilhuang007/Gibbsiq/blob/master/src/gibbsiq/data/qualification/QUICKSTART.md)
- [Z1T model evaluation](https://github.com/neilhuang007/Gibbsiq/blob/master/docs/qualification/z1t.md)
- [Contributing](https://github.com/neilhuang007/Gibbsiq/blob/master/CONTRIBUTING.md)
- [Changelog](https://github.com/neilhuang007/Gibbsiq/blob/master/CHANGELOG.md)
- [Release process](https://github.com/neilhuang007/Gibbsiq/blob/master/docs/qualification/local-release-contract.md)

## License

Gibbsiq is [MIT licensed](https://github.com/neilhuang007/Gibbsiq/blob/master/LICENSE). Adapted Z1T code carries
[Apache-2.0 attribution](https://github.com/neilhuang007/Gibbsiq/blob/master/src/gibbsiq/qualification/adapters/Z1T_LICENSE.txt).
