# Gibbsiq And ThermoMap Roadmap

## Canonical Entry Point

This directory contains two roadmap layers:

1. `stage-00` through `stage-06` preserve the original Gibbsiq product history.
2. [`autonomous-implementation-roadmap.md`](autonomous-implementation-roadmap.md) is the
   canonical dependency graph for completing the full ThermoMap compiler, verifier,
   profiler, benchmark, and release plan from the current repository state.

After completing the canonical startup read order in
[`autonomous-agent-runbook.md`](autonomous-agent-runbook.md), use these roadmap controls in
this order:

1. [`NEXT_TASK.md`](NEXT_TASK.md) — current coordinator task plus zero or more explicitly
   `ready` or `claimed` parallel lanes; each worker claims one bounded task.
2. [`autonomous-agent-runbook.md`](autonomous-agent-runbook.md) — execution, verification,
   journaling, commit, and handoff loop.
3. [`autonomous-implementation-roadmap.md`](autonomous-implementation-roadmap.md) — stable task
   IDs, dependencies, public/blind tests, independent oracles, and exit gates.
4. [`thermomap-plan-status-2026-07-14.md`](thermomap-plan-status-2026-07-14.md) — detailed
   evidence audit and interpretation boundaries at the implementation snapshot.

If `NEXT_TASK.md` or the runbook is absent, the first ready task is `TM-GOV-001`. Chat history
does not replace the ledger.

## Status Snapshot — 2026-07-17

The verified foundation is commit `c62169e` (`feat: add audited ThermoMap analysis foundation`).
Commit `42c2409` (`feat: implement first ThermoMap frontier`) adds the independent CPU
Gibbs/exact-kernel verifier, complete target-fact schema, and artifact-only Inspector core. Its
commands, raw artifacts, checksums, review findings, and final integration evidence are recorded
in the four dated 2026-07-15 journals. Test counts belong to those recorded commands rather than
being a permanent property of the repository.

The target-independent `ThermodynamicProgram` envelope is now complete. The implementation
tracked at `35a2ba3` plus the 2026-07-17 closure commit provides exact Ising and pairwise
categorical clamping, logical coordinates, observation metadata, source-factor lineage,
deterministic relabeling, and versioned typed serialization. Its retained 42-program corpus
independently checks 248 projected assignments with maximum absolute energy error `0.0`.

The detailed audit reports two separate scores:

- optimizer and audit foundation: 8.5/10 = 85%;
- full ThermoMap proposal: 8/20 = 40% in the verified current tree.

These are equal-row capability scores. Placement, routing, degree reduction, stale dynamics,
cost calibration, and physical hardware access carry more engineering risk than their row
count suggests.

### Verified Present

- canonical offset-preserving Ising/QUBO/BQM model and `SampleResult`, with versioned lossless
  typed-label serialization;
- audited fixed-beta and parallel-tempering THRML execution with deterministic DSATUR blocks,
  seed/schedule/init controls, raw retained samples, traces, and work accounting;
- sampler-health diagnostics, strict witness oracle, anti-echo bridge, and exact 27-fixture
  corpus;
- exact capped Boltzmann comparison, declared stored-coefficient quantization, direct
  accumulator-range checks, and logical target assessment using topology capacity when supplied;
- THRML-independent seeded CPU Gibbs traces plus capped transition, stationarity,
  detailed-balance, ergodicity, and simultaneous full-state empirical-law verification
  conditional on caller-asserted independent retained states;
- complete provenanced `TSUSpec` facts for grid/explicit topology, coefficient and accumulator
  formats, communication, host transfer, programming/reprogramming, and optional cell facts;
- immutable target-independent `ThermodynamicProgram` roles, clamps, logical coordinates,
  observations, factor/source identities, same-type projection, reconstruction, and relabeling;
- pairwise categorical IR and exact domain-wall lowering;
- supplied-partition chain-order search plus separately named communication algebraic proxies;
- supplied-assignment Potts objective evaluation and an optimization-only ICM primitive;
- deterministic artifact-only Inspector JSON/Markdown summaries with optional all-row canonical
  energy verification.

### Open Product Boundary

The repository lacks automatic graph partitioning, variable placement, general routing,
degree-reduction/equality gadgets, hybrid TSU/GPU partitioning, stale-boundary dynamics,
calibrated end-to-end latency or energy, observable-specific ESS/joule roofline classification,
cross-domain baseline runners, unified Inspector/HTML/CLI reporting, and a physical TSU
backend.

The public execution path is the THRML JAX simulator. A simulator run validates software
lowering and sampling behavior on its recorded host. It does not establish production TSU
timing, energy, or optimization advantage.

## Original Stage History

The linked stage files retain their original scope and decisions. Their dated status
paragraphs are historical snapshots. This index and the autonomous roadmap state the current
implementation status.

| Legacy stage | Current evidence-based status |
| --- | --- |
| 0 — [Research and framing](stage-00-research-and-framing.md) | Complete for the original Gibbsiq scope: research pack, evaluator, strict oracle, and exact corpus exist. |
| 1 — [Core model compatibility](stage-01-core-model-compatibility.md) | Complete for binary pairwise QUBO/Ising/BQM and the target-independent program envelope. Pairwise categorical/domain-wall modeling, strict clamping, logical coordinates, observations, and factor lineage are implemented extensions. General higher-order factors and constrained encodings remain open. |
| 2 — [THRML optimization runtime](stage-02-thrml-optimization-runtime.md) | Core correctness complete. The 2026-07-14 correction verifies exchange sign, local transition/work accounting, first retained-sample work, and two-replica attempts. Device-side PT remains a performance refactor, not an open correctness gate. |
| 3 — [Diagnostics pipeline](stage-03-diagnostics-pipeline.md) | Core semantic correction complete and integrated. Scalar energy ESS/tau, plain and rank/folded R-hat, diversity, magnetization, and frozen-state checks exist. Rank-normalized bulk/tail ESS, feasibility, and broader joint-mode checks remain future work. |
| 4 — [Inspector and reporting](stage-04-inspector-and-reporting.md) | Partial. The artifact-only `Inspector` core emits deterministic JSON/Markdown and verifies every stored energy row against an optional caller-supplied model. Unified CLI, HTML, topology, profiler, baseline, and compiled-manifest integration remain under `TM-REP-001`. |
| 5 — [Baselines and benchmarks](stage-05-baselines-and-benchmarks.md) | Partial. Exact fixtures and witness verification exist; matched solver adapters, fixed-work/fixed-time runners, and comparative artifacts remain open. |
| 6 — [Adaptive hardware-aware runtime](stage-06-adaptive-hardware-runtime.md) | Partial analysis foundation. Complete provenanced target facts, topology contracts, independent Gibbs/kernel verification, quantization, exact-law comparison, logical admissibility, and supplied-partition communication analysis exist. Automatic mapping, target-aware execution, calibration, and adaptive compiler search remain open. |

The private runtime type `_Lowering` executes the current THRML conversion in process. A
public `THRMLProgramBundle` is not implemented. Target-flow prose using that name is an API
proposal rather than a current class.

## Canonical Delivery Sequence

The full dependency graph and task cards live in the autonomous roadmap. The shortest
software-MVP critical path is:

```text
governance and verified foundation
-> program IR + complete target contract + independent verifier
-> higher-order/degree lowering + schedule candidates
-> partition -> placement -> routing
-> compiled artifact and one-call API
-> non-idealities + end-to-end cost model
-> mixing-aware thermodynamic roofline
-> baseline harness + physics/Bayesian/optimization benchmarks
-> Inspector/CLI/reports
-> compatibility matrix and software release
```

The first frontier and `TM-IR-001` are complete. The live ledger selects `TM-IMP-001` as the
earliest dependency-ready unclaimed task: freeze a versioned pairwise factor-JSON contract and
an optional NetworkX importer without losing typed labels, offsets, clamps, coordinates,
isolated nodes, or source metadata. Other newly unblocked tasks remain governed by the roadmap
dependency order and may be exposed only through explicit, disjoint ledger claims.

The mapping passes are sequential because each freezes the artifact consumed by the next:

```text
TM-MAP-001 partition
-> TM-MAP-002 placement
-> TM-MAP-003 routing
-> TM-API-001 compiled artifact
```

Physics, Bayesian, and optimization benchmark families may proceed in parallel only after
`TM-BENCH-001` freezes the raw-artifact, timing, seed, and witness-accounting contract.

The release-state labels are intentionally narrower than “project complete”:

- M2 emits `software_mvp_complete` only after every M2 gate closes.
- M3 emits `simulator_research_release_complete` only after every simulator/research gate
  closes.
- M4 has no autonomous completion claim: it closes only after `TM-HW-001` records authorized
  physical-device calibration and matched evidence.

Without hardware access, the honest terminal state is M3
`simulator_research_release_complete` with `TM-HW-001` still `blocked_external`.

## Software And Hardware Completion Gates

The simulator-backed software milestones are autonomous once their Python dependencies and
public source material are available. `TM-REL-001` requires an actual Python 3.10–3.13 CI
matrix because `pyproject.toml` declares that range while the snapshot CI exercises only
Python 3.13. Support is verified only for jobs that pass.

`TM-HW-001` is `blocked_external`. It starts only when all of the following exist:

- an authorized physical TSU and documented backend API;
- immutable device identity and calibration interface;
- an agreed timing and energy measurement boundary;
- permission to preserve raw samples, calibration data, versions, and checksums.

No agent may fill that gate with modeled paper values or simulator timings. A hardware claim
requires exact small-law checks and matched TSU-versus-host workloads at equal quality targets.

## Source-Of-Truth Order

When status prose conflicts, use this order:

1. `AGENTS.md` and higher-level instructions for workflow and non-negotiable behavior;
2. canonical equations and conventions in
   [`../08-evaluation/equation-audit.md`](../08-evaluation/equation-audit.md);
3. executable source, tests actually run at the current `HEAD`, and the latest dated
   verification/status record for implementation status;
4. [`autonomous-implementation-roadmap.md`](autonomous-implementation-roadmap.md) for task
   dependencies and exit criteria;
5. [`NEXT_TASK.md`](NEXT_TASK.md) for active claims, file ownership, and the dependency-ready
   frontier, constrained by the roadmap dependencies;
6. `PROJECT_BRIEF.md`, `spec.md`, `CLAUDE.md`, dated journals, legacy stage prose, and other
   scope/history documents.

This order preserves historical decisions while preventing an old test count, open corrective
gate, or proposed class name from overriding the current tree.

## Adoption And Publication Tracks

Adoption remains a parallel concern after the relevant compiler and benchmark contracts
close:

- reproduce selected third-party THRML optimization work through the audited Gibbsiq path;
- prepare narrowly scoped upstream THRML contributions around stable sampler/compiler
  boundaries;
- publish the proven-optimum corpus as an independent Ising-machine verification suite;
- produce the claims-evidence map, raw benchmark artifacts, figures, bibliography, and
  mandatory AI-usage disclosure required by the publication track.

These tracks cannot bypass the witness, diagnostic, provenance, or matched-budget gates. The
defensible current contribution is the integrated audit contract and analysis foundation.
Automatic mapping and quality-adjusted calibrated costs are required for a distinct ThermoMap
systems claim.
