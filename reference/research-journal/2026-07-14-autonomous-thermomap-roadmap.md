# 2026-07-14 - Autonomous ThermoMap Implementation Roadmap

## Paper Hook

This entry feeds the systems-methods, implementation-status, reproducibility, and limitations
sections. It records how the 40% verified ThermoMap capability snapshot becomes an executable
dependency graph whose rewards come from independent tests and artifacts.

## Context

Commit `c62169e` contains the audited ThermoMap analysis foundation. The dated status audit
scores that tree at 8/20 = 40% for the full proposal and 8.5/10 = 85% for the narrower
optimizer/audit foundation. The existing stage index still described the 2026-07-11
parallel-tempering and diagnostic corrections as open. The 2026-07-14 implementation and final
integration evidence close those correctness corrections while leaving device-side PT
performance, bulk/tail ESS, feasibility, Inspector, baselines, mapping, calibrated costs, and
physical TSU execution open.

The roadmap required two simultaneous properties. It had to preserve the original Gibbsiq
stage history, and it had to let the coordinator expose disjoint parallel lanes from which a
context-free worker selects one bounded task with explicit dependencies, file ownership,
public tests, blind tests, an independent oracle, and a binary exit gate.

## Hard-Parts Analysis

### H1 — Status Authority Must Survive Stale Progress Prose

The repository contains production behavior that postdates several stage documents. A fresh
reader found that the first draft did not match the runbook's ownership order. We corrected it
to: `AGENTS.md` and higher-level workflow instructions; the equation audit for mathematics;
executable source, tests actually run at current `HEAD`, and the latest verification/status
record for implementation status; the autonomous roadmap for dependencies and exit gates;
`NEXT_TASK.md` for active claims, ownership, and the dependency-ready frontier constrained by
that roadmap; then other scope and historical prose. This preserves history without allowing a
stale test count, task state, or proposed class to override its owning source.

### H2 — Stable Tasks Require Acyclic Milestones

The supplied 12-week schedule groups deliverables by time, while autonomous execution requires
logical prerequisites. We replaced week labels with stable task IDs and an explicit DAG. The
first parallel-safe lanes are `TM-VERIFY-01`, `TM-TARGET-01`, and `GQ-INSPECT-01` after
`TM-GOV-001` closes. Partition, placement, routing, and compiled-artifact work remain sequential
because each pass freezes the schema consumed by the next.

The original parallel statement was under-specified when the coordinator has fewer than three
worker slots. The corrected rule selects the deterministic prefix of that same order: one slot
gets `TM-VERIFY-01`; two slots get `TM-VERIFY-01` and `TM-TARGET-01`; three slots expose all
three. An earlier lane may be skipped only for a recorded ownership, input, or external blocker.

We audited the milestone graph for self-dependencies. `TM-REL-001` depends on every other M2
task. The M3 documentation release then depends on `TM-REL-001` plus the existing-THRML
importer, hybrid partitioner, and hybrid-AI benchmark. Publication and RFC tasks depend on the
M3 reproducibility artifacts. This ordering removes a provisional cycle in which the M2
release gate depended on an M3 notebook task.

### H3 — Inspector Evidence Is Limited By Stored Artifacts

`SampleResult` stores samples, total energies, and offset-free interaction energies but does
not store the complete linear and quadratic Ising coefficients. The dependency-ready API is
now exact: `Inspector.from_result(result, *, model: IsingModel | None = None)`. Without a model,
association and objective recomputation are `not_available`; stored energy fields are not
promoted to oracle evidence. With a caller-supplied model, the core requires exact variable
order, accepts only `SPIN` or `BINARY` result encodings, and independently recomputes both total
and interaction energy for every sample row using the current vartype. Every row must agree at
the established absolute tolerance (`1e-9`, zero relative tolerance) before the association is
labeled `caller_supplied_sample_checked`; a mismatch fails closed. Compiled-manifest
association is deliberately deferred to `TM-API-001`/`TM-REP-001` because no public compiled
artifact exists at the snapshot. A final ledger comparison found one more omission: the
roadmap and design did not mirror the required deterministic model fingerprint. The corrected
contract hashes a documented `ising_energy_v1` positional coefficient payload using canonical
UTF-8 JSON and SHA-256, records exact variable order/vartype separately, and requires an
independent encoder test. It excludes metadata, label `repr`, pickle, object identity, and hash
iteration order.

### H4 — A Physical TSU Is An External Dependency

The public THRML backend is a JAX simulator. We placed physical programming, calibration,
timing, energy measurement, and TSU-versus-host claims in `TM-HW-001`, whose initial state is
`blocked_external`. M2 emits only `software_mvp_complete`; M3 emits only
`simulator_research_release_complete`. Without hardware, the honest autonomous terminal is M3
complete with `TM-HW-001` still `blocked_external`. M4 has no autonomous completion label and
can close only after the physical calibration gate. Modeled paper values and simulator wall
time cannot close it.

### H5 — Declared Python Support Requires A Matrix

`pyproject.toml` declares Python 3.10 through 3.13, while the snapshot workflow selects Python
3.13. `TM-REL-001` requires passing jobs for 3.10, 3.11, 3.12, and 3.13 before the release can
describe that range as verified. Optional THRML, dimod, and ArviZ environments remain a
separate matrix because their dependency bounds differ from the zero-dependency core.

### H6 — ESS Variants Require Separate Names And Threshold Provenance

The implemented diagnostic is raw-energy Geyer ESS under EVAL-EQ-008. Rank-normalized
bulk/tail ESS remains a distinct future estimator family with different transformations,
applicability rules, degenerate cases, and published recommendations. We assigned the missing
bulk/tail work to `TM-PROF-001` and required every efficiency output to name both its observable
and estimator. The task retains raw-energy Geyer ESS separately, cross-checks bulk/tail values
against pinned ArviZ and independent reference cases, and prohibits threshold transfer between
estimator variants.

### H7 — Governance Checks Must Not Require Future Outputs

The first TM-GOV gate said that “every referenced path and command” had to resolve. A fresh
reader correctly observed that downstream task cards intentionally name modules, tests, report
assets, and commands that do not exist yet. Requiring those planned outputs during governance
would make the first gate impossible. The corrected gate checks current control files,
canonical startup inputs, task-specific source inputs needed to select the first bounded task,
and commands required at governance time. Future output paths remain contracts owned by their
downstream tasks.

### H8 — Inspector Core And Full Reporting Need Separate Exit Claims

The prior Inspector design mixed artifact summarization with HTML, comparison, topology,
constraint, and baseline features whose producers are later in the DAG. The revised design
limits `GQ-INSPECT-01` to deterministic JSON/Markdown over `SampleResult` plus the optional
caller-supplied model check. HTML, `show()`, comparisons, compiled-manifest association,
topology/routing views, baseline integration, roofline views, and report bundles remain under
`TM-REP-001`. The design file is explicitly non-implementation evidence.

## Decisions

1. We made `reference/00-roadmap/README.md` the high-level index and
   `autonomous-implementation-roadmap.md` the owner of stable task definitions and
   dependencies.
2. We preserved `stage-00` through `stage-06` as historical product documents and reconciled
   their status in the index.
3. We adopted the runbook state vocabulary exactly: `planned`, `dependency_blocked`, `ready`,
   `claimed`, `in_progress`, `review`, `verified`, `complete`, and `blocked_external` through
   the declared transitions.
4. We aligned the first-lane identifiers across the roadmap, runbook, and ledger:
   `TM-VERIFY-01`, `TM-TARGET-01`, and `GQ-INSPECT-01`.
5. We defined five milestones: verified foundation, compiler kernel, software MVP, full
   simulator-backed research release, and a separately gated calibrated physical release.
   The verified foundation is M0, so the total count is M0 through M4. M2 and M3 use the narrow
   terminal labels `software_mvp_complete` and `simulator_research_release_complete`; M4 remains
   evidence-gated on physical calibration.
6. We gave every executable task a suggested file boundary, public test, blind/metamorphic
   test, independent oracle, and exit evidence.
7. We kept the equal-row 40% score as a capability snapshot and stated that it does not
   estimate remaining person-time.
8. We assigned every component from the supplied ThermoMap proposal to at least one stable
   task ID through a final coverage matrix.
9. We made rank-normalized bulk/tail ESS a required `TM-PROF-001` deliverable with equation-
   first definitions, observable-specific names, reference cross-checks, and estimator-specific
   threshold provenance.
10. We scoped `TM-GOV-001` path/command checks to current controls and required source inputs,
    excluding downstream output contracts until their owner starts.
11. We fixed the core Inspector signature and model-association semantics, including exact
    variable order, supported vartypes, all-row dual-energy recomputation, fail-closed mismatch
    behavior, deterministic association fingerprint, and the
    `caller_supplied_sample_checked`/`not_available` states.
12. We made first-lane selection deterministic under limited capacity by selecting the ordered
    prefix `TM-VERIFY-01`, `TM-TARGET-01`, `GQ-INSPECT-01`.

## Rejected Alternatives

- We rejected replacing the legacy stage files because that would erase the sequence and
  rationale of the original Gibbsiq implementation.
- We rejected the linear `0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6` chain as the execution scheduler.
  Independent verifier, target-contract, and artifact-Inspector work have disjoint files and
  can proceed concurrently after governance closes.
- We rejected marking coding lanes `ready` during the governance review. The live ledger keeps
  them `dependency_blocked` until the coordinator verifies the control plane.
- We rejected broad week-sized tasks without oracles because an agent could satisfy them with
  prose or self-reported output.
- We rejected presenting `_Lowering` as a public `THRMLProgramBundle`; the snapshot has the
  private implementation type only.
- We rejected treating stored Inspector energies as independently verified canonical energies
  when the model coefficients are absent.
- We rejected a compiled manifest as a `GQ-INSPECT-01` model input because the public compiled
  artifact is not defined until `TM-API-001`; integration belongs to `TM-REP-001`.
- We rejected checking only the best Inspector witness. A wrong non-best energy row would pass,
  so model association requires total and interaction-energy checks for every row.
- We rejected `repr`, pickle, object identity, and unordered mapping iteration in the model
  fingerprint. The positional `ising_energy_v1` coefficient payload is portable and is bound to
  the separately recorded exact variable order and vartype.
- We rejected forcing future output modules and report commands to exist before governance can
  close; the owning downstream task supplies and verifies those outputs.
- We rejected scheduler discretion when fewer than three first-lane workers are available;
  deterministic prefix selection is reproducible and any exception must name its blocker.
- We rejected treating `requires-python` metadata as compatibility evidence without the
  matching CI jobs.
- We rejected routing bulk/tail ESS to the profiler without an executable exit gate, and we
  rejected applying a published rank-normalized recommendation to the existing raw-energy
  Geyer estimate.
- We rejected hard-coded Z1 parameters, simulator-to-silicon extrapolation, and paper-derived
  values labeled as measurements.

## Sources Read And Examples Used

- `AGENTS.md`, `PROJECT_BRIEF.md`, `spec.md`, and `CLAUDE.md`.
- `reference/README.md`, `reference/glossary.md`, and
  `reference/claims-evidence-map.md`.
- `reference/00-roadmap/README.md`, all seven legacy stage files, and
  `reference/00-roadmap/thermomap-plan-status-2026-07-14.md`.
- `reference/08-evaluation/equation-audit.md`, `evaluation-framework.md`, and
  `agentic-evaluation-research.md`.
- `reference/06-benchmarks/ground-truth-datasets.md` and
  `tools/generate_ground_truth.py`.
- `reference/research-journal/gotchas-and-todo.md`, `style.md`, and
  `2026-07-14-thermomap-final-integration-verification.md`.
- Production and test file inventories under `src/gibbsiq/` and `test_suite/tests/`, plus
  `pyproject.toml` and `.github/workflows/ci.yml` for compatibility claims.
- `reference/00-roadmap/autonomous-agent-runbook.md` for the exact source-precedence and task
  selection contracts.
- `reference/07-inspector/inspector-design.md`, `src/gibbsiq/model.py`,
  `src/gibbsiq/result.py`, `src/gibbsiq/benchmark_oracle.py`, and their focused tests for the
  Inspector association, vartype, best-row, and absolute-tolerance contracts.

No new hardware number or external performance claim was introduced. Primary-paper
classifications and hashes remain in the 2026-07-14 final integration journal.

## Artifacts

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| `reference/00-roadmap/README.md` | 11,232 | `d60c9cfd6e07d3577d42581d7ee16c80cfa2c7f9191fcb5e9fed05c3ec420408` |
| `reference/00-roadmap/autonomous-implementation-roadmap.md` | 62,159 | `e92d15a2b38134896eb9324f8412a50cdc429951594d8dbcd5a472e7f94d7ce9` |
| `reference/07-inspector/inspector-design.md` | 10,575 | `544c6152a72dda2692486916a1de7ff6268bb3d0144f6ac3270f4cfe4e57fdf0` |

The hashes identify the reader-corrected roadmap artifacts that passed the focused document
checks. Any later coordinator correction produces new final hashes in the integration journal
or commit record.

## Verification

Focused document checks ran from `E:\projects\Gibbsiq` on Windows in PowerShell:

```powershell
python tools/check_markdown_math.py reference/00-roadmap/README.md reference/00-roadmap/autonomous-implementation-roadmap.md reference/research-journal/2026-07-14-autonomous-thermomap-roadmap.md reference/07-inspector/inspector-design.md
git diff --check -- reference/00-roadmap/README.md reference/00-roadmap/autonomous-implementation-roadmap.md reference/research-journal/2026-07-14-autonomous-thermomap-roadmap.md reference/07-inspector/inspector-design.md
```

Both commands completed successfully. `git diff --check` emitted only the repository's
line-ending conversion warning for `reference/00-roadmap/README.md`; it reported no whitespace
error. A scoped path/link audit checked 15 current control/startup inputs and 28 local Markdown
links with zero missing paths. Planned downstream output modules/tests were intentionally
excluded from the governance existence gate.

A task-ID consistency and task-card dependency scan extracted all `TM-*` and `GQ-*`
identifiers. It found 36 defined IDs, zero duplicates, zero undefined used IDs, zero
defined-but-unused IDs, zero unknown dependencies, and zero dependency cycles. The fresh-reader
reconciliation also checked matching first-lane prefix order, the exact Inspector signature,
all-row total/interaction-energy validation, the independently reproducible
`ising_energy_v1` fingerprint contract, and first-tie interaction-energy selection against the
actual task cards, ledger, `IsingModel`, and `SampleResult.best_index`.

The final orphan-gap check verified that `TM-PROF-001` names raw-energy Geyer ESS separately,
requires observable-specific rank-normalized bulk/tail outputs and matching reference cases,
and prohibits threshold transfer. It also verified the hard graph edges for the physics
(`TM-NID-002`, `TM-CAT-001`), Bayesian (`TM-IR-001`, `TM-VERIFY-01`), optimization
(`TM-LWR-001`, `TM-CAT-001`), and hybrid-AI (`TM-HYB-001`, `TM-CAT-001`) benchmark tasks.
The first textual assertion expected one threshold sentence to be contiguous and failed because
Markdown line wrapping placed a newline between `tail` and `threshold`; the corrected check
uses a whitespace-tolerant regular expression and passed without changing the contract.

The full 457-test run belongs to the unchanged production snapshot and was not rerun for this
documentation-only task.

## Follow-Up

1. The coordinator performs a context-free reader test across the index, runbook, roadmap, and
   ledger, then records corrections.
2. After `TM-GOV-001` verifies, the coordinator changes it to `complete` and exposes the three
   first lanes as `ready` in `NEXT_TASK.md`.
3. The first implementation agent claims one lane with exclusive file ownership and follows
   the per-task public, blind, oracle, journal, and commit gates.
