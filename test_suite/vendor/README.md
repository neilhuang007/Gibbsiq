# Vendored third-party test suites

This directory holds upstream test suites copied verbatim from other projects. They
are cross-validation reference material for Gibbsiq, not part of Gibbsiq's own test
run: `python -m unittest discover -s test_suite/tests` starts at `test_suite/tests`
and never descends into `test_suite/vendor`, and the directory is excluded from
`ruff` (see `[tool.ruff] extend-exclude` in `pyproject.toml`). mypy is already scoped
to `src/gibbsiq`, so it does not see these files either. Read and adapt them; do not
expect them to run in place against Gibbsiq's tooling.

## Why these two suites

- **dimod** is the reference for the QUBO / Ising / BQM contracts Gibbsiq interoperates
  with. `test_bqm.py`, `test_quadratic_model.py`, `test_vartypes.py`, and
  `test_sampleset.py` pin the energy convention, vartype handling, and sample-set
  semantics that Gibbsiq's `model.py`, `conversions.py`, and `result.py` mirror.
- **arviz-stats** is the reference for the MCMC diagnostics Gibbsiq reimplements in pure
  stdlib. `tests/base/test_diagnostics.py` covers the split R-hat and ESS/tau algorithms
  that Gibbsiq cross-checks in `test_suite/tests/test_diagnostics_arviz_crosscheck.py`.
  In arviz 1.x the diagnostics and their tests live in the separate `arviz-stats` repo;
  the top-level `arviz-devs/arviz` repository is a meta-package whose only test is a
  namespace check, so `arviz-stats` is the suite worth vendoring.

## Provenance

Cloned 2026-07-04 (shallow `--depth 1`).

| Name        | Upstream repository                          | Commit    |
| ----------- | -------------------------------------------- | --------- |
| dimod       | https://github.com/dwavesystems/dimod        | `bad4cba` |
| arviz-stats | https://github.com/arviz-devs/arviz-stats    | `856b310` |

For reference, the arviz meta-package repository is
https://github.com/arviz-devs/arviz at commit `3d7ef50`.

## Licensing

Both projects are Apache License 2.0. Each vendored subdirectory keeps the upstream
`LICENSE` file (`dimod/LICENSE`, `arviz-stats/LICENSE`); retain them and the copyright
notices per the terms of that license.

## What was copied, and what was left out

- **dimod/** — the complete upstream `tests/` directory, including the small
  `tests/data/` fixtures (~121 KB) and `requirements.txt`. Nothing omitted.
- **arviz-stats/** — every Python test module under the upstream `tests/` tree,
  preserving structure (`tests/base/`, `tests/loo/`, `tests/numba/`). All non-Python
  data fixtures were omitted: the suite ships large binary netCDF datasets, dominated by
  `tests/loo/roaches.nc.xz` (~14.9 MB) and `tests/univariate_normal.nc` (~1.1 MB), which
  back the LOO / metrics / survival tests that are unrelated to Gibbsiq's R-hat/ESS
  diagnostics. They are left out to keep this zero-dependency repository lean.
  Consequence: the tests that load those fixtures will not run as-is; the diagnostics
  reference — `tests/base/test_diagnostics.py` — does not depend on them.
