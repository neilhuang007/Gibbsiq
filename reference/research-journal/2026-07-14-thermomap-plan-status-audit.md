# 2026-07-14 - ThermoMap Plan Status Audit

## Paper Hook

This entry feeds the system boundary, limitations, and research-roadmap sections of the
Gibbsiq paper. It records a reproducible separation between the implemented THRML optimizer
and audit foundation and the proposed target-aware compiler, verifier, mapper, and
thermodynamic-roofline system.

## Context

The ThermoMap proposal describes a larger system than the existing Gibbsiq roadmap. Gibbsiq
already converts binary quadratic models into one Ising convention, executes THRML
block-Gibbs programs, records sampler evidence, and verifies optimization witnesses. The
proposal adds a target specification, hardware-aware transformations, physical placement and
routing, a quantization and non-ideality model, quality-adjusted hardware costs, additional
frontends, cross-domain benchmarks, and reports.

Older progress paragraphs also lagged the working tree. The supplied project status reported
209 tests with six skips and left parallel tempering and the Stage 3 corrective suite open.
The recorded 2026-07-14 corrective run executed 342 tests and passed. During this audit, a
concurrent paper-grounded tranche added candidate target, exact-distribution, quantization,
and cluster-move modules with focused tests. This entry preserves the pre-tranche baseline
and reports the concurrent tranche separately.

The resulting artifact is
`reference/00-roadmap/thermomap-plan-status-2026-07-14.md`. It maps every named ThermoMap
component and every 12-week deliverable to concrete source and test evidence.

## Hard-Parts Analysis

### H1 - One completion percentage merges different denominators

The implemented Gibbsiq substrate and the ThermoMap proposal answer different questions. A
substrate score asks whether canonical models can be lowered, sampled, diagnosed, and
verified. A ThermoMap score asks whether models can be transformed and placed on a declared
hardware target and whether useful independent samples can be costed and verified.

We therefore use two explicit denominators. Ten foundation capabilities score 8.5 points,
or 85%. Twenty ThermoMap components score 6.0 points, or 30%. The 85% value excludes
Inspector, baselines, physical mapping, and a TSU backend. The 30% value includes those
compiler/profiler requirements and is the correct summary of the supplied plan.

### H2 - Related primitives do not establish the proposed compiler behavior

The audit resolves ten recurring category errors.

1. Logical graph coloring does not establish physical placement or routing.
2. JAX floating-dtype validation does not establish fixed-point hardware quantization.
3. Correct replica exchange does not make an optimization-only ICM output an independent
   equilibrium chain.
4. Energy-observable ESS does not prove state-space mixing or optimality.
5. Test-local exact enumeration does not expose a reusable verifier contract.
6. A witness oracle does not execute classical baselines.
7. Categorical result storage does not implement a Potts IR or sampler.
8. Paper-derived energy and timing parameters are modeled values, not device measurements.
9. THRML JAX execution does not demonstrate physical TSU execution.
10. A low-energy witness and a healthy sampling process are separate claims with separate
    evidence.

Each distinction appears in the status artifact with the production symbol or missing
boundary that determines it.

### H3 - Concurrent implementation needs a frozen baseline

The active tranche contains a provenanced `TSUSpec` and fixed-point format, beta-effective
coefficient quantization with exact distribution comparison, and an isoenergetic
disagreement-cluster move. Source and test files appeared while this audit was being drafted.
At one audit snapshot, the focused run executed 43 tests and the full working-tree run
executed 385 tests; both passed, as did the static checks. These are command-specific audit
records, not final tranche-freeze counts: concurrent tests continued to land afterward.

The baseline completion percentages remain frozen. The tranche receives zero baseline credit
until its API review and dated implementation journals land. This rule prevents concurrent
work from changing the denominator or converting an in-flight implementation into a
retroactive baseline claim.

### H4 - A hardware performance claim needs an evidence class per parameter

The peer-reviewed Extropic system paper combines circuit measurement, device modeling, and
software simulation. Public THRML remains a JAX execution path for programs intended for
future hardware. A target analysis must therefore label every timing and energy parameter as
measured, modeled, assumed, or inferred. A future physical TSU claim requires a device
identity, calibration artifact, programmed values, observed samples, end-to-end timing, an
energy measurement boundary, and exact small-model distribution checks.

## Decisions

1. We score each checklist item as `1.0` for production implementation plus direct
   verification, `0.5` for a reusable subset, and `0.0` for design prose, test-local helpers,
   research prototypes, or absent behavior.
2. We weight rows equally because the source plan supplies no effort or impact weights. The
   status document states that row count is not a person-week estimate.
3. We publish foundation and full-ThermoMap percentages separately. We do not publish a
   blended percentage.
4. We keep the existing Gibbsiq roadmap and the proposed compiler roadmap as distinct paths.
   ThermoMap extends the current optimizer and trust layer.
5. We preserve old status paragraphs as historical snapshots. The dated reconciliation names
   their current resolution without rewriting their recorded facts.
6. We assign zero baseline completion credit to the active tranche. Its working-tree progress
   and verification results are reported in a separate section.
7. We keep the ICM primitive optimization-only. Coupled replica outputs are dependent and do
   not inherit independent-chain diagnostics.
8. We schedule domain-wall categorical lowering and Aadit-style communication profiling as
   subsequent gates. They are not part of the active implementation tranche.
9. Every gate carries a done-evidence checklist. A design, best-energy result, or persuasive
   report cannot close a gate alone.
10. We record a prospective 37.5% post-tranche score only as a conditional reassessment. The
    current full-ThermoMap score remains the 30% pre-tranche baseline until every stated
    closure condition is satisfied.

## Rejected Alternatives

- We rejected one percentage for the repository. It would let the mature Ising substrate hide
  the absent mapping and hardware-analysis system, or let the ambitious compiler denominator
  hide the quality of the implemented core.
- We rejected scoring roadmap stages as single units. Stage 5 already contains an exact corpus
  and oracle while lacking every solver adapter; one stage label cannot express that split.
- We rejected line-count weighting. Large files can represent architecture debt, and a short
  exact verifier can carry more scientific value than a long UI.
- We rejected credit for design documents and equation drafts. They define contracts and
  receive evidence credit only after production implementation and tests.
- We rejected immediate baseline-score updates when concurrent files appeared. The audit
  requires full verification, static checks, API review, and dated implementation journals.
- We rejected treating `_Lowering` float32 checks as hardware quantization. The former audits
  incidental backend rounding; the latter applies a declared target format with explicit
  rounding and overflow.
- We rejected treating the exact benchmark oracle as a baseline suite. The oracle verifies a
  candidate; a baseline suite measures independent solvers under matched budgets.
- We rejected integrating ICM into `THRMLSampler` during the primitive tranche. Stationary-law,
  trace-dependence, work-accounting, and diagnostics semantics require a separate audit.

## Sources Read And Evidence Used

Repository sources:

- `PROJECT_BRIEF.md`, `spec.md`, `CLAUDE.md`, `AGENTS.md`;
- `reference/README.md`, `reference/glossary.md`, and
  `reference/claims-evidence-map.md`;
- all stage files under `reference/00-roadmap/`;
- `reference/08-evaluation/equation-audit.md`;
- `reference/research-journal/gotchas-and-todo.md`;
- every production module under `src/gibbsiq/` and the directly relevant test modules;
- `tools/benchmark_performance_baseline.py`, `tools/benchmark_cluster_moves.py`, and
  `tools/generate_ground_truth.py`.

Primary external sources:

- THRML official documentation: https://docs.thrml.ai/en/latest/
- Jelinčič et al., peer-reviewed thermodynamic hardware system:
  https://www.nature.com/articles/s44335-026-00075-3
- Jelinčič et al., codon optimization and domain-wall representation:
  https://arxiv.org/abs/2606.17327
- Aadit et al., distributed million-pbit implementation:
  https://arxiv.org/abs/2606.25313
- Chowdhury et al., adaptive parallel tempering and ICM:
  https://arxiv.org/abs/2503.10302
- Vehtari et al., rank-normalized R-hat and ESS:
  https://doi.org/10.1214/20-BA1221

## Artifacts And Checksums

Status artifact:

- Path: `reference/00-roadmap/thermomap-plan-status-2026-07-14.md`
- Size at verification: 34,250 bytes
- SHA-256: `75a865ace8b62d0b4e70a57d0de4b7dfe5e5a2abf30bd8ee7f650db410182ba6`

Primary PDFs added by the concurrent research tranche:

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| `reference/01-architecture/papers/jelincic-2026-codon-optimization.pdf` | 2,081,289 | `81b73f3bc67e9b323b90cb27763701b7b529d2ee5fd753735464e4385b0066f9` |
| `reference/05-theory/papers/aadit-2026-million-pbit.pdf` | 25,492,691 | `56475ad7733bc5eb8e58e4435b7c549e2d1e26c76ede406d693c8c273949f268` |
| `reference/05-theory/papers/chowdhury-2025-adaptive-parallel-tempering-icm.pdf` | 16,392,886 | `e9a7eb2fb608b7ac8c8cc24284b0b3132392fdc83d09362b11df6eb0b0834cec` |

These hashes record file identity. They do not validate the claims in a PDF; the primary text
and its experimental boundary remain authoritative.

## Limitations

Equal row weights understate the technical risk of physical placement, routing, auxiliary
transformations, non-Hamiltonian error models, and device calibration. The component matrix
is more informative than its 30% summary.

The audit reads a shared working tree with concurrent edits. Line references describe the
2026-07-14 snapshot and may move after refactoring. The baseline/current-tranche separation
preserves the score when that occurs.

The recorded 385-test audit run established repository regression status at that working-tree
snapshot. It is not a final tranche-freeze count because concurrent tests continued to land,
and it does not establish Python 3.10–3.12 compatibility, GPU performance, physical TSU
behavior, mixing on large models, or a solver advantage. CI currently exercises Python 3.13
only.

No hardware energy, effective-samples-per-joule, or TSU speedup measurement was produced.

## Final Integration Addendum

The earlier sections above are immutable audit snapshots: 30% was the pre-tranche Full
ThermoMap baseline, and the 43/385-test runs were explicitly non-final. The final integrated
tree subsequently closed the analysis tranche after correcting the communication profiler,
exporting the reviewed package API, and running independent scouts plus the repository suite.

- Immutable Full ThermoMap baseline: 6/20 = 30%.
- Verified current-tree Full ThermoMap score: 8/20 = 40% under the same equal-row rubric.
- Optimizer/audit foundation: unchanged at 8.5/10 = 85%.
- Final focused evidence: 114 new-surface tests passed.
- Final repository evidence: 457 tests in 120.615 seconds, `OK`; Ruff lint and format,
  `mypy src/gibbsiq`, and Markdown math passed.
- Corrected communication boundary: Aadit paper-pair, aggregate-link, and max-composite
  algebraic proxies are distinct and are not latency, feasibility, hardware-frequency, energy,
  or mixing claims.
- Public API boundary: reviewed analysis APIs are exported and package-smoke tested; there is
  still no unified compile/profile/verify CLI or target-aware execution path.

The complete closure record, independent scout results, choices/rejections, environment, and
source/test/PDF hashes are in
`reference/research-journal/2026-07-14-thermomap-final-integration-verification.md`.
The finalized status artifact is 51,872 bytes with SHA-256
`a40203c9cf31be2d4e948fd0a361514f8886801a2cfe0baea298917073900172`.

## Follow-Up

1. Complete API review and implementation journals for the active target/quantization and ICM
   tranche, then record its post-baseline score separately.
2. Implement Potts IR and domain-wall lowering with exact bidirectional witness checks.
3. Build the communication and boundary-update profiler using explicit provenance and exact
   small-model error tests.
4. Add placement, routing, and degree-reduction passes only after the verifier can detect their
   distribution and witness effects.
5. Build fixed-work and fixed-time baselines before making optimization-impact claims.
6. Build the Inspector and thermodynamic roofline after their input schemas and provenance
   contracts stabilize.

## Verification

Inventory and evidence searches used `rg --files` and targeted `rg -n` queries over
`src/gibbsiq`, `test_suite/tests`, `tools`, `reference`, and the root project documents.

Focused active-tranche tests:

```powershell
$env:PYTHONPATH = "src"
python -m unittest test_suite.tests.test_hardware_specs test_suite.tests.test_exact_distribution test_suite.tests.test_quantization test_suite.tests.test_cluster_moves -v
```

Result at that audit snapshot: 43 tests ran in 0.019 seconds and passed. Concurrent test
additions after the command make this evidence non-final for tranche closure.

Full working-tree verification:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s test_suite/tests
```

Result at that audit snapshot: 385 tests ran in 117.775 seconds and passed. ArviZ emitted its
existing constant-trace `RuntimeWarning`; no test failed. Concurrent test additions after the
command make this evidence non-final for tranche closure.

Static and document checks:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m mypy
python tools/check_markdown_math.py
git diff --check
```

Results: Ruff lint passed; Ruff reported 51 files formatted; mypy reported no issues in 15
source files; Markdown math passed; `git diff --check` passed with line-ending warnings for
existing modified files.
