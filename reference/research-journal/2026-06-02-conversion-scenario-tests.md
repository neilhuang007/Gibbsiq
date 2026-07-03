# 2026-06-02 — Conversion Scenario Coverage

Paper hook: methods section for model-normalization oracle; reward-surface table row for
QUBO/BQM/Ising conversion correctness.

## Scope

Added focused tests for the Stage 1 model-normalization step that turns QUBO, Ising,
and BQM inputs into Gibbsiq's canonical Ising IR:

```text
E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j
s_i in {-1,+1}
```

Production code was changed only to reject non-finite numeric coefficients and offsets at
the canonical IR boundary. Test coverage was added in `test_suite/tests/test_conversion_scenarios.py`.

## Sources Consulted

Search queries used:

- `D-Wave dimod BinaryQuadraticModel to_ising from_qubo offset diagonal QUBO documentation`
- `dimod qubo_to_ising source code diagonal offset QUBO coefficient duplicate upper triangular`
- `PyQUBO to_qubo to_ising offset spin binary conversion documentation diagonal QUBO`
- `OpenJij BinaryQuadraticModel from_qubo from_ising offset vartype documentation`
- `qubovert QUBO PUBO Ising conversion offset mapping x = (1+s)/2 documentation`
- `dimod qubo_to_ising GitHub source utilities.py D-Wave dimod`

Primary/reference sources consulted:

- D-Wave Ocean QUBO/Ising transformation docs:
  https://docs.dwavequantum.com/en/latest/quantum_research/qubo_ising.html
- D-Wave `dimod.utilities.qubo_to_ising` API docs:
  https://docs.dwavequantum.com/en/latest/ocean/api_ref_dimod/generated/dimod.utilities.qubo_to_ising.html
- PyQUBO model API:
  https://pyqubo.readthedocs.io/en/latest/reference/model.html
- PyQUBO getting-started conversion example:
  https://pyqubo.readthedocs.io/en/latest/getting_started.html
- OpenJij tutorial showing dimod-BQM interop:
  https://tutorial.openjij.org/en/tutorial/002-HuboSolver.html
- qubovert docs for Boolean/spin model mapping and value checks:
  https://qubovert.readthedocs.io

## Convention Decision

Decision: use the D-Wave/Ocean upper-triangular QUBO convention as the external
compatibility target:

- diagonal `(u, u)` QUBO entries are binary linear terms;
- off-diagonal `(u, v)` entries are pair terms counted once;
- reversed duplicate pair entries are summed before applying the upper-triangle formula;
- binary-to-spin mapping is `x_i = (s_i + 1) / 2`;
- every input and conversion offset is explicit and preserved in the IR and metadata.

Reasoning: D-Wave Ocean, dimod, and PyQUBO all expose QUBO as dict pair keys plus a
separate offset, and dimod is the de facto compatibility target for Python BQM tooling.
This also matches `reference/08-evaluation/equation-audit.md` EVAL-EQ-002/003.

Rejected alternatives:

- Dense symmetric matrix convention with `x^T Q x` double-counting off-diagonal entries.
  Rejected because it conflicts with the project equation audit and common Ocean/PyQUBO
  dict APIs.
- Silently dropping offsets during conversion. Rejected because benchmark witnesses and
  candidate energies must be recomputed from the true objective.
- Taking or vendoring dimod implementation code. Rejected to avoid a brittle dependency
  bridge and license/maintenance coupling. Instead, optional conformance tests compare
  directly against installed dimod.

## Scenario Matrix Added

New file: `test_suite/tests/test_conversion_scenarios.py`.

Active tests added:

1. D-Wave documented three-variable QUBO-to-Ising example: exact `h`, `J`, offset, and
   exhaustive energy equivalence.
2. Symmetric/reversed QUBO matrix entries: pair folding before conversion and exhaustive
   energy equivalence.
3. Structured QUBO with isolated variables and string pair keys.
4. Ising reversed-pair duplicate summing plus diagonal self-term folding into offset.
5. Duck-typed BINARY BQM conversion path, checked over all binary assignments.
6. Mixed hashable labels, including integer, string, and tuple labels.
7. Validation failures for duplicate variables, unknown variables, and unsupported vartype.
8. Non-finite numeric inputs (`NaN`, `+inf`, `-inf`) are rejected before IR storage.
9. Spin/binary helper round trip and invalid value checks.
10. SK spin-glass benchmark Ising fixtures compile and recompute witness ground energies.
11. Max-Cut benchmark fixtures lower to `J=+1` Ising edges and recompute witness cut/energy.

Optional dimod conformance tests added:

12. `compile_qubo` matches `dimod.qubo_to_ising`.
13. `compile_bqm` matches `dimod.BinaryQuadraticModel.from_qubo(...).energy(...)`.
14. `compile_bqm` matches SPIN `dimod.BinaryQuadraticModel.energy(...)`.
15. `IsingModel.to_dimod()` preserves spin energy over all assignments.
16. `SampleResult.to_dimod()` preserves sample-energy pairs and metadata. Dimod does not
    promise insertion-order preservation, so the test asserts the unordered row contract.

## Benchmark Coverage Statistics

Project benchmark corpus inspected:

- Total Tier A fixtures: 27.
- Families: Max-Cut, number partitioning, knapsack, TSP, SK spin glass.
- Conversion tests now directly touch all 3 SK spin-glass fixtures and all 14 Max-Cut
  fixtures through canonical Ising lowering.
- The full benchmark oracle remains responsible for number partitioning, knapsack, and TSP
  native objective witness checks.

## Environment And Artifacts

`.venv` initially had no `pip`. I ran:

```powershell
.\.venv\Scripts\python.exe -m ensurepip --upgrade
.\.venv\Scripts\python.exe -m pip install dimod
```

Installed into `.venv`:

- `dimod 0.12.21`
- `numpy 2.4.6`

Artifact checksum:

```text
Path: E:\projects\Gibbsiq\src\gibbsiq\model.py
SHA-256: 1523107FC0BB8D61CC21E78933027BA6317FDA17771A57B40CD0CBBC7AE701F0

Path: E:\projects\Gibbsiq\tests\test_conversion_scenarios.py
SHA-256: 379984D04D38BBF5119D2F32969F2AF2E6BEFA5130AF1C57C87AEF588C57A500
```

## Verification

Command:

```powershell
$env:PYTHONPATH = "src"; .\.venv\Scripts\python.exe -m unittest tests.test_conversion_scenarios
```

Result:

```text
Ran 16 tests in 0.245s
OK
```

Command:

```powershell
$env:PYTHONPATH = "src"; .\.venv\Scripts\python.exe -m unittest discover -s test_suite/tests
```

Result:

```text
Ran 71 tests in 1.043s
OK
```

Earlier non-venv run before installing dimod:

```text
Ran 68 tests in 0.936s
OK (skipped=3)
```

The 3 skips were the optional dimod conformance checks before dimod was installed.



