# AGENTS.md

Guidance for AI agents working on Gibbsiq.

## Project Identity

Gibbsiq is THRML-native optimization infrastructure for QUBO / Ising / BQM models. The
target product lowers standard optimization models into THRML block-Gibbs programs, records
the raw evidence needed to audit the run, compares against classical baselines, and reports
whether the result should be trusted.

ThermoMap is the compiler, mapping, verification, and thermodynamic-roofline capability track
inside Gibbsiq. It does not rename the Python package: production APIs continue to be exported
from `gibbsiq`. The live work order is
`reference/00-roadmap/autonomous-implementation-roadmap.md`; agent execution rules are in
`reference/00-roadmap/autonomous-agent-runbook.md`; live task state and claims are in
`reference/00-roadmap/NEXT_TASK.md`. The ledger may authorize multiple dependency-ready lanes
when their ownership is disjoint. Each worker claims and executes exactly one bounded task.

The project is THRML-first. Do not reinterpret it as a generic diagnostics package.
Diagnostics and dimod compatibility make the current THRML-backed path auditable and
interoperable. Planned baseline adapters will add independent comparison.

The important distinction is not that another optimizer found a low-energy sample. The
important distinction is the audit trail: model conversion is checked, sampler behavior is
measured, failures are flagged, and benchmark claims are checked against exact or
independently verified oracles.

Current repository status is recorded in `reference/00-roadmap/README.md`. The binary Ising
model layer, fixed-beta and parallel-tempering THRML correctness paths, diagnostics core,
strict witness oracle, and exact public corpus are implemented. The parallel-tempering
correctness criterion and the 2026-07-11 diagnostic semantic correction are closed by the
2026-07-14 verification record. Rank-normalized bulk/tail ESS, general constraint feasibility,
and comprehensive joint-mode diagnostics remain open. Pairwise categorical/domain-wall
lowering is implemented; it does not supply general higher-order or knapsack/TSP constraint
encoding. Inspector and classical solver adapters remain absent. The Stage 6 analysis
foundation includes a provenanced `TSUSpec`, coefficient quantization, exact small-law
comparison, logical admissibility, and supplied-partition communication proxies; automatic
partitioning, placement, routing, calibrated costs, and target-aware execution remain absent.

## Non-Negotiable Contracts

- Use the canonical Ising convention from `reference/08-evaluation/equation-audit.md`:
  `E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j`, with `s_i in {-1,+1}`.
- Preserve offsets through every QUBO / BQM / Ising conversion.
- Use the audited Gibbs conditional sign:
  `P(s_i = +1 | s_-i) = sigmoid(-2 * beta * gamma_i)`.
- Never treat R-hat, ESS, or diversity metrics as proof of optimality. They are sampler
  health warnings.
- Never benchmark on "best known" values unless the source is recorded. Prefer exact,
  brute-force, closed-form, planted, or independently verified optima.
- Candidate benchmark answers must include witness states. The oracle must recompute the
  objective from the input model.
- Do not silently regenerate golden fixtures. If a formula changes, update the equation
  audit first.

## Implementation Boundary

Until explicitly asked to implement solver code, work in documentation and research files
only. You may define conventions, schemas, test layout, and placeholder contracts, but do
not add production solver implementations as part of research-doc tasks.

When implementation begins, keep modules small and direct. Avoid god files, brittle wrapper
layers, and broad abstractions that do not match the roadmap. The intended layers are:

1. Interface and internal Ising IR.
2. THRML optimization runtime.
3. Diagnostics and telemetry.
4. Inspector/reporting.
5. Baselines and benchmarks.

The ThermoMap capability track adds target specification, compiler validation and transforms,
physical mapping, non-ideality verification, and quality-adjusted profiling across these
layers. Its roadmap controls dependency order; this short layer list does not.

## Code Style And Naming

This is a Python codebase: follow **PEP 8**. It is the best, standard naming convention for
Python and the one every Python developer, linter, and the `dimod` ecosystem expects. Do
**not** use camelCase for Python identifiers — it is non-idiomatic and works against tooling
and readers. The existing code already conforms; match it.

- `snake_case` for modules, functions, methods, variables, parameters, and JSON/fixture keys
  (`compile_qubo`, `best_energy`, `witness_spin_samples`).
- `PascalCase` for classes and type aliases (`IsingModel`, `SampleResult`, `Vartype`).
- `UPPER_SNAKE_CASE` for module-level constants (`DEFAULT_TOLERANCE`, `FAMILY_SPECS`).
- Leading `_` for private/module-local helpers (`_resolve_variables`, `_spin_witness`).
- Names must be intuitive and descriptive — no random or guessed abbreviations. The only
  short names allowed are domain-standard math symbols (`h`, `J`, `beta`, `gamma`).

See `CLAUDE.md` → "Code style and naming conventions" for the worked examples.

## Evaluation Strategy For Agentic Work

Agents should optimize for verifiable rewards, not persuasive prose or self-reported wins.
A valid reward must be computed by tests or oracles that do not trust the solver output.

Public tests should cover:

- exact small-instance energy equivalence;
- QUBO-to-Ising offset/sign conversion;
- analytic Gibbs conditionals;
- result schema and metadata;
- diagnostic trap fixtures;
- strict benchmark witness verification.

Blind tests should cover:

- private generated small instances with hidden seeds;
- variable-order, offset-shift, coefficient-scale, and spin-gauge mutations of public
  fixtures;
- private diagnostic traces that look superficially healthy but should fail;
- private baseline-accounting cases that check tuning time, versions, seeds, and hardware;
- anti-echo checks where a candidate cannot pass by copying expected fixture values without
  an independently valid witness.

The benchmark should award credit in this order:

1. Model correctness and witness validity.
2. Diagnostic honesty.
3. Reproducibility and resource accounting.
4. Solver quality under fixed-work and fixed-time budgets.

Do not reward best energy alone.

## Research Workflow

Before editing technical claims:

- Read `PROJECT_BRIEF.md`, `spec.md`, `CLAUDE.md`, and `reference/README.md`.
- For orientation, read `reference/glossary.md` and `reference/claims-evidence-map.md`.
- For math, read `reference/08-evaluation/equation-audit.md` before any raw paper transcript.
- For evaluation work, read `reference/08-evaluation/evaluation-framework.md` and
  `reference/08-evaluation/agentic-evaluation-research.md`.
- For benchmarks, read `reference/06-benchmarks/ground-truth-datasets.md` and
  `tools/generate_ground_truth.py`.
- Prefer primary sources: official docs, papers, source repositories.

## Commands

```powershell
$env:PYTHONPATH = "src"
python -m gibbsiq.evaluation .\test_suite\examples\evaluation-candidate.example.json
python -m unittest discover -s test_suite/tests
python tools/generate_ground_truth.py --out reference/06-benchmarks/fixtures/ground-truth-small.json
```

## Current Research Priority

Read `reference/00-roadmap/NEXT_TASK.md` before selecting work. Execute exactly one bounded
task that the ledger authorizes and assigns to the worker, following the dependency and
completion gates in
`reference/00-roadmap/autonomous-implementation-roadmap.md` and the evidence protocol in
`reference/00-roadmap/autonomous-agent-runbook.md`. A dated status report, including
`reference/00-roadmap/thermomap-plan-status-2026-07-14.md`, is evidence for its recorded
commit; it is not a live task queue.

Throughout, keep converting the project into an agentic workflow with verifiable rewards:
specify what is checked by public tests, what is held back as blind tests, and how rewards
prevent agents from cheating by reading fixtures, echoing expected values, overfitting to
public examples, or hiding sampler failures.

## Verification & Recording Obligations

Applies to **every** task, not just paper work. Default stance: distrust self-reported
numbers. A result is "done" only when an independent check confirms it **and** the evidence,
the choices behind it, and the raw data are recorded. If it was not recorded, it did not
happen. The cost of over-recording is disk; the cost of under-recording is an unreproducible
claim that fails review later.

### Choices you must document (with the rejected alternative and why)

- Any convention: energy sign, offset handling, variable ordering, upper-triangle vs diagonal,
  comparison tolerance. A convention *change* edits `equation-audit.md` first, then the journal.
- Any solver parameter: penalty weight, schedule/beta, seed, RNG, block strategy, `num_reads`,
  init state. Record the value, the search you did, and what you rejected.
- Any diagnostic threshold or flag boundary (ESS cutoff, R-hat-style limit, diversity floor,
  no-improvement window). Record the value, its justification, and a sensitivity note.
- Any deviation from `spec.md` / `PROJECT_BRIEF.md`, and any assumption made to proceed.
- Any data source classification: exact vs brute-forced vs closed-form vs planted vs
  best-known. Best-known is never used without a recorded source.

### Data you must capture (keep the raw — never only the summary)

- Raw samples and full traces, not just `best_energy`/`best_sample` and aggregate metrics.
- Seeds and RNG identity for every stochastic step; reproduction command.
- Solver/backend versions, device/hardware, OS where it can affect numerics.
- Timing split out by category: compile, sample, diagnostics, tuning, wall-clock. Never mix
  fixed-time and fixed-work budgets in one comparison.
- SHA-256 checksum + exact file path + parameters for every generated artifact.
- Primary-source URL/DOI inline for every external number or claim.

### What you must independently verify before claiming done (and the failure it blocks)

- Recompute the objective from the witness state via the oracle — never trust a reported
  energy. (blocks echoed/fabricated optima)
- Re-enumerate small instances exhaustively to confirm optimum + degeneracy. (blocks wrong target)
- Confirm offset survives every QUBO/BQM/Ising conversion and appears in `best_energy` +
  metadata. (blocks the dropped-offset failure)
- Confirm the Gibbs conditional sign against `equation-audit.md`. (blocks the sign-bug class)
- For empirical sampler claims, report a statistical interval, not a point estimate. (blocks
  noise-as-signal)
- Re-run from the stored seed/config and get the same result before saying "reproducible".
- Confirm diagnostics distinguish healthy / unhealthy / `not_enough_data` on the relevant
  fixtures. (blocks hidden mode collapse and false-healthy traces)
- Run the matching test module and record the command + pass/fail. A green test you did not
  run is not evidence.

### Record failures too

Negative results, abandoned parameters, flaky runs, and traps you fell into are recorded, not
deleted — in a diagnostics-first project, a hidden failure is the worst outcome. Append a new
journal entry; do not rewrite an old one.

### Where each thing goes

- Design decisions and experiments → dated `research-journal/` entry (append-only).
- Per-run provenance → the result `metadata` fields listed in `spec.md`.
- Raw samples/traces and generated corpora → artifact files with recorded checksums.
- Convention changes → `reference/08-evaluation/equation-audit.md` **first**, then journal.

## Paper / Publication Track

We are building toward a publication. Every agent's work is also paper material — capture it
as you go so the methodology can be transcribed without reconstructing it from git history.

### Target framing (in priority order)

1. **Primary, writable now — evaluation/benchmark methodology.** "Verifiable rewards for
   stochastic optimization-solver agents: anti-gaming evaluation for QUBO/Ising." Novelty is
   the *evaluation contract* (witness recomputation, anti-echo, metamorphic mutations,
   public/blind split, hierarchical reward surface), not "another QUBO solver." Source
   material: `reference/08-evaluation/agentic-evaluation-research.md`,
   `src/gibbsiq/benchmark_oracle.py`, `tools/generate_ground_truth.py`,
   `reference/06-benchmarks/ground-truth-datasets.md`. Candidate venue: NeurIPS Datasets &
   Benchmarks / eval workshop.
2. **Secondary — systems/tools.** "Gibbsiq: THRML-native infrastructure for auditable
   combinatorial optimization." Folds in as the harness/system section of (1); standalone
   only once the solver runs (JOSS/SoftwareX).
3. **Follow-up, gated on Stage 2–5 — empirical study.** "When do thermodynamic/block-Gibbs
   samplers beat classical baselines on QUBO?" Requires the THRML adapter + baselines +
   fixed-work/fixed-time runs. Do NOT make empirical performance claims before this exists.

Honesty constraint inherited from the impact audit: do not claim a blank-space market or a
generic THRML optimization advantage. Position against dimod, D-Wave Inspector, OpenJij,
simulated-bifurcation tools, and QuboAuditor.

### What a submission requires (deliverable checklist)

- A defensible central claim plus explicit novelty vs. the prior art above.
- A **claims → evidence map**: every technical claim backed by a fixture, a passing test, a
  proof/enumeration, or a cited primary source. No "best known" value without a recorded
  source (existing non-negotiable).
- Reproducibility artifacts: seeds, SHA-256 checksums, deterministic generators, and the
  exact-vs-best-known distinction stated per number.
- Figures/tables: reward-surface table, public/blind split diagram, oracle architecture,
  a worked anti-echo example, ground-truth corpus table.
- Related work + bibliography, abstract + keywords, LaTeX manuscript, and a venue-specific
  **AI-usage disclosure** (agents are used heavily; this is mandatory at most venues).

### Process and tooling (academic-research-skills plugin)

Pipeline: scope → lit review → outline + evidence map → methods/experiments (journal as you
go) → draft → internal review → revise → finalize/format → disclosure. Use ARS sub-commands
while drafting; reserve `/ars-full` (≈$4–6/run) for an end-to-end pass once scope is locked.

- `/ars-plan` — Socratic scoping, lock the claim and venue.
- `/ars-outline` — outline + evidence map (do this before any drafting).
- `/ars-lit-review` — annotated bibliography (seed from `agentic-evaluation-research.md`
  "Source Notes And Citations").
- `/ars-revision-coach`, `/ars-revision` — handle reviewer rounds.
- `/ars-citation-check` — verify every citation has a real, recorded source.
- `/ars-format-convert` — LaTeX/DOCX/PDF.
- `/ars-disclosure` — AI-usage statement.

### Paper-readiness on top of the recording obligations

Follow the "Verification & Recording Obligations" section above for *what* to record and
verify. For paper-readiness, each `research-journal/` entry additionally carries a one-line
**paper hook**: which section, claim, table, or figure the entry feeds. That single line is
what lets the methodology be transcribed into the manuscript without re-deriving it from code.
