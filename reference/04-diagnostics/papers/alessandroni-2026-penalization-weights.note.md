# Lab note — Scalable Penalization Weights for Approximate Solvers

> **Paper.** E. Alessandroni, S. Ramos-Calderer, M. Krispin, F. Schinkel, S. Walter,
> M. Kliesch, L. Aolita, and I. Roth. "Scalable Determination of Penalization Weights
> for Constrained Optimizations on Approximate Solvers." arXiv preprint, 2026.
> arXiv:[2604.02416](https://arxiv.org/abs/2604.02416) · BibTeX `alessandroni2026weights`.
> Transcript: [`alessandroni-2026-penalization-weights.md`](./alessandroni-2026-penalization-weights.md).

## What the paper does

The paper attacks the *big-$M$ problem*: when a linearly constrained binary optimization
$\min_{\mathbf{x}} \mathbf{x}^t Q \mathbf{x}$ subject to $A\mathbf{x} = \mathbf{b}$ is turned
into a QUBO by adding a penalty $M(A\mathbf{x}-\mathbf{b})^2$, the weight $M$ governs the
energy landscape. Too large and the low-energy spectrum becomes uninformative (feasible but
far from optimal); too small and infeasible states sink below the feasible optimum. Classical
big-$M$ prescriptions are tuned for *exact* solvers and grossly overestimate the required
penalty — by orders of magnitude on the authors' instances — which degrades the output of the
*approximate* solvers actually used in practice. The key move is to model an approximate solver
as a Gibbs sampler at known inverse temperature $\beta$, with output $p(\mathbf{x}) \propto
e^{-\beta E(\mathbf{x})}$, so the whole degree-of-approximation collapses into one parameter.

The contribution is a precomputation algorithm with a provable guarantee: it returns an $M$ for
which the sampler draws a feasible solution of objective at most $E_f$ with probability at least
$\eta$ (Definition 1, $\Pr[\{x\in\mathcal{F} \mid E(x) \leq E_f\}] \geq \eta$). It does so by
bounding three mutually exclusive events — low-objective feasible, high-objective feasible, and
infeasible — using a penalization degeneracy $n_{\text{pen}}(v)$, feasible spectral weights
$n_\Delta(e)$ estimated by uniform sampling over $\mathcal{F}$, and an SDP objective lower bound
$E_{\text{LB}}$. The weight is the root of
$$g(M) = B_{\overline{\mathcal{F}}}(M) + B^{>}_{\mathcal{F}} - \tfrac{1-\eta}{\eta}B^{<}_{\mathcal{F}},$$
which is proven correct (Theorem 2) and robust to finite samples ($N_s \geq 2/(\epsilon\delta)^2$
gives an $(\eta-\epsilon)$-reformulation, Theorem 4), running in $\mathrm{poly}(n)$ for TSP, MNPP,
and portfolio optimization. Experiments on ideal Gibbs, simulated annealing, and Fujitsu's Digital
Annealer (up to ~4098 bits) show $\eta_{\text{eff}} \geq \eta$ and order-of-magnitude
time-to-solution speedups over binary search seeded from the direct bound
$M_{\ell_1}(\beta) = \beta^{-1}(n\ln 2 - \ln(1-\eta)) + \|Q\|_{\ell_1}$.

## Why it matters to Gibbsiq

- **It is a feasibility-diagnostic and penalty-setting tool for the interface/IR layer.**
  Gibbsiq ingests constrained problems by promoting constraints to penalty terms folded into
  `linear`/`quadratic`/`offset`; this paper says how to *choose* the penalty weight a priori
  rather than guessing. The $\eta$-reformulation guarantee is exactly the kind of feasibility
  contract layer 3 measures after sampling (feasibility fraction, feasibility flags).
- **Its solver model is the Gibbsiq runtime model.** The paper's solver is a Gibbs sampler at
  inverse temperature $\beta$ with $p(\mathbf{x}) \propto e^{-\beta E(\mathbf{x})}$ — the same
  Boltzmann target the THRML block-Gibbs runtime (Stage 2) approximates. The diagnostics already
  expose a $\beta$/temperature schedule, which is the single input this algorithm needs, so
  $M$-setting could be driven directly off a configured Gibbsiq run.
- **It connects feasibility, energy threshold $E_f$, and $\eta$ as one trade-off.** This is the
  quantitative backbone for a "should we trust feasibility?" diagnostic: a too-large $M$ produces
  feasible-but-high-objective collapse, a too-small $M$ floods infeasible samples — both are
  Gibbsiq failure modes (mode-collapse-like degradation, low feasibility) the inspector should flag.
- **Same benchmark scope.** TSP, number partitioning, and portfolio optimization are NP-problem
  formulations in Gibbsiq's benchmark catalog, and the paper reports them under the identical
  Gibbs/SA convention plus seeds — directly comparable baselines.

## Reading-list hooks

- Penalty/offset handling in QUBO↔Ising conversion and the energy convention →
  `CLAUDE.md` → "Canonical conventions".
- Feasibility / failure-flag diagnostics this guarantee feeds →
  diagnostics layer notes in [`../`](../) and the evaluation contract in
  [`../../08-evaluation/`](../../08-evaluation/).
- NP-problem Ising/QUBO formulations (TSP, number partitioning) used as benchmarks → Lucas 2014,
  [`../../05-theory/`](../../05-theory/) and [`../../06-benchmarks/`](../../06-benchmarks/).
