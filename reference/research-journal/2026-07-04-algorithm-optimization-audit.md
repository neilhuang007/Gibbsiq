# 2026-07-04 - Algorithm Optimization Audit

## Paper Hook

Feeds the methodology limitations, optimization roadmap, and baseline-comparison sections:
which calculations Gibbsiq performs today, which faster or more accurate alternatives are
credible, and which claims require new evidence before they can appear in a paper.

## Context

The user requested a repository-wide diagnosis of the algorithms and calculations in
Gibbsiq, with web research for faster or more accurate alternatives. The project is
THRML-first and targets TSU-style thermodynamic sampling hardware through THRML. The audit
therefore treats THRML block Gibbs as the primary execution path and treats classical
optimizers as baselines or preprocessing tools unless they preserve the sampling evidence
contract.

External TSU framing matters for claims hygiene. Extropic describes a TSU as a sampling unit
that produces samples from programmable probability distributions rather than a conventional
CPU or GPU replacement:
https://extropic.ai/writing/thermodynamic-computing-from-zero-to-one. A 2025 Extropic
preprint reports GPU-parity energy results for denoising-style generative workloads, not a
measured QUBO/Ising optimization advantage for this repository:
https://arxiv.org/abs/2510.23972.

## Hard-Parts Analysis

1. The repository has two different classes of calculations: exact/audit calculations and
   stochastic optimization. Exact routines must remain independent of sampler output because
   they prevent echoed or fabricated optima.
2. The main accuracy bottleneck for rugged QUBO/Ising instances is likely low-temperature
   mixing, not the energy formula. Parallel tempering is the best-aligned Stage 2 upgrade
   because it preserves the Gibbs-family execution model while improving escape from local
   minima.
3. The current runtime-dependency boundary is deliberate. The core package has no required
   third-party dependencies, so heavyweight speedups should enter through optional extras,
   adapters, or generated artifacts instead of mandatory imports.
4. Some faster optimizers, especially simulated bifurcation and MQLib heuristics, optimize
   the same objective but do not produce MCMC diagnostics with the same interpretation.
   They are strong baseline candidates and weak drop-in replacements for THRML sampling.
5. QUBO preprocessing can reduce runtime and improve solution quality, but it changes the
   model boundary. Any preprocessing pass must record fixed variables, relations, offset
   changes, rejected rules, and an expansion map back to the original witness space.

## Algorithm Inventory

### Model And Conversion

- `src/gibbsiq/conversions.py:17` `compile_qubo` parses diagonal and pair QUBO terms,
  normalizes pair orientation, folds duplicate coefficients, and maps binary QUBO terms to
  the canonical Ising convention.
- `src/gibbsiq/conversions.py:73` `compile_ising` folds self-couplings into the offset and
  normalizes coupler keys.
- `src/gibbsiq/conversions.py:103` `compile_bqm` uses `dimod.to_ising()` when available and
  has a duck-typed fallback.
- `src/gibbsiq/model.py:149` `energy` recomputes `offset + h*s + J*s*s` directly in
  `O(n + m)`.
- `src/gibbsiq/model.py:159` `local_field` scans all couplers, so repeated local-field
  queries cost `O(m)` per variable today.
- `src/gibbsiq/model.py:174` `conditional_probability` uses the audited Gibbs sign and a
  numerically stable sigmoid branch.

The QUBO-to-Ising algebra matches the standard binary-to-spin expansion and the dimod
contract that `BinaryQuadraticModel.to_ising()` returns linear terms, quadratic terms, and
offset:
https://docs.dwavequantum.com/en/latest/ocean/api_ref_dimod/generated/dimod.binary.BinaryQuadraticModel.to_ising.html.

### Block Construction

- `src/gibbsiq/blocks.py:60` computes graph density.
- `src/gibbsiq/blocks.py:68` `color_blocks` builds independent variable blocks with a
  topology-only cache.
- `src/gibbsiq/blocks.py:105` detects bipartite graphs by BFS and emits two blocks.
- `src/gibbsiq/blocks.py:129` uses deterministic DSATUR with lazy heap priorities.
- `src/gibbsiq/blocks.py:189` validates that no block contains adjacent variables.

The existing same-day journal entry
`reference/research-journal/2026-07-04-block-coloring-optimization-review.md` already
records that sparse graph coloring improved from 4.6550 seconds to 0.0353 seconds on the
first run and 0.000330 seconds on a cached repeat for the measured 5000-variable instance.
NetworkX documents smallest-last coloring as `O(n + m)` and DSATUR as a saturation-degree
strategy:
https://networkx.org/documentation/stable/_modules/networkx/algorithms/coloring/greedy_coloring.html.

### THRML Runtime

- `src/gibbsiq/thrml_runtime.py:54` `SamplerConfig` validates beta, chain count, read count,
  sweep count, initialization policy, warmup ladder, and diagnostics toggles.
- `src/gibbsiq/thrml_runtime.py:106` splits warmup sweeps over a beta ladder.
- `src/gibbsiq/thrml_runtime.py:133` stores lowered THRML program objects.
- `src/gibbsiq/thrml_runtime.py:253` `THRMLSampler` handles optional THRML/JAX import,
  lowering, initialization, sampling, decoding, metadata, and diagnostics.
- `src/gibbsiq/thrml_runtime.py:277` `sample` returns raw samples, energies, timing splits,
  traces, chain ids, schedule metadata, and diagnostics.

THRML's own documentation describes a JAX library for block Gibbs sampling of energy-based
models using graph-colored blocks and GPU sampling:
https://docs.thrml.ai/en/latest/. The THRML repository describes the implementation as
minimizing Python loops and maximizing JAX array parallelism:
https://github.com/extropic-ai/thrml.

### Diagnostics

- `src/gibbsiq/diagnostics.py:140` implements Geyer's initial positive sequence ESS.
- `src/gibbsiq/diagnostics.py:262` computes plain split R-hat.
- `src/gibbsiq/diagnostics.py:320` computes rank-normalized and folded split R-hat.
- `src/gibbsiq/diagnostics.py:460` computes diversity from weighted unique state counts,
  including unique fraction, top-k mass, entropy, and pairwise Hamming distance over unique
  states.
- `src/gibbsiq/diagnostics.py:583` records magnetization traces.
- `src/gibbsiq/diagnostics.py:595` records distance-to-best traces.
- `src/gibbsiq/diagnostics.py:611` assembles the diagnostics payload and family-scoped
  flags.

The implementation intentionally mirrors the Vehtari et al. rank-normalized split R-hat and
ESS family of diagnostics. The paper recommends rank-normalized ESS greater than 400 for
reliable estimates and uses folded split R-hat to expose scale problems:
https://sites.stat.columbia.edu/gelman/research/published/Vehtari_etal_2020_rhat_ess.pdf.
ArviZ 0.21 is a useful reference implementation, but it returns special statuses for
constant chains and exposes additional ESS variants that Gibbsiq should wrap carefully:
https://python.arviz.org/en/v0.21.0/_modules/arviz/stats/diagnostics.html.

### Benchmarks And Oracles

- `src/gibbsiq/benchmark_oracle.py:239` recomputes candidate objectives from witness states.
- `src/gibbsiq/benchmark_oracle.py:316` verifies benchmark fixtures.
- `src/gibbsiq/benchmark_bridge.py:48` lowers supported benchmark fixtures into Ising.
- `src/gibbsiq/benchmark_bridge.py:122` converts `SampleResult` output into benchmark
  candidates.
- `tools/generate_ground_truth.py:112` brute-forces small MaxCut fixtures.
- `tools/generate_ground_truth.py:171` brute-forces number partition fixtures.
- `tools/generate_ground_truth.py:240` brute-forces knapsack fixtures.
- `tools/generate_ground_truth.py:306` brute-forces TSP fixtures.
- `tools/generate_ground_truth.py:378` brute-forces generic Ising fixtures.

The oracle/witness split is a project strength. Exact methods can be expanded without
weakening the anti-echo contract. BiqMac is a credible exact MaxCut/BQP reference for larger
small-instance corpora because it uses SDP branch-and-bound:
https://biqmac.aau.at/ and
https://optimization-online.org/wp-content/uploads/2007/05/1659.pdf.

## Recommendations

### 1. Implement Parallel Tempering In The THRML Path

Priority: highest.

Parallel tempering directly targets the current open Stage 2 exit criterion and the likely
mixing bottleneck on rugged Ising models. The algorithm runs chains across a beta ladder and
proposes swaps between neighboring temperatures, improving low-temperature exploration while
keeping fixed-beta samples auditable.

Primary sources:

- Hukushima and Nemoto's exchange Monte Carlo paper describes multiple temperatures and
  exchange moves that shorten ergodicity times for low-temperature systems:
  https://arxiv.org/abs/cond-mat/9512035.
- A THRML pull request already sketches parallel-tempering utilities around
  `BlockSamplingProgram`:
  https://github.com/extropic-ai/thrml/pull/30/files/e328bfbb27aa9330d402f4b2e00f566863a1eb66.

Implementation hygiene:

- Add config fields for beta ladder, swap interval, swap seed stream, and swap policy.
- Record attempted swaps, accepted swaps, beta occupancy, per-beta trace segments, and final
  state provenance.
- Keep `SampleResult` fixed-beta interpretation explicit. Diagnostics should be computed on
  compatible trace segments, with tempering metadata echoed separately.
- Tests should verify swap acceptance probabilities by recomputing energies, deterministic
  replay from seed, and a small model where the tempered run reaches both modes more often
  than a fixed cold chain under a fixed work budget.

### 2. Add An Optional QUBO Preprocessing Layer

Priority: high for speed and accuracy on larger QUBO inputs.

Preprocessing can shrink the state space before THRML lowering by fixing variables,
discovering persistencies, reducing dynamic range, or simplifying relations. This should be
optional and provenance-heavy because it mutates the optimization instance seen by the
sampler.

Primary sources:

- QUBOLite documents partial assignments, energy recovery constants, QPRO+ persistencies,
  dynamic-range reduction, and clamping:
  https://arxiv.org/html/2509.21321v1.
- Lewis and Glover survey preprocessing rules for identifying QUBO variables whose optimal
  values can be predetermined:
  https://arxiv.org/abs/1705.09844.
- Boros, Hammer, and Tavares discuss roof duality, derivative implications, bounds, fixed
  variables, and binary relations:
  https://users.cecs.anu.edu.au/~pcarr/qpbo/BorosRRR102006.pdf.
- Qoolchain is a C++/Cython QUBO reduction and decomposition toolchain:
  https://github.com/ilRenato/Qoolchain.

Implementation hygiene:

- Start with a design document and a tiny stdlib-safe rule set before adding optional
  accelerator integrations.
- Store a preprocessing certificate: original variable count, reduced variable count, fixed
  assignments, relation constraints, offset delta, rejected rules, and reconstruction map.
- Prove energy equivalence by enumerating small fixtures before and after reduction and by
  expanding reduced witnesses through the oracle.
- Preserve the canonical Ising offset in every reduced model and in every expanded witness.

### 3. Build Penalty And Encoding Support For Constrained Families

Priority: high for benchmark coverage.

`benchmark_bridge.py` currently supports MaxCut, number partition, and SK spin glass. It
does not lower knapsack or TSP because the penalty/encoding layer is absent. This limits
benchmark breadth and leaves accuracy comparisons focused on unconstrained models.

Primary source:

- Ayodele surveys penalty-weight setting and notes that excessive penalties can overwhelm
  objective coefficients while weak penalties allow infeasible solutions:
  https://arxiv.org/pdf/2206.11040.

Implementation hygiene:

- Add one-hot and cardinality encoders with explicit penalty provenance.
- For TSP, use the standard first-city symmetry reduction and two-way one-hot constraints
  before sampling.
- Record rejected penalty values and feasibility rates during tuning.
- Add tests where feasible and infeasible witnesses are both recomputed by the oracle.

### 4. Add Baseline Adapters Rather Than Replacing THRML

Priority: medium-high for evaluation credibility.

Several mature solvers optimize the same objective and should be compared against Gibbsiq.
They should enter through the baseline layer because their diagnostic semantics differ from
THRML block Gibbs.

Candidate baselines:

- D-Wave `dwave-samplers` simulated annealing supports beta schedules, Gibbs/Metropolis
  update styles, reverse annealing, and timing metadata:
  https://docs.dwavequantum.com/en/latest/ocean/api_ref_samplers/index.html.
- OpenJij provides a C++ core with a Python interface for Ising and QUBO:
  https://tutorial.openjij.org/en/tutorial/001-openjij_introduction.html.
- Simulated bifurcation supports QUBO/TSP/MaxCut-style quadratic models and exposes ballistic,
  discrete, and heated variants:
  https://github.com/bqth29/simulated-bifurcation-algorithm.
- MQLib includes a hyper-heuristic and many MaxCut/BQP heuristics:
  https://github.com/MQLib/MQLib and
  https://github.com/MQLib/MQLib/blob/master/src/heuristics/heuristic_factory.cpp.

Implementation hygiene:

- Normalize inputs through the same Ising IR where possible.
- Record seed, version, hardware, compile time, solve time, tuning time, and postprocessing
  time separately.
- Treat solver-specific health metrics separately from Gibbsiq R-hat/ESS diagnostics.
- Use witness recomputation as the common comparison surface.

### 5. Add An Optional Fast Diagnostics Backend

Priority: medium.

The stdlib diagnostics implementation is valuable for portability and explicit statuses.
For long traces, autocovariance and rank operations could be accelerated by an optional
NumPy/SciPy/ArviZ backend, and additional tail/local ESS or MCSE metrics would improve
diagnostic coverage.

Implementation hygiene:

- Keep the current stdlib backend as the reference.
- Add an optional backend selected by config or availability.
- Preserve Gibbsiq's `not_enough_data`, constant-chain, NaN, and Inf statuses even when an
  external library returns a numeric fallback.
- Cross-check optional backend outputs against the stdlib backend on existing fixtures and
  against ArviZ on non-degenerate traces.

### 6. Expand Exact Fixture Generation Carefully

Priority: medium.

Current brute-force generators are correct for small fixtures and easy to audit. If the
fixture corpus grows, exact specialized algorithms can increase scale without using
best-known values.

Candidates:

- Held-Karp dynamic programming for exact TSP on modest `n`.
- Pseudo-polynomial dynamic programming for integer knapsack where weights/capacities are
  bounded.
- SDP branch-and-bound references such as BiqMac for MaxCut/BQP instances beyond brute
  force.

Implementation hygiene:

- Keep brute force as a cross-check for the overlapping small regime.
- Record solver versions, command lines, seeds when applicable, and SHA-256 checksums for
  generated corpora.
- Store witness states and recompute objectives from input models.

### 7. Consider A Cached Adjacency View For Repeated Local-Field Work

Priority: low until a CPU-side sampler or inspector needs it.

`IsingModel.local_field` scans all couplers, which is simple and correct. For repeated local
field calculations, an adjacency map gives `O(degree)` updates and would better match Gibbs
update workloads. The current THRML path performs sampling outside this Python method, so
this is a targeted optimization for future inspectors, CPU fallbacks, or preprocessing
rules.

Implementation hygiene:

- Use a private topology cache or explicit helper rather than changing the public Ising IR
  shape.
- Verify local-field equivalence against direct energy deltas on random small models.

### 8. Keep The Current Block Coloring Direction

Priority: maintain, benchmark before changing.

The block-coloring path already had a large same-day speedup and matches THRML's variable
block interface. Edge-coloring advances such as near-linear Vizing algorithms are interesting
for edge-update formulations, but they do not directly partition variables into independent
sets for the current THRML API:
https://arxiv.org/abs/2410.05240 and https://arxiv.org/abs/2510.12619.

If block construction becomes a bottleneck again, benchmark smallest-last coloring as an
optional sparse-graph heuristic against DSATUR on color count, lowering time, sampling
throughput, and final objective quality.

### 9. Add Replica Cluster Moves As A Tempering Accelerator

Priority: high after basic parallel tempering, medium before it.

External statistics justify implementing the feature, but they do not prove a Gibbsiq speedup
until the local kernel is benchmarked against fixed-beta THRML and plain parallel tempering.
The relevant published numbers are:

| Source | Workload | Reported statistic | Gibbsiq relevance |
| --- | --- | --- | --- |
| Houdayer 2001, https://arxiv.org/abs/cond-mat/0101116 | 2D +/-J Edwards-Anderson spin glass | Cluster updates give a speed gain of several orders of magnitude and equilibrate systems of size `100^2` down to `T = 0.1`. | Supports cluster moves for sparse low-dimensional spin-glass-like QUBO families. |
| Zhu, Ochoa, Katzgraber 2015, https://arxiv.org/abs/1501.05630 | 2D, 3D, and Chimera spin glasses | Isoenergetic cluster moves speed thermalization by at least one order of magnitude; the reported `t_PT / t_PT+ICM` ratio increases with system size and the plotted range reaches `10^3`. | Strongest direct evidence for PT plus replica cluster moves in Gibbsiq-like sparse/frustrated instances. |
| Aramon et al. 2019, https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2019.00048/full | Sparse 2D and fully connected spin-glass QUBO benchmarks | PT+ICM is described as highly effective for low-dimensional spin-glass-like problems. The same paper warns that ICM gives no benefit on fully connected graphs because clusters span the whole system; its dense-graph 100x result is for Digital Annealer hardware, not for ICM. | Gives the key guardrail: use cluster moves where clusters stay local; skip them when the graph is dense enough that clusters percolate. |
| Komura and Okabe 2012, https://arxiv.org/abs/1110.0899 | GPU Wolff update on 2D and 3D Ising models | CUDA Wolff is `5.60x` faster than a CPU core for 2D `L = 4096` and `7.90x` faster for 3D `L = 256`. | Shows direct cluster kernels can exploit GPU parallelism on regular models. |
| Komura and Okabe 2012, https://arxiv.org/abs/1202.0635 | GPU Swendsen-Wang on 2D classical spin systems | Reports `2.51 ns` per spin flip for Ising (`q = 2`) at `L = 4096`; `12.4x` CPU speedup for `q = 2` and `35.6x` for `q = 6`. | Supports specialized SW/Wolff kernels for ferromagnetic or gauge-balanced cases. |
| Weigel 2011, https://arxiv.org/abs/1105.5804 | GPU cluster labeling and updates | Local spin updates can see `10^2` to `10^3` GPU speedups, but connected-component labeling makes cluster updates harder to parallelize. | Explains why a TSU/GPU implementation needs a JAX-friendly cluster-labeling kernel instead of Python graph walks. |

Plain Swendsen-Wang and Wolff cluster moves are attractive because they update many
correlated spins at once. The original Swendsen-Wang paper reports an efficient method for
large systems near criticality:
https://link.aps.org/doi/10.1103/PhysRevLett.58.86. Wolff's single-cluster update similarly
updates large clusters near criticality:
https://pubmed.ncbi.nlm.nih.gov/10040213/.

For Gibbsiq's generic QUBO/Ising target, the safer cluster direction is replica cluster
movement rather than a direct Swendsen-Wang/Wolff replacement. Standard Swendsen-Wang and
Wolff are most natural for ferromagnetic or gauge-balanced models. In Gibbsiq's sign
convention, an attractive pair has `J_ij < 0`, so the usual ferromagnetic bond rule maps to
opening a satisfied attractive edge with probability `1 - exp(-2 * beta * abs(J_ij))`. Generic
QUBO instances contain mixed-sign and frustrated couplers, arbitrary linear fields, and
constraint penalties, so a direct cluster flip can be invalid or can create giant low-value
clusters.

The better fit is an isoenergetic replica cluster move, also known as a Houdayer-style move.
Houdayer reports several orders of magnitude speedup for two-dimensional spin glasses:
https://arxiv.org/abs/cond-mat/0101116. Zhu, Ochoa, and Katzgraber extend this family to
spin glasses in any dimension and report at least an order-of-magnitude thermalization
speedup, including on Chimera topology:
https://arxiv.org/abs/1501.05630.

Implementation hygiene:

- Add this after the parallel-tempering skeleton or as a sibling feature that requires two
  replicas at the same beta.
- Use fixed-beta pairs. Build a disagreement mask `q_i = s_i^(a) * s_i^(b)`; choose a
  connected component of `q_i = -1`; swap that component between replicas.
- Treat the move as a proposal with an invariant check. Recompute
  `E(replica_a) + E(replica_b)` before and after; accept automatically only when the total
  energy is unchanged within tolerance. If a generalized cluster proposal is added later,
  use an explicit Metropolis-Hastings correction against the full canonical energy.
- Record cluster size, cluster fraction, energy delta, accepted/rejected status, beta,
  replica ids, RNG seed stream, and per-temperature move counts.
- Add percolation guards. Skip or downweight moves when clusters are trivial, for example
  size 0, size 1 for large models, or more than 50-70 percent of variables. Giant clusters
  often mean the move is close to swapping entire replicas and gives little additional
  exploration.
- Start with sparse spin-glass fixtures. Benchmark against fixed-beta THRML and against
  plain parallel tempering on ESS, R-hat status, ground-state hit rate, round-trip rate, and
  wall time.
- Keep direct Swendsen-Wang/Wolff as a specialized optional kernel for ferromagnetic,
  antiferromagnetic-bipartite, or gauge-balanced instances. A signed-graph balance check can
  decide whether the model can be transformed into an all-attractive coupling system.
- For GPU/TSU simulation hygiene, avoid Python graph walks in the hot path. Cluster labeling
  needs a JAX-friendly connected-component or union-find-style kernel if it becomes part of
  THRML execution. GPU cluster updates are feasible, but connected-component labeling is the
  hard part; Weigel's GPU study calls out this non-local step:
  https://arxiv.org/abs/1105.5804.
- Keep block Gibbs as the correctness baseline. Cluster moves should be an additional
  transition kernel with its own metadata, not a replacement for the audited single-site
  conditional sign.

Rejected cluster shortcut:

- Do not apply ordinary Swendsen-Wang or Wolff globally to arbitrary QUBO instances. The
  assumptions behind their rejection-free update do not hold for the mixed-sign frustrated
  models that Gibbsiq is expected to lower.

## Rejected Alternatives

- Replacing THRML block Gibbs with simulated bifurcation as the primary runtime. Simulated
  bifurcation is a strong optimizer and baseline, but it does not provide the same sampling
  diagnostics contract.
- Adding NetworkX as a required dependency for graph coloring. The project already has a
  fast deterministic stdlib implementation and a zero-required-dependency core.
- Trusting ArviZ raw outputs as final diagnostics. ArviZ is a reference, but Gibbsiq needs
  explicit failure statuses and family-scoped flags for auditability.
- Using "best known" benchmark values without sources. The oracle contract requires
  witnesses and objective recomputation.
- Treating TSU denoising energy claims as QUBO optimization speedup evidence. That would
  overstate the current evidence.

## Follow-Up Items

1. Draft a parallel-tempering design note with metadata schema, tests, and THRML integration
   points.
2. Draft a preprocessing certificate schema before adding any reduction implementation.
3. Add a baseline-adapter design for D-Wave samplers, OpenJij, simulated bifurcation, and
   MQLib.
4. Benchmark stdlib diagnostics against an optional array backend on long synthetic traces.
5. Expand the claims-evidence map after any implementation so every speed or accuracy claim
   has a test, fixture, or primary-source citation.
6. Add a cluster-move design note covering Houdayer/isoenergetic moves, percolation guards,
   cluster metadata, and signed-graph balance checks for specialized Swendsen-Wang/Wolff
   kernels.

## Verification

- Read the required project context before editing technical claims:
  `PROJECT_BRIEF.md`, `spec.md`, `CLAUDE.md`, `reference/README.md`,
  `reference/glossary.md`, `reference/claims-evidence-map.md`,
  `reference/08-evaluation/equation-audit.md`,
  `reference/08-evaluation/evaluation-framework.md`,
  `reference/08-evaluation/agentic-evaluation-research.md`,
  `reference/06-benchmarks/ground-truth-datasets.md`, and
  `tools/generate_ground_truth.py`.
- Inspected the source files listed in the inventory with `rg -n` and `Get-Content`.
- Used web research from primary or implementation sources for THRML, TSU framing, dimod,
  ArviZ, Vehtari et al., parallel tempering, graph coloring, QUBO preprocessing, penalty
  selection, cluster algorithms, and baseline solvers.
- This entry is documentation-only. No production solver implementation was changed.
