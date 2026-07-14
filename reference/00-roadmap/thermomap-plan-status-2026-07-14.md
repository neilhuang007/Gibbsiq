# ThermoMap Plan Status — 2026-07-14

## Paper Hook

This status audit feeds the system-boundary, limitations, and future-work sections of the
Gibbsiq paper. It distinguishes the implemented THRML optimization and trust substrate from
the proposed ThermoMap compiler and thermodynamic-roofline system, and it defines the
evidence required before a compiler or hardware-performance claim receives completion credit.

## Status Basis And Authority

This document is the frozen repository-state assessment for commit `c62169e`, observed on
2026-07-14. It preserves the baseline, rubric, evidence, and score at that commit. The live
status index is `reference/00-roadmap/README.md`; the live dependency order is
`reference/00-roadmap/autonomous-implementation-roadmap.md`; agent execution rules and the
authorized next task are `reference/00-roadmap/autonomous-agent-runbook.md` and
`reference/00-roadmap/NEXT_TASK.md`. `AGENTS.md`, `spec.md`, `CLAUDE.md`, and the equation audit
remain binding for conventions and workflow.

The baseline score includes production behavior and tests present before the paper-grounded
implementation tranche and remains frozen at 30%. The integrated tranche now has production
modules, public exports, focused and independent audit evidence, static checks, dated journals,
and a final 457-test repository pass. Its verified post-tranche score is reported separately so
new work does not rewrite its own baseline.

The public execution backend is the THRML JAX simulator. The repository contains no evidence
from a production Extropic TSU. THRML describes its current software as a simulator for future
hardware in its [official probabilistic-computing tutorial](https://docs.thrml.ai/en/latest/examples/00_probabilistic_computing/).

## Completion Scoring

Each checklist item has equal weight because neither the original roadmap nor the ThermoMap
proposal assigns effort weights.

- `1.0` — production implementation plus a direct executable test or independent artifact.
- `0.5` — a reusable subset exists, while at least one named behavior remains absent.
- `0.0` — design prose, test-local helper, research prototype, or absent production behavior.
- `Verified current-tree implementation` — production code, direct tests, independent audit
  evidence, and final integrated-suite evidence exist at the recorded snapshot.

Equal weighting is an audit convenience, not an estimate of remaining person-weeks. Placement,
routing, degree reduction, and hardware calibration carry more technical risk than their row
count suggests.

### Optimizer And Audit Foundation: 8.5 / 10 = 85%

This denominator covers the substrate on which a hardware-aware compiler can be built. It
excludes Inspector, classical baselines, physical mapping, and a TSU backend, so 85% does not
mean that the product or ThermoMap is 85% complete.

| Foundation capability | Score | Evidence and limitation |
| --- | ---: | --- |
| Canonical pairwise Ising IR | 1.0 | `src/gibbsiq/model.py:128-195`; boundary and energy tests in `test_model_compatibility.py:62-176`. |
| QUBO, Ising, BQM, and dimod interchange | 1.0 | `src/gibbsiq/conversions.py:17-161`, `model.py:337-343`, and `result.py:236-254`; exhaustive dimod-backed contracts in `test_conversion_scenarios.py`. |
| Equation and conversion verification | 1.0 | `reference/08-evaluation/equation-audit.md`; offset, sign, gauge, relabeling, and exact-energy tests under `test_suite/tests/`. |
| Automatic legal Gibbs blocks | 1.0 | Bipartite coloring and deterministic DSATUR in `src/gibbsiq/blocks.py:62-175`; validity tests in `test_block_partition.py:37-145`. |
| Fixed-beta THRML execution | 1.0 | `_Lowering` and `THRMLSampler.sample` in `src/gibbsiq/thrml_runtime.py:173-380,1235-1413`; exact Boltzmann tests in `test_thrml_runtime.py:122-154,303-324`. |
| Multi-chain and parallel-tempering execution | 1.0 | `SamplerConfig` and PT path in `thrml_runtime.py:51-156,1079-1233`; exchange, offset, and sweep-accounting contracts in `test_runtime_correctness_contracts.py:65-509`. |
| Result, retained samples, and trace provenance | 0.5 | `SampleResult` is immutable and serializable in `result.py:62-234`; runtime traces include retained states, energies, schedules, chain ids, work, and swaps. Warmup states, block transitions, local fields, flip rates, and routing events are not captured. |
| Sampler-health diagnostics | 0.5 | Energy ESS/tau, plain and rank/folded R-hat, diversity, magnetization, and frozen-state checks exist in `diagnostics.py:165-723`. Constraints are explicitly `not_available` at `diagnostics.py:684-719`; rank-normalized bulk/tail ESS and general joint-mode checks remain absent. |
| Strict benchmark oracle and exact corpus | 1.0 | Witness recomputation in `benchmark_oracle.py`; deterministic 27-fixture corpus in `reference/06-benchmarks/fixtures/ground-truth-small.json`; anti-echo bridge in `benchmark_bridge.py:1-172`. |
| Machine-readable evaluation entry point | 0.5 | `gibbsiq-evaluate` emits JSON through `evaluation.py:381-417` and `pyproject.toml:66-67`. It is a fixture scorer, not the proposed compile/profile/verify API or Inspector. |

### Full ThermoMap Proposal: 6.0 / 20 = 30%

This denominator follows the components named in the supplied ThermoMap report. It is the
appropriate percentage for the compiler, mapper, verifier, profiler, and benchmark proposal.
The score is a baseline score; the current implementation tranche remains separate.

### Verified Post-Tranche ThermoMap: 8.0 / 20 = 40%

This is the verified current-tree score, not a replacement for the immutable 30% pre-tranche
baseline. The two-point delta is limited to four half-row improvements: a partial target
specification, a complete target-parameterized coefficient-quantization pass, a partial
supplied-partition chain-order mapping pass, and a partial set of communication algebraic
proxies. Exact distribution, direct admissibility, categorical/domain-wall lowering, Potts
objective evaluation, and ICM materially broaden the repository but do not earn extra row
credit where the corresponding ThermoMap row remains partial or absent. Forty percent is an
equal-row capability score, not an estimate that 60% of the engineering effort remains.

## Executive Snapshot

| Question | Evidence-based answer |
| --- | --- |
| What exists? | A correct and well-tested Ising/QUBO/BQM substrate; THRML block-Gibbs and parallel-tempering execution; audit diagnostics and witness oracles; exact small-law comparison; declared fixed-point quantization; direct logical target assessment; pairwise categorical/domain-wall lowering; a supplied-partition chain-order analyzer with distinct paper-pair, aggregate-link, and max-composite proxies; Potts objective evaluation; and an optimization-only ICM primitive. The reviewed analysis APIs are exported and exercised through a public smoke test. |
| What does not exist? | Automatic graph partitioning, node placement, general physical routing, degree-reduction/equality gadgets, hybrid TSU/GPU partitioning, stale-boundary dynamics, calibrated end-to-end latency or energy, ESS/joule roofline classification, categorical THRML execution, cross-domain baseline runners, Inspector/HTML reporting, or a physical TSU backend. |
| What would a professor say? | The programmer understands the implemented Ising, MCMC, exact-enumeration, quantization, and finite-state lowering mathematics and has unusually strong audit discipline. The repository is a credible research kernel, not yet the promised ThermoMap compiler or evidence of a TSU advantage. Its most important strength is that an independent audit found a communication-model overclaim and the code and prose were corrected before integration. |

## Existing Gibbsiq Roadmap Versus ThermoMap

Gibbsiq's existing roadmap builds a THRML-native optimization and trust layer:

```text
QUBO / Ising / BQM
-> canonical IsingModel
-> THRML block-Gibbs execution
-> SampleResult and diagnostics
-> witness oracle
-> future Inspector and baselines
```

ThermoMap adds a compiler and hardware-analysis path ahead of execution:

```text
model or factor graph
-> target-independent thermodynamic IR
-> target specification
-> lowering / quantization / placement / routing / hybrid partition
-> THRML simulator or future TSU backend
-> exact statistical verifier
-> thermodynamic roofline and recommendation
```

The second path is an extension, not a rename of completed work. Automatic Gibbs coloring is
one compiler pass; it does not place variables on physical cells or route couplings. THRML
execution validates the software lowering; it does not validate future silicon behavior.

| Existing roadmap stage | Current evidence-based status |
| --- | --- |
| Stage 0 — research and framing | Complete for the original Gibbsiq scope. Research files, evaluator, oracle, and corpus exist. |
| Stage 1 — model compatibility | Complete for binary pairwise QUBO/Ising/BQM. A pairwise finite-state `CategoricalModel` and exact domain-wall QUBO/Ising lowering are implemented and publicly exported. Higher-order factors, constraints, clamping, physical coordinates, and categorical THRML execution remain absent. |
| Stage 2 — THRML runtime | Core complete. The 2026-07-14 correction gives the first retained fixed-beta sample declared work, records exact sweep accounting, and verifies PT exchange behavior. The ICM module is an isolated optimization primitive and is not integrated into this runtime; device-side PT remains a performance refactor. |
| Stage 3 — diagnostics | Core complete with named limitations: constraints unavailable, energy-observable ESS only, default one chain, no bulk/tail ESS, and incomplete joint-mode coverage. |
| Stage 4 — Inspector | Absent. `reference/07-inspector/inspector-design.md` is a design, and no `Inspector` production class exists. |
| Stage 5 — baselines and benchmarks | Partial. Exact corpora and witness oracles exist; solver adapters, fixed-work/fixed-time runners, and comparative artifacts are absent. |
| Stage 6 — adaptive hardware runtime | Partial analysis foundation, not a runtime layer. Provenanced target facts, direct logical admissibility, coefficient quantization, exact small-distribution comparison, and supplied-partition chain communication/order analysis are implemented, exported, and integrated. Automatic partitioning, node placement, general routing, cost calibration, and target-aware execution remain absent. |

## ThermoMap Component Matrix

| Proposed component | Pre-tranche baseline | Baseline score | Verified current status | Current score | Concrete current evidence and remaining gap |
| --- | --- | ---: | --- | ---: | --- |
| Small Thermodynamic IR | Partial | 0.5 | Partial | 0.5 | `IsingModel` supplies the binary pairwise IR. `categorical.py` now adds an immutable finite pairwise `CategoricalModel`, and `domain_wall.py` lowers it exactly to QUBO/Ising. Clamping, physical coordinates, and general factors remain absent, so the new categorical path broadens this row without completing it. |
| `TSUSpec` | Absent | 0.0 | Partial | 0.5 | `hardware.py` implements and publicly exports provenanced capacity, degree, color-phase, coefficient-format, cell-energy, and cell-update fields with 12 focused specification tests. It deliberately has no topology, tile shape, allowed offsets, communication, reprogramming, or host-transfer contract. |
| Ising/QUBO/NetworkX/THRML/factor-JSON importers | Partial | 0.5 | Partial | 0.5 | QUBO, Ising, and BQM import remain implemented. The categorical constructor is a new model API, not a NetworkX, existing-THRML, or factor-JSON importer. |
| Compiler validation | Partial | 0.5 | Partial | 0.5 | Existing model/schedule validation is joined by `hardware_assessment.py`, which checks declared capacity, fixed-beta effective degree, color phases, and coefficient format and returns `conditional` for unknown topology. Its 20 focused tests include a 20,000-variable sparse smoke case and the beta-zero graph correction. Clamping conflicts, physical feasibility, placement, and routing validation remain absent, so no score delta is awarded. |
| Higher-order factor lowering | Absent | 0.0 | Absent | 0.0 | `domain_wall.py` lowers complete **pairwise categorical tables**; it is not higher-order quadratization. No higher-order factor IR, ancilla reduction, or TSP/knapsack constraint lowering exists. |
| Degree reduction and replicated-variable equality constraints | Absent | 0.0 | Absent | 0.0 | Logical maximum degree is measured, but no degree-reduction transform, replicated-variable equality gadget, reconstruction map, or mixing-overhead report exists. |
| Graph coloring and block scheduling | Partial | 0.5 | Partial | 0.5 | Legal deterministic bipartite/DSATUR blocks remain implemented. Target assessment correctly distinguishes a constructive schedule from a proven chromatic optimum; no competing coloring heuristics or ESS-aware schedule search exists. |
| Placement and routing | Absent | 0.0 | Partial supplied-partition chain mapping | 0.5 | `communication_profile.py` exactly searches partition-to-chain permutations through `K <= 6` under `(max-composite proxy, aggregate-link proxy, paper-pair C_max, paper-pair C_tot, canonical order)` and refuses an unproven larger fallback. This maps **caller-supplied partitions to chain slots** only; it does not partition the graph, place variables, add auxiliary routes, or support a general topology. Dense active-route metadata remains worst-case $O(K^3)$, and the canonical fallback for custom labels may inherit cross-process instability from `repr`. The Potts S.7 function evaluates a supplied assignment and is not an optimizer. |
| Hardware coefficient quantization | Partial | 0.5 | Implemented for declared coefficient formats | 1.0 | `hardware.py`, `quantization.py`, and `exact_distribution.py` implement beta-effective fixed-point formats, named rounding/overflow, analytic local-logit and distribution bounds, and exact small-model TV/KL/marginal/correlation checks. The 38 focused tests cover format endpoints, rounding ties, saturation, beta/offset/gauge mutations, and JSON finiteness. Accumulator and physical-response quantization remain non-ideality work, not stored-coefficient behavior. |
| Hybrid TSU/GPU partitioning | Absent | 0.0 | Absent | 0.0 | No component graph, transfer boundary, reprogramming model, or heterogeneous partition objective exists. |
| THRML executable backend | Implemented | 1.0 | Implemented | 1.0 | `_Lowering` builds THRML nodes, edges, blocks, and programs; `THRMLSampler` executes them on JAX. None of the new target, categorical, mapping, or ICM modules is integrated into that execution path. |
| Parameterized latency and energy model | Absent | 0.0 | Partial communication algebraic-proxy subset | 0.5 | `communication_profile.py` separately reports the Aadit paper-pair proxy, an aggregate-link proxy, and their max-composite proxy. These are algebraic serialization proxies shaped like time, ratio, and frequency values; they are **not** measured latency, a feasible communication schedule, a hardware-frequency limit, an energy model, or a mixing guarantee. There is no cell/route/host/reprogram end-to-end model, and the profiler is not composed with `TSUSpec` provenance. |
| Thermodynamic roofline profiler | Partial | 0.5 | Partial | 0.5 | Logical work, simulator timing, energy-observable ESS, and communication algebraic inputs exist separately. No unified ESS/second, ESS/joule, sensitivity report, or circuit/color/communication/mixing/host bottleneck classifier exists; the communication proxies are not themselves a roofline. |
| Reusable statistical verifier | Partial | 0.5 | Partial, substantially broadened | 0.5 | `exact_distribution.py` now provides capped exact Boltzmann laws and reusable TV, bidirectional KL, marginal, pair-correlation, and state-error comparison. The witness oracle remains independent. Transition-matrix stationarity, detailed-balance residuals, empirical interval coverage, and large-model reference comparison remain absent, so the row stays partial. |
| Non-ideality injection | Absent | 0.0 | Absent | 0.0 | No bias error, sigmoid distortion, accumulator error, stale/dropped update, boundary delay, timing skew, or drift injector exists. Communication feasibility equations do not simulate stale-state dynamics. |
| Physics benchmark family | Partial | 0.5 | Partial | 0.5 | Small Ising tests and the research PT/ICM harness remain. `cluster_moves.py` adds an exhaustively checked general-field isoenergetic disagreement-component primitive, but it is optimization-only and does not create a temperature/critical-region equilibrium benchmark or Potts runtime. |
| Bayesian benchmark family | Absent | 0.0 | Absent | 0.0 | No clamped HMM, image-denoising MRF, LDPC decoder, posterior calibration, or posterior benchmark exists. Exact distribution utilities provide an oracle substrate, not a benchmark family. |
| Optimization benchmark family | Partial | 0.5 | Partial | 0.5 | The exact corpus and witness bridge remain. ICM adds an optimization primitive but no integrated APT+ICM solver, classical adapters, matched-budget runner, time-to-target, or energy-per-success artifact, so it earns no ThermoMap benchmark-row delta. |
| Hybrid AI benchmark | Absent | 0.0 | Absent | 0.0 | No encoder, DTM/latent sampler, or decoder exists. `CategoricalModel` and domain-wall compilation do not constitute a categorical THRML sampler or hybrid AI pipeline. |
| Compile/profile/verify CLI and report | Partial | 0.5 | Partial | 0.5 | The fixture evaluator, machine-readable `to_dict()` payloads, and reviewed public APIs exported from `gibbsiq.__init__` exist and have a package-level smoke test. There is still no unified `compile_model`, `profile`, `verify`, Inspector, HTML report, or artifact manifest. |

## Twelve-Week Deliverable Audit

Every deliverable from the proposed schedule is listed below. “Test-local” means that a test
contains the calculation but users cannot call it as a supported production API.

| Weeks | Proposed deliverable | Status | Evidence and limitation |
| --- | --- | --- | --- |
| 1–2 | Reproduce THRML examples | Partial | Stage 2 exercises the installed THRML API and exact small models; no version-pinned reproduction artifact covers the current public example suite. |
| 1–2 | Exact enumeration | Implemented for capped Ising laws | `exact_distribution.py` exposes stable capped Boltzmann enumeration and comparison; `tools/generate_ground_truth.py` independently proves optimization fixtures. General categorical enumeration is still test-local. |
| 1–2 | Reference Gibbs sampler | Partial | Analytic conditionals and THRML empirical tests exist; no independent reusable CPU reference Gibbs sampler exists in `src/gibbsiq/`. |
| 1–2 | `TSUSpec` | Partial | `hardware.py` supplies immutable provenanced logical limits, coefficient format, and optional cell facts through the public package API. Topology, neighbor offsets, communication, reprogramming, and host-transfer fields remain absent. |
| 1–2 | Binary Thermodynamic IR | Partial | The canonical pairwise `IsingModel` exists and now has an adjacent pairwise categorical/domain-wall path; clamp, coordinate, and general-factor fields do not. |
| 3–4 | Ising importer | Implemented | `compile_ising`, `conversions.py:71-99`. |
| 3–4 | QUBO importer | Implemented | `compile_qubo`, `conversions.py:17-68`. |
| 3–4 | NetworkX importer | Absent | No production importer or dependency. |
| 3–4 | THRML importer | Absent | Gibbsiq lowers to THRML; it does not ingest an existing THRML graph. |
| 3–4 | Automatic coloring | Implemented | `color_blocks`, `blocks.py:62-85`. |
| 3–4 | Block schedule generation | Implemented | Color classes become ordered THRML free blocks in `thrml_runtime.py:200-206`. |
| 5–6 | Locality-aware placement | Partial supplied-partition chain subset | Exact small-`K` permutation search maps caller-supplied partitions to chain slots and evaluates both pair and aggregate-link algebraic proxies. It does not compute partitions, place nodes, route a general topology, or scale exact search beyond six partitions; dense active-route metadata remains worst-case $O(K^3)$. |
| 5–6 | Degree analysis | Implemented for the fixed-configuration logical graph | `hardware_assessment.py` reports effective degree facts and checks a declared `max_degree`. At beta zero it correctly retains all variables while treating the effective interaction graph as edgeless. It does not reduce degree, prove physical routability, or certify a later positive-beta schedule. |
| 5–6 | Auxiliary-node transformations | Absent | Domain-wall bits encode categorical state; they are not a degree-reduction, higher-order, or equality-gadget pass. |
| 5–6 | Parameterized latency model | Partial algebraic communication-proxy subset | Aadit S4 paper-pair, aggregate-link, and max-composite proxies are callable and separately labeled. They do not establish latency, feasibility, hardware-frequency limits, local execution, host transfer, reprogramming, or an end-to-end model. |
| 5–6 | Parameterized energy model | Absent | No joule or cell-energy calculation exists. |
| 7–8 | Autocorrelation and integrated time | Implemented | Geyer estimator in `diagnostics.py:113-195`, with external cross-check tests. |
| 7–8 | ESS | Implemented for scalar observables | Energy-trace ESS exists. Bulk/tail ESS and multivariate state ESS remain absent. |
| 7–8 | Split R-hat | Implemented for scalar observables | Plain and rank/folded variants exist; default `num_chains=1` makes them unavailable by default. |
| 7–8 | Marginal verification | Implemented for capped exact Ising laws | `compare_boltzmann_distributions` returns single-spin marginal, pair-correlation, TV, KL, and state-probability errors. Empirical interval coverage and detailed-balance checks remain absent. |
| 7–8 | Quantization sweeps | Implemented for beta-effective stored coefficients | `analyze_quantization` accepts a declared format and reports rounding, saturation, analytic error bounds, and optional exact-law error. It does not model accumulator or physical-response precision. |
| 7–8 | Non-ideality injection | Absent | No production injector or calibrated error model. |
| 9–10 | Ising/statistical-physics benchmarks | Partial | Small tests, a research PT/ICM harness, and an isolated ICM primitive exist; no standardized phase/critical-region equilibrium suite. |
| 9–10 | Bayesian benchmarks | Absent | Clamping and benchmark models are missing. |
| 9–10 | Optimization benchmarks | Partial | Proven corpus, oracle, and an isolated ICM primitive exist; constrained lowering, integrated APT+ICM, and comparative runners are missing. |
| 9–10 | JAX CPU/GPU baselines | Absent | THRML runs through JAX; independent matched solver baselines do not. |
| 11 | CLI/API | Partial | Fixture evaluation CLI plus reviewed package-level exports and a public smoke test exist. They are not unified as `compile_model`, `profile`, and `verify`. |
| 11 | Visualization | Absent | No plotting or interactive inspection layer. |
| 11 | Machine-readable report | Partial | Evaluation JSON, `SampleResult.to_dict()`, and typed target/quantization/admissibility/communication payloads exist; no unified target-profile schema or artifact manifest. |
| 11 | HTML report | Absent | Inspector design only. |
| 12 | Technical report | Partial | The research pack and dated journals provide methods material; no completed ThermoMap technical report exists. |
| 12 | Example notebooks | Absent | No notebook artifact appears in the repository. |
| 12 | Reproducible benchmark data | Partial | Exact fixtures and several research artifacts have seeds/checksums; the cross-domain ThermoMap benchmark corpus is absent. |
| 12 | THRML integration PR/RFC | Absent in this repository | Local prose discusses THRML PR #30; no accepted Gibbsiq integration artifact is recorded. |
| Extension | Pairwise categorical/domain-wall lowering | Implemented | `categorical.py` and `domain_wall.py` exhaustively preserve valid-state energies and record overhead/mixing warnings. There is no categorical THRML conditional or sampler, and this is not higher-order quadratization. |
| Extension | Direct target admissibility | Implemented for declared logical facts | `hardware_assessment.py` returns pass/fail/not-evaluated evidence for declared logical limits and refuses to invent topology claims. |
| Extension | Potts S.7 supplied-assignment objective | Implemented evaluator | `evaluate_potts_assignment` computes the paper objective for one assignment; it performs no partition optimization. |
| Extension | General-field ICM primitive | Implemented | `cluster_moves.py` preserves combined replica energy and records dependent-replica semantics. It is not integrated APT+ICM and adds no ThermoMap compiler-row credit. |

## Interpretation Boundaries That Must Stay Explicit

| Confusion point | Correct interpretation |
| --- | --- |
| Coloring versus mapping | Coloring partitions the logical interaction graph into independent update phases. Mapping assigns variables to physical cells and routes couplings under degree, distance, precision, and communication constraints. `blocks.py` implements the former. |
| Float lowering versus hardware quantization | `_Lowering` audits conversion into the active JAX floating dtype. `quantization.py` separately maps beta-effective stored coefficients into a declared finite format with named rounding and overflow. Neither behavior models an accumulated-field DAC, sigmoid distortion, or physical mismatch. |
| PT/ICM optimization versus equilibrium sampling | Correct PT exchange can preserve a joint replica target and yields cold-slot samples. `cluster_moves.py` is deliberately optimization-only; coupled replicas are dependent, and its outputs cannot inherit independent-chain ESS/R-hat semantics without a separate stationary-law and diagnostics audit. The APT+ICM source is [Chowdhury et al., arXiv:2503.10302](https://arxiv.org/abs/2503.10302). |
| ESS for an observable versus optimality | Gibbsiq estimates ESS for energy and applies R-hat to energy or magnetization traces. ESS describes estimator correlation for that observable. It neither proves state-space mixing nor certifies an optimum; witness oracles establish objective correctness. |
| Exact test oracle versus reusable verifier | A test that enumerates four spins proves one contract. `exact_distribution.py` now supplies a capped reusable Ising-law comparator, but it still does not test transition stationarity, detailed balance, or empirical confidence-interval coverage. |
| Benchmark oracle versus baseline suite | The oracle checks a claimed answer and recomputes its witness. A baseline suite runs independent solvers under fixed-work and fixed-time budgets. Gibbsiq has the first and lacks the second. |
| Categorical IR versus categorical execution | `CategoricalModel` represents complete finite pairwise tables and domain-wall lowering compiles them into Ising. The repository still has no categorical Gibbs conditional, categorical THRML lowering, or categorical sampler. A model/compiler is not an execution backend. |
| Domain-wall energy equivalence versus mixing | Exhaustive valid-state equality proves the encoded objective, not the encoded Markov dynamics. Category order changes one-bit adjacency, mixed differences can densify the graph, and invalid wall words add states; penalty choice and mixing remain empirical and target-dependent. |
| Fixed beta zero versus a multi-beta schedule | For one declared configuration, the effective interaction graph is $E_\beta=\{(i,j):\beta J_{ij}\ne0\}$. At beta zero it is edgeless: all variables remain, effective degree is zero, one update block is legal, topology is vacuous, and the original logical-edge count is still reported. That certificate applies only at beta zero; it does not certify a later positive-beta or multi-beta run. |
| Aadit `b_ab` versus directed traffic | Aadit S4 describes states sent from `a` to `b` but inserts one `b_ab` into unordered sums. General partitions can have unequal directed unique-boundary counts. `communication_profile.py` exposes both and records its explicit `max_directed` collapse; it does not attribute that unstated policy to the paper. |
| Chain reversal versus heterogeneous pins | The paper states `6!/2` orders up to reversal, but its DSIM-1 pin list is not palindromic. Reversal is a cost symmetry only for a reflection-symmetric interconnect; otherwise the exact search evaluates all `K!` orders. |
| Paper-pair versus aggregate-link versus max-composite proxy | Aadit S4's pair-level $C_{max}$ does not sum simultaneous demand from every pair sharing a physical link. The integrated profiler therefore reports three distinct algebraic proxies. The $K_{5,5}$ regression has paper-pair 18 but aggregate-link and max-composite 50. None is a measured latency, feasible schedule, hardware-frequency bound, energy value, or mixing certificate. |
| Potts S.7 evaluation versus partitioning | `evaluate_potts_assignment` scores one supplied assignment. It does not minimize the objective, balance a graph, or reproduce METIS, KaHIP, or the paper's optimizer. |
| Sparse FPGA simulated bifurcation versus TSU sampling | Yao et al.'s 2026 sparse, quantized simulated-bifurcation FPGA is a useful digital baseline and cost-model comparator. It executes a different deterministic/stochastic numerical architecture; it is neither evidence about a TSU stationary distribution nor an algorithm to insert into the THRML sampler without a separate design. The paper is stored for future matched-budget baseline work, not claimed as implemented. |
| Modeled versus measured hardware values | Simulator wall time is measured on the recorded JAX device. Cell energy, update latency, communication energy, and future TSU throughput are modeled assumptions until device measurements exist. Extropic's peer-reviewed system paper combines circuit measurement and modeling and labels its limitations ([Jelinčič et al., 2026](https://www.nature.com/articles/s44335-026-00075-3)). |
| Direct THRML execution versus future TSU execution | `THRMLSampler` executes public THRML on JAX CPU/GPU. A physical TSU backend requires a device API, target calibration, and sample-law verification. No repository result crosses that boundary today. |
| Low energy versus healthy sampling | An optimizer can find a low-energy witness from a trapped chain. The witness proves the objective value; diagnostics describe the evidence-generating process. Neither substitutes for the other. |

## Current Implementation Tranche — Integrated And Verified

The shared working tree now contains eight audited feature groups:

1. `hardware.py`: provenanced `TSUSpec` and `FixedPointSpec`.
2. `exact_distribution.py`: capped exact Ising laws and reusable comparison metrics.
3. `quantization.py`: beta-effective coefficient quantization and analytic/exact error evidence.
4. `hardware_assessment.py`: direct logical target admissibility with explicit unknown states.
5. `communication_profile.py`: supplied-partition chain-order search and separately labeled
   Aadit paper-pair, aggregate-link, and max-composite algebraic communication proxies.
6. `communication_profile.py`: supplied-assignment Potts S.7 objective evaluation.
7. `categorical.py` and `domain_wall.py`: pairwise categorical IR and exact valid-state
   domain-wall QUBO/Ising lowering.
8. `cluster_moves.py`: general-field isoenergetic disagreement-cluster move with explicit
   dependent-replica semantics.

Each group has focused tests and a dated journal. The reviewed surface is exported through
`gibbsiq.__init__` and a public smoke test composes categorical lowering, target assessment,
quantization, exact comparison, communication analysis/search, Potts evaluation, and ICM
metadata. An independent audit found and reproduced a communication defect: a $K_{5,5}$ case
scored 18 under the paper-pair proxy while aggregate shared-link demand required 50. The code
now reports both plus the max-composite proxy, stores a no-traffic $K=400$ report in linear
space, and keeps exact chain search capped at $K\le6$. Dense active routes can still require
$O(K^3)$ metadata, custom-label canonicalization can inherit cross-process `repr` instability,
and communication analysis is not composed with `TSUSpec` provenance. The final 457-test
suite and static checks passed, so the tranche is closed as an integrated analysis surface,
not misrepresented as a complete mapper or hardware model.

### Verified Score Delta Without Double Counting

The **30% Full ThermoMap score remains the immutable pre-tranche baseline**. The following
table accounts for every new feature against the original 20 component rows:

| New feature or distinct sub-capability | ThermoMap row receiving credit | Baseline | Current | Delta | Why no additional credit is assigned |
| --- | --- | ---: | ---: | ---: | --- |
| Provenanced `TSUSpec` | `TSUSpec` | 0.0 | 0.5 | +0.5 | The target record lacks topology, neighbor offsets, communication, reprogramming, and transfer facts, so it is partial rather than complete. |
| Exact distribution verifier | Reusable statistical verifier | 0.5 | 0.5 | +0.0 | Exact TV/KL/marginal/correlation evidence broadens the reusable subset, but transition stationarity, detailed balance, empirical intervals, and large-model comparison are missing. |
| Coefficient quantization | Hardware coefficient quantization | 0.5 | 1.0 | +0.5 | The declared stored-coefficient pass is complete; accumulator and nonlinear physical errors belong to non-ideality injection and are not deducted from this row. |
| Direct target admissibility | Compiler validation | 0.5 | 0.5 | +0.0 | It validates every fact expressible by the current target and honestly returns `not_evaluated` for topology, but clamping and physical routing validation remain absent. |
| Exact supplied-partition chain-order search | Placement and routing | 0.0 | 0.5 | +0.5 | Credit covers only small-`K` partition-to-chain permutation. It is not graph partitioning, variable placement, general routing, or a scalable mapper. |
| Aadit paper-pair, aggregate-link, and max-composite algebraic proxies | Parameterized latency and energy model | 0.0 | 0.5 | +0.5 | The separately named outputs provide a reusable communication cost-model subset. They are not latency or frequency bounds, do not prove a feasible schedule, and have no energy or end-to-end calculation. |
| Potts S.7 supplied-assignment evaluator | Placement and routing | 0.5 | 0.5 | +0.0 | It supports analysis of an already supplied assignment but performs no optimization; placement credit was already assigned to the exact chain-order search. |
| Pairwise categorical IR and domain-wall lowering | Small Thermodynamic IR / higher-order lowering | 0.5 / 0.0 | 0.5 / 0.0 | +0.0 | The IR is broader, but clamping/general factors remain absent. Domain-wall lowering handles pairwise finite tables and is not higher-order quadratization. |
| ICM primitive | Optimization benchmark family | 0.5 | 0.5 | +0.0 | It adds optimizer capability but no integrated APT+ICM runner, baseline comparison, or benchmark artifact. Coupled outputs are not equilibrium chains. |

The verified result is therefore **8.0/20 = 40%**. The two credits from
`communication_profile.py` are not duplicate counts: one is an exact discrete mapping search
against the placement row, and the other is a separately returned family of communication
algebraic proxies against the cost-model row. Potts S.7, roofline, energy, benchmark, and
Inspector rows receive no further credit. This equal-row result is not a forecast of effort
remaining.

The existing `tools/benchmark_cluster_moves.py` remains a research harness. The new ICM module
is a reusable primitive, not a production THRML or TSU kernel. Domain-wall energy equivalence
and the Potts objective evaluator similarly do not imply good mixing or a working mapper.

Primary sources stored locally are:

- Jelinčič et al., domain-wall representation,
  [arXiv:2606.17327](https://arxiv.org/abs/2606.17327), local file
  `reference/01-architecture/papers/jelincic-2026-codon-optimization.pdf`.
- Aadit et al., distributed p-bit communication and fixed-point implementation,
  [arXiv:2606.25313](https://arxiv.org/abs/2606.25313), local file
  `reference/05-theory/papers/aadit-2026-million-pbit.pdf`.
- Chowdhury et al., adaptive parallel tempering with isoenergetic cluster moves,
  [arXiv:2503.10302](https://arxiv.org/abs/2503.10302), local file
  `reference/05-theory/papers/chowdhury-2025-adaptive-parallel-tempering-icm.pdf`.
- Yao et al., sparse FPGA quantized simulated bifurcation,
  [Nature Communications, DOI 10.1038/s41467-026-75119-0](https://doi.org/10.1038/s41467-026-75119-0), local file
  `reference/01-architecture/papers/yao-2026-sparse-fpga-quantized-simulated-bifurcation.pdf`.
  This is a digital FPGA baseline/cost-model comparator, not TSU sampling evidence; no Yao
  algorithm is claimed as implemented because its architecture and update dynamics differ.

## Final Integration Evidence

The final integrated snapshot passed 114 focused new-surface tests. The repository-wide
command below then ran **457 tests in 120.615 seconds and returned `OK`**:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s test_suite/tests
```

Static and document verification at the same integration point reported:

- `ruff check .` — passed;
- `ruff format --check .` — 60 files already formatted;
- `mypy src/gibbsiq` — 19 source files checked with no issues;
- Markdown-math validation — passed.

Independent checks did not trust module self-reports:

| Independent check | Recorded result |
| --- | --- |
| Communication defect reproduction | $K_{5,5}$ paper-pair proxy 18 versus aggregate-link/max-composite 50; fixed by separating the metrics and pinning the regression. |
| Exact chain-order search | 170 exhaustive cases for $K=1\ldots6$ matched independent enumeration. |
| Communication random profiles | 200 independently generated profiles satisfied the corrected algebraic contracts; an earlier 50-case/all-24-permutation pre-correction scout is retained as superseded evidence. |
| No-traffic storage | A $K=400$ report stores active-pair information linearly; dense active routes remain worst-case $O(K^3)$. |
| Beta-zero target semantics | All 1,099 simple graphs with one to five vertices retained every variable, had zero effective edges/degree, one legal block, preserved the logical-edge count, and gave exact-law TV error zero. |
| Exact and quantized laws | 120 random cases had maximum probability residual $5.55\times10^{-16}$ and maximum analytic-bound residual zero. |
| ICM invariant | 2,501 accepted/rejected move checks had maximum paired-energy residual $7.105\times10^{-15}$. |
| Domain-wall lowering | 60 random models, 602 valid assignments, and 2,223 encoded words had maximum valid-state energy error zero. |

These results establish software contracts on the recorded Windows 11 / Python 3.13.5
environment. They do not establish cross-version behavior, hardware timing, physical TSU
sampling, energy per independent sample, or a solver advantage.

## External Test Reuse

The repository has already borrowed selectively instead of copying an upstream suite into the
runtime gate:

- `test_dimod_ported_contracts.py` contains 18 dependency-free contract tests selectively
  ported from dimod commit `bad4cba` under Apache-2.0, with upstream file-and-line provenance;
  `reference/research-journal/2026-07-04-dimod-contract-test-port.md` records the choices and
  license boundary.
- Live dimod parity tests already compare Gibbsiq conversion/interchange behavior when dimod
  is installed.
- Diagnostics already cross-check against ArviZ and an R-`posterior` reference rather than
  trusting Gibbsiq's ESS/R-hat implementation in isolation.

The next useful borrow is narrow: property/metamorphic BQM relabel, coefficient-scale, and
offset-shift cases; dimod/D-Wave sampler-response accounting only where Gibbsiq exposes the
same semantic contract; and ArviZ bulk/tail ESS cases only after a production bulk/tail metric
exists. Do **not** port DQM, CQM, serialization, or sampler tests for unsupported surfaces, or
tests that merely prove dimod/ArviZ itself works. Every adapted test must retain license,
commit, and file/line provenance and must assert a Gibbsiq contract against an independent
oracle rather than echoing an upstream expected value without a valid witness.

## Professor-Style Assessment

| Area | Candid assessment |
| --- | --- |
| Mathematical understanding | Strong and genuine for canonical Ising math, fixed-point equilibrium error, exact small distributions, pairwise categorical finite differences, domain-wall valid-state equivalence, replica exchange, and the general-field ICM invariant. The authors also caught ambiguities in Aadit's directed boundary count and reversal quotient and corrected the pair-versus-link aggregation error. Mastery of higher-order gadgets, scalable physical mapping, stale-boundary stationary laws, and hardware non-idealities is not yet demonstrated. |
| Code quality | Better than a typical early research solver in immutability, validation, deterministic fixtures, stdlib fallbacks, and anti-echo tests. The analysis passes are isolated rather than inserted into the 1,413-line `thrml_runtime.py`, exported deliberately, and exercised through a public smoke path. Independent review found and corrected a communication-profile overclaim/storage defect before closure; that is evidence of a functioning review process, while the remaining $O(K^3)$ active-route metadata, `repr`-based label-order risk, and lack of `TSUSpec` composition show the code is not a finished compiler. CI still tests only Python 3.13 despite a Python 3.10–3.13 package claim. |
| Test quality | Strong on exact contracts, metamorphic transformations, numerical-domain failures, diagnostic traps, dimod/ArviZ/R cross-checks, witness recomputation, categorical exhaustive tables, ICM invariance, communication aggregation, and paper-value pins. Weak on systematic property-based generation, mutation/coverage measurement, cross-version CI, stale-boundary dynamics, scalable placement, higher-order constraints, and independent solver comparison. |
| Debugger claim | The project has audit telemetry, not a complete debugger. It records retained samples and scalar traces but lacks warmup/block transition traces, local logits, flip rates, routing/quantization overlays, and an Inspector. |
| Optimization claim | The sampler finds proven optima on small fixtures. Competitive optimization remains unevaluated because the baseline layer, fixed-budget runner, and time-to-solution study are absent. |
| TSU impact claim | Unsupported today. The repository has no physical TSU run, automatic graph partitioner, node placer, general router, calibrated end-to-end cost model, or measured energy per independent sample. Paper-grounded communication algebra is an analysis proxy, not an Extropic result. |
| Defensible research impact | The strongest current contribution remains the integrated audit contract, now extended with exact target-error, categorical-lowering, and corrected supplied-partition communication evidence. A distinct ThermoMap systems claim still requires automatic mapping and quality-adjusted calibrated costs. |

A professor would likely describe the repository as a serious research kernel with unusually
good correctness discipline and an unfinished systems thesis. The programmer understands the
implemented Ising, finite-state lowering, and MCMC mathematics. The programmer is also willing
to contradict under-specified paper formulas rather than echo them. The repository still does
not substantiate the claim that it automatically maps useful workloads to TSU hardware or that
TSU-backed optimization is competitive.

## Historical Gated Plan At Commit `c62169e`

This section records the ordering proposed during the dated audit. The live autonomous roadmap
supersedes this ordering while preserving this document's evidence and scores.

### Gate 0 — Closed: Integrated Analysis Surface

The communication profiler now distinguishes paper-pair, aggregate-link, and max-composite
algebraic proxies; the no-traffic representation is linear; the reviewed public API is exported
without wiring optimization-only ICM into equilibrium sampling; and the 114 focused tests,
457-test full suite, Ruff, format, mypy, and Markdown-math checks passed. Dated journals retain
the defect reproduction, correction, choices, rejected alternatives, commands, provenance,
and checksums. Closure means the analysis tranche is integrated. It does not close automatic
mapping, target-calibrated execution, or physical-hardware claims.

### Gate 1 — Complete Categorical Execution After Domain-Wall Lowering

The pairwise categorical convention, domain-wall binary reduction, codec, and valid-state
energy proof are implemented and integrated. Next implement the categorical conditional/THRML
execution path and a defensible penalty policy or explicit user policy. The codon work in
[Jelinčič et al., arXiv:2606.17327](https://arxiv.org/abs/2606.17327) is the primary starting
point.

Required closure evidence:

- equation audit defines the categorical energy, state order, offset, conditional, and
  domain-wall penalty/validity contract;
- exhaustive small instances prove energy/order/witness equivalence in both directions;
- invalid domain walls are detected and penalty sensitivity is reported;
- node, edge, degree, dynamic-range, and color overhead are recorded;
- categorical sampling is tested against exact probabilities.

### Gate 2 — Generalize Corrected Communication Analysis And Model Stale Dynamics

Directed unique-boundary counts, exact small chain-order search, bottleneck pins, paper-pair
proxies, aggregate physical-link demand, max-composite proxies, and linear no-traffic summaries
are implemented and independently checked. Next support general networks, reduce dense
active-route metadata, compose the analysis with `TSUSpec` provenance, and model exchange
cadence, stale-state delay, and host/device transfer separately. Aadit et al. report a
throughput–accuracy tradeoff as boundary exchange changes; their result motivates a parameter
sweep rather than a universal constant
([arXiv:2606.25313](https://arxiv.org/abs/2606.25313)).

Required closure evidence for the next extension:

- every future timing field carries measured, paper-derived, assumed, or simulated provenance,
  while algebraic proxies remain explicitly labeled as proxies;
- pair-route and aggregate shared-link metrics have distinct names and independent hand
  fixtures;
- exact small models quantify stationary-distribution error under delayed/stale updates;
- larger runs preserve raw traces and confidence intervals;
- the report distinguishes communication time, local update time, mixing, and host overhead;
- no Extropic hardware number is presented as measured without a device artifact.

### Gate 3 — Placement, Routing, And Degree Reduction

Add target coordinates, allowed neighbor offsets, maximum degree, placement, routes,
replication/equality gadgets, and a decoder. Compile failure is an explicit result when the
target cannot represent a model within declared limits.

Required closure evidence:

- exhaustive small cases prove original-objective witness equivalence;
- exact distributions quantify the effect of equality penalties and quantization;
- the compiler reports auxiliary nodes, routes, congestion, color phases, coefficient range,
  and rejected mappings;
- sparse graphs near $10^5$ variables have a recorded compile benchmark and checksum;
- alternative heuristics are compared on compile time, target cost, and sampling quality.

### Gate 4 — Thermodynamic Roofline

Combine logical work, target cost, and observable-specific statistical efficiency. Report raw
sweeps, energy-observable ESS/second, and modeled energy-observable ESS/joule. Preserve the
observable name in every metric.

Required closure evidence:

- circuit-, color-, communication-, mixing-, and host-limited synthetic fixtures produce the
  expected classification;
- sensitivity ranges accompany assumed cost parameters;
- predictions are compared with measured JAX runs without treating simulator wall time as TSU
  time;
- repeated seeds produce confidence intervals and raw artifacts.

### Gate 5 — Baselines, Cross-Domain Benchmarks, And Inspector

Add exact, simulated annealing, tabu/steepest-descent, and appropriate specialized baselines;
then add physics, Bayesian, and optimization benchmark runners and an exportable report.

Required closure evidence:

- fixed-work and fixed-time budgets remain separate;
- tuning, compile, sample, diagnostics, postprocess, and wall time are recorded separately;
- every optimum claim carries a recomputed witness;
- at least two independent baselines run on the same fixture ids and seeds;
- the physics suite spans easy, critical, and frustrated regimes; the Bayesian suite verifies
  posterior marginals and calibration; the optimization suite reports target-hit probability,
  quality distribution, and diversity;
- `Inspector.from_result` exports summary, samples, traces, problem, and metadata artifacts.

### Gate 6 — Physical TSU Calibration

This gate begins when a device backend and calibration interface are available.

Required closure evidence:

- programmed and observed coefficient/response calibration artifacts are stored with device
  identity and checksums;
- exact small distributions bound physical stationary-law error;
- end-to-end host transfer, programming, sampling, and diagnostics timing is measured;
- energy comes from a documented measurement boundary;
- TSU-versus-GPU claims use matched workloads, quality targets, and uncertainty intervals.

## Reconciliation Of Stale Status Statements

The following statements remain useful historical context and should not be read as the
2026-07-14 working-tree status.

| Older statement | 2026-07-14 resolution |
| --- | --- |
| Supplied project guidance reports 209 tests with six ArviZ skips. | The recorded pre-tranche full run in `reference/research-journal/2026-07-14-runtime-sampling-and-frozen-mode-correctness.md` ran 342 tests in 172.789 seconds with no failures. The final post-tranche integrated run executed 457 tests in 120.615 seconds and returned `OK`; counts remain command-specific. |
| At commit `c62169e`, `PROJECT_BRIEF.md`, `spec.md`, `CLAUDE.md`, and `reference/00-roadmap/README.md` left PT and the Stage 3 corrective suite open. | The 2026-07-14 runtime/diagnostic correction has code, focused tests, a full 342-test pass, static checks, and a journal entry. Device-side PT performance remains open; the listed correctness correction is closed in the audited working tree. |
| Product-layer prose says diagnostics compute feasibility. | Actual `compute_diagnostics` returns `constraints={"status": "not_available"}` until an encoding layer exists (`diagnostics.py:684-719`). Feasibility is target behavior. |
| At commit `c62169e`, the target flow named `THRMLProgramBundle`. | No public class with that name exists. `_Lowering` is private and executes in-process. |
| README examples call `Inspector.from_result`. | The call is a target API example. No production `Inspector` exists. |
| A categorical `SampleResult` might imply Potts execution. | A pairwise `CategoricalModel` and domain-wall compiler now exist, but the categorical conditional, THRML lowering, and sampler remain absent. Storage, modeling, compilation, and execution are four separate claims. |
| The earlier in-progress equation audit contained fixed-point and distribution formulas. | EVAL-EQ-016 through EVAL-EQ-020 now have production implementations, focused tests, public exports where applicable, and final integration evidence. The 30% baseline remains unchanged; the verified current-tree score is 40%. |

This dated reconciliation leaves the old snapshots intact. Future status updates should add a
new dated document or journal entry and preserve this audit's baseline and scoring choices.
