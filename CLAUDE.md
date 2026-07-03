# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Gibbsiq is **THRML-native optimization infrastructure** for QUBO / Ising / BQM problems.
It turns standard optimization models into auditable THRML programs. Its differentiator is
not diagnostics in isolation. Its differentiator is the complete THRML optimization contract:
audited model conversion, graph-aware block construction, schedules, seed and initialization
control, trace capture, sampler-health diagnostics, baseline comparison, and witness-based
benchmark verification.

Do not reinterpret the project as a backend-agnostic diagnostics package. dimod and baseline
support are adoption and comparison bridges into the THRML path. Diagnostics are mandatory
telemetry for THRML-backed optimization runs, not an independent product objective.

The accurate analogy is Ocean and dimod for D-Wave plus ArviZ for Stan and PyMC, applied to
the THRML ecosystem: Gibbsiq is the ingestion, runtime-contract, diagnostics, and
independent-verification layer, while the general programming layer for thermodynamic sampling
units is THRML itself. Gibbsiq does not aim to be a PyTorch-like TSU programming layer; that
role belongs to THRML (Extropic-owned). The durable moat is independent verification and
diagnostics, which a hardware vendor cannot credibly supply for its own device; ingestion and
lowering may later be absorbed by an Extropic-owned optimization SDK, while the verification
and diagnostics contracts remain. Accordingly, the `SampleResult` schema, diagnostic inputs,
and benchmark oracle are kept backend-portable at the architectural level as a hedge. This is
contract-level portability that keeps the THRML-first execution target, journaled in
`reference/research-journal/2026-07-01-trust-layer-positioning.md`.

The repository has completed **Stages 0 through 3 of a 6-stage roadmap** (status:
`reference/00-roadmap/README.md`). `src/gibbsiq/` holds the model IR and conversions
(`model.py`, `conversions.py`), the `SampleResult` schema (`result.py`), the JSON evaluator
(`evaluation.py`), the strict benchmark oracle (`benchmark_oracle.py`), the THRML runtime
(`thrml_runtime.py` with `THRMLSampler` and `SamplerConfig`), deterministic DSATUR
graph-coloring block construction (`blocks.py`), the benchmark bridge
(`benchmark_bridge.py`) lowering ground-truth fixtures into the IR and scoring sampler
results against the strict oracle, and the diagnostics layer (`diagnostics.py`, pure
stdlib). **Stage 2 (THRML optimization runtime)** landed 2026-07-01 with exhaustive
small-instance validation; parallel-tempering execution is its open exit criterion.
**Stage 3 (diagnostics pipeline)** landed 2026-07-02: Geyer ESS/tau and plain split R-hat
(arviz v0.21.0 algorithm, cross-validated to 1e-9 against arviz and to 1e-8 against an
R-`posterior` reference), diversity/energy/chain sections, family-scoped failure flags with
a thresholds echo, and magnetization / distance-to-best traces — every `sample()` call
embeds the payload. SOTA alignment landed 2026-07-03: rank-normalized + folded split R-hat
under separately named `rank_normalized_rhat*` keys (EVAL-EQ-013; the plain `rhat` key is
frozen), and magnetization chain-disagreement wiring (`chains.magnetization` subsection)
closing the equal-energy double-well blind spot. Trace-window diagnostics assume a
constant-beta collection window (guaranteed by the runtime; see EVAL-EQ-007). The full suite
runs 265 tests (12 skip without the optional arviz dev dependency). Inspector and baseline
layers remain to be built.

## Commands

The project targets **Python >= 3.10** and the core package has **zero required runtime dependencies**.

```powershell
# Run the JSON fixture evaluator (primary verification entry point today)
$env:PYTHONPATH = "src"
python -m gibbsiq.evaluation .\test_suite\examples\evaluation-candidate.example.json

# Or via the installed console script (after `pip install -e .`)
gibbsiq-evaluate .\test_suite\examples\evaluation-candidate.example.json

# Evaluate a candidate and write the report to a file
python -m gibbsiq.evaluation <candidate.json> --output report.json --tolerance 1e-9

# Run the unit tests (stdlib unittest, no third-party deps required; THRML tests skip without pip install -e ".[thrml]")
python -m unittest discover -s test_suite/tests

# Regenerate the brute-force ground-truth benchmark corpus (deterministic)
python tools/generate_ground_truth.py --out reference/06-benchmarks/fixtures/ground-truth-small.json
```

The evaluator exits with status `0` **only** when every known fixture is present and passing.
Tests live under `test_suite/tests/` and run with the stdlib `unittest` runner (no pytest dependency yet);
there is no linter or CI configured. The framework prescribes a fuller layout under `test_suite/tests/`
(see `reference/08-evaluation/evaluation-framework.md` → "Suggested Test Layout").

## Canonical conventions (do not violate)

These are fixed contracts. Changing any of them requires updating
`reference/08-evaluation/equation-audit.md` **first**, then the fixtures.

- **Energy convention:** `E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j`, with
  `s_i in {-1, +1}`. Quadratic terms are upper-triangle only and never double-counted.
- **Gibbs local field:** `gamma_i = h_i + sum_j J_ij s_j`; single-site conditional is
  `sigmoid(-2 * beta * gamma_i)`. The sign here is a frequent source of bugs — it is explicitly
  audited.
- **Offset must be preserved** through QUBO↔Ising conversion and reported in `best_energy` and
  metadata. Dropping it is a hard evaluation failure.
- Fixtures must **not** depend on dictionary/iteration order. Floating-point comparisons use
  absolute tolerance `1e-9` unless a fixture states otherwise.

## Code style and naming conventions

This is a Python project, so follow **PEP 8** — it is the standard every Python developer,
linter, and the `dimod` ecosystem we interoperate with expects. Do **not** use camelCase for
Python identifiers; it is non-idiomatic and breaks reader/tooling expectations. The existing
code already conforms — match it.

- **Modules / packages:** short, lowercase `snake_case` filenames
  (`benchmark_oracle.py`, `generate_ground_truth.py`).
- **Functions, methods, variables, parameters:** `snake_case`
  (`compile_qubo`, `local_field`, `verify_benchmark_fixture`, `best_energy`, `variable_order`).
- **Classes / type aliases:** `PascalCase` (`IsingModel`, `SampleResult`, `Difference`,
  `Variable`, `Vartype`).
- **Module-level constants:** `UPPER_SNAKE_CASE` (`DEFAULT_TOLERANCE`, `UNORDERED_LIST_KEYS`,
  `SCHEMA_VERSION`, `FAMILY_SPECS`).
- **Internal/private helpers:** prefix with a single underscore (`_parse_pair_key`,
  `_resolve_variables`, `_spin_witness`); keep them module-local unless deliberately exported.
- **Names must be intuitive and descriptive**, not abbreviated guesses. Prefer
  `quadratic`/`coefficient`/`witness` over `q`/`c`/`w`. The few terse names that exist are
  domain-standard math symbols (`h`, `J`, `beta`, `gamma`) or documented helpers (`round6`) —
  reuse those exact symbols rather than inventing new ones.
- **String/JSON keys** in fixtures and serialized output stay `snake_case` too
  (`best_ising_energy`, `witness_spin_samples`) so the IR, fixtures, and `to_dict()` agree.
- Public API surface is whatever `src/gibbsiq/__init__.py` re-exports in `__all__`; keep that
  list sorted and in sync with the modules.

## Markdown LaTeX math formatting (do not violate)

Markdown documents in this repo (`README.md`, `reference/**/*.md`, design notes) are read
through a renderer that fails on one-line display math. Format every equation safely:

1. Keep inline math as `$...$` for short expressions inside sentences.
2. Write **every** display equation in multiline form — opening `$$` and closing `$$` each
   alone on their own line:

   ```md
   $$
   E(\mathbf{s}) = \mathrm{offset} + \sum_i h_i s_i + \sum_{i \lt j} J_{ij} s_i s_j
   $$
   ```

3. Never write a display equation as one-line `$$...$$`. A single one-line block early in a
   file cascades and breaks *every* equation after it.
4. Do not put punctuation, prose, or comments on the same line as `$$` (no trailing comma
   at the end of the math, either — move it into the following sentence).
5. Use `\lt` / `\gt` instead of a literal `<` / `>` inside math; a literal `<` is parsed as
   an HTML tag and breaks rendering.
6. Preserve all LaTeX commands (`\mathbf`, `\widehat`, `\sum`, `\beta`, `\gamma`, `\mathrm`).
7. Do not alter code blocks, shell commands, Python examples, citations, headings, or
   bibliography entries unless their math formatting is broken. After editing, scan the file
   and confirm no one-line display blocks remain.

## Architecture (target design)

The intended product is five layers (see `spec.md` and `reference/00-roadmap/`):

1. **Interface** — ingest QUBO / Ising / BQM into one internal Ising IR with deterministic
   variable ordering and offset-preserving conversion. IR fields: `variables`, `linear`,
   `quadratic`, `offset`, `vartype`, `graph`, `source_format`, `variable_order`, `metadata`.
2. **THRML optimization runtime** — lower the IR into THRML nodes/blocks/factors/programs and
   run block Gibbs with schedule/seed/init/read controls, deterministic DSATUR graph-coloring
   block construction, and trace hooks.
3. **Diagnostics and telemetry** — energy & best-so-far traces, autocorrelation, ESS-style
   estimate, R-hat-style chain disagreement, diversity (unique fraction, top-k mass, entropy,
   Hamming), feasibility, and failure flags (`mode_collapse`, `chain_disagreement`,
   `no_recent_improvement`, etc.).
4. **Inspector** — `Inspector.from_result(result).show()` produces topology/trace/diagnostic
   reports, best-state tables, and baseline comparisons.
5. **Benchmarks** — exact/bruteforce validator plus simulated annealing (neal/dimod), OpenJij,
   and simulated-bifurcation baselines, all run under the same energy convention and seeds.

Target API the whole stack converges on:

```python
model  = compile_qubo(problem)
result = THRMLSampler(config).sample(model, num_reads=128)
Inspector.from_result(result).show()
```

The result schema must expose `samples`, `variables`, `energies`, `best_sample`,
`best_energy`, `traces`, `diagnostics`, `metadata`, and `to_dimod()`.

## Evaluation harness (how correctness is checked)

`src/gibbsiq/evaluation.py` compares a candidate JSON document against golden fixtures in
`reference/08-evaluation/fixtures/`:

- `exact-small-instances.json` — exact energies, QUBO→Ising conversion, Boltzmann
  probabilities, Gibbs conditionals, and Max-Cut optima for tiny instances.
- `diagnostic-fixtures.json` — synthetic traces / sample counts that must trigger specific
  diagnostic flags.

A third group, **`benchmark`**, is loaded from
`reference/06-benchmarks/fixtures/ground-truth-small.json` — 27 small instances (Max-Cut,
number partitioning, knapsack, TSP, SK spin glass, plus named graphs with published
closed-form optima: Petersen, K4–K7, cycles, complete bipartite, hypercube Q3) whose optima
are **proven by exhaustive enumeration** in `tools/generate_ground_truth.py`. These are scored
by `src/gibbsiq/benchmark_oracle.py` under a **strict** criterion, *not* the generic
deep-compare: a candidate passes only if it matches the proven optimum value, the exact
degeneracy, **and** supplies a witness state whose objective the oracle recomputes from the
input model (feasibility + optimality re-verified, never trusting self-reported numbers). See
`reference/06-benchmarks/ground-truth-datasets.md` for the full dataset catalog (Tier A
self-generated + Tier B external libraries, every value with a recorded source) and
`test_suite/examples/benchmark-candidate.example.json` for the candidate shape.

Sampler results reach the oracle through `src/gibbsiq/benchmark_bridge.py`:
`compile_fixture` lowers a fixture's `input` block into the Ising IR and
`candidate_from_result` builds the oracle candidate from a `SampleResult` — both read **only**
the `input` block, never `expected`, so a candidate cannot echo proven values. Sampler
candidates are scored with `verify_optimum_claim`, which matches the strict criterion except
that enumeration-only keys (degeneracy, optimal-selection counts) may be omitted — sampling
cannot prove them — though a volunteered value is still checked. Knapsack and TSP fixtures
raise `NotImplementedError` in the bridge until a penalty/one-hot encoding layer exists.

Candidate input accepts three shapes (see `normalize_candidate`): a `results`/`fixtures` list
of `{id, actual}` rows, or a flat `{fixture_id: {...}}` map. Comparison is deep and recursive;
keys in `UNORDERED_LIST_KEYS` (`energy_table`, `best_binary_samples`, `best_spin_samples`,
`required_flags`, `sample_counts`) are compared as multisets so iteration order never matters.

Golden fixtures are **source-controlled** — do not silently regenerate expected outputs. If a
formula changes, update `reference/08-evaluation/equation-audit.md` first. The
"Non-Negotiable Failure Cases" list in `evaluation-framework.md` enumerates what automatically
fails evaluation (wrong Gibbs sign, dropped offset, repeated samples reported as diverse,
constant trace yielding healthy ESS, best-known values without a recorded source, etc.).

## Reference pack layout

`reference/` is the research backbone and is organized by concern, each subdir holding design
notes plus primary-source papers (`.md` summaries alongside `.pdf`):

- `00-roadmap/` — staged plan (stage 0 research → stage 6 adaptive hardware runtime).
- `01-architecture/` — THRML runtime notes.
- `02-interfaces/` — QUBO/BQM API, PyQUBO, qubolite.
- `03-samplers/` — baseline solvers, THRML optimization runtime notes.
- `04-diagnostics/` — mixing quality, R-hat/ESS (Vehtari), penalty weighting.
- `05-theory/` — Lucas 2014 Ising formulations of NP problems, p-bit / probabilistic computing.
- `06-benchmarks/` — `benchmark-plan.md` and benchmark-suite papers (Max-Cut/GSET, Amplify).
- `07-inspector/` — inspector design.
- `08-evaluation/` — the evaluation contract, equation audit, and golden fixtures.

When adding benchmark instances with known optima, record per the `evaluation-framework.md`
"Benchmark Families" rules: instance id, source, seed or file checksum, exact/best-known energy
(**with source**), formulation metadata, solver config, raw samples/traces, diagnostics, and
timings. Lucas 2014 (`reference/05-theory/`) is the canonical source for NP-problem Ising
formulations (Max-Cut, TSP, knapsack, graph coloring, etc.).

## Research journal (always record decisions here)

Document every research decision and the process behind it in a dated entry under
`reference/research-journal/`. This is a hard convention, not an optional nicety: the journal
is the publication-grade record whose methodology transcribes directly into the final paper,
so any session that makes a design choice, runs an experiment, resolves a hard point, or
shifts positioning must leave an entry rather than let the reasoning live only in code and git
history. One dated entry per work session (`YYYY-MM-DD-topic.md`); entries are append-only —
when a decision is later revised, add a new entry instead of rewriting an old one.

- **Writing tone is fixed by `reference/research-journal/style.md`.** Write each entry in the
  register of the project's anchor paper (Jelinčić et al. 2025, arXiv:2510.23972): direct,
  detailed, declarative present tense, every claim tied to a mechanism, a measurement, or a
  primary-reference identifier. State the positive fact; do not define something by what it is
  not, and do not use the "not X but Y" contrast as a sentence pattern. No emojis and no
  rhetorical `**bold**` / `*italic*` emphasis in journal prose.
- **Skeleton** (use the sections an entry needs): Paper Hook, Context, Hard-Parts Analysis
  (`H1..Hn`, lead with this whenever the work had non-trivial reasoning), Decisions, Rejected
  Alternatives, Sources Read / Examples Used, Follow-Up, Verification. The strongest models to
  imitate are `2026-07-02-stage-03-diagnostics-pipeline.md` and
  `2026-07-01-stage-02-thrml-runtime-implementation.md`.
- The same tone governs the wider `reference/` pack; `style.md` subsumes the emoji/negation
  rules and adds the paper register.
- **Before starting work, read `reference/research-journal/gotchas-and-todo.md`.** It records
  the recurring writing and engineering pitfalls (Gibbs sign, offset preservation, R-hat
  variant mixing, constant-trace ESS, THRML sign mapping and edgeless-model `IndexError`,
  echo-proofing, one-line display math) and the live cross-stage TODO list. When a pitfall
  costs time, add a row; when a TODO closes, record it in a dated entry and remove it there.

## Workflow notes

- THRML docs: https://docs.thrml.ai/ — repo: https://github.com/extropic-ai/thrml
- Project glossary: `reference/glossary.md`; claims/evidence map:
  `reference/claims-evidence-map.md`.
- The git default branch (and the base for PRs) is `master`.
- Energy-sign and offset bugs are the highest-risk class here; when implementing conversions or
  conditionals, validate against the exact fixtures before anything else.
