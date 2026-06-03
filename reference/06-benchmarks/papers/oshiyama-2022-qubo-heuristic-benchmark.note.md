# Lab note — Benchmark of quantum-inspired heuristic QUBO solvers

> **Paper.** H. Oshiyama and M. Ohzeki. "Benchmark of quantum-inspired heuristic
> solvers for quadratic unconstrained binary optimization." *Scientific Reports*
> 12(1):2146 (2022).
> DOI: [10.1038/s41598-022-06070-5](https://doi.org/10.1038/s41598-022-06070-5) ·
> BibTeX `oshiyama2022`.
> Transcript: [`oshiyama-2022-qubo-heuristic-benchmark.md`](./oshiyama-2022-qubo-heuristic-benchmark.md).

## What the paper does

The paper benchmarks four heuristic solvers for quadratic unconstrained binary
optimization — D-Wave Hybrid Solver Service (HSS), Toshiba Simulated Bifurcation
Machine (SBM), Fujitsu Digital Annealer (DA), and simulated annealing (SA) run on a
single CPU via D-Wave neal — under a fixed-wall-clock-time protocol. QUBO is taken in
the standard binary form $E(\mathbf{x}) = \sum_{i,j} Q_{i,j} x_i x_j$ with
$x_i \in \{0,1\}$. Three problem families probe different landscape types: 45 MQLib
instances (real-world-derived, $1000 \le N \le 10000$, stratified by size and edge
density), random Not-All-Equal 3-SAT at the SAT–UNSAT critical ratio $M/N \approx 2.11$,
and the Sherrington–Kirkpatrick spin glass. The latter two are stated directly in the
Ising convention $\sigma_i \in \{-1,+1\}$ — NAE 3-SAT as
$E(\boldsymbol{\sigma}) = \tfrac14 \sum_m (\zeta_{m,1}\zeta_{m,2}\sigma_{i_{m,1}}\sigma_{i_{m,2}} + \cdots + 1)$
and SK as $E(\boldsymbol{\sigma}) = \tfrac{1}{\sqrt{N}} \sum_{i \le j} J_{i,j}\sigma_i\sigma_j$
with Gaussian $J_{i,j}$ — then mapped to QUBO via $x_i = (\sigma_i + 1)/2$.

Solution quality is scored relative to the best value found across all four solvers,
$S_{\mathrm{solver}} = E_{\mathrm{solver}}/E_0$ with $E_0 = \min\{E_{\mathrm{HSS}}, E_{\mathrm{SBM}}, E_{\mathrm{DA}}, E_{\mathrm{SA}}\}$.
The headline finding is that no solver dominates: HSS ranks first on the heterogeneous
MQLib set (most wins, with SBM nearly tied and stable), DA wins on NAE 3-SAT across most
run times, and SBM clearly leads on the SK model. Listings 1 and 2 give the exact Python
generators (fixed seeds) for the NAE 3-SAT and SK instances, and Table 10 records the
lowest cost-function value found per MQLib instance with the winning solver(s).

## Why it matters to Gibbsiq

- **It is a baseline-layer reference.** SA via D-Wave neal and the simulated-bifurcation
  family are exactly the baselines Gibbsiq's benchmark layer must reproduce under the same
  energy convention and seeds; this paper documents their relative behaviour and the
  fixed-time protocol they were run under.
- **The relative-score metric is a model for benchmark reporting.** Because true optima are
  unknown at $N \sim 10^4$, the paper scores against a best-found value $E_0$ — a pattern
  Gibbsiq's ground-truth datasets follow only where optima are *proven* by enumeration,
  while flagging best-known-without-source values as a non-negotiable failure case.
- **The instance generators are reusable, seeded fixtures.** Listings 1–2 produce the SK and
  NAE 3-SAT instances deterministically in Ising form, matching Gibbsiq's requirement that
  benchmark instances record a seed or checksum and convert offset-faithfully into the
  internal Ising IR ($x_i = (\sigma_i+1)/2$ being the QUBO↔Ising map Gibbsiq audits).
- **SK and SAT cover hard mixing regimes.** The SK many-valley landscape and the
  solution-scarce SAT–UNSAT transition are precisely the regimes where Gibbsiq's diagnostics
  layer (mode collapse, chain disagreement, no recent improvement) should fire, so they make
  good stress fixtures for the THRML block-Gibbs runtime.

## Reading-list hooks

- Benchmark protocol and dataset catalog → [`../benchmark-plan.md`](../benchmark-plan.md),
  [`../ground-truth-datasets.md`](../ground-truth-datasets.md).
- Simulated-bifurcation baseline algorithm → [`bernal-neira-2024-quantum-heuristics-ising-machines.md`](./bernal-neira-2024-quantum-heuristics-ising-machines.md)
  and the Max-Cut/Ising benchmark note [`shaglel-2025-maxcut-ising-benchmark.md`](./shaglel-2025-maxcut-ising-benchmark.md).
- Energy / QUBO↔Ising convention and offset preservation → `CLAUDE.md` →
  "Canonical conventions", audited in [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).
- NP-problem Ising formulations (SAT, spin glass) → Lucas 2014 in
  [`../../05-theory/`](../../05-theory/).
