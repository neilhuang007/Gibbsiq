# Gibbsiq: offline qualification walkthrough

Gibbsiq validates stochastic workloads against declared quality contracts and
exports frozen policies only when their final evaluation passes. The experimental
package also preserves its QUBO/Ising tools and integer `SampleResult` API.

Install the supplied wheel in a fresh Python 3.10+ environment, then run these
commands from an empty directory outside the source checkout. The core requires
no third-party packages, network, model download or GPU.

```console
gibbsiq --version
gibbsiq doctor --json
gibbsiq qualify --example spin-conditional --output pass --json
gibbsiq inspect pass --verify --json
gibbsiq qualify --example spin-conditional --candidate sign-reversed --runs 256 --output fail --json
gibbsiq compare pass fail --candidate-change spin-conditional-sign-reversed-v1 --json
gibbsiq qualify --example spin-conditional --runs 16 --output uncertain --json
gibbsiq tune --example no-feasible-policy --output search --json
```

The default 1024-run example should pass (exit 0). The sign error should fail
(exit 1), and comparison should report a declared regression (exit 1). The short
run should be inconclusive (exit 3). Search should retain three failed calibration
candidates and report `no_feasible_policy` (exit 3), with no exported policy.
Inspecting any valid bundle succeeds even when its scientific result failed.
Use a fresh output directory for each independent experiment.

Ordinary qualification JSON contains `report`, including metric estimates,
intervals, independent observation counts, execution and qualification states.
Comparison and search JSON contain their respective summary schemas directly.
All examples retain their completed unfavorable observations. No metric test is
passed merely because a file was produced. Budgets are at most 120 seconds and
16 MiB per spin qualification; the negative search allows 30 seconds and 8 MiB.

Exit codes: 0 success, 1 failure/regression, 2 invalid or incompatible, 3
inconclusive/no feasible policy, 4 unsupported, 5 execution error, 130 cancelled.
Bounded fixed-sample intervals are conditional on the declared fixed inputs;
they cannot be used as an adaptive stopping rule or a claim about all inputs.

## Recovery

If qualification is interrupted, inspect its partial evidence. Resume the same
frozen recipe with `gibbsiq qualify --example spin-conditional --output pass
--resume --json`. Preserve the original arguments: changed inputs, seeds or
settings are a new experiment. A completed bundle is immutable. Corrupt evidence
must be retained for diagnosis and a new output directory used; resume does not
silently discard corruption or replace a completed unfavorable result.

## Optional tiny complete model

The tested optional stack is Python 3.13.5 CPU, JAX/JAXLIB 0.10.2, Equinox 0.13.8,
NumPy 2.4.6 and the `research/z1t` package at sparse-transformers commit
`13051e90df9669be5b8f9f34fb097329fa82f674`. It must already be installed for these
commands. There is no `gibbsiq[z1t]` extra and doctor does not install anything.

```console
gibbsiq qualify --example tiny-z1t --output tiny --json
gibbsiq inspect tiny --verify --json
gibbsiq tune --example tiny-z1t --output tiny-search --json
```

The generated model and synthetic tokens need no checkpoint. Evaluation includes
the final vocabulary head. Capped loss and modeled sampling work are separate
from raw descriptive loss and measured software timing. Tiny search permits at
most 256 jobs, 600 seconds and 64 MiB; an inconclusive or negative result is valid
evidence. Only a passing frozen evaluation can export a qualified policy, and the
policy applies only to its exact workload/input identities. A modeled reduction
in spin draws is not a measured hardware speedup or energy saving.

The legacy `gibbsiq-evaluate` command remains available for discrete-model JSON
fixtures. It has its original schema; floating activation observations use the
separate qualification API.

Project-authored code is MIT licensed. Adapted Z1T expressions retain the shipped
Apache-2.0 notice; the distribution expression is `MIT AND Apache-2.0`. No model
weights or external datasets are bundled. No Extropic endorsement, physical Z1
execution, useful trained-model quality or whole-model dy4p compilation is claimed.
