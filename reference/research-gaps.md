# Research Gaps and Integration Risks

These are explicit gaps found during the first research pass. Do not assume they are solved by THRML unless later source inspection proves otherwise.

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

Treat THRML as the execution substrate, not the whole product. Gibbsiq should own:

- `compile_qubo` / `compile_bqm` lowering.
- `THRMLSampler` public API.
- Stable result object and metadata schema.
- Diagnostics pipeline.
- Inspector/report layer.
- Baseline wrappers and benchmark harness.

## High-Risk Areas

- Schedule quality: Gibbs samplers can fail to mix on hard, frustrated, or disconnected-energy landscapes.
- Block construction: bad block partitioning can destroy mixing or waste GPU work through padding.
- Diagnostic interpretation: optimization runs are not posterior inference; ESS/R-hat ideas need careful adaptation to energy, objective, and state features.
- Benchmark fairness: comparing THRML to SA/SQA/SB requires fixed seeds, fixed time budgets, repeated trials, and honest reporting of wall-clock plus quality.
- Python version: local `pyproject.toml` currently says Python `>=3.13`, while THRML docs state Python `>=3.10`; verify THRML compatibility with Python 3.13 before choosing dependencies.

