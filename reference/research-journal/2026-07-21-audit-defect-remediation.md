# 2026-07-21 - Remediation Of The 2026-07-19 Audit Defects

## Paper Hook

Both confirmed defects from the 2026-07-19 whole-tree audit close with the same design move:
each convention seam gets exactly one order authority. Frozenset serialization now delegates
member order to the label codec that later re-validates it, and every QUBO linear fold now
routes through the exact typed-label index that the rest of the conversion path already
enforces. The remediation therefore supplies direct evidence for the paper's claim that seam
defects are eliminated by collapsing duplicate conventions, and the fix surface is eleven
production lines.

## Context

The 2026-07-19 full-source audit (`2026-07-19-full-source-correctness-and-optimization-audit.md`)
confirmed two defects at base `cdd0a58` and routed them to a remediation task. This session
reproduces both at the same base, fixes them test-first, and verifies the repair with
independent oracles. The remediation precedes the `TM-IMP-001` feature claim because the
importer task consumes both repaired paths: factor-JSON export rides the
`ThermodynamicProgram` serialization round trip, and imported coefficients ride the QUBO
linear fold.

## Hard-Parts Analysis

- H1 - Two sort conventions on one payload. `program._encode_value` ordered frozenset items
  by `_canonical_json`, which ASCII-escapes non-ASCII characters, while the decoder's
  canonical check re-encodes through `model.encode_variable_label`, which orders items by the
  raw-code-point key `_encoded_label_sort_key`. Members such as `{"é", "f"}` order differently
  under the two keys, so `from_dict(to_dict())` rejected its own payload. The repair sorts the
  members with the public `canonical_variable_sort_key` before encoding, which reproduces the
  decoder's order by construction; no second sort convention survives on that payload.
- H2 - Equality-keyed buckets ahead of the typed-identity gate. `conversions._parse_qubo`
  folded diagonal QUBO entries into `linear_terms` through plain-dict `setdefault`, so a
  Python-equal, type-distinct diagonal label (`1.0` against linear `1`, `True` against `1`)
  merged silently before `_resolve_variables` could fail closed. A session probe showed the
  same bucket dict loses a coefficient outright when a non-dict `Mapping` supplies
  equality-aliased linear keys (`{1: 3.0, 1.0: 5.0}` kept only `5.0`). Because the IR stores
  `linear` as a plain dict and `_resolve_variables` rejects equality-aliased variable orders,
  two aliased labels can never coexist as distinct variables, so rejection is the only
  representable contract. The repair introduces `_fold_linear_term`, which buckets by
  `exact_label_key` and raises `equality alias` on a Python-equal, type-distinct collision;
  both the structured linear construction and the diagonal fold now use it.

## Decisions

1. `program.py` frozenset encoding sorts members with `canonical_variable_sort_key` and then
   encodes, making `encode_variable_label` the single order authority for every frozenset
   payload the decoder re-canonicalizes.
2. `conversions.py` gains module-level `_fold_linear_term(linear_terms, key_index, label,
   coefficient)`; the structured linear items and all diagonal folds route through it. The
   error message names both colliding labels.
3. The linear-construction guard ships in this pass even though the audit scoped the defect
   to the diagonal fold, because the probe demonstrated silent coefficient loss through the
   identical bucket dict; one invariant covers both sites.
4. `_parse_ising` keeps its current linear construction. Its diagonal entries fold into the
   offset without touching labels, and the equality-aliased custom-`Mapping` linear input
   remains a recorded residual for a future hardening pass rather than an unscoped change here.

## Rejected Alternatives

- Importing `model._encoded_label_sort_key` into `program.py`. The public
  `canonical_variable_sort_key` yields the identical order over decoded members without a
  cross-module private import.
- Detecting equality aliases inside the shared `exact_mapping_index` helper. That helper
  validates many mappings whose keys legitimately never collide by equality, and changing its
  semantics would ripple into sample alignment and clamp validation call sites this task does
  not own.
- Representing aliased diagonal labels as two distinct variables. The plain-dict `linear`
  field and the `set`-based uniqueness gate make that state unrepresentable in the current IR;
  the off-diagonal path already rejects, so the diagonal path now matches it.

## Sources Read

- `reference/research-journal/2026-07-19-full-source-correctness-and-optimization-audit.md`
  (defect statements, reproductions, fix directions).
- `src/gibbsiq/program.py` (`_canonical_json`, `_encode_value`, `_decode_label`).
- `src/gibbsiq/model.py` (`_encoded_label_sort_key`, `encode_variable_label`,
  `exact_label_key`, `exact_mapping_index`, `canonical_variable_sort_key`).
- `src/gibbsiq/conversions.py` (`_parse_qubo`, `_parse_ising`, `_resolve_variables`).

## Verification

- Red phase: `test_structured_qubo_diagonal_alias_rejected`,
  `test_qubo_alias_labels_from_pair_mappings_rejected`, and
  `test_non_ascii_frozenset_metadata_round_trip` fail at base `cdd0a58` exactly as the audit
  predicts; the exact-fold and typed-variable controls pass before and after.
- Focused run: `python -m unittest` over `test_model_compatibility`,
  `test_thermodynamic_program`, `test_conversion_scenarios`, `test_serialization_contract`,
  `test_stage_01_core_model_compatibility`, and `test_metamorphic_model_properties` passes
  98 tests in 2.095 seconds with 0 skips.
- Full suite: `python -m unittest discover -s test_suite/tests` passes 608 tests with 0 skips
  in 105.882 seconds on CPython 3.13 / Windows 11 (five tests added by this pass).
- Static gates: `python tools/check_markdown_math.py`, `ruff check .`,
  `ruff format --check .`, `mypy src/gibbsiq` (24 source files), and `git diff --check` pass.
- Independent oracle sweep (session scratchpad `verify_remediation.py`, seed 20260721):
  2,000 random structured QUBOs, 24,516 exhaustively enumerated assignments compared against
  direct evaluation of the input dictionaries without any Gibbsiq conversion helper; maximum
  absolute error `5.329e-15` at tolerance `1e-9`. A ten-member mixed-type frozenset payload
  (non-ASCII strings, bytes, numeric aliases, nested tuple/frozenset) round-trips and produces
  byte-identical canonical JSON with SHA-256
  `44a7827cd46c305be3a3877a2c16c2d9dc559d0708072d0ddcdebc943e1a226b` under
  `PYTHONHASHSEED=1` and `PYTHONHASHSEED=31337`.
- Both audit reproductions now behave per contract: the non-ASCII frozenset round trip
  succeeds, and the diagonal alias inputs raise
  `QUBO label 1.0 is an equality alias of linear label 1`.

## Follow-Up

- `TM-IMP-001` is the next dependency-ready task and starts from this repaired base.
- Residuals from the 2026-07-19 audit remain open and unclaimed: the optional
  `tanh(epsilon/2)` quantization bound tightening (equation audit first), the
  `paper_pair_tau_proxy_seconds` field rename, knapsack witness difference-code alignment,
  `PROGRAM_SCHEMA_VERSION` placement in `__all__`, and the `_parse_ising` custom-`Mapping`
  linear alias hardening noted above.
