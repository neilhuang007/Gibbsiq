# Model evaluation

Gibbsiq evaluates complete model outputs against a numerical reference.
The model workload records architecture, initialization or checkpoint identity,
input splits, preprocessing, metrics, and selected operations.

## Token losses

Teacher-forced evaluation predicts each target token from its preceding input.
Document boundaries, sequence windows, masks, and target counts are explicit.
Aggregation uses the recorded target-token counts.

Reports include raw descriptive loss and the declared capped loss used by the
bounded statistical procedure. The cap is part of the frozen contract.
Independent runs produce the units used by its confidence interval.

## Input splits and attribution

Calibration, development, and evaluation inputs have separate identities.
A frozen policy carries the identity of the inputs used for its final
evaluation.

Projection observations help locate output differences. The report associates
summaries with named operations, sample settings, model outputs, and token-loss
changes. Reference and candidate executions share the declared workload.

## Run the example

```console
python examples/qualification/qualify_tiny_z1t.py --count 32 --output-root runs/model
```

The script writes an immutable qualification bundle and a model summary.
`summarize_model_bundle` reconstructs that summary from saved observations;
`render_model_summary` produces Markdown. See
[installation](../installation.md) for the numerical environment.
