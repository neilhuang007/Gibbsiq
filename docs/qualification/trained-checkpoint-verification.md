# Checkpoint verification

The checkpoint tools acquire and verify the pinned Z1T-0 weights, prepare a
bounded workload, and compare numerical and stochastic projection execution.

## Environment

Create a Python 3.13.5 CPU environment and install the checkpoint recipe:

```console
python -m pip install -r requirements/checkpoint-verification.txt
python -m pip install .
python -m pip check
```

Use `--help` to inspect acquisition and execution settings:

```console
python -m tools.qualification.acquire_z1t_checkpoint --help
python -m tools.qualification.verify_trained_checkpoint --help
```

## Workflow

1. Select the checkpoint, its source and use terms, and the local destination.
2. Run acquisition to verify the pinned file identity.
3. Configure token inputs, selected projections, sampling counts, and budgets.
4. Run verification into a fresh output directory.
5. Inspect the saved model metrics and execution records.

```console
python -m tools.qualification.acquire_z1t_checkpoint /path/to/weights
python -m tools.qualification.verify_trained_checkpoint /path/to/weights/model.eqx /path/to/run
```

The report records checkpoint and tokenizer identities, target-token counts,
reference losses, sampling variation, and measured execution timings.
Keep run outputs alongside the exact environment recipe used to produce them.
