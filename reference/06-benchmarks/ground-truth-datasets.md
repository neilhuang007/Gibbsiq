# Ground-Truth Benchmark Datasets

This document catalogs optimization instances whose optimal answer is known, so that a
Gibbsiq solver run can be graded against the truth instead of against another heuristic's
guess. It is the source record required by the project rule in
`reference/08-evaluation/evaluation-framework.md` ("Non-Negotiable Failure Cases"), which
forbids using a "best known" value without citing where it came from.

A benchmark is only trustworthy as a pass/fail oracle if its optimum is *proven*, not merely
the best value anyone has found so far. Heuristic best-known records — large GSET Max-Cut
targets, for example — are moving competition numbers: a solver that beat one would be marked
as failing by a test harness that treated the record as ground truth. The datasets here are
therefore split by how strongly the optimum is established.

## Two tiers of ground truth

| Tier | What it is | How the optimum is established | Where it lives |
| --- | --- | --- | --- |
| A. Self-generated, brute-forced | Small instances solved by exhaustive enumeration | Proven by us, reproducible from a seed | `fixtures/ground-truth-small.json` (this repo) |
| B. External standard libraries | Community benchmark instances | Proven (small instances) or best-known heuristic (large) — stated per source | Download URLs below |

Tier A is the primary correctness oracle for v0: license-free, reproducible, and unambiguous.
Tier B supplies citable, recognized instances for scaling up once the solver works, but only
its proven-optimal subsets are safe as a pass/fail oracle; best-known values are competition
targets.

## Tier A — self-generated, brute-force-verified corpus

Generator: `tools/generate_ground_truth.py` (standard library only, deterministic).
Output: `reference/06-benchmarks/fixtures/ground-truth-small.json`.

For every instance the generator enumerates the entire solution space and records the proven
optimum, the exact degeneracy (the count of optimal states), and a sample of witness states
that attain it. Each fixture also carries provenance: the generator path, the method
(`exhaustive_enumeration`), the seed, and the model parameters. A SHA-256 content checksum
for the whole corpus is recorded in `research-journal/2026-05-31-ground-truth-test-set.md`.
Regenerate and verify with:

```powershell
python tools/generate_ground_truth.py --out reference/06-benchmarks/fixtures/ground-truth-small.json
```

Sizes are chosen to stay brute-forceable (`2^n` spin enumeration, or `(n-1)!/2` tour
enumeration). The families are:

| Family | Search space enumerated | What is proven | Notes |
| --- | --- | --- | --- |
| `maxcut` | `2^n` spin configs | max cut value, min Ising energy, degeneracy | seeded Erdos-Renyi, n = 8..14; invariant `E = |edges| - 2*cut` |
| `number_partition` | `2^n` sign vectors | min subset-sum difference (Lucas `H=(Sum a_i s_i)^2`) | includes perfect (optimum 0) and frustrated (optimum > 0, forced odd sum) instances |
| `knapsack` | `2^n` item subsets | max feasible value, weight at optimum, count | capacity = `floor(Sum weights / 2)` |
| `tsp` | `(n-1)!/2` tours | optimal tour length, count of optimal tours | rounded-Euclidean (TSPLIB EUC_2D style), n = 6..9 |
| `sk_spin_glass` | `2^n` spin configs | ground-state energy, degeneracy | Sherrington-Kirkpatrick, J in {-1,+1}, h = 0, n = 8..12 |
| `maxcut` (structured) | `2^n` spin configs, plus a closed-form cross-check | max cut value, degeneracy, witness | named graphs K_n, C_n, K_{m,n}, Q_3, Petersen |

The structured Max-Cut instances are the only fixtures whose optimum also has an independent
published value rather than just our own enumeration. Each is built from a closed-form
formula (`floor(n^2/4)`, `n` or `n-1`, `m*n`, `d*2^{d-1}`, `12`), and the generator raises if
exhaustive enumeration disagrees with the formula. They therefore serve a second purpose as
analytic regression checks on the enumerator itself. They reuse the `maxcut` family schema
and oracle, so no new verification code is needed.

Two structural facts are checked as sanity guards. Max-Cut and zero-field SK both have global
spin-flip symmetry, so their degeneracy is always even. Each fixture records a
`provenance.formulation_source` field citing the primary literature for its encoding
(Lucas 2014 for the NP-problem QUBO/Ising encodings; Sherrington-Kirkpatrick 1975 for the
spin glass) or for its closed-form optimum (Edwards 1973, West 2001, Diestel 2017, Harary
1969, Barahona 1983 for the named graphs). See References below.

These fixtures use the same schema as
`reference/08-evaluation/fixtures/exact-small-instances.json` (`id`, `purpose`, `input`,
`expected`).

### How a benchmark fixture is scored

Benchmark fixtures are scored by `src/gibbsiq/benchmark_oracle.py`, not by the generic
deep-compare used for the other fixture groups. A fixture passes only when all three of the
following hold:

1. The reported optimum value matches the proven value exactly (floats within `1e-9`).
2. The reported degeneracy matches the proven count of optimal states
   (`ground_state_degeneracy` / `num_optimal_selections` / `num_optimal_tours`).
3. Witness re-verification: the candidate supplies at least one witness state, and the oracle
   recomputes that witness's objective directly from the input model — cut value, Ising
   energy, tour length, knapsack value and feasibility, or partition discrepancy — and
   confirms it is feasible and attains the optimum.

The third check is the important one: the oracle never trusts a candidate's self-reported
numbers. Witnesses are re-checked against the fixture's proven optimum, so a solver cannot
pass by reporting a wrong optimum together with a self-consistent but wrong witness, and
cannot pass by reporting a correct number with no witness or a fabricated one. Required
candidate fields per family are the scalar keys plus the witness list
(`witness_spin_samples`, `witness_partitions`, `witness_selections`, `witness_tours`).
Coverage and anti-gaming behavior are pinned by `test_suite/tests/test_benchmark_oracle.py`.

### Wiring into the evaluator

The Tier A corpus is loaded by `src/gibbsiq/evaluation.py` as a third fixture group,
`benchmark`, alongside `exact` and `diagnostic`. `load_fixture_sets` loads
`ground-truth-small.json` automatically, so a default run scores against the benchmark
fixtures as well:

```powershell
$env:PYTHONPATH = "src"
python -m gibbsiq.evaluation <candidate>.json
```

A candidate emits one `actual` block per `gt_*` fixture id; see
`test_suite/examples/benchmark-candidate.example.json` for the exact shape.

## Tier B — external standard libraries

### Max-Cut and QUBO

BiqMac Library — the main source of proven-optimal small and medium instances.
- Library page: https://biqmac.aau.at/biqmaclib.html
- Optimal-value tables (PDF): https://biqmac.aau.at/biqmaclib.pdf
- Online exact solver (branch-and-bound plus SDP): https://biqmac.aau.at/
- Max-Cut families: `g05` (n=60/80/100, unweighted, density ~0.5), `pm1s`/`pm1d`
  (+/-1, sparse/dense), toroidal 2D/3D Ising grids, Ising chains.
- QUBO families: Beasley `bqp50/100/250/500`, GKA, Billionnet-Elloumi.
- Proven-optimal subset: small instances (g05_60/80/100, bqp50/100, GKA-small, t2g/t3g Ising
  grids). Larger instances may be best-known bounds — check the PDF.
- File format: `.sparse` edge-list `(i j value)` with `N M` header (same as GSET); `.mat`
  dense matrix for QUBO.
- Cite: Rendl, Rinaldi, Wiegele, "Solving max-cut to optimality...", *Math. Programming*
  121(2):307-335, 2010.

GSET (Stanford / Yinyu Ye) — large instances, heuristic best-known only.
- Graphs: http://web.stanford.edu/~yyye/yyye/Gset/
- 71 instances, 800-20,000 nodes. Format: `N M` header then `i j weight` lines.
- Not a correctness oracle: values are competition targets, still being improved (G63 was
  updated in Oct 2025). Best-known table: Benlic & Hao, *EAAI* 26(3):1162-1173, 2013 —
  https://leria-info.univ-angers.fr/~jinkao.hao/BLS_max_cut.html

OR-Library BQP (Beasley) — unconstrained binary quadratic.
- Index: https://people.brunel.ac.uk/~mastjjb/jeb/orlib/bqpinfo.html
- `bqp50..bqp2500`; coefficients integer in [-100, 100], maximization convention.
- Proven optima for bqp50/100 are recorded in the BiqMac PDF; larger are best-known.
- Auto-download helper: https://github.com/rliang/qubo-benchmark-instances

Closed-form Max-Cut families (no download, exact by formula).
- Complete graph K_n: maxcut = `floor(n^2/4)`. Cycle C_n: `n` (even) / `n-1` (odd).
  Path P_n: `floor(n/2)`. Useful as analytic regression checks.

### Spin glass

Spin Glass Server (U. Bonn, formerly U. Cologne) — exact 2D/3D lattice Edwards-Anderson.
- http://spinglass.uni-bonn.de/ (confirm availability before depending on it)
- Submit a lattice Ising instance, receive the proven exact ground-state energy and
  configuration. 2D planar without a field is polynomial-time exact via min-weight perfect
  matching; small 3D is handled by branch-and-cut.
- Method cite: Liers, Junger, Reinelt, Rinaldi, "Computing Exact Ground States of Hard Ising
  Spin Glass Problems by Branch-and-Cut."
- Caveat: targets lattice structure, not dense all-to-all SK graphs (use Tier A enumeration
  or BiqMac for those).

### TSP and QAP

TSPLIB (Reinelt, Heidelberg) — all instances solved to proven optimal.
- Main: http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/
- Optimal tour lengths: http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/STSP.html
- Format spec (the GEO/EUC_2D/ATT distance formulas are non-trivial): `tsp95.pdf` there.
- Smallest: burma14 (opt 3323), ulysses16 (6859), gr17 (2085).
- QUBO caveat: the Lucas one-hot encoding uses N^2 bits ((N-1)^2 after fixing one city), so
  even burma14 becomes 169 bits. For QUBO-scale tests, use Tier A synthetic TSP (n <= 9).
- Parser: `pip install tsplib95` (do not reimplement GEO rounding).
- Mirror with raw files: https://github.com/mastqe/tsplib
- Cite: Reinelt, *ORSA J. Computing* 3(4):376-384, 1991.

QAPLIB (Burkard, Karisch, Rendl) — quadratic assignment, proven optima for n up to ~16.
- COR@L mirror: https://coral.ise.lehigh.edu/data-sets/qaplib/
- Smallest proven-optimal (all marked `OPT`): Nug12 (578), Had12 (1652), Chr12a (9552),
  Tai12a (224416), Nug14 (1014), Nug15 (1150), Esc16* family, Had16 (3720).
- Format: `n`, then n*n flow matrix, then n*n distance matrix. Minimize
  `Sum F_ij * D_{pi(i)pi(j)}`. The one-hot QAP QUBO needs n^2 bits (144 at n=12).
- Cite: Burkard, Karisch, Rendl, *J. Global Optimization* 10:391-403, 1997.

### Synthetic with planted optima

Posiform Planting (arXiv:2308.05859) generates an arbitrary-size QUBO with a guaranteed-unique
known optimal solution (proven by construction), optionally matched to a hardware connectivity
graph. Useful for large-scale tests where enumeration is impossible but the true answer is
still needed.

## Theory reference (encodings, not data)

Andrew Lucas, "Ising formulations of many NP problems," *Frontiers in Physics* 2:5 (2014).
DOI 10.3389/fphy.2014.00005; arXiv:1302.5843 (open access). Local notes:
`reference/05-theory/papers/lucas-2014-ising-formulations.md`. This is the source of the
QUBO/Ising encodings for every Tier A family (Max-Cut, number partitioning section 2.1,
knapsack section 5.2, TSP section 7.2) and the penalty-weight conditions.

For constrained encodings (TSP, QAP, knapsack) the QUBO energy at the optimum depends on the
penalty weight A, so it is not a fixed citable number. Score these by decoding the solver
bitstring to a solution, checking feasibility, computing the native objective (tour length,
value), and comparing that to the known optimum. Lucas's condition is `0 < B*max(W_uv) < A`.
See arXiv:2206.11040 on penalty tuning.

## References

Primary sources for the Tier A formulations and closed-form optima. Each entry's short key
matches the `CITATIONS` map in `tools/generate_ground_truth.py`, which stamps it into every
fixture's `provenance.formulation_source`.

Formulations (NP-problem QUBO/Ising encodings):

- `[lucas2014]` Lucas, A. (2014). *Ising formulations of many NP problems.* Frontiers in
  Physics 2:5. DOI [10.3389/fphy.2014.00005](https://doi.org/10.3389/fphy.2014.00005);
  arXiv:1302.5843. Encodings for Max-Cut, number partitioning (section 2.1), knapsack
  (section 5.2), and TSP (section 7.2), plus the penalty-weight conditions.
- `[sk1975]` Sherrington, D. & Kirkpatrick, S. (1975). *Solvable Model of a Spin-Glass.*
  Phys. Rev. Lett. 35, 1792. DOI [10.1103/PhysRevLett.35.1792](https://doi.org/10.1103/PhysRevLett.35.1792).
  The all-to-all +/-1 spin-glass model used by the `sk_spin_glass` family.

Closed-form Max-Cut optima (named graphs):

- `[edwards1973]` Edwards, C. S. (1973). *Some extremal properties of bipartite subgraphs.*
  Canadian J. of Mathematics 25(3):475-485.
  DOI [10.4153/CJM-1973-048-x](https://doi.org/10.4153/CJM-1973-048-x).
  Complete graph K_n max-cut = `floor(n^2/4)`.
- `[west2001]` West, D. B. (2001). *Introduction to Graph Theory,* 2nd ed. Prentice Hall
  (cycle max-cut, p. 76). Cycle C_n max-cut = `n` (even) / `n-1` (odd).
- `[diestel2017]` Diestel, R. (2017). *Graph Theory,* 5th ed. Springer.
  DOI [10.1007/978-3-662-53622-3](https://doi.org/10.1007/978-3-662-53622-3).
  Complete bipartite K_{m,n} max-cut = `m*n` (the whole edge set, both sides cut).
- `[harary1969]` Harary, F. (1969). *Graph Theory.* Addison-Wesley (hypercube bipartiteness,
  ch. 13). Hypercube Q_d max-cut = `d*2^{d-1}`.
- `[barahona1983]` Barahona, F. (1983). *The max-cut problem on graphs not contractible to
  K5.* Operations Research Letters 2(3):107-111. DOI `10.1016/0167-6377(83)90016-0`.
  Petersen graph max-cut = 12.

Tier B external libraries (full provenance in the Tier B section above): Rendl, Rinaldi &
Wiegele (2010, BiqMac); Benlic & Hao (2013, GSET best-known); Beasley (OR-Library BQP);
Liers, Junger, Reinelt & Rinaldi (Spin Glass Server); Reinelt (1991, TSPLIB); Burkard,
Karisch & Rendl (1997, QAPLIB); Posiform Planting (arXiv:2308.05859).
