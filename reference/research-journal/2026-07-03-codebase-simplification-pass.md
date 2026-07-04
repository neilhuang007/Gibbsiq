# 2026-07-03 — Full-package simplification and convention pass

## Context

A structured quality review of `src/gibbsiq` (10 modules, ~2,800 lines) ran five
parallel review lenses — reuse/duplication, simplification, efficiency,
altitude (design depth), and Python conventions/architecture — with every
finding re-verified by the session lead against the source before application.
The baseline suite (265 tests, THRML/arviz stack installed) was green before
the first edit and green after the last. The review confirms the architecture
is a one-directional DAG (`model` → {`conversions`, `result`, `blocks`,
`diagnostics`} → `thrml_runtime`; `benchmark_oracle` standalone →
{`benchmark_bridge`, `evaluation`}) and keeps that structure unchanged.

## Decisions

Applied, all behavior-preserving (serialized JSON, fixtures, frozen `rhat`
keys, and the public `__all__` surface are untouched):

- `thrml_runtime`: warmup segments now build each `(ebm, program)` pair once
  (the first segment's EBM previously lowered twice — once discarded for the
  program list, once for the init EBM); the dead per-segment `beta` tuple slot
  is gone; `_Lowering` stores `jax`/`jnp`/`thrml_models` once and drops the
  unused `_thrml` attribute; the edgeless-EBM class cache uses
  `functools.lru_cache` instead of a module global.
- `diagnostics`: `_split_rows_for_rhat` and `_zero_within_status` consolidate
  the identical rectangularize/guard/split prep and the W==0 status selection
  shared by both R-hat variants; `ess_mean` gains the module's established
  `public(chains) = core(rows)` split so `energy_section` rectangularizes
  once; the weighted pairwise Hamming distance in `diversity_section` is
  computed by per-position value grouping — at each position the differing
  read pairs number (total² − Σ_v W_v²)/2 — which is integer-exact and
  identical to the explicit pairwise sum while reducing O(states²·variables)
  to O(states·variables). EVAL-EQ-011 semantics and fixture outputs are
  byte-identical; only the summation grouping changed.
- `conversions`: `_finish` returns the sparse linear dict and
  `IsingModel.__post_init__` remains the single owner of densification and the
  finite check; two unreachable defensive branches fell (`_ordered_pair`'s
  not-in-index arm and the `10**9` sort sentinels — `_resolve_variables`
  validates every pair member first); `_vartype_name` reads the attribute
  once; `_complete_linear` was inlined and removed.
- `evaluation`: `compare_values` threads the mapping key explicitly
  (keyword-only `key` parameter) and drops the `path.rsplit` round-trip that
  re-derived it from the formatted breadcrumb; `compare_unordered_lists` uses
  `collections.Counter`; `Difference.to_json` is renamed `to_dict` to match
  `IsingModel.to_dict`/`SampleResult.to_dict`; the unused `sys` import fell.
- `result`: `from_model` materializes samples once and leaves the defensive
  per-sample copy to `__post_init__`.
- `benchmark_oracle`: `VerifyResult`/`VerifyFn` are `TypeAlias` declarations
  with a precise callback signature (`Callable` now from `collections.abc`);
  `ising_energy` carries an explicit comment that its independence from
  `IsingModel.energy` is the verification guarantee and must not be
  consolidated.
- Dataclasses `IsingModel`, `SampleResult`, `SamplerConfig`, `BlockPartition`,
  and `Difference` are `frozen=True, slots=True` (no `__dict__`/`vars()`
  consumer exists in the repository).
- Packaging: `src/gibbsiq/py.typed` ships per PEP 561 with the matching
  `[tool.setuptools.package-data]` entry; the version is single-sourced from
  `gibbsiq.__version__` via `[tool.setuptools.dynamic]`.

## Rejected Alternatives

- Consolidating `benchmark_oracle.ising_energy`/`_normalize_spins` with
  `IsingModel.energy`/`sample_to_spin`: the oracle recomputes objectives from
  raw fixture input precisely so an IR sign or offset bug cannot
  self-consistently pass verification. The duplication is the moat; the code
  now says so at the site.
- Unifying `evaluation.Difference` with the oracle's `_diff` dict factory in a
  shared record module: the two comparison engines are deliberately decoupled,
  the record shape is five keys, and a shared module would exist only to
  preserve a decoupling that is currently free.
- Threading rectangular rows through the public diagnostics section builders:
  each section function keeps an independently callable contract; the passes
  are O(n) over ≤ thousands of floats, and the one redundant pass inside
  `energy_section` is the only one removed.
- Decomposing `THRMLSampler.sample` (~150 lines): the linear phase narrative
  (lower → schedule → run → decode → traces → metadata → diagnostics) reads
  better than helpers threading ten locals; revisit when parallel tempering
  grows the schedule section.
- Extracting a formulations module for the Lucas-2014 encoders now living in
  `compile_fixture`, and table-driving the bridge's per-family dispatch to
  mirror `FAMILY_SPECS`: correct end state, but the encoders have one consumer
  today and the extraction belongs to the penalty/one-hot encoding layer work
  (Stage 4/5) that adds knapsack and TSP; doing it twice would churn.
- A split-argument `compile_qubo(linear, quadratic, offset=...)` symmetric
  with `compile_ising`, and a cached adjacency view on `IsingModel` for
  `local_field`/`color_blocks`/`_Lowering`: both are additive API decisions
  deferred until a second consumer exists.

## Verification

- `python -m unittest discover -s test_suite/tests`: 265 tests, OK, before and
  after every batch of edits (three full runs).
- Evaluator CLI smoke run on the example candidate reproduces the pinned
  contract: 12 passed, 27 benchmark fixtures missing, exit code 1.
- `pip install --dry-run --no-deps .` resolves `gibbsiq-0.1.0` from the
  dynamic version.
- The Hamming rewrite is provably integer-identical: same-state read pairs
  share every position, so per-position value grouping counts exactly the
  pairs the explicit double loop weighted.

## Follow-Up

- When the penalty/one-hot encoding layer lands, move the family→IR encoders
  out of `benchmark_bridge.compile_fixture` into a formulations module beside
  `conversions.py` and table-drive the bridge dispatch to mirror
  `FAMILY_SPECS`.
- `MAX_WITNESSES = 8` is duplicated between `benchmark_bridge` and
  `tools/generate_ground_truth.py` (the generator stays import-independent by
  design); keep the values in sync on future edits.
