# Lab note — Extended-variable probabilistic computing with p-dits

> **Paper.** C. Duffee, J. Athas, A. Grimaldi, D. Volpe, G. Finocchio, E. Wei, and
> P. Khalili Amiri. "Extended-variable probabilistic computing with p-dits."
> arXiv:[2506.00269](https://arxiv.org/abs/2506.00269) (2025) · BibTeX `duffee2025pdits`.
> Transcript: [`camsari-2025-pdits-extended-variable.md`](./camsari-2025-pdits-extended-variable.md).

## What the paper does

The paper generalizes the binary p-bit to a *probabilistic d-dimensional variable*
(p-dit) that stochastically oscillates among $d$ discrete states
$s_i \in \{0,1,\ldots,d-1\}$. The system energy is the multi-state Ising form
$H = -\sum_{i<j}\sum_{\alpha,\beta} J_{ij}^{\alpha\beta}\,\delta(s_i-\alpha)\,\delta(s_j-\beta) - \sum_i\sum_\alpha h_i^{\alpha}\,\delta(s_i-\alpha)$,
and each variable is resampled with a softmax conditional that generalizes the
binary sigmoid update,

$$P\bigl(s_i(t+1)=\alpha\bigr) = \frac{\exp(-\beta\,E_i^{\alpha})}{\sum_{\gamma=0}^{d-1}\exp(-\beta\,E_i^{\gamma})},$$

where $E_i^{\alpha}$ is the local energy of p-dit $i$ in state $\alpha$. Two
restrictions are studied: *isotropic p-dits*, where all cross-state couplings are
equal ($J_{ij}^{\alpha\beta}=J_{ij}$ for $\alpha\neq\beta$, $J_{ij}^{\alpha\alpha}=0$),
giving an unbiased categorical variable that — unlike one-hot p-bit groups — is
*never* in an invalid configuration; and *probabilistic integers* (p-ints), which
encode ordered numeric values with regular steps so that adjacent integers are not
separated by the energy barriers a binary encoding introduces.

The authors fabricate a Skywater 130 nm CMOS ASIC (576 p-bit cells, co-integrated
RISC-V) that completes a full probabilistic iteration in two clock cycles, and add
two formulation tricks for inequality constraints: *violation variables* (0 when
satisfied, $-1$ when violated; they break the symmetry of the $J$ matrix and leave
much of it zero, so it need not be stored) replacing classical slack variables, and
*scaled sampling* that visits each p-int proportionally to its range. Benchmarks
report roughly $34\times$ (3-partition, isotropic p-dits vs. p-bits), $5.3\times$
(change-making ILP, p-ints vs. p-bits), $10\times$ (fixed-charge ILP, violation +
scaled vs. slack + even), and $64\times$ (non-convex 17-variable IQP on FPGA vs. the
best GAMS software solver) improvements in trials- or time-to-solution.

## Why it matters to Gibbsiq

- **Categorical and integer encoding pressure on the interface/IR.** Gibbsiq's IR is
  binary spin Ising ($s_i\in\{-1,+1\}$); this paper quantifies the cost the IR pays
  for multi-valued variables — one-hot needs $d$ p-bits plus a one-hot penalty,
  binary encoding needs $\lceil\log_2 d\rceil$ p-bits with barriers between adjacent
  integers. It is the reference for *why* the penalty weights and offset that
  QUBO/BQM ingestion bakes in matter, and what a native d-state representation would
  save (Table 1: 42 p-bits vs. 14 p-dits for 3-partition).
- **The softmax update is the d-state generalization of our Gibbs conditional.** The
  binary special case of Eq. (5) is exactly Gibbsiq's audited single-site rule
  `sigmoid(-2 * beta * gamma_i)` with $\gamma_i = h_i + \sum_j J_{ij}s_j$; the paper
  shows the categorical/multinomial form the THRML block-Gibbs runtime (layer 2)
  would need for non-binary blocks, and the $\beta$ schedules it sweeps are the
  schedule controls that layer must expose.
- **Penalty handling for inequalities — a candidate convention for the IR.** Violation
  variables and slack variables are two offset-preserving ways to fold inequality
  constraints into the Ising Hamiltonian; the claim that violation variables avoid
  distorting the energy landscape into hard-to-escape minima is directly relevant to
  Gibbsiq's penalty/offset bookkeeping and to the mode-collapse / no-improvement
  failure flags in the diagnostics layer (layer 3).
- **Benchmark formulations and baselines.** Partition, change-making ILP,
  fixed-charge ILP, and non-convex IQP are NP-formulations in Gibbsiq's benchmark
  scope; the GAMS/MOSEK comparison points are the kind of external software baseline
  the benchmark layer (layer 5) runs the THRML sampler against under matched seeds.

## Reading-list hooks

- Single-site Gibbs sign and local-field convention → `CLAUDE.md` → "Canonical
  conventions", audited in
  [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).
- The binary p-bit this paper extends →
  [`./camsari-2018-probabilistic-spin-logic.note.md`](./camsari-2018-probabilistic-spin-logic.note.md)
  and [`./camsari-2016-stochastic-pbits-invertible-logic.md`](./camsari-2016-stochastic-pbits-invertible-logic.md).
- NP-problem Ising formulations (partition, knapsack/ILP-style encodings) used for
  benchmarks → Lucas 2014,
  [`./lucas-2014-ising-formulations.md`](./lucas-2014-ising-formulations.md).
- Follow-on p-dit work on the quadratic assignment problem →
  [`./duffee-2026-pdit-ising-qap.md`](./duffee-2026-pdit-ising-qap.md).
