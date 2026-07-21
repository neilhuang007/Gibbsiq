# Factor-Graph JSON Schema Version 1 And The NetworkX Frontend

This document fixes the wire contract for `TM-IMP-001` before any implementation code.
It defines `gibbsiq-factor-graph` schema version 1, the import and export semantics in
`src/gibbsiq/importers.py`, and the policy set for the NetworkX graph frontend. The
schema decisions here bind the implementation; a change to any rule below requires a new
schema version and a dated research-journal entry.

## Scope

Schema version 1 carries pairwise Ising and QUBO factor graphs into and out of
`ThermodynamicProgram`. A document holds one model: a typed variable list, position-scoped
factor records of arity one or two, a required offset, and the program sections the IR
already defines (clamps, logical coordinates, observations, factor provenance, metadata).
Categorical models are out of scope for version 1 and export rejects them with a
`TypeError`; higher-arity factors and domain tables arrive with a future version once
`TM-CAT-001` fixes the categorical wire form.

## Document envelope

A document is a JSON object with six required fields and up to five optional fields.
Unknown top-level fields fail with `unknown factor-graph document field`, which keeps
version-2 additions detectable instead of silently ignored.

Required fields:

- `format`: the exact string `gibbsiq-factor-graph`.
- `schema_version`: the exact integer `1`. Booleans and floats are rejected; `True` and
  `1.0` are JSON-representable aliases of `1` and accepting them would make version
  detection depend on the reader's coercion rules.
- `vartype`: the exact string `SPIN` or `BINARY`. The wire format is strict about case;
  the Python graph API below normalizes through `normalize_vartype` because it receives
  Python values, and dimod-style vartype objects are useful there.
- `offset`: a finite JSON number. The field is required with no default because dropped
  offsets are the project's highest-risk defect class; a document that omits the offset
  is indistinguishable from one whose producer forgot it, so the reader refuses to guess.
- `variables`: a JSON array of encoded label records in model order. Each record uses the
  typed-label wire codec from `TM-IR` (`encode_variable_label` /
  `decode_variable_label`), so `1`, `1.0`, `True`, `"1"`, and `b"1"` stay distinct on the
  wire. The importer re-encodes each decoded label and requires byte equality with the
  input record, the same canonical check `ThermodynamicProgram.from_dict` applies.
  Decoded labels that alias by Python equality are rejected by the existing
  `variables must be unique` gate in the conversion layer.
- `factors`: a JSON array of factor records, possibly empty.

Optional fields: `clamps`, `coordinates`, `observations`, `metadata`. A canonical
document omits an optional section rather than carrying it empty.

## Factor records

A factor record is `{"scope": [...], "coefficient": number}` with an optional
`source_id`. Unknown record fields are rejected.

- `scope` contains one or two variable positions: exact integers in
  `[0, len(variables))`, booleans rejected. A two-element scope must be strictly
  increasing. This single rule subsumes three failure modes with one check: self-pairs
  (`[i, i]`), reversed duplicates (`[j, i]` after `[i, j]`), and any ambiguity about
  which triangle of the coupling matrix the wire carries. The energy convention already
  fixes quadratic terms to the upper triangle, so the wire mirrors it.
- Two factor records may not share a scope. Silent addition of duplicate records would
  hide producer bugs; a producer that wants a summed coefficient sums it before writing.
- `coefficient` is a finite JSON number; booleans, strings, `NaN`, and infinities are
  rejected. Position scopes rather than repeated label records keep documents compact
  and make the duplicate-scope check exact rather than equality-based.
- `source_id`, when present, is a non-empty string recorded in
  `ThermodynamicProgram.factor_sources` under the program's canonical factor identity:
  scope `[i]` maps to `linear:i` and scope `[i, j]` to `quadratic:i:j`. The mapping is
  positional and survives the BINARY-to-SPIN conversion because both frontends pass the
  document's variable order through explicitly.

The document energy is the project's fixed convention applied to the factor list:

$$
E(\mathbf{s}) = \mathrm{offset} + \sum_{\{i\} \in \mathrm{scopes}} c_i s_i
  + \sum_{\{i,j\} \in \mathrm{scopes}} c_{ij} s_i s_j
$$

with `s` in `{-1, +1}` for `SPIN` documents and `{0, 1}` for `BINARY` documents.

## Vartype semantics

`SPIN` documents lower directly through `compile_ising` using the structured
`{"linear", "quadratic", "offset"}` form with the decoded variable order passed
explicitly, so a string label spelled `"linear"` can never be misread as a schema key.

`BINARY` documents lower through `compile_qubo` under the same structured form. The
conversion to the SPIN IR is one-way at the wire level: export always emits a `SPIN`
document because the IR stores only the SPIN form, and re-deriving a QUBO would invent a
producer intent the program never recorded. The exported SPIN document is energy-equal
to the BINARY source at corresponding assignments under `x = (1 + s) / 2`.

Zero-coefficient pair factors are accepted on import; the IR canonicalization drops
them, and any `source_id` attached to a dropped factor is discarded with it. Linear
factors keep zero coefficients because the IR stores a dense linear vector.

## Clamps, coordinates, observations, metadata

- `clamps`: array of `{"position": p, "value": v}`. For `SPIN` documents the value
  passes through to the program layer unaltered, which enforces exact-integer domain
  `{-1, +1}` and rejects booleans. For `BINARY` documents the value must be the exact
  integer `0` or `1` (booleans rejected) and maps to the spin `2v - 1` during lowering.
  Duplicate positions flow to the program layer as an ordered pair sequence, so its
  existing `duplicate clamp record` / `conflicting clamps for one variable` distinction
  applies unchanged.
- `coordinates`: array of `{"position": p, "coordinate": [...]}`. Duplicate positions
  are rejected at parse time because the program layer receives a mapping and a
  duplicate would silently overwrite. Component validation (finite floats, no booleans,
  uniform dimension) stays in the program layer, which already owns those rules.
- `observations`: array of `{"position": p, "metadata": {...}}`. Duplicate positions
  are rejected at parse time for the same overwrite reason; the program layer enforces
  that every observed variable is clamped.
- `metadata`: a JSON object with exact string keys. Values are restricted to the
  JSON-safe closure: `null`, booleans, exact integers, finite floats, strings, arrays,
  and objects with exact string keys. Sets, bytes, tuples-as-keys, and non-finite
  floats are rejected with a path-carrying message. Import raises `ValueError` because
  the document is malformed; export raises `TypeError` because the failure is an
  unsupported Python type on a live program. Observation metadata obeys the same rule.

## Canonical export form

`factor_json_from_program` emits one canonical document per program, making
export-import a fixed point on canonical documents and giving reordered inputs a single
normal form:

1. `variables` in model order, encoded with `encode_variable_label`.
2. `factors` as the dense linear block first — every position, zeros included, in
   position order — followed by the quadratic block in the IR's position-sorted order.
   Every factor carries `source_id`, defaulted to its own identity, so provenance is
   explicit rather than implied.
3. `clamps`, `coordinates`, and `observations` ascending by position; empty sections
   omitted.
4. `metadata` deep-copied to plain JSON types (frozen mappings to objects, frozen
   sequences to arrays).
5. `vartype` is always `SPIN` and `offset` is the model offset.

Determinism was verified byte-for-byte under `json.dumps(sort_keys=True)` across
interpreter hash seeds during `TM-IR`; this schema adds no hash-order-dependent step.

## NetworkX frontend policy

`program_from_networkx(graph, *, vartype, ...)` consumes the duck-typed surface
`is_directed()`, `is_multigraph()`, `nodes(data=True)`, `edges(data=True)`, and the
`graph` attribute mapping. `importers.py` never imports `networkx`, so the zero-dependency
core is preserved and any object exposing that surface (including test stubs) works.
Objects missing the surface fail with a `TypeError` naming the graph-like contract.

- Node biases read from `linear_attribute` (default `bias`), edge coefficients from
  `coefficient_attribute` (default `weight`), clamps from `clamp_attribute` (default
  `clamp`), coordinates from `coordinate_attribute` (default `coordinate`). A missing
  node bias is `0.0`; a missing edge coefficient is an error unless
  `default_coefficient` is supplied, because `0.0` would silently delete a coupling the
  producer drew as an edge.
- The offset comes from the `offset` keyword or the graph attribute `offset`. Supplying
  both is rejected even when equal; neither present means `0.0`. Graph attributes are
  preserved verbatim under `metadata["graph_attributes"]` (validated JSON-safe) with
  `metadata["source_format"] = "networkx"`.
- Directed graphs, multigraphs, and self-loops are rejected. NetworkX stores one
  attribute dict per undirected edge and re-adding the edge in either orientation
  merges the new attributes into that dict with `dict.update` semantics (verified
  against networkx 3.6.1; the documented contract states that adding an existing edge
  updates its data). A directed or multi-edge input therefore has no faithful pairwise
  Ising reading, and refusing is the only lossless response. Duplicate or reversed edge
  pairs from duck-typed inputs are rejected by position-pair bookkeeping.
- Default variable order is the canonical typed order (`canonical_variable_sort_key`),
  which makes the import insertion-order invariant. An explicit `node_order` must list
  every node exactly once (exact typed match) and overrides the canonical order.

## Relation to existing formats

- NetworkX (BSD-3-Clause) `node_link_data` JSON collapses typed labels: its
  documentation states attribute keys are converted to strings for JSON compliance,
  tuple ids become lists, and `1` and `True` merge inside NetworkX itself (verified on
  3.6.1). It cannot carry the exact typed-label contract, so Gibbsiq consumes live
  graph objects instead of that JSON.
- dimod (Apache-2.0) BQM `to_serializable` (bqm_schema 3.0.0, verified on dimod
  0.12.21) stores `variable_labels` as plain JSON values: a tuple label is emitted as
  a JSON array and deserialization rebuilds every nested list as a tuple by
  convention, so a genuine list label and a tuple label are indistinguishable after a
  round trip. Its COO triple arrays motivated the position-scoped factor design here,
  while the typed-label codec repairs the label channel.
- pgmpy (MIT) represents factors as `DiscreteFactor(variables, cardinality, values)`
  flat tables with the left-most variable cycling fastest and interchanges through
  UAI and XML dialects (XMLBIF, BIF, NET); it publishes no JSON factor-graph format.
- The UAI inference format and libDAI `.fg` are integer-indexed text formats with
  dense or sparse per-factor tables over discrete domains; they carry no variable
  labels, no offset, and multiply factors rather than summing energies, so they fit
  `TM-CAT-001`'s table export better than this pairwise additive schema.
- Biq Mac / GSET, MQLib, and qbsolv COO edge lists are `i j weight` text triplets
  with integer indices only, no offset field, and an implicit vartype; they are
  ingestion candidates for the benchmark bridge rather than program envelopes.

No external schema was close enough to adopt wholesale, and no external implementation
or test code was copied into this task: the binding constraints are the typed-label
codec, the required offset, and program sections (clamps, coordinates, observations,
provenance) that none of the surveyed formats represent. The surveyed licenses
(BSD-3-Clause, Apache-2.0, MIT) are recorded here per the task's research boundary;
only the public iteration API surface of NetworkX is consumed, by duck typing.

## Rejected alternatives

- Label-keyed factor records (`{"u": ..., "v": ...}`): forces label equality semantics
  into duplicate detection and doubles document size; positions are exact and compact.
- Optional `offset` defaulting to `0.0`: indistinguishable from a producer that dropped
  the offset, the project's top-listed hazard.
- Accepting directed graphs by symmetrizing: NetworkX already merges reversed edges
  unpredictably at add time, so symmetrization would bless inputs whose meaning the
  producer never fixed.
- Emitting BINARY documents on export when the source was a QUBO: the IR does not
  record producer vartype intent, and inventing it would break the one-canonical-form
  rule.
- Sparse linear export: omitting zero linear factors saves bytes yet makes the dense
  variable list and the factor list disagree about which variables exist as factors;
  density keeps the export a fixed point.
