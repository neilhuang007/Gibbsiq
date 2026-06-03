# Lab note — Simulated Bifurcation Quantum Annealing

> **Paper.** J. Pawłowski, P. Tarasiuk, J. Tuziemski, Ł. Pawela, and B. Gardas.
> "Simulated Bifurcation Quantum Annealing." 2026.
> arXiv:[2604.01050](https://arxiv.org/abs/2604.01050) · BibTeX `pawlowski2026`.
> Transcript: [`pawlowski-2026-simulated-bifurcation-annealing.md`](./pawlowski-2026-simulated-bifurcation-annealing.md).

## What the paper does

The paper introduces **Simulated Bifurcation Quantum Annealing (SBQA)**, a
quantum-inspired heuristic for Ising spin-glass ground states that grafts
inter-replica coupling onto the Simulated Bifurcation Machine (SBM). SBM evolves
continuous position/momentum pairs $(q_i, p_i)$ under a time-dependent nonlinear
Hamiltonian whose equations of motion read
$\dot{q}_i = a_0 p_i$ and
$\dot{p}_i = -[a_0 - a(t)]\,q_i - c_0 h_i q_i - \tfrac{c_0}{2}\sum_j J_{ij} f(q_j) + h_i$,
with $a(t) = t/T$ and a confinement that resets $q_i \to \operatorname{sign}(q_i)$,
$p_i \to 0$ whenever $|q_i| > 1$. The spins are read off as $\operatorname{sign}(q_i)$
once the bifurcation has driven the system away from the origin. SBQA runs $R$
replicas of this dynamics and couples adjacent imaginary-time slices, so the
momentum update gains a term $J_\perp\,(q_{i,k-1} + q_{i,k+1})$ that mimics quantum
tunneling and lets trajectories escape the steep, isolated minima where SBM
stalls.

The replica coupling is not a free knob: it is the exact Suzuki–Trotter coupling
of the transverse-field Ising model, derived in the supplement, giving
$$J_\perp(t) = -\frac{1}{2\beta}\,\ln\tanh\!\left(\frac{\beta\,\Gamma_x(t)}{R}\right),
\qquad \Gamma_x(t) = \Gamma_x(0)\big[(1 - t/T)^\alpha + 10^{-5}\big],$$
so annealing the transverse field $\Gamma_x(t) \to 0$ ramps the replicas from
strongly coupled to independent ($\alpha$ is the schedule exponent, $\beta$ the
inverse temperature, and $10^{-5}$ regularizes the endpoint). Because $\beta$ and
$\alpha$ resist per-instance tuning, the authors restrict them to
$\beta \in [0.5, 1.5]$, $\alpha \in [0.5, 1.0]$ and auto-tune by drawing fresh
$(\beta, \alpha)$ per repetition and keeping the best. Scored by time-to-epsilon
and the optimality gap $g = (E - E_0)/|E_0|$, SBQA systematically beats SBM on
sparse and rugged landscapes (Zephyr graphs, QAC logical graphs, 2D/3D
tile-planted glasses, Pegasus-embedded glasses, heavy-hex HUBO) at negligible
runtime overhead, while staying competitive elsewhere.

## Why it matters to Gibbsiq

- **A baseline the benchmark layer should carry.** Gibbsiq's benchmark layer
  already names simulated bifurcation alongside simulated annealing and OpenJij as
  reference solvers; SBQA is the current strengthened SBM variant and the right
  classical bar for the "sparse and rugged" instance families, run under the same
  energy convention and seeds as the THRML sampler.
- **Replica coupling parallels block-Gibbs chains.** SBQA's $R$ interacting
  replicas are conceptually adjacent to the multiple chains the diagnostics layer
  compares for R-hat-style chain disagreement — both run independent trajectories
  and exploit their disagreement, one to escape minima, the other to flag mixing
  failure. The transverse-field ramp $\Gamma_x(t)$ is the same kind of annealing
  schedule control the THRML runtime layer must expose (schedule/seed/init/read).
- **Time-to-epsilon and optimality gap are honest figures of merit.** The paper's
  insistence on total externally measurable runtime and the gap
  $g = (E - E_0)/|E_0|$ against a *recorded* reference energy aligns with Gibbsiq's
  rule that best-known values need a source and that the oracle re-verifies a
  witness state rather than trusting self-reported numbers.
- **Same Ising object, offset aside.** SBM/SBQA optimize $\sum h_i s_i + \sum J_{ij} s_i s_j$
  with $s_i \in \{-1,+1\}$ — the IR Gibbsiq lowers QUBO/Ising/BQM into — so a
  baseline adapter only needs to pass $(h, J)$ and preserve the offset when
  reporting `best_energy`.

## Reading-list hooks

- Sibling simulated-bifurcation papers →
  [`./tao-2026-tabu-simulated-bifurcation.md`](./tao-2026-tabu-simulated-bifurcation.md)
  and [`./turingq-2025-qis3-qubo-solver.md`](./turingq-2025-qis3-qubo-solver.md).
- Baseline solver catalog and the THRML Gibbs runtime →
  [`../baseline-solvers.md`](../baseline-solvers.md),
  [`../thrml-gibbs-implementation.md`](../thrml-gibbs-implementation.md).
- Energy convention and offset preservation → `CLAUDE.md` → "Canonical conventions";
  benchmark sourcing/witness rules →
  [`../../06-benchmarks/ground-truth-datasets.md`](../../06-benchmarks/ground-truth-datasets.md).
- NP-problem Ising formulations behind the benchmark families → Lucas 2014,
  [`../../05-theory/papers/lucas-2014-ising-formulations.md`](../../05-theory/papers/lucas-2014-ising-formulations.md).
