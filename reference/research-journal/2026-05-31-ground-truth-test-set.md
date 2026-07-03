# Ground-Truth Test Set: Construction, Verification, and Citation

**Date:** 2026-05-31
**Artifacts:**
- `tools/generate_ground_truth.py` — deterministic generator
- `reference/06-benchmarks/fixtures/ground-truth-small.json` — the corpus (27 fixtures)
- `src/gibbsiq/benchmark_oracle.py` — independent re-verification oracle
- `test_suite/tests/test_benchmark_oracle.py` — anti-gaming / coverage tests
- `test_suite/examples/benchmark-candidate.example.json` — reference candidate (all-pass)
- `reference/06-benchmarks/ground-truth-datasets.md` — dataset catalog + bibliography
- **Corpus content SHA-256:** `afb035eeeae7e0f8cff71846457ff750e14e3455fa72214efd63656f8a5f40fe`

---

## 1. Motivation

Every Gibbsiq result answers two questions about a run: what is the best solution,
and can the search that found it be trusted. Making either claim measurable
requires problems whose true optimum is known and independently verifiable.
Heuristic best-known values, such as large GSET Max-Cut targets, are moving
competition records; a solver that beats one would be failed by a harness that
treats the record as the optimum, so best-known values cannot serve as a pass/fail
oracle.

The test set therefore has one governing requirement: every fixture's optimum must
be provable by us, without trusting any external claim. For small instances
exhaustive enumeration furnishes that proof directly. This entry records how the
corpus was built, how the scoring oracle resists gaming, and how each fixture is
tied to primary literature for the eventual paper.

## 2. Two-tier design

Two tiers of ground truth are distinguished (full catalog in
`reference/06-benchmarks/ground-truth-datasets.md`):

- **Tier A — self-generated, brute-forced.** Small instances whose optimum,
  degeneracy, and witness states are computed by full enumeration: proven here,
  reproducible from a seed, and license-free. Tier A is the primary correctness
  oracle for v0 and the subject of this entry.
- **Tier B — external standard libraries.** BiqMac (proven-optimal small
  Max-Cut/QUBO), GSET (heuristic best-known only, which excludes it as an oracle),
  OR-Library BQP, the Spin Glass Server, TSPLIB, QAPLIB, and posiform-planted
  instances. Catalogued with download URLs and citations for scaling up later;
  only the proven-optimal subsets are safe as a pass/fail oracle.

Leading with Tier A is a deliberate choice: it removes every external dependency
and every ambiguity about whether a recorded number is proven or conjectured.

## 3. Families and how each optimum is proven

The generator (`tools/generate_ground_truth.py`, stdlib-only, deterministic)
emits five problem families. Sizes were chosen to stay brute-forceable
(2^n spin enumeration, or (n−1)!/2 tour enumeration).

| Family | Search space enumerated | What is proven | Encoding source |
| --- | --- | --- | --- |
| `maxcut` (Erdős–Rényi) | 2^n spin configs | max cut, min Ising energy, degeneracy | Lucas 2014 |
| `number_partition` | 2^n sign vectors | min subset-sum difference (`H=(Σ aᵢsᵢ)²`) | Lucas 2014 §2.1 |
| `knapsack` | 2^n item subsets | max feasible value + count | Lucas 2014 §5.2 |
| `tsp` | (n−1)!/2 tours | optimal tour length + count | Lucas 2014 §7.2 |
| `sk_spin_glass` | 2^n spin configs | ground-state energy + degeneracy | Sherrington–Kirkpatrick 1975 |
| `maxcut` (structured) | 2^n spin configs **+ closed-form cross-check** | max cut + degeneracy | named-graph theorems (§5) |

For every instance the generator records: the proven optimum, the exact degeneracy
(count of optimal states, always exact even when only a sample of witnesses is
serialized), up to `MAX_WITNESSES = 8` representative witness states, and a
`provenance` block (generator path, method, seed, model parameters, and a
`formulation_source` citation).

Design choices worth recording for the paper:

- Frustrated number-partition instances. Beyond perfect instances (optimum 0), the
  generator forces odd-sum instances whose optimum is provably greater than 0
  (`gt_partition_frustrated_*`, optima = 1). These separate an exact solver from a
  near-optimal one: a solver that always reports 0 passes the easy instances and
  fails these.
- Degeneracy-parity sanity check. Max-Cut and zero-field SK both have global
  spin-flip symmetry, so their ground-state degeneracy must be even. The corpus
  satisfies this for every relevant fixture (verifiable in the table in §6).
- Witness sampling versus exact count. The witness list is a representative sample
  (cap 8) and is never used to assert completeness; the degeneracy count is always
  the true total from enumeration. This keeps the artifact small while every claim
  stands.

## 4. Strict scoring and anti-gaming (the oracle)

The benchmark group uses a dedicated scorer, `src/gibbsiq/benchmark_oracle.py`, in
place of the generic deep-compare applied to the other fixture groups. A candidate
passes only when three conditions all hold:

1. Optimum value matches the proven value exactly (floats within `1e-9`).
2. Exact degeneracy matches the proven count of optimal states.
3. Witness re-verification — the candidate supplies at least one witness state, and
   the oracle recomputes that witness's objective directly from the input model
   (cut value / Ising energy / tour length / knapsack value+feasibility /
   partition discrepancy) and confirms it is feasible and attains the optimum.

The critical property is in step 3: the oracle recomputes every witness against the
fixture's proven optimum, using none of the candidate's self-reported numbers. A
solver therefore cannot pass by reporting a wrong optimum with a self-consistent
but wrong witness, and cannot pass by reporting a correct number with no witness or
a fabricated one.

This anti-gaming behaviour is pinned by `test_suite/tests/test_benchmark_oracle.py`
(9 stdlib `unittest` tests), which assert, among other properties, that a tampered
suboptimal TSP tour is rejected even when the reported length is correct; that an
over-capacity knapsack selection is rejected; that a number-partition witness
dropping a number is rejected; and that a wrong reported optimum still leaves a
genuinely optimal witness verifying, which shows the witness check is independent
of the reported scalar. One test asserts the corpus covers exactly the families the
oracle knows, so a new family cannot enter without a matching verifier.

## 5. Structured / named-graph Max-Cut additions (paper-cited optima)

The Erdős–Rényi Max-Cut instances are proven only by our own enumeration; no
published value exists for those specific random graphs. To obtain fixtures whose
optimum is also independently published, the corpus adds named graphs whose Max-Cut
value has a known closed form. Each is built from its formula, and the generator
raises `ValueError` when exhaustive enumeration disagrees with the closed form, so
each fixture carries a citable optimum and acts as an analytic regression check on
the enumerator itself.

| Graph | Closed form | Value | Citation |
| --- | --- | --- | --- |
| Complete Kₙ (n=4,5,6,7) | ⌊n²/4⌋ | 4, 6, 9, 12 | Edwards 1973 |
| Cycle C₆, C₇ | n (even) / n−1 (odd) | 6, 6 | West 2001 |
| Complete bipartite K_{3,3}, K_{2,4} | m·n | 9, 8 | Diestel 2017 |
| Hypercube Q₃ | d·2^{d−1} | 12 | Harary 1969 |
| Petersen | (special, max-cut = 12) | 12 | Barahona 1983 |

These reuse the existing `maxcut` family schema and `_verify_maxcut` oracle, so no
new verification code was required and the family-coverage test stays green. All
ten cross-checks passed at generation time (no `ValueError`), so each published
value is corroborated by our independent enumeration.

> Note on a discarded value: an intermediate research note claimed C₄ Max-Cut
> = 2. That is wrong (C₄ = 4). The cross-check would have raised on it; the correct
> formula `Cₙ = n (even) / n−1 (odd)` was used throughout. Recorded here so the
> error is not reintroduced.

## 6. The corpus as generated (27 fixtures)

Generated `2026-05-31`, checksum `afb035ee…f40fe`. `deg` = exact ground-state
degeneracy / number of optimal selections / number of optimal tours.

| Fixture id | Family | Optimum | deg |
| --- | --- | --- | --- |
| gt_maxcut_er_n8_p50_s1 | maxcut | cut = 12 | 14 |
| gt_maxcut_er_n10_p40_s2 | maxcut | cut = 12 | 24 |
| gt_maxcut_er_n12_p30_s3 | maxcut | cut = 14 | 4 |
| gt_maxcut_er_n14_p50_s4 | maxcut | cut = 33 | 4 |
| gt_partition_n10_v20_s5 | number_partition | diff = 0 | 24 |
| gt_partition_n12_v50_s6 | number_partition | diff = 0 | 20 |
| gt_partition_n14_v99_s7 | number_partition | diff = 0 | 70 |
| gt_partition_frustrated_n11_v30_s16 | number_partition | diff = 1 | 50 |
| gt_partition_frustrated_n13_v7_s17 | number_partition | diff = 1 | 724 |
| gt_knapsack_n10_s8 | knapsack | value = 96 | 1 |
| gt_knapsack_n14_s9 | knapsack | value = 205 | 1 |
| gt_tsp_n6_s10 | tsp | length = 177 | 1 |
| gt_tsp_n8_s11 | tsp | length = 223 | 1 |
| gt_tsp_n9_s12 | tsp | length = 217 | 1 |
| gt_sk_n8_s13 | sk_spin_glass | E₀ = −12 | 4 |
| gt_sk_n10_s14 | sk_spin_glass | E₀ = −21 | 2 |
| gt_sk_n12_s15 | sk_spin_glass | E₀ = −26 | 2 |
| gt_maxcut_complete_k4 | maxcut | cut = 4 | 6 |
| gt_maxcut_complete_k5 | maxcut | cut = 6 | 20 |
| gt_maxcut_complete_k6 | maxcut | cut = 9 | 20 |
| gt_maxcut_complete_k7 | maxcut | cut = 12 | 70 |
| gt_maxcut_cycle_c6 | maxcut | cut = 6 | 2 |
| gt_maxcut_cycle_c7 | maxcut | cut = 6 | 14 |
| gt_maxcut_bipartite_k33 | maxcut | cut = 9 | 2 |
| gt_maxcut_bipartite_k24 | maxcut | cut = 8 | 2 |
| gt_maxcut_hypercube_q3 | maxcut | cut = 12 | 2 |
| gt_maxcut_petersen | maxcut | cut = 12 | 10 |

Spot-checks against theory all agree: K₆ ⌊36/4⌋ = 9; K₇ ⌊49/4⌋ = 12; K_{3,3} 3·3 = 9;
K_{2,4} 2·4 = 8; Q₃ 3·2² = 12; C₆ = 6; C₇ = 6. Even degeneracy holds for
every Max-Cut and zero-field-SK fixture (the structured-graph degeneracies 6, 20,
20, 70, 2, 14, 2, 2, 2, 10 are all even).

## 7. Verification performed (this session)

1. Generation: `python tools/generate_ground_truth.py --out …` produced
   27 fixtures with no `ValueError`, so all ten structured closed-form cross-checks
   agreed with enumeration. Emitted checksum `afb035ee…f40fe`.
2. Unit tests: `python -m unittest discover -s test_suite/tests` → 9 tests, OK. The
   family-coverage test confirms the structured graphs slot into the existing
   `maxcut` family rather than introducing an unverified family.
3. End-to-end evaluation: the regenerated
   `test_suite/examples/benchmark-candidate.example.json` (built from each
   fixture's proven scalars plus one proven witness) scored 27/27 benchmark
   fixtures passing, 0 failed. The evaluator additionally reports the 8
   `exact`+`diagnostic` fixtures as "missing" because this example is
   benchmark-only by design, which does not indicate any benchmark failure.

## 8. Provenance and traceability

Each fixture carries `provenance.formulation_source`, a free-text citation stamped
from the `CITATIONS` map in the generator, so a reader of the corpus JSON can trace
any fixture to the paper that defines its encoding (Lucas 2014; Sherrington–
Kirkpatrick 1975) or its closed-form optimum (Edwards 1973, West 2001, Diestel
2017, Harary 1969, Barahona 1983). The full bibliography with DOIs lives in
`reference/06-benchmarks/ground-truth-datasets.md` → **References**. This satisfies
the project's "Non-Negotiable Failure Cases" rule that forbids using any value
without a recorded source: here the value is self-proven by enumeration and the
encoding / closed form is paper-cited.

## 9. Reproducing this artifact

```powershell
# regenerate the corpus (deterministic; prints the content checksum)
python tools/generate_ground_truth.py --out reference/06-benchmarks/fixtures/ground-truth-small.json

# verify the oracle + anti-gaming properties
python -m unittest discover -s test_suite/tests

# score the reference all-pass candidate
$env:PYTHONPATH = "src"
python -m gibbsiq.evaluation test_suite/examples/benchmark-candidate.example.json
```

Expected: 27 fixtures, checksum `afb035eeeae7e0f8cff71846457ff750e14e3455fa72214efd63656f8a5f40fe`,
9 tests OK, 27/27 benchmark fixtures passing.

## 10. Open items / next steps

- Tier B import path. When scaling beyond enumeration, import only the
  proven-optimal BiqMac / TSPLIB / QAPLIB subsets. Mind the sign convention:
  BiqMac/OR-Library state QUBO as maximization (e.g. gka1b = +133) while Gibbsiq
  minimizes, so any import must sign-flip and be re-checked against
  `reference/08-evaluation/equation-audit.md`.
- Constrained-encoding scoring. For TSP/QAP/knapsack the QUBO energy at the
  optimum depends on the penalty weight A and is therefore not a fixed citable
  number; score by decoding to a native solution and comparing the native
  objective (already what the oracle does).
- Posiform planting for large instances where enumeration is impossible but a
  unique optimum is guaranteed by construction.
