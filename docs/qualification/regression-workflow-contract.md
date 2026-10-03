# Regression checks

Compare two completed experiments with the CLI:

```console
gibbsiq compare runs/baseline runs/candidate --json
```

For a deliberate backend or candidate revision, declare the new identity:

```console
gibbsiq compare runs/baseline runs/defect --candidate-change spin-conditional-sign-reversed-v1 --json
```

The Python entry point is `gibbsiq.qualification.compare_bundles`.

## Comparison contract

Gibbsiq verifies both bundles, then checks workload, inputs, reference, metrics,
statistical procedure, and execution settings for compatibility. A declared
candidate revision makes that revision the comparison variable.

Reports include metric changes, qualification outcomes, comparable cost changes,
and environment differences. Cost comparisons require matching units,
measurement boundaries, and provenance.

## CI use

Run qualification into a new directory, retain that directory as a CI artifact,
and compare it with the selected baseline. Exit code 1 identifies a regression;
exit code 2 identifies an incompatible comparison. Use the JSON result to
present individual metric changes.

An inspection command returning 0 means the saved bundle was successfully
inspected. Read its `qualification` field for the experiment's quality decision.
See the [quickstart](../../src/gibbsiq/data/qualification/QUICKSTART.md) for the
complete exit-code table.
