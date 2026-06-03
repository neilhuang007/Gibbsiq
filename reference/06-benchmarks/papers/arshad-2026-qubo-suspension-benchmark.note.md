# Lab note — Benchmarking QUBO Solvers on a Suspension-Geometry Instance

> **Paper.** M. W. Arshad, S. Lodi, O. Ashraf, M. H. Rasool, and S. R. Hassan.
> "HPC: A Computational Benchmark of Classical, Parallel, and Hybrid Metaheuristics
> for QUBO-Based Suspension Geometry Optimization." *Machines* 14(2):248 (2026).
> DOI: [10.3390/machines14020248](https://doi.org/10.3390/machines14020248) · BibTeX `arshad2026`.
> Transcript: [`arshad-2026-qubo-suspension-benchmark.md`](./arshad-2026-qubo-suspension-benchmark.md).

## What the paper does

The paper builds a single large QUBO instance from a realistic engineering model — a
symbolic 3D double-wishbone suspension — and uses it as a fixed reference benchmark for
comparing a suite of classical, parallel, and hybrid metaheuristic solvers. A SymPy
kinematic model yields polynomial surrogates for camber $\tilde\gamma^{(k)}$ and caster
$\tilde\kappa^{(k)}$ across $N_p=5$ roll samples; a continuous tracking-plus-penalty
objective $f_{tot}=f_{track}+P_{eq}\sum_m g_m^2 + P_{ineq}\sum_\ell[\max\{0,h_\ell\}]^2$
is then discretized. Each of the 30 geometry variables and the internal angles is linearly
encoded by $B$ bits, $v_i(\mathbf b_i)=l_i+\frac{u_i-l_i}{2^B-1}\sum_k 2^k b_{i,k}$, and at
the chosen low resolution $B=1$ this collapses to a two-level choice $v_i=l_i+(u_i-l_i)b_{i,0}$.
Substituting and applying Rosenberg-style quadratic reduction yields the standard form

$$\min_{\mathbf{x}\in\{0,1\}^N} E(\mathbf{x}) = \mathbf{x}^{\top} Q\,\mathbf{x} + \mathbf{q}^{\top}\mathbf{x} + c,$$

a 787-variable QUBO with a constant offset $c$ (defaults $P_{equality}=1000$, $P_{inequality}=500$).

Seven solvers run on this one BQM on the EuroHPC Leonardo CPU partition under fixed seeds and a
shared `FAST_MODE` budget: simulated annealing (Metropolis rule
$\Pr(\mathbf x\to\mathbf x')=\exp(-\Delta E/T)$ for $\Delta E>0$), tabu search, parallel-SA,
bandit-hybrid SA–tabu (softmax over reward-per-time arm values), population-parallel SA, an
ADMM continuous relaxation, and an ADMM-warm-started SA hybrid. The headline finding is a
runtime–quality Pareto frontier with no dominant solver: parallel-SA reaches the best energy
(−845.29 with offset, ~8 units below SA) at the cost of runtime, while BH-SA and the ADMM
methods cut wall-clock time by one-to-two orders of magnitude at slightly worse energy.
Decoded camber/caster RMSE is nearly solver-independent — an artifact of the coarse $B=1$
encoding, not of the optimizers.

## Why it matters to Gibbsiq

- **It is a baselines-and-benchmarks reference for layer 5.** The solver roster — SA, tabu,
  parallel-SA, and hybrids on a shared BQM under fixed seeds — is exactly the comparison set
  Gibbsiq's benchmark layer targets (simulated annealing / neal-dimod, plus the
  simulated-bifurcation/OpenJij baselines). The paper's protocol (one frozen instance, common
  stopping criteria, seed control, speedup-vs-SA tables) is a template for how Gibbsiq should
  report a THRML sampler against established samplers under one energy convention.
- **It exercises the interface/IR offset contract.** Energy is reported "both with and without
  the constant offset," and the QUBO is `z^T Q z + q^T z + c` with $c$ tracked through compilation.
  This is precisely Gibbsiq's rule that the offset is preserved through QUBO↔Ising conversion and
  surfaced in `best_energy` — dropping it is a hard evaluation failure. The penalty structure
  ($P_{eq}$, $P_{ineq}$ sum-of-squares / hinge terms folded into $c$) is the encoding-side
  penalty/offset handling the IR layer must round-trip faithfully.
- **It is a runtime–quality trade-off study, which is the diagnostics thesis.** The paper's core
  message — that solver choice is a Pareto decision between objective value and time-to-solution,
  and that apparent solution differences can be modeling artifacts — is the same argument behind
  Gibbsiq's "should we trust how we found it?" contract. Best-so-far energy traces and convergence
  plateaus (their ADMM early-stagnation finding) map directly onto layer-3 best-so-far traces and
  `no_recent_improvement`-style flags.
- **It is a real-world QUBO source for the corpus.** Unlike synthetic instances, this engineering-
  derived QUBO has dense couplings and heterogeneous penalty magnitudes; recording it (id, seed,
  formulation metadata, solver config) fits the benchmark-family rules, though its optimum is
  best-known rather than exhaustively proven, so it belongs alongside Tier B externals, not the
  strict exact-oracle Tier A.

## Reading-list hooks

- Baseline samplers and benchmark reporting → [`../benchmark-plan.md`](../benchmark-plan.md)
  and [`../ground-truth-datasets.md`](../ground-truth-datasets.md); baseline solver notes in
  [`../../03-samplers/`](../../03-samplers/).
- Offset-preserving QUBO→Ising conversion and penalty handling → `CLAUDE.md`
  → "Canonical conventions" and the interface/IR layer.
- Penalty-weight calibration for constrained QUBOs →
  [`../../04-diagnostics/`](../../04-diagnostics/) penalty-weighting references.
- NP-problem Ising/QUBO formulations for the wider benchmark corpus → Lucas 2014,
  [`../../05-theory/papers/lucas-2014-ising-formulations.md`](../../05-theory/papers/lucas-2014-ising-formulations.md).
