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

Extract a helper when callers share the same behavior and error contract. Keep
independent numerical oracles separate from the implementation they verify.
Remove a test only when it checks no product behavior or another test covers the
same inputs, assertions, and failure mode. Numerical assertions should use an
independent expected value and a tolerance justified by the algorithm or dtype.

Keep local agent instructions, planning notes, research downloads, and generated
run records out of Git. Commit user documentation, small reproducible fixtures,
and required license notices alongside the code they support.
Put personal editor settings, agent notes, and ad hoc scratch paths in
`.git/info/exclude`; reserve `.gitignore` for shared build and runtime output.

Add a regression test when fixing a bug. Update the relevant guide when behavior
changes, and add a concise changelog entry for user-facing changes.

## Before opening a pull request

Run the focused tests, the full relevant suite, lint, formatting, and type checks.
Build the distributions with `python -m build` and validate them with
`python -m twine check --strict dist/*` when changing packaging.

Explain what changed and how it was tested. Keep each change focused enough to
review independently. The [release guide](docs/qualification/local-release-contract.md)
covers package verification.

Use a short imperative commit subject that describes the change. Explain why in
the body when the reason is not clear from the diff. A type prefix such as `fix:`
is optional; avoid vague subjects such as "cleanup" or claims about code quality.

These conventions draw on [Google's review checklist](https://google.github.io/eng-practices/review/reviewer/looking-for.html),
[Google's change descriptions](https://google.github.io/eng-practices/review/developer/cl-descriptions.html),
[AWS commit guidance](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/dl.cr.7-create-consistent-and-descriptive-commit-messages-using-a-specification.html),
and [NumPy's testing guidelines](https://numpy.org/doc/stable/reference/testing.html).
