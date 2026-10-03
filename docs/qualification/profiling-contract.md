# Cost and timing

Gibbsiq records what a cost measures, its units, and how it was obtained.
A `CostRecord` pairs a value with a `CostScope` and provenance such as
`measured` or `modeled`.

## Compare costs

`compare_costs(reference, candidate)` reports the difference and ratio when
quantity, units, scope, provenance, and method match. Availability is explicit.

`sample_work(elements, samples, scope=...)` counts modeled IID spin draws:
the sum of output elements multiplied by samples for each operation.

`critical_path_seconds(regions)` computes the longest dependency path through
named latency regions. Use disjoint component sets and explicit dependencies.

## Measure execution

`profile_execution` accepts callbacks for preparation, compilation, execution,
synchronization, and output handling. It records:

- Preparation and compilation.
- First execution.
- Warmed executions after the declared warmups.
- Output handling.

Each series includes raw durations, count, median, range, and interquartile
range. Execution timing includes synchronization. `synchronize_jax` waits for
the complete output tree.

Compare observer-off, summary, and trace modes with
`examples/qualification/profile_tiny_z1t.py`. Reports retain workload and
environment identities so timing results can be reproduced.
