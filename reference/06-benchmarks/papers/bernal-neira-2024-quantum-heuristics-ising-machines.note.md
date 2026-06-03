# Lab note — Benchmarking Quantum Heuristics and Ising Machines

> **Paper.** D. E. Bernal Neira, R. Brown, P. Sathe, F. Wudarski, M. Pavone,
> E. G. Rieffel, and D. Venturelli. "Benchmarking the Operation of Quantum
> Heuristics and Ising Machines: Scoring Parameter Setting Strategies on
> Optimization Applications." arXiv preprint, 2024.
> arXiv:[2402.10255](https://arxiv.org/abs/2402.10255) · BibTeX `bernalneira2024`.
> Transcript: [`bernal-neira-2024-quantum-heuristics-ising-machines.md`](./bernal-neira-2024-quantum-heuristics-ising-machines.md).

## What the paper does

The paper proposes an *operational* benchmarking methodology for parameterized
stochastic optimization solvers — quantum heuristics, quantum annealers, and Ising
machines — that treats each solver as a sampler of an unknown output distribution
rather than a deterministic oracle. Its raw output is a bitstring
$\mathbf{z} = \{z_1,\dots,z_N\}$, $z_i \in \{0,1\}$ (equivalently a spin
configuration $\sigma_i \in \{-1,+1\}$), mapped through a pseudo-Boolean cost
$X = \mathrm{fun}(\mathbf{z})$, and the benchmark estimates the PDF of $X$ over a
distribution of representative instances. The central insight is that the *cost of
setting parameters* must be accounted for: optimal parameters vary per instance, so
a fair score charges the resources spent tuning. The methodology builds "Window
stickers" — performance profiles for a set of parameter-setting strategies (PSSs),
bounded above by the *virtual best* (an oracle that picks the best method per
instance and resource), with fixed (fPSS) and adaptive (`Hyperopt`-driven,
exploration–exploitation) strategies cross-validated over train/test splits. The
worked example minimizes a zero-field Ising energy

$$\min_{\mathbf{s}\in\{\pm1\}^N}\ \sum_{i,j=1}^{N} s_i J_{ij} s_j
  = \min_{\mathbf{s}\in\{\pm1\}^N}\ \mathbf{s}^\top J\,\mathbf{s}$$

over Wishart planted instances (known optima), comparing a chaotic-amplitude-control
coherent Ising machine simulator against parallel tempering (`PySA`). Quality is
reported with a normalized performance score,

$$\text{Performance Score} =
  \frac{\text{best found} - \text{random}}{\text{optimal} - \text{random}},$$

ranging from 0 (no better than random sampling) to 1 (optimal), and shipped in the
open-source `Stochastic-Benchmark` package.

## Why it matters to Gibbsiq

- **Direct charter for the benchmarks layer (layer 5).** The paper formalizes what
  a "conscientious" stochastic benchmark must report — instance distribution,
  resource definition, parameter search space, success test, confidence intervals,
  and the *tuning overhead* — which is exactly the discipline Gibbsiq's benchmark
  oracle and `benchmark-plan.md` need. Gibbsiq's THRML sampler is itself a
  parameterized stochastic solver (schedule, seed, init, num_reads), so its results
  belong on a Window-sticker-style profile rather than a single best-energy number.
- **Wishart planted instances are a ready-made oracle corpus.** Like Gibbsiq's
  exhaustively-proven ground-truth fixtures, the Wishart ensemble supplies the
  *known optimum* needed to define an optimality gap; the normalized performance
  score is a clean diagnostics-side metric ("how close, and should we trust it?")
  that fits beside Gibbsiq's feasibility/optimality re-verification.
- **Energy convention matches.** The paper's $\sum_{i,j} s_i J_{ij} s_j$,
  $s_i\in\{\pm1\}$ objective is the same Ising object Gibbsiq lowers QUBO/BQM into;
  its footnote that spin and binary representations are equivalent up to a linear
  transformation is the offset-preserving QUBO↔Ising conversion Gibbsiq audits.
- **Parallel tempering is a named baseline.** `PySA` and the CIM simulator are
  precisely the simulated-annealing / Ising-machine baselines Gibbsiq plans to run
  under shared seeds and the same energy convention.

## Reading-list hooks

- Benchmark methodology and corpus design → [`../benchmark-plan.md`](../benchmark-plan.md)
  and [`../ground-truth-datasets.md`](../ground-truth-datasets.md).
- Sibling QUBO/Ising solver benchmarks →
  [`./oshiyama-2022-qubo-heuristic-benchmark.md`](./oshiyama-2022-qubo-heuristic-benchmark.md),
  [`./shaglel-2025-maxcut-ising-benchmark.md`](./shaglel-2025-maxcut-ising-benchmark.md).
- Energy/offset and Gibbs-sign contract the baselines must share →
  `CLAUDE.md` → "Canonical conventions", audited in
  [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).
- Ising machine / p-bit solver lineage being benchmarked →
  [`../../05-theory/papers/camsari-2018-probabilistic-spin-logic.note.md`](../../05-theory/papers/camsari-2018-probabilistic-spin-logic.note.md).
