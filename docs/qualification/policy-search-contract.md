# Policy search

Policy search chooses sampling settings that meet a quality contract while
reducing a declared cost objective.

```console
gibbsiq tune --example tiny-z1t --output runs/tiny-search --json
```

Install the [numerical integration environment](../installation.md) first.
The dependency-free `no-feasible-policy` example demonstrates a search whose
candidates fail its quality requirement.

## Search procedure

1. Declare candidates, baseline, controls, cost objective, and compute budget.
2. Screen candidates on calibration inputs.
3. Compare surviving candidates on development inputs.
4. Freeze the selected candidate, baseline, and error allocation.
5. Evaluate the frozen selection on held-out inputs.
6. Export a policy when final qualification passes.

All attempts and candidate decisions remain in the search result. Each dataset
split has an explicit identity.

## Python interface

`SearchSpace` and `Candidate` describe supported settings. `SearchPlan` fixes
the workload, splits, objective, and budgets. `run_search` executes it, and
`inspect_search` verifies its saved result.

Use `resolve_policy` to apply an exported policy to the matching workload,
backend, profile, operation map, and input identity. Policy settings are data:
a fallback and optional settings for named operation groups.

Search records its lifecycle separately from execution and qualification.
Useful outcomes include `qualified`, `failed_validation`,
`inconclusive_validation`, `no_feasible_policy`, and `budget_exhausted`.
