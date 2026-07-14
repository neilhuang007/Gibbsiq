# TM-GOV-001 Control-Plane Closure

Date: 2026-07-14

Paper hook: supplies the reproducible agent-orchestration and anti-ambiguity protocol for the
methods section, including a context-free reader test, deterministic work selection, and an
honest external-hardware boundary.

## Context

`TM-GOV-001` existed to turn a dated implementation audit into an executable control plane.
The verified documentation commit is `21c2a71` (`docs: add autonomous ThermoMap execution
roadmap`). It is separate from implementation checkpoint `c62169e` and defines the canonical
roadmap, agent runbook, live ledger, source precedence, bounded task contracts, public/blind
gates, independent oracles, and completion vocabulary.

This entry records the independent review and the later ledger transition from governance
review to three dependency-ready coding lanes. It does not claim that any of those three
implementations or their task-specific tests have run.

## Decisions And Rejected Alternatives

- Decision: treat `21c2a71` as the immutable identity of the verified control-plane content,
  then record the state transition in the next Git commit. Rejected: write the transition
  commit's SHA inside its own tracked content. That creates a self-referential content cycle:
  changing the file changes the commit object and therefore changes the SHA being written.
  The transition commit in Git history is itself the authoritative state-transition record.
- Decision: expose a deterministic worker-capacity prefix: one slot claims `TM-VERIFY-01`,
  two claim `TM-VERIFY-01` plus `TM-TARGET-01`, and three or more claim all three in that
  order, adding `GQ-INSPECT-01`. Rejected: let context-free workers choose among equally
  described lanes, because that makes scheduling non-reproducible and invites ownership
  collisions.
- Decision: keep each lane bounded, serial, and owned by one worker while allowing disjoint
  lanes to run concurrently. Rejected: describe the entire repository as a single active
  task, because that needlessly prevents safe parallelism.
- Decision: retain physical TSU calibration as `blocked_external`. Rejected: infer calibrated
  timing, energy, or production behavior from simulator results or public modeled numbers.
- Decision: require stable model-fingerprint encoding for Inspector association and forbid
  process-specific `repr`. Rejected: an unstable fingerprint that changes across processes
  or Python versions and cannot serve as audit evidence.

## Fresh-Reader Findings And Corrections

An independent context-free reader initially found eight control-plane ambiguities:

1. The three first lanes had no deterministic priority when worker capacity was smaller than
   three.
2. The governance requirement that every referenced path exist accidentally appeared to
   include future worker outputs.
3. The Inspector contract did not say whether model association came from a supplied model or
   a compiled manifest.
4. `SampleResult` does not contain canonical `h` and `J`, so objective recomputation is
   impossible without an independently supplied model; artifact-only row selection is the
   strongest valid no-model claim.
5. The Inspector design document described a broader interface than the bounded first task.
6. Source precedence differed between the roadmap and live ledger.
7. The active governance task lacked an explicit owner.
8. One completion label conflated the M2 software MVP with the M3 simulator research release.

The documents were corrected to add the deterministic capacity prefix; scope existence checks
to current required inputs; define `Inspector.from_result(result, *, model: IsingModel | None
= None)`; require `not_available` objective verification without a model and every-row energy
verification with one; defer compiled-manifest binding and richer HTML/CLI behavior; align
source precedence; record ownership; and separate `software_mvp_complete` from
`simulator_research_release_complete`.

The same reader then performed a post-correction regression and reported all eight issues
resolved, no new blocker, the same sole governance task before closure, and the same three
deterministic next lanes after closure.

## Independent Evidence

- Roadmap graph audit: 36 task IDs were defined once, all dependencies resolved, and the
  dependency graph was acyclic.
- Link audit: current control-document links and pre-existing required inputs resolved; paths
  explicitly named as future task outputs were excluded from the existence gate.
- Independent stable-fingerprint contract digest:
  `e851227af4a2b8a319cd7b726d929fc49fd19375973d622efe481f00ec7acd37`.
- Fresh-reader full suite:
  `python -m unittest discover -s test_suite/tests` — 457 tests, 0 reported skips, `OK`,
  135.015 seconds.
- Coordinator focused correctness suite:
  `python -m unittest test_suite.tests.test_public_api_thermomap
  test_suite.tests.test_runtime_correctness_contracts` — 20 tests, `OK`, 54.527 seconds.
- `python tools/check_markdown_math.py` — passed.
- `ruff check .` — passed.
- `ruff format --check .` — passed.
- `mypy src/gibbsiq` — passed.
- `git diff --check` — passed.
- Scoped Markdown link scan — passed after correction.

The coordinator's first PowerShell link-scan scout failed because it treated a root-level
Markdown file as though it had a non-empty parent path. The scanner was corrected to use `.`
for an empty parent; the corrected current-input link scan passed. The failed scout is kept
here because suppressing it would hide a reproducibility trap in the verification method.
The first ledger state-assertion scout also stopped at PowerShell parse time because a colon
immediately followed an unbraced variable name. Bracing that variable fixed the checker; the
corrected run found three ready table rows, gates, unclaimed owners, and no-blocker cards,
nine checked and zero unchecked governance items, and zero `dependency_blocked` tokens.

The verified control-plane documentation commit is `21c2a71`. The state-transition commit
cannot embed its own SHA for the content-cycle reason above; its Git commit identity records
the transition.

## Result And Remaining Boundary

`TM-GOV-001` is complete. The deterministic dependency-ready prefix is now:

1. `TM-VERIFY-01` — independent CPU Gibbs and exact-kernel verifier;
2. `TM-TARGET-01` — complete provenanced target specification;
3. `GQ-INSPECT-01` — artifact-only Inspector core.

Each task remains unclaimed and has no task-specific implementation evidence yet. Physical
TSU calibration remains `blocked_external` until an authorized device/backend, identities and
versions, calibration artifacts, timing/energy boundaries, and publication permission exist.
The honest autonomous terminal state without that external change is the M3 simulator
research release, not calibrated physical completion.
