# Lab note — Parallel p-bit Ising machines and update dynamics

> **Paper.** N. Onizawa and T. Hanyu. "A Unified Performance-Cost Landscape of
> Parallel p-bit Ising Machines Based on Update Dynamics." arXiv preprint, 2026.
> arXiv:[2604.01564](https://arxiv.org/abs/2604.01564) · BibTeX `onizawa2026`.
> Transcript: [`onizawa-2026-parallel-pbit-ising.md`](./onizawa-2026-parallel-pbit-ising.md).

## What the paper does

The paper studies how the *update schedule* of a parallel p-bit Ising machine —
not the probabilistic model itself — governs stability, solution quality, and
hardware cost. Each Ising spin $\sigma_i \in \{-1,+1\}$ is a logical p-bit whose
stochastic update is $\sigma_i(t^+) = \mathrm{sgn}\!\big(r_i(t) + \tanh I_i(t)\big)$
with $r_i \sim U(-1,1)$, equivalent to sampling $\Pr[\sigma_i = +1] = \tfrac12(1 +
\tanh I_i)$ from the local field $I_i(t) = I_0(t)\big(h_i + \sum_j J_{ij}\sigma_j\big)$,
where the pseudo inverse temperature $I_0(t)$ is ramped to anneal. On this common
substrate the authors sweep four architectural knobs: the update policy
(asynchronous Gillespie vs. synchronous tick-random / block-random /
block-random-stride), the update interval $\tau$, a *time-multiplexing reuse
factor* $c$ (logical p-bits mapped onto one physical p-bit), and the input-DAC bit
width $b$. The central observable is the delay-to-update ratio $d/\tau$ with fixed
apply delay $d = 5$ ns.

Their key result is that synchronous oscillation is a consequence of excessive
update simultaneity, not an inherent flaw: reuse rescales the per-spin update rate
to $\lambda_{\text{spin}} = 1/(\tau c)$, a pure temporal thinning of the Markov
process that leaves the stationary distribution unchanged while smoothing the
energy trajectory once $c \ge 2$. Because reuse shrinks the physical resource count
as $N_p = \lceil N/c\rceil$ (DACs scaling likewise), with abstract cost
$C_{\text{HW}} = \alpha N_p + \beta b\,N_{\text{DAC}}$, structured synchronous
control reaches near-best normalized cut on G-set MaxCut instances (800–2000 nodes)
at less than half the cost of the best asynchronous configuration. Asynchronous
updates, by contrast, degrade as $d/\tau \to 1$ from spins acting on stale local
fields, and cannot exploit reuse. Low-resolution input DACs (3–4 bits) suffice
within a few percent of best-known when annealing time is extended.

## Why it matters to Gibbsiq

- **The p-bit update is the THRML block-Gibbs conditional in hardware form.**
  $\Pr[\sigma_i = +1] = \tfrac12(1 + \tanh I_i)$ with $I_i \propto h_i + \sum_j
  J_{ij}\sigma_j$ is algebraically Gibbsiq's audited `sigmoid(-2 * beta * gamma_i)`
  over local field $\gamma_i = h_i + \sum_j J_{ij} s_j$ — the paper's $I_0(t)$ is the
  $\beta$ schedule the Stage-2 runtime must expose. Note the sign/factor
  reconciliation against the paper's $H = -\tfrac12 \sigma^{\top} J \sigma -
  h^{\top}\sigma$ form versus Gibbsiq's upper-triangle, offset-preserving
  $E = \text{offset} + \sum_i h_i s_i + \sum_{i<j} J_{ij} s_i s_j$.
- **It is direct guidance for the block-Gibbs update policy.** The synchronous /
  asynchronous / sequential distinction maps onto how the THRML runtime schedules
  block updates; the paper's warning that excessive simultaneity in tightly coupled
  graphs causes oscillation (non-monotonic energy) is exactly the kind of failure the
  diagnostics layer should surface via the energy trace and chain-disagreement flags.
- **Its benchmark is in scope.** G-set MaxCut at 800–2000 nodes, scored by
  normalized cut against best-known, is the family Gibbsiq's benchmark layer targets;
  the "near-best within a few percent" framing is a baseline-comparison reference.

## Reading-list hooks

- p-bit lineage and probabilistic-computing background →
  [`../probabilistic-computing-and-pbits.md`](../probabilistic-computing-and-pbits.md);
  foundational BSN/energy convention →
  [`./camsari-2018-probabilistic-spin-logic.note.md`](./camsari-2018-probabilistic-spin-logic.note.md).
- Gibbs sign and local-field convention → `CLAUDE.md` → "Canonical conventions",
  audited in [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).
- Max-Cut Ising formulation for the benchmark family → Lucas 2014,
  [`./lucas-2014-ising-formulations.md`](./lucas-2014-ising-formulations.md).
