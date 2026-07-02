# Lab note — Tabu-Enhanced Simulated Bifurcation

> **Paper.** X.-Z. Tao, Q.-G. Zeng, Z.-J. Huang, B.-W. Zuo, Y.-Q. Liu, J. Zhuang,
> H. Okawa, and M.-H. Yung. "Tabu-Enhanced Simulated Bifurcation for combinatorial
> optimization." *Communications Physics* 9(1):100 (2026).
> DOI: [10.1038/s42005-026-02538-2](https://doi.org/10.1038/s42005-026-02538-2) ·
> BibTeX `tao2026`.
> Transcript: [`tao-2026-tabu-simulated-bifurcation.md`](./tao-2026-tabu-simulated-bifurcation.md).

## What the paper does

Simulated Bifurcation (SB) is a quantum-annealing-inspired solver that maps an
Ising problem onto continuous oscillators and integrates classical equations of
motion to relax toward a low-energy spin configuration. The target is the standard
objective over $\{s_i\} \in \{-1,+1\}^n$,
$E_{\text{Ising}} = -\tfrac{1}{2}\sum_{i,j} J_{ij} s_i s_j - \sum_i h_i s_i$, with
the ballistic (bSB) and discrete (dSB) variants driven by a time-dependent
Hamiltonian whose Ising term is gradually turned on by a linear schedule $a(t)$
from $0$ to $a_0$. The known failure mode is entrapment in local optima,
especially on skewed-degree graphs. The paper's contribution, Tabu-Enhanced SB
(TESB / TEdSB), runs a cheap *warming-up* phase that collects a set of suboptimal
minima $\mathcal{M}$, then a *checking* phase that adds a history-guided penalty to
the potential so those visited basins are raised and the dynamics are pushed
elsewhere. The penalty contributes an extra force term to the equation of motion,

$$T_i(t) = -\frac{c_0}{2\,|\mathcal{M}_\ell|}\sum_{s^{\mu}\in \mathcal{M}_\ell} s_i^{\mu},$$

and — crucially — it is built from a *stochastic mini-batch* of $\mathcal{M}$
(batch size $|\mathcal{M}_\ell| = 2$) re-sampled each iteration rather than the full
set, which keeps the penalty dynamic and preserves search diversity. A single
hyperparameter $\alpha$ splits the iteration budget between phases; at $\alpha = 0$
the method reduces exactly to baseline bSB/dSB. On G-set Max-Cut instances TESB
cuts Time-to-Solution, $\text{TTS} = T\,\log(1-0.99)/\log(1-P_s)$, by up to three
orders of magnitude, and on TrackML particle-tracking Ising models exceeding
$10^5$ spins it finds lower-energy states at reduced cost.

## Why it matters to Gibbsiq

- **It is a benchmark-layer baseline solver.** SB / bSB / dSB sit alongside
  simulated annealing and OpenJij as the non-Gibbs baselines Gibbsiq's layer-5
  benchmarks must run under a shared energy convention and seed; TESB is the
  current state-of-the-art SB variant to compare THRML block-Gibbs against on
  Max-Cut.
- **Its evaluation protocol is our benchmark protocol.** G-set Max-Cut with
  best-known optima as the reference, approximation ratio, and TTS over many
  independent trials are exactly the metrics and instance families the benchmark
  oracle scores; the TTS formula above is a ready-made cross-solver yardstick.
- **The local-optima trap and the mini-batch fix map onto diagnostics.** The
  paper's core problem — premature convergence into a single basin — is what the
  layer-3 `mode_collapse` and diversity diagnostics (unique fraction, top-k mass,
  Hamming spread) are meant to detect, and its "keep the penalty diverse" argument
  is the same intuition behind tracking sample diversity rather than just
  best-energy.
- **Phase split as schedule/trace hooks.** Warming-up vs. checking, the linear
  $a(t)$ ramp, and the per-iteration best-energy trajectory are precisely the
  schedule controls and best-so-far traces the THRML runtime layer must expose.
- **Convention check.** The paper's $-\tfrac12\sum J_{ij}s_i s_j$ (full,
  symmetric, double-counted) form differs from Gibbsiq's
  $E = \text{offset} + \sum_i h_i s_i + \sum_{i<j} J_{ij} s_i s_j$ (upper-triangle,
  no double-count, offset preserved); the factor-of-two and overall sign must be
  reconciled before any TESB energy is reported through Gibbsiq.

## Reading-list hooks

- Baseline solver catalog and how SB sits beside SA/OpenJij →
  [`../baseline-solvers.md`](../baseline-solvers.md).
- Companion SB-annealing paper in this section →
  [`./pawlowski-2026-simulated-bifurcation-annealing.md`](./pawlowski-2026-simulated-bifurcation-annealing.md).
- THRML block-Gibbs runtime (schedule / trace hooks) →
  [`../thrml-optimization-runtime.md`](../thrml-optimization-runtime.md).
- Energy convention and offset handling (`CLAUDE.md` → "Canonical conventions"),
  audited in [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).
- Max-Cut Ising formulation used for benchmarks → Lucas 2014,
  [`../../05-theory/papers/lucas-2014-ising-formulations.md`](../../05-theory/papers/lucas-2014-ising-formulations.md).
