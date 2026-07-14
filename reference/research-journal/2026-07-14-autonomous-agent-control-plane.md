# 2026-07-14 - Autonomous Agent Control Plane

## Paper Hook

This entry feeds the reproducibility and agentic-evaluation methods sections. It records the
control plane that converts the ThermoMap roadmap into dependency-gated tasks with independent
oracles, exclusive file ownership, and command-specific completion evidence.

## Context

Commit `c62169e` contains the audited ThermoMap analysis foundation. The dated status audit
scores that tree at 8 of 20 equal-weight ThermoMap capability rows. The repository previously
distributed current-state guidance across root files, stage notes, journals, tests, and the
status audit. A fresh agent could identify missing capabilities, while task ownership,
dependency-ready selection, and the physical-hardware stop condition required reconstruction
from several documents.

We add two control files:

- `reference/00-roadmap/autonomous-agent-runbook.md` defines the operating loop;
- `reference/00-roadmap/NEXT_TASK.md` records active claims, ownership, and dependency state.

The implementation roadmap is produced in the same coordinated documentation pass. The live
ledger keeps `TM-GOV-001` in `review` until a coordinator verifies the combined diff.

## Hard-Parts Analysis

### H1. Authority Depends On Claim Type

Equations, implementation state, dependency order, and active ownership have different
authoritative sources. A single linear document-precedence list would allow stale prose to
override executable evidence or allow a current test result to redefine a mathematical
convention. The runbook assigns conventions to the equation audit, factual status to current
source/tests plus dated verification, dependencies to the implementation roadmap, and active
ownership to the live ledger. Conflicts create a reconciliation task before feature work.

### H2. Shared-Tree Parallelism Requires Integration Ownership

Three next lanes can run concurrently after governance closes:
`TM-VERIFY-01`, `TM-TARGET-01`, and `GQ-INSPECT-01`. Each lane receives disjoint production and
test files. The coordinator retains `src/gibbsiq/__init__.py`, roadmap files, root guidance,
and the ledger. This split prevents nominally independent workers from colliding in exports or
changing their own completion state. Worker capacity claims a fixed prefix in that order, so
one slot always starts verification before target specification or Inspector work.

### H3. Verification Requires An Independent Reward Path

The runbook requires each task to name its oracle before implementation. Conversion tasks use
exhaustive energy tables, transition kernels use independent row/stationarity equations,
constraint gadgets use native-objective witnesses, placement uses small independent
enumeration, and benchmark claims use witness recomputation. Public tests teach these
contracts. Private seeds, generated instances, and metamorphic mutations remain outside the
agent-visible repository and package import path.

### H4. Public Software And Physical Calibration Have Different Terminal Conditions

M2 closure records `software_mvp_complete`. Closure of every autonomous public and simulator
task through M3 records `simulator_research_release_complete`. Physical TSU calibration
requires an authorized backend, identified device and software versions, calibration
artifacts, a documented timing and energy boundary, and publication permission. The ledger
retains `TM-HW-001` as `blocked_external` until those inputs exist. Modeled or assumed
parameters cannot transition it to complete.

### H5. Test Counts Are Command-Scoped Measurements

The 457-test result belongs to the final integration command recorded for `c62169e`. Optional
dependencies and later changes alter counts and skips. The runbook requires every handoff to
record the command, environment, actual count, skip count, and duration from the new run. It
prohibits copying a historical count as current evidence.

### H6. Context-Free Reader Findings Expose Operational Ambiguity

The independent fresh-reader audit surfaced eight underspecified controls:

1. Worker capacity had no deterministic one-slot choice.
2. The governance path check could be read as requiring planned worker outputs before their
   tasks began.
3. The Inspector core lacked one exact optional-model API.
4. Supplied-model verification lacked every-row recomputation, an explicit artifact-only
   boundary, and a stable association fingerprint.
5. The bounded Inspector core was not separated sharply enough from deferred CLI, HTML,
   comparison, and compiled-manifest reporting.
6. Source-of-truth precedence required one aligned ordering across the control documents.
7. The active governance owner was implicit.
8. The public terminal-state text used one marker for both M2 and M3.

The corrected control plane orders the first-lane capacity prefix, excludes planned outputs
from the governance existence gate, freezes the Inspector core API to an optional
`IsingModel`, verifies every stored row when that model is supplied, records a stable
caller-supplied association fingerprint, defers broader reporting to `TM-REP-001`, aligns
precedence, assigns `/root` as the active governance owner, and distinguishes the M2 and M3
completion labels.

## Decisions

1. We use a stable task schema with dependencies, exact ownership, sources, public and blind
   tests, an independent oracle, artifacts, acceptance criteria, and last-verified evidence.
2. Only the coordinator updates the ledger and marks a worker task verified or complete.
   Coordinator `/root` owns the active `TM-GOV-001` review for this pass.
3. Workers implement disjoint modules and tests with `apply_patch`; the coordinator reads the
   actual diff, reruns checks, integrates shared exports, and commits.
4. The first frontier uses the fixed order `TM-VERIFY-01`, `TM-TARGET-01`,
   `GQ-INSPECT-01`. Available worker capacity claims that prefix: one, two, or all three tasks.
   Each worker executes one bounded task, and every lane remains serial.
5. The live ledger marks all three coding lanes `dependency_blocked` while `TM-GOV-001`
   remains in review. The coordinator changes all four states in one verified integration
   patch.
6. A missing independent oracle, conflicting equation, active file owner, or unavailable
   required artifact stops the task. Unexpected local edits trigger reread and retry.
7. Physical TSU measurements remain externally gated. Unknown target facts remain explicit
   unknowns with provenance requirements.
8. Governance path existence covers current control links, commands, and pre-existing required
   inputs/sources. Future worker modules, tests, artifacts, and journal targets are expected to
   be absent before their tasks begin.
9. The artifact-only API is
   `Inspector.from_result(result, *, model: IsingModel | None = None)`. With no model it reports
   objective verification as `not_available`. With a model it validates vartype and exact
   variable order, recomputes every sampled total and interaction energy at absolute tolerance
   `1e-9`, fails any mismatch, and reports a deterministic fingerprint of the caller-supplied
   association. Compiled-manifest binding belongs to later API/report integration.
10. M2 and M3 use distinct terminal markers. The final autonomous state without device access
    is M3 complete with `TM-HW-001` retained as `blocked_external`.

## Rejected Alternatives

### One Narrative Roadmap As The Complete Control Plane

A narrative roadmap describes scope well and performs poorly as a mutable claim ledger.
Separating stable dependencies from live ownership keeps historical plan prose intact while
making task transitions auditable.

### Letting Workers Edit Shared Exports And Mark Their Own Tasks Complete

This path creates merge collisions and turns self-reported success into project status. The
coordinator owns shared integration files and independently verifies worker claims.

### Marking Governance Complete When The Two Files First Exist

File existence does not establish internal consistency. `TM-GOV-001` stays in review until
current control links, required input/source paths, IDs, commands, root guidance, and the
complete diff pass coordinator review. Future worker outputs are excluded from this gate.

### Accepting A Compiled Manifest In The Inspector Core

No public compiled-manifest contract exists at `c62169e`. Adding an unspecified manifest
argument would create a second association path without a stable schema. The Inspector core
accepts only the explicit optional `IsingModel`; `TM-API-001` and `TM-REP-001` own later
compiled-artifact binding.

### Treating Physical Calibration As An Ordinary Pending Software Task

An autonomous software agent cannot manufacture device identity, measurement access, or
publication authority. The external gate preserves forward progress on the public software
MVP while preventing simulator evidence from being relabeled as silicon evidence.

## Sources Read And Examples Used

- `AGENTS.md`, `PROJECT_BRIEF.md`, `spec.md`, and `CLAUDE.md`.
- `reference/README.md`, `reference/glossary.md`, and
  `reference/claims-evidence-map.md`.
- `reference/00-roadmap/README.md` and
  `reference/00-roadmap/thermomap-plan-status-2026-07-14.md`.
- `reference/08-evaluation/equation-audit.md`, `evaluation-framework.md`, and
  `agentic-evaluation-research.md`.
- `reference/06-benchmarks/ground-truth-datasets.md`.
- `reference/research-journal/gotchas-and-todo.md` and `style.md`.
- `.github/workflows/ci.yml` and `pyproject.toml` for executable repository gates.
- Current production contracts in `hardware.py`, `exact_distribution.py`, `model.py`,
  `result.py`, and `__init__.py`.

## Artifacts

The following checksums describe the files before coordinator integration review:

| File | Lines | SHA-256 |
| --- | ---: | --- |
| `reference/00-roadmap/autonomous-agent-runbook.md` | 383 | `b6693d375e9e39456ef47330f21c3745dd0c439491aeebb793ba9edfda0ad61e` |
| `reference/00-roadmap/NEXT_TASK.md` | 267 | `371dcdfab41ca2b9e9c20023bdac2bffe13c2564369317e9c727d678edb0edaa` |

Coordinator edits produce new checksums and must record them in the integration evidence.

## Verification

Commands run from `E:\projects\Gibbsiq`:

```powershell
python tools/check_markdown_math.py
git diff --check -- reference/00-roadmap/autonomous-agent-runbook.md reference/00-roadmap/NEXT_TASK.md
```

Both commands returned exit code 0. A PowerShell local-link scan resolved every relative
Markdown link in the two control files. The scan ignored HTTP and mail links and returned
`Local Markdown links: OK`. A PowerShell task-schema scan found every required field in each
first-lane card. A separate assertion scan confirmed the capacity prefix, scoped path gate,
active owner, exact Inspector signature and validation behavior, and distinct M2/M3 terminal
markers.

The context-free reader audit completed with the eight findings recorded in H6. The
post-correction verification below closes the reader-review evidence. Governance remains in
`review` until the documentation commit and ledger transition complete.

### Post-Correction Verification

| Check | Recorded result |
| --- | --- |
| Initial independent-reader full discovery | 457 tests, 0 reported skips, `OK`, 135.015 seconds. |
| Post-correction reader contract | All eight findings pass; 36 task IDs each have exactly one definition; no ID is undefined; all 36 tasks are topologically visited with no cycle; links, Markdown math, and diff checks pass. |
| Independent fingerprint implementations | Python and PowerShell encoders both produce `e851227af4a2b8a319cd7b726d929fc49fd19375973d622efe481f00ec7acd37`. |
| Coordinator focused unit modules | 20 tests in 54.527 seconds, `OK`. |
| Coordinator Markdown math | Passed. |
| Coordinator Ruff check | Passed. |
| Coordinator Ruff format | 60 files already formatted. |
| Coordinator mypy | 19 source files with no issues; mypy also emitted the recorded unused `dimod` configuration note. |
| Coordinator diff check | Passed with only LF/CRLF warnings. |
| Coordinator corrected link scan | Checked 20 changed Markdown entries; every relative link resolves. |
| Coordinator task audit | 36 definitions, 36 unique mentions, 0 unknown dependencies, and 0 cycles. |

The coordinator's first PowerShell link-scan scout failed because root-level Markdown files
produce an empty `Split-Path -Parent`. The corrected scan normalizes an empty parent to `.` and
then passes. This negative check remains recorded because it distinguishes a scanner defect
from a repository link failure.

## Follow-Up

The coordinator reads the combined roadmap and guidance diff, runs the governance closure
checklist, commits the control plane, and records the new SHA. Closing `TM-GOV-001` makes
`TM-VERIFY-01`, `TM-TARGET-01`, and `GQ-INSPECT-01` ready as disjoint parallel lanes. Available
worker slots claim that ordered prefix. M2 and M3 closure record their distinct simulator-backed
terminal markers while `TM-HW-001` remains externally gated.
