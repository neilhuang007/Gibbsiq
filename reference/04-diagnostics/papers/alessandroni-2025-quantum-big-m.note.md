# Lab note — Alleviating the quantum Big-$M$ problem

> **Paper.** E. Alessandroni, S. Ramos-Calderer, I. Roth, E. Traversi, and L. Aolita.
> "Alleviating the quantum Big-$M$ problem." *npj Quantum Information* 11(1):125 (2025).
> DOI: [10.1038/s41534-025-01067-0](https://doi.org/10.1038/s41534-025-01067-0) · BibTeX `alessandroni2025bigm`.
> Transcript: [`alessandroni-2025-quantum-big-m.md`](./alessandroni-2025-quantum-big-m.md).

## What the paper does

The paper formalizes the *quantum Big-$M$ problem*: when a linearly-constrained binary
quadratic optimization $\min_{\mathbf{x}\in\{0,1\}^n} \mathbf{x}^t Q\mathbf{x}$ subject to
$A\mathbf{x}=\mathbf{b}$ is converted to a QUBO by adding a quadratic penalty,
$\min_{\mathbf{x}} \mathbf{x}^t Q\mathbf{x} + M(A\mathbf{x}-\mathbf{b})^2$, the weight $M$
must be large enough that every infeasible point is lifted above the feasible optimum (an
*exact reformulation*, with a gap $\delta>0$ satisfying
$f(\mathbf{x}^*)+\delta \le f(\mathbf{x}) + M(A\mathbf{x}-\mathbf{b})^2$), yet an overlarge
$M$ degrades the solver. The authors prove that finding the optimal (minimal) $M$ is
NP-hard, via a reduction of the threshold-decision problem `decideF` to `decidePM`. The
common polynomial-time recipe $M_{\ell_1}=\|Q\|_{\ell_1}+\delta$ is exact but wildly
over-estimates. Their alternative (Observation 2) sets $M=f(\mathbf{x}_{\text{feas}})-f_{\text{unc}}+\delta$,
where $f_{\text{unc}}$ is a lower bound on the unconstrained objective obtained from an SDP
relaxation and $\mathbf{x}_{\text{feas}}$ is any feasible point from a time-boxed classical
solver; this yields $M_{\text{SDP}}$.

The penalty weight is then tied to the solver's runtime through the *normalized spectral
gap* of the encoding Ising Hamiltonian $H_M = H_f + M H_c$,

$$\Delta_M := \frac{E_1 - E_0}{E_{\max} - E_0},$$

and Observation 3 shows that for any exact reformulation $E_0=f(\mathbf{x}^*)$,
$\Delta_M \le \Delta_0$, and asymptotically $\Delta_M = \mathcal{O}(\Delta_0/M)$ — a smaller
$M$ buys a wider gap, hence shorter time-to-solution. On random sparse LCBOs, set
partitioning, and S&P 500 portfolio optimization, $M_{\text{SDP}}$ is roughly an order of
magnitude below $M_{\ell_1}$ and $\Delta$ one-to-two orders larger; a 6-qubit IonQ trapped-ion
experiment raises the probability of measuring the optimum by over an order of magnitude.

## Why it matters to Gibbsiq

- **Penalty/offset handling in the interface layer.** Gibbsiq's IR ingests constrained
  problems by lifting constraints into the Ising energy
  $E(s) = \text{offset} + \sum_i h_i s_i + \sum_{i<j} J_{ij} s_i s_j$; the choice of penalty
  weight $M$ is exactly what sets the relative magnitudes of those $h$/$J$ entries (and the
  preserved `offset`). This paper is the canonical argument that the weight is not a free
  knob: too small breaks exactness, too large flattens the landscape.
- **$M$ is a sampler-health lever, not just a formulation detail.** The
  $\Delta_M = \mathcal{O}(\Delta_0/M)$ result says an inflated penalty shrinks the energy gap
  between the optimum and its competitors — the same mechanism that, for a block-Gibbs
  sampler, drives slow mixing, long autocorrelation, low ESS, and `mode_collapse` onto
  infeasible-but-low-penalty basins. The diagnostics layer should treat a near-degenerate
  feasible/infeasible gap as a flaggable formulation smell, not silently report poor mixing.
- **Feasibility checking is shared contract.** The exactness condition (Eq. 1) is precisely
  what the benchmark oracle re-verifies when it recomputes a witness state's objective and
  feasibility from the input model rather than trusting reported numbers.
- **SDP-precomputed $M$ as a baseline preprocessor.** "Classical solvers pre-condition the
  problem for the quantum/quantum-inspired backend" maps onto Gibbsiq's pipeline: compute
  $M_{\text{SDP}}$ once at compile time, then sample — and benchmark it against the naive
  $M_{\ell_1}$ encoding under the same seeds.

## Reading-list hooks

- Penalty/offset convention and feasibility re-verification → `CLAUDE.md`
  ("Canonical conventions", "Evaluation harness"), audited in
  [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).
- Companion penalty-weighting work by the same group →
  [`./alessandroni-2026-penalization-weights.md`](./alessandroni-2026-penalization-weights.md).
- QUBO-encoding thermodynamics and gap effects →
  [`./doucet-2026-qubo-encoding-thermodynamics.md`](./doucet-2026-qubo-encoding-thermodynamics.md).
- QUBO translation tooling that this $M$-recipe would slot into →
  [`../../02-interfaces/papers/zaman-2021-pyqubo.md`](../../02-interfaces/papers/zaman-2021-pyqubo.md),
  [`../../02-interfaces/papers/mucke-2025-qubolite.md`](../../02-interfaces/papers/mucke-2025-qubolite.md).
- NP-problem Ising formulations whose penalties motivate this analysis (TSP, set
  partitioning, knapsack) → Lucas 2014,
  [`../../05-theory/papers/lucas-2014-ising-formulations.md`](../../05-theory/papers/lucas-2014-ising-formulations.md).
