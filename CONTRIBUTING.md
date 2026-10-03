# Contributing

Open an [issue](https://github.com/neilhuang007/Gibbsiq/issues) with a reproducible
example, or submit a pull request describing the problem and resulting behavior.

## Development setup

Create and activate a Python 3.10+ virtual environment, then run:

```console
python -m pip install -e ".[dev]"
python -m unittest discover -s test_suite/tests
ruff check .
ruff format --check .
mypy
```

For numerical integration tests, use Python 3.13.5 and install
`requirements/qualification-integration.txt`. Set `JAX_PLATFORMS=cpu` and
`JAX_ENABLE_X64=false`, then run `python -m tools.run_integration_tests`.
The integration runner requires every test to execute and pass.
CI runs the core across supported Python versions and
runs the pinned numerical suite plus isolated checks of the installed wheel.

## Code and tests

- Keep the core dependency-free; import numerical libraries inside adapters.
- Use type annotations and small functions with clear inputs and outputs.
- Reuse shared validation, serialization, and numerical helpers.
- Preserve public APIs and the integer-valued `SampleResult` contract.
- Test observable behavior with independent numerical references.
- Cover meaningful failure paths, recovery, and artifact integrity.
- Prefer behavior assertions to source-text checks or incidental formatting.
- Keep experiments reproducible with explicit seeds and resource budgets.

Add a regression test when fixing a bug. Update the relevant guide when behavior
changes, and add a concise changelog entry for user-facing changes.

## Before opening a pull request

Run the focused tests, the full relevant suite, lint, formatting, and type checks.
Build the distributions with `python -m build` and validate them with
`python -m twine check --strict dist/*` when changing packaging.

Explain what changed and how it was tested. Keep each change focused enough to
review independently. The [release guide](docs/qualification/local-release-contract.md)
covers package verification.

These conventions draw on [Click's contributor guidance](https://click.palletsprojects.com/en/stable/contributing/)
and [scikit-learn's development guide](https://scikit-learn.org/stable/developers/index.html).
