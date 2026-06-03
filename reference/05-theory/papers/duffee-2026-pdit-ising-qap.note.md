# Lab note — P-dit Probabilistic Ising Machine for the Quadratic Assignment Problem

> **Paper.** C. Duffee, C. M. Burling-Smith, J. Athas, A. Grimaldi, G. Finocchio,
> E. Wei, and P. K. Amiri. "P-dit Probabilistic Ising Machine for Solving the
> Quadratic Assignment Problem." arXiv preprint, 2026.
> arXiv:[2605.24408](https://arxiv.org/abs/2605.24408) · BibTeX `duffee2026qap`.
> Transcript: [`duffee-2026-pdit-ising-qap.md`](./duffee-2026-pdit-ising-qap.md).

## What the paper does

The paper maps the quadratic assignment problem (QAP) — placing $N$ facilities at
$N$ locations to minimize $\min_p \sum_{i=1}^{N}\sum_{j=1}^{N} D_{ij} F_{p(i)p(j)}$,
where $D$ is the distance matrix and $F$ the flow matrix — onto a probabilistic
Ising machine (PIM) built from *p-dits* rather than binary p-bits. A p-dit is a
multi-state variable holding a unit vector along one of $d$ dimensions; here each of
the $N$ p-dits represents a location and points at the facility currently assigned to
it. Because every p-dit is initialized to a distinct dimension and updates only ever
*swap* assignments between two p-dits, the permutation constraint is satisfied by
construction — no penalty energy terms are needed to forbid two locations sharing a
facility. The force on location $i$ toward facility $a$ is
$I_i^a = -\sum_j D_{ij} F_{a,p(j)} + D_{ji} F_{p(j),a}$, and a candidate swap of p-dits
$i$ and $j$ (dimensions $a,b$) has energy change
$\Delta E_{i\leftrightarrow j}^{a\leftrightarrow b} = -(I_i^b - I_i^a + I_j^a - I_j^b)$
for symmetric zero-diagonal $D$. Each swap is accepted with the softmax probability

$$P(i \leftrightarrow j) = \frac{\exp\!\left(-\beta\,\Delta E_{i\leftrightarrow j}^{p(i)\leftrightarrow p(j)}\right)}{\sum_{k=1}^{n} \exp\!\left(-\beta\,\Delta E_{i\leftrightarrow k}^{p(i)\leftrightarrow p(k)}\right)},$$

scaled by inverse temperature $\beta$. Parallel tempering across replicas at
multiplicatively spaced $\beta$ values (with an automatic $\beta$-range sweep and a
forced low/high swap to escape frozen replicas) drives mixing. On QAPLIB the CPU-PIM
finds the best-known solution on 121 of 127 instances versus 46 for Gurobi under
matched runtime/CPU, with two-to-three-order-of-magnitude speedups on the largest
instance (tai256c); GPU implementations parallelize across replicas and, in the
concurrent-update variant, trade some convergence fidelity for throughput.

## Why it matters to Gibbsiq

- **A constraint-by-construction alternative to penalty encoding.** Where Gibbsiq's
  interface/IR encodes QAP/permutation problems as QUBO with penalty terms (Lucas-2014
  style), this paper keeps the permutation feasible by only swapping multi-state p-dit
  assignments. It is the strongest argument in the reference pack for treating
  feasibility-preserving moves as a first-class option, and a caution that naive
  one-hot QUBO encodings inflate both variable count and the offset/penalty bookkeeping
  the IR must preserve.
- **The swap acceptance rule is a tempered, multi-state Gibbs kernel.** The softmax over
  $-\beta\,\Delta E$ is the categorical analogue of Gibbsiq's single-site conditional
  `sigmoid(-2 * beta * gamma_i)`; the local "force" $I_i^a$ plays the role of the local
  field $\gamma_i$. This is a useful cross-check for the THRML block-Gibbs runtime
  (layer 2) when it lowers structured problems whose blocks are categorical rather than
  binary.
- **Parallel tempering and the $\beta$-sweep are schedule controls the runtime owes.**
  The replica ladder, the 4-iterations-between-swaps cadence, and the automatic
  $\beta$-range selection are exactly the schedule/seed/replica knobs the THRML runtime
  layer must expose, and the symptoms they fight (replicas frozen in local minima) are
  what the diagnostics layer flags as `mode_collapse` / `no_recent_improvement`.
- **A concrete benchmark target and baseline set.** QAPLIB instances with proven
  best-known values, plus the Gurobi / CPTS / PHA / BLS comparison table, fit directly
  into the benchmark layer's "best-known with recorded source" rule and the
  exact/heuristic baseline comparisons.

## Reading-list hooks

- p-dit definition and extended-variable probabilistic computing →
  [`./camsari-2025-pdits-extended-variable.md`](./camsari-2025-pdits-extended-variable.md).
- p-bit lineage and the binary-stochastic-neuron update this generalizes →
  [`./camsari-2018-probabilistic-spin-logic.note.md`](./camsari-2018-probabilistic-spin-logic.note.md),
  [`../probabilistic-computing-and-pbits.md`](../probabilistic-computing-and-pbits.md).
- NP-problem Ising/QUBO formulations (QAP as permutation/assignment) for the
  benchmark layer → [`./lucas-2014-ising-formulations.md`](./lucas-2014-ising-formulations.md).
- Gibbs sign, local field, and offset/penalty handling → `CLAUDE.md` →
  "Canonical conventions", audited in
  [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).
