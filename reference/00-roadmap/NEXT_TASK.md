# Live Task Ledger

## Ledger Checkpoint

| Field | Value |
| --- | --- |
| Observed date | 2026-07-15 |
| Verified implementation base | `c62169e` (`feat: add audited ThermoMap analysis foundation`) |
| Verified control-plane documentation | `21c2a71` (`docs: add autonomous ThermoMap execution roadmap`) |
| Implementation score at base | 8/20 ThermoMap rows = 40%, using the equal-row audit in `thermomap-plan-status-2026-07-14.md` |
| Public backend | THRML JAX simulator; no production TSU artifact is present |
| Control-plane state | `TM-GOV-001` is `complete`; `21c2a71` verifies the control documents and this ledger transition closes the task |
| Active governance owner | none |
| Current coding state | `TM-VERIFY-01`, `TM-TARGET-01`, and `GQ-INSPECT-01` are `verified` implementation candidates; worker ownership is released and coordinator `/root` owns integration |
| Scratch state observed before this pass | Untracked `Project_GOAL.md` supplied as task input; excluded from the implementation commit |

The implementation base has a recorded full-suite result of 457 tests in 120.615 seconds at
the environment captured by
`reference/research-journal/2026-07-14-thermomap-final-integration-verification.md`. This is
historical evidence tied to that command and commit. Every later completion records the count,
skips, duration, dependencies, and environment from the command actually run.

During the 2026-07-15 implementation pass, all three lanes advanced through `claimed`,
`in_progress`, and `review` before the coordinator set the current `verified` state. The worker
claims and review corrections are preserved in the dated task and integration journals; the
intermediate dirty-worktree states are not separate Git commits.

## Source Control Rules

- [Autonomous implementation roadmap](autonomous-implementation-roadmap.md): dependencies,
  gates, and project completion.
- [Autonomous agent runbook](autonomous-agent-runbook.md): task selection, verification,
  ownership, handoff, and stop conditions.
- [Dated status audit](thermomap-plan-status-2026-07-14.md): evidence-based baseline and gaps.
- `reference/08-evaluation/equation-audit.md`: mathematical authority.

Executable source/tests plus the latest dated verification evidence outrank stale progress
prose. Reconcile a conflict before selecting a feature task.

## State Table

| Task | State | Dependencies | Reason |
| --- | --- | --- | --- |
| `TM-FND-001` | `complete` | none | Canonical model, runtime, diagnostics, and witness oracle are verified at `c62169e`. |
| `TM-FND-002` | `complete` | none | Target-analysis and finite-state foundation is verified at `c62169e`. |
| `TM-GOV-001` | `complete` | none | Control documents, links, task graph, reader test, and evidence were verified in `21c2a71`; this ledger transition closes the task. |
| `TM-VERIFY-01` | `verified` | `TM-FND-001`, `TM-GOV-001` | Focused, independent-oracle, artifact, static, and final 518-test repository gates pass; awaiting the feature commit. |
| `TM-TARGET-01` | `verified` | `TM-FND-002`, `TM-GOV-001` | Focused, exhaustive-topology, artifact, compatibility, static, and final 518-test repository gates pass; awaiting the feature commit. |
| `GQ-INSPECT-01` | `verified` | `TM-FND-001`, `TM-GOV-001` | Focused, independent fingerprint/energy, artifact, static, and final 518-test repository gates pass; awaiting the feature commit. |
| `TM-IR-001` | `dependency_blocked` | `TM-VERIFY-01` | The implementation is verified but the dependency becomes `complete` only in the post-feature ledger transition. |

## Historical Governance Closure — `TM-GOV-001`

Objective: establish one internally consistent control plane from which a context-free agent
selects the same next task and can state its dependencies, files, oracle, and exit condition.

Closure owner: coordinator `/root`. Current owner: none.

Owned files for this coordinated pass:

- `reference/00-roadmap/README.md`;
- `reference/00-roadmap/autonomous-implementation-roadmap.md`;
- `reference/00-roadmap/autonomous-agent-runbook.md`;
- `reference/00-roadmap/NEXT_TASK.md`;
- explicitly assigned root guidance/status files;
- distinct dated journal entries.

Closure checklist, verified against control-plane documentation commit `21c2a71`:

- [x] Every current control-document link, command, and pre-existing required input/source path
      exists. Future worker outputs named for creation (new modules, tests, artifacts, and
      dated journals) are excluded from this governance existence check.
- [x] Roadmap task IDs and dependencies match this ledger.
- [x] Root guidance points to the roadmap and live ledger without preserving a contradictory
      current-stage claim.
- [x] A context-free reader identifies the same three next coding lanes.
- [x] `python tools/check_markdown_math.py` passes.
- [x] `git diff --check` passes.
- [x] The coordinator reads every documentation diff and records the commands and results.
- [x] A dated journal entry records choices, rejected alternatives, and a paper hook.
- [x] The coordinator committed the verified documentation separately from `c62169e` and records
      the new SHA here.

The checklist is closed. Commit `21c2a71` contains the independently reviewed control-plane
documents; this subsequent ledger patch records the authorized state transition. The
state-transition commit cannot contain its own SHA without creating a self-referential content
cycle, so Git history is the authoritative identity of this transition.

Worker-capacity selection is deterministic after that transition:

- one available worker slot: claim `TM-VERIFY-01`;
- two available worker slots: claim `TM-VERIFY-01` and `TM-TARGET-01`;
- three or more available worker slots: claim all three lanes in the order
  `TM-VERIFY-01`, `TM-TARGET-01`, `GQ-INSPECT-01`.

This is a prefix rule. Reconcile an earlier task that ceases to be `ready` before claiming a
later lane. Each worker owns one bounded task, and each lane remains serial.

## Verified First-Frontier Commit Candidate

### `TM-VERIFY-01` — Independent CPU Gibbs And Exact Kernel Verifier

- Gate/state: M1 compiler kernel; `verified`.
- Dependencies: `TM-FND-001`, `TM-GOV-001`.
- Owner: none; implementation worker `/root/tm_verify_01`, coordinator reviewer `/root`.
- Blocker: none; both dependencies are complete.
- Objective: add a THRML-independent seeded Gibbs reference and capped transition,
  stationarity, detailed-balance, and empirical-interval verification.
- Sources: EVAL-EQ-001/004/005/014 in `reference/08-evaluation/equation-audit.md`;
  `src/gibbsiq/exact_distribution.py`;
  `test_suite/tests/test_exact_distribution.py`,
  `test_suite/tests/test_exact_fixtures.py`, and
  `test_suite/tests/test_runtime_correctness_contracts.py`.
- Worker-owned files: `src/gibbsiq/reference_sampler.py`,
  `src/gibbsiq/verification.py`, relevant new entries in
  `reference/08-evaluation/equation-audit.md`,
  `test_suite/tests/test_reference_sampler.py`, and
  `test_suite/tests/test_statistical_verifier.py`.
- Shared integration files reserved for coordinator: `src/gibbsiq/__init__.py`, this ledger,
  root docs, and package-wide reports.
- Public gate: analytic one/two-spin conditionals; row-stochastic capped kernels; enumerated
  stationary and detailed-balance residuals; wrong-sign and non-ergodic traps; fixed-seed
  exact trace replay; predeclared simultaneous empirical intervals.
- Independent oracle: `exact_distribution.py`, direct conditional tables, direct row sums and
  stationary equations implemented outside the sampler path.
- Blind contract: gauge, relabel, offset, beta-zero, isolated-variable, permutation-similar
  kernel, delayed-kernel, hidden small-graph, and private-seed mutations.
- Exit evidence: raw traces, RNG identity, seed, interval method, state cap, tolerance,
  work-unit accounting, focused/full commands, actual counts/skips, journal, and review.
- Artifact target: `reference/00-roadmap/artifacts/tm-verify-01/<run-id>/` with raw traces,
  transition evidence, config, environment, manifest, and SHA-256 values.
- Acceptance commands: focused discovery with patterns `test_reference_sampler.py` and
  `test_statistical_verifier.py`, followed by the shared acceptance commands below.
- Journal target: `reference/research-journal/YYYY-MM-DD-tm-verify-01.md`.
- Last verified: 2026-07-15 coordinator run passed 10 sampler tests, 20 verifier tests, the
  final 518-test suite with 0 skips in 108.136 seconds, Ruff, format, mypy, Markdown math, and
  diff checks. Seven manifest-covered files rehashed successfully; manifest SHA-256 is
  `7c203e5672a3d8ff1f976ee163778a43f877131e2f452f9362ba7ad20008e253`.

### `TM-TARGET-01` — Complete Provenanced Target Specification

- Gate/state: M1 compiler kernel; `verified`.
- Dependencies: `TM-FND-002`, `TM-GOV-001`.
- Owner: none; implementation worker `/root/tm_target_01`, coordinator reviewer `/root`.
- Blocker: none; both dependencies are complete.
- Objective: complete the immutable target contract without inventing Z1 defaults.
- Sources: `src/gibbsiq/hardware.py`, `src/gibbsiq/hardware_assessment.py`,
  `reference/01-architecture/papers/jelincic-2025-probabilistic-hardware-architecture.pdf`
  (primary Extropic architecture/model source; classify each field as measured or modeled),
  `reference/01-architecture/papers/jelincic-2026-codon-optimization.pdf` (modeled workload
  evidence), `reference/05-theory/papers/aadit-2026-million-pbit.pdf` (non-Extropic digital
  p-bit comparator; never TSU measurement evidence),
  `reference/research-journal/2026-07-14-hardware-admissibility-assessment.md`,
  `reference/research-journal/2026-07-14-thermomap-fixed-point-quantization.md`, and
  `reference/research-journal/2026-07-14-communication-contention-correction.md`.
- Worker-owned files: `src/gibbsiq/hardware.py`, new `src/gibbsiq/topology.py`, and
  `test_suite/tests/test_target_spec.py`.
- Shared integration files reserved for coordinator: `src/gibbsiq/__init__.py`, this ledger,
  root docs, and package-wide reports.
- Public gate: deterministic finite serialization; grid/explicit topology validation;
  independently recomputed capacity, degree, distance, and adjacency; explicit unknowns for
  absent accumulator, communication, host-transfer, programming, or reprogramming facts;
  invalid units and provenance fail closed.
- Independent oracle: enumerate small topology adjacency without consuming target-derived
  summary values.
- Blind contract: reflected/translated grids, reordered explicit graphs, omitted optional
  facts, unknown propagation, impossible limits, and unit-scale mutations.
- Exit evidence: every external number has source class, primary identifier/access date, and
  sensitivity range; no physical TSU field is labeled measured without a device artifact.
- Artifact target: `reference/00-roadmap/artifacts/tm-target-01/<run-id>/` with serialized
  target fixtures, independently enumerated topology facts, source manifest, and SHA-256 values.
- Acceptance commands: focused discovery with patterns `test_target_spec.py`,
  `test_hardware_specs.py`, and `test_hardware_assessment.py`, followed by the shared commands.
- Journal target: `reference/research-journal/YYYY-MM-DD-tm-target-01.md`.
- Last verified: 2026-07-15 coordinator run passed 15 target tests, 32 nearest hardware tests,
  exhaustive independent enumeration of 48 grids and all 1,099 simple graphs through five
  nodes, the final 518-test suite with 0 skips in 108.136 seconds, and all static gates. Eight
  manifest entries rehashed successfully; manifest SHA-256 is
  `5fc6a3a32087561936dff69beebcc619d28cbee2e0bb0b3ae220a5b7121e94df`.

### `GQ-INSPECT-01` — Artifact-Only Inspector Core

- Gate/state: M2 software MVP; `verified`.
- Dependencies: `TM-FND-001`, `TM-GOV-001`.
- Owner: none; implementation worker `/root/gq_inspect_01`, coordinator reviewer `/root`.
- Blocker: none; both dependencies are complete.
- Objective: implement `Inspector.from_result(result, *, model: IsingModel | None = None)` as
  a deterministic consumer of stored `SampleResult` artifacts without rerunning THRML.
- Sources: EVAL-EQ-001 in `reference/08-evaluation/equation-audit.md`,
  `src/gibbsiq/model.py`, `src/gibbsiq/result.py`, `src/gibbsiq/benchmark_oracle.py`,
  `reference/00-roadmap/stage-04-inspector-and-reporting.md`,
  `reference/07-inspector/inspector-design.md`,
  `test_suite/tests/test_model_compatibility.py`, and
  `test_suite/tests/test_benchmark_oracle.py`.
- Worker-owned files: `src/gibbsiq/inspector.py`,
  `test_suite/tests/test_inspector.py`, and
  `reference/07-inspector/inspector-design.md`.
- Shared integration files reserved for coordinator: `src/gibbsiq/__init__.py`, this ledger,
  root docs, and full HTML/CLI integration assigned to `TM-REP-001`. Compiled-manifest binding
  belongs to `TM-API-001`/`TM-REP-001`; it is outside this core API.
- Public gate: deterministic JSON and Markdown summaries; one/multi-chain results; recompute
  the first-tie argmin of stored `interaction_energies` and select the corresponding sample
  and total `energies` row; offset metadata; missing optional metadata; explicit unavailable
  sections; serialization round trips; sampler execution disabled during tests. With
  `model=None`, canonical objective verification reports `not_available` and states that no
  model was supplied. With a model, require a `SPIN` or `BINARY` result and an exact variable
  tuple match; recompute every sampled canonical total and interaction energy using the result
  vartype; compare every stored value at the audited absolute tolerance `1e-9`; and fail the
  report on any mismatch. Record that the association is caller-supplied together with a
  deterministic model fingerprint, vartype, variable order, and verification tolerance. The
  fingerprint encoding must be documented and independently tested; it must never depend on
  process-specific `repr` output.
- Independent oracle: outside Inspector, separately recompute sample counts, the first-tie
  argmin of stored `interaction_energies`, the corresponding total energy and sample, every
  model-supplied total/interaction energy, and the deterministic association fingerprint.
- Blind contract: variable/key reordering, offset shifts with a supplied model, hostile labels,
  unknown diagnostic keys, corrupt best-row selection, a corrupted non-best energy row,
  vartype/variable mismatch, model/energy mismatch, and absent optional sections.
- Exit evidence: focused/full commands with actual counts/skips, artifact-only proof, journal,
  and critical coordinator review.
- Artifact target: `reference/00-roadmap/artifacts/gq-inspect-01/<run-id>/` with the input
  result, optional caller-supplied model association/fingerprint evidence, JSON and Markdown
  summaries, environment, and SHA-256 values.
- Acceptance commands: focused discovery with pattern `test_inspector.py`, followed by the
  shared acceptance commands below.
- Journal target: `reference/research-journal/YYYY-MM-DD-gq-inspect-01.md`.
- Last verified: 2026-07-15 coordinator run passed 15 Inspector tests, public API integration,
  the final 518-test suite with 0 skips in 108.136 seconds, and all static gates. Six
  manifest-covered files rehashed successfully; manifest SHA-256 is
  `7aae3476248a9483bfdf9b4f5de7489bdd94112859170a695f1d85cf1f44804e`.

## Shared Acceptance Commands

Set `$env:PYTHONPATH = "src"`, replace `<pattern>` with each lane's focused test filename, and
record the actual test/skip count from every command:

```powershell
python -m unittest discover -s test_suite/tests -p "<pattern>"
python -m unittest discover -s test_suite/tests
python tools/check_markdown_math.py
ruff check .
ruff format --check .
mypy src/gibbsiq
git diff --check
```

## Parallel Ownership Matrix

| File family | Owner while lanes run |
| --- | --- |
| `reference_sampler.py`, `verification.py`, verifier tests, assigned equation entries | `TM-VERIFY-01` worker |
| `hardware.py`, `topology.py`, target-spec tests | `TM-TARGET-01` worker |
| `inspector.py`, inspector tests/design note | `GQ-INSPECT-01` worker |
| `__init__.py`, roadmap, ledger, root docs, integration journal/commit | Coordinator only |

Workers use distinct journal filenames. If an unexpected edit appears inside an owned file,
the worker rereads and retries the patch. It reports an actual semantic overlap to the
coordinator; it never discards the other change.

## External Blocker Ledger

| Gate | State | Required state change |
| --- | --- | --- |
| Physical TSU calibration | `blocked_external` | Authorized backend/device, identity and versions, calibration artifacts, timing/energy measurement boundary, and publication permission. |

This external blocker does not block simulator/compiler work. Record `software_mvp_complete`
when M2 closes. Record `simulator_research_release_complete` when every autonomous public and
simulator task through M3 closes. Without device access, the final autonomous state is M3
complete with `TM-HW-001` retained as `blocked_external`; calibrated physical completion
requires M4 evidence.

## Handoff Template

```text
Task / state / commit:
Changed files:
Choices and rejected alternatives:
Independent oracle and result:
Focused command — tests, skips, duration:
Full/static commands — tests, skips, duration:
Raw artifacts — paths, SHA-256, seeds, environment:
Known failures and limitations:
Next dependency-ready task and ownership:
```

Missing fields keep a task in `review`.
