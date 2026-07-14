# 2026-07-11 - Project Status and Novelty Audit

## Paper Hook

This entry feeds the introduction, contribution statement, related work, and limitations. It
narrows the paper claim to the evidence that the repository can independently verify.

## Context

Top-level documents disagreed about the implementation boundary. Some described Stage 2 as a
future target, while others described Stages 0-3 as complete. The same documents positioned
THRML as though public execution implied a hardware path and repeated a 2026-07-01 claim that
no QUBO/Ising tool exposed sampler-health diagnostics.

## Hard-Parts Analysis

### H1. Software execution and hardware evidence are separate claims

THRML's official getting-started guide calls the current library a GPU simulator of sampling
programs intended for future Extropic hardware. Its architecture guide states that the
relative performance of Gibbs sampling depends on the problem. Extropic's hardware page
labels Z1 as early access 2026. These sources establish a simulator and a stated hardware
roadmap. They do not establish general availability, a Gibbsiq hardware run, or a QUBO
speedup.

### H2. Broad diagnostics novelty is no longer defensible

Current dimod documentation exposes `compute_ess` and `compute_ess_sampleset`, including
energy and magnetization as example test functions. The local environment contains dimod
0.12.21, where neither function is exported, which demonstrates why a claim tied to one local
version becomes stale. Gibbsiq's defensible scope is the combined optimization audit contract:
offset-preserving conversion, explicit degenerate diagnostic states, raw traces, public/blind
anti-echo evaluation, and witness-recomputed objectives.

### H3. Stage labels must expose open exit criteria

The model, fixed-beta runtime, diagnostics, evaluator, and strict benchmark oracle are present.
Parallel-tempering code is also present, but the 2026-07-11 audit found exchange and transition
defects that require correction and full re-verification. The diagnostics formulas retain
their recorded external cross-checks, while the semantic audit found that raw-energy ESS lacks
rank-normalized bulk/tail ESS and cannot inherit its threshold. It also found that observable
or progress statuses can be mislabeled as sampler failures. Inspector, constraint encoding,
and classical-baseline adapters remain absent. Calling Stages 2 or 3 absent discards real work;
calling either corrective criterion closed overstates current evidence.

## Decisions

- Status documents now describe Stages 0-3 as having implemented core deliverables while
  keeping the parallel-tempering and diagnostic-semantic criteria open under corrective audit.
- Every hardware-performance statement distinguishes JAX/GPU simulation, projected future
  hardware, and measured production hardware.
- The contribution claim centers the integrated evidence and evaluation contract rather than
  ESS, R-hat, or sampler-health telemetry in isolation.
- Historical exact test counts were removed from current-status prose. Verification records
  carry the count produced by the command actually run.

## Rejected Alternatives

- "No existing QUBO/Ising tool has sampler-health diagnostics" was rejected because current
  official dimod documentation directly contradicts it.
- "THRML-backed" as shorthand for TSU hardware execution was rejected because the current
  public runtime is documented as a JAX/GPU simulator.
- Declaring Stage 2 complete was rejected until corrected PT invariants and the full optional
  THRML suite pass.
- Declaring Stage 3 SOTA-aligned or fully closed was rejected because rank-normalized
  bulk/tail ESS is absent and the flag taxonomy is under correction.
- Reverting the project to a generic diagnostics package was rejected because the implemented
  lowering and oracle contracts remain THRML-first.

## Sources Read

- THRML getting started:
  https://docs.thrml.ai/en/latest/examples/00_probabilistic_computing/
- THRML architecture: https://docs.thrml.ai/en/latest/architecture/
- Extropic hardware roadmap: https://extropic.ai/hardware
- dimod ESS API: https://docs.dwavequantum.com/en/latest/ocean/api_ref_dimod/ess.html
- Jelinčič et al., arXiv:2510.23972v2.

## Verification

The local-version boundary was checked with:

```powershell
.\.venv\Scripts\python.exe -c "import dimod; print(dimod.__version__); print(hasattr(dimod, 'compute_ess')); print(hasattr(dimod, 'compute_ess_sampleset'))"
```

The output was `0.12.21`, `False`, `False`. The official latest documentation listed both
helpers on 2026-07-11. This entry makes no release-version claim beyond those two observed
surfaces.

The updated README warmup example was constructed with:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -c "from gibbsiq import SamplerConfig; print(SamplerConfig(beta=2.0, n_warmup=50, warmup_beta_ladder=(0.5, 1.0, 2.0), num_chains=2, seed=0))"
```

The command exited 0 and printed the expected configuration. `python
tools/check_markdown_math.py` exited 0. The coordinating audit owns the final unit-suite,
lint, type, and package verification because Python sources were changing concurrently.

The first local-link check failed because `Split-Path -Parent` returns an empty string for
top-level files. The corrected PowerShell check substitutes `.` for that case and reported
`All checked local Markdown link targets exist.` across the edited status, source, roadmap,
diagnostics, and journal files.
