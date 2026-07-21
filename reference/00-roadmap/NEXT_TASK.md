# Live Task Ledger

## Ledger Checkpoint

| Field | Value |
| --- | --- |
| Observed date | 2026-07-21 |
| Verified implementation base | `c62169e` (`feat: add audited ThermoMap analysis foundation`) |
| Verified control-plane documentation | `21c2a71` (`docs: add autonomous ThermoMap execution roadmap`) |
| Verified first-frontier implementation | `42c2409` (`feat: implement first ThermoMap frontier`) |
| Reconciled TM-IR implementation base | `35a2ba3` (`feat: comprehensive correctness, robustness, and reference audit`) |
| Implementation score at base | 8/20 ThermoMap rows = 40%, using the equal-row audit in `thermomap-plan-status-2026-07-14.md` |
| Public backend | THRML JAX simulator; no production TSU artifact is present |
| Control-plane state | `TM-GOV-001` is `complete`; `21c2a71` verifies the control documents and this ledger transition closes the task |
| Active governance owner | none |
| Current coding state | `TM-VERIFY-01`, `TM-TARGET-01`, `GQ-INSPECT-01`, `TM-IR-001`, and `TM-IMP-001` are `complete`; `TM-LWR-001`, `TM-CAT-001`, `TM-IMP-002`, and `TM-VAL-001` are dependency-ready and unclaimed, with `TM-LWR-001` earliest in roadmap edge order |
| Scratch state observed before this pass | Untracked `Project_GOAL.md` and three 2026-07-15 audit journals remain preserved and excluded from task commits; the audit-defect remediation commit `403bbb3` precedes this closure and repaired both confirmed defects on this task's critical paths |

The implementation base has a recorded full-suite result of 457 tests in 120.615 seconds at
the environment captured by
`reference/research-journal/2026-07-14-thermomap-final-integration-verification.md`. This is
historical evidence tied to that command and commit. Every later completion records the count,
skips, duration, dependencies, and environment from the command actually run.

During the 2026-07-15 implementation pass, all three lanes advanced through `claimed`,
`in_progress`, `review`, and `verified` before feature commit `42c2409` allowed this ledger to
set them `complete`. The worker claims and review corrections are preserved in the dated task
and integration journals; the intermediate dirty-worktree states are not separate Git commits.

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
| `TM-VERIFY-01` | `complete` | `TM-FND-001`, `TM-GOV-001` | Independent CPU Gibbs and exact verifier evidence is committed in `42c2409`. |
| `TM-TARGET-01` | `complete` | `TM-FND-002`, `TM-GOV-001` | Complete target-fact/topology evidence is committed in `42c2409`. |
| `GQ-INSPECT-01` | `complete` | `TM-FND-001`, `TM-GOV-001` | Artifact-only Inspector evidence is committed in `42c2409`. |
| `TM-IR-001` | `complete` | `TM-VERIFY-01` | The implementation at `35a2ba3` plus the adversarial hardening, raw evidence, and ledger transition in the containing commit pass every closure gate. |
| `TM-IMP-001` | `complete` | `TM-IR-001` | Factor-graph JSON schema v1, the NetworkX frontend, tests, artifacts, and journal pass every closure gate in the commit containing this transition. |
| `TM-LWR-001` | `ready` | `TM-IR-001`, `TM-VERIFY-01` | Both dependencies are complete; it is the earliest ready task in roadmap edge order and remains unclaimed. |
| `TM-CAT-001` | `ready` | `TM-IR-001`, `TM-VERIFY-01`, `TM-TARGET-01` | All dependencies are complete; unclaimed. |
| `TM-IMP-002` | `ready` | `TM-IR-001`, `TM-TARGET-01` | Both dependencies are complete; unclaimed. |
| `TM-VAL-001` | `ready` | `TM-IR-001`, `TM-TARGET-01` | Both dependencies are complete; unclaimed. |

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

## Completed First Frontier

### `TM-VERIFY-01` — Independent CPU Gibbs And Exact Kernel Verifier

- Gate/state: M1 compiler kernel; `complete`.
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
  Feature commit: `42c2409`.

### `TM-TARGET-01` — Complete Provenanced Target Specification

- Gate/state: M1 compiler kernel; `complete`.
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
  Feature commit: `42c2409`.

### `GQ-INSPECT-01` — Artifact-Only Inspector Core

- Gate/state: M2 software MVP; `complete`.
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
  Feature commit: `42c2409`.

## Completed Thermodynamic IR

### `TM-IR-001` — Thermodynamic Program Envelope, Clamping, And Coordinates

- Gate/state: M1 compiler kernel; `complete` in the commit containing this ledger transition.
- Dependencies: `TM-VERIFY-01`, complete in `42c2409`.
- Owner: none. Coordinator `/root` reconciled the implementation already tracked at `35a2ba3`,
  delegated the bounded hardening to `/root/tm_ir_impl_audit`, and critically inspected its
  actual diff. Fresh reviewer `/root/ledger_audit` independently attacked recursive labels,
  serialization, metadata shape, relabeling, and exhaustive categorical energies. Earlier
  worker/process history remains in the 2026-07-15 task journal; the 2026-07-17 closure journal
  records the reconciliation and final corrections.
- Objective: add an immutable, target-independent `ThermodynamicProgram` envelope around one
  audited logical model with deterministic free/clamped roles, clamp values, optional logical
  coordinates, observation metadata, and factor/source identities.
- Worker-owned files: new `src/gibbsiq/program.py`; narrow changes to
  `src/gibbsiq/model.py`, `src/gibbsiq/categorical.py`, and `src/gibbsiq/result.py`;
  `test_suite/tests/test_thermodynamic_program.py`;
  `reference/08-evaluation/equation-audit.md` entry assigned to this task; deterministic raw
  evidence under `reference/00-roadmap/artifacts/tm-ir-001/`; and the append-only task journal
  `reference/research-journal/2026-07-15-tm-ir-001.md`.
- Shared integration files reserved for coordinator: `src/gibbsiq/__init__.py`, this ledger,
  `reference/claims-evidence-map.md`, root guidance/status files, and final integration review.
- Public gate: immutable defensive freezing; exactly one `IsingModel` or `CategoricalModel`;
  deterministic variable/domain/free/clamped order; strict unknown, duplicate, conflicting,
  Boolean-alias, and out-of-domain clamp rejection; logical coordinates, observations, and
  factor/source identities; all-free, partial, full, and isolated-variable projection;
  exhaustive energy equivalence; same-type zero-variable constant projection; offset and
  source-factor preservation; deterministic relabeling; and deterministic versioned lossless
  serialization.
- Blind contract: hidden relabel, isolated-variable, clamp/unclamp, offset-shift, and spin-gauge
  mutations.
- Independent oracle: test code enumerates every free assignment, merges it with clamps,
  evaluates the original model directly without the production projection helper, and compares
  it with the projected model at `rel_tol=0.0`, `abs_tol=1e-9`.
- Artifact target: `reference/00-roadmap/artifacts/tm-ir-001/<run-id>/` with serialization and
  projection fixtures, environment/configuration, manifest, and SHA-256 values.
- Review evidence: run `2026-07-15-program-envelope` contains 42 deterministic programs and
  248 independently recomputed free assignments; every energy, serialization round trip, and
  lineage-destination check passed with maximum absolute energy error `0.0`. The manifest
  records SHA-256 values for all six evidence files, including nine pinned source/test files,
  and the generator refuses overwrite unless `--overwrite` is explicit.
- Last verified: 2026-07-17 on CPython 3.13.5 / Windows 11 against source base `35a2ba3`.
  Recursive typed-label identity, canonical decoding, metadata reconstruction, and categorical
  relabel evidence have permanent regressions. The focused module passed 31 tests; the final
  repository suite passed 603 tests with zero skips in 89.427 seconds; Ruff, format, mypy over
  24 source files, Markdown math, deterministic-payload comparison, manifest/source rehashing,
  and `git diff --check` passed. Manifest SHA-256 is
  `8faf62c46b2265eb2982737ec4b6cb3eb7dc766138abf8a4b13eed1a8a74d785`; the pinned-source
  aggregate is `45c76ad8621d9705e3a3493e8e17cf8915599f04580dacce66369149f3849dd4`.
- Acceptance commands: focused discovery with `test_thermodynamic_program.py`; the nearest
  model, categorical, result, immutability, Inspector, and public-API modules; then the shared
  full/static commands below.
- Exit evidence: equation-audit entry before production code, recorded test-first red phase,
  serialized round trip, raw fixtures/checksums, worker handoff, independent reviewer, and a
  journal with rejected schema alternatives.
- Completion condition: satisfied by the commit containing the verified code corrections,
  tests, journals, artifacts, and this transition. Git history is authoritative because a
  state-transition commit cannot contain its own final SHA.

## Completed Import Frontend

### `TM-IMP-001` — Factor-JSON And NetworkX Frontends

- Gate/state: M1 compiler kernel; `complete` in the commit containing this ledger transition.
- Dependencies: `TM-IR-001`, complete in the `cdd0a58` closure.
- Owner: none. A single session working from remediated base `403bbb3` wrote the schema
  contract first, the falsifying tests second, and the implementation third; an independent
  simplification pass reviewed the final module.
- Objective: import and export a versioned pairwise factor-graph JSON record and import NetworkX
  graphs into `ThermodynamicProgram` with explicit coefficient, vartype, offset, node-order,
  clamp, coordinate, and metadata policies.
- Delivered files: `src/gibbsiq/importers.py`;
  `reference/02-interfaces/factor-graph-json-v1.md` (wire contract, written before code);
  `test_suite/tests/test_importers.py`; `tools/generate_tm_imp_001_artifacts.py`; a
  `networkx>=3.0` optional extra in `pyproject.toml`; five public exports in
  `src/gibbsiq/__init__.py`; and the dated journal
  `reference/research-journal/2026-07-21-tm-imp-001-factor-json-and-networkx-frontends.md`.
- Research boundary outcome: NetworkX node-link JSON, dimod bqm_schema 3.0.0, pgmpy/UAI/libDAI
  tables, and the benchmark edge-list formats each lose typed labels, the offset, or program
  sections; licenses (BSD-3-Clause, Apache-2.0, MIT) are recorded in the schema document and
  no external implementation or test code was copied. Only NetworkX's public iteration API is
  consumed, by duck typing, so `importers.py` never imports networkx.
- Public and blind gates: covered by 39 focused tests, including shuffled records, recursive
  typed labels, reversed/duplicate edges, isolated nodes, offset shifts, hand-converted
  symmetric-QUBO equivalence, Boolean/numeric aliases, JSON-key coercion, and a subprocess
  proof that the module imports and runs with networkx blocked.
- Independent oracle result: 15,993 enumerated assignments across 1,500 random documents and
  5,159 across 500 random graphs match direct source evaluation with maximum absolute errors
  `3.553e-15` and `1.776e-15`; the 1,500-document export corpus SHA-256 is byte-identical
  under `PYTHONHASHSEED=1` and `31337`.
- Artifact evidence: run `2026-07-21-factor-json-and-networkx` under
  `reference/00-roadmap/artifacts/tm-imp-001/` holds 36 document and 16 graph fixtures with
  494 independently enumerated energies, export fixed-point and insertion-order-invariance
  checks, environment, seeds, and pinned sources. Manifest SHA-256 is
  `f904a672dd3959c4d9d23d2bf65d2dcf0a2af208188318ddf957a20b61f69f08`; the pinned-source
  aggregate is `58e9a4ffc904fad47e1106710a440d0d11c2554e21504c95eb71df19ce7ef7a0`.
- Last verified: 2026-07-21 on CPython 3.13.5 / Windows 11. Focused module 39 tests in
  0.158 seconds; nearest program/model/conversion/public-API modules 71 tests; the full
  suite 647 tests with 0 skips in 101.164 seconds; Markdown math, Ruff check, Ruff format,
  mypy over 25 source files, and `git diff --check` pass.
- Completion condition: satisfied by the commit containing the verified code, tests, schema
  contract, artifacts, journal, and this transition. Git history is authoritative because a
  state-transition commit cannot contain its own final SHA.

## Next Dependency-Ready Tasks

Four tasks are dependency-ready and unclaimed; full cards live in
`autonomous-implementation-roadmap.md`. Worker-capacity selection is a prefix rule in roadmap
edge order:

1. `TM-LWR-001` — Higher-Order And Constraint Lowering (`TM-IR-001` + `TM-VERIFY-01`).
2. `TM-CAT-001` — Categorical Conditional And THRML Execution
   (`TM-IR-001` + `TM-VERIFY-01` + `TM-TARGET-01`).
3. `TM-IMP-002` — Existing-THRML Program Importer (`TM-IR-001` + `TM-TARGET-01`).
4. `TM-VAL-001` — Whole-Program Validation And Structured Compile Failure
   (`TM-IR-001` + `TM-TARGET-01`).

Each worker claims exactly one bounded task and records the claim here before editing owned
files. Reconcile an earlier task that ceases to be `ready` before claiming a later lane.

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
| Files named by each ready task's roadmap-card suggested ownership | Future worker after claim |
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
