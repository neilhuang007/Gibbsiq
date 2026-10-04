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

## Frozen policy comparison

The policy study is a separate, predeclared experiment on four fresh authored
texts. It samples the final attention output projection with 8 draws and the
final MLP output projection with 128 draws. Its uniform baseline uses 68 draws
at both projections. The projections have equal output width, so both policies
have the same modeled spin work for a given input length.

```console
python -m tools.qualification.verify_trained_checkpoint \
  /path/to/weights/model.eqx /path/to/new-policy-run --policy-study
```

The study uses 32 independent whole-corpus replicates. Each replicate contains
one result from each policy, with independently derived policy and document
random streams. Execution order alternates by replicate. The three mandatory
fixed-input checks use capped loss at 16 nats/token and split total alpha 0.05
equally: each policy may degrade no more than 0.5 nats/token from the numerical
reference, and the heterogeneous policy may degrade no more than 0.25
nats/token from the uniform baseline. The report also retains uncapped loss,
cap hits, full-head timings, observer overhead, peak RSS, and the much larger
run counts needed for narrow distribution-free intervals.
Observer overhead comes from five rotated warmed wrapper/observed pairs; the
direct model timing is reported separately. Stochastic records separate
forward-plus-host-transfer time from forward-plus-transfer-plus-loss time.

This is bounded CPU software evidence. The modeled work objective does not
measure energy, temperature, physical-device latency, or an unpublished
compiler. An inconclusive interval is an inconclusive result even when the
point estimate looks favorable.

The [4 October trained-checkpoint result](checkpoint-policy-result-2026-10-04.md)
records the completed comparison, its inconclusive verdicts, measured costs,
exact source revision, and reproduction recipe.
