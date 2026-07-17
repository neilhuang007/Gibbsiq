# 2026-07-17 - TM-IR-001 Reconciliation, Adversarial Hardening, And Closure

## Paper Hook

This closure supplies a worked anti-echo example for the methods and evaluation sections: the
compiler projection is accepted only after an independent enumerator recomputes every source
energy, typed-identity traps falsify superficially valid Python mappings, and the serialized
evidence is regenerated and checked by hash. It also supplies the logical-IR box immediately
upstream of the future factor-JSON and NetworkX frontend in the compiler architecture figure.

## Context And Source-Of-Truth Reconciliation

The user asked for the next research implementation after reading `Project_GOAL.md` and using
`reference/` as the knowledge base. No application database was present: a repository-wide
file scan found no `.db`, `.sqlite`, `.sqlite3`, or `.sql` file, and no application database
configuration outside `reference/`. In this task, “database” therefore means the repository's
versioned source, tests, raw artifacts, roadmap, and research corpus.

The live ledger authorized exactly one bounded task, `TM-IR-001`. Startup reconciliation found
that commit `35a2ba3fa6bccc90bf33bc41f9838a8036bd339e` already tracked the main program-envelope
implementation while `NEXT_TASK.md` still described it as an uncommitted working-tree
candidate. The executable source outranks stale status prose under the runbook. I preserved the
human/concurrent commit, audited the actual code at that base, and treated this pass as the
required adversarial hardening, evidence refresh, and authorized closure commit. `Project_GOAL.md`
and three unrelated concurrent audit journals remain outside this task's commit.

The product intent remains broader than this task. `Project_GOAL.md` defines ThermoMap as a
mixing-aware compiler from THRML/Ising/QUBO/NetworkX/factor graphs through a target-independent
thermodynamic IR to lowering, mapping, verification, and ESS-per-joule profiling. Section 11.1
separates the logical program from `TSUSpec`; Section 11.2 then names NetworkX and factor-graph
JSON as frontends. This task closes only the logical envelope. It does not add target facts,
physical coordinates, placement, routing, schedules, calibrated costs, or a new sampler.

## Engineering Difficulty Points And Resolutions

### H1. Python equality is weaker than the IR's typed identity

Python treats `True == 1`, and that aliasing recurs inside tuples and frozensets. The existing
top-level checks therefore did not protect a categorical domain containing `(1,)` from a sample
or clamp containing `(True,)`. The correction routes category indexing, clamp comparison, and
duplicate/conflict detection through recursive typed keys and recursive exact equality. Tests
cover sample lookup, unary tables, direct clamps, and conflicting ordered clamp records.

Rejected: coercing values through equality or hashing alone. That would let a Boolean
observation silently select an integer state and would make public/blind label mutations
disagree.

### H2. Projection must preserve energy, offset, and the zero-variable case

The production projection follows EVAL-EQ-023. Ising fixed-free interactions become surviving
fields; fixed linear and fixed-fixed interactions become offset contributions. Categorical
fixed-free tables become unary slices; fixed unary and fixed-fixed tables become offset
contributions. A fully clamped program remains the same model type with no variables and its
complete energy in the offset.

The closing oracle does not call `program.project()` or `model.energy()` on its expected path.
It merges each free assignment with the declared clamps and independently sums the original
offset and source factors. Forty-two deterministic programs and 248 assignments pass at
`rel_tol=0.0`, `abs_tol=1e-9`; maximum absolute error is `0.0`.

Rejected: reusing projected coefficients as expected values. That would echo a dropped offset
or wrong endpoint orientation on both sides of the test.

### H3. Immutable reconstruction must not change metadata container semantics

`thaw()` intentionally turns tuples and sets into JSON-like lists. Using it as an intermediate
for `project`, `with_clamps`, `relabel_variables`, or `SampleResult.from_program` therefore
changed set-shaped evidence even though the destination constructor froze it again. The fix
passes detached outer dictionaries containing the already frozen children; the receiving
constructor performs the defensive recursive copy. Set-shaped model, program, and observation
metadata now survives projection, reconstruction, relabeling, and result integration.

Tuple/list metadata intentionally normalizes to the program wire format's `list` record because
both become `FrozenSequence` at the public boundary. Tuple labels, tuple mapping keys, and tuple
members of frozensets retain typed label encoding. A coordinator audit initially suspected a
decoder asymmetry; tracing the freeze boundary showed that generic metadata `tuple` and `set`
records were unreachable and noncanonical. Those dead encoder branches were removed rather than
broadening the decoder, and a regression pins the canonical behavior including nested integer
versus Boolean values.

Rejected: accepting every decoder tag the old private encoder could construct. A payload that
the public serializer can never emit is not a canonical program record, and accepting it would
make `restored.to_dict()` differ from its input.

### H4. A deterministic typed wire format must fail closed

The generic decoder previously accepted lossy or noncanonical label records, including decimal
integer strings such as `"01"` and frozensets whose typed children collapse under Python
equality. Label positions, domains, clamp values, metadata keys, and frozenset members now reuse
the canonical `IsingModel` label decoder and must re-encode byte-for-byte to the same typed
record. Extra fields, noncanonical numbers, duplicate alias members, and unsupported tags fail.

The emitted JSON is deterministic for this schema, but it is not labeled RFC 8785 JCS. RFC 8785
has its own ECMAScript number serialization and property-ordering requirements; the program
instead uses explicit decimal integer strings, hexadecimal floats, positional records, and
sorted typed keys.

Rejected: JSON object keys for logical labels. NetworkX's own node-link documentation warns
that attribute keys are converted to strings for JSON, which is incompatible with Gibbsiq's
lossless `1` versus `"1"` and recursive typed-label contract.

### H5. Relabeling must preserve categorical normalization evidence

`CategoricalModel.reversed_pair_count` records how many caller pair tables arrived in reversed
endpoint order. Reconstructing every relabeled pair canonically silently reset that evidence to
zero. Relabeling now reconstructs the recorded number of canonical pair positions in reversed
orientation, transposes those tables, and lets the model constructor canonicalize them again.
The energy tables and serialized canonical payload are unchanged while the representable count
survives.

The permanent regression uses three canonical pair positions supplied reversed, forward, and
reversed; it checks identity-payload equality, count `2`, and all 16 energies after tuple-label
renaming. The schema stores only the aggregate count, not which original pairs were reversed.
Per-factor orientation history cannot be recovered from this schema and is recorded as a
limitation rather than invented.

### H6. Validation must be atomic before reconstruction

The envelope validates unknown, duplicate, conflicting, aliased, and out-of-domain clamps
before projecting. Serialization validates canonical label records and duplicate positional
records before constructing dictionaries that could erase evidence. This follows the useful
validate-first/new-destination pattern in Qiskit Optimization's substitution implementation,
but Gibbsiq retains arbitrary supported hashable labels and explicit lineage.

Rejected: dimod's in-place `fix_variable` as the program object. It is a useful algebraic
reference, but mutation removes the original unclamped carrier and supplies neither the logical
observation contract nor Gibbsiq's transformation lineage.

### H7. Source lineage and runtime state are different boundaries

Factor identities remain tied to source-model positions while projected destination positions
refer to the compact free-variable model. Collapsed factors remain transformation rows even
when their contribution lands in the offset. THRML's sampling programs are a later executable
boundary with blocks, schedules, and clamp arrays; they are not the durable target-independent
program envelope.

MLIR `FusedLoc` was the closest compiler precedent found for preserving multiple source
locations when rewrites would otherwise lose them. It influenced the lineage reasoning only;
no MLIR code or schema was copied. A future cross-system provenance export could map the same
records to W3C PROV, but that is not required for this task.

### H8. External code reuse requires both semantic fit and a clear license

The research request explicitly asked for similar programs whose code could be copied. The
audit found useful precedents but no implementation that satisfied typed identity, immutable
reconstruction, offsets, zero-variable constants, logical coordinates, and factor lineage as
one contract. No third-party source code was copied or adapted.

QUBOLite's partial assignment is the closest QUBO-specific mechanism and its paper explicitly
returns a reduced QUBO plus a constant. At reviewed source pin
`cbe57e0bea68e9f751f8591e3ba0254030ac5965`, the repository tree and package metadata exposed
no license declaration. That is an audit inference, not a legal opinion; it is sufficient to
prohibit code copying here. Only the published mechanism comparison was retained.

## Similar-System And License Audit

All sources were accessed 2026-07-17. Pins prevent a moving repository from silently changing
the reviewed implementation.

| System | Reviewed source | License finding | Decision for Gibbsiq |
| --- | --- | --- | --- |
| dimod 0.12.22 | [repository at `3ecf9cc`](https://github.com/dwavesystems/dimod/tree/3ecf9cc24b63841b0e2a495ff0cb196dcbe0a0cb), [`fix_variable` docs](https://docs.dwavequantum.com/en/latest/ocean/api_ref_dimod/generated/dimod.binary.BinaryQuadraticModel.fix_variable.html) | Apache-2.0 | Algebra and compatibility reference only; its mutable BQM operation is not the durable envelope. |
| THRML 0.1.3 source snapshot | [repository at `7f40e5c`](https://github.com/extropic-ai/thrml/tree/7f40e5cbc460a4e2e913557a6c2a21d9155c4db6), [Ising API](https://docs.thrml.ai/en/latest/api/models/ising/), [block sampling](https://docs.thrml.ai/en/latest/api/block_sampling/) | Apache-2.0 | Future runtime adapter boundary; do not bind the logical IR to blocks or schedules. |
| NetworkX 3.6.1 | [`node_link_data`](https://networkx.org/documentation/stable/reference/readwrite/generated/networkx.readwrite.json_graph.node_link_data.html), [license](https://github.com/networkx/networkx/blob/main/LICENSE.txt) | BSD-3-Clause | Future optional importer; define an explicit Gibbsiq schema because node-link attribute keys stringify. |
| pgmpy 1.1.2 | [`DiscreteFactor.reduce`](https://github.com/pgmpy/pgmpy/blob/v1.1.2/pgmpy/factors/discrete/DiscreteFactor.py), [license](https://github.com/pgmpy/pgmpy/blob/dev/LICENSE) | MIT | Dense factor slicing precedent only; default mutation and state-name fallback do not fit strict typed identity. |
| Qiskit Optimization 0.7.0 | [`substitute_variables.py`](https://github.com/qiskit-community/qiskit-optimization/blob/0.7.0/qiskit_optimization/problems/substitute_variables.py), [repository](https://github.com/qiskit-community/qiskit-optimization) | Apache-2.0 | Validate-first/new-object precedent; no code copied because its string/index variable and constraint model differs. |
| QUBOLite | [paper, arXiv:2509.21321v1](https://arxiv.org/html/2509.21321v1), [source at `cbe57e0`](https://github.com/smuecke/qubolite/tree/cbe57e0bea68e9f751f8591e3ba0254030ac5965) | No license detected in reviewed tree/metadata | Mechanism comparison only; no copying or adaptation. |
| MLIR | [`FusedLoc`](https://mlir.llvm.org/docs/Dialects/Builtin/#fusedloc) | Apache-2.0 with LLVM exception | Lineage-design inspiration only. |
| JSON/W3C standards | [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html), [RFC 8949](https://www.rfc-editor.org/rfc/rfc8949.html), [W3C PROV-DM](https://www.w3.org/TR/prov-dm/) | Open standards | Bound the deterministic-JSON claim and identify future canonical binary/provenance options. |

Pyro and NumPyro conditioning were also reviewed as runtime observation mechanisms. They were
rejected for this bounded task because conditioning a probabilistic program does not supply the
durable pairwise energy, source-factor, coordinate, and compiler-replay artifact ThermoMap
requires.

## Adversarial Findings And Corrections

The coding worker's claims were treated as leads and the coordinator inspected the actual diff.
Four falsified contracts produced corrections:

1. recursive `(True,)`/`(1,)` aliases in categorical domains, samples, unary tables, and clamps;
2. noncanonical or collapsing typed-label records accepted during program decoding;
3. set-shaped metadata changed to list-shaped metadata across reconstruction paths;
4. categorical relabeling discarded `reversed_pair_count`.

The coordinator caught an incomplete first recursive-key patch: lookup used the new exact key
while construction still built the old shallow key. Both sides were corrected before the gate
run. A fresh independent reviewer reported no remaining correctness finding after 4,347
exhaustive energy comparisons across 200 generated categorical models, recursive-label and
serialization attacks, and metadata-shape checks. Because that reviewer used an inline
unretained script, this is supplementary review evidence; the retained generator and public
tests are the closing oracle.

The coordinator separately exercised a three-pair mixed-orientation relabel and recursive label
attack for 21 assertions. An initial handwritten status line called this “20” checks; the
programmatic count was 21 and is the recorded value. The permanent three-pair test replaces the
unretained relabel probe.

## Artifacts And Reproduction

Artifact directory:
`reference/00-roadmap/artifacts/tm-ir-001/2026-07-15-program-envelope/`.

Reproduction command:

```powershell
& .venv/Scripts/python.exe tools/generate_tm_ir_001_artifacts.py --overwrite
```

Configuration: seed `20260715`; RNG `Python random.Random (MT19937)`; 24 Ising and 18
categorical programs; one to five Ising variables; one to four categorical variables with
domain sizes two or three; absolute tolerance `1e-9`; relative tolerance `0.0`. No sampling,
diagnostic, or tuning work occurs in this projection corpus. The environment record captures
CPython 3.13.5, Windows 11, source base `35a2ba3`, and split generator timings.

Final evidence hashes:

| File | SHA-256 |
| --- | --- |
| `manifest.json` | `8faf62c46b2265eb2982737ec4b6cb3eb7dc766138abf8a4b13eed1a8a74d785` |
| `environment.json` | `a64de94a704d2953f40cd2c0df75ce0f350e773734eade0316fad5ef1622bc80` |
| `generation-config.json` | `98bcc9f46fe37d5c895571c1d948c259d04f99e76bae422c62be428aa588198c` |
| `oracle-results.json` | `73b284e1adc80f6165dd54c33bb08677a07c9dd3aa5ce1f1b2907606e6e8e51e` |
| `projection-fixtures.json` | `7b3fa53fdafe5f19918de6a83e25be7992bff85618313bc2430d1076657e3a72` |
| `serialization-fixture.json` | `9a08a1b5731cb8763114a2102ddf269c1614709bcb29f7b91d2991967a84bb47` |
| `source-files.json` | `f9e617d19eda9163dcde6662315eace47e46f6a0e483aeb890834a00270a42fc` |

The nine pinned source/test inputs have aggregate SHA-256
`45c76ad8621d9705e3a3493e8e17cf8915599f04580dacce66369149f3849dd4`.
Two independent generations matched for the five deterministic payloads. The environment and
manifest intentionally include observed timing and therefore are verified by their recorded
hashes rather than asserted identical across runs.

## Verification

Commands run from `E:\projects\Gibbsiq` with the repository virtual environment:

| Command/check | Result |
| --- | --- |
| `python -m unittest test_suite.tests.test_thermodynamic_program` | 31 tests, 0 skips, pass in 0.009 s |
| Seven nearest model/categorical/result/immutability/Inspector/public-API modules | 95 tests, 0 skips, pass |
| `python -m unittest discover -s test_suite/tests` | 603 tests, 0 skips, pass in 89.427 s |
| `python -m ruff check .` | pass |
| `python -m ruff format --check .` | 73 files already formatted |
| `python -m mypy src` | 24 source files, no issues |
| `python tools/check_markdown_math.py` | pass |
| manifest/file/source SHA-256 recomputation | all match |
| deterministic double generation | all five deterministic payloads match |
| `git diff --check` | pass |

The full suite emitted the known ArviZ diagnostic-fixture `RuntimeWarning` for division by an
invalid within-chain variance; the suite still passed, and this task does not alter diagnostic
semantics. Four PowerShell cleanup attempts, including recursive and individually enumerated
`Remove-Item` forms, were rejected by command policy before execution. The final checks used
explicit workspace paths verified with `Resolve-Path`, separate generator calls, hash
comparison, and explicit same-shell directory cleanup; no evidence directory was left behind.

## Decisions And Remaining Limits

1. Close `TM-IR-001` in the commit containing this journal and ledger transition. Git history is
   the authoritative identity because a commit cannot contain its own final SHA.
2. Select `TM-IMP-001` as the next dependency-ready task because the runbook requires the
   earliest ready task in roadmap dependency order. Do not implement it in this commit.
3. Keep the current typed positional program schema rather than adopting NetworkX node-link,
   pgmpy dense factors, Qiskit variable names, or an executable THRML sampling program.
4. Copy no upstream code. Licensed sources remain conceptual/API precedents; QUBOLite is
   mechanism-only because no license was detected.
5. Make no empirical sampler, hardware, performance, or ESS-per-joule claim. This evidence
   verifies logical projection and serialization only.
6. Preserve the aggregate-only limitation of `reversed_pair_count`; a future schema revision
   would be required for per-factor input-orientation history.
7. Preserve `Project_GOAL.md` and unrelated concurrent journals as unstaged coworker inputs.

`TM-IMP-001` must next freeze the factor-JSON schema and optional NetworkX policy before code:
typed node identity, explicit node order, vartype and offset, edge symmetry/duplication,
clamps/coordinates, disconnected nodes, metadata normalization, and a direct source-energy
oracle are the principal engineering gates.
