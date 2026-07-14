# 2026-07-04 - Porting dimod contract cases into the Gibbsiq test suite

## Paper Hook

Feeds the evaluation-methods section: it records how Gibbsiq imports the reference
QUBO / Ising / BQM contracts from the library it interoperates with (dimod) as
dependency-free tests, and how the port doubles as documentation of the places
where Gibbsiq deliberately diverges from dimod's semantics.

## Context

`test_suite/vendor/dimod/tests/` holds the upstream dimod suite verbatim (commit
`bad4cba`, per `test_suite/vendor/README.md`), copied as cross-validation reference
and excluded from Gibbsiq's own run. `test_suite/tests/test_conversion_scenarios.py`
already exercises dimod parity two ways: it ports the documented QUBO->Ising example
and symmetric-pair folding as literals, and it carries a `DimodConformanceTest` class
that cross-checks `compile_qubo` / `compile_bqm` / `to_dimod` against a live dimod
install, skipped with `@unittest.skipUnless(HAS_DIMOD, ...)` when dimod is absent.

The task was to take dimod's concrete input->expected-output numeric cases and add
them to Gibbsiq's own suite. The core package carries zero required runtime
dependencies, so the port has to run in the zero-dependency core, which the
dimod-gated conformance class does not.

## Hard-Parts Analysis

- **H1 - Separating additive cases from duplication.** dimod's `tests/` tree is
  large and most of it tests dimod, not Gibbsiq: DQM / CQM, samplers, serialization,
  record arrays, and integer/real vartypes have no Gibbsiq equivalent, and
  `test_vartypes.py` only checks dimod enum identity and pickle round-trips. The
  cases worth porting are the ones that pin a contract Gibbsiq mirrors in `model.py`,
  `conversions.py`, and `result.py`, and that are not already covered in
  `test_conversion_scenarios.py`. The added value narrows to two kinds: dependency-
  free literal pins that run without dimod installed, and convention divergences that
  dimod's own suite cannot express because dimod lacks Gibbsiq's contracts.

- **H2 - Binary cases assert observable energy, spin cases assert coefficients.**
  `compile_qubo` returns a SPIN `IsingModel` energy-equivalent to the input QUBO under
  $x_i = (s_i + 1) / 2$, so `model.linear` after a binary conversion holds transformed
  spin fields, not the binary linear coefficients. A binary contract like "diagonal
  term becomes a linear coefficient" is therefore verified through
  `energy(sample, vartype="BINARY")`, the observable quantity, and not by reading the
  internal dict. `compile_ising` is an identity on the SPIN IR, so spin cases can and
  do assert `model.offset` / `model.linear` / `model.quadratic` directly.

- **H3 - The all-ones matrix exercises three conventions at once.** dimod's dense
  `ones((5,5))` cases fold the diagonal, sum both off-diagonal triangles, and apply
  the self-loop identity in one construction. Reproducing them with a coupling dict
  that carries both `(i,j)` and `(j,i)` plus every `(i,i)` confirms that
  `compile_ising` sums duplicate pairs to a coefficient of 2 and folds each diagonal
  self-term into the offset because $s_i^2 = 1$, matching dimod's matrix semantics.
  The binary counterpart confirms $x_i^2 = x_i$ routes a QUBO self-loop to the linear
  coefficient.

- **H4 - The divergences are the payload.** dimod permits a zero-sample `SampleSet`
  and its `.first` relies on an unstable argsort, so the winner among exactly-tied
  energies is unspecified. Gibbsiq rejects an empty result at construction, guarantees
  the first occurrence of the minimum on degenerate optima, and defaults `vartype` to
  SPIN. Pinning these three as their own class turns a future regression into a test
  failure rather than a silent semantic drift.

## Decisions

- We add a new module, `test_suite/tests/test_dimod_ported_contracts.py` (18 tests),
  rather than extending `test_conversion_scenarios.py`. The new module hardcodes
  expected literals and imports no dimod, so it runs in the zero-dependency core; the
  dimod-gated conformance class stays where it is. Every test carries a `file:line`
  provenance comment back to the dimod source so a reader can re-derive the literal.

- Binary conversion cases assert `energy(sample, vartype="BINARY")` at specific
  assignments; spin conversion cases assert the IR coefficients directly (H2).

- We port the energy literals not already covered (asymmetric spin fields
  `[-0.9, 0.7, 1.3, -1.1]`, binary-with-offset all-assignment tables, the single-spin
  `x -> 2x - 1` energy pair), the convention-sensitive diagonal / duplicate-pair /
  offset-preservation cases, the lowest-energy selection case, and the three
  divergence cases. We skip the spin<->binary helper round-trips and the documented
  QUBO->Ising example, which `test_conversion_scenarios.py` already pins.

## Rejected Alternatives

- **Porting the whole dimod `tests/` tree.** DQM / CQM, samplers, serialization,
  record arrays, and integer/real vartypes have no Gibbsiq surface; `test_vartypes.py`
  asserts only dimod enum identity and pickle. Porting them would test dimod inside
  Gibbsiq's suite and add maintenance with no coverage of a Gibbsiq contract.

- **Importing dimod and asserting against live dimod output.** `DimodConformanceTest`
  already does this and skips without dimod. Duplicating it adds a dependency gate
  and no new coverage; the point of this port is to run in the zero-dependency core.

- **Asserting internal spin coefficients for binary inputs.** That encodes the
  post-conversion representation instead of the observable energy contract, and would
  break on any internal change to the QUBO->Ising splash even when energies stay
  correct.

## Sources Read / Examples Used

- dimod commit `bad4cba` (Apache-2.0), `test_suite/vendor/README.md` provenance table.
  Ported cases cite: `test_bqm.py` lines 346-352, 364-368, 372-379, 383-390, 394-402,
  1062-1070, 1113-1118, 1122-1127, 1166-1169, 1191-1199, 1440-1460, 2509, 2527;
  `test_quadratic_model.py` lines 338-339; `test_sampleset.py` lines 981-989 plus its
  empty-set and `.first` behavior.
- Existing coverage the port complements: `test_suite/tests/test_conversion_scenarios.py`
  (`DimodConformanceTest`, documented QUBO->Ising example, symmetric-pair folding).
- Canonical contracts pinned: `CLAUDE.md` -> "Canonical conventions";
  `reference/08-evaluation/equation-audit.md`.

## Follow-Up / Open Items

- The arviz diagnostics port (extracting `arviz-stats/tests/base/test_diagnostics.py`
  R-hat / ESS cases into dependency-free Gibbsiq assertions) is the natural next
  parallel to this dimod port; it complements the existing
  `test_diagnostics_arviz_crosscheck.py`, which is arviz-gated.

## Verification

- `python -m unittest discover -s test_suite/tests -p "test_dimod_ported_contracts.py" -v`
  -> Ran 18 tests, OK. All ported literals match Gibbsiq's behavior on the first run;
  no Gibbsiq code changed.
- `python -m unittest discover -s test_suite/tests` -> Ran 291 tests with one failure:
  `test_parallel_tempering_records_swap_and_per_beta_traces` asserts
  `swap_attempts == 5` and observes 3, deterministic across repeated runs. The test
  originates in commit `41572d3` ("Add parallel tempering and cached Ising
  evaluation"), which landed after this session began; it is unrelated to this
  additive test module and belongs to the open Stage 2 parallel-tempering work
  (`gotchas-and-todo.md` -> "Open TODOs"). This entry records the observation without
  changing that code.
