# Changelog

## Unreleased

- Add `examples/tsp_qubo_ground_state.py`, which compiles a four-city traveling
  salesman problem with `compile_tsp`, checks the penalty certificate, finds the
  exact ground state by enumerating all 65,536 states, samples with a seeded
  reference run or `--backend thrml`, and reports diagnostics.
- Add exhaustive oracle tests for TSP ground states and knapsack instances in
  `test_constraints.py`.
- Speed up cluster moves, exact Boltzmann and transition kernels, sample result
  construction, energy evaluation, and diagnostics. Outputs match the previous
  implementation bit for bit. Median cluster move time fell from 352.6 ms to
  6.2 ms, and median sample result construction fell from 2433.6 ms to 443.0 ms,
  measured with `tools/benchmark_performance_baseline.py --repeat 5`.
- Add spin-based energy methods to `IsingModel`: `energy_from_spins`,
  `interaction_energy_from_spins`, `energy_and_interaction`, and
  `energy_and_interaction_from_spins`.
- Add `_validation.py` with shared standard-library validators for canonical
  JSON, variable positions, bounded integers, finite and nonnegative numbers,
  and inverse temperature. Core modules use these validators in place of local
  copies.
- Add `_reads.py` with a `reads_by_chain` helper shared by the reference sampler
  and the THRML runtime. The THRML runtime decodes chains once and reuses the
  interaction trace during parallel tempering.
- Change sample alignment for custom mappings so duplicate exact keys among
  non-variable extra keys no longer raise. Plain dictionaries behave as before.
- Add seven cases to `tools/benchmark_performance_baseline.py`:
  `sample_result_from_model`, `freeze_thaw_json_evidence`, `compile_tsp`,
  `exact_transition_kernel`, `verify_empirical_distribution`, `cluster_move`,
  and `exact_boltzmann_distribution`.
- Add equivalence tests for exact distributions, verification kernels, and
  spin-based model paths, and tests for the shared validators.
- Consolidate the test suite. The two conformance tests from
  `test_stage_01_core_model_compatibility.py` move into
  `test_model_compatibility.py`, `test_stage3_end_to_end_validation.py` becomes
  `test_thrml_diagnostics_end_to_end.py`, and duplicate or constant assertions
  are removed.
- Remove the unused `_replica_exchange_log_ratio` helper from the THRML runtime
  and the unused `dimod.*` mypy override from `pyproject.toml`.
- Pin UTF-8 on both sides of the qualification CLI subprocess in
  `test_qualification_cli.py`, so the inspection test no longer depends on the
  locale codec of the parent shell.
- Restate the project as QUBO and Ising optimization on THRML with exact
  oracles and mixing diagnostics in the README, the user guide index, and the
  package description. The qualification workflow is documented as a secondary
  capability.

## 0.2.0a1 — 2026-10-04

- Add stochastic qualification with frozen run plans, independent references,
  confidence intervals, and reproducible evidence bundles.
- Add `gibbsiq qualify`, `inspect`, `compare`, `tune`, and `doctor`.
- Add THRML, Torx, and Z1T adapters with pinned integration environments.
- Add complete-model evaluation, document-aware token losses, projection
  observations, and trained-checkpoint verification tools.
- Add a frozen equal-work trained-checkpoint policy comparison with explicit
  uncertainty, per-operation sampling budgets, and measured CPU cost boundaries.
- Add policy search with separate calibration, development, and evaluation
  inputs, plus validated policy export.
- Add cost accounting, synchronized timing, and regression reports.
- Add PyPI Trusted Publishing of tested CI artifacts, with artifact hashes
  and an isolated installation check after upload.
- Accept equivalent Windows and Unix line endings in pinned backend sources.
- Preserve the QUBO/Ising APIs, integer `SampleResult`, and
  `gibbsiq-evaluate` command.
