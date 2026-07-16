# Autonomous Agent Runbook

## Purpose And Completion Boundary

This runbook is the operating procedure for a fresh agent advancing Gibbsiq from the current
audited kernel to the ThermoMap software roadmap. The dependency graph and exit criteria live
in [the autonomous implementation roadmap](autonomous-implementation-roadmap.md). Active task
claims, file ownership, and verification states live in [`NEXT_TASK.md`](NEXT_TASK.md).

An agent can complete every public-software, simulator, benchmark, reporting, and publication
gate without Extropic hardware access. Physical TSU calibration is a hard external-access
gate. A simulator result, paper model, or assumed parameter cannot close that gate or support
a measured TSU-performance claim.

## Source-Of-Truth Precedence

Different files own different kinds of truth. Apply this order before selecting work.

1. `AGENTS.md` and higher-level instructions own workflow and non-negotiable behavior.
2. `reference/08-evaluation/equation-audit.md` owns mathematical conventions.
3. Executable source, tests actually run at the current `HEAD`, and the latest dated
   verification/status record own implementation status.
4. `autonomous-implementation-roadmap.md` owns stage dependencies and exit criteria.
5. `NEXT_TASK.md` owns active claims, file ownership, and the dependency-ready frontier.
6. `PROJECT_BRIEF.md`, `spec.md`, `CLAUDE.md`, and undated stage prose describe scope and
   intent. Their historical test counts or progress statements do not override current
   executable evidence.

A conflict between these sources creates a reconciliation task before feature work begins.
Record the conflict and resolution in a dated journal entry. Never copy a historical test or
skip count as current evidence: record the command-specific count from the run just executed.

## Canonical Startup Read Order

A fresh coordinating agent reads these files before changing code:

1. `AGENTS.md`.
2. `PROJECT_BRIEF.md`, `spec.md`, and `CLAUDE.md`.
3. `reference/README.md`, `reference/glossary.md`, and
   `reference/claims-evidence-map.md`.
4. `reference/08-evaluation/equation-audit.md`.
5. `reference/00-roadmap/thermomap-plan-status-2026-07-14.md` and the autonomous
   implementation roadmap.
6. This runbook and `NEXT_TASK.md`.
7. `reference/research-journal/gotchas-and-todo.md` and
   `reference/research-journal/style.md`.
8. Task-specific stage notes, evaluation documents, source code, tests, and primary sources
   named by the selected task.

For evaluation or benchmark work, also read:

- `reference/08-evaluation/evaluation-framework.md`;
- `reference/08-evaluation/agentic-evaluation-research.md`;
- `reference/06-benchmarks/ground-truth-datasets.md`;
- `tools/generate_ground_truth.py`.

Read a selected instruction or source completely. A search result, PDF transcript, derivative
Markdown note, or agent summary is an index into evidence rather than authority for a formula.

## Startup Audit

Run this read-only audit before claiming a task:

```powershell
git rev-parse --short HEAD
git status --short
git diff --name-only
git diff --cached --name-only
```

Then compare `HEAD`, the working tree, the latest dated status, and `NEXT_TASK.md`.

- Preserve coworker and concurrent-agent changes.
- When a file changes unexpectedly, read it again and retry a non-destructive patch against
  the new contents.
- Never use `git reset --hard`, discard another agent's edits, or delete scratch data to make
  the tree appear clean.
- Keep generated scratch files outside commits unless the task declares them as artifacts.
- A dirty file inside another active task's ownership excludes it from the current task.

### Governance path-check scope

The `TM-GOV-001` existence check covers current control-document links, commands, and
pre-existing input/source paths required to start the first lanes. It excludes future worker
outputs that the task cards deliberately name for creation: new production modules, new test
files, artifact directories, dated journal targets, and other generated deliverables. Their
absence is expected before implementation and cannot block governance closure.

## Task Record Schema

Every executable roadmap task has one record with these fields:

| Field | Required content |
| --- | --- |
| `id` | Stable roadmap identifier, such as `TM-VERIFY-01`. |
| `gate` | Owning roadmap gate and link. |
| `state` | One allowed state from the transition list below. |
| `dependencies` | Task IDs that must be `complete`. |
| `objective` | One bounded, testable outcome. |
| `owner` | Coordinator or worker name; empty until claimed. |
| `owned_files` | Exact files or disjoint path patterns the worker may edit. |
| `shared_integration_files` | Files reserved for coordinator integration. |
| `sources` | Equation entries, primary papers, docs, and current code to read. |
| `public_tests` | Visible contract tests required for development. |
| `blind_tests` | Hidden or metamorphic behavior the design must generalize to. |
| `independent_oracle` | Checker that does not trust the implementation output. |
| `artifacts` | Raw outputs, seeds, configs, timing, and checksum locations. |
| `acceptance` | Binary exit criteria, including commands. |
| `journal` | Append-only dated evidence entry. |
| `blocker` | Concrete unmet dependency or external requirement. |
| `last_verified` | Commit, date, environment, commands, and command-specific results. |

Allowed transitions are:

```text
planned -> dependency_blocked -> ready -> claimed -> in_progress
in_progress -> review -> verified -> complete
in_progress -> blocked_external
review -> in_progress
```

Only the coordinator updates task state in `NEXT_TASK.md`. A worker reports evidence to the
coordinator and does not mark its own work `verified` or `complete`.

## Dependency-Ready Selection

The coordinator selects work using this deterministic procedure:

1. Reconcile source-of-truth conflicts.
2. Mark a task `ready` only when every dependency is `complete` and each required input exists.
3. Exclude a task whose files overlap an active owner or unexpected dirty changes.
4. Select the earliest `ready` task in roadmap dependency order.
5. Prefer parallel lanes only when their worker-owned files are disjoint. A coordinator may
   claim several such tasks concurrently; each worker owns one bounded task, and each lane
   remains serial.
6. Reserve shared exports, top-level docs, package metadata, and the live ledger for coordinator
   integration.
7. Record every claim and its exact ownership before a worker edits.

At the first post-governance frontier, worker capacity uses one fixed priority order:
`TM-VERIFY-01`, then `TM-TARGET-01`, then `GQ-INSPECT-01`. Claim the prefix whose length equals
the available worker slots: one slot claims only `TM-VERIFY-01`; two claim the first two; three
or more claim all three. If an earlier prefix task no longer satisfies `ready`, reconcile its
blocker before claiming a later task. Every worker still executes one bounded task, and each
lane remains serial.

When no task is `ready`, the coordinator audits all blockers. It proceeds on another lane when
possible. It stops only when every unfinished lane has a genuine dependency or external-access
blocker.

## Coordinator And Subagent Contract

Coding tasks use a capable lower-cost subagent with high reasoning effort. The coordinating
agent remains responsible for correctness.

### Worker responsibilities

- Read the binding docs, task sources, current implementation, and relevant tests.
- Edit only declared worker-owned files with `apply_patch`.
- Add direct public tests and independent-oracle evidence.
- Preserve raw stochastic artifacts, seeds, configs, and failures.
- Add a dated append-only journal entry with a paper hook, choices, rejected alternatives,
  sources, commands, and results.
- Return exact changed files, commands, counts, skips, failures, and unresolved risks.
- Leave commits and shared integration files to the coordinator unless explicitly assigned.

### Coordinator responsibilities

- Read the actual diff and changed source; do not accept a worker's narrative as evidence.
- Check formulas against the equation audit and primary sources.
- Inspect tests for circular assertions, fixture echoing, overfitting, and missing failure cases.
- Recompute key examples through an independent implementation or exhaustive enumeration.
- Rerun targeted and repository gates in the coordinator environment.
- Integrate public exports and shared docs only after worker-owned code passes review.
- Record negative findings and return the task to `in_progress` when review fails.

Use a second independent reviewer when a change affects energy signs, offsets, detailed
balance, stationary laws, constraint gadgets, target cost claims, or benchmark scoring.

## The Single-Task Loop

Complete one bounded task through this loop before claiming another task in the same lane.

### 1. Establish the contract

- Restate the objective, exclusions, dependencies, owned files, and exit criteria.
- Read the current files rather than relying on summaries.
- Identify the independent oracle before choosing an implementation.

### 2. Audit equations first

Any new formula, convention, tolerance, penalty, schedule rule, or cost equation updates
`reference/08-evaluation/equation-audit.md` before production code or goldens.

The canonical Ising contracts remain:

```text
E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j
P(s_i = +1 | s_-i) = sigmoid(-2 * beta * gamma_i)
```

Offsets survive every model conversion. THRML lowering uses its separately audited sign map.
Replica exchange uses EVAL-EQ-014. Diagnostics never certify optimality.

### 3. Fix evidence boundaries

Classify every external parameter or number as `measured`, `modeled`, `assumed`, or `inferred`
and record its primary URL, DOI, arXiv identifier, repository commit, or device artifact.
Unknown hardware values remain unknown. Sensitivity analysis accompanies assumed values.

### 4. Write the falsifying test and oracle

Build a test that fails for the known wrong implementation. Compute its expected result from
an independent path:

| Change type | Minimum independent check |
| --- | --- |
| QUBO/Ising conversion | Exhaustive state-energy equivalence including offsets. |
| Gibbs/transition kernel | Analytic conditional plus enumerated transition/stationary law. |
| Constraint or auxiliary lowering | Exhaustive native-objective witness and degeneracy check. |
| Quantization/non-ideality | Exact small-law comparison plus an analytic bound. |
| Placement/routing | Hand instance plus independent enumeration for small targets. |
| Diagnostics | Healthy, unhealthy, and `not_enough_data` trap fixtures. |
| Benchmark claim | Witness recomputation from the input model. |
| Performance/cost model | Dimensional checks, sensitivity cases, and measured-vs-modeled labels. |
| Serialization/evidence | JSON round trip with typed-label and delimiter collisions; compare canonical bytes across hash seeds. |
| Empirical distribution | A higher-order parity trap that matches lower-order moments but has known nonzero total variation. |
| Numeric telemetry | Finite extreme-magnitude and imbalanced-chain cases with independently scaled statistics. |
| Target admissibility | A supplied fact that contradicts the model while every unrelated target check passes. |

### 5. Implement the smallest coherent surface

Keep modules direct and small. Preserve the zero-dependency core unless the roadmap explicitly
assigns an optional adapter. Reject unsupported input explicitly. Avoid speculative wrappers,
unbounded exact algorithms, guessed target defaults, and silent fallbacks advertised as
optimal.

### 6. Run focused checks

Run the changed test module and its nearest contract tests. Record the exact command, number of
tests, skip count, duration when available, and failure output. A test not run is not evidence.

### 7. Exercise metamorphic and blind contracts

Public tests teach the contract. Design the code to survive private variants involving variable
relabeling, coefficient scaling, offset shifts, spin gauges, key reordering, hidden seeds,
diagnostic traps, and resource-accounting omissions. Hidden fixtures and seeds stay outside the
agent-visible repository and outside the package import path.

Before declaring a cross-layer audit complete, exercise the boundary-attack matrix below. These
cases are cheap and should be selected before broad exploratory reading because they target the
failure modes most likely to survive ordinary happy-path tests:

- Python equality aliases such as `True == 1` and `1 == 1.0` at typed-label boundaries;
- delimiter collisions and JSON object-key coercion such as `1` versus `"1"`;
- equal or process-specific `repr()` values and at least two `PYTHONHASHSEED` settings;
- finite values near overflow/underflow and unequal chain lengths;
- distributions with correct one- and two-variable moments but wrong higher-order support;
- omitted versus explicitly supplied target facts, especially topology capacity and accumulator
  range;
- generator output scored immediately by its independent oracle at the declared tolerance.

### 8. Preserve raw evidence

Store raw samples and full traces for stochastic claims. Record RNG identity, seeds, versions,
OS/device, input/config, compile/sample/diagnostics/tuning/wall timing, and the reproduction
command. Compute SHA-256 for every generated artifact:

```powershell
Get-FileHash -Algorithm SHA256 <artifact-path>
```

Keep failed runs, rejected parameters, and flaky results in the journal or a named raw artifact.

### 9. Audit the worker diff

The coordinator reads every changed production file and test. It searches for expected-value
leaks, calls from the implementation into the oracle, disabled assertions, stale status claims,
NaN/Inf serialization, hidden global state, nondeterministic ordering, and unbounded complexity.
The coordinator independently reproduces at least one positive case and one adversarial case.

### 10. Run integration gates

After focused review passes, run the applicable repository gates:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s test_suite/tests
python tools/check_markdown_math.py
ruff check .
ruff format --check .
mypy src/gibbsiq
git diff --check
```

Optional dependencies change skip counts. Record the environment and actual count from this
run. Do not convert one environment's skips into a project-wide status.

### 11. Journal, integrate, and commit

- Add a new dated journal entry; never rewrite historical evidence.
- Integrate public exports and shared docs after review.
- Update `NEXT_TASK.md` with the verified commit candidate and next state.
- Inspect `git diff`, `git diff --cached --stat`, and `git diff --cached`.
- Stage only task and evidence files; keep unrelated and scratch files out.
- Require `git diff --cached --check` before commit.
- Commit one coherent verified change with an informative subject.
- Re-read `git status --short` and record the commit SHA in the ledger.

Push, open a PR, deploy, or modify a remote system only when the user authorizes that action.
For an authorized server deployment, follow `AGENTS.md`: local change, GitHub push, then
`plink.exe` and `git pull` on the server.

## Public And Blind Evaluation Boundary

Every task defines visible tests and a hidden generalization contract. The hidden evaluator:

- stays outside the repository and submitted package;
- generates small private instances or uses private fixtures;
- recomputes objectives and feasibility from witnesses;
- uses metamorphic variants rather than public fixture IDs;
- rejects missing seed, version, timing, tuning, or artifact metadata;
- scores correctness and diagnostic honesty before optimization quality.

Do not add hidden expected outputs to source control. A public anti-echo test demonstrates the
interface; it does not replace evaluator isolation.

## Journal And Paper Record

Every coding or design task adds one dated entry under `reference/research-journal/`. Use the
style and skeleton in `style.md`. At minimum record:

- one-line paper hook;
- context and hard-parts analysis;
- chosen design and the rejected alternative with reasons;
- primary sources and exact local files read;
- parameters, thresholds, seeds, versions, environment, and commands;
- raw artifact paths and SHA-256 checksums;
- failures and limitations;
- command-specific test and skip counts;
- follow-up task and gate.

Technical claims then map to a test, proof/enumeration, raw artifact, or primary citation in the
claims-evidence map. Agent use is retained for the publication's AI-usage disclosure.

## Blockers And Stop Conditions

Mark `blocked_external` only when the task requires unavailable authority, data, credentials,
hardware, a private API, or an upstream state change. A hard problem, failed test, incomplete
implementation, or need for more reading remains `in_progress`.

Stop the current task and reconcile before proceeding when:

- a mathematical convention conflicts with the equation audit;
- dependencies or required artifacts are absent;
- an active agent owns an overlapping file;
- an oracle cannot be made independent of the implementation;
- a source/license boundary prevents reuse;
- the requested action would broaden authority to a remote or external system.

Unexpected local edits are handled by rereading and retrying. They do not authorize overwriting
another contributor's work.

## Physical TSU External-Access Gate

Physical calibration begins only when all of the following exist:

1. an authorized device/backend interface;
2. device identity, firmware/backend versions, and calibration procedure;
3. programmed-versus-observed coefficient and response artifacts;
4. a documented timing and energy measurement boundary;
5. permission to store and publish the resulting evidence.

Until then:

- `TSUSpec` values require provenance and unknowns remain `None`;
- simulator timing is labeled JAX/THRML simulator timing;
- paper-derived values are labeled modeled or inferred;
- ESS/joule remains a modeled sensitivity result;
- no result is described as measured TSU performance or a TSU advantage.

When M2 closes, the coordinator records `software_mvp_complete`. When every autonomous public
and simulator task through M3 closes, it records the distinct state
`simulator_research_release_complete`. Without device access, the final honest autonomous state
is M3 complete with `TM-HW-001` still `blocked_external`; project-wide calibrated physical
completion requires M4 and the external evidence above.

## Handoff Minimum

A handoff is usable only when it states:

- task ID, state, commit, and exact changed files;
- choices and rejected alternatives;
- focused and full commands with actual counts/skips;
- independent-oracle result;
- raw artifact paths, checksums, seeds, and environment;
- known failures, limitations, and blockers;
- the next dependency-ready task and its file ownership.

If any field is missing, the receiving agent treats the task as `review`, not `complete`.
