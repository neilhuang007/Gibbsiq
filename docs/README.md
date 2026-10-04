# User guide

Start with the [quickstart](../src/gibbsiq/data/qualification/QUICKSTART.md), then
choose the guide for your workflow.

| Task | Guide |
| --- | --- |
| Install the core or numerical integrations | [Installation](installation.md) |
| Run an experiment from Python | [Qualification workflow](qualification/workflow-contract.md) |
| Understand metrics and confidence intervals | [Contracts and statistics](qualification/foundations-contract.md) |
| Compare results in CI | [Regression checks](qualification/regression-workflow-contract.md) |
| Select sampling settings | [Policy search](qualification/policy-search-contract.md) |
| Evaluate a Z1T model | [Z1T walkthrough](qualification/z1t.md) |
| Compare policies on trained weights | [Checkpoint study](qualification/trained-checkpoint-verification.md) |
| Integrate THRML or Torx | [Backend adapters](qualification/interoperability-contract.md) |
| Measure cost and timing | [Profiling](qualification/profiling-contract.md) |
| Retain or recover experiments | [Maintenance](qualification/maintenance.md) |
| Run an independent pilot | [Pilot handoff](qualification/independent-pilot.md) |

For model integrations, see the [adapter interface](qualification/model-adapter-contract.md),
[evaluation semantics](qualification/model-evaluation-contract.md), and
[stochastic profiles](qualification/stochastic-profile-contract.md).

Developers can use the [contributing guide](../CONTRIBUTING.md),
[architecture decisions](adr/0001-qualification-boundary.md), and
[release checklist](qualification/local-release-contract.md).
