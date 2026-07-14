# 2026-07-14 - Reviewed Analysis API Integration

## Paper Hook

This entry feeds the software-interface and reproducibility sections: it records the smallest
reviewed package surface that can execute a categorical-to-Ising, target-assessment, exact-
comparison, communication-profiling, and cluster-move audit path without private imports.

## Decision

The package root now exports the reviewed constructors, operations, and direct result/specification
classes from categorical/domain-wall lowering, target specifications, exact distribution analysis,
fixed-point quantization, hardware assessment, communication profiling, and isoenergetic cluster
moves. `__all__` remains an explicit deterministic list with no duplicates.

Private wall labels, internal helpers, type aliases, constants, and nested evidence-row classes are
not re-exported. They remain available from their defining modules where intentionally public, but
they do not expand the package-level compatibility contract. In particular,
`_DomainWallVariable` is neither in `gibbsiq.__all__` nor attached to the package root.

Rejected alternatives:

- Wildcard module re-exports were rejected because they would expose implementation details and
  make future compatibility changes accidental.
- Re-exporting every nested evidence row was rejected because callers receive them through the
  direct result classes and no independent construction use case has been reviewed.
- Re-exporting private domain-wall labels was rejected because their representation is an internal
  deterministic compiler identity, not a user model API.
- Changing runtime defaults or sampler behavior during package integration was rejected; this pass
  changes imports and tests only.

## Smoke Contract

`test_public_api_thermomap.py` imports through `gibbsiq` and executes one tiny path:

```text
pairwise categorical model -> domain-wall Ising lowering
  -> TSUSpec admissibility + fixed-point quantization
  -> exact Boltzmann comparison
  -> chain communication profile + exact small-order search + Potts evaluation
  -> isoenergetic cluster move metadata
```

The test also verifies the exact tranche order inside `__all__`, uniqueness of the complete export
list, direct import of the numerical exception, and exclusion of the private wall-label class.

This is an import/composition smoke test, not evidence of physical hardware support, mixing quality,
measured performance, or API stability beyond the reviewed alpha tranche.

## Verification

The public smoke tests were run together with the corrected communication tests:

```powershell
$env:PYTHONPATH = "src"
python -m unittest test_suite.tests.test_communication_profile `
  test_suite.tests.test_public_api_thermomap -v
```

Result: 24 tests ran in 0.024 seconds and passed, including the two public-package tests. Ruff lint
and format-check passed for `src/gibbsiq/__init__.py` and the smoke test; mypy reported success for
the package root. The root integrator owns the repository-wide test run.

| Path | SHA-256 |
| --- | --- |
| `src/gibbsiq/__init__.py` | `77FE43B3BC4282813C310183BEB3A8184212177AF08AF969064AF36017C80497` |
| `test_suite/tests/test_public_api_thermomap.py` | `9BF0D071731BC268558813DB5FE8C74F619039E301A61E648A65B9B44B9A675A` |
