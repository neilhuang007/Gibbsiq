# Lab note — Thermodynamic significance of QUBO encoding

> **Paper.** E. Doucet, Z. Mzaouali, R. Robertson, B. Gardas, S. Deffner, and
> K. Domino. "Thermodynamic significance of QUBO encoding on quantum annealers."
> *New Journal of Physics* 28(5):054512 (2026).
> DOI: [10.1088/1367-2630/ae6e98](https://doi.org/10.1088/1367-2630/ae6e98) ·
> arXiv:[2601.04402](https://arxiv.org/abs/2601.04402) · BibTeX `doucet2026`.
> Transcript: [`doucet-2026-qubo-encoding-thermodynamics.md`](./doucet-2026-qubo-encoding-thermodynamics.md).

## What the paper does

The paper studies how the *choice* of QUBO encoding for a fixed constrained problem
reshapes the energy landscape a quantum annealer experiences. Using a Job Shop
scheduling instance, the authors build a two-parameter family of encodings whose
constraints are imposed by penalty terms with weights $p_{\text{sum}}$ (one-hot /
sum constraints) and $p_{\text{pair}}$ (precedence constraints), added to a linear
tardiness objective. The QUBO is read on hardware as the equivalent Ising energy,
with the spin map $s = 2\vec{x} - 1$, $s_i \in \{-1, +1\}$, giving
$$E_{\text{Ising}}(s) = \sum_i h_i s_i + \tfrac{1}{2} \sum_{i \neq i'} J_{ii'} s_i s_{i'},$$
where $h_i$ and $J_{ii'}$ are built by linear transformation from the linear and
quadratic parts of the QUBO. Sweeping the $(p_{\text{sum}}, p_{\text{pair}})$ plane
reveals sharp regime boundaries: too-weak penalties leave low-energy *infeasible*
configurations dominating the spectrum, while sufficiently strong penalties lift the
infeasible manifold and isolate the feasible optimum (the transition near
$p_{\text{sum}} > 0.5$, $p_{\text{pair}} > 0.25$ for the 8-variable instance). The
boundaries are asymmetric — $p_{\text{sum}}$ matters far more than $p_{\text{pair}}$.

Beyond solution probability, the annealer is treated as an open thermodynamic
machine. Cyclic reverse-anneal experiments are initialized from classical Gibbs
samples $p_{\beta_1}(\sigma) \propto e^{-\beta_1 E_z(\sigma)}$ and only the processor
energy change $\Delta E_1$ is measured. From its first two moments a thermodynamic
uncertainty relation yields a lower bound on entropy production,
$$\langle \Sigma \rangle \ge 2\,g\!\left(\frac{\langle \Delta E_1 \rangle}{\sqrt{\langle \Delta E_1^2 \rangle}}\right), \qquad g(x) = x\,\tanh^{-1}(x),$$
with companion bounds on heat and work and an efficiency $\eta = -\langle W \rangle / \langle Q \rangle$.
The same penalty transitions that govern computational hardness also reorganize
dissipation, so QUBO penalties act as thermodynamic control knobs.

## Why it matters to Gibbsiq

- **Penalty weights are an interface/IR concern, not a postprocessing afterthought.**
  The paper's central claim — one constrained task admits many QUBO encodings whose
  penalty magnitudes reshape feasibility, degeneracy, and barrier structure — is the
  rationale for treating penalty/offset handling as a first-class part of Gibbsiq's
  ingestion layer (QUBO/Ising/BQM → Ising IR). The linear tardiness objective is
  reported relative to an `offset` (Eqs. 4, A6b), exactly the offset Gibbsiq must
  preserve through QUBO↔Ising conversion.
- **The spin/energy convention is checkable against ours.** The paper's
  $E_{\text{Ising}}$ uses the symmetric $\tfrac12 \sum_{i \neq i'}$ form; Gibbsiq uses
  the upper-triangle, no-double-count $E(s) = \text{offset} + \sum_i h_i s_i + \sum_{i<j} J_{ij} s_i s_j$.
  Reconciling the factor of two is the routine conversion the equation audit guards.
- **Feasibility transitions are a diagnostics signal.** "Weak penalty → low-energy
  infeasible manifold" is precisely the failure mode Gibbsiq's feasibility and
  failure-flag diagnostics (layer 3) exist to surface; the paper shows the boundary is
  sharp and encoding-driven, motivating sweeping penalty weights as part of solver health checks.
- **Dissipation as a hardware-grounded health metric** complements Gibbsiq's
  mixing/efficiency diagnostics: entropy-production / work bounds give an
  irreversibility readout analogous in spirit to the ESS- and R-hat-style quality
  estimates the diagnostics layer reports, but on the physical annealer.

## Reading-list hooks

- Penalty-weight selection and the big-M / scaling problem →
  [`./alessandroni-2026-penalization-weights.md`](./alessandroni-2026-penalization-weights.md),
  [`./alessandroni-2025-quantum-big-m.md`](./alessandroni-2025-quantum-big-m.md).
- Energy convention, Gibbs sign, and offset preservation → `CLAUDE.md`
  ("Canonical conventions"), audited in
  [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).
- QUBO/BQM ingestion and offset-preserving conversion →
  [`../../02-interfaces/qubo-bqm-api.md`](../../02-interfaces/qubo-bqm-api.md).
- Job Shop / scheduling Ising formulations and benchmark catalog → Lucas 2014
  ([`../../05-theory/papers/lucas-2014-ising-formulations.md`](../../05-theory/papers/lucas-2014-ising-formulations.md))
  and [`../../06-benchmarks/ground-truth-datasets.md`](../../06-benchmarks/ground-truth-datasets.md).
- Mixing-quality diagnostics this complements →
  [`../mixing-quality.md`](../mixing-quality.md).
