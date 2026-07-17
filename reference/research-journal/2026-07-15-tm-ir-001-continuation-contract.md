# 2026-07-15 - Thermodynamic Program Continuation Contract

## Paper Hook

This entry feeds the systems-method section on the logical program boundary and the
evaluation-method section on independently verified model projection. It records the decisions
that constrain `TM-IR-001` before its test-first implementation begins.

## Context

The repository is at commit `b22406d`. The live roadmap contains 36 bounded task cards. The
ledger records six completed cards. Thirty cards remain. `TM-HW-001` is one of the remaining
cards, and its physical calibration gate requires authorized device evidence.

`TM-IR-001` is the sole task in the `ready` state in
`reference/00-roadmap/NEXT_TASK.md`. Its dependency, `TM-VERIFY-01`, is complete at commit
`42c2409`. The task introduces an immutable, target-independent `ThermodynamicProgram` around
one audited logical model.

The goal-to-roadmap reconciliation in
`reference/research-journal/2026-07-15-goal-roadmap-and-first-frontier-integration.md` maps the
ThermoMap proposal to every roadmap capability. That audit requires no roadmap adjustment.
This continuation selects the next dependency-ready task from the existing graph.

## Hard-Parts Analysis

### H1. The program boundary must preserve logical meaning before target mapping

`Project_GOAL.md` separates the logical program from `TSUSpec`. The roadmap makes the same
separation by assigning clamping, logical coordinates, observations, and provenance to
`TM-IR-001`, while target feasibility, placement, and routing remain in later tasks.

The program envelope therefore carries logical coordinates only. Physical node identifiers,
routes, target limits, and calibrated costs remain outside this task. This boundary permits one
logical program to be validated against multiple targets without changing its objective.

### H2. Clamping is an energy-preserving projection

The canonical binary carrier evaluates
$E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j$ under `EVAL-EQ-001`. Fixing a subset of
variables produces a model over the remaining variables. Constant contributions enter the
projected offset. Incident pair terms enter the remaining linear terms. Free-free pair terms
retain their coefficients.

Independent verification requires an implementation path separate from the projection helper.
The oracle enumerates every free assignment, combines it with the clamp values, and evaluates
the original model directly. It then compares that value with the projected model energy. This
check detects dropped offsets, sign errors, omitted incident terms, and incorrect variable
ordering.

Clamping introduces a derived equation contract. The implementing agent adds the binary and
categorical projection rules to `reference/08-evaluation/equation-audit.md` before production
code. The existing `EVAL-EQ-001` convention remains binding.

### H3. Determinism requires ordered records rather than label stringification

`IsingModel` and `CategoricalModel` preserve explicit variable and domain order. Their current
serialization surfaces differ: `CategoricalModel.to_dict()` emits ordered table rows, while
`IsingModel.to_dict()` stringifies quadratic keys. The Inspector uses a separate canonical label
encoding for deterministic evidence fingerprints.

`TM-IR-001` requires deterministic relabeling and a serialized round trip. The implementing
agent must choose and document a reversible label policy, an ordered factor identity policy, and
a versioned payload shape. The chosen representation accepts only labels and metadata that it
can round-trip. Stable typed records and explicit order determine semantic identity.

### H4. Provenance must remain attached to the logical objects it explains

The envelope requires observation metadata and factor/source identities. These fields support
later import, lowering, and reporting tasks, so their association with variables and factors
must survive clamping, relabeling, and serialization.

The exact record types remain an implementation design choice because the roadmap specifies
their invariants rather than a field-level schema. The implementing agent must inspect the two
current model contracts, define the smallest coherent schema, and record rejected schema
alternatives before declaring the task complete.

### H5. Public tests and blind mutations exercise different failure modes

The public gate teaches the direct contract: immutability, clamp validation, exhaustive energy
equivalence, deterministic relabeling, deterministic serialization, round-trip recovery, and
offset preservation. The blind contract changes labels, isolates variables, clamps and unclamps
variables, shifts offsets, and applies a spin gauge.

The implementation must generalize from structural invariants. Projection tests recompute energy
equivalence instead of copying an expected serialized payload. The independent oracle follows a
separate code path from the production projection.

## Decisions

1. We select `TM-IR-001` because it is the sole dependency-ready task in the live ledger.
2. We retain the roadmap without modification because the prior goal-to-roadmap audit maps the
   complete ThermoMap proposal to explicit task cards.
3. We keep `ThermodynamicProgram` target-independent. Physical placement, routing, target
   feasibility, cost calibration, and host-transfer behavior remain assigned to later cards.
4. We preserve `IsingModel` as the canonical binary pairwise energy carrier. The program accepts
   exactly one `IsingModel` or `CategoricalModel`, and projection returns the same logical model
   type.
5. We represent a fully clamped program as the same logical model type with zero free variables
   and the complete substituted energy in its offset.
6. We interpret the blind clamp/unclamp mutation as reconstruction of a new immutable program
   with a changed clamp set. A mutating `unclamp()` method is outside the contract.
7. We require a direct-substitution enumeration oracle that shares no projection helper with
   production code. Floating energies use `rel_tol=0.0` and `abs_tol=1e-9`, matching
   `CLAUDE.md`, unless a fixture records a stricter tolerance and its sensitivity reason.
8. We require tests before production changes. The journal must retain the initial failing
   command and failure reason as red-phase evidence.
9. We require deterministic, reversible serialization. The schema must preserve variable order,
   domains, clamp roles and values, logical coordinates, observation metadata, factor identities,
   source identities, coefficients, and offsets.
10. We distinguish explicit ordered records from unordered mappings. Model variable and domain
    sequences retain their declared order, while clamp, coordinate, metadata, and provenance
    mappings normalize against that order.
11. We define a clamp conflict as two supported input records assigning different values to one
    variable. A decoder detects duplicate records before constructing a Python mapping.
12. We retain source identities when a clamped factor becomes a linear or constant contribution.
    The transformation record links each derived term to its originating factor identity.
13. We reserve shared exports, the live ledger, and final integration records for coordinator
   review. A capable lower-cost subagent implements the bounded coding lane, and the coordinator
   verifies the actual diff and reruns the gates.
14. We use current primary sources only for external API or state-of-the-art claims. Modeled
   hardware values remain classified as modeled and stay outside the logical envelope.

## Rejected Alternatives

- Skipping to `TM-IMP-001` is rejected because its JSON and NetworkX frontends depend on the
  program schema established by `TM-IR-001`.
- Embedding `TSUSpec`, physical cells, or routes in the program is rejected because those fields
  make the logical model target-dependent and pre-empt later validation and mapping tasks.
- Reusing the production projection helper inside the oracle is rejected because the comparison
  would preserve the same implementation error on both sides.
- Using `repr()` or stringified mapping keys as stable identities is rejected because distinct
  labels can collide and round trips can lose label types.
- Treating provenance as one unstructured metadata mapping is rejected because later passes
  require stable associations between source factors, logical factors, observations, and
  variables.
- Combining imports, higher-order factors, automatic mapping, or runtime schedule changes with
  this task is rejected because each capability has a separate dependency card and oracle.
- Regenerating an expected fixture silently is rejected because a changed formula first requires
  an equation-audit update and an append-only decision record.

## Sources Read And Required Reading Order

This continuation decision uses the following repository sources:

1. `AGENTS.md` for workflow, mathematical contracts, test-first execution, and recording rules.
2. `PROJECT_BRIEF.md`, `spec.md`, and `CLAUDE.md` for the product boundary, result schema, code
   conventions, and Markdown conventions.
3. `Project_GOAL.md`, especially Section 11, for the logical IR, program/target separation, and
   compiler-pass intent.
4. `reference/README.md`, `reference/glossary.md`, and `reference/claims-evidence-map.md` for the
   research-pack map and terminology.
5. `reference/08-evaluation/equation-audit.md`, especially `EVAL-EQ-001`, for the canonical
   energy and offset convention.
6. `reference/00-roadmap/thermomap-plan-status-2026-07-14.md`,
   `reference/00-roadmap/autonomous-implementation-roadmap.md`,
   `reference/00-roadmap/autonomous-agent-runbook.md`, and
   `reference/00-roadmap/NEXT_TASK.md` for status, dependency order, ownership, gates, and the
   independent oracle.
7. `reference/research-journal/gotchas-and-todo.md`,
   `reference/research-journal/style.md`, and the three 2026-07-15 first-frontier task journals
   for current corrections, writing requirements, and evidence patterns.
8. `src/gibbsiq/model.py`, `src/gibbsiq/categorical.py`, `src/gibbsiq/result.py`,
   `src/gibbsiq/_frozen.py`, `src/gibbsiq/inspector.py`, and `src/gibbsiq/__init__.py` for the
   current immutable models, serialization behavior, metadata freezing, deterministic label
   encoding, result integration, and public exports.
9. `test_suite/tests/test_model_compatibility.py`,
   `test_suite/tests/test_metamorphic_model_properties.py`,
   `test_suite/tests/test_categorical_model.py`,
   `test_suite/tests/test_categorical_result.py`,
   `test_suite/tests/test_immutability_and_provenance.py`, and
   `test_suite/tests/test_inspector.py` for the nearest executable contracts.

The implementing agent reads each selected source completely. Search results and prior agent
summaries serve as indexes rather than formula authority.

## Continuation Prompt

```text
This project is Gibbsiq, THRML-native optimization infrastructure for QUBO, Ising, and BQM
models, with ThermoMap as its compiler, mapping, verification, and thermodynamic-roofline
capability track. Your task is to execute exactly one bounded roadmap task: TM-IR-001,
Thermodynamic Program Envelope, Clamping, And Coordinates. Reference material is placed in the
repository root and under reference/, with live task state in
reference/00-roadmap/NEXT_TASK.md.

Act as the coordinating agent. Do not begin from a summary. Read the current files and inspect
the current Git state before editing:

1. Read AGENTS.md completely.
2. Read PROJECT_BRIEF.md, spec.md, and CLAUDE.md completely.
3. Read Project_GOAL.md completely, paying particular attention to Section 11 and preserving
   the document's broader mixing-aware compiler and profiler objective.
4. Read reference/README.md, reference/glossary.md, and
   reference/claims-evidence-map.md.
5. Read reference/08-evaluation/equation-audit.md before deriving any clamp projection formula.
6. Read reference/00-roadmap/thermomap-plan-status-2026-07-14.md,
   reference/00-roadmap/autonomous-implementation-roadmap.md,
   reference/00-roadmap/autonomous-agent-runbook.md, and
   reference/00-roadmap/NEXT_TASK.md. Reconfirm that TM-IR-001 remains ready and unclaimed.
7. Read reference/research-journal/gotchas-and-todo.md,
   reference/research-journal/style.md,
   reference/research-journal/2026-07-15-goal-roadmap-and-first-frontier-integration.md, and
   reference/research-journal/2026-07-15-tm-ir-001-continuation-contract.md.
8. Read src/gibbsiq/model.py, src/gibbsiq/categorical.py, src/gibbsiq/result.py,
   src/gibbsiq/_frozen.py, src/gibbsiq/inspector.py, src/gibbsiq/__init__.py, and their nearest
   tests. Inspect current serialization and arbitrary-label behavior directly.

Run the startup audit from the runbook:

git rev-parse --short HEAD
git status --short
git diff --name-only
git diff --cached --name-only

Preserve all coworker changes. When a file changes concurrently, read it again and retry a
non-destructive patch. Reconcile any conflict among the equation audit, executable code, current
tests, the roadmap, and the ledger before implementation.

Claim TM-IR-001 in NEXT_TASK.md as coordinator before delegating code. Record the exact owner,
worker-owned files, coordinator-reserved shared files, public tests, blind contract, independent
oracle, artifacts, and acceptance commands. Only the coordinator changes ledger state. If the
task is already claimed or no longer ready, stop feature edits, preserve the other claim, and
reconcile the ledger through the runbook instead of racing or stealing ownership.

Use a capable lower-cost coding subagent with high reasoning effort for the bounded
implementation. Assign exact file ownership and reserve shared exports, the ledger, and final
integration records for coordinator review. Require the worker to use apply_patch and to return
changed files, commands, counts, failures, and unresolved risks. Treat the worker's narrative as
a lead; inspect every changed source and test yourself.

Write test_suite/tests/test_thermodynamic_program.py before production code. Run it and preserve
the expected red-phase failure. The public tests must cover:

- immutable program state and defensive freezing;
- exactly one IsingModel or CategoricalModel with deterministic variable and domain order;
- deterministic free and clamped roles plus clamp values;
- optional logical coordinates, observation metadata, and factor/source identities;
- rejection of unknown, duplicate, conflicting, Boolean-alias, and out-of-domain clamp values;
- all-free, partially clamped, fully clamped, and isolated-variable cases;
- exhaustive projected-energy equivalence with the original model for every free assignment;
- projection to the same model type, including a zero-variable constant model when fully clamped;
- offset preservation and source-factor traceability through linear and constant contributions;
- deterministic relabeling without repr-based semantic identity;
- deterministic, versioned serialization and a lossless serialized round trip;
- narrow result/public-API integration required by the task card.

Build the independent oracle in test code without calling the production projection helper.
Enumerate free assignments, merge each assignment with the clamp mapping, evaluate the original
model directly, and compare with the projected model using rel_tol=0.0 and abs_tol=1e-9 unless a
fixture records a stricter tolerance and a sensitivity reason. Exercise blind-contract reasoning
through public local metamorphic cases: custom label relabeling, isolated variables,
clamp/unclamp, constant offset shifts, input mapping reordering, and spin-gauge transformation.
Interpret unclamping as construction of a new immutable program with a reduced clamp set; a
mutating unclamp API is outside this task. Do not create, reveal, or commit the evaluator's blind
fixtures or seeds.

Add the binary and categorical clamping/projection rules to
reference/08-evaluation/equation-audit.md before production code. Preserve the canonical energy
E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j, preserve offsets through projection, and
do not alter the audited Gibbs conditional sign.

Implement the smallest coherent surface. The expected primary module is
src/gibbsiq/program.py, with only narrow, justified changes to model.py, categorical.py,
result.py, and public exports. Keep IsingModel as the canonical binary pairwise carrier. Keep the
program target-independent: do not add physical placement, routing, target feasibility,
calibrated costs, import frontends, higher-order lowering, runtime schedule changes, or solver
work. Reject unsupported inputs explicitly.

The envelope accepts exactly one IsingModel or CategoricalModel, and projection returns the same
model type. A fully clamped program uses a zero-variable model with the substituted energy in its
offset. A conflict means that two supported input records assign different values to one
variable; detect duplicate serialized records before converting them to a Python mapping. Model
variable and domain sequences keep their declared order, while unordered mappings normalize
against that order. Preserve the source identity of every factor that becomes a derived linear
or constant contribution.

Before freezing the remaining schema, document the accepted and rejected choices for clamp
record shape, coordinate dimensionality, observation association, factor/source identity,
arbitrary-label serialization, schema versioning, and relabel semantics. Conduct a current-source
web audit covering official THRML program/clamping documentation and source,
official dimod variable-fixing/relabeling/serialization documentation and source, and primary
papers or source repositories for any additional state-of-the-art optimization claim. Search
broadly enough to compare viable mechanisms, then cite only sources that affect a decision or
establish a limitation. Record exact URLs or identifiers and access dates inline, classify
values as measured, modeled, assumed, or inferred, and do not import modeled hardware values
into the logical program.

Create raw deterministic serialization and projection fixtures plus a SHA-256 manifest under
reference/00-roadmap/artifacts/tm-ir-001/. Record exact generation commands, environment,
parameters, paths, and checksums. Do not silently regenerate a golden fixture.

After the worker finishes, critically audit the actual diff. Look for circular tests, dropped
offsets, mutable nested metadata, lossy labels, insertion-order leakage, factor-provenance loss,
silent clamp coercion, unsupported fully clamped models, and scope expansion. Recompute key
cases with your independent enumerator. Use a second independent reviewer because projection
changes offsets and energy terms. The reviewer must be a fresh subagent that did not implement
the task; provide the task card and actual diff without the worker's conclusions, and require an
independent projection recomputation.

Run these commands from the repository root, using the existing virtual environment:

$env:PYTHONPATH = "src"
& .venv/Scripts/python.exe -m unittest discover -s test_suite/tests -p "test_thermodynamic_program.py"
$patterns = @("test_model_compatibility.py", "test_metamorphic_model_properties.py",
"test_categorical_model.py", "test_categorical_result.py",
"test_immutability_and_provenance.py", "test_inspector.py", "test_public_api_thermomap.py")
foreach ($pattern in $patterns) {
    & .venv/Scripts/python.exe -m unittest discover -s test_suite/tests -p $pattern
}
& .venv/Scripts/python.exe -m unittest discover -s test_suite/tests
& .venv/Scripts/python.exe tools/check_markdown_math.py
& .venv/Scripts/ruff.exe check .
& .venv/Scripts/ruff.exe format --check .
& .venv/Scripts/mypy.exe src/gibbsiq
git diff --check

Record the exact command-specific test and skip counts from the commands you actually run; never
copy a historical count. A missing tool or environmental failure remains a recorded blocker
until the required gate runs successfully.

Add a new append-only dated research-journal entry using
reference/research-journal/style.md. Include a Paper Hook, H1..Hn hard-parts analysis, decisions,
rejected alternatives, sources, red-phase evidence, raw artifacts and checksums, coordinator
audit findings, exact verification commands and results, limitations, and the condition for
TM-IR-001 closure. Update the ledger through review, verified, and complete only when the
independent oracle and all acceptance gates pass. Do not claim the dependent TM-IMP-001 task in
the same lane until TM-IR-001 is complete.

Do not commit, push, deploy, or modify the server unless the invoking user explicitly authorizes
those actions. Without commit authorization, leave the task as a locally verified candidate and
do not mark it complete because the ledger requires a verified commit. If push and deployment
are authorized later, update locally, push to GitHub, then use plink.exe with the repository's
documented key to run git pull on the server.
```

## Follow-Up And Open Items

`TM-IR-001` remains unclaimed until an implementing coordinator records the claim in
`NEXT_TASK.md`. Its closing condition is the exit evidence stated in the task card: tests precede
production code, the projection rules precede code in the equation audit, projection passes the
independent enumeration oracle, serialization round-trips deterministically, raw fixtures carry
checksums, and the dated implementation journal records rejected schema alternatives.

The field-level program schema remains an open implementation decision. The implementation task
closes that design choice through executable tests, explicit failure behavior, and a separate
append-only journal record.

## Verification

The task-card counts were recomputed from the live roadmap and ledger with:

```powershell
$taskCount = (rg -o '^### [A-Z][A-Z0-9-]+[0-9]+' `
    reference/00-roadmap/autonomous-implementation-roadmap.md | Measure-Object).Count
$completeCount = (rg '^\| `[A-Z][A-Z0-9-]+` \| `complete` \|' `
    reference/00-roadmap/NEXT_TASK.md | Measure-Object).Count
$taskCount
$completeCount
$taskCount - $completeCount
```

The command returned 36 task cards, 6 completed cards, and 30 remaining cards. The startup audit
also returned commit `b22406d`. `git status --short` showed the user-supplied untracked
`Project_GOAL.md` and this new journal entry; both files remain preserved.

The first context-free reader received only this file. It reconstructed `TM-IR-001`, the required
read order, the target-independent scope, the direct-substitution oracle, and the closing gates.
It identified underspecified equation-audit timing, tolerance, categorical scope, unclamp
semantics, duplicate clamps, fully clamped output, provenance, ordering, blind fixtures,
concurrent claims, reviewer independence, acceptance commands, artifacts, and commit state. We
revised the contract to resolve each item.

A second context-free reader evaluated the revised file without editing it. Its final assessment
was `No material issues remain.`

The first Markdown command exposed a local Windows command-resolution failure:

```powershell
python tools/check_markdown_math.py
```

Windows routed `python` to the Microsoft Store application alias and returned exit code 1. The
repository virtual environment supplied Python 3.13.5. The following command returned exit code
0 with no findings:

```powershell
& .venv/Scripts/python.exe tools/check_markdown_math.py
```

`git diff --check` returned exit code 0. The journal remained untracked during this check, so a
separate trailing-whitespace scan covered the new file:

```powershell
Select-String `
    -Path reference/research-journal/2026-07-15-tm-ir-001-continuation-contract.md `
    -Pattern '[ \t]+$'
```

The scan returned zero matches. This documentation-only task changed no production code, so no
unit-test count is claimed.
