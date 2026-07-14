# 2026-07-14 - Roadmap Authority And Status Reconciliation

## Paper Hook

This entry feeds the system-boundary and reproducibility-methods sections. It records how the
project separates stable technical contracts, dated evidence, live work ordering, and
agent-execution state after the ThermoMap analysis tranche.

## Context

Commit `c62169e` contains the verified ThermoMap analysis foundation. Several root guidance
files still described the 2026-07-11 pre-verification state: they left parallel-tempering and
diagnostic corrections open, reported a historical test count, classified the exact benchmark
and hardware-analysis subsets as absent, and directed agents back to Stage 2. The same files
mixed the Gibbsiq product name with the proposed ThermoMap capability name and referred to a
public `THRMLProgramBundle` class that the package does not export.

## Hard-Parts Analysis

### H1. Status prose and technical contracts have different lifetimes

The energy convention, result schema, and evidence rules are stable contracts. Test counts,
current tasks, and stage status change after every integration. We assign those facts to
different files so an autonomous agent reads one live task queue and treats dated audits as
evidence snapshots.

### H2. Correctness closure preserves explicit performance gaps

The 2026-07-14 runtime record verifies the replica-exchange sign, local transitions,
two-replica pairing, cold-slot behavior, and sweep accounting. This closes the Stage 2
correctness criterion. Device-side replica exchange, adaptive ladders, and matched-budget
performance remain separate extensions. The diagnostic correction is also verified, while
bulk/tail ESS, general constraint feasibility, and complete joint-mode coverage remain open.

### H3. Partial compiler evidence requires narrow names

The public analysis surface contains provenanced target facts, exact-law and quantization
analysis, logical admissibility, pairwise categorical/domain-wall lowering, supplied-partition
communication proxies, and an optimization-only ICM primitive. These modules do not perform
automatic partitioning, physical placement, routing, calibrated costing, or physical TSU
execution. The documentation now states each implemented subset and its missing boundary.

### H4. Package identity and capability identity serve different readers

Gibbsiq remains the product and Python package. ThermoMap names the compiler, mapping,
verification, and thermodynamic-roofline capability track inside it. Existing and future
production APIs therefore remain under `gibbsiq` unless a later recorded decision deliberately
changes the package boundary.

## Decisions

1. `reference/00-roadmap/README.md` owns the live stage summary.
2. `reference/00-roadmap/autonomous-implementation-roadmap.md` owns dependency order and work
   packages.
3. `reference/00-roadmap/autonomous-agent-runbook.md` owns execution and handoff rules.
4. `reference/00-roadmap/NEXT_TASK.md` owns live task state and claims. It may authorize
   multiple dependency-ready lanes with disjoint ownership; each worker claims exactly one
   bounded task.
5. `reference/00-roadmap/thermomap-plan-status-2026-07-14.md` is a frozen assessment for commit
   `c62169e`. Its 30% baseline and 40% post-tranche score remain unchanged.
6. `spec.md` owns stable contracts and current public data boundaries. Its current data path
   names an audited private THRML lowering instead of a nonexistent public bundle type.
7. `AGENTS.md` and `CLAUDE.md` link to the live control files and carry no volatile test count.
8. Stage 2 records correctness closure. Stage 3 records core closure and its statistical and
   constraint extensions. Stage 4 remains absent. Stage 5 is partial because the exact corpus
   and witness oracle exist. Stage 6 is a partial analysis foundation with adaptive execution
   absent.
9. Pairwise categorical/domain-wall lowering is recorded separately from general constraint
   encoding.
10. Physical prose distinguishes proposed architecture behavior, implementation-specific
    operating temperature, modeled system values, and device measurements.
11. `.gitignore` excludes `tmp/` as local PDF extraction and render scratch space. Existing
    scratch contents remain untouched.

## Rejected Alternatives

- We rejected copying the full live stage table into every root guidance file. Duplicated
  status had already diverged between the 2026-07-11 and 2026-07-14 records.
- We rejected using the dated 40% audit as a mutable task queue. Updating that file on every
  task would destroy the frozen baseline comparison.
- We rejected creating a separate `thermomap` package in documentation. The current public API
  and project metadata define `gibbsiq` as the package boundary.
- We rejected treating domain-wall lowering as higher-order quadratization or constraint
  feasibility. The implemented model accepts complete pairwise categorical tables, while
  general higher-order factors and knapsack/TSP bridge encodings remain absent.
- We rejected treating paper communication proxies or `TSUSpec` cell fields as measured
  Extropic hardware results. Provenance and measurement boundaries remain explicit.
- We rejected retaining a historical suite count in agent guidance. Counts belong in the
  dated command record that produced them.
- We rejected deleting the `tmp/` directory. Ignoring local scratch state removes repository
  noise while preserving concurrent research artifacts.

## Sources Read And Evidence Used

- Commit `c62169e`, including `src/gibbsiq/__init__.py`, `thrml_runtime.py`,
  `diagnostics.py`, `hardware.py`, `hardware_assessment.py`, `quantization.py`,
  `exact_distribution.py`, `categorical.py`, `domain_wall.py`,
  `communication_profile.py`, and `cluster_moves.py`.
- `reference/research-journal/2026-07-14-runtime-sampling-and-frozen-mode-correctness.md`.
- `reference/research-journal/2026-07-14-thermomap-final-integration-verification.md`.
- `reference/00-roadmap/thermomap-plan-status-2026-07-14.md`.
- `.github/workflows/ci.yml` and `pyproject.toml` for the verified Python-version and packaging
  boundary.

## Follow-Up

- The live roadmap, runbook, and next-task files must exist at the exact linked paths before
  this documentation set closes.
- CI currently exercises Python 3.13. The package classifiers list Python 3.10 through 3.13;
  a matrix and package-build check must precede a cross-version verification claim.
- `PROJECT_BRIEF.md` is locally excluded by `.git/info/exclude`. The integration owner must use
  `git add -f PROJECT_BRIEF.md` or revise the local exclude before committing that updated
  brief.
- `reference/research-journal/gotchas-and-todo.md` retains the old Stage 2 and Stage 3 open
  items. A later append-only cleanup should remove those closed TODOs after the live roadmap
  absorbs them.

## Verification

The documentation pass ran:

```powershell
python tools/check_markdown_math.py
$env:PYTHONPATH = "src"
python -m unittest test_suite.tests.test_public_api_thermomap test_suite.tests.test_runtime_correctness_contracts
git diff --check
```

The Markdown-math checker passed. The two focused modules ran 20 tests in 56.022 seconds and
returned `OK`. `git diff --check` returned no whitespace error; Git emitted only the existing
LF-to-CRLF working-copy warnings.

The first canonical-link check ran while the roadmap and runbook agents were still writing
their files and reported the missing runbook path. This negative result is retained here. The
closing check found all three exact paths, confirmed that the root guidance routes to them,
and repeated the owned-file stale-status scan. The link, routing, and stale-status checks
returned `PASS`. A final Markdown-math and `git diff --check` invocation also returned `PASS`;
Git emitted only the existing LF-to-CRLF working-copy warnings.

## Mandatory Gotchas Reconciliation Addendum

### Paper Hook

This addendum feeds the reproducibility-methods account of autonomous handoff. Every agent is
required to read `gotchas-and-todo.md`, so its state must agree with the live task ledger before
the control plane can close.

### Context And Hard Part

The first consistency pass identified stale Stage 2 and Stage 3 TODO entries. The mandatory
gotchas file still instructed a future agent to wait for parallel tempering and to close
corrective audits that the 2026-07-14 evidence already closes. The same text proposed
segmenting diagnostics after PT without reflecting the implemented cold-slot return contract.

The runtime evolves every configured beta replica and records per-beta energy and swap
telemetry. It returns only the cold slot at `config.beta` as `SampleResult.samples`, and
`compute_diagnostics` consumes the cold-slot interaction-energy and magnetization chains.
This makes the retained diagnostic input a target-beta sequence. Per-beta telemetry has
different semantics and cannot be relabeled as independent retained chains.

### Decisions

1. The PT failure mechanism remains an engineering gotcha with a closed date and a pointer to
   its invariant tests.
2. The Stage 3 flag-taxonomy correction remains closed historical evidence. Bulk/tail ESS and
   joint-mode coverage remain explicitly open.
3. General constraints route to `TM-LWR-001`; observable-specific statistical efficiency routes
   to `TM-PROF-001`; joint-mode evidence routes to the domain benchmark tasks; Inspector,
   baselines, mapping, non-idealities, and costing route to their stable task IDs.
4. Nested R-hat, R\*, and device-side PT optimization have no standalone stable task ID. An
   agent cannot self-select them. The coordinator must add a bounded task, or place an upstream
   interface artifact under `TM-RFC-001` after its dependencies close.

### Rejected Alternatives

- We rejected deleting the PT and diagnostic failures from the gotchas file. Their mechanisms
  remain regression risks even though their corrective gates are closed.
- We rejected applying current chain diagnostics directly to per-beta PT telemetry. Replica
  slots exchange configurations, and the existing diagnostics contract consumes cold-slot
  retained sequences.
- We rejected leaving optional diagnostics as free-floating TODOs. Autonomous selection
  requires a stable task ID, dependencies, owned files, and an independent oracle.

### Verification

The addendum is verified with the repository Markdown-math checker, `git diff --check`, a scan
for the stale PT phrases, and direct comparison with `thrml_runtime.py:1135-1226`. The command
completed with no Markdown-math or whitespace error. Git emitted only the existing LF-to-CRLF
working-copy warnings. The stale Stage 2/Stage 3 phrase scan returned `PASS`, and every routed
task ID was found in `autonomous-implementation-roadmap.md`.

## Parallel-Lane Ledger Clarification

### Paper Hook

This clarification feeds the autonomous-evaluation methods section by separating global
scheduling from worker ownership.

### Decision

`NEXT_TASK.md` is the live task-state and claim ledger. It may authorize several
dependency-ready tasks concurrently when the runbook proves their file ownership is disjoint.
Each worker claims and executes exactly one bounded task. At the governance checkpoint,
`TM-GOV-001` remains the only active claim and coding lanes remain dependency-blocked until
the coordinator closes that gate.

### Rejected Alternative

We rejected describing the ledger as a single-task queue. That wording prevents the three
parallel-safe lanes recorded in the control plane from becoming ready together after
governance closure and conflates coordinator scheduling with worker scope.

### Verification

The root-guidance scan found no remaining single-task wording and confirmed that every owned
guidance file routes through `NEXT_TASK.md`. The Markdown-math checker and `git diff --check`
returned `PASS`; Git emitted only the existing LF-to-CRLF working-copy warnings.

## Integration Clarification — 2026-07-14

### Paper Hook

This clarification feeds the reproducibility-methods account of how the public autonomous
control plane is separated from intentionally local project context.

### Resolution

The earlier Follow-Up is resolved. The three control files now exist at their exact published
paths: `reference/00-roadmap/autonomous-implementation-roadmap.md`,
`reference/00-roadmap/autonomous-agent-runbook.md`, and
`reference/00-roadmap/NEXT_TASK.md`. The stale gotchas were reconciled in the later Mandatory
Gotchas Reconciliation Addendum above.

`PROJECT_BRIEF.md` is intentionally local-only. `.git/info/exclude` explicitly says to keep
the internal project brief out of the published repository, so this documentation commit will
not publish it. The tracked public roadmap, `spec.md`, and agent guidance contain the
autonomous contracts required by a fresh agent.

### Rejected Alternative

We reject force-adding `PROJECT_BRIEF.md`. Overriding the explicit local exclusion with
`git add -f` would publish an internal document contrary to the recorded repository boundary;
the correct resolution is to keep it local and make the public contracts self-sufficient.

### Read-Only Verification

`git check-ignore -v PROJECT_BRIEF.md` reported
`.git/info/exclude:10:PROJECT_BRIEF.md` (with `PROJECT_BRIEF.md` as the matched path). A
separate `git ls-files -- PROJECT_BRIEF.md` check returned no path, confirming that the file
is not tracked.
