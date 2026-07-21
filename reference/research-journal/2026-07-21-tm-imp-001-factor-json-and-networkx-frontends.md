# 2026-07-21 - TM-IMP-001 Factor-JSON And NetworkX Frontends

## Paper Hook

The ingestion boundary is where the trust-layer thesis first meets external data, and every
surveyed interchange representation loses at least one quantity the audited IR guarantees:
NetworkX node-link JSON coerces attribute keys to strings and merges Boolean and integer
node identities, dimod's bqm_schema 3.0.0 rebuilds every nested list label as a tuple by
convention, and the UAI, libDAI, Biq Mac, MQLib, and qbsolv formats carry integer indices
with no offset field at all. Factor-graph JSON schema version 1 therefore contributes a
position-scoped factor wire whose label channel reuses the typed codec audited in TM-IR-001
and whose offset is a required field, and its correctness witness is exhaustive enumeration
against the raw document rather than against any importer output.

## Context

`TM-IMP-001` is the sole dependency-ready task in the ledger after the `TM-IR-001` closure,
and this session starts from the remediated base `403bbb3`, which repaired the two
serialization and fold defects on this task's critical paths. The deliverable is a new
`src/gibbsiq/importers.py` with a versioned pairwise factor-graph JSON import/export and a
NetworkX graph import into `ThermodynamicProgram`, with NetworkX kept an optional extra.
The wire contract is fixed in `reference/02-interfaces/factor-graph-json-v1.md`, written
before any implementation code per the task's exit evidence. Tests were written first; the
module import failed as expected before implementation, and all 39 tests passed on the
first run after it.

## Hard-Parts Analysis

- H1 - Label-channel fidelity. NetworkX 3.6.1 `node_link_data` documents string coercion of
  attribute keys, emits tuple identifiers as JSON arrays, and collapses `1` and `True` into
  one node inside the live graph itself (session verification on 3.6.1); dimod 0.12.21
  serializes `variable_labels` as plain JSON values and deserializes every nested list as a
  tuple by convention, so list and tuple labels are indistinguishable after a round trip.
  The schema stores variables once as encoded typed-label records and scopes every factor by
  integer position, so the label channel is exactly the codec `ThermodynamicProgram` already
  round-trips. The importer re-encodes each decoded label and requires equality with the
  input record, the same canonical gate `program.from_dict` applies.
- H2 - Offset as a required field. A document without an offset is indistinguishable from a
  producer that dropped it, and dropped offsets are the project's highest-risk defect class,
  so the reader refuses to default it. The NetworkX frontend accepts the offset from exactly
  one channel per call and rejects the keyword and the graph attribute arriving together,
  even when equal.
- H3 - One ordering rule for scopes. Requiring a two-element scope to be strictly increasing
  subsumes four failure modes in a single check: self-pairs, reversed duplicates, repeated
  records, and ambiguity about which coupling triangle the wire carries. The rule mirrors
  the upper-triangle quadratic convention in the energy contract, and the duplicate-scope
  set makes repeated records an explicit error rather than a silent sum.
- H4 - Optional-dependency inversion. The graph frontend consumes the duck-typed surface
  `is_directed()`, `is_multigraph()`, `nodes(data=True)`, `edges(data=True)`, and the
  `.graph` mapping, and `importers.py` contains no networkx import. A subprocess test plants
  `sys.modules["networkx"] = None` and imports a stub graph successfully, which proves the
  frontend works on machines without the extra while the same test file also exercises real
  `networkx.Graph` objects when the extra is installed.
- H5 - Reuse of the audited conversion path. Both frontends lower through the structured
  `{"linear", "quadratic", "offset"}` form of `compile_ising`/`compile_qubo` with the
  document's variable order passed explicitly. The structured form keeps a variable label
  spelled `"linear"` distinct from the schema key, the explicit order preserves document
  positions through the QUBO conversion so positional `source_id` provenance survives, and
  `_resolve_variables` supplies the equality-alias fail-closed gate (`1` beside `1.0` beside
  `True`) that the remediated base hardened.
- H6 - Canonical export as a fixed point. Export emits the dense linear block in position
  order, the quadratic block in the IR's position-sorted order, `source_id` on every factor,
  ascending clamp/coordinate/observation records, and omits empty optional sections. IR
  canonicalization drops zero-coefficient pair factors, so import discards their source
  annotations with them; with that rule, export-import is a fixed point on every canonical
  document, verified per-case in the artifact run.

## Decisions

1. Schema envelope: required `format`, exact-integer `schema_version` 1, exact uppercase
   `vartype` string on the wire, required finite `offset`, encoded `variables`, and
   position-scoped `factors`; unknown fields at document and record level fail closed. The
   Python graph API accepts `normalize_vartype` inputs because it receives Python values.
2. `BINARY` documents and graphs convert one way: import maps bits through `x = (1 + s)/2`
   via `compile_qubo`, clamp bits map to spins as `2v - 1`, and export always emits `SPIN`
   because the IR records no producer vartype intent.
3. Clamps flow to the program layer as an ordered pair sequence so its existing duplicate
   and conflicting-clamp distinction applies; coordinates and observations reject duplicate
   positions at parse time because the program layer receives mappings.
4. Metadata is validated against the JSON-safe closure with path-carrying messages; import
   raises `ValueError` for malformed documents and export raises `TypeError` for unsupported
   Python types on live programs.
5. NetworkX policy: directed graphs, multigraphs, self-loops, and duplicate or reversed
   duck-typed edge pairs are rejected; a missing edge coefficient is an error unless
   `default_coefficient` is supplied; missing node biases read as `0.0`; the default node
   order is the canonical typed order with an exact-match `node_order` override; graph
   attributes are preserved under `metadata["graph_attributes"]` with
   `metadata["source_format"] = "networkx"`.
6. Packaging: a `networkx>=3.0` optional extra joins `pyproject.toml` and the five public
   names (`FACTOR_GRAPH_FORMAT`, `FACTOR_GRAPH_SCHEMA_VERSION`, `factor_json_from_program`,
   `program_from_factor_json`, `program_from_networkx`) join the sorted `__all__`.
7. No external implementation or test code was copied. The surveyed licenses (NetworkX
   BSD-3-Clause, dimod Apache-2.0, pgmpy MIT) and the semantic mismatches are recorded in
   the schema document per the task's research boundary.

## Rejected Alternatives

- Label-keyed factor records: they force label equality into duplicate detection and double
  document size; integer positions are exact and compact.
- Optional offset defaulting to zero: indistinguishable from a dropped offset.
- Symmetrizing directed graphs: NetworkX merges a re-added edge's attributes with
  `dict.update` semantics at add time, so a directed input's intended coupling is already
  ambiguous before the importer sees it.
- Emitting `BINARY` on export when the source was a QUBO: the IR stores only the SPIN form,
  and inventing producer intent breaks the one-canonical-form rule.
- Sparse linear export: density keeps the variable list and factor list in agreement and
  keeps export a fixed point.
- Merging the import-side JSON validator and the export-side JSON copier into one flagged
  walker: the two differ in return semantics and error type, and the simplification pass
  confirmed keeping them separate preserves intent.

## Sources Read

- `reference/00-roadmap/NEXT_TASK.md` (task card) and
  `reference/00-roadmap/autonomous-implementation-roadmap.md` (dependency edges).
- NetworkX `node_link_data` reference and 3.6 release notes (PR 8282 removing the `link`
  kwarg deprecated in PR 7565); session verification of node identity collapse, edge
  re-add merge, and self-loop iteration on networkx 3.6.1.
- dimod `binary_quadratic_model.py` and `variables.py` (bqm_schema 3.0.0,
  `iter_serialize_variables`); session verification on dimod 0.12.21.
- pgmpy readwrite modules (UAI and XMLBIF), the UAI evaluation format specification, a
  libDAI `.fg` example, the Biq Mac library format page, and the MQLib input README.
- `src/gibbsiq/model.py` (typed-label codec, `canonical_variable_sort_key`,
  `normalize_vartype`), `src/gibbsiq/program.py` (normalization contracts, factor ids),
  `src/gibbsiq/conversions.py` (structured parse paths, `_resolve_variables`).

## Verification

- Red phase: `test_suite.tests.test_importers` fails with a module import error at base
  `403bbb3`; after implementation the module passes 39 tests in 0.158 seconds, including
  the with-networkx classes (networkx 3.6.1 installed) and the subprocess evidence that
  `gibbsiq.importers` never imports networkx.
- Simplification pass: one behavior-preserving consolidation (required list fields validate
  through `_record_list`), 39 tests and Ruff gates identical before and after.
- Nearest modules: `test_thermodynamic_program`, `test_model_compatibility`,
  `test_conversion_scenarios`, and `test_public_api_thermomap` pass 71 tests in
  0.459 seconds.
- Full suite: `python -m unittest discover -s test_suite/tests` passes 647 tests with
  0 skips in 101.164 seconds on CPython 3.13 / Windows 11 (39 tests added by this task).
- Static gates: `python tools/check_markdown_math.py`, `ruff check .`,
  `ruff format --check .`, `mypy src/gibbsiq` (25 source files), and `git diff --check`
  pass.
- Independent oracle sweep (session scratchpad `verify_importers.py`, seeds 20260721 and
  31337): 15,993 exhaustively enumerated assignments across 1,500 random documents (max
  absolute error `3.553e-15`) and 5,159 assignments across 500 random duck-typed graphs
  (max absolute error `1.776e-15`), every expected energy computed directly from the raw
  document or graph rows; the 1,500-document export corpus hashes to
  `592fe0d1c416bd6847e98268373eca19b91fb72de0020439b33dd57094328054` under both
  `PYTHONHASHSEED=1` and `PYTHONHASHSEED=31337`.
- Artifact run `2026-07-21-factor-json-and-networkx` under
  `reference/00-roadmap/artifacts/tm-imp-001/` (generator
  `tools/generate_tm_imp_001_artifacts.py`, seed 20260721): 36 documents with 400
  enumerated assignments (max absolute error `1.776e-15`), 16 graphs with 94 enumerated
  assignments (max absolute error `8.882e-16`), per-case export fixed-point checks, and
  insertion-order invariance checks. Export corpus SHA-256 is
  `987952eab1d566609059b6f8c65aab031eac67a50d3ef3ac1e8e452867f634b2`; the manifest hashes
  to `f904a672dd3959c4d9d23d2bf65d2dcf0a2af208188318ddf957a20b61f69f08`; the pinned-source
  aggregate is `58e9a4ffc904fad47e1106710a440d0d11c2554e21504c95eb71df19ce7ef7a0`.

## Follow-Up

- Dependency-ready tasks after this closure: `TM-LWR-001` (earliest in roadmap edge order),
  `TM-CAT-001`, `TM-IMP-002`, and `TM-VAL-001`.
- Benchmark edge-list formats (Biq Mac, GSET, MQLib, qbsolv COO) are ingestion candidates
  for the benchmark bridge rather than this program envelope.
- Residuals recorded in the 2026-07-21 remediation journal remain open and unclaimed.
