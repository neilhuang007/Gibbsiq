# Research Gaps and Integration Risks

These are explicit gaps found during research and implementation audits. THRML's public
documentation currently describes a JAX-based GPU simulator for future Extropic hardware;
hardware execution requires separate evidence.

## THRML Does Provide

- JAX-based probabilistic graphical model sampling.
- Efficient block Gibbs sampling abstractions.
- Blocks, factors, and programs as the central architecture.
- Discrete EBM utilities, including spin/Ising-like examples.
- `SamplingSchedule` with warmup, sample count, and steps between samples.
- GPU-oriented array/PyTree execution style.

## Not Clearly Provided by THRML

- A dimod-compatible `Sampler` implementation.
- Direct QUBO/BQM ingestion and conversion utilities.
- PyQUBO-like symbolic modeling or decoding.
- General block partitioning heuristics for optimization instances.
- Built-in convergence diagnostics such as autocorrelation, ESS, R-hat, or rank plots.
- Built-in solution diversity, mode collapse, or stuck-chain detection.
- Inspector/report UI comparable to D-Wave Inspector.
- Baseline wrappers for `neal`, OpenJij, simulated bifurcation, or exact solvers.
- Reproducible benchmark suite definitions.

## Design Consequence

Treat THRML as the execution substrate, not the whole optimization product. Gibbsiq should
own the missing optimization infrastructure around THRML:

- `compile_qubo` / `compile_bqm` lowering.
- `THRMLSampler` public API.
- graph-aware block construction for optimization instances.
- schedule, seed, initialization, and multi-chain configuration.
- trace capture and canonical energy recomputation.
- Stable result object and metadata schema.
- Diagnostics and telemetry pipeline.
- Inspector/report layer.
- Baseline wrappers and benchmark harness.

This is not a pivot to a backend-agnostic diagnostics library. dimod and baseline
interoperability are adoption and comparison bridges. The central goal remains a
THRML-native optimization stack.

The durable part of that stack is independent verification and diagnostics. A hardware vendor
cannot credibly own the trust layer for its own device, so audited conversion, sampler-health
diagnostics, and witness-recomputing benchmark oracles retain value even if ingestion and
lowering are later absorbed by an Extropic-owned optimization SDK. The result schema,
diagnostic inputs, and benchmark oracle are kept backend-portable at the architectural level
as a hedge: execution stays THRML-first, and the same audited artifacts apply to the wider
Ising-machine field if the THRML hardware path is delayed. The accurate analogy for this
layer is Ocean and dimod for D-Wave plus ArviZ for Stan and PyMC, applied to the THRML
ecosystem.

## High-Risk Areas

- Schedule quality: Gibbs samplers can fail to mix on hard, frustrated, or disconnected-energy landscapes.
- Block construction: bad block partitioning can destroy mixing or waste GPU work through padding.
- Diagnostic interpretation: optimization runs are not posterior inference; ESS/R-hat ideas need careful adaptation to energy, objective, and state features.
- Benchmark fairness: comparing THRML to SA/SQA/SB requires fixed seeds, fixed time budgets, repeated trials, and honest reporting of wall-clock plus quality.
- Python version: `pyproject.toml` and THRML's installation docs both state Python `>=3.10`;
  optional runtime tests must continue to cover the Python/JAX/THRML version matrix actually
  used by CI and benchmark runs.
- Ecosystem timing: THRML is young. Avoid unverified speed claims. Build the optimization
  layer while the API surface is still small enough to influence.
- Ingestion commoditization: model ingestion and IR-to-THRML lowering could be absorbed by an
  Extropic-owned optimization SDK. Keep the independent verification and diagnostics
  contracts, which a vendor cannot self-certify, as the durable differentiator, and keep those
  contracts backend-portable.
- Novelty scope: current dimod documentation exposes ESS helpers for arrays and `SampleSet`
  objects. Gibbsiq's defensible contribution is the combined optimization audit contract:
  conversion checks, explicit degenerate diagnostic states, raw evidence, anti-echo evaluation,
  and witness recomputation. The presence of ESS alone is not novel.
