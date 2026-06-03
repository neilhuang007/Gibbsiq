# Lab note — QIS3, a Hybrid Quantum-Inspired QUBO Solver

> **Paper.** J. Yang, D. Wang, X. Zhao, H. Zhang, M. Gao, and L. Yang. "A Novel
> Solver for QUBO Problems: Performance Analysis and Comparative Study with
> State-of-the-Art Algorithms." TuringQ Co. Ltd., 2025.
> arXiv:[2506.04596](https://arxiv.org/abs/2506.04596) · BibTeX `turingq2025`.
> Transcript: [`turingq-2025-qis3-qubo-solver.md`](./turingq-2025-qis3-qubo-solver.md).

## What the paper does

The paper introduces QIS3, a quantum-inspired solver for the Quadratic
Unconstrained Binary Optimization problem $\min_{x \in \{0,1\}^n} x^{\mathsf T} Q x$,
where $Q \in \mathbb{R}^{n \times n}$ encodes pairwise interactions and exact
solution is NP-hard. QIS3 interleaves three paradigms inside one adaptive control
loop: branch-and-bound tree search for global pruning, gradient descent over a
continuous relaxation for local refinement, and quantum-annealing-style moves for
non-local escape from deep minima. Around this core it layers real-time control —
ensemble-weighted initial-solution seeding, state-adaptive intensification versus
diversification driven by measured curvature and barrier depth, and Bayesian
on-the-fly tuning of the annealing schedule, branch thresholds, and learning rates
— exposed as *nine distinct operating modes* with an automatic mode selector plus a
manual sweep workflow for expert users.

The empirical contribution is a uniform-runtime benchmark against eight competitors
(genetic algorithm, coherent Ising machine, simulated bifurcation, parallel
tempering, simulated annealing, the prior QIS2, D-Wave Neal, and Gurobi) on three
canonical classes. For Max-Cut on G-Set graphs the objective is the spin form
$\max_{x \in \{\pm 1\}^n} \tfrac12 \sum_{i<j} w_{ij}(1 - x_i x_j)$, mapped to QUBO
via $x_i = 2y_i - 1$ with $Q_{ij} = -w_{ij}$ plus linear offset terms. The other
classes are random Not-All-Equal 3-SAT at the critical ratio $m/n \approx 2.11$ and
the fully connected Sherrington-Kirkpatrick spin glass
$H(\sigma) = \tfrac{1}{\sqrt N}\sum_{i<j} J_{ij}\sigma_i\sigma_j$ with Gaussian
couplings. Under a 10 s (Max-Cut) or 1 s (3-SAT, SK) budget QIS3 attains optimality
on 15/16 Max-Cut instances (94%), achieves the best 3-SAT assignment at every scale
$\geq 700$ variables, and matches the Gurobi-certified SK ground states on all ten
seeds, taking an average Max-Cut rank of 1.06 versus Neal's 1.69.

## Why it matters to Gibbsiq

- **A baseline-layer competitor set, run under one budget.** The eight comparators
  here are exactly the baseline samplers Gibbsiq's benchmark layer must run under
  matched seeds and energy convention — simulated annealing, simulated bifurcation,
  parallel tempering, and especially D-Wave Neal. The paper's uniform-runtime
  protocol (fixed wall-clock budget, identical batch size and iteration count) is a
  concrete template for fair time-to-solution comparison against the THRML sampler.
- **The G-Set / 3-SAT / SK trio overlaps Gibbsiq's ground-truth corpus.** Max-Cut
  and SK spin glass are already among the proven-optimum families in
  `ground-truth-small.json`; this paper supplies published best-known values for the
  *large* G-Set instances (e.g. G72 at $n=10{,}000$) that exceed exhaustive
  enumeration, which is the "best-known with a recorded source" tier the benchmark
  contract requires.
- **The QUBO↔spin mapping is the interface-layer offset case.** The Max-Cut
  reduction $x_i = 2y_i - 1$ generates exactly the constant and linear offset terms
  Gibbsiq must preserve through QUBO↔Ising conversion; dropping them is a hard
  evaluation failure, so this is a clean worked instance of the conversion the IR
  has to get right.
- **Gurobi-certified SK ground states are an oracle cross-check.** Table 4's exact
  energies (e.g. seed 0 at $-218.9203$) are independent optimal values the strict
  benchmark oracle can re-verify a witness state against.

## Reading-list hooks

- Baseline samplers (SA / simulated bifurcation / Neal) under matched budgets →
  [`../baseline-solvers.md`](../baseline-solvers.md);
  simulated bifurcation in detail →
  [`./pawlowski-2026-simulated-bifurcation-annealing.md`](./pawlowski-2026-simulated-bifurcation-annealing.md),
  [`./tao-2026-tabu-simulated-bifurcation.md`](./tao-2026-tabu-simulated-bifurcation.md).
- G-Set / SK / Max-Cut benchmark families and the best-known-with-source rule →
  [`../../06-benchmarks/benchmark-plan.md`](../../06-benchmarks/benchmark-plan.md),
  [`../../06-benchmarks/ground-truth-datasets.md`](../../06-benchmarks/ground-truth-datasets.md).
- QUBO→Ising mapping and offset preservation → project energy contract
  (`CLAUDE.md` → "Canonical conventions"), audited in
  [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).
- NP-problem Ising formulations (Max-Cut, SK) used for benchmarks → Lucas 2014,
  [`../../05-theory/papers/lucas-2014-ising-formulations.md`](../../05-theory/papers/lucas-2014-ising-formulations.md).
