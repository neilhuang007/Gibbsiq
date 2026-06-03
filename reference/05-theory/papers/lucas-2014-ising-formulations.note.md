# Lab note — Ising formulations of many NP problems

> **Paper.** Andrew Lucas. "Ising formulations of many NP problems." *Frontiers in
> Physics* 2:5 (2014).
> DOI: [10.3389/fphy.2014.00005](https://doi.org/10.3389/fphy.2014.00005) ·
> BibTeX `lucas2014`.
> Transcript: [`lucas-2014-ising-formulations.md`](./lucas-2014-ising-formulations.md).

## What the paper does

The paper is a systematic catalog of Ising encodings for NP-complete and NP-hard
problems, covering all of Karp's 21 problems, each using a number of spins at most
cubic in the problem size. It works in the spin convention
$H(s_1,\ldots,s_N) = -\sum_{i<j} J_{ij} s_i s_j - \sum_i h_i s_i$ with $s_i = \pm 1$,
and freely switches to binary variables $x_a \equiv (s_a + 1)/2$. The recurring
recipe is to split the energy into a constraint penalty $H_A$ and an objective term
$H_B$, with the penalty weight chosen large enough ($A \gg B$) that the ground state
never violates a constraint to lower the objective — the paper derives an explicit
$A/B$ bound for each construction.

The four formulations Gibbsiq benchmarks all appear here. *Number partitioning* of a
set $\{n_i\}$ is the single term $H = A\left(\sum_i n_i s_i\right)^2$ (Eq. 6), whose
zero-energy ground states are equal-sum partitions. *Graph cuts* come from the
edge term $H_B = B\sum_{(uv)\in E}\tfrac{1 - s_u s_v}{2}$ (Eq. 9), which counts edges
crossing the partition; combined with the balance penalty
$H_A = A\left(\sum_i s_i\right)^2$ (Eq. 8) it is graph partitioning, and dropping the
balance constraint with $B<0$ gives unconstrained Max-Cut. *Knapsack* with integer
weights uses log-encoded slack variables $y_n$ to track the achieved weight,
penalizing weight-mismatch in $H_A$ (Eq. 49) and maximizing value via
$H_B = -B\sum_a c_a x_a$ (Eq. 50), at a cost of $N + \lceil 1 + \log W\rceil$ spins.
*TSP* places $N^2$ binary variables $x_{v,j}$ (vertex $v$ at tour position $j$),
reuses the Hamiltonian-cycle constraints for $H_A$, and adds the tour-length
objective $H_B = B\sum_{(uv)\in E}\sum_j W_{uv}\,x_{u,j}x_{v,j+1}$ (Eq. 57), with
$\max(W_{uv}) < A/B$.

## Why it matters to Gibbsiq

- **It is the canonical source for the benchmark corpus.** Gibbsiq's ground-truth
  fixtures (`reference/06-benchmarks/fixtures/ground-truth-small.json`) include
  Max-Cut, number partitioning, knapsack, and TSP instances; this paper supplies the
  exact $H_A/H_B$ formulations and the spin-count claims those families are built
  against, and `CLAUDE.md` names it the canonical reference for NP-problem Ising
  formulations.
- **The constraint/objective split drives penalty-weight handling at the interface
  layer.** Each formulation here is a penalty Hamiltonian with a derived $A/B$ ratio.
  When the interface/IR ingests such a problem it must fold those penalties (and any
  constant from expanding $(\cdots)^2$) into the IR so the offset is preserved through
  QUBO↔Ising conversion — dropping it is a hard evaluation failure.
- **The penalty structure is exactly what the diagnostics layer must surface.** Soft
  constraints encoded as energy penalties mean an infeasible state can still have low
  energy if $A/B$ is set wrong; Gibbsiq's feasibility check and failure flags exist to
  catch precisely the constraint-violation regime this paper bounds analytically.
- **Convention bridge.** The paper's spin energy uses leading minus signs
  ($-\sum J_{ij}s_is_j - \sum h_i s_i$); Gibbsiq's contract has no leading sign and is
  upper-triangle, no-double-count. Translating a Lucas formulation into Gibbsiq's IR
  requires flipping those signs consistently — the kind of step the equation audit
  guards.

## Reading-list hooks

- Benchmark families and the ground-truth dataset catalog →
  [`../../06-benchmarks/ground-truth-datasets.md`](../../06-benchmarks/ground-truth-datasets.md),
  [`../../06-benchmarks/benchmark-plan.md`](../../06-benchmarks/benchmark-plan.md).
- Penalty-weight and offset handling at the interface/IR → `CLAUDE.md`
  ("Canonical conventions"), audited in
  [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).
- p-bit / probabilistic-computing lineage that runs these formulations (incl. its TSP
  annealing demo) →
  [`./camsari-2018-probabilistic-spin-logic.note.md`](./camsari-2018-probabilistic-spin-logic.note.md).
