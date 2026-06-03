# Lab note — Stochastic p-Bits for Invertible Logic

> **Paper.** K. Y. Camsari, R. Faria, B. M. Sutton, and S. Datta. "Stochastic
> p-Bits for Invertible Logic." *Physical Review X* 7(3):031014 (2017).
> DOI: [10.1103/physrevx.7.031014](https://doi.org/10.1103/physrevx.7.031014) ·
> arXiv:[1610.00377](https://arxiv.org/abs/1610.00377) · BibTeX `camsari2017invertible`.
> Transcript: [`camsari-2016-stochastic-pbits-invertible-logic.md`](./camsari-2016-stochastic-pbits-invertible-logic.md).

## What the paper does

The paper introduces the *p-bit*, an unstable stochastic unit whose output follows
a tunable random number generator with a sigmoidal mean response,

$$m_i(t) = \mathrm{sgn}\!\left\{\mathrm{rand}(-1,1) + \tanh(I_i(t))\right\},$$

so that the time-averaged magnetization equals $\tanh(I_i)$. p-bits are
interconnected through the local field

$$I_i(t) = I_0\left(h_i(t) + \sum_j J_{ij}\, m_j(t)\right),$$

with $I_0$ acting as an inverse pseudo-temperature. These are exactly the defining
equations of a Boltzmann machine: under serial (asynchronous) updating the network
samples the Boltzmann distribution $P(\{m\}) \propto \exp(-E)$ of the quadratic
energy $E(\{m\}) = -I_0\left(\tfrac12\sum_{i,j} J_{ij} m_i m_j + \sum_i h_i m_i\right)$.
The authors give a one-shot prescription — no learning — for turning *any* Boolean
truth table into a symmetric, sparse, integer-quantized $[J]$ matrix by treating
truth-table rows as eigenvectors of eigenvalue $+1$, $[J] = \sum_{i,j} [S^{-1}]_{ij}\,u_i u_j^{\dagger}$
with $S_{ij} = u_i^{\dagger} u_j$. The resulting gates are *invertible*: clamping
the input yields the output, and clamping the output makes the network fluctuate
over all consistent inputs (the relation inverse). By wiring symmetric BM Full
Adders together with *directed* carry couplings ($J_{ij}\neq J_{ji}$), they build a
32-bit adder that "quenches" to the one correct sum out of $2^{33}\approx$ 8 billion
states, and a 4-bit multiplier that runs in reverse as a factorizer. A two-p-bit
master-equation model explains why directivity matters: the slow mode decays as
$\lambda_4 = \tanh(I_0 J_{12})\tanh(I_0 J_{21})$, which vanishes for a fully directed
link but approaches 1 (exponentially slow mixing) when bidirectional.

## Why it matters to Gibbsiq

- **The single-p-bit update is the Gibbsiq single-site conditional.** The rule
  $m_i = \mathrm{sgn}\{\mathrm{rand}(-1,1) + \tanh(I_i)\}$ with $I_i = I_0(h_i + \sum_j J_{ij} m_j)$
  is the spin-form Boltzmann-machine update that Gibbsiq audits as
  `sigmoid(-2 * beta * gamma_i)` over $s_i \in \{-1,+1\}$ with local field
  $\gamma_i = h_i + \sum_j J_{ij} s_j$. The paper's $I_0$ plays the role of $\beta$,
  and its symmetric $-\tfrac12 \sum_{i,j} J_{ij} m_i m_j$ energy is the double-counted
  twin of the Gibbsiq upper-triangle, no-double-count form
  $E = \text{offset} + \sum_i h_i s_i + \sum_{i<j} J_{ij} s_i s_j$ — reconciling that
  factor-of-two and the field sign is exactly what the equation audit guards.
- **Asynchronous (serial) updating is mandatory.** The paper notes that *parallel*
  updates give wrong results and only serial/random-order updates converge to the
  Boltzmann distribution. This is the THRML block-Gibbs sweep discipline: blocks
  must be conditionally independent or updates serialized, or the stationary
  distribution is corrupted.
- **Quenching $I_0$ is a sampling schedule.** Suddenly raising $I_0$ from ~0.25 to 5
  to crystallize the answer is an annealing/$\beta$-schedule — precisely the schedule
  control the THRML runtime layer (Stage 2) must expose, and a regime where the slow
  $\lambda_4$ mode predicts the kind of slow mixing Gibbsiq diagnostics flag.
- **Bidirectionality predicts mixing failure.** The two-p-bit eigenvalue analysis
  ($\lambda_4 \to 1$ for bidirectional couplings, exponentially long settling) is a
  closed-form instance of the slow-mixing / `no_recent_improvement` pathology the
  diagnostics layer detects via autocorrelation and ESS.
- **Truth-table gates are QUBO/Ising constraint encodings.** The one-shot $[J]$
  prescription that pins valid configurations as ground states is the same penalty
  idea behind Lucas-style NP-problem formulations that feed the benchmark oracle.

## Reading-list hooks

- Local-field convention and the Gibbs sign → project energy contract
  (`../../../CLAUDE.md` → "Canonical conventions"), audited in
  [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).
- The p-bit lineage and the BSN restated → companion note
  [`./camsari-2018-probabilistic-spin-logic.note.md`](./camsari-2018-probabilistic-spin-logic.note.md).
- NP-problem Ising/QUBO formulations used by the benchmark oracle → Lucas 2014,
  [`./lucas-2014-ising-formulations.md`](./lucas-2014-ising-formulations.md).
