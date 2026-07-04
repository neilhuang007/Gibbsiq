# 2026-07-04 — CI mypy failure on numpy 2.5 stubs, and vendored dimod/arviz-stats suites

## Paper Hook

The trust-layer thesis rests on a reproducible type-checked contract. A green CI
that silently type-checks against a drifting dependency stack is worth recording:
the failure here is a dependency-resolution effect, not a code defect, and the fix
that survived CI differs from the fix that passed a local reproduction.

## Context

The `test-thrml` CI job (`.github/workflows/ci.yml`) installs the optional extras
with a fresh `pip install -e ".[dev]"` and runs ruff, mypy, then the THRML
end-to-end tests. The job began failing at the mypy step. The `test` job (stdlib
only, no extras) stayed green throughout. Two unrelated pieces of work shared the
branch: local benchmark-harness commits already pushed, and a concurrent agent's
uncommitted parallel-tempering cache implementation. The CI fix was kept isolated
from the concurrent work, which was left uncommitted and untouched.

## Hard-Parts Analysis

H1. Locating the fault. mypy reported
`numpy/__init__.pyi:737: error: Type statement is only supported in Python 3.12
and greater [syntax]`. numpy is not a declared dependency of gibbsiq and appears
nowhere in `src/gibbsiq` as a direct import; a fresh CI install resolved it to
2.5.1 as a transitive dependency of the arviz/dimod/thrml stack. numpy 2.5's stubs
use PEP 695 `type` statements, which mypy parses against its configured
`python_version`; under the project target of 3.10 the parse is rejected. The
error is a syntax-target check keyed on `python_version`, emitted the moment mypy
loads the stub, and it halts further checking (`errors prevented further
checking`), so nothing downstream is validated until it is resolved.

H2. Why the first fix passed locally and failed in CI. `src/gibbsiq` imports only
three third-party packages, each inside a guarded function: `thrml` and `jax`
(`thrml_runtime.py`), and `dimod` (`model.py`, `result.py`). The reasoning was to
cut mypy's import-follow at each backend boundary so it never reaches numpy, via
per-module `follow_imports = "skip"`. A faithful local reproduction against
numpy 2.5.1 with fake `thrml`/`dimod`/`jax` packages that each `import numpy`
confirmed the mechanism: skipping only `thrml` reproduced the error, skipping
`thrml`+`dimod`+`jax` (each plus its `.*`) type-checked cleanly, and the pyproject
`[[tool.mypy.overrides]]` array-of-tables form behaved identically to the
`[mypy-...]` INI form. Both the thrml-only and the complete skip lists were pushed;
both still failed CI with the identical numpy error. The local reproduction could
not reproduce the CI failure because the CI environment has the real jax stack and
numpy 2.5.1, while the local interpreter has numpy 2.4.6 whose stubs parse under
3.10. The conclusion is empirical: in the real environment mypy loads numpy's stub
despite the follow-imports skips, for a path the fake-package model does not
capture. The skip is therefore not a reliable lever against this failure.

H3. Choosing a fix that is independent of the import path. The error condition is
definitional: the stub is rejected only because the target is below 3.12. Raising
`python_version` to 3.12 makes the stub parse the moment it is reached, regardless
of how mypy reaches it, which is exactly the property the follow-imports approach
lacked. This was confirmed against real numpy 2.5.1 (targets 3.12 and 3.13 both
succeed on a file that imports numpy directly). The cost is the loss of the 3.10
syntax-target guardrail for gibbsiq's own code; `requires-python` stays `>= 3.10`
and the runtime code remains 3.10-compatible, so only mypy's syntax target moves.

## Decisions

1. Set `[tool.mypy] python_version = "3.12"` — the minimum the numpy 2.5 stubs
   require. This is the fix that turned CI green (run on `cb7b7e3`: `test-thrml`
   and `test` both success).
2. Keep `[[tool.mypy.overrides]] follow_imports = "skip"` for
   `thrml`/`dimod`/`jax` and their submodules. It does not prevent the numpy stub
   load on its own, but it keeps mypy out of the jax/numpy stack so a future stub
   change in those packages cannot introduce unrelated type errors into the
   gibbsiq check.
3. Vendor the upstream test suites under `test_suite/vendor/` as cross-validation
   reference material: `dimod` (QUBO/Ising/BQM contracts, sample-set semantics)
   from `dwavesystems/dimod@bad4cba`, and `arviz-stats` (split R-hat and ESS/tau
   diagnostics) from `arviz-devs/arviz-stats@856b310`. In arviz 1.x the diagnostics
   tests live in the separate `arviz-stats` repository; the `arviz` meta-package
   has only a namespace test.
4. Copy the full dimod `tests/` including its small `data/` fixtures, and every
   Python test module from arviz-stats preserving structure, while omitting the
   large binary netCDF fixtures (`loo/roaches.nc.xz` ~14.9 MB,
   `univariate_normal.nc` ~1.1 MB) that back unrelated LOO/metrics tests. The
   omission is documented in `test_suite/vendor/README.md` with the paths and
   sizes so the reduction is auditable.
5. Exclude the vendored tree from ruff (`[tool.ruff] extend-exclude`). mypy is
   already scoped to `src/gibbsiq` and unittest discovery starts at
   `test_suite/tests`, so the vendored suites are reference-only and touch no CI
   gate. Both upstreams are Apache-2.0; each subdirectory retains the upstream
   `LICENSE`.

## Rejected Alternatives

- `follow_imports = "skip"` on numpy itself: a local reproduction confirmed the
  parse error still fires once the stub is reached, so skipping the leaf does
  nothing.
- Pinning `numpy < 2.5` in the dev extras: changes the dependency the tests run
  against and masks the incompatibility rather than accommodating it.
- Vendoring the arviz-stats binary fixtures to keep the LOO tests runnable:
  ~15 MB of data for statistical methods gibbsiq does not implement, against a
  repository whose value is a lean zero-dependency core.

## Verification

- `cb7b7e3` CI run: `test-thrml` success, `test` success.
- Local reproduction (numpy 2.5.1 + mypy 2.1.0): `python_version = 3.12` and
  `3.13` both type-check a direct numpy import; `python_version = 3.10` with the
  complete follow-imports skip list type-checks the fake-package model but does
  not hold in CI.
- Vendored tip verified in an isolated worktree before push: ruff check, ruff
  format, mypy, markdown-math, and the 269-test suite all pass; vendored files add
  zero discovered tests and are skipped by ruff.

## Follow-Up

- Add the numpy-2.5-stub / mypy-`python_version` interaction to
  `gotchas-and-todo.md` once the concurrent parallel-tempering edits to that file
  land, to avoid a merge collision.
- The concurrent parallel-tempering cache work carries a failing test
  (`test_parallel_tempering_records_swap_and_per_beta_traces`: `swap_attempts` 3
  vs 5) and remains uncommitted; the CI fix and the vendored suites were committed
  without it.
