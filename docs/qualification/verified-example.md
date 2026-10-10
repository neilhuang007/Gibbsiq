# Offline example

The bundled spin workload demonstrates qualification, inspection, and regression
comparison with the standard library.

```console
gibbsiq qualify --example spin-conditional --output runs/baseline --json
gibbsiq inspect runs/baseline --verify --json
gibbsiq qualify --example spin-conditional --candidate sign-reversed --runs 256 --output runs/defect --json
gibbsiq compare runs/baseline runs/defect --candidate-change spin-conditional-sign-reversed-v1 --json
```

The baseline estimates the analytic spin mean 0.5. The candidate reverses the
sign, producing a quality failure and a reported regression. Each command
retains the observations behind its result.

The [quickstart](../../src/gibbsiq/data/qualification/QUICKSTART.md) explains the
report fields, exit codes, shorter experiments, and policy-search example.
