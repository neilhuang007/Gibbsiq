# Gibbsiq

**Validate and tune stochastic workloads.**

Gibbsiq helps you decide whether a sampler, model approximation, or execution
policy meets your application's quality requirements. It compares executions
with a reference, measures uncertainty, and saves a reproducible report.

Stochastic outputs vary from run to run. A single score can hide a sampling
error or make a backend change look better than it is. Gibbsiq turns that
comparison into a repeatable workflow: define the workload and tolerance, run
the experiment, then use the result in development or CI.

- **Qualify:** evaluate quality with explicit metrics and confidence intervals.
- **Compare:** detect regressions between compatible experiments.
- **Tune:** select sampling settings and validate them on held-out inputs.
- **Inspect:** read and verify saved results offline.
- **Model:** build QUBO/Ising problems, sample them, and compute diagnostics.

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

## Your first experiment

```console
gibbsiq qualify --example spin-conditional --output runs/baseline
gibbsiq inspect runs/baseline --verify
```

This example compares sampled spins with their analytic mean. The report shows
the estimated error, confidence interval, tolerance, and qualification result.
The output directory contains the plan, observations, metrics, and report.

Introduce a sign error and compare the results:

```console
gibbsiq qualify --example spin-conditional --candidate sign-reversed --runs 256 --output runs/defect
gibbsiq compare runs/baseline runs/defect --candidate-change spin-conditional-sign-reversed-v1
```

Both the defective experiment and its regression comparison return exit code 1.
Add `--json` to consume results in scripts.

## Python API

```python
from gibbsiq import compile_ising, exact_boltzmann_distribution

model = compile_ising({"a": 0.25, "b": -0.5}, {("a", "b"): 1.0})
distribution = exact_boltzmann_distribution(model, beta=1.0)
```

The qualification API exposes `qualify`, `inspect_bundle`, `compare_bundles`,
and `run_search`. See the [Python workflow](https://github.com/neilhuang007/Gibbsiq/blob/master/docs/qualification/workflow-contract.md)
for an executable example.

## Documentation

- [Quickstart](https://github.com/neilhuang007/Gibbsiq/blob/master/src/gibbsiq/data/qualification/QUICKSTART.md)
- [User guide](https://github.com/neilhuang007/Gibbsiq/blob/master/docs/README.md)
- [Z1T model evaluation](https://github.com/neilhuang007/Gibbsiq/blob/master/docs/qualification/z1t.md)
- [Contributing](https://github.com/neilhuang007/Gibbsiq/blob/master/CONTRIBUTING.md)
- [Changelog](https://github.com/neilhuang007/Gibbsiq/blob/master/CHANGELOG.md)
- [Release process](https://github.com/neilhuang007/Gibbsiq/blob/master/docs/qualification/local-release-contract.md)

## License

Gibbsiq is [MIT licensed](https://github.com/neilhuang007/Gibbsiq/blob/master/LICENSE). Adapted Z1T code carries
[Apache-2.0 attribution](https://github.com/neilhuang007/Gibbsiq/blob/master/src/gibbsiq/qualification/adapters/Z1T_LICENSE.txt).
