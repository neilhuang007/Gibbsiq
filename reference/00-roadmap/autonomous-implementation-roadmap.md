# Autonomous ThermoMap Implementation Roadmap

## Purpose And Evidence Snapshot

This document is the canonical implementation dependency graph for completing the software
roadmap described in the ThermoMap proposal. It converts the proposal into bounded work
packages that an agent can select, implement, verify, journal, and hand off without inventing
missing hardware facts.

The initial evidence snapshot is commit `c62169e` on 2026-07-14. At that snapshot, the
verified current-tree score is 8/20 = 40% under the equal-row audit in
[`thermomap-plan-status-2026-07-14.md`](thermomap-plan-status-2026-07-14.md). The percentage is
a capability count. It is not an effort estimate. Apply the precedence below rather than
letting older progress prose override current executable evidence.

The public backend is the THRML JAX simulator. Physical TSU calibration is an external gate.
An agent may complete the simulator-backed software release without device access. It may not
claim measured TSU latency, energy, accuracy, or advantage until `TM-HW-001` closes with a
device artifact.

## Companion Control Files

- [`README.md`](README.md) is the roadmap index and current high-level status.
- [`NEXT_TASK.md`](NEXT_TASK.md) is the mutable state ledger. It names the current coordinator
  task plus zero or more explicitly `ready` or `claimed` parallel lanes, their owners,
  dependencies, evidence snapshots, and last verified commands. Each worker claims exactly one
  bounded task.
- [`autonomous-agent-runbook.md`](autonomous-agent-runbook.md) defines task selection,
  research, implementation, verification, journaling, commit, and handoff procedure.
- This document owns stable task IDs, dependencies, deliverables, and gates. Task definitions
  change only through a dated decision journal.

If a companion control file is absent, `TM-GOV-001` is the first ready task. An agent must not
infer task state from chat history.

## Source-Of-Truth Precedence

Different files own different kinds of truth. Apply this order before selecting or closing a
task:

1. `AGENTS.md` and higher-level instructions own workflow and non-negotiable behavior.
2. [`../08-evaluation/equation-audit.md`](../08-evaluation/equation-audit.md) owns mathematical
   conventions.
3. Executable source, tests actually run at the current `HEAD`, and the latest dated
   verification/status record own implementation status.
4. This autonomous roadmap owns task dependencies and exit criteria.
5. [`NEXT_TASK.md`](NEXT_TASK.md) owns active claims, file ownership, and the dependency-ready
   frontier, constrained by this roadmap.
6. `PROJECT_BRIEF.md`, `spec.md`, `CLAUDE.md`, dated journals, legacy stage prose, and other
   scope/history documents provide context but do not override the authorities above.

A conflict creates a reconciliation task before feature work. Record its resolution in a
dated journal; chat history is not evidence.

## Status Vocabulary

| Status | Meaning |
| --- | --- |
| `complete` | Every named public gate passed, independent evidence exists, raw artifacts and provenance are recorded, and the matching journal names the commit. |
| `verified` | The coordinator independently reran the acceptance checks and reviewed the actual diff; the final state/commit update remains. |
| `review` | The worker reported implementation evidence and released the files for coordinator audit. |
| `in_progress` | One owner is actively changing the task's declared files. A second agent may audit read-only and may not edit those files. |
| `claimed` | The coordinator assigned an owner and exact files; implementation has not started. |
| `ready` | Every dependency is `complete`, no owner holds the files, and required external inputs are present. |
| `dependency_blocked` | At least one internal dependency remains open; the ledger names it. |
| `planned` | The task is outside the current dependency-ready frontier; its re-entry condition remains recorded. |
| `blocked_external` | Progress requires unavailable device access, credentials, an upstream API, a license decision, or another external state change. |

Allowed transitions match the runbook exactly:

```text
planned -> dependency_blocked -> ready -> claimed -> in_progress
in_progress -> review -> verified -> complete
in_progress -> blocked_external
review -> in_progress
```

A task never becomes `complete` from code review alone. It requires its public tests, an
independent oracle or metamorphic check, the repository checks appropriate to its risk, and a
dated journal entry. Blind tests remain outside the agent-visible repository.

## Release Milestones

| Milestone | Required task closure | Result |
| --- | --- | --- |
| M0 — verified foundation | `TM-FND-001`, `TM-FND-002` | Audited Ising/THRML/diagnostic substrate and partial target-analysis foundation at `c62169e`. |
| M1 — compiler kernel | `TM-GOV-001`, `TM-IR-001`, `TM-IMP-001`, `TM-VAL-001`, `TM-VERIFY-01`, `TM-TARGET-01`, `TM-LWR-001`, `TM-LWR-002`, `TM-COL-001`, `TM-MAP-001`, `TM-MAP-002`, `TM-MAP-003`, `TM-API-001` | One-call compilation from supported logical inputs to an audited, target-constrained simulator artifact. |
| M2 — software MVP | M1 plus `GQ-INSPECT-01`, `TM-CAT-001`, `TM-NID-001`, `TM-NID-002`, `TM-COST-001`, `TM-PROF-001`, `TM-BASE-001`, `TM-BASE-002`, `TM-BENCH-001` through `TM-BENCH-004`, `TM-REP-001`, `TM-REL-001` | `software_mvp_complete`: compile/profile/verify workflow, three benchmark domains, matched baselines, Inspector, and a quality-adjusted thermodynamic roofline using explicitly modeled assumptions. |
| M3 — full simulator-backed research release | M2 plus `TM-IMP-002`, `TM-HYB-001`, `TM-BENCH-005`, `TM-REP-002`, `TM-PAPER-001`, `TM-RFC-001` | `simulator_research_release_complete`: complete proposal coverage on public simulators, including hybrid partitioning, hybrid AI demonstration, notebooks, report, paper artifacts, and an upstream-ready RFC. |
| M4 — calibrated physical release | M3 plus `TM-HW-001` | Device-calibrated backend and matched TSU-versus-host evidence. This milestone is externally blocked at the initial snapshot. |

The honest autonomous terminal without hardware access is M3
`simulator_research_release_complete` with `TM-HW-001` remaining `blocked_external`. M4 has no
autonomous completion label and may close only after its physical calibration evidence gate.

## Dependency Graph

```text
TM-GOV-001 + TM-FND-001 -> TM-VERIFY-01, GQ-INSPECT-01
TM-GOV-001 + TM-FND-002 -> TM-TARGET-01
TM-VERIFY-01 -> TM-IR-001
TM-IR-001 -> TM-IMP-001
TM-IR-001 + TM-VERIFY-01 -> TM-LWR-001
TM-IR-001 + TM-VERIFY-01 + TM-TARGET-01 -> TM-CAT-001
TM-IR-001 + TM-TARGET-01 -> TM-IMP-002, TM-VAL-001
TM-TARGET-01 + TM-VAL-001 + TM-VERIFY-01 -> TM-COL-001
TM-LWR-001 + TM-TARGET-01 + TM-VERIFY-01 -> TM-LWR-002
TM-TARGET-01 + TM-LWR-002 + TM-COL-001 -> TM-MAP-001
TM-MAP-001 + TM-TARGET-01 -> TM-MAP-002
TM-MAP-002 + TM-LWR-002 + TM-TARGET-01 -> TM-MAP-003
TM-IMP-001 + TM-VAL-001 + TM-LWR-002 + TM-COL-001 + TM-MAP-003 -> TM-API-001
TM-TARGET-01 + TM-VERIFY-01 -> TM-NID-001
TM-NID-001 + TM-MAP-003 + TM-VERIFY-01 -> TM-NID-002
TM-TARGET-01 + TM-COL-001 + TM-MAP-003 -> TM-COST-001
TM-API-001 + TM-VERIFY-01 + TM-COST-001 + TM-NID-002 -> TM-PROF-001
TM-API-001 + TM-COST-001 + TM-PROF-001 -> TM-HYB-001
TM-API-001 -> TM-BASE-001 -> TM-BASE-002
TM-BASE-001 + TM-BASE-002 + TM-PROF-001 -> TM-BENCH-001
TM-BENCH-001 + TM-NID-002 + TM-CAT-001 -> TM-BENCH-002
TM-BENCH-001 + TM-IR-001 + TM-VERIFY-01 -> TM-BENCH-003
TM-BENCH-001 + TM-LWR-001 + TM-CAT-001 -> TM-BENCH-004
TM-HYB-001 + TM-BENCH-001 + TM-CAT-001 -> TM-BENCH-005
GQ-INSPECT-01 + TM-API-001 + TM-PROF-001 + TM-BENCH-001 -> TM-REP-001
all other M2 gates, including TM-REP-001 -> TM-REL-001
TM-REL-001 + TM-IMP-002 + TM-HYB-001 + TM-BENCH-005 -> TM-REP-002
TM-REP-002 -> TM-PAPER-001, TM-RFC-001
TM-REL-001 + authorized device access -> TM-HW-001
```

The graph states logical prerequisites. `TM-VERIFY-01`, `TM-TARGET-01`, and
`GQ-INSPECT-01` can run concurrently because they own separate modules. If capacity is below
three workers, claim the deterministic prefix of that order: one slot gets `TM-VERIFY-01`, two
slots get `TM-VERIFY-01` and `TM-TARGET-01`. Skip an earlier lane only for a recorded ownership,
input, or external blocker. The mapping chain is intentionally ordered: partition, placement,
and routing share compiled-artifact schemas and must not be implemented concurrently until the
preceding schema is frozen.

## Verified Foundation

### TM-FND-001 — Canonical Model, Runtime, Diagnostics, And Oracle

- **Initial status:** `complete` at `c62169e`.
- **Evidence:** `model.py`, `conversions.py`, `result.py`, `blocks.py`,
  `thrml_runtime.py`, `diagnostics.py`, `benchmark_oracle.py`, and
  `benchmark_bridge.py`; the final integration journal records 457 passing tests.
- **Contract:** preserve the canonical energy and offset, use the audited Gibbs sign, retain
  raw samples/traces, and recompute every benchmark witness.
- **Residual work:** bulk/tail ESS, feasibility, Inspector, and baseline runners belong to
  later task IDs. The private runtime class `_Lowering` is an implementation detail; no public
  `THRMLProgramBundle` exists at this snapshot.

### TM-FND-002 — Target-Analysis And Finite-State Foundation

- **Initial status:** `complete` for the named bounded surface at `c62169e`.
- **Evidence:** `hardware.py`, `hardware_assessment.py`, `quantization.py`,
  `exact_distribution.py`, `communication_profile.py`, `categorical.py`, `domain_wall.py`,
  and `cluster_moves.py`, with direct tests and independent audits recorded in
  `2026-07-14-thermomap-final-integration-verification.md`.
- **Contract:** the implemented `TSUSpec` contains provenanced logical facts and a coefficient
  format. It does not contain a physical topology, host/reprogram costs, or a calibrated
  end-to-end hardware model. Supplied-partition communication values remain algebraic proxies.

## Work Packages

### TM-GOV-001 — Autonomous Control Plane

- **Initial status:** `review` during the coordinated documentation pass. If a companion file
  is absent in a later checkout, return this task to `in_progress` and restore it.
- **Dependencies:** none.
- **Suggested ownership:** `reference/00-roadmap/autonomous-agent-runbook.md`,
  `reference/00-roadmap/NEXT_TASK.md`, and links from agent guidance; no production code.
- **Deliverable:** a deterministic task-selection loop, exclusive file ownership, evidence
  fields, stop conditions, handoff template, the active governance review, and the three
  dependency-blocked first lanes that become `ready` after closure.
- **Public gate:** the current control files, canonical startup inputs, and task-specific source
  inputs required to select the first bounded task all resolve; the commands that the runbook
  requires at governance time execute; Markdown math and links among those current inputs pass.
  Planned output modules, tests, report assets, and commands named only as downstream task
  contracts are explicitly excluded until their owning task begins.
- **Blind/metamorphic gate:** a context-free reader identifies `TM-GOV-001` as the active
  review and the same three next-to-ready lanes, then selects the same first `ready` task after
  the coordinator closes governance.
- **Exit evidence:** a dated journal and reader-test record. Chat messages are not evidence.

### TM-IR-001 — Thermodynamic Program Envelope, Clamping, And Coordinates

- **Initial status:** `dependency_blocked`; `IsingModel` and `CategoricalModel` exist, while clamping,
  observation roles, coordinates, and general factor provenance are absent.
- **Dependencies:** `TM-VERIFY-01`.
- **Suggested ownership:** new `src/gibbsiq/program.py`; narrow changes to `model.py`,
  `categorical.py`, `result.py`, and public exports; `test_thermodynamic_program.py`.
- **Deliverable:** an immutable `ThermodynamicProgram` envelope containing one audited logical
  model, deterministic free/clamped roles, clamp values, optional logical coordinates,
  observation metadata, and factor/source identities. `IsingModel` remains the canonical
  binary pairwise energy carrier. The envelope is target-independent; target feasibility is a
  later validation and mapping concern.
- **Public gate:** exhaustive energy equivalence after clamping; conflicting or out-of-domain
  clamps fail; relabeling and serialization are deterministic; offsets survive projection.
- **Blind/metamorphic gate:** hidden relabel, isolated-variable, clamp/unclamp, offset-shift,
  and spin-gauge mutations.
- **Independent oracle:** enumerate free variables and compare every projected energy against
  direct substitution into the original model.
- **Exit evidence:** equation-audit entry before any new formula, public tests, serialized
  round trip, and a journal with rejected schema alternatives.

### TM-IMP-001 — Factor-JSON And NetworkX Frontends

- **Initial status:** `dependency_blocked`; QUBO/Ising/BQM frontends exist.
- **Dependencies:** `TM-IR-001`.
- **Suggested ownership:** `src/gibbsiq/importers.py`, JSON schema under
  `reference/02-interfaces/`, and `test_importers.py`. NetworkX remains an optional extra.
- **Deliverable:** versioned pairwise factor-graph JSON import/export and NetworkX graph import
  with explicit coefficient, vartype, offset, node-order, clamp, and coordinate policies.
- **Public gate:** round trips preserve all enumerated energies and metadata; malformed,
  duplicate, asymmetric, and unsupported factors fail explicitly.
- **Blind/metamorphic gate:** shuffled JSON keys, custom hashable labels, reversed edge order,
  disconnected nodes, and equivalent symmetric QUBO normalization.
- **Independent oracle:** compare imported energies against direct evaluation of the source
  JSON/graph without calling Gibbsiq conversion helpers.
- **Exit evidence:** schema version, optional-dependency behavior, provenance, and fixture
  checksums recorded.

### TM-IMP-002 — Existing-THRML Program Importer

- **Initial status:** `dependency_blocked`; Gibbsiq lowers to THRML and does not ingest an existing THRML
  program.
- **Dependencies:** `TM-IR-001`, `TM-TARGET-01`.
- **Suggested ownership:** `src/gibbsiq/thrml_import.py` and version-pinned optional tests.
- **Deliverable:** import the documented binary pairwise subset of THRML into the program
  envelope, preserving clamps, node order, factors, and schedule metadata. Unsupported node or
  factor types return a structured refusal.
- **Public gate:** version-pinned documented THRML examples round-trip through the canonical
  energy convention and reproduce conditional probabilities.
- **Blind/metamorphic gate:** hidden node reordering, edgeless programs, negative fields,
  clamps, and unsupported-factor refusal.
- **Independent oracle:** evaluate the source THRML energy/conditional directly and compare
  against exact enumeration under Gibbsiq's sign mapping.
- **Exit evidence:** tested THRML version and API paths recorded; no claim of compatibility
  with untested versions.

### TM-VAL-001 — Whole-Program Validation And Structured Compile Failure

- **Initial status:** `dependency_blocked`; model, schedule, coefficient, and direct logical target checks
  exist separately.
- **Dependencies:** `TM-IR-001`, `TM-TARGET-01`.
- **Suggested ownership:** `src/gibbsiq/validation.py` plus narrow composition with
  `hardware_assessment.py`; `test_program_validation.py`.
- **Deliverable:** one validation report covering model consistency, clamp conflicts,
  supported factor arity, capacity, effective degree, precision, schedule coverage, topology
  prerequisites, and explicit `pass`/`fail`/`not_evaluated` evidence.
- **Public gate:** each failure has a stable code, source path, and remediation; unknown
  topology remains `not_evaluated` rather than passing.
- **Blind/metamorphic gate:** coefficient-scale boundaries, beta zero versus positive-beta
  schedules, empty/free-only/clamped-only models, and impossible target limits.
- **Independent oracle:** direct graph and coefficient calculations that do not consume the
  report's derived values.
- **Exit evidence:** no unsupported model reaches a lowering pass silently.

### TM-VERIFY-01 — Independent CPU Gibbs And Exact Kernel Verifier

- **Initial status:** `dependency_blocked` until `TM-GOV-001` closes, then first-lane `ready`; analytic
  conditionals and THRML empirical tests exist, while no reusable independent CPU sampler is
  exported.
- **Dependencies:** `TM-FND-001`, `TM-GOV-001`.
- **Suggested ownership:** `src/gibbsiq/reference_sampler.py`,
  `src/gibbsiq/verification.py`, equation-audit additions,
  `test_reference_sampler.py`, and `test_statistical_verifier.py`; neither production module
  may call THRML or `thrml_runtime.py`.
- **Deliverable:** seeded single-site and legal blocked Gibbs for canonical Ising models;
  warmup/retention and work accounting; capped exact transition matrices; stationary-law and
  detailed-balance residuals where reversibility is expected; empirical marginal,
  correlation, and energy intervals; and explicit non-reversible schedule semantics.
- **Public gate:** one- and two-spin conditionals match analytic values; tiny empirical laws
  fall inside predeclared simultaneous intervals; repeated seeds reproduce exact traces;
  hand-derived kernels, intentionally wrong-sign kernels, non-ergodic kernels, and valid
  systematic/block schedules produce the expected verification result.
- **Blind/metamorphic gate:** gauge, relabel, offset, beta-zero, isolated-variable, private
  small-graph, permutation-similar transition-matrix, delayed-kernel, and subtly
  non-stochastic-row mutations with private seeds.
- **Independent oracle:** `exact_distribution.py`, direct conditional tables, direct linear
  stationarity equations, and row-sum checks implemented outside the sampler path; interval
  coverage is checked over repeated seeded experiments rather than only against THRML.
- **Exit evidence:** RNG identity, seed, interval method, work units, state cap, numerical
  tolerance, sensitivity results, and raw traces recorded.

### TM-TARGET-01 — Complete Provenanced Target Specification

- **Initial status:** `dependency_blocked` until `TM-GOV-001` closes, then first-lane `ready`; the current
  `TSUSpec` is partial.
- **Dependencies:** `TM-FND-002`, `TM-GOV-001`.
- **Suggested ownership:** `src/gibbsiq/hardware.py`, new `src/gibbsiq/topology.py`, and
  `test_target_spec.py`.
- **Deliverable:** immutable topology kind, tile/shape, allowed neighbor offsets or explicit
  graph, physical degree, capacity, coefficient and accumulator formats, color/update facts,
  communication model, host transfer, programming/reprogramming, and per-field provenance
  with uncertainty or sensitivity range.
- **Public gate:** serialization is finite and deterministic; inconsistent shapes/offsets,
  unsupported provenance, nonphysical times/energies, and incomplete cost facts fail or remain
  explicitly unknown.
- **Blind/metamorphic gate:** reflected/translated grids, reordered explicit topologies,
  omitted optional facts, unit-scale mutations, and unknown-value propagation.
- **Independent oracle:** enumerate small topology adjacency and recompute capacity, degree,
  distance, and allowed-edge facts independently.
- **Exit evidence:** no Z1 value is hard-coded as measured. Every external number carries a
  primary URL/DOI, access date, source class, and sensitivity range.

### TM-LWR-001 — Higher-Order And Constraint Lowering

- **Initial status:** `dependency_blocked`; pairwise categorical domain-wall lowering exists, while
  higher-order quadratization and native constrained encodings are absent.
- **Dependencies:** `TM-IR-001`, `TM-VERIFY-01`.
- **Suggested ownership:** `src/gibbsiq/factor_lowering.py`,
  `src/gibbsiq/constraints.py`, decoders, equation-audit entries, and focused tests.
- **Deliverable:** a bounded catalog of binary higher-order reductions plus one-hot/penalty
  encodings required by the current knapsack and TSP fixtures. Every transform returns
  ancillas, penalty policy, decoder, source-to-lowered objective map, and overhead report.
- **Public gate:** exhaustive minimization over ancillas recovers every source-state energy or
  the documented affine relation; decoded witnesses preserve feasibility and native
  objective; inadequate penalties are detected.
- **Blind/metamorphic gate:** coefficient scaling, redundant constraints, variable relabeling,
  offset shifts, alternative feasible witnesses, and penalties immediately below/above the
  proved boundary.
- **Independent oracle:** native problem evaluator and exhaustive source/ancilla enumeration,
  never the lowered solver's reported energy.
- **Exit evidence:** each formula enters `equation-audit.md` first; no universal penalty is
  asserted without proof.

### TM-LWR-002 — Degree Reduction And Equality Gadgets

- **Initial status:** `dependency_blocked`; logical degree is measured but never transformed.
- **Dependencies:** `TM-LWR-001`, `TM-TARGET-01`, `TM-VERIFY-01`.
- **Suggested ownership:** `src/gibbsiq/degree_reduction.py`, decoder and overhead schemas,
  `test_degree_reduction.py`.
- **Deliverable:** replicated-variable/equality-gadget transforms for declared degree limits,
  deterministic reconstruction, penalty selection or required user policy, and reports for
  auxiliary nodes, coefficient range, color count, and projected-law error.
- **Public gate:** exhaustive small graphs recover the original ground states and objective;
  projected exact distributions quantify finite-penalty distortion; impossible precision
  returns a structured compile failure.
- **Blind/metamorphic gate:** stars, cliques, asymmetric fields, scale/offset/gauge mutations,
  and adversarial label order.
- **Independent oracle:** minimize over replicas/ancillas for every original state and compare
  against direct source energy; verify decoded witnesses independently.
- **Exit evidence:** equality penalties are recorded as a mixing risk, never as distribution-
  preserving at finite strength without the measured bound.

### TM-CAT-001 — Categorical Conditional And THRML Execution

- **Initial status:** `dependency_blocked`; categorical IR and domain-wall compilation are complete,
  execution is absent.
- **Dependencies:** `TM-IR-001`, `TM-VERIFY-01`, `TM-TARGET-01`.
- **Suggested ownership:** `src/gibbsiq/categorical_runtime.py` and focused exact-law tests;
  reuse `domain_wall.py` without changing its audited valid-state identity.
- **Deliverable:** exact categorical conditional, direct or domain-wall THRML execution,
  explicit invalid-wall policy, user/derived penalty provenance, decoded categorical traces,
  and sampling-overhead metadata.
- **Public gate:** empirical probabilities on tiny unary/pairwise models match exact categorical
  laws; category-order and penalty sweeps expose invalid-state mass and mixing effects.
- **Blind/metamorphic gate:** domain reorder with table permutation, singleton domains,
  transposed pair tables, and penalties across the adequacy boundary.
- **Independent oracle:** enumerate categorical states directly, without passing through the
  domain-wall encoding.
- **Exit evidence:** energy equivalence and empirical sampling quality are reported separately.

### TM-COL-001 — Coloring And Schedule Candidate Search

- **Initial status:** `dependency_blocked`; deterministic legal DSATUR blocks exist.
- **Dependencies:** `TM-TARGET-01`, `TM-VAL-001`, `TM-VERIFY-01`.
- **Suggested ownership:** extend `blocks.py` through small strategy objects or a new
  `schedule_search.py`; `test_schedule_candidates.py`.
- **Deliverable:** deterministic bipartite, DSATUR, largest-first, smallest-last, and
  target-aware schedule candidates; legal-block proof; color, balance, communication, work,
  and measured mixing summaries. Optional upstream libraries remain comparison oracles.
- **Public gate:** every candidate is legal; known graph families pin color bounds; identical
  seeds and labels yield stable schedules; selection reports the full candidate set.
- **Blind/metamorphic gate:** hidden graph isomorphisms, disconnected components, dense/sparse
  extremes, beta-zero effective graphs, and label-order mutations.
- **Independent oracle:** exact chromatic enumeration for small graphs and direct edge scans for
  legality. A heuristic color count is never called the chromatic number.
- **Exit evidence:** schedule selection may optimize measured ESS only on a training split;
  held-out graphs evaluate generalization.

### TM-MAP-001 — Deterministic Graph Partitioning

- **Initial status:** `dependency_blocked`; the current communication profiler accepts caller-supplied
  partitions and the Potts function only scores a supplied assignment.
- **Dependencies:** `TM-TARGET-01`, `TM-LWR-002`, `TM-COL-001`.
- **Suggested ownership:** `src/gibbsiq/partitioning.py` and `test_partitioning.py`; optional
  METIS/KaHIP adapters remain extras with recorded versions and licenses.
- **Deliverable:** zero-dependency deterministic partition baselines, balance/cut/locality
  objectives, multiple candidates, and a stable partition artifact consumed by
  `communication_profile.py`.
- **Public gate:** hand graphs have expected cut/balance values; candidate scoring is recomputed;
  sparse 100,000-variable compile benchmark records time, memory, input checksum, and hardware.
- **Blind/metamorphic gate:** graph relabel, disconnected components, skewed weights,
  adversarial hubs, and partition-count sensitivity.
- **Independent oracle:** exact partition enumeration on small graphs and direct recomputation
  of every objective term; external partitioners are comparators, not ground truth.
- **Exit evidence:** quality, compile time, and stochastic impact are reported separately.

### TM-MAP-002 — Topology-Constrained Placement

- **Initial status:** `dependency_blocked`; exact small chain-order search maps partitions to chain slots
  only.
- **Dependencies:** `TM-MAP-001`, `TM-TARGET-01`.
- **Suggested ownership:** `src/gibbsiq/placement.py`, immutable placement artifact, and
  `test_placement.py`.
- **Deliverable:** deterministic grid/explicit-topology placement baselines, capacity and fixed
  cell constraints, multiple starts with recorded seeds, and objectives for edge distance,
  congestion proxy, and color locality.
- **Public gate:** exhaustive tiny placements match the optimum; translations/reflections have
  canonical tie-breaking; infeasible capacity returns a structured failure.
- **Blind/metamorphic gate:** topology automorphisms, variable relabeling, fixed coordinates,
  high-degree hubs, and near-capacity cases.
- **Independent oracle:** enumerate all tiny placements and directly recompute distances from
  the target adjacency; do not trust placer scores.
- **Exit evidence:** supplied-partition chain mapping is labeled as one placement strategy, not
  general routing.

### TM-MAP-003 — Routing, Auxiliary Paths, And Congestion

- **Initial status:** `dependency_blocked`; no general router or route-auxiliary insertion exists.
- **Dependencies:** `TM-MAP-002`, `TM-LWR-002`, `TM-TARGET-01`.
- **Suggested ownership:** `src/gibbsiq/routing.py`, route artifact and decoder, and
  `test_routing.py`.
- **Deliverable:** route logical couplings on declared topologies, insert only audited
  auxiliary/equality paths, report path length, link demand, congestion, colors, coefficient
  range, and rejected edges, and preserve host-to-logical witness decoding.
- **Public gate:** exact small topologies prove path feasibility and objective reconstruction;
  shared-link counterexamples reproduce aggregate demand; no-route cases fail explicitly.
- **Blind/metamorphic gate:** reflected grids, bottleneck cuts, simultaneous routes, pin/edge
  capacity changes, and reordered labels.
- **Independent oracle:** direct graph path validation and exhaustive original-versus-routed
  minimization on small cases; communication metrics are recomputed outside the router.
- **Exit evidence:** algebraic proxies remain distinguished from a feasible time schedule.

### TM-API-001 — Compiled Artifact And One-Call Compiler API

- **Initial status:** `dependency_blocked`; public analysis functions exist separately and `_Lowering` is
  private.
- **Dependencies:** `TM-IMP-001`, `TM-VAL-001`, `TM-LWR-002`, `TM-COL-001`,
  `TM-MAP-003`.
- **Suggested ownership:** `src/gibbsiq/compiler.py`, public exports, schema fixtures, and
  `test_compile_model.py`.
- **Deliverable:** `compile_model(...)` returns an immutable compiled artifact containing the
  original program, all transforms and decoders, target snapshot, blocks, placement, routes,
  quantization, warnings, rejected candidates, checksums, and a THRML-executable model when
  supported.
- **Public gate:** QUBO/Ising/factor-JSON compile in one call; every pass can be replayed from
  the manifest; an unsupported target returns structured evidence rather than a partial
  executable.
- **Blind/metamorphic gate:** pass-order replay, label/gauge/offset mutations, corrupted
  manifests, omitted provenance, and equivalent target topology orderings.
- **Independent oracle:** replay source and compiled energies/witnesses through separate
  evaluators; hash every artifact.
- **Exit evidence:** the public type is named and documented. Do not refer to a nonexistent
  `THRMLProgramBundle` unless this task deliberately creates and tests that exact API.

### TM-NID-001 — Static Non-Ideality Injection

- **Initial status:** `dependency_blocked`; stored-coefficient quantization exists.
- **Dependencies:** `TM-TARGET-01`, `TM-VERIFY-01`.
- **Suggested ownership:** `src/gibbsiq/nonidealities.py` and
  `test_nonidealities_static.py`.
- **Deliverable:** seeded bias/coupling mismatch, accumulator quantization, sigmoid response
  distortion, process variation, and drift trajectories, with per-parameter provenance and
  composition order.
- **Public gate:** zero perturbation is identity; seeded perturbations reproduce; exact small
  laws or transition kernels quantify target error; nonfinite and unproven parameter ranges
  fail.
- **Blind/metamorphic gate:** sign-symmetric perturbations, coefficient scaling, zero-beta,
  composition reorder traps, and drift reversal.
- **Independent oracle:** direct perturbed energies/conditionals and exact transition analysis,
  separate from the injector's summaries.
- **Exit evidence:** synthetic, paper-derived, assumed, and measured parameters remain distinct.

### TM-NID-002 — Delayed, Dropped, And Stale Boundary Dynamics

- **Initial status:** `dependency_blocked`; communication equations do not simulate stale-state dynamics.
- **Dependencies:** `TM-NID-001`, `TM-MAP-003`, `TM-VERIFY-01`.
- **Suggested ownership:** `src/gibbsiq/distributed_dynamics.py` and exact/empirical tests.
- **Deliverable:** explicit boundary-exchange cadence, delay, drop, timing-skew, and update-order
  models on a mapped program; raw communication events and effective transition semantics.
- **Public gate:** zero delay matches the reference kernel; tiny delayed systems expose
  stationary-law error; exchange-frequency sweeps retain raw traces and intervals.
- **Blind/metamorphic gate:** asynchronous order changes, asymmetric directed boundaries,
  disconnected partitions, deterministic drop patterns, and hidden seeds.
- **Independent oracle:** construct the augmented finite-state transition matrix for tiny
  systems including stale buffers.
- **Exit evidence:** throughput/accuracy observations are workload-specific. Aadit et al.
  motivate the sweep and do not provide a universal TSU parameter.

### TM-COST-001 — Provenanced End-To-End Cost Model

- **Initial status:** `dependency_blocked`; cell facts and communication proxies exist separately.
- **Dependencies:** `TM-TARGET-01`, `TM-COL-001`, `TM-MAP-003`.
- **Suggested ownership:** `src/gibbsiq/cost_model.py`, provenance schema, sensitivity tests.
- **Deliverable:** separate compile, host transfer, program/reprogram, color-phase update,
  local cell, route communication, sample return, and diagnostics time/energy terms. Every
  result carries measured/paper-derived/assumed/simulated provenance and uncertainty range.
- **Public gate:** dimensional/unit checks, zero-traffic and zero-reprogram limits, hand totals,
  sensitivity monotonicity, and unknown propagation pass.
- **Blind/metamorphic gate:** unit rescaling, missing terms, dominant-term swaps, sparse/dense
  mappings, and host-amortization boundaries.
- **Independent oracle:** recompute hand fixtures term by term without the model's aggregation
  function; compare simulator wall time only in a separately labeled field.
- **Exit evidence:** modeled quantities never inherit the label `measured`; communication
  proxies are not silently promoted to latency bounds.

### TM-PROF-001 — Mixing-Aware Thermodynamic Roofline

- **Initial status:** `dependency_blocked`; logical work, simulator timing, scalar ESS, and algebraic cost
  inputs exist but are not unified.
- **Dependencies:** `TM-API-001`, `TM-VERIFY-01`, `TM-COST-001`, `TM-NID-002`.
- **Suggested ownership:** `src/gibbsiq/profiler.py`, a small
  `src/gibbsiq/efficiency.py` if estimator isolation is needed, profile schema, new equation-
  audit entries, `test_bulk_tail_ess.py`, and `test_thermodynamic_roofline.py`.
- **Deliverable:** `profile(...)` reports raw sweeps/second, autocorrelation, time to
  equilibrium, quality/error, sensitivity intervals, and circuit/color/communication/mixing/
  host bottleneck classification. It retains the existing raw-energy Geyer ESS under its
  separately named estimator and adds separately named, observable-specific rank-normalized
  bulk ESS and tail ESS where the trace semantics make those estimators mathematically
  applicable. Every ESS/second and ESS/joule output identifies its observable and estimator;
  raw samples/joule remains a distinct unadjusted metric.
- **Public gate:** five synthetic bottleneck fixtures classify correctly; changing raw speed
  while worsening autocorrelation can lower ESS/second; every metric names its observable and
  provenance. Rank-normalized bulk/tail values match vetted ArviZ and independently recorded
  reference cases within a declared tolerance. Constant, tied/discrete, and too-short traces
  return their audited value or explicit status; non-finite traces are rejected at the input
  boundary. A threshold applies only to the estimator variant and observable for which its
  source justifies it; the raw-energy Geyer metric never inherits a rank-normalized bulk/tail
  threshold.
- **Blind/metamorphic gate:** dominant-cost swaps, equal bottlenecks, missing energy facts,
  highly correlated traces, deceptive raw-throughput improvements, scale changes, sticky-tail
  traces with acceptable bulk behavior, tied discrete energies, and estimator-name/threshold
  substitution traps.
- **Independent oracle:** hand calculations from raw traces and cost terms, with ESS checked
  against pinned vetted ArviZ cases and a separately recorded reference implementation. The
  oracle compares each named estimator to the matching reference output and never treats one
  ESS variant as another's expected value.
- **Exit evidence:** report `unknown` when energy or calibration is unavailable. A numeric
  ESS/joule requires both recorded ESS semantics and an energy boundary. The equation audit
  records formulas, degenerate statuses, applicability limits, threshold provenance, and the
  explicit separation between raw-energy Geyer ESS and rank-normalized bulk/tail ESS before
  production code lands.

### TM-HYB-001 — Hybrid TSU/CPU/GPU Partitioning

- **Initial status:** `dependency_blocked`.
- **Dependencies:** `TM-API-001`, `TM-COST-001`, `TM-PROF-001`.
- **Suggested ownership:** `src/gibbsiq/hybrid.py`, component graph schema, and
  `test_hybrid_partition.py`.
- **Deliverable:** classify deterministic/dense/continuous and probabilistic/sparse components,
  enumerate or search device cuts, account for transfer/reprogram frequency, and emit an
  executable host/THRML plan with rejected alternatives.
- **Public gate:** exhaustive small component graphs recover the minimum declared cost;
  all-host and all-TSU limits behave correctly; unknown target facts prevent false precision.
- **Blind/metamorphic gate:** transfer-cost threshold crossings, component relabeling, repeated
  denoising stages, dense latent factors, and amortization changes.
- **Independent oracle:** enumerate every cut on small graphs and recompute cost/quality
  constraints directly.
- **Exit evidence:** the recommendation names assumptions and remains conditional without
  calibrated device facts.

### TM-BASE-001 — Uniform Exact And Classical Baseline Contract

- **Initial status:** `dependency_blocked`; exact corpus/oracle exist, while solver adapters do not.
- **Dependencies:** `TM-API-001`.
- **Suggested ownership:** `src/gibbsiq/baselines/base.py`, exact adapter, common result
  schema, and `test_baseline_contract.py`.
- **Deliverable:** a backend-neutral baseline protocol that records model checksum, witness,
  seed/RNG, version, hardware, tuning, compile, sample, postprocess, diagnostics, and wall
  times; exact enumeration uses the same fixture IDs.
- **Public gate:** adapter energies and witnesses are recomputed; missing accounting fields
  fail; fixed-work and fixed-time modes cannot be mixed.
- **Blind/metamorphic gate:** omitted tuning, false self-reported energy, offset/sign traps,
  reordered variables, and incompatible timing budgets.
- **Independent oracle:** `benchmark_oracle.py` and native problem decoders.
- **Exit evidence:** non-MCMC solvers do not receive MCMC diagnostics unless their trace
  semantics justify them.

### TM-BASE-002 — Simulated Annealing And Independent Solver Adapters

- **Initial status:** `dependency_blocked`.
- **Dependencies:** `TM-BASE-001`.
- **Suggested ownership:** separate optional modules under `src/gibbsiq/baselines/` for
  `dwave-samplers`, OpenJij, and simulated bifurcation; adapter-specific tests.
- **Deliverable:** exact plus at least two independently maintained classical solvers under the
  uniform contract. Use Yao et al. as a digital comparator reference, not TSU evidence.
- **Public gate:** live optional-dependency parity on shared fixtures, seed behavior recorded,
  witness objective recomputed, and unavailable packages skip with an explicit reason.
- **Blind/metamorphic gate:** maximization/minimization sign flips, offsets, coefficient scale,
  unsupported labels, version drift, and tuning-accounting traps.
- **Independent oracle:** exact small corpus and native witnesses; upstream tests may be ported
  only with license, commit, file/line provenance, and a Gibbsiq-facing assertion.
- **Exit evidence:** at least two adapters pass matched fixture IDs. Package installation alone
  is not completion. `TM-REL-001` later repeats the optional adapters on the declared release
  matrix.

### TM-BENCH-001 — Reproducible Cross-Solver Harness

- **Initial status:** `dependency_blocked`; the fixture evaluator is not a matched-budget runner.
- **Dependencies:** `TM-BASE-001`, `TM-BASE-002`, `TM-PROF-001`.
- **Suggested ownership:** `src/gibbsiq/benchmark_runner.py`, artifact schema, generators,
  command-line entry point, and accounting tests.
- **Deliverable:** fixed-work and fixed-time modes, train/tune/test split, multiple seeds,
  target-hit probability, quality distribution, diversity, feasibility, time-to-target,
  energy-per-success when available, raw samples/traces, and checksummed manifests.
- **Public gate:** exact fixtures reproduce; interrupted/resumed runs retain identity; tuning
  never leaks into held-out evaluation; witness recomputation gates quality credit.
- **Blind/metamorphic gate:** private seeds, renamed fixtures, withheld optima, resource traps,
  anti-echo candidates, and syntactically different equivalent models.
- **Independent oracle:** external evaluator outside the package import path computes private
  optima or validates planted/proven witnesses.
- **Exit evidence:** aggregate tables are regenerable from raw artifacts and never keep only a
  best run.

### TM-BENCH-002 — Statistical-Physics Benchmark Family

- **Initial status:** `dependency_blocked`; tiny Ising tests and an isolated ICM primitive exist.
- **Dependencies:** `TM-BENCH-001`, `TM-NID-002`, `TM-CAT-001`.
- **Suggested ownership:** benchmark definitions and runners under `benchmarks/physics/`,
  tests under `test_suite/tests/`, raw artifacts outside source modules.
- **Deliverable:** two-dimensional Ising and Potts cases below, near, and above the critical
  region, plus frustrated/spin-glass cases; observables, autocorrelation, mode coverage, and
  replica/PT/ICM metadata.
- **Public gate:** exact small laws and known finite/closed-form observables match intervals;
  critical cases show larger autocorrelation than easy controls under the fixed reference
  sampler without encoding that observation as a universal threshold.
- **Blind/metamorphic gate:** hidden temperatures, gauge transforms, lattice relabeling,
  frustrated couplings, and same-energy opposite modes.
- **Independent oracle:** exact enumeration for small systems and independently implemented or
  established CPU reference algorithms for larger systems.
- **Exit evidence:** local Gibbs, PT, and optimization-only ICM results are labeled by their
  stationary semantics.

### TM-BENCH-003 — Bayesian-Inference Benchmark Family

- **Initial status:** `dependency_blocked`.
- **Dependencies:** `TM-BENCH-001`, `TM-IR-001`, `TM-VERIFY-01`.
- **Suggested ownership:** `benchmarks/bayesian/`, native posterior evaluators, and tests.
- **Deliverable:** at least one clamped hidden Markov model and one grid MRF or LDPC decoding
  task; posterior marginals, calibration, ESS, mode coverage, and end-to-end latency.
- **Public gate:** exact small posterior marginals and credible/confidence interval coverage
  match direct enumeration; observations are clamped throughout every schedule.
- **Blind/metamorphic gate:** hidden observations, state relabeling, likelihood scaling,
  disconnected latent components, and strong global correlations.
- **Independent oracle:** forward-backward for HMMs or exact enumeration for small factor
  graphs, implemented outside the sampler path.
- **Exit evidence:** posterior accuracy and optimization witness quality remain separate
  metrics.

### TM-BENCH-004 — Optimization And Combinatorial-Sampling Family

- **Initial status:** `dependency_blocked`; proven fixtures and witness oracle exist, while comparative
  runners and constrained lowering are absent.
- **Dependencies:** `TM-BENCH-001`, `TM-LWR-001`, `TM-CAT-001`.
- **Suggested ownership:** `benchmarks/optimization/`, fixture adapters, and tests.
- **Deliverable:** Max-Cut plus at least one constrained family and one diverse-solution family;
  integrate PT and the ICM primitive only under audited semantics; report target-hit
  probability, solution-quality distribution, near-optimum diversity, feasibility, and
  energy/resource per success.
- **Public gate:** every claimed optimum has a recomputed witness; exact small instances match
  optimum and degeneracy; fixed budgets compare the same transformed and native objectives.
- **Blind/metamorphic gate:** private generated instances, offset/gauge/scale/relabel changes,
  anti-echo witnesses, and penalty boundary cases.
- **Independent oracle:** exhaustive, closed-form, planted, or independently verified optima;
  best-known values are comparison targets only with a source.
- **Exit evidence:** no claim is based on the single best chain.

### TM-BENCH-005 — Hybrid AI Demonstration

- **Initial status:** `planned`; the re-entry condition is closure of the hybrid, runtime, and
  compiler contracts.
- **Dependencies:** `TM-HYB-001`, `TM-BENCH-001`, `TM-CAT-001`.
- **Suggested ownership:** `benchmarks/hybrid_ai/`, pinned model/data artifacts, and a compact
  reproducible notebook.
- **Deliverable:** a modest encoder → binary/categorical latent thermodynamic sampler → decoder
  pipeline with joint host/sampler accounting, exact synthetic mode-coverage checks, and a
  deterministic baseline. A large-scale image-quality claim is outside this gate.
- **Public gate:** end-to-end reproduction from pinned weights/data; latent sampler quality,
  host transfer, reconstruction, and wall time reported separately.
- **Blind/metamorphic gate:** latent-bit permutation, held-out seeds/data, all-host ablation,
  sampler-sweep sensitivity, and transfer-cost threshold changes.
- **Independent oracle:** synthetic multimodal law or enumerably small latent model plus an
  all-host reference execution.
- **Exit evidence:** the demonstration supports a heterogeneous-systems claim only; it does not
  establish state-of-the-art generation.

### GQ-INSPECT-01 — Artifact-Only Inspector Core

- **Initial status:** `dependency_blocked` until `TM-GOV-001` closes, then first-lane `ready`;
  `SampleResult`, diagnostics, traces, and machine-readable serialization exist, while no
  production `Inspector` class exists.
- **Dependencies:** `TM-FND-001`, `TM-GOV-001`.
- **Suggested ownership:** `src/gibbsiq/inspector.py`, a stable artifact-summary schema, and
  `test_inspector.py`; the coordinator integrates public exports. This task does not own
  compiler, profiler, or HTML code.
- **Deliverable:** `Inspector.from_result(result, *, model: IsingModel | None = None)` consumes
  a stored `SampleResult` without rerunning THRML and produces a deterministic artifact
  summary. It reports identity, variables, vartype, sample counts, stored energies, traces,
  diagnostics, warnings, best witnesses, timing/backend metadata when present, and explicitly
  unavailable sections. A compiled manifest is not a core input; compiled-artifact association
  belongs to `TM-API-001` and `TM-REP-001`.
- **Public gate:** a stored result renders JSON and Markdown summaries; diagnostic values are
  recomputed or traced to raw fields; best-row selection recomputes the first argmin of stored
  `interaction_energies` and then selects the corresponding total `energies` row and sample.
  With `model`, construction requires exact variable-order equality, a `SPIN` or `BINARY`
  result vartype, and independent recomputation of every row's total and interaction energy
  through `IsingModel.energy(..., vartype=result.vartype)` and
  `IsingModel.interaction_energy(..., vartype=result.vartype)`. Every stored value must agree
  within the project's audited absolute energy tolerance (`DEFAULT_TOLERANCE`, `1e-9` at the
  snapshot, zero relative tolerance) before the association is labeled
  `caller_supplied_sample_checked`; otherwise construction fails closed with the mismatched row
  and field. The checked association also records the exact variable-order field, result
  vartype, tolerance, and a deterministic SHA-256 model fingerprint. Its documented
  `ising_energy_v1` payload uses variable positions, normalized binary64-hex offset/linear/
  quadratic coefficients, sorted integer-index edges, canonical UTF-8 JSON, and no metadata,
  label `repr`, or other process-specific value. The fingerprint is interpreted only together
  with the separately recorded exact variable order and vartype. Without `model`, model
  association and objective recomputation are `not_available` with a reason. One- and
  multi-chain inputs, missing optional sections, offsets, and serialization round trips pass.
- **Blind/metamorphic gate:** reordered model variables, `SPIN`/`BINARY` equivalent samples,
  categorical-result rejection, offset shifts with a supplied model, any corrupt total or
  interaction-energy row, corrupt best-row selection, coefficient/order mutations, metadata
  mutations, missing optional metadata, unknown diagnostics, and hostile/custom labels. The
  fingerprint test rejects use of `repr` and checks independent reproduction from the
  documented payload.
- **Independent oracle:** parse the emitted summary and separately recompute sample counts,
  first-argmin index from `interaction_energies`, the selected total energy/sample at that
  index, and selected diagnostic facts from the raw artifact. When the caller supplies a
  model, independently recompute and compare both energy arrays for every sample row; when no
  model is supplied, assert the explicit `not_available` association state. Independently
  serialize the documented positional energy payload and reproduce the model fingerprint.
- **Exit evidence:** tests prove artifact-only operation by making sampler execution
  unavailable. The target API example in older prose becomes an implemented claim only after
  this gate closes.

### TM-REP-001 — Unified CLI And Full Inspector Integration

- **Initial status:** `dependency_blocked`; `gibbsiq-evaluate` and machine-readable component payloads
  exist, while compiler/profile/verify orchestration and static HTML remain absent.
- **Dependencies:** `GQ-INSPECT-01`, `TM-API-001`, `TM-PROF-001`, `TM-BENCH-001`.
- **Suggested ownership:** extend `src/gibbsiq/inspector.py` only after the core schema freezes;
  add `src/gibbsiq/cli.py`, report templates, and integration tests. Keep presentation
  separate from metric computation.
- **Deliverable:** public `compile_model`, `profile`, and `verify` commands/APIs;
  JSON, Markdown, and static HTML reports; topology/placement/routes,
  traces, diagnostics, best states, distribution error, provenance, warnings, and baseline
  comparison. This is the first task allowed to associate Inspector output through the
  compiled artifact produced by `TM-API-001`; it must retain the core's caller-supplied-model
  validation rather than treating a manifest as self-verifying.
- **Public gate:** reports render from stored artifacts without rerunning a sampler; every
  summary value recomputes from raw evidence; two-result comparison and unavailable sections
  work.
- **Blind/metamorphic gate:** missing optional fields, unknown cost facts, corrupt raw links,
  hostile labels/HTML escaping, reordered artifacts, and report regeneration.
- **Independent oracle:** parse emitted JSON and recompute a selected set of metrics and
  witness energies outside Inspector.
- **Exit evidence:** HTML snapshots or render checks are stored; a design note alone does not
  close the task.

### TM-REP-002 — Notebooks, Technical Guide, And Reproducible Data Release

- **Initial status:** `dependency_blocked`.
- **Dependencies:** `TM-REL-001`, `TM-REP-001`, `TM-IMP-002`, `TM-HYB-001`,
  `TM-BENCH-002`, `TM-BENCH-003`, `TM-BENCH-004`, `TM-BENCH-005`.
- **Suggested ownership:** `examples/`, `notebooks/`, release manifests, and concise reference
  docs. Generated outputs live in artifact directories with checksums.
- **Deliverable:** one quick-start plus physics, Bayesian, optimization, and hybrid examples;
  machine-readable data, pinned environments, and commands that regenerate every figure/table.
- **Public gate:** notebooks execute headlessly from a clean environment; links resolve; output
  hashes or justified numeric tolerances match.
- **Blind/metamorphic gate:** clean-machine install, alternate supported Python version,
  relocated repository path, missing optional extras, and regeneration without cached output.
- **Independent oracle:** release verifier checks manifests, raw artifacts, figures, and table
  derivations.
- **Exit evidence:** no hand-edited chart is accepted without the generating data and command.

### TM-REL-001 — Compatibility Matrix, Packaging, And Software-MVP Gate

- **Initial status:** `dependency_blocked`; `pyproject.toml` declares Python 3.10–3.13 while CI initially
  exercises only 3.13.
- **Dependencies:** every other M2 task, including `TM-REP-001`; this task may add early CI
  jobs once their runtime is bounded.
- **Suggested ownership:** `.github/workflows/ci.yml`, `pyproject.toml`, release checklist,
  packaging tests, and changelog.
- **Deliverable:** green Python 3.10, 3.11, 3.12, and 3.13 jobs for the zero-dependency core;
  separately declared optional THRML/dimod/ArviZ matrix; wheel/sdist install tests; versioned
  schemas and migration policy.
- **Public gate:** lint, format, mypy, Markdown math, unit, package-build, clean-install, and
  supported-version jobs pass from the release commit.
- **Blind/metamorphic gate:** isolated clean environments, absent extras, lowest and highest
  dependency bounds, path relocation, and deterministic artifact regeneration.
- **Independent oracle:** CI logs and installed-package smoke tests, not the development
  worktree.
- **Exit evidence:** documentation may claim only the versions whose jobs passed. A declaration
  in `pyproject.toml` is not verification.

### TM-PAPER-001 — Publication Artifacts And Claims-Evidence Closure

- **Initial status:** `dependency_blocked`.
- **Dependencies:** `TM-REP-002`, `TM-REL-001`, and completed benchmark artifacts.
- **Suggested ownership:** manuscript directory, `reference/claims-evidence-map.md`, figure/table
  generators, bibliography, and venue disclosure.
- **Deliverable:** central claim, related-work comparison, methods, validity limits, claims to
  evidence map, reward-surface/public-blind/oracle figures, bibliography, LaTeX manuscript,
  and venue-specific AI-usage disclosure.
- **Public gate:** every technical claim resolves to a test, proof, artifact, or primary source;
  every number regenerates; citation and format checks pass.
- **Blind/metamorphic gate:** context-free review finds no unsupported speedup, novelty, or
  hardware-measurement claim; selected tables are independently regenerated.
- **Independent oracle:** source/artifact audit by a fresh reviewer with no access to the
  implementation agents' self-reports.
- **Exit evidence:** the paper distinguishes evaluation-methodology evidence, software-system
  evidence, simulator performance, modeled hardware, and physical measurements.

### TM-RFC-001 — THRML Integration RFC/PR Artifact

- **Initial status:** `dependency_blocked`.
- **Dependencies:** `TM-REP-002`, `TM-REL-001`, `TM-API-001`.
- **Suggested ownership:** `reference/rfcs/` and a minimal upstream patch branch only after the
  local contract is frozen.
- **Deliverable:** narrowly scoped RFC or pull request for the reusable THRML boundary, with
  versioned API, tests, benchmark evidence, migration notes, and no dependency on private
  hardware interfaces.
- **Public gate:** local integration test against the pinned upstream commit passes and the RFC
  states which behavior belongs in Gibbsiq versus THRML.
- **Blind/metamorphic gate:** upstream version change, missing optional API, and backward-
  compatibility review.
- **Independent oracle:** clean clone against the exact upstream commit. Upstream acceptance is
  externally controlled and is not required to prove that the local artifact is complete.
- **Exit evidence:** record URL/commit if submitted; otherwise label the artifact `draft`.

### TM-HW-001 — Physical TSU Backend And Calibration

- **Initial status:** `blocked_external`.
- **Dependencies:** `TM-REL-001`, a documented device API, authorized device access, and a
  calibration interface supplied by the hardware owner.
- **Suggested ownership:** a separate optional backend and immutable calibration artifacts;
  simulator code remains unchanged.
- **Deliverable:** program/load/sample interface; coefficient and response calibration;
  device identity; raw samples; host transfer, programming, sampling, and diagnostics timing;
  documented energy measurement boundary; uncertainty and drift records.
- **Public gate:** exact small distributions bound physical stationary-law error; replayed
  calibration reproduces the programmed target within declared intervals; device errors fail
  explicitly.
- **Blind/metamorphic gate:** hidden small Hamiltonians, offsets, coefficient scales, repeated
  calibrations, warm/cold device states, and host/device workload matching.
- **Independent oracle:** host exact enumeration and external timing/energy instrumentation;
  the device's self-reported objective is never trusted.
- **Exit evidence:** matched TSU-versus-GPU/CPU workloads, equal quality targets, full raw data,
  confidence intervals, device/backend versions, and checksums. Until then, TSU cost fields
  remain assumptions or paper-derived models.

## Parallelization And File-Ownership Rules

The first-lane capacity rule is deterministic: select the prefix
`TM-VERIFY-01`, `TM-TARGET-01`, `GQ-INSPECT-01`. A coordinator with fewer than three worker
slots does not choose among these by preference; any skip requires a recorded blocker.

| Work | Safe parallelism | Unsafe overlap |
| --- | --- | --- |
| Target specification, CPU verifier, and importer research | Separate source modules and tests may proceed concurrently after shared schemas are frozen. | Concurrent edits to `model.py`, `result.py`, `hardware.py`, public exports, or equation-audit formulas. |
| Higher-order lowering and categorical runtime | Research and test-oracle preparation may run concurrently. | Two agents changing shared decoder/compiled-artifact schemas or penalty conventions. |
| Partition, placement, and routing | Independent read-only algorithm surveys may run together. | Production implementation out of dependency order; each artifact is the next task's input contract. |
| Non-idealities and cost model | Static parameter schemas can be reviewed concurrently. | Claiming timing/energy closure before topology, routing, and provenance fields are frozen. |
| Physics, Bayesian, and optimization benchmarks | May run concurrently after `TM-BENCH-001` freezes artifact and accounting schemas. | Each family inventing a different timing, witness, or raw-artifact contract. |
| Inspector, notebooks, paper, and RFC | Drafting can proceed from frozen artifacts. | Presentation code recomputing metrics differently from production, or paper tables edited by hand. |

One agent owns each writable file set. A second agent performs read-only critical review, then
the owner applies corrections. Unexpected concurrent changes are reread and integrated; they
are never overwritten from a stale buffer.

## Public And Blind Evaluation Contract

Every work package applies the hierarchical reward order:

1. model and transform correctness;
2. witness and decoder validity;
3. statistical and diagnostic honesty;
4. reproducibility and resource accounting;
5. solver or mapping quality.

Public tests teach the contract through exact, hand-derived, and intentionally failing cases.
Blind tests use private seeds and generated small instances, variable-order/offset/scale/gauge
mutations, diagnostic traps, resource-accounting omissions, and anti-echo witnesses. Hidden
evaluators remain outside the package import path. A public fixture's expected value is never
accepted without an independently valid witness or recomputation.

## Definition Of Done For Every Task

Before changing a task to `complete`, the owner records all of the following:

1. Dependencies are complete and the current source files were reread before editing.
2. Every new formula or convention appears in `equation-audit.md` before production code.
3. Production modules, public exports, schemas, and failure behavior match the task card.
4. Public tests cover success, numerical/structural boundaries, and a negative control.
5. An independent oracle, exhaustive small check, or metamorphic test does not trust returned
   summaries.
6. Raw samples/traces, seeds, RNG identity, versions, hardware, timings, checksums, and source
   classifications are recorded when the task generates evidence.
7. Focused tests, the relevant optional matrix, full unit discovery, Ruff, format, mypy, and
   Markdown-math checks run in proportion to the change. Exact commands and outcomes enter a
   dated append-only journal.
8. A critical reviewer inspects the actual diff and reruns at least one independent check.
9. `NEXT_TASK.md` records the completed commit and selects the next `ready` task from this DAG.
10. The commit contains only the audited task scope. External hardware or benchmark claims
    remain blocked when their evidence is unavailable.

## Coverage Of The Supplied ThermoMap Plan

| Requested component | Owning task(s) |
| --- | --- |
| Binary/categorical thermodynamic IR, clamping, coordinates | `TM-IR-001`, `TM-CAT-001` |
| Complete provenanced `TSUSpec` | `TM-TARGET-01` |
| Ising/QUBO/BQM frontends | `TM-FND-001` |
| NetworkX, factor-JSON, existing-THRML frontends | `TM-IMP-001`, `TM-IMP-002` |
| Validation | `TM-VAL-001` |
| Higher-order factors and constrained encodings | `TM-LWR-001` |
| Degree reduction and equality constraints | `TM-LWR-002` |
| Coloring and block schedule comparison | `TM-COL-001` |
| Partition, placement, routing | `TM-MAP-001`, `TM-MAP-002`, `TM-MAP-003` |
| Coefficient quantization | `TM-FND-002` |
| Hybrid TSU/GPU partitioning | `TM-HYB-001` |
| THRML executable backend and one-call compiler | `TM-FND-001`, `TM-CAT-001`, `TM-API-001` |
| Parameterized latency/energy model | `TM-COST-001` |
| Thermodynamic roofline and ESS/joule | `TM-PROF-001` |
| Exact/statistical verifier and detailed balance | `TM-VERIFY-01` |
| Hardware non-idealities and stale communication | `TM-NID-001`, `TM-NID-002` |
| Physics, Bayesian, optimization, hybrid-AI benchmarks | `TM-BENCH-002` through `TM-BENCH-005` |
| Exact and classical baselines | `TM-BASE-001`, `TM-BASE-002` |
| CLI/API, Inspector, JSON/Markdown/HTML reports | `TM-API-001`, `GQ-INSPECT-01`, `TM-REP-001` |
| Notebooks and reproducible data | `TM-REP-002` |
| Compatibility and release | `TM-REL-001` |
| Technical paper and THRML RFC/PR | `TM-PAPER-001`, `TM-RFC-001` |
| Physical TSU calibration | `TM-HW-001` (`blocked_external`) |

This matrix is the completeness check. A future roadmap revision must keep every row or record
its explicit rejection and rationale in a dated journal.
