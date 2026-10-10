# Quickstart

Gibbsiq compares stochastic executions with a reference and evaluates the
difference against a quality tolerance. Each experiment saves its inputs,
settings, observations, and result in an evidence directory.

Install Gibbsiq in a Python 3.10+ environment, then run:

```console
gibbsiq --version
gibbsiq doctor
gibbsiq qualify --example spin-conditional --output runs/baseline
gibbsiq inspect runs/baseline --verify
```

The spin example averages 32 draws in each of 1,024 independent runs. It compares
the observed mean with the analytic value 0.5, using an error tolerance of 0.125.
The default example passes with exit code 0.

## Detect a regression

```console
gibbsiq qualify --example spin-conditional --candidate sign-reversed --runs 256 --output runs/defect
gibbsiq compare runs/baseline runs/defect --candidate-change spin-conditional-sign-reversed-v1
```

The candidate deliberately reverses the spin sign. Qualification and comparison
both return exit code 1. The comparison records the declared candidate change.

## Read the result

Add `--json` to any command for structured output. Qualification JSON contains
a `report` with metric estimates, intervals, observation counts, and decisions.
Inspection reads the stored experiment.

| Exit code | Meaning |
| --- | --- |
| 0 | Command succeeded |
| 1 | Quality failure or regression |
| 2 | Invalid input or incompatible comparison |
| 3 | Inconclusive result or no feasible policy |
| 4 | Required capability unavailable |
| 5 | Execution error |
| 130 | Cancelled |

Each independent experiment uses a fresh output directory. Resume an interrupted
experiment with the same arguments and `--resume`:

```console
gibbsiq qualify --example spin-conditional --output runs/baseline --resume
```

Completed experiments remain immutable, preserving the result used by a later
comparison or policy.

## Explore sample budgets

```console
gibbsiq qualify --example spin-conditional --runs 16 --output runs/short
gibbsiq tune --example no-feasible-policy --output runs/search
```

The short experiment returns an inconclusive result. The search example
evaluates three candidates and reports `no_feasible_policy`. Both return
exit code 3, demonstrating how automation can distinguish these outcomes.

## Evaluate a model

After installing the pinned numerical environment described in the repository's
installation guide:

```console
gibbsiq qualify --example tiny-z1t --output runs/tiny
gibbsiq inspect runs/tiny --verify
gibbsiq tune --example tiny-z1t --output runs/tiny-search
```

The generated model uses synthetic tokens and includes the complete vocabulary
head. Its report records token losses and modeled sampling work. Policy search
freezes selected settings before evaluating held-out inputs.
