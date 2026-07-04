# 2026-07-04 - Strict scalar validation and quality gates

## Paper Hook

This entry feeds the methods and artifact-quality sections of the evaluation
paper. The harness rejects scalar type confusion, records sampler provenance
through smaller runtime helpers, and adds reproducible lint/type gates that can
be cited as part of the public artifact contract.

## Context

The full-package review found two executable strictness defects: the generic
fixture comparator accepted `True == 1` and `False == 0`, and `SampleResult`
accepted Python bools as spin, binary, or categorical sample states. Both cases
weaken the anti-gaming contract because a candidate could satisfy a scalar field
with the wrong JSON type or serialize a spin sample as `true` instead of `1`.

The same review identified `THRMLSampler.sample()` as the only high-value local
readability refactor: the method performed lowering, scheduling, execution,
decode, trace assembly, metadata assembly, diagnostics, and result construction
inline. The phase order was correct, so the refactor needed to reduce local
state without changing the emitted `SampleResult`.

## Hard-Parts Analysis

H1. Bool/int strictness binds to the oracle. Python makes `bool` a subclass of
`int`, so equality and tuple-membership checks accept the wrong type unless the
bool guard runs before numeric comparison. The evaluator now requires expected
bools to match actual bools, and integer expected values reject actual bools.

H2. Result validation chooses rejection over coercion. Coercing `True` to `1`
would hide malformed producer output and preserve a lossy JSON path. Rejecting
bools in `SampleResult.__post_init__` matches `_resolve_num_states`, keeps raw
samples type-honest, and forces upstream decoders to perform intentional
conversion.

H3. The runtime refactor preserves phase boundaries. `_decode_sample_chains`
owns the per-chain sample, energy, best-so-far, and chain-id alignment. `_build_metadata`
owns sampler, backend, schedule, graph, sign-convention, and timing provenance.
The public method still reads as lower, schedule, run, decode, traces, metadata,
diagnostics, result.

H4. The quality-gate baseline is passing without suppressing source errors.
The mypy step checks `src/gibbsiq` with `check_untyped_defs` and `strict_equality`;
the fixes make the existing annotations explicit enough for a clean baseline.
Ruff is configured at line length 110 with the E/F/B rule baseline and the
repository is formatter-normalized once so `ruff format --check .` is an
enforceable CI step.

## Decisions

- `evaluation.compare_values` now rejects bool/int substitution in both
  directions. This matches `benchmark_oracle._scalar_diffs`, whose scalar rule
  requires exact type equality except for non-bool int/float numeric equality.
- `SampleResult` now rejects Python bool sample values before domain membership
  checks. The runtime already decodes THRML booleans with `int(value)`, so this
  catches malformed external producers without changing THRML sampler output.
- `THRMLSampler.sample()` now delegates chain decode to `_decode_sample_chains`
  and provenance construction to `_build_metadata`. The helpers are private and
  keep the same trace keys, metadata keys, timings, and best-index rule.
- Development tooling is dev-only. `pyproject.toml` adds `ruff>=0.12` and
  `mypy>=1.16` to the `dev` extra, configures Ruff and mypy, and CI runs
  `ruff check .`, `ruff format --check .`, and `mypy` after `pip install -e ".[dev]"`.
- Ruff formatting was applied once across Python files. The formatter reported
  28 files reformatted and 9 files unchanged; the follow-up check reported
  37 files already formatted.

## Rejected Alternatives

- Coercing bool sample values inside `SampleResult`: this would serialize a
  malformed input as if it had been intentional. Rejection keeps producer
  boundaries explicit and matches the existing strictness of `num_states`.
- Adding a shared scalar-comparison helper between `evaluation` and
  `benchmark_oracle`: the oracle remains deliberately independent of the
  generic fixture comparator. The duplicated bool guard is smaller than a shared
  module and preserves the acyclic dependency graph.
- Weakening mypy with broad `ignore_errors`: the reported issues were local
  type-narrowing gaps, not design blockers. The step now passes by improving
  annotations, control-flow narrowing, and branch-local names.
- Deferring Ruff formatting while enforcing `ruff format --check` in CI: the
  check would fail immediately on a fresh clone. Applying the formatter once
  gives CI a stable baseline.

## Sources Read / Examples Used

- Ruff configuration documentation, Astral `ruff` repository:
  https://github.com/astral-sh/ruff/blob/main/docs/configuration.md.
- mypy configuration documentation, Python `mypy` repository:
  https://github.com/python/mypy/blob/master/docs/source/config_file.md.
- Local strictness reference: `src/gibbsiq/benchmark_oracle.py`
  `_scalar_diffs` and `close_within`.
- Local regression targets: `test_suite/tests/test_evaluation_harness.py` and
  `test_suite/tests/test_categorical_result.py`.

## Verification

- `python -m pip install -e ".[dev]"`: pass. The run installed `ruff 0.15.20`
  and `mypy 2.1.0` into the local environment and rebuilt editable
  `gibbsiq-0.1.0`.
- `ruff check .`: pass, "All checks passed!".
- `ruff format --check .`: pass, "37 files already formatted".
- `mypy`: pass, "Success: no issues found in 10 source files".
- `$env:PYTHONPATH = "src"; python -m unittest discover -s test_suite/tests`:
  pass, 267 tests in 42.779 s. The run emitted the known ArviZ
  zero-variance runtime warning during diagnostics cross-checks and still
  completed with `OK`.

## Addendum: Final quality review verification

The final review used the official Python style sources requested for this
pass: PEP 8 for naming and readability conventions, PEP 20 for the simplicity
and explicitness principles, and the Python `typing` documentation for the role
of type annotations. Ruff and mypy configuration were checked against their
current project documentation before the CI gates were kept.

The package import graph remains acyclic after the refactor. The current
`src/gibbsiq` package has nine implementation modules: `model` and
`benchmark_oracle` have no local dependencies; `blocks`, `conversions`,
`diagnostics`, and `result` depend on `model`; `benchmark_bridge` depends on
`benchmark_oracle`, `conversions`, `model`, and `result`; `evaluation` depends
on `benchmark_oracle`; `thrml_runtime` depends on `blocks`, `conversions`,
`diagnostics`, `model`, and `result`. This preserves the intended layered
architecture.

Additional commands run in the final pass:

- `python -m pip install -e ".[dev]"`: pass. The editable build produced
  `gibbsiq-0.1.0-0.editable-py3-none-any.whl` with SHA-256
  `b6d081acb914338d8d81f93d8087e6820f3f518f47624dde5321ca83313a5385`.
- `ruff check .`: pass.
- `ruff format --check .`: pass, 37 files already formatted.
- `mypy`: pass, no issues in 10 source files.
- `python tools/check_markdown_math.py`: pass.
- `$env:PYTHONPATH = "src"; python -m compileall -q src tools test_suite`: pass.
- `$env:PYTHONPATH = "src"; python -m unittest discover -s test_suite/tests`:
  pass, 267 tests in 46.042 s. The known ArviZ zero-variance runtime warning
  appeared during diagnostics cross-checks.
- `python -m pip install --dry-run --no-deps .`: pass, resolves
  `gibbsiq-0.1.0`.
- `git diff --check`: pass.
- `$env:PYTHONPATH = "src"; python -m gibbsiq.evaluation .\test_suite\examples\evaluation-candidate.example.json`:
  expected exit code 1, with 12 exact/diagnostic fixtures passed and 27
  benchmark fixtures missing from the example candidate.
