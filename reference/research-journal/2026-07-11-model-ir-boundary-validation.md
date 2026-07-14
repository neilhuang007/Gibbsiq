# 2026-07-11 - Model IR Boundary Validation

## Paper Hook

This entry feeds the methods section on model correctness and verifiable rewards. The
canonical Ising IR now rejects a coefficient whose label lies outside the declared variable
set, so direct construction cannot silently change the represented Hamiltonian.

## Context

`IsingModel.__post_init__` previously formed normalized linear biases by iterating over
`variables` and calling `self.linear.get(variable, 0.0)`. The direct input
`IsingModel(variables=("a",), linear={"b": 3.0}, quadratic={})` therefore produced a
zero-bias one-variable model and discarded the supplied coefficient. Quadratic terms already
reject endpoint labels outside `variables`.

## Hard-Parts Analysis

### H1. Preserve sparse linear input while rejecting undeclared labels

An absent bias for a declared variable has the canonical value `0.0`; this permits sparse
linear mappings. A supplied bias for an undeclared label changes the input domain and must
raise before normalization. The implementation checks every supplied linear key against the
same variable index used by quadratic validation, then retains the existing zero-fill step
for declared variables.

## Decisions

We raise `ValueError` with the message `linear bias for <label> references unknown variable`.
This matches the existing quadratic unknown-variable contract and identifies the invalid
coefficient at the model boundary. The regression test also constructs a two-variable model
with one omitted declared bias and verifies the normalized value `0.0`.

## Rejected Alternatives

Silently extending `variables` from the linear mapping was rejected because explicit
`variables` and `variable_order` define the canonical state-vector layout. Continuing to
drop extra keys was rejected because it changes every energy containing that coefficient
without surfacing an invalid model.

## Sources Read / Examples Used

- `reference/08-evaluation/equation-audit.md`, EVAL-EQ-001, defines the canonical Ising
  energy over the declared variables.
- `reference/08-evaluation/evaluation-framework.md`, Model Compatibility, requires exact
  model preservation and deterministic variable ordering.
- `src/gibbsiq/model.py`, quadratic normalization, supplies the existing unknown-variable
  exception contract.

## Verification

Environment: Python from the repository `.venv` on Windows; the checks are deterministic and
use no random seed.

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m unittest test_suite.tests.test_model_compatibility
```

Result: 9 tests ran in 0.002 seconds; all passed.

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m unittest test_suite.tests.test_model_compatibility test_suite.tests.test_immutability_and_provenance test_suite.tests.test_conversion_scenarios test_suite.tests.test_stage_01_core_model_compatibility
```

Result: 43 tests ran in 0.140 seconds; all passed.

```powershell
.\.venv\Scripts\python.exe -m ruff check src/gibbsiq/model.py test_suite/tests/test_model_compatibility.py
.\.venv\Scripts\python.exe -m ruff format --check src/gibbsiq/model.py test_suite/tests/test_model_compatibility.py
```

Result: Ruff reported all checks passed and both files formatted.
