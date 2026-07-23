# TM-LWR-001 coordinator verification — 2026-07-23

Paper hook: supplies the checked reduction formulas, exact-arithmetic penalty boundaries,
finite-precision counterexample, anti-echo constrained-witness path, and reproducibility
record for the paper's bounded-lowering methods section.

## Context and hard-parts analysis

The fixed review point was pre-task commit `8e4b4a0`. Worker `/root/tm_lwr_001` implemented
the equation-first task; an independent gadget reviewer and `/root/tm_lwr_math_audit`
challenged the proofs. The coordinator then read the production code, tests, generator, and
raw outputs before running separate Standards and Spec reviews.

- **H1 — cubic sign and boundary.** Direct truth-table analysis confirmed
  `R(x,y,a) = xy - 2xa - 2ya + 3a` and `P >= abs(c)` for exact-arithmetic source-minimum
  equality. Strict `P > abs(c)` is required for a unique valid ancilla. The negative-`c`
  equality trap uses `(x,y,z) = (0,1,1)` with invalid `a = 1`.
- **H2 — knapsack lexicographic map and penalty.** With `R = C + 1`,
  `F = -R*V + W` implements maximum value then minimum weight on feasible selections.
  Removing at most `d = W-C` positive-integer-weight items proves
  `F(x') - F(x) <= d*M <= d^2*M`, where
  `M = max(0, max_i(R*v_i-w_i))`; therefore `P > M` separates every infeasible word.
  The `C=1`, `(w,v)=(2,2)`, `P=M=2` equality tie is retained.
- **H3 — TSP one-hot gap.** The two one-hot families have equal total bit count, so one
  nonzero integer discrepancy requires another; every invalid word has
  `H_one_hot >= 2`. A declared feasible tour of native length `U` therefore gives the strict
  exact-arithmetic certificate `P > B*U/2`.
- **H4 — native candidate semantics.** Penalized sampler energy is not a native knapsack or
  TSP objective. The bridge decodes every sample, rejects invalid words, and ranks remaining
  selections by native value/weight or tour length before the strict oracle recomputes each
  witness from fixture input.
- **H5 — numerical and evidence honesty.** Expanded binary64 arithmetic tied the cubic
  ancilla energies at `P = nextafter(2,+inf)`. Policies now expose
  `certificate_arithmetic="exact"` and
  `finite_precision_guarantee="not_universally_certified"` as structured metadata. Artifact
  generation stages a complete snapshot and publishes its manifest last, so an interrupted
  overwrite cannot leave a matching stale manifest.

## Choices and rejected alternatives

- Implemented one cubic monomial plus the current positive-integer knapsack and
  symmetric-TSP fixture contracts. A universal polynomial/constraint compiler was rejected
  because it has no proof or test envelope in this task.
- Used the sharper instance-derived knapsack boundary above. The larger
  `(C+1)*sum(values)` bound was rejected as safe but unnecessarily destructive to coefficient
  scale.
- Used a declared feasible TSP tour as the certificate upper bound. Calling it an optimal
  penalty or an automatic tuner was rejected.
- Kept equality/below-bound experiments caller-accessible and labelled them honestly rather
  than silently increasing caller penalties.
- Added typed relabeling, item/city permutation, redundant slack, alternative feasible
  witness, scale, offset, and immediately adjacent boundary cases. User-supplied redundant
  constraint lists are inapplicable to these fixed encoders; the TSP construction itself
  retains both one-hot families and their dependent total-cardinality relation. A general
  redundant-constraint mutation belongs to a future constraint-language task.
- During `$simplify`, reused the canonical sample validator, removed double decoder
  validation/native evaluation, cached repeated proof quantities, and centralized penalty
  metadata projection. A family-adapter registry, cross-task artifact framework, and shared
  lowering-construction module were rejected as broader abstractions that would make these
  bounded modules shallower.

## Current primary sources

Checked on 2026-07-23:

- Mandal et al., [Compressed Quadratization of Higher Order Binary Optimization
  Problems](https://arxiv.org/abs/2001.00658).
- Lucas, [Ising formulations of many NP
  problems](https://doi.org/10.3389/fphy.2014.00005), sections 5.2 and 7.2.
- Ayodele, [Penalty Weights in QUBO Formulations: Permutation
  Problems](https://arxiv.org/abs/2206.11040).
- D-Wave Ocean 9.4.0 / dimod 0.12.22,
  [`make_quadratic`](https://docs.dwavequantum.com/en/latest/ocean/api_ref_dimod/generated/dimod.make_quadratic.html)
  and
  [`cqm_to_bqm`](https://docs.dwavequantum.com/en/latest/ocean/api_ref_dimod/generated/dimod.cqm_to_bqm.html).
- Alessandroni et al., [Alleviating the quantum Big-M
  problem](https://doi.org/10.1038/s41534-025-01067-0) and [Scalable Determination of
  Penalization Weights](https://arxiv.org/abs/2604.02416).
- Doucet et al., [Thermodynamic significance of QUBO encoding on quantum
  annealers](https://doi.org/10.1088/1367-2630/ae6e98).

These sources motivate explicit strength and scale policies. The task's correctness claims
come from the local finite-state proofs and independent enumeration, not empirical or vendor
performance claims.

## Review and simplification record

- The coordinator corrected an equation-audit count: the Rosenberg expansion has one
  nonzero linear and at most four nonzero quadratic terms, not four total QUBO terms.
- Standards review found incomplete timing categories, direct live-directory artifact writes,
  and the need for an explicit hard-parts record. The generator now separates compile,
  native-oracle/bridge, sample, diagnostics, tuning, and wall timing; stages outputs; and
  publishes the manifest last. This entry supplies the hard-parts record.
- Spec review found the live metamorphic contract under-documented. Permanent regressions now
  cover exact typed relabeling, item/city permutations, redundant slack representations, and
  multiple native-optimal witnesses. Exhaustive artifacts already cover every tiny feasible
  slack word and every valid three-city tour.
- Four `$simplify` perspectives covered reuse, clarity, efficiency, and module altitude.
  Applied changes are listed above; no reviewer edited the worktree.

## Retained failures and negative results

- Red-first imports failed before `factor_lowering.py` and `constraints.py` existed.
- The first negative-cubic test used the wrong source word and failed; the proof identified
  and retained the correct counterexample.
- Treating a one-ULP strict cubic margin as an observed binary64 uniqueness case failed. The
  tie remains in `cubic-enumeration.json`; the positive numerical probe uses a declared
  `1e-6` sensitivity margin.
- Running the generator without `--overwrite` raised the intended `FileExistsError`.
- An optional temporary-directory determinism command was rejected before execution by the
  command-safety layer because it combined a computed path with recursive removal. No path
  was created. The replacement check re-generated the retained snapshot in place and proved
  all six substantive payload hashes byte-identical before and after.
- The full suite emitted the known non-fatal `arviz_stats` invalid-scalar-divide warning; all
  tests still passed.

## Raw evidence and provenance

The deterministic run is
`reference/00-roadmap/artifacts/tm-lwr-001/2026-07-23-lowering-contract/`.
`manifest.json` has SHA-256
`93baa759113b986ef7d846523faa487312592fa03f113c42f7b20bfd6baf858d`;
it records the exact path, byte count, and SHA-256 for all seven generated payloads.
`source-files.json` has SHA-256
`183de260a56365cfcdae528ebf477e9031dd5195d0cda9953671a3db960547f2`
and pins ten equation/source/test/generator files.

The four evidence payloads report `passed: true`. They contain six cubic coefficient/boundary
tables plus the one-ULP negative probe, exhaustive item/slack words for the recorded
knapsack cases, all 512 binary words per recorded three-city TSP case, and input-only
knapsack/TSP bridge candidates checked by the strict witness oracle. No RNG is used; the
recorded seed `20260723` is a fixed generator identifier. The reproduction command is
`python tools/generate_tm_lwr_001_artifacts.py --overwrite`.

Environment: CPython 3.13.5 on Windows 11, source base
`8e4b4a0081b9dc4cc3063fee81eae0875da13425`. Final recorded artifact timings in seconds are
compile `0.0368332`, native-oracle/bridge validation `0.1112105`, sample `0`, diagnostics
`0`, tuning `0`, and bounded wall clock `0.2657527`. `generation-config.json` defines the
timing boundaries; no sampling, solver tuning, or hardware claim is made.

## Final commands and results

All commands ran from `E:\projects\Gibbsiq` with `PYTHONPATH=src` where needed:

- Focused discovery: `test_factor_lowering.py` — 6 tests in 0.003 seconds;
  `test_constraints.py` — 9 in 0.055 seconds; `test_benchmark_bridge.py` — 27 in
  11.476 seconds; `test_public_api_thermomap.py` — 3 in 0.005 seconds. Total: 45 passed,
  zero skipped.
- Nearest model/conversion/oracle/corpus modules — 72 tests in 0.708 seconds, zero skipped.
- `python -m unittest discover -s test_suite/tests` — 668 tests in 93.507 seconds, zero
  skipped.
- `python tools/check_markdown_math.py` — passed.
- `ruff check .` — passed.
- `ruff format --check .` — 81 files already formatted.
- `mypy src/gibbsiq` — no issues in 27 source files.
- `git diff --check` — passed.
- Artifact generation, four gate checks, manifest/source independent rehashing, guarded
  no-overwrite failure, and byte-identical substantive-payload regeneration — passed.

## Completion and follow-up

`TM-LWR-001` satisfies its public, metamorphic, independent-oracle, artifact, review, and
recording gates in the commit containing this entry and the ledger transition. The next ready
tasks in roadmap edge order are `TM-CAT-001`, `TM-IMP-002`, `TM-VAL-001`, and newly unblocked
`TM-LWR-002`. None is claimed here.
