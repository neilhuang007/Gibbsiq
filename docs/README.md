# User guide

Gibbsiq compiles QUBO and Ising problems, samples them with the standard-library
reference sampler or the THRML backend, and checks the result against exact
references and mixing diagnostics. Start with the model conventions and the TSP
example. The qualification guides cover the experiment comparison workflow.

## Optimization

| Task | Guide |
| --- | --- |
| Install the core or numerical integrations | [Installation](installation.md) |
| Check energy signs, conversions, and sampling probabilities | [Model conventions](model-conventions.md) |
| Solve a QUBO such as a TSP and check the result against an exact optimum | [TSP example](../examples/tsp_qubo_ground_state.py) |
| Integrate THRML or Torx | [Backend adapters](qualification/interoperability-contract.md) |
| Measure cost and timing | [Profiling](qualification/profiling-contract.md) |

## Stochastic qualification

| Task | Guide |
| --- | --- |
| Run the command-line quickstart | [Quickstart](../src/gibbsiq/data/qualification/QUICKSTART.md) |
| Run an experiment from Python | [Qualification workflow](qualification/workflow-contract.md) |
| Understand metrics and confidence intervals | [Contracts and statistics](qualification/foundations-contract.md) |
| Compare results in CI | [Regression checks](qualification/regression-workflow-contract.md) |
| Select sampling settings | [Policy search](qualification/policy-search-contract.md) |
| Evaluate a Z1T model | [Z1T walkthrough](qualification/z1t.md) |
| Compare policies on trained weights | [Checkpoint study](qualification/trained-checkpoint-verification.md) |
| Retain or recover experiments | [Maintenance](qualification/maintenance.md) |

For model integrations, see the [adapter interface](qualification/model-adapter-contract.md),
[evaluation semantics](qualification/model-evaluation-contract.md), and
[stochastic profiles](qualification/stochastic-profile-contract.md).

Developers can use the [contributing guide](../CONTRIBUTING.md),
[architecture decisions](adr/0001-qualification-boundary.md), and
[release checklist](qualification/local-release-contract.md).
