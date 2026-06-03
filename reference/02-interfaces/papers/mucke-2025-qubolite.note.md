# Lab note — qubolite: a lightweight Python toolkit for QUBO

> **Paper.** S. Mücke, T. Gerlach, N. Piatkowski, and L. Theißinger. "qubolite: A
> lightweight Python toolkit for QUBO." arXiv preprint, 2025.
> arXiv:[2509.21321](https://arxiv.org/abs/2509.21321) · BibTeX `mucke2025`.
> Transcript: [`mucke-2025-qubolite.md`](./mucke-2025-qubolite.md).

## What the paper does

The paper presents *qubolite*, a Python package for creating, manipulating,
analyzing, and solving Quadratic Unconstrained Binary Optimization (QUBO)
instances. It is a thin wrapper around NumPy: the central `qubo` class holds a
weight matrix $Q \in \mathbb{R}^{n \times n}$ and treats it as the unique
characterization of the problem of minimizing the energy
$E_Q(z) = z^{\mathsf T} Q z$ over $z \in \{0,1\}^n$. By design the package does
*not* help formulate QUBOs from higher-level constraints; it focuses on operating
on existing instances. The matrix is always stored in upper-triangular form,
converting any off-triangle input via $Q_{ij} \to Q_{ij} + Q_{ji}$ for $i<j$
(diagonal kept, lower triangle zeroed), with the symmetric form recovered as
$Q_{\text{sym}} = (Q_m + Q_m^{\mathsf T})/2$. Beyond vectorized energy evaluation
it exposes discrete first/second derivatives (the energy change from flipping one
or two bits) and a probabilistic view: every QUBO is a Gibbs/Boltzmann
distribution
$$P(x; Q, \beta) = \frac{1}{Z_{Q,\beta}}\,e^{-\beta E_Q(x)}, \qquad
Z_{Q,\beta} = \sum_{x \in \{0,1\}^n} e^{-\beta E_Q(x)},$$
with inverse temperature $\beta>0$ and a partition function whose exact
computation is #P-complete, so partition-function, pairwise-marginal, and
full-probability routines are feasible only for small $n$.

The package's preprocessing layer is its distinctive contribution. It implements
*partial assignments* (clamping) that fix or tie variables and shrink an instance,
returning a smaller QUBO plus a constant offset that recovers the original energy;
an implementation of Glover et al.'s QPRO+ algorithm for detecting strong
persistencies (provably optimal variable values and same/opposite pairs); and a
dynamic-range reduction heuristic. Dynamic range,
$\text{DR}(Q) = \log_2\!\big(\max D(Q)/\min D(Q)\big)$ over the set of distinct
pairwise weight differences $D(Q)$, governs solution quality on finite-precision
annealers, and the heuristic lowers it while preserving optima. Solving is
secondary: simulated annealing and local search, plus a fast parallel C
brute-force solver using Gray codes that is exact below roughly 30 variables.

## Why it matters to Gibbsiq

- **It is a reference design for Gibbsiq's interface/IR layer.** qubolite's
  insistence on the weight matrix as the canonical object, with strict
  upper-triangular storage and no double-counting, mirrors Gibbsiq's energy
  convention `E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j` and the
  upper-triangle-only rule for quadratic terms — the same normalization, on the
  spin side.
- **Clamping with a recovered constant is exactly the offset-preservation
  contract.** `partial_assignment.apply` returns a reduced instance plus a constant
  that re-creates the full energy; Gibbsiq's hard requirement that the offset
  survive QUBO↔Ising conversion and reappear in `best_energy`/metadata is the same
  discipline, and qubolite's `to_ising()` (returning `h, J, const`) is a concrete
  conversion to validate Gibbsiq's against.
- **The Gibbs/Boltzmann framing is the sampling target Gibbsiq's THRML runtime
  approximates.** qubolite computes $P(x;Q,\beta)$, marginals, and $Z$ exactly only
  for tiny $n$ — precisely the regime where Gibbsiq's exact/brute-force oracle
  applies; for larger instances Gibbsiq's block-Gibbs sampler estimates the same
  distribution, and qubolite's small-$n$ probabilities and Gray-code brute force are
  a natural cross-check for the benchmark oracle.
- **Dynamic-range and discrete-derivative tooling informs diagnostics.** The
  per-bit energy changes ($\partial E/\partial x$) are the local moves a sampler
  makes, and dynamic range is a precision-health signal of the kind Gibbsiq's
  diagnostics layer reports.

## Reading-list hooks

- Interface/IR ingestion, offset-preserving QUBO↔Ising conversion, upper-triangle
  convention → `CLAUDE.md` → "Canonical conventions" and "Architecture (layer 1)".
- Exact small-instance probabilities and Gray-code brute force → Gibbsiq benchmark
  oracle and exact fixtures, [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).
- Companion QUBO/BQM interface tooling →
  [`./zaman-2021-pyqubo.md`](./zaman-2021-pyqubo.md).
- NP-problem Ising/QUBO formulations that produce such instances → Lucas 2014,
  [`../../05-theory/papers/lucas-2014-ising-formulations.md`](../../05-theory/papers/lucas-2014-ising-formulations.md).
