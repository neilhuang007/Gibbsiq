# THRML and Torx adapters

Gibbsiq connects backend execution to common plans, observations, and reports.
Install the [pinned numerical environment](../installation.md) to use these
qualification adapters.

## THRML

`gibbsiq.qualification.adapters.thrml` adapts THRML sampling into qualification
observations. Its plan records the model, inverse temperature, sampling
settings, and randomization. Small-state references provide independent checks.

The top-level `THRMLSampler` remains available for discrete `SampleResult`
workflows.

## Torx

Run the bundled circuit example:

```console
gibbsiq qualify --example torx-two-gate --output runs/torx --json
gibbsiq inspect runs/torx --verify
```

`TorxCircuitBackend` supplies the plan and execution adapter. Circuit evidence
records named sites, settings, random streams, observations, and the reference
comparison.

## Shared conventions

Adapters declare their supported controls before execution. Random streams
derive from the frozen plan and run identity. Results use named operations and
axes; the qualification workflow evaluates their metrics.

Integration requirements pin both distribution versions and upstream source
revisions. `gibbsiq doctor --json` reports the local environment.
