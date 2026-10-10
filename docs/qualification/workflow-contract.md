# Qualification from Python

Build a frozen plan, supply its backend, and choose a new output directory:

```python
from gibbsiq.qualification import inspect_bundle, qualify
from gibbsiq.qualification.adapters.spin import SpinConditionalBackend
from gibbsiq.qualification.examples import spin_conditional_plan


def main():
    plan = spin_conditional_plan(runs=1024, samples=32, seed=7)
    report = qualify(
        plan,
        backends={plan.workload.candidate.identity: SpinConditionalBackend()},
        destination="runs/python-example",
    )
    print(report.qualification)
    saved = inspect_bundle("runs/python-example", verify=True)
    print(saved.qualification)


if __name__ == "__main__":
    main()
```

Save this example as a script. The main guard supports the worker process used
to enforce execution deadlines.

## Execution and evidence

`qualify` validates the plan, prepares the backend, executes planned runs,
evaluates metrics, and finalizes the evidence bundle. Its `resume` argument
continues an interrupted matching plan; `cancel` accepts a parent-side callback.

The bundle contains the workload and plan, environment, attempt journal,
metrics, costs, Markdown report, and final manifest. The manifest records file
sizes and digests. `inspect_bundle` checks identities and recomputes metric
decisions from retained observations.

Use a fresh destination for changed inputs, settings, or independent experiments.
Completed bundles are immutable. Recovery preserves previous attempts and
reuses completed runs from the same plan.

## Custom backends

Pass a trusted Python adapter through the `backends` mapping. It provides:

- `capabilities()`: backend identity, supported controls, and observation names.
- `prepare(workload)`: initialize the workload once.
- `execute(run, randomization)`: return observations and cost records.

The engine owns worker lifetime, deadlines, cancellation, and evidence writes.
The statistics layer owns qualification decisions. See
[backend integrations](interoperability-contract.md) for concrete adapters.
