# Lab note — p-Bits for Probabilistic Spin Logic

> **Paper.** K. Y. Camsari, B. M. Sutton, and S. Datta. "p-bits for probabilistic
> spin logic." *Applied Physics Reviews* 6(1):011305 (2019).
> DOI: [10.1063/1.5055860](https://doi.org/10.1063/1.5055860) ·
> arXiv:[1809.04028](https://arxiv.org/abs/1809.04028) · BibTeX `camsari2019pbits`.
> Full transcript: [`camsari-2018-probabilistic-spin-logic.md`](./camsari-2018-probabilistic-spin-logic.md).

## What the paper does

The paper introduces the *p-bit*, a classical unit that fluctuates rapidly between
0 and 1, positioned between the deterministic bit and the quantum q-bit. Its
behaviour is the binary stochastic neuron (BSN): given a normalized input $I_i$,
the output is

$$m_i = \mathrm{sgn}\!\left[\tanh(I_i) - r\right], \qquad r \sim U(-1, 1),$$

so that $\langle m_i \rangle = \tanh(I_i)$. A network of $N$ p-bits coupled by a
weight matrix $[W]$ and bias $\{h\}$ runs an interleaved update — each p-bit reads
its local field $I_i = \beta\big(h_i + \sum_j W_{ij} m_j\big)$ and resamples — and
the stationary distribution is the Boltzmann distribution of

$$E(\{m\}) = -\tfrac{1}{2}\,\{m\}^{\mathsf T}[W]\{m\} - \{h\}^{\mathsf T}\{m\}.$$

The authors give a physical realization (low-barrier magnets + a transistor, the
1T/MTJ cell) and demonstrate, in SPICE, p-circuits solving optimization problems,
invertible Boolean logic, and a simulated-annealing travelling-salesman instance.

## Why it matters to Gibbsiq

This is the foundational reference for the probabilistic-computing lineage that
Gibbsiq's THRML substrate descends from. Three concrete links:

- **The single-unit update is our single-site Gibbs conditional.** The BSN rule
  $m_i = \mathrm{sgn}[\tanh(I_i) - r]$ with $I_i = \beta\,\gamma_i$ is algebraically
  the conditional Gibbsiq audits as `sigmoid(-2 * beta * gamma_i)` over
  $s_i \in \{-1,+1\}$, with local field $\gamma_i = h_i + \sum_j J_{ij} s_j$. The
  paper works in the $m_i \in \{-1,+1\}$ ("spin") convention and the symmetric
  $-\tfrac12 \{m\}^{\mathsf T}[W]\{m\}$ energy; Gibbsiq uses the upper-triangle,
  no-double-count form $E = \text{offset} + \sum_i h_i s_i + \sum_{i<j} J_{ij} s_i s_j$.
  Reconciling the factor-of-two and the sign between these two conventions is
  exactly the kind of bug the equation audit guards against — this paper is a useful
  cross-check on that sign.
- **The energy framing is our Ising convention.** Sampling the Boltzmann
  distribution of a quadratic spin energy *is* the Gibbsiq contract; the paper is the
  hardware-side statement of the same object Gibbsiq lowers QUBO/BQM problems into.
- **The annealing TSP example is in our benchmark scope.** The paper's
  simulated-annealing TSP demonstration (Fig. 8, raising $\beta$ over time) is one of
  the NP-problem formulations Gibbsiq benchmarks; the $\beta$-schedule it uses is the
  schedule control the THRML runtime layer must expose.

## Reading-list hooks

- Single-site/local-field convention and Gibbs sign → project energy contract
  (`CLAUDE.md` → "Canonical conventions"), audited in
  [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).
- Probabilistic-computing background and the p-bit lineage →
  [`../probabilistic-computing-and-pbits.md`](../probabilistic-computing-and-pbits.md).
- NP-problem Ising formulations (incl. TSP) used for benchmarks → Lucas 2014,
  [`./lucas-2014-ising-formulations.md`](./lucas-2014-ising-formulations.md).
