# Gibbsiq: THRML-Native Optimization Infrastructure for QUBO and Ising Models

## Abstract

Combinatorial optimization problems such as maximum cut, number partitioning, and the travelling salesman problem can be expressed as quadratic unconstrained binary optimization (QUBO) or as ground-state search over an Ising energy function. THRML provides a JAX-based block-sampling substrate that its official documentation describes as a GPU simulator for programs intended for future Extropic hardware. Gibbsiq is the optimization and audit layer above that substrate. The implemented core compiles QUBO, Ising, and binary quadratic models (BQM), lowers the canonical Ising representation into THRML programs, records raw traces and diagnostics, runs a verified opt-in parallel-tempering path, independently checks small Gibbs kernels, verifies benchmark witnesses, and emits artifact-only Inspector summaries. Classical-baseline runners and full Inspector/HTML integration remain absent.

The project is THRML-first. Diagnostics are required, but the execution target is THRML. The intended contribution is a reusable optimization stack with five parts: audited model conversion, graph-aware block construction, schedule and seed control, multi-chain trace capture, and benchmark oracles that recompute objective values from witness states. Positioned by analogy, Gibbsiq is to THRML what Ocean and dimod are to D-Wave and what ArviZ is to Stan and PyMC: the ingestion, runtime-contract, diagnostics, and independent-verification layer above the sampling substrate. The general programming layer for thermodynamic sampling units is THRML itself; Gibbsiq occupies the optimization and trust layer above it.

ThermoMap is the compiler, auto-mapping, verification, and thermodynamic-roofline capability
track inside Gibbsiq. It is not a separate installed package. The live implementation plan is
[the autonomous roadmap](reference/00-roadmap/autonomous-implementation-roadmap.md).

**Keywords:** combinatorial optimization, QUBO, Ising model, block-Gibbs sampling, thermodynamic computing, convergence diagnostics

---

## 1. Introduction

Combinatorial optimization is central to operations research, scheduling, routing, and scientific search, and a large class of such problems can be cast as quadratic unconstrained binary optimization. Computing the ground state of a general Ising model is NP-hard [1], so exact minimization is intractable at scale and practical solvers draw samples biased toward low energy rather than certifying optima. A broad family of physical and classical machines pursues this objective, including quantum annealers [4, 5, 6], coherent Ising machines [8], simulated bifurcation [9], digital annealers [10], and probabilistic (p-bit) Ising machines [11, 12].

For these solvers, the algorithmic primitive relevant to Gibbsiq is Gibbs sampling: an MCMC method that updates each variable according to its conditional distribution given the state of its neighbors. This locality is hardware-relevant. In a sparse Ising graph, each spin depends only on a small neighborhood, which is the structure that THRML and proposed thermodynamic-sampling architectures represent through graph-colored block updates.

THRML is lower-level than an optimization SDK. A user starting from a QUBO or BQM should not have to hand-build `SpinNode` graphs, block partitions, schedules, trace capture, benchmark accounting, and convention checks for every experiment. Gibbsiq provides that translation and audit layer. Its durable contribution is independent verification: audited conversion, sampler-health diagnostics, and witness-recomputing benchmark oracles that a hardware vendor cannot credibly supply for its own device. Model ingestion and lowering may in time be absorbed by an Extropic-owned optimization SDK; the verification and diagnostics contracts are the part that survives that.

The second observation motivating this work is that a best energy alone cannot characterize a stochastic optimization run. A reported best energy can come from a collapsed distribution, a single chain trapped in one basin, a cooling schedule that mixed poorly, or penalty weights that make infeasible states artificially cheap. The Bayesian computation community supplies statistics such as $\widehat{R}$ and effective sample size [15, 16, 17], and current dimod documentation also exposes ESS helpers for arrays and `SampleSet` objects. Gibbsiq's narrower contribution is the combined audit contract: conversion checks, explicit degenerate diagnostic states, raw traces, anti-echo evaluation, and witness recomputation.

The implemented and planned contributions are:

1. Implemented: a problem interface that ingests QUBO, Ising, and BQM models into a single internal Ising representation with deterministic variable ordering and offset-preserving conversion.
2. Implemented: a THRML optimization runtime that lowers this representation into THRML nodes, factors, graph-colored blocks, sampling programs, schedules, seeds, initialization policies, and trace capture, validated by exhaustive small-instance comparison against analytic Boltzmann probabilities. The 2026-07-14 verification closes the opt-in parallel-tempering correctness criterion. Device-side/vectorized exchange and adaptive ladders remain performance extensions.
3. Implemented: a diagnostics layer that reports autocorrelation and integrated autocorrelation time, raw-energy effective sample size, plain and rank-normalized between-chain disagreement, diversity, and explicit statuses for each THRML run. The formulas retain their ArviZ and R-`posterior` cross-checks. The verified semantic correction removes the unsupported raw-ESS threshold, names occupancy efficiency accurately, and separates observations from failures. Rank-normalized bulk/tail ESS and general constraint feasibility remain future work.
4. Partly implemented: a benchmark harness that scores candidate runs against exact enumeration under witness recomputation, with later classical-baseline comparisons under matched seeds and resource budgets.
5. Partly implemented: the ThermoMap analysis foundation, including provenanced abstract target facts, fixed-point coefficient quantization, exact small-law comparison, logical target admissibility, pairwise categorical/domain-wall lowering, and supplied-partition communication proxies. Automatic partitioning, placement, routing, calibrated cost models, and physical TSU execution remain future work.

This document reviews QUBO and Ising formulations, the sampling-based solvers that target them, convergence diagnostics from the MCMC literature, the Gibbsiq architecture, and the current implementation.

---

## 2. Background

### 2.1 QUBO and Ising Models

An Ising model defines a probability distribution over spin configurations $\mathbf{s} \in \{-1, +1\}^n$ via an energy function $E(\mathbf{s})$:

$$
p(\mathbf{s}) = \frac{1}{Z} \exp(-\beta E(\mathbf{s}))
$$

where $Z$ is the partition function and $\beta$ is an inverse-temperature parameter. We adopt the energy convention

$$
E(\mathbf{s}) = \mathrm{offset} + \sum_i h_i s_i + \sum_{i \lt j} J_{ij} s_i s_j
$$

with linear fields $h_i$, upper-triangular couplings $J_{ij}$, and a constant offset that is preserved through every conversion. Many discrete optimization tasks are equivalently written as quadratic unconstrained binary optimization,

$$
\min_{\mathbf{x} \in \{0,1\}^n} \mathbf{x}^\top Q \mathbf{x}
$$

This is mapped to the Ising form by the substitution $\mathbf{s} = 2\mathbf{x} - \mathbf{1}$. Barahona [1] established that finding the ground state of a general Ising spin glass is NP-hard. Lucas [2] gave explicit, polynomial-size Ising formulations for Karp's 21 NP-complete problems, supplying the reductions on which our benchmark corpus draws, while Glover, Kochenberger, and Du [3] surveyed QUBO as a unifying model and catalogued the penalty constructions that absorb hard constraints into the objective.

### 2.2 Sampling-Based Ising Solvers

One line of work encodes the objective as a quantum Hamiltonian and drives the system toward its ground state. Kadowaki and Nishimori [4] introduced quantum annealing in the transverse-field Ising model, Farhi et al. [5] framed adiabatic quantum optimization for NP-complete problems, and Johnson et al. [6] demonstrated programmable quantum annealing on superconducting flux qubits. The superconducting implementation in [6] requires cryogenic operation; this repository makes no facility-energy comparison from that fact.

A parallel family of classical and analog Ising machines pursues the same objective at or near room temperature. Simulated annealing [7] remains the reference heuristic; coherent Ising machines realize spins as optical parametric oscillators [8]; simulated bifurcation reformulates the search as the adiabatic evolution of a classical nonlinear Hamiltonian system [9]; and application-specific digital hardware accelerates parallel-trial annealing on CMOS [10]. These machines motivate the classical baselines against which we score our runs.

Probabilistic computing replaces the deterministic bit with the p-bit, a unit that fluctuates between states under controllable noise. Camsari et al. [11] formalized stochastic p-bits and their use in invertible logic, and Aadit et al. [12] demonstrated massively parallel probabilistic computing with sparse Ising machines. Operating temperature is an implementation-specific device property; using noise as a computational resource does not establish it. Jelinčič et al. [13] describe an all-transistor thermodynamic sampling architecture for diffusion-like models and report a system-level projected energy advantage for that setting. Gibbsiq does not treat those hardware projections as evidence of QUBO optimization speedup. The accompanying open-source JAX runtime, [THRML](https://github.com/extropic-ai/thrml), performs GPU-accelerated block-Gibbs sampling on sparse factor graphs and simulates future hardware programs; we target THRML as our execution substrate.

### 2.3 Gibbs Sampling and Convergence Diagnostics

Block-Gibbs sampling, the primitive THRML exposes, originates in the stochastic-relaxation work of Geman and Geman [14]. For a single spin, the algorithm draws from the conditional

$$
P(s_i = +1 \mid \mathbf{s}_{\neg i}) = \sigma(-2 \beta \gamma_i), \qquad \gamma_i = h_i + \sum_j J_{ij} s_j
$$

where $\sigma$ is the logistic sigmoid and $\gamma_i$ is the local field at site $i$. Because the sampler returns a distribution rather than a point, its output inherits the reliability concerns of MCMC. Gelman and Rubin [15] introduced the potential-scale-reduction statistic $\widehat{R}$, which contrasts within-chain and between-chain variance to detect non-convergence; Geyer [16] formalized autocorrelation-based effective-sample-size estimation; and Vehtari et al. [17] provided a rank-normalized $\widehat{R}$ and effective-sample-size estimators that remain valid under heavy tails and non-stationary variance. We carry these diagnostics into the combinatorial-optimization sampling loop.

---

## 3. System Design

Gibbsiq is organized as five product layers. The interface layer ingests QUBO, Ising, and dimod BQM inputs, normalizes them into one internal Ising representation with deterministic variable ordering and offset-preserving conversion, and decodes solutions back to user variables. The THRML optimization runtime lowers that representation into THRML nodes, blocks, factors, programs, schedules, seeds, and initialization policies, then captures raw state and energy traces. The diagnostics layer computes energy and best-so-far traces, autocorrelation, effective-sample-size estimates, between-chain disagreement, solution diversity (unique fraction, top-$k$ mass, entropy, Hamming spread), and explicit failure flags; its constraint section currently reports `not_available`. The target Inspector layer presents topology, trace summaries, warnings, best states, and baseline comparisons. The benchmark layer currently supplies exact witness verification and is intended to compare THRML-backed runs with classical baselines under matched seeds and separate fixed-work and fixed-time budgets. ThermoMap adds compiler, physical-mapping, verification, and roofline capabilities across these layers.

dimod compatibility lets users bring existing QUBO/BQM workloads into the THRML path and compare the result against established baselines. It is an interoperability bridge, not a change in execution target.

The runtime contracts — the `SampleResult` schema, the diagnostic inputs, and the witness-recomputing benchmark oracle — are specified to be backend-portable at the architectural level. Execution stays THRML-first; the portability is a hedge, not a backend-agnostic product. If the THRML hardware path is delayed, the same audited artifacts carry over to the wider Ising-machine field.

The data path is:

```text
QUBO/BQM/Ising
-> IsingModel
-> audited private THRML lowering
-> SampleResult
-> Diagnostics
-> Inspector / benchmark report
```

Gibbsiq does not currently claim that THRML is faster than classical or GPU baselines, and it does not treat R-hat, ESS, or diversity as proof of optimality. The implemented scope comprises conversion, fixed-beta and parallel-tempering runtime lowering, graph-colored blocks, schedule and seed controls, raw multi-chain traces, diagnostics, witness-verified benchmark scoring, an independent small-state verifier, a complete provenanced target-fact schema, an artifact-only Inspector core, bounded cubic/knapsack/TSP lowerings, and the partial ThermoMap analysis surface described above. General constraint encoding, automatic physical mapping, calibrated cost models, classical-baseline runners, and full Inspector/HTML integration remain to be built.

The implemented Stage 4 core is artifact-only. Browser display and unified HTML/CLI integration
remain future work.

```python
model  = compile_qubo(problem)
result = THRMLSampler(config).sample(model, num_reads=128)
report = Inspector.from_result(result, model=model)
print(report.to_markdown())
```

## 4. Usage and Installation

```python
from gibbsiq import compile_qubo, compile_ising

# QUBO as {(i, j): coefficient}; diagonal (i, i) entries are linear (binary) terms.
model = compile_qubo({(0, 0): -1.0, (1, 1): -1.0, (0, 1): 2.0})
model.energy({0: 1, 1: 0}, vartype="BINARY")               # returns -1.0
model.conditional_probability(0, {0: 1, 1: 1}, beta=1.0)   # P(s_0 = +1 | rest)
model.offset                                               # offset preserved through conversion

compile_ising({0: 0.5}, {(0, 1): -1.0}).energy({0: 1, 1: 1})   # returns -0.5
```

To run THRML-backed optimization, install the THRML runtime extra and use the sampler:

```python
from gibbsiq import SamplerConfig, THRMLSampler, compile_qubo

model = compile_qubo({(0, 0): -1.0, (1, 1): -1.0, (0, 1): 2.0})
config = SamplerConfig(beta=2.0, n_warmup=50, warmup_beta_ladder=(0.5, 1.0, 2.0), num_chains=2, seed=0)
result = THRMLSampler(config).sample(model, num_reads=128)
print(result.best_energy)       # -1.0
print(result.traces["energy"])  # per-chain energy traces
print(result.metadata["num_blocks"])  # DSATUR block count
```

The current public ThermoMap analysis surface remains under `gibbsiq`:

```python
from gibbsiq import (
    GridTopology,
    Inspector,
    ReferenceGibbsSampler,
    ReferenceSamplerConfig,
    FixedPointSpec,
    TSUSpec,
    analyze_quantization,
    assess_target_admissibility,
    build_exact_transition_kernel,
    exact_boltzmann_distribution,
    verify_transition_kernel,
)
```

The proposed one-call `compile_model`, `profile`, and `verify` orchestration APIs remain roadmap
targets.

```bash
# JSON fixture evaluator and test suite
gibbsiq-evaluate ./test_suite/examples/evaluation-candidate.example.json
PYTHONPATH=src python -m unittest discover -s test_suite/tests
```

Requires Python 3.10 or later. The core package has no required dependencies and uses only the standard library. `dimod` is optional, needed only for `to_dimod()` interoperability and the dimod conformance tests, which are skipped when it is absent.

```bash
pip install -e .                    # core (zero runtime dependencies)
pip install -e ".[dimod]"           # core plus dimod interoperability
pip install -e ".[thrml]"           # core plus THRML sampler (enables THRMLSampler)
pip install -e ".[dev]"             # full test suite
```

On Windows PowerShell, set `$env:PYTHONPATH = "src"` before the module invocations above.

Additional reference material:

- [Glossary](reference/glossary.md)
- [Claims evidence map](reference/claims-evidence-map.md)
- [Technical specification](spec.md)
- [Stage 2 THRML optimization runtime](reference/00-roadmap/stage-02-thrml-optimization-runtime.md)
- [THRML runtime notes](reference/03-samplers/thrml-optimization-runtime.md)

---

## References

[1] F. Barahona. On the computational complexity of Ising spin glass models. *Journal of Physics A: Mathematical and General*, 15(10):3241–3253, 1982.

[2] A. Lucas. Ising formulations of many NP problems. *Frontiers in Physics*, 2:5, 2014.

[3] F. Glover, G. Kochenberger, and Y. Du. Quantum Bridge Analytics I: a tutorial on formulating and using QUBO models. *4OR*, 17:335–371, 2019.

[4] T. Kadowaki and H. Nishimori. Quantum annealing in the transverse Ising model. *Physical Review E*, 58(5):5355–5363, 1998.

[5] E. Farhi, J. Goldstone, S. Gutmann, J. Lapan, A. Lundgren, and D. Preda. A quantum adiabatic evolution algorithm applied to random instances of an NP-complete problem. *Science*, 292(5516):472–475, 2001.

[6] M. W. Johnson, M. H. S. Amin, S. Gildert, et al. Quantum annealing with manufactured spins. *Nature*, 473:194–198, 2011.

[7] S. Kirkpatrick, C. D. Gelatt, and M. P. Vecchi. Optimization by simulated annealing. *Science*, 220(4598):671–680, 1983.

[8] P. L. McMahon, A. Marandi, Y. Haribara, et al. A fully programmable 100-spin coherent Ising machine with all-to-all connections. *Science*, 354(6312):614–617, 2016.

[9] H. Goto, K. Tatsumura, and A. R. Dixon. Combinatorial optimization by simulating adiabatic bifurcations in nonlinear Hamiltonian systems. *Science Advances*, 5(4):eaav2372, 2019.

[10] M. Aramon, G. Rosenberg, E. Valiante, T. Miyazawa, H. Tamura, and H. G. Katzgraber. Physics-inspired optimization for quadratic unconstrained problems using a digital annealer. *Frontiers in Physics*, 7:48, 2019.

[11] K. Y. Camsari, R. Faria, B. M. Sutton, and S. Datta. Stochastic p-bits for invertible logic. *Physical Review X*, 7(3):031014, 2017.

[12] N. A. Aadit, A. Grimaldi, M. Carpentieri, et al. Massively parallel probabilistic computing with sparse Ising machines. *Nature Electronics*, 5:460–468, 2022.

[13] A. Jelinčič, O. Lockwood, A. Garlapati, P. Schillinger, I. Chuang, G. Verdon, and T. McCourt. An efficient probabilistic hardware architecture for diffusion-like models. arXiv:2510.23972, 2025.

[14] S. Geman and D. Geman. Stochastic relaxation, Gibbs distributions, and the Bayesian restoration of images. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 6(6):721–741, 1984.

[15] A. Gelman and D. B. Rubin. Inference from iterative simulation using multiple sequences. *Statistical Science*, 7(4):457–472, 1992.

[16] C. J. Geyer. Practical Markov chain Monte Carlo. *Statistical Science*, 7(4):473–483, 1992.

[17] A. Vehtari, A. Gelman, D. Simpson, B. Carpenter, and P.-C. Bürkner. Rank-normalization, folding, and localization: an improved $\widehat{R}$ for assessing convergence of MCMC. *Bayesian Analysis*, 16(2):667–718, 2021.
