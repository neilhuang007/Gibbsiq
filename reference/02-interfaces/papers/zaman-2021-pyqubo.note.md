# Lab note — PyQUBO: mapping combinatorial problems to QUBO

> **Paper.** M. Zaman, K. Tanahashi, and S. Tanaka. "PyQUBO: Python Library for
> Mapping Combinatorial Optimization Problems to QUBO Form." arXiv preprint, 2021.
> arXiv:[2103.01708](https://arxiv.org/abs/2103.01708) · BibTeX `zaman2021`.
> Transcript: [`zaman-2021-pyqubo.md`](./zaman-2021-pyqubo.md).

## What the paper does

PyQUBO is a Python library for building the energy function (Hamiltonian) that an
Ising machine consumes, starting from the objective and constraints of a
combinatorial optimization problem. The user writes a Hamiltonian as composable
`Express` objects over `Binary` ($\{0,1\}$) and `Spin` ($\{-1,1\}$) variables,
calls `compile()` to produce a `Model`, and extracts the problem in two
interchangeable forms: `to_qubo()` returns the QUBO matrix plus an energy offset,
and `to_ising()` returns linear and quadratic dictionaries plus an offset. The two
forms are the standard pair — the QUBO cost
$H_{QUBO}(x)=\sum_{i\in V} a_i x_i + \sum_{(i,j)\in E} b_{ij} x_i x_j = x^{\mathsf T} Q x$
with $x_i\in\{0,1\}$, and the Ising energy
$H_{Ising}(s)=\sum_{i\in V} h_i s_i + \sum_{(i,j)\in E} J_{ij} s_i s_j$
with $s_i\in\{-1,1\}$ — which are equivalent "except for a constant value," i.e.
the offset the conversion must carry. Constraints enter by the penalty method,
$H = H_{cost} + \lambda H_{const}$, where $H_{const}$ is zero on feasible states and
positive otherwise.

Beyond the core, PyQUBO contributes the engineering pieces that make formulation
practical: a `Constraint` class whose satisfaction (and per-constraint energy) is
checked at decode time via `decode_sample()`; a `Placeholder` class that lets
penalty weights $\lambda$ be retuned through a `feed_dict` without recompiling;
integer encodings (`OneHotEncInteger`, `UnaryEncInteger`, `LogEncInteger`,
`OrderEncInteger`); and automatic order reduction that rewrites $k$-body terms
($k>2$) into quadratic form by introducing auxiliary variables and matching penalty
terms (e.g. $H=xyz \to az + \lambda D(a,x,y)$). Internally a Hamiltonian is an AST
that `expand()`s into a polynomial hash map keyed by sets of variables; the C++
backend using a sorted-array set representation reaches $O(n)$ expression and
compile time, beating the Python/SymPy $O(n^2)$ baselines.

## Why it matters to Gibbsiq

- **Same QUBO↔Ising contract, including the offset.** PyQUBO returns an explicit
  energy offset from both `to_qubo()` and `to_ising()`; Gibbsiq's interface/IR makes
  the identical promise — the offset is preserved through QUBO↔Ising conversion and
  reported in `best_energy` and metadata, and dropping it is a hard evaluation
  failure (`CLAUDE.md` → "Canonical conventions"). The paper's energy form matches
  Gibbsiq's $\sum_i h_i s_i + \sum_{i<j} J_{ij} s_i s_j$ up to the convention that
  Gibbsiq keeps quadratic terms upper-triangle only.
- **A reference front-end for the interface layer.** PyQUBO is precisely the kind of
  upstream problem builder Gibbsiq's layer 1 must ingest: it emits QUBO/Ising as
  key-value dictionaries compatible with the `dimod` BQM ecosystem Gibbsiq
  interoperates with, so a PyQUBO `Model` is a natural input to `compile_qubo`.
- **Penalty weights and order reduction inform IR handling.** The
  $\lambda H_{const}$ penalty discipline, `Placeholder`-based weight tuning, and
  automatic degree reduction are exactly the encoding concerns the interface/IR has
  to track (variable provenance, penalty strength, auxiliary variables) so that
  diagnostics later can report feasibility against the original constraints.
- **Constraint decoding parallels feasibility diagnostics.** PyQUBO's
  `constraints()` report (which penalties are broken, at what energy) is the
  upstream analogue of the feasibility signal Gibbsiq's diagnostics layer surfaces.

## Reading-list hooks

- QUBO/BQM ingestion API and offset-preserving conversion →
  [`../qubo-bqm-api.md`](../qubo-bqm-api.md).
- Sister QUBO toolkit (matrix-level manipulation) →
  [`./mucke-2025-qubolite.md`](./mucke-2025-qubolite.md).
- Canonical NP-problem Ising formulations behind PyQUBO's examples (number
  partitioning, knapsack, TSP, graph coloring) → Lucas 2014,
  [`../../05-theory/papers/lucas-2014-ising-formulations.md`](../../05-theory/papers/lucas-2014-ising-formulations.md).
- Energy convention and offset rule it must match → `CLAUDE.md` → "Canonical
  conventions," audited in
  [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).
