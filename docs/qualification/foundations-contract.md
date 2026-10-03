# Contracts and statistics

A qualification experiment connects four values:

| Value | Purpose |
| --- | --- |
| `WorkloadSpec` | Identifies the computation, inputs, reference, and candidate |
| `AcceptanceContract` | Declares metrics, tolerances, and error allocation |
| `RunPlan` | Freezes runs, settings, seeds, and resource budgets |
| `QualificationReport` | Records estimates, intervals, and decisions |

These immutable records live in `gibbsiq.qualification.contracts`. Each validates
its inputs and supports the versioned artifact format.

## Metric decisions

A `MetricSpec` records the quantity, bounds, aggregation, tolerance, and planned
number of independent units. `MetricBinding` connects it to scalar observations
from named runs.

For sampled bounded metrics, Gibbsiq uses fixed-sample Hoeffding intervals.
A pass means the entire interval satisfies the declared acceptance region.
A failure means the interval establishes a violation. An overlapping interval
produces an inconclusive result. Exact evidence uses its declared exact procedure.

Declare the independent unit and input population before execution. Keep
calibration and final evaluation inputs separate. Family error allocation covers
the metrics evaluated together.

## Observations and identity

An `Observation` includes the operation, context, run, dtype, shape, axes, and
values. Large arrays can use an `ArrayRef`; scalar and small-array observations
use inline values.

Workload identities include sources, model configuration, preprocessing, inputs,
operations, and evaluation semantics. Canonical JSON and content digests let
comparison and recovery verify that they are using the same experiment.

Execution state and qualification outcome are separate fields. See the
[quickstart](../../src/gibbsiq/data/qualification/QUICKSTART.md) for command
outcomes and the [workflow guide](workflow-contract.md) for an example.
