# 2026-07-15 - Goal, Roadmap, And First-Frontier Integration

## Paper Hook

This entry feeds the systems-method section and the claims-to-evidence figure. It records why
the ThermoMap proposal is implemented as a dependency-ordered, mixing-aware compiler and
verification stack, and it ties the first three executable contracts to independent tests and
raw artifacts.

## Goal And Roadmap Reconciliation

`Project_GOAL.md` describes ThermoMap as a compiler, mapper, verifier, and profiler for
THRML-oriented probabilistic hardware, with a hybrid host path and quality-adjusted
thermodynamic roofline. The canonical roadmap covers that goal without a missing capability
lane:

| Goal capability | Roadmap ownership |
| --- | --- |
| Canonical program IR, clamping, coordinates, and imports | `TM-IR-001`, `TM-IMP-001`, `TM-IMP-002` |
| Higher-order lowering, categorical lowering, degree reduction, and coloring | `TM-LWR-001`, `TM-CAT-001`, `TM-LWR-002`, `TM-COL-001` |
| Complete target facts and exact reference verification | `TM-TARGET-01`, `TM-VERIFY-01` |
| Automatic partition, placement, and routing | `TM-MAP-001`, `TM-MAP-002`, `TM-MAP-003` |
| One-call compiled artifact and API | `TM-VAL-001`, `TM-API-001` |
| Non-ideal dynamics, cost boundaries, and mixing-aware roofline | `TM-NID-001`, `TM-NID-002`, `TM-COST-001`, `TM-PROF-001` |
| Hybrid execution, baselines, cross-domain benchmarks, and reports | `TM-HYB-001`, `TM-BASE-001`, `TM-BASE-002`, `TM-BENCH-001` through `TM-BENCH-005`, `GQ-INSPECT-01`, `TM-REP-001`, `TM-REP-002` |
| Compatibility, publication, upstream RFC, and physical calibration | `TM-REL-001`, `TM-PAPER-001`, `TM-RFC-001`, `TM-HW-001` |

No dependency or task-card change was required. Two roadmap interpretations are deliberate.
The production package remains `gibbsiq`; ThermoMap is a capability track rather than a
package rename. Modeled paper values and simulator timings cannot close `TM-HW-001`, which
remains externally gated on an authorized device and calibration evidence.

## Current-Source And State-Of-The-Art Audit

The source audit used primary papers, official product documentation, and source repositories.
It found no evidence that justifies changing the dependency order or weakening an evidence
gate.

1. The official [THRML architecture documentation](https://docs.thrml.ai/en/latest/architecture/)
   exposes programs, blocks, and factors for block-Gibbs simulation. This supports the current
   compiler/runtime boundary; it does not supply a physical topology or calibrated target
   contract.
2. The official [Extropic hardware roadmap](https://extropic.ai/hardware) identifies Z1 early
   access in 2026 but does not publish the stable topology, precision, communication,
   programming, or host-transfer facts needed by a mapper. `TSUSpec` therefore keeps those
   facts caller-supplied and provenanced instead of inventing defaults.
3. Jelinčič et al., [DOI 10.1038/s44335-026-00075-3](https://www.nature.com/articles/s44335-026-00075-3),
   combine circuit measurements with a physical system model for sparse local probabilistic
   hardware and emphasize mixing/expressivity tradeoffs. The paper supports topology and
   sensitivity modeling; its projected energy comparison is not a Gibbsiq optimization or
   physical-device benchmark.
4. Aadit et al., [arXiv:2606.25313](https://arxiv.org/abs/2606.25313), report a digital FPGA
   p-bit comparator where boundary communication changes solution quality. It reinforces the
   roadmap separation between partition, communication dynamics, and quality verification;
   it is not Extropic TSU measurement evidence.
5. The automatic-partitioning scan covered
   [dKaMinPar](https://arxiv.org/abs/2303.01417),
   [Jet](https://arxiv.org/abs/2304.13194), and the
   [parallel social spider algorithm](https://arxiv.org/abs/2004.03819). These are useful
   comparator or candidate backends for `TM-MAP-001`. None is an independent oracle for the
   small exact cut/balance tests required by that task.
6. The sampler scan included adaptive parallel tempering with isoenergetic cluster moves,
   [DOI 10.1038/s41467-025-64235-y](https://www.nature.com/articles/s41467-025-64235-y),
   and the p-bit update-policy study
   [DOI 10.1038/s41598-026-47285-0](https://www.nature.com/articles/s41598-026-47285-0).
   These results support future schedule, delay, and sensitivity experiments in
   `TM-NID-001`, `TM-PROF-001`, and benchmark tasks. They do not alter the need to establish an
   exact CPU reference and finite-kernel verifier first.

The accepted decision is to preserve the roadmap and execute its deterministic three-lane
frontier: `TM-VERIFY-01`, `TM-TARGET-01`, and `GQ-INSPECT-01`.

## Test-First Execution And Independent Audit

Each worker wrote its focused tests before its production module. The coordinator read the
binding sources, tests, and implementation rather than accepting the worker summaries. The
audit found and corrected four concrete issues:

1. The first independently pinned Inspector fingerprint digest was wrong. Recomputing the
   documented canonical payload outside Inspector produced
   `a7b042c433de7bb4c0ec3d71cfa63296019744fcfaae2f2d0761874a75291ff5`;
   the test and implementation now agree with that independent value.
2. Two opaque metadata keys of the same Python type received equal encoded key tokens. Sorting
   only by key leaked insertion order into JSON. The implementation now sorts the full encoded
   entry, and a reversed-insertion regression verifies byte-identical output without calling
   `repr`.
3. The initial complete-target tests allowed modeled scalar cell energy and time without a
   sensitivity range. Complete-contract validation now requires an access date and a matching
   unit/range for every supplied scalar fact; measured facts additionally require a device
   artifact.
4. The first empirical-verifier test allocated rounded exact-law counts and did not exercise
   the sampler. A fixed-seed test now takes one retained one-spin Gibbs refresh from each of
   2,000 independently derived RNG chains. The evidence artifact also records repeated-seed
   sensitivity. Caller-supplied state tables reject Boolean and floating aliases, observable
   identifiers are positional rather than `repr`-based, and the reported Hoeffding intervals
   are clipped to their declared support as required by EVAL-EQ-022.

The public integration test was also written before the root exports. Its first run failed on
the missing `CommunicationSpec` import, after which the new target, verifier, reference sampler,
and Inspector APIs were exported and exercised together.

## Decisions And Rejected Alternatives

- Decision: keep the verifier independent of THRML and cap exact enumeration at a declared
  state limit. Reusing the runtime lowering was rejected because the oracle would share the
  implementation under test.
- Decision: use finite row, stationary, detailed-balance, connectivity, and period checks.
  Treating detailed balance alone as sufficient was rejected because an identity kernel can
  satisfy it without exploring the law.
- Decision: represent target quantities in canonical SI units with explicit unknowns,
  provenance, and sensitivity intervals. Filling unavailable Z1 fields from modeled papers was
  rejected because it would convert projections into device facts.
- Decision: make the Inspector an artifact-only consumer. Replaying a sampler during reporting
  was rejected because it would replace stored evidence with a new stochastic run.
- Decision: defer HTML, compiled-manifest binding, calibrated roofline output, and automatic
  mapping to their dependency-ordered tasks. Combining them into this tranche was rejected
  because their input schemas and independent oracles are not yet frozen.
- Decision: pin Python, JSON, and Markdown files to LF in `.gitattributes`. The artifact
  manifests hash exact bytes, so platform-dependent `core.autocrlf` checkout conversion was
  rejected because it would invalidate otherwise correct SHA-256 evidence on Windows.

## Evidence Locations

- `reference/00-roadmap/artifacts/tm-verify-01/` contains raw reference traces, exact transition
  matrices and residuals, empirical draws, repeated-seed sensitivity, configuration,
  environment, generator, and SHA-256 manifest.
- `reference/00-roadmap/artifacts/tm-target-01/` contains serialized complete/unknown targets,
  independent topology enumeration, source classification, environment, and SHA-256 manifest.
- `reference/00-roadmap/artifacts/gq-inspect-01/` contains the stored input result,
  independently checked model association, JSON and Markdown summaries, environment,
  configuration, and SHA-256 manifest.
- Worker decisions, failures, commands, and limitations are recorded in the three dated task
  journals. This coordinator entry records cross-lane review, public integration, roadmap
  reconciliation, and final repository gates.

## Coordinator Verification

The coordinator-owned public API test was written before the exports changed. Its red-phase
run failed with one import error because `CommunicationSpec` was not exported from `gibbsiq`.
After integration, the focused commands passed 95 tests with no skips:

| Pattern | Tests | Unittest duration |
| --- | ---: | ---: |
| `test_reference_sampler.py` | 10 | 0.003 s |
| `test_statistical_verifier.py` | 20 | 0.047 s |
| `test_target_spec.py` | 15 | 0.162 s |
| `test_hardware_specs.py` | 12 | 0.001 s |
| `test_hardware_assessment.py` | 20 | 0.083 s |
| `test_inspector.py` | 15 | 0.008 s |
| `test_public_api_thermomap.py` | 3 | 0.002 s |

The final post-review repository command passed 518 tests with 0 skips in 108.136 seconds:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s test_suite/tests
```

ArviZ emitted its pre-existing constant-trace invalid-value runtime warning during a diagnostic
trap. No test failed. The final static gates passed:

```powershell
python tools/check_markdown_math.py
ruff check .
ruff format --check .
mypy src/gibbsiq
git diff --check
```

Ruff reported 69 formatted files and mypy reported no issues in 23 source files. An independent
coordinator loop recomputed file sizes and SHA-256 values for all 8 target-manifest entries, 7
verifier-manifest entries, and 6 Inspector-manifest entries. The manifest SHA-256 values are,
respectively,
`5fc6a3a32087561936dff69beebcc619d28cbee2e0bb0b3ae220a5b7121e94df`,
`7c203e5672a3d8ff1f976ee163778a43f877131e2f452f9362ba7ad20008e253`, and
`7aae3476248a9483bfdf9b4f5de7489bdd94112859170a695f1d85cf1f44804e`.

This evidence verifies the implementation candidate. The feature commit contains the code,
tests, sources, artifacts, journals, public exports, and status reconciliation; a following
ledger-only commit records the feature SHA and exposes `TM-IR-001` as the next dependency-ready
task without creating a self-referential commit hash.
