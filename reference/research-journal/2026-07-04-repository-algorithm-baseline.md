# 2026-07-04 - Repository Algorithm Baseline

## Paper Hook

Feeds the optimization-roadmap and artifact-evidence sections. This entry records the
repository-wide algorithm inventory, the primary sources checked for faster or more accurate
alternatives, and the local baseline artifacts available for future benchmark comparisons.

## Context

The user requested a diagnosis of the algorithms and calculations in the repository, with
extensive web research for faster or more accurate alternatives and a benchmark baseline for
performance comparison. The request described TSU as a GPU architecture. The Extropic source
material describes TSU as a thermodynamic sampling unit that samples from programmable
probability distributions; THRML is the JAX block-Gibbs software layer used to prototype the
sampling path. Gibbsiq should therefore avoid GPU-speedup claims and keep TSU-specific claims
limited to what has been measured through THRML or a future hardware backend.

## Algorithm Inventory

The repository currently computes these core quantities:

- Model normalization: `compile_qubo`, `compile_ising`, and `compile_bqm` normalize user
  inputs into the canonical Ising IR and preserve offsets.
- Energy and conditionals: `IsingModel.energy`, `local_field`, and
  `conditional_probability` implement the audited energy, local field, and Gibbs conditional
  sign.
- Block construction: `color_blocks` builds independent variable blocks using an edgeless
  path, a bipartite BFS path, heap-based DSATUR fallback, topology caching, and partition
  validation.
- THRML execution: `THRMLSampler.sample` lowers the IR to THRML nodes, factors, and blocks,
  runs fixed-beta block Gibbs with optional warmup beta ladders, decodes chain samples,
  recomputes energies through the IR, and records traces and timing metadata.
- Diagnostics: `compute_diagnostics` assembles energy summaries, Geyer ESS and tau, plain
  split R-hat, rank-normalized folded split R-hat, diversity metrics, magnetization traces,
  distance-to-best traces, and family-scoped flags.
- Benchmark verification: `benchmark_oracle` recomputes objectives from witness states for
  MaxCut, number partition, knapsack, TSP, and Ising/SK fixtures.
- Benchmark bridging: `benchmark_bridge` lowers supported fixtures to Ising and converts
  `SampleResult` objects into witness-backed oracle candidates.
- Ground-truth generation: `tools/generate_ground_truth.py` brute-forces small MaxCut,
  number partition, knapsack, TSP, SK spin glass, and structured MaxCut fixtures.
- Research benchmark: `tools/benchmark_cluster_moves.py` compares plain parallel tempering
  against parallel tempering plus isoenergetic cluster moves on fixed seeded grid spin
  glasses.

## Source-Backed Optimization Candidates

1. Parallel tempering remains the first production sampler upgrade. Hukushima and Nemoto's
   exchange Monte Carlo source states that replicas at different temperatures exchange
   configurations so low-temperature systems can escape local minima. This maps directly to
   the open Stage 2 exit criterion.

2. Isoenergetic cluster moves are the strongest follow-on sparse spin-glass accelerator.
   Zhu, Ochoa, and Katzgraber report that their cluster algorithm works for Ising spin
   glasses in any dimension and speeds thermalization by at least one order of magnitude in
   hard temperature regimes. The local harness records a Gibbsiq-specific pilot, but
   production claims still require a THRML/JAX implementation.

3. QUBO preprocessing can reduce problem size before sampling. Lewis and Glover report rules
   that identify variables whose optimal values can be predetermined and verify improvements
   in solution quality and time to solution. Gibbsiq needs this as an optional certificate
   layer that records fixed variables, offset deltas, rejected rules, and witness expansion.

4. Penalty and one-hot encoders are required for constrained benchmark coverage. Ayodele's
   penalty-weight source records the central failure mode: weak penalties return infeasible
   solutions, while excessive penalties can slow convergence. Gibbsiq should record penalty
   search, feasibility rates, and rejected values.

5. External optimizers belong in the baseline layer. D-Wave's sampler docs expose beta
   schedules, seeds, reads, sweeps, and timing categories; OpenJij and simulated bifurcation
   provide fast Ising/QUBO optimizers; MQLib provides MaxCut/QUBO heuristics. These tools
   optimize the same objective but do not replace Gibbsiq's THRML trace and diagnostic
   contract.

6. Diagnostics can gain an optional array backend. ArviZ is the implementation reference for
   R-hat and ESS variants, but Gibbsiq must preserve its explicit constant-trace,
   insufficient-data, and non-finite-input statuses rather than returning library NaN or
   healthy-looking degenerate values.

7. Exact fixture generation can scale with specialized exact methods. BiqMac supplies exact
   SDP branch-and-bound for MaxCut/BQP. It is a candidate source for larger proven instances
   if every imported value includes a witness or independent objective recomputation.

## Primary Sources Checked

- Extropic TSU framing: `https://extropic.ai/writing/thermodynamic-computing-from-zero-to-one`
- THRML docs: `https://docs.thrml.ai/en/latest/`
- THRML source repository: `https://github.com/extropic-ai/thrml`
- Parallel tempering / exchange Monte Carlo: `https://arxiv.org/abs/cond-mat/9512035`
- Isoenergetic cluster moves: `https://arxiv.org/abs/1501.05630`
- QUBO preprocessing: `https://arxiv.org/abs/1705.09844`
- Penalty weights: `https://arxiv.org/abs/2206.11040`
- D-Wave simulated annealing sampler docs:
  `https://docs.dwavequantum.com/en/latest/ocean/api_ref_samplers/generated/dwave.samplers.SimulatedAnnealingSampler.sample.html`
- ArviZ diagnostics source docs:
  `https://python.arviz.org/en/v0.21.0/_modules/arviz/stats/diagnostics.html`
- NetworkX graph-coloring source docs:
  `https://networkx.org/documentation/stable/_modules/networkx/algorithms/coloring/greedy_coloring.html`
- BiqMac exact MaxCut/BQP solver: `https://biqmac.aau.at/`
- MQLib source repository: `https://github.com/MQLib/MQLib`

## Baseline Artifacts

The benchmark baseline is not a production THRML speed claim. It is a preserved local
comparison harness for future algorithm work.

- Existing clean local cluster-move benchmark:
  `reference/06-benchmarks/artifacts/cluster-move-benchmark-2026-07-04-clean.json`
  with SHA-256 `c47f4eedd9287d076c2fc977d37500444a3794744a70e87560f541fa0392ab79`.
- Current-session benchmark smoke:
  `reference/06-benchmarks/artifacts/cluster-move-benchmark-2026-07-04-current-smoke.json`
  with SHA-256 `570294927a558ded905cf8aae2ef5e7b641c6da9e253ab7c3474016022aabad8`.
- The smoke benchmark used `6x6` grids, two instances, 20 sweeps, and six beta values. It
  proves that the harness still runs. It is too small and too noisy for any speedup claim.

## Decisions

1. Keep production solver code unchanged in this session. The user asked for diagnosis,
   research, and baseline preservation; project instructions restrict solver implementation
   unless explicitly requested.
2. Treat parallel tempering as the first implementation target because it improves mixing
   while preserving the THRML block-Gibbs execution model.
3. Treat isoenergetic cluster moves as a post-PT accelerator guarded by graph-density and
   cluster-size metadata.
4. Treat QUBO preprocessing as optional and certificate-backed because it changes the model
   boundary seen by the sampler.
5. Treat D-Wave samplers, OpenJij, simulated bifurcation, MQLib, and BiqMac as baselines or
   fixture sources, not replacements for the THRML-native runtime.

## Rejected Alternatives

- Claiming TSU/GPU speedup from Extropic positioning material. The repository has no
  measured TSU hardware backend result.
- Replacing THRML block Gibbs with a classical optimizer. This would lose the sampling trace
  contract and diagnostic semantics.
- Adding required dependencies for speed. The core package remains zero-dependency; fast
  backends should be optional extras or research tools.
- Using best-known benchmark values as correctness targets. Witness recomputation and exact
  source classification remain mandatory.

## Verification

- Required project context read: `PROJECT_BRIEF.md`, `spec.md`, `CLAUDE.md`,
  `reference/README.md`, `reference/glossary.md`, `reference/claims-evidence-map.md`,
  `reference/08-evaluation/equation-audit.md`,
  `reference/08-evaluation/evaluation-framework.md`,
  `reference/08-evaluation/agentic-evaluation-research.md`,
  `reference/06-benchmarks/ground-truth-datasets.md`,
  `tools/generate_ground_truth.py`, and `reference/research-journal/gotchas-and-todo.md`.
- Source inventory command: `rg "^(class|def) " src tools test_suite/tests -n`.
- Full test suite command:
  `$env:PYTHONPATH = "src"; py -3 -m unittest discover -s test_suite/tests`.
  Result: 269 tests pass, 54 skipped for optional extras.
- Benchmark smoke command:
  `py -3 tools/benchmark_cluster_moves.py --sizes 6 --instances 2 --sweeps 20 --beta-count 6 --out reference/06-benchmarks/artifacts/cluster-move-benchmark-2026-07-04-current-smoke.json`.
  Result: artifact written with SHA-256
  `570294927a558ded905cf8aae2ef5e7b641c6da9e253ab7c3474016022aabad8`.
- Syntax check command: `py -3 -m py_compile tools/benchmark_cluster_moves.py`.
  Result: pass.
- Baseline checksum command:
  `Get-FileHash -Algorithm SHA256 reference/06-benchmarks/artifacts/cluster-move-benchmark-2026-07-04-clean.json`.
  Result: `c47f4eedd9287d076c2fc977d37500444a3794744a70e87560f541fa0392ab79`.
