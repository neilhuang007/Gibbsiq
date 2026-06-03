# Lab note — Penalty Weights in QUBO Formulations: Permutation Problems

> **Paper.** M. Ayodele. "Penalty Weights in QUBO Formulations: Permutation
> Problems." *Lecture Notes in Computer Science*, 2022, pp. 159–174.
> DOI: [10.1007/978-3-031-04148-8_11](https://doi.org/10.1007/978-3-031-04148-8_11) ·
> BibTeX `ayodele2022`.
> Transcript: [`ayodele-2022-penalty-weights-permutation.md`](./ayodele-2022-penalty-weights-permutation.md).

## What the paper does

The paper studies how to choose the penalty weight $\alpha$ when a *constrained*
permutation problem (TSP, QAP) is folded into an unconstrained QUBO of the form
$E(x) = c(x) + \alpha\, g(x)$, where $c$ is the cost and $g$ is a non-negative
two-way one-hot constraint penalty that is $0$ on feasible solutions and $>0$
otherwise. A weight is *valid* exactly when the optimum stays feasible, which
the author formalises as

$$\alpha > \max_{x \in S} \frac{c(y) - c(x)}{g(x)},$$

with $y$ the constrained optimum and $S$ the infeasible set. Because that ratio
cannot be enumerated in practice, the paper surveys cheap upper bounds — the
all-ones upper bound (UB), the maximum QUBO coefficient (MQC), and Verma–Lewis's
single-flip gain estimate (VLM) — and then proposes two refinements that divide
the VLM numerator by the smallest achievable change in the constraint function.
The key observation is that for two-way one-hot encodings any single flip away
from a feasible state changes $g$ by exactly $2$, so $\mathrm{MOMC} =
\max(1, \mathrm{VLM}/2)$ roughly halves VLM, while MOC takes the per-variable
maximum of $|W_i^c / W_i^g|$. Running these on a CPU model of Fujitsu's
single-flip Digital Annealer over TSPLIB/QAPLIB instances, the paper finds the
*smallest valid* weight consistently gives the best solution quality (MQC for
TSP, MOC for QAP), because over-large penalties flatten the landscape and starve
the search of the infeasible stepping-stones it needs.

## Why it matters to Gibbsiq

- **It is the design reference for the interface/IR penalty layer.** Gibbsiq's
  layer 1 ingests constrained problems and must lower them into a single Ising/QUBO
  IR; this paper is the concrete recipe for the $\alpha$ that multiplies the
  constraint block, and its UB/MQC/VLM/MOMC/MOC methods are exactly the kind of
  penalty estimators that layer should offer rather than leaving $\alpha$ to the
  caller.
- **Penalty weight is an offset/coefficient contract, not a free knob.** Folding
  $\alpha\,g(x)$ into the cost shifts both the quadratic coefficients and the
  constant term; under Gibbsiq's convention
  $E(s) = \text{offset} + \sum_i h_i s_i + \sum_{i<j} J_{ij} s_i s_j$ that constant
  is the `offset` that must be preserved through QUBO↔Ising conversion. A penalty
  encoding that silently drops it is the kind of offset bug the equation audit
  guards against.
- **"Smallest valid weight wins" is a diagnostics story.** The paper's mechanism —
  too-large penalties suppress the feasible-region exploration a single-flip
  sampler needs — is precisely what Gibbsiq's diagnostics layer should surface:
  feasibility fraction, lack of diversity, and stalled improvement under an
  over-weighted constraint are observable failure signatures, and the recomputed
  feasibility check echoes the benchmark oracle's refusal to trust self-reported
  numbers.
- **TSP/QAP two-way one-hot is in benchmark scope.** The permutation-matrix
  formulation and the proven TSPLIB/QAPLIB optima give ready feasibility-and-optimality
  fixtures for the benchmark layer, complementing the Lucas 2014 formulations.

## Reading-list hooks

- QUBO/BQM ingest and offset preservation → `CLAUDE.md` → "Canonical conventions"
  and "Architecture (target design)" layer 1; offset handling audited in
  [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).
- Companion QUBO-construction tooling that emits these penalty terms →
  [`./zaman-2021-pyqubo.md`](./zaman-2021-pyqubo.md) and
  [`./mucke-2025-qubolite.md`](./mucke-2025-qubolite.md).
- Canonical NP-problem Ising formulations (TSP, QAP-adjacent) used for benchmarks →
  Lucas 2014, [`../../05-theory/papers/lucas-2014-ising-formulations.md`](../../05-theory/papers/lucas-2014-ising-formulations.md).
- Benchmark dataset catalog (proven optima, feasibility re-verification) →
  [`../../06-benchmarks/ground-truth-datasets.md`](../../06-benchmarks/ground-truth-datasets.md).
