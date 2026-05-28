# Gibbsiq Impact Audit

Snapshot date: 2026-05-28.

## Verdict

Gibbsiq can make a real impact, but not as "another QUBO solver" and not because THRML alone is a moat.

The strongest version of the project is a diagnostics-first optimization layer: a `dimod`-compatible sampler/composite that accepts QUBO, Ising, and BQM inputs, runs one or more solvers, and explains whether failures come from the formulation, schedule, sampler dynamics, penalties, or solver choice.

The weaker version is a THRML-only QUBO wrapper with plots. That would likely be incremental.

## Why The Need Is Real

- MCMC and Gibbs chains produce correlated samples, so raw sample counts can be misleading. R-hat, ESS, autocorrelation, and trace-style checks are relevant warning tools, even if they do not prove optimality.
- QUBO and Ising solver performance is strongly problem-dependent. Fair comparison requires fixed seeds, repeated trials, wall-clock timing, solver versions, hardware metadata, and raw artifacts.
- Recent penalty and encoding work reinforces that many QUBO failures are formulation failures: bad penalty scaling, Big-M effects, feasibility cliffs, coefficient dynamic range, and encodings that reshape the energy landscape.
- Existing solver stacks often report best samples and timing, but they rarely provide a single structured contract that combines formulation audit, run diagnostics, baseline comparison, and remediation guidance.

## Prior Art And Novelty Risk

The project should not claim a blank-space market.

- `dimod` already defines the de facto Python BQM interface and sampler contract.
- D-Wave Problem Inspector provides mature visualization for submitted quantum annealing problems, embeddings, responses, warnings, and QPU parameters.
- D-Wave preprocessing includes roof-duality-style lower bounds and variable fixing.
- OpenJij provides SA/SQA tooling and benchmark metrics such as time to solution, success probability, residual energy, and error bars.
- Simulated bifurcation tools and Toshiba SQBM-style systems already compete strongly on QUBO/Ising optimization.
- Fixstars Amplify Benchmark and similar suites already frame solver comparison as a first-class concern.
- QUBOLite and QuboAuditor are direct warnings that QUBO analysis/preprocessing/formulation audit is already becoming a tool category.

Conclusion: a generic "QUBO dashboard" is not enough. Gibbsiq must be materially better by integrating with the ecosystem, returning machine-readable diagnostics, and suggesting concrete repair actions.

## THRML Assessment

THRML is credible as a young JAX block-Gibbs runtime for probabilistic graphical models and energy-based models. It is a plausible research backend for sparse Ising, categorical, higher-order, and future thermodynamic-hardware experiments.

It is not yet evidence of a generic QUBO optimization advantage.

Practical implications:

- Put THRML behind an adapter interface, not at the center of every public abstraction.
- Keep classical baselines first-class: simulated annealing, OpenJij, simulated bifurcation, tabu/local search, exact small-instance validation, and later MILP/CP-SAT where useful.
- Preserve structure as long as possible. If future thermodynamic hardware benefits from higher-order, categorical, or graph-structured models, flattening everything into dense binary QUBO may destroy the advantage.
- Treat THRML as a research lane until benchmarks prove where it wins.

## Highest-Impact Product Shape

1. Accept `dimod.BinaryQuadraticModel`, QUBO dicts, Ising `(h, J)`, and internal structured formulations.
2. Run pre-solve formulation diagnostics:
   - coefficient dynamic range;
   - penalty dominance;
   - infeasible low-energy states on small probes;
   - graph density/connectivity;
   - constraint contribution breakdown;
   - expected precision issues;
   - encoding expansion cost.
3. Wrap multiple samplers and normalize results into one schema.
4. Return ordinary `SampleSet` compatibility while placing diagnostics in structured metadata.
5. Produce reports that answer solver questions, not decorative plots:
   - did the run improve;
   - did chains disagree;
   - did the sample distribution collapse;
   - did penalties dominate the objective;
   - did any baseline solve it faster;
   - should the user rescale, re-encode, restart, reheat, or switch solver.
6. Calibrate warning thresholds against benchmark artifacts instead of inventing constants.

## Go / No-Go Criteria

Gibbsiq is worth pursuing if v0 can demonstrate all of the following:

- It catches known-bad QUBO formulations before or during solving.
- It explains at least three distinct failure modes with actionable next steps.
- It interoperates with `dimod` enough that users do not need to abandon existing BQM workflows.
- Its reports compare THRML against at least two strong baselines on the same instances.
- Its diagnostic flags correlate with measurable solver outcomes across repeated runs.

Gibbsiq should be de-scoped or repositioned if:

- THRML is the only backend and is not competitive on the selected instances.
- diagnostics remain descriptive but not actionable;
- metrics are uncalibrated and produce noisy warnings;
- the tool cannot distinguish formulation failure from solver failure;
- it duplicates QuboAuditor/QUBOLite/Ocean features without integration or remediation.

## Critical Architecture Changes Recommended

- Rename the core public concept from "THRML solver" to "diagnostic sampler/composite"; keep `THRMLSampler` as one backend.
- Make `SampleResult` convertible to and from `dimod.SampleSet`.
- Add a `FormulationReport` before the runtime stage.
- Add a benchmark metadata contract before implementing inspector visuals.
- Define `num_reads`, chains, restarts, samples, and sweeps precisely.
- Record all solver versions, seeds, schedules, and hardware metadata.
- Separate MCMC-only diagnostics from non-MCMC solver diagnostics.
- Add threshold provenance to every failure flag.

## Bottom Line

The project is important if it helps users answer: "is my solver bad, my formulation bad, or my sampling run untrustworthy?"

That is a valuable gap. The current docs point in the right direction, but the impact depends on validating diagnostics against real failures and positioning THRML as one backend inside a broader solver-quality system.

## Sources Consulted

- THRML docs: https://docs.thrml.ai/
- THRML repository: https://github.com/extropic-ai/thrml
- D-Wave `dimod` docs: https://docs.dwavequantum.com/en/latest/ocean/api_ref_dimod/
- D-Wave Inspector docs: https://docs.dwavequantum.com/en/latest/ocean/api_ref_inspector/
- OpenJij homepage/docs: https://www.openjij.org/
- Simulated bifurcation docs: https://simulated-bifurcation-algorithm.readthedocs.io/en/v2.0.0/
- Fixstars Amplify Benchmark: https://github.com/fixstars/amplify-benchmark
- QuboAuditor: https://github.com/firaskhabour/QuboAuditor
- QUBOLite: https://arxiv.org/abs/2509.21321
- Alleviating the Quantum Big-M Problem: https://www.nature.com/articles/s41534-025-01067-0
- Thermodynamic significance of QUBO encoding: https://arxiv.org/abs/2601.04402
- Scalable determination of penalization weights for approximate QUBO solvers: https://arxiv.org/abs/2604.02416
