# Inspector Design

Status: the artifact-only core is implemented in commit `42c2409` with focused coverage in
`test_suite/tests/test_inspector.py`. HTML, CLI, comparison, and compiled-manifest integration
remain assigned to `TM-REP-001`.

## Authority And Sources

This design is subordinate to the repository source-of-truth order: `AGENTS.md` workflow,
[`equation-audit.md`](../08-evaluation/equation-audit.md) mathematics, executable source/tests
plus the latest verification record, the
[`autonomous roadmap`](../00-roadmap/autonomous-implementation-roadmap.md) dependencies, and
then [`NEXT_TASK.md`](../00-roadmap/NEXT_TASK.md) live ownership/state.

The current executable inputs are [`model.py`](../../src/gibbsiq/model.py),
[`result.py`](../../src/gibbsiq/result.py), and
[`diagnostics.py`](../../src/gibbsiq/diagnostics.py). D-Wave Inspector is interface inspiration,
not evidence that Gibbsiq already has equivalent topology or hardware artifacts:

- [D-Wave Inspector documentation](https://docs.dwavequantum.com/en/latest/ocean/api_ref_inspector/)
- [`dwave.inspector.show` documentation](https://docs.dwavequantum.com/en/latest/ocean/api_ref_inspector/generated/dwave.inspector.show.html)
- [D-Wave Inspector source repository](https://github.com/dwavesystems/dwave-inspector)
- [D-Wave embedding guidance](https://docs.dwavequantum.com/en/latest/quantum_research/embedding_guidance.html)

## Work Split

| Boundary | Dependency-ready core | Deferred integration |
| --- | --- | --- |
| Task | `GQ-INSPECT-01` | `TM-REP-001`, after `TM-API-001`, `TM-PROF-001`, and `TM-BENCH-001` |
| Input | Stored `SampleResult`; optional caller-supplied `IsingModel` | Compiled artifact, profile, benchmark, topology, routing, and baseline artifacts |
| Output | Deterministic in-memory summary plus JSON and Markdown | CLI orchestration, static HTML, plots, comparisons, and report bundles |
| Prohibited shortcut | Rerun THRML, infer missing model coefficients, or trust stored energies as an oracle | Treat a compiled manifest or profiler summary as self-verifying |

Closing the core task does not close the reporting stage or emit `software_mvp_complete`.
That label requires every M2 gate, including `TM-REP-001` and `TM-REL-001`.

## `GQ-INSPECT-01`: Artifact-Only Core

### API

```python
report = Inspector.from_result(
    result,
    model=model,  # IsingModel | None; keyword-only
)

summary = report.to_dict()
json_text = report.to_json()
markdown_text = report.to_markdown()
```

The constructor signature is exactly:

```python
Inspector.from_result(result, *, model: IsingModel | None = None)
```

The core never samples, compiles, profiles, reads a compiled manifest, or opens a browser.
An `Inspector.compare(...)` API and `report.show()` are deferred to `TM-REP-001`.

### Model Association And Energy Verification

`SampleResult` contains samples and stored total/interaction-energy arrays, but not the full
linear and quadratic Ising coefficients. The core therefore has two explicit association
states.

Without `model`:

- report stored energies as stored artifact fields, not independently verified values;
- set model association and objective recomputation to `not_available`;
- include the reason that no caller-supplied model was available;
- do not infer association from metadata, a model name, an offset, or a checksum string.

With `model`:

1. Require a position-by-position variable-order match using exact recursive label type and
   equality. Ordinary Python tuple equality is insufficient because `True == 1`, `1.0 == 1`,
   and the same aliases can occur inside tuple or frozenset labels. A set match in a different
   order is also insufficient for this core contract.
2. Require `result.vartype` to be `SPIN` or `BINARY`. `IsingModel` is internally spin-valued,
   while its energy methods explicitly accept either input encoding; a `CATEGORICAL` result is
   incompatible and fails validation.
3. For every sample row, recompute both
   `model.energy(sample, vartype=result.vartype)` and
   `model.interaction_energy(sample, vartype=result.vartype)`.
4. Compare every recomputed total and interaction energy with its stored row using the
   established project absolute energy tolerance `DEFAULT_TOLERANCE` (`1e-9` at the snapshot),
   with zero relative tolerance.
5. Only after all rows pass, label the association
   `caller_supplied_sample_checked` and record the tolerance, checked-row count, exact variable
   order, result vartype, and deterministic model fingerprint.

Any variable, vartype, total-energy, or interaction-energy mismatch fails closed with a
`ValueError` that identifies the field and row where applicable. A partially checked result is
never labeled associated. Adding a compiled-manifest association path is deferred until
`TM-API-001` defines the compiled artifact and `TM-REP-001` integrates it.

#### Deterministic Model Fingerprint

The association records `model_fingerprint` as SHA-256 over an `ising_energy_v1` payload. The
encoding is deliberately positional so it supports the current arbitrary hashable label
surface without serializing label `repr` values:

```text
schema = "gibbsiq.ising_energy.v1"
vartype = "SPIN"
num_variables = len(model.variables)
offset = normalized_binary64_hex(model.offset)
linear = [normalized_binary64_hex(model.linear[v]) for v in model.variables]
quadratic = sorted(
    [[left_index, right_index, normalized_binary64_hex(J_left_right)] for each edge],
    by=(left_index, right_index),
)
```

`normalized_binary64_hex` is `float.hex()` after normalizing either signed zero to positive
zero; model construction already rejects non-finite coefficients. Quadratic endpoints are
integer positions in `model.variables`, ordered with `left_index < right_index`, and edges are
sorted lexicographically by those positions. Serialize the payload as UTF-8 JSON with sorted
object keys, compact separators, no insignificant whitespace, and no metadata. Hash those
bytes with SHA-256.

The positional fingerprint is interpreted only with the separately recorded exact variable
order and vartype. It identifies the associated energy table, not arbitrary model metadata or
a relabeled model in isolation. It must never use process-specific `repr`, object identity,
hash iteration order, or pickle output. Public tests reconstruct the payload independently,
pin at least one golden digest, confirm metadata changes do not change it, and confirm
coefficient/order changes do. The independent oracle implements the encoding separately from
Inspector.

### Best-Row Semantics

The best row is the first argmin of `result.interaction_energies`, matching
`SampleResult.best_index`. The report selects the sample, stored interaction energy, and stored
total energy from that same row. It must not independently minimize the total-energy array or
silently repair a corrupt row.

When a model is supplied, the all-row verification above covers the best witness as a strict
subset. When no model is supplied, best-row selection is artifact consistency, not objective
verification.

### Core Summary Sections

The core summary is limited to facts available in `SampleResult` and deterministic
recomputations from those facts:

- artifact identity: schema version, variable order, vartype, sample count, and categorical
  state counts when present;
- best row: first-argmin index, sample, stored total energy, and stored interaction energy;
- model association: `caller_supplied_sample_checked` or `not_available`, including reason,
  tolerance, checked-row count, fingerprint, exact variable order, and vartype where
  applicable;
- traces and diagnostics: known fields with their stored status/provenance, plus unknown fields
  retained without reinterpretation;
- recorded metadata: backend, seed, timing, schedule, and versions only when present;
- availability: explicit `not_available` entries and reasons for every optional section that
  cannot be supported by the artifact.

The core does not invent warning thresholds. It preserves the distinction in the equation
audit between sampler-health flags, observations, and `not_enough_data`/unavailable states.

#### Summary Schema And Label Encoding

The implementation emits schema `gibbsiq.inspector.summary.v1`. Its top-level fields
are `artifact`, `stored_energies`, `best_row`, `model_association`, `traces`, `diagnostics`,
`warnings`, `metadata`, and `availability`. Stored traces, diagnostics, flags, and metadata
carry their `result.*` source path. Missing data and every deferred integration section carry
`status = "not_available"` and a concrete reason.

Variable assignments are positional. `artifact.variable_order` and
`model_association.variable_order` contain ordered `{position, label}` records, and
`best_row.sample_values` contains values in that order. Built-in immutable labels use tagged,
lossless JSON encodings: `none`, `bool`, decimal-string `int`, normalized binary64-hex `float`,
`str`, base64 `bytes`, recursively encoded `tuple`, and sorted encoded `frozenset`. An arbitrary
custom label uses `kind = "opaque"` plus its module-qualified Python type. The report therefore
retains the exact checked position while excluding object identity and process-specific
`repr`. Two opaque instances of the same type are distinguished by their positions in the raw
`SampleResult`, which remains the source artifact; the summary does not claim to reconstruct
opaque Python objects.

Non-string keys in auxiliary stored evidence use a sorted `mapping_entries_v1` representation.
Bytes use base64, sets use sorted item encodings, non-finite floats use explicit tagged values,
and other opaque Python values retain only their module-qualified type. This keeps JSON finite
and deterministic without presenting the report as a replacement for raw evidence. Markdown
embeds the complete JSON under a fence longer than any backtick run in the payload, so a stored
label cannot terminate the evidence block.

### Core Artifacts And Gates

The core may emit `summary.json` and `report.md`. Raw samples, traces, and metadata remain the
source artifact; the report must not replace them. JSON ordering and Markdown rendering are
deterministic for the same input.

Public tests cover:

- artifact-only construction while sampler execution is unavailable;
- one- and multi-chain payloads, absent optional sections, unknown diagnostics, and hostile
  labels;
- first-tie interaction-energy selection and same-row total/sample selection;
- exact variable-order and vartype validation;
- all-row total and interaction-energy recomputation for both `SPIN` and `BINARY` results;
- independent/golden reproduction of the documented fingerprint without label `repr`, plus
  coefficient, order, and irrelevant-metadata mutations;
- offset shifts and corruption in any energy row;
- serialization round trips and explicit `not_available` reasons.

The independent oracle parses the emitted JSON, recomputes structural counts and first-argmin
selection from the raw result, and, when a model is supplied, recomputes both energy arrays for
every row and reproduces the documented fingerprint outside Inspector. A no-model test asserts
that no objective-verification or fingerprint claim is present.

## `TM-REP-001`: Deferred Full Integration

The following features are intentionally absent from the dependency-ready core and belong to
`TM-REP-001` after their producing schemas freeze:

- `report.show()`, static HTML, escaping/render checks, plots, and report bundles;
- `Inspector.compare(...)`, solver/baseline tables, time-to-target, energy distributions, and
  matched resource accounting;
- compiler-manifest association and source-to-compiled provenance;
- topology, partition, placement, routes, congestion, block coloring, and communication views;
- roofline regimes, ESS/second, ESS/joule, non-ideality, uncertainty, and cost sensitivity;
- constraint feasibility and penalty views once the general constraint contract exists;
- unified compile/profile/verify CLI orchestration and stored-artifact regeneration.

`TM-REP-001` must consume stored artifacts without rerunning a sampler, retain the core's
caller-supplied-model checks, escape hostile labels, and keep unknown or unavailable hardware
facts explicit. Physical-device timing or energy remains unavailable until `TM-HW-001` closes.

## Evidence Boundary

This file defines interfaces and task ownership; it is not implementation evidence. The core
becomes present only after the roadmap's public, blind/metamorphic, independent-oracle, journal,
and coordinator-review gates close against actual source and tests. The full reporting claim
requires the separate `TM-REP-001` closure.
