# Lab note — Benchmarking an Ising Machine on Max-Cut

> **Paper.** S. Shaglel, M. Kirsch, M. Winkler, C. Münch, S. Walter, F. Schinkel,
> and M. Kliesch. "A comprehensive benchmark of an Ising machine on the Max-Cut
> problem." arXiv:2507.22117, 2025.
> arXiv:[2507.22117](https://arxiv.org/abs/2507.22117) · BibTeX `shaglel2025`.
> Transcript: [`shaglel-2025-maxcut-ising-benchmark.md`](./shaglel-2025-maxcut-ising-benchmark.md).

## What the paper does

The paper is a large-scale, deliberately *fair* benchmark of Fujitsu's
quantum-inspired CMOS Digital Annealer — second generation (DAv2) and third
generation (DAv3) — on the Max-Cut problem, measured against the best classical
MQLib heuristics, D-Wave's hybrid solver, and the QIS3 metaheuristic. Evaluation
spans 2,125 MQLib instances from 200 to 53,000 variables, bucketed by size
(x-small through x-large) and density (sparse / balanced / dense). Max-Cut on a
graph $G=(V,E)$ is cast as the QUBO
$\text{minimize}\ x^{\mathsf T} Q x = \sum_{i \ge j} q_{ij} x_i x_j$ with
$x \in \{0,1\}^n$; concretely, maximizing the cut $\sum_{(i,j)\in E}(1 - x_i x_j)$
is equivalent to $\text{minimize}\ \sum_{(i,j)\in E} x_i x_j$. The Digital Annealer
itself is an MCMC/simulated-annealing engine — random spin init, a temperature
schedule, accept/reject moves, terminate at a stopping criterion — so its solver
contract is the same Boltzmann-sampling object Gibbsiq targets, just realized in
hardware.

The methodological core is *fairness under time budget*. Because solvers do not
stop exactly at a deadline, the authors enforce instance-specific time limits with
a 10% safety margin. For DAv2 they fit annealing-time and CPU-time functions of
runs, iterations, and $n$ (Eqs. 6–7), e.g.
$\text{Annealing\_time}(\text{runs}, \text{iterations}) = a\,(\text{runs}\times\text{iterations}) + b$;
for DAv3, whose runtime is too stochastic to fit, they pick an empirical 3-second
offset. Headline results: DAv2 beats or matches the best classical heuristic on
~69% of x-small/small instances and DAv3 on ~61%, with both DA versions matching or
exceeding QIS3 on 14 of 16 G-set instances and frequently converging to their best
cut within the first few seconds. DAv3 is notably more sensitive to float-to-integer
rounding error, and degrades on instances above the 8,192-variable single-DAU
capacity that force partitioning. The authors also disclose Fujitsu funding and
affiliations as a conflict of interest.

## Why it matters to Gibbsiq

- **It is a worked template for the Stage-5 benchmark layer.** Gibbsiq's benchmark
  plan compares the THRML sampler against simulated-annealing / OpenJij /
  simulated-bifurcation baselines under one energy convention and shared seeds; this
  paper supplies the discipline that makes such comparisons honest — instance-specific
  time limits, a 10% runtime safety margin, recorded solver configs, and
  best-vs-time-limit accounting rather than self-reported wins.
- **MQLib and the G-set are direct corpus candidates.** The 2,125 MQLib instances and
  the 16 G-set graphs (with the per-instance cut values in Table 4: G11→564, G32→1410,
  G1→11624, …) are externally sourced best-known values with provenance — exactly the
  "Tier B external library" entries Gibbsiq's `ground-truth-datasets.md` requires, and
  candidate Max-Cut instances beyond the brute-force-provable Tier A oracle.
- **The DA is a baseline peer of the THRML runtime.** Both are annealing/MCMC samplers
  of a quadratic spin energy; the DA's random-init → schedule → accept/reject loop maps
  onto the schedule/seed/init controls the Stage-2 THRML block-Gibbs layer must expose.
- **It motivates diagnostics, not just final energy.** The "rapid convergence in the
  first few seconds" finding is a best-so-far-trace observation, and the float-rounding
  and partitioning failure modes are precisely the sampler-health signals Gibbsiq's
  diagnostics layer (energy/best-so-far traces, feasibility, failure flags) is meant to
  surface alongside the answer.

## Reading-list hooks

- Benchmark methodology and corpus catalog (Tier A oracle + Tier B libraries, every
  value sourced) → [`../benchmark-plan.md`](../benchmark-plan.md),
  [`../ground-truth-datasets.md`](../ground-truth-datasets.md).
- Companion QUBO/Ising-machine benchmarks →
  [`./oshiyama-2022-qubo-heuristic-benchmark.md`](./oshiyama-2022-qubo-heuristic-benchmark.md),
  [`./bernal-neira-2024-quantum-heuristics-ising-machines.md`](./bernal-neira-2024-quantum-heuristics-ising-machines.md).
- Max-Cut Ising formulation it builds on → Lucas 2014,
  [`../../05-theory/papers/lucas-2014-ising-formulations.md`](../../05-theory/papers/lucas-2014-ising-formulations.md).
- Energy convention and offset-preserving QUBO↔Ising conversion the baselines must
  share (`CLAUDE.md` → "Canonical conventions").
