# Stage 01 Model Compatibility Research And Decisions

Date: 2026-06-01

## Question

Implement the first step of the Gibbsiq QUBO diagnostics tool, but first verify
whether Stage 1 is the right place to start.

## Local Repository Findings

Required orientation files read:

- `PROJECT_BRIEF.md`
- `AGENTS.md`
- `CLAUDE.md`
- `spec.md`
- `reference/README.md`
- `reference/08-evaluation/equation-audit.md`
- `reference/08-evaluation/evaluation-framework.md`
- `reference/08-evaluation/agentic-evaluation-research.md`
- `reference/06-benchmarks/ground-truth-datasets.md`
- `tools/generate_ground_truth.py`

The repository is currently a research/specification pack plus an evaluator, not
a solver implementation. The non-negotiable technical contracts are:

- internal Ising convention:
  `E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j`;
- spin values are `{-1, +1}`;
- QUBO conversion must preserve offset;
- Gibbs conditional must use
  `P(s_i = +1 | s_-i) = sigmoid(-2 * beta * gamma_i)`;
- benchmarks must be verified from witness states, not trusted scalar claims.

## Benchmarks Provided By This Project

The checked-in benchmark corpus is
`reference/06-benchmarks/fixtures/ground-truth-small.json`.

Statistics:

| Metric | Value |
| --- | ---: |
| Total benchmark fixtures | 27 |
| Corpus checksum | `afb035eeeae7e0f8cff71846457ff750e14e3455fa72214efd63656f8a5f40fe` |
| Families | 5 |
| Max-Cut fixtures | 14 |
| Number partition fixtures | 5 |
| Knapsack fixtures | 2 |
| TSP fixtures | 3 |
| SK spin glass fixtures | 3 |
| Exhaustive-enumeration fixtures | 17 |
| Closed-form plus enumeration cross-check fixtures | 10 |
| Maximum enumerated binary/spin variables | 14 |
| Maximum TSP city count | 9 |
| Maximum serialized witnesses per fixture | 8 |

The public benchmark families are:

- seeded Erdos-Renyi Max-Cut;
- named/structured Max-Cut graphs with closed-form optima;
- number partitioning, including frustrated nonzero optima;
- 0/1 knapsack;
- small rounded-Euclidean symmetric TSP;
- Sherrington-Kirkpatrick spin glass.

The strict oracle in `src/gibbsiq/benchmark_oracle.py` checks scalar optima,
degeneracy, and at least one independently recomputed witness. This is the right
anti-cheating shape for future agentic rewards.

## External Source And License Check

The user requested GitHub repository research and asked whether code should be
copied or imported as packages. I checked primary repositories through GitHub
metadata on 2026-06-01.

| Repository | License | Currentness | Reuse decision |
| --- | --- | --- | --- |
| `dwavesystems/dimod` | Apache-2.0 | pushed 2026-05-14 | Prefer optional import for BQM and SampleSet interop; do not copy. |
| `recruit-communications/pyqubo` | Apache-2.0 | pushed 2024-11-09 | Use API convention inspiration for compile/decode flow; do not copy. |
| `Jij-Inc/OpenJij` | Apache-2.0 | pushed 2026-03-17 | Later baseline adapter target; not needed for Stage 1. |
| `extropic-ai/thrml` | Apache-2.0 | pushed 2026-05-26 | Later runtime adapter target; not needed for Stage 1. |
| `usra-riacs/stochastic-benchmark` | Apache-2.0 | pushed 2026-05-27 | Later benchmark scorecard inspiration; not copied. |
| `fixstars/amplify-benchmark` | MIT | pushed 2023-10-08 | Later benchmark inspiration; not copied. |
| `rliang/qubo-benchmark-instances` | MIT | pushed 2021-08-17 | Later external fixture source after checksum/provenance review. |
| `arviz-devs/arviz` | Apache-2.0 | pushed 2026-04-24 | Later diagnostics reference for ESS/R-hat methods; not Stage 1. |

Local package availability check:

| Package | Installed locally |
| --- | --- |
| `dimod` | no |
| `pyqubo` | no |
| `openjij` | no |
| `thrml` | no |
| `arviz` | no |

Decision: no external implementation code was copied. The QUBO-to-Ising formulas
are already audited locally and are small enough to implement clean-room. Adding
hard runtime dependencies would also violate the current zero-dependency package
shape. The implementation therefore supports duck-typed dimod-style BQM objects
and uses optional imports only for `to_dimod()`.

## Why Stage 1 Is The Correct Starting Point

Stage 1 is the right first implementation step because every later layer depends
on the model target being exact:

1. A THRML sampler cannot be validated if the Ising coefficients or offsets are
   wrong.
2. Diagnostics are meaningless if they summarize samples from the wrong energy
   landscape.
3. Benchmarks cannot be compared fairly unless QUBO, Ising, and BQM inputs are
   normalized into one deterministic convention.
4. Hidden tests are expected to include variable-order, offset-shift,
   coefficient-scale, and symmetric-QUBO mutations, so a robust model layer is
   the natural first reward surface.

The implementation deliberately stops before solver logic. It creates the
interface and IR needed by later THRML, diagnostics, inspector, and baseline
layers.

## API Decisions

The user-facing Stage 1 API is:

```python
from gibbsiq import compile_bqm, compile_ising, compile_qubo

model = compile_qubo(Q)
energy = model.energy({"x0": 1, "x1": 0}, vartype="BINARY")

ising = compile_ising(h, J, offset=offset)
prob = ising.conditional_probability("x0", sample, beta=1.0)
```

Initial result schema:

```python
from gibbsiq import SampleResult

result = SampleResult.from_model(model, samples, vartype="BINARY")
result.best_sample
result.best_energy
result.to_dict()
```

Design choices:

- Keep `IsingModel` as the sole internal IR.
- Keep conversion functions in `conversions.py`, model math in `model.py`, and
  result schema in `result.py`.
- Preserve explicit variable order when supplied; otherwise sort mixed labels
  deterministically by type and `repr`.
- Accept fixture-style QUBO objects and flat `{(u, v): coefficient}` QUBO maps.
- Treat diagonal QUBO entries as binary linear terms.
- Sum symmetric duplicate QUBO pair entries before conversion so energy is
  preserved for users who supply both `(i, j)` and `(j, i)`.
- Fold Ising diagonal terms into offset because `s_i^2 = 1`.
- Provide optional dimod export without making dimod a required dependency.

## Implementation Statistics

New implementation files:

| File | Lines |
| --- | ---: |
| `src/gibbsiq/model.py` | 138 |
| `src/gibbsiq/conversions.py` | 268 |
| `src/gibbsiq/result.py` | 113 |
| `test_suite/tests/test_model_compatibility.py` | 138 |

New focused tests: 7.

Coverage intent:

- exact public QUBO conversion fixture;
- binary/spin energy equivalence;
- symmetric duplicate QUBO normalization;
- structured diagonal QUBO handling;
- deterministic Ising variable ordering;
- Ising diagonal offset folding;
- audited Gibbs conditional sign;
- duck-typed BQM compatibility;
- initial `SampleResult` schema and best-sample computation.

## Open Follow-Ups

- Add optional dependency groups in `pyproject.toml` only when the project is
  ready to run integration tests for dimod/OpenJij/THRML.
- Add exhaustive hidden-style metamorphic tests for variable relabeling,
  offset shifts, and spin-gauge transforms.
- Add `to_qubo()` once a reverse conversion is needed by baseline adapters.
- Add a real dimod integration test in an optional test environment.

