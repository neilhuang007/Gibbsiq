# Lab note — pc-COP: a 2048-p-bit FPGA accelerator for combinatorial optimization

> **Paper.** K. Magar, S. Bharathan, and U. Banerjee. "pc-COP: An Efficient and
> Configurable 2048-p-Bit Fully-Connected Probabilistic Computing Accelerator for
> Combinatorial Optimization." *2024 IEEE High Performance Extreme Computing
> Conference (HPEC)*, pp. 1-7, 2024.
> DOI: [10.1109/hpec62836.2024.10938509](https://doi.org/10.1109/hpec62836.2024.10938509) ·
> arXiv:[2504.04543](https://arxiv.org/abs/2504.04543) · BibTeX `magar2025`.
> Transcript: [`magar-2025-pc-cop-pbit-accelerator.md`](./magar-2025-pc-cop-pbit-accelerator.md).

## What the paper does

The paper presents pc-COP, a configurable Xilinx UltraScale+ FPGA accelerator with
2048 fully connected probabilistic bits (p-bits) that solves graph max-cut by
running the probabilistic-computing analogue of Gibbs sampling in hardware. Each
p-bit is a binary stochastic neuron updated *sequentially* (one full sweep over all
$N_m$ p-bits is a "sample", repeated for $N_s$ samples) via the rule
$m_i \leftarrow \mathrm{sgn}\!\big(\mathrm{rand}(-1,+1) + \tanh(I_i)\big)$ with local
field $I_i = \beta\,(h_i + \sum_{j} J_{i,j} m_j)$ and $m_i \in \{-1,+1\}$. The
stationary distribution is Boltzmann, $p_{\{m\}} \propto \exp[-\beta E(\{m\})]$, for
the Ising energy

$$E(\{m\}) = -\Big(\sum_{i<j} J_{i,j} m_i m_j + \sum_i h_i m_i\Big),$$

and $\beta$ is annealed geometrically across samples,
$\beta_s = \beta_{\text{initial}} \cdot \beta_{\text{anneal-rate}}^{\,s-1}$. Max-cut
is encoded by setting $J_{i,j} = -w_{i,j}$, $h_i = 0$, so minimizing the energy
maximizes the cut. The engineering contributions are a logarithmic adder tree for
the sum-of-products, a piece-wise-linear approximation of $\tanh$ (the $T=1$ clamp
$\mathrm{clip}(\text{input}, -1, +1)$ costs ~5x fewer LUTs than a lookup table at
matched accuracy), and a *pseudo-parallel speculate-and-select* update that
pre-computes both branches of the next p-bit conditioned on the current one and
selects after — preserving the exact sequential Gibbs dependency while updating
$k$ p-bits per cycle (4x speedup at $k=4$). On standard G-Set and K2000 benchmarks
up to 2000 nodes pc-COP reaches near-99% average accuracy (98.49% at $N_s=1000$)
with lower FPGA resource use than prior digital annealers.

## Why it matters to Gibbsiq

- **The update rule is exactly Gibbsiq's single-site Gibbs conditional.** The BSN
  step $m_i = \mathrm{sgn}(\mathrm{rand}(-1,+1) + \tanh(\beta\gamma_i))$ over
  $m_i\in\{-1,+1\}$, with $\gamma_i = h_i + \sum_j J_{i,j} m_j$, is algebraically the
  conditional Gibbsiq audits as `sigmoid(-2 * beta * gamma_i)`. The paper's
  *sequential* sweep ("does not allow independently updating multiple p-bits in
  parallel") is precisely block-Gibbs's serial-within-block discipline, and its
  speculate-and-select trick is a hardware way to parallelize without breaking that
  dependency — directly relevant to how the THRML runtime layer schedules updates.
- **Sign and offset cross-check.** The paper's energy is the symmetric, sign-flipped
  $E = -(\sum_{i<j} J_{i,j} m_i m_j + \sum_i h_i m_i)$ with no offset; Gibbsiq uses
  $E = \text{offset} + \sum_i h_i s_i + \sum_{i<j} J_{ij} s_i s_j$. The overall minus
  sign (and the max-cut convention $J_{i,j} = -w_{i,j}$) is the kind of sign
  bookkeeping the equation audit exists to catch.
- **Geometric $\beta$-annealing is a concrete schedule for the runtime.** The
  $\beta_s = \beta_{\text{initial}}\cdot\beta_{\text{anneal-rate}}^{s-1}$ schedule
  (with the paper's tuned $(\beta_{\text{initial}}, \beta_{\text{anneal-rate}})$ pairs
  for $N_s=100$ vs $1000$) is exactly the schedule control the THRML layer must
  expose, and the per-sample energy trace it reports (Fig. 13) is the energy /
  best-so-far trace Gibbsiq's diagnostics layer consumes.
- **G-Set / K2000 max-cut is in our benchmark scope.** The G-Set table (proven /
  best-known cut values with accuracy) is a ready external baseline for the benchmark
  layer's max-cut family, against an FPGA probabilistic-computing reference point.

## Reading-list hooks

- Single-site update, local field, and Gibbs sign → project energy contract
  (`CLAUDE.md` → "Canonical conventions"), audited in
  [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).
- p-bit / BSN lineage and the foundational stochastic-unit rule →
  [`./camsari-2018-probabilistic-spin-logic.note.md`](./camsari-2018-probabilistic-spin-logic.note.md)
  and [`./camsari-2016-stochastic-pbits-invertible-logic.md`](./camsari-2016-stochastic-pbits-invertible-logic.md).
- Parallel p-bit update schemes for Ising hardware →
  [`./onizawa-2026-parallel-pbit-ising.md`](./onizawa-2026-parallel-pbit-ising.md).
- Max-cut Ising formulation used for benchmarks → Lucas 2014,
  [`./lucas-2014-ising-formulations.md`](./lucas-2014-ising-formulations.md).
