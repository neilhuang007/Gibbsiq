# 2026-07-14 - Communication Contention And Complexity Correction

## Paper Hook

This correction feeds the thermodynamic-roofline methods and limitations sections. It records
why a worst-partition-pair communication number cannot stand in for aggregate shared-link load,
and turns that failure into an anti-overclaiming regression fixture.

## Correction Scope

This entry supersedes the latency/feasibility interpretation and zero-traffic representation
described in `2026-07-14-aadit-communication-profiler.md`. The paper pin itself was correct:
the implementation reproduced Aadit et al.'s `C_max ~= 50.8` and `eta ~= 305` for the declared
pair. The incorrect step was treating the paper's maximum single-pair proxy as a communication
bound for a whole mapping. The first implementation also emitted every zero-demand unordered
pair and materialized each pair's route. For a no-edge `K`-partition chain, that stored
quadratically many pair rows and cubically many route-index elements despite having no traffic.

The failed interpretation is retained here rather than hidden. It was found by an independent
adversarial audit after the initial focused tests passed. Those tests reproduced one equation but
did not contain a shared-link-contention counterexample or a large no-edge representation test.

## Corrected Contract

EVAL-EQ-018 was amended before the production implementation. For active unordered pairs only,
the Aadit pair-route quantities remain

```text
b_ab = max(b_(a->b), b_(b->a))
C_ab = b_ab * d_ab / P_ab
C_max = max C_ab
```

For physical link `ell`, the profiler now independently accumulates

```text
Q_ell = sum_(active pairs routed over ell) b_ab
L_ell = Q_ell / P_ell
L_max = max L_ell
W_composite = max(C_max, L_max).
```

`Q_ell` and `L_ell` are exact under the declared `max_directed` accounting policy. They are not
a packet or circuit schedule. The clock-shaped values are named `*_proxy`: the paper pair proxy,
the aggregate-link serialization proxy, and a composite proxy obtained from their maximum. The
composite uses `max`, not a sum, because the two diagnostics account for overlapping work and a
sum would double count without a scheduling model. The composite is not asserted to be a measured
latency, a latency bound, a feasible schedule, or a hardware-frequency limit.

Exact small-chain search now minimizes

```text
(W_composite, L_max, C_max, C_tot, canonical_partition_order)
```

using rational comparisons. Its optimality statement applies only to that declared diagnostic
objective over permutations of the supplied partition and pin sequence.

## Independent Counterexample

The regression uses ten one-vertex partitions in physical slots `0..9`. Every partition in slots
`0..4` interacts with every partition in slots `5..9`, all nine physical links have one usable
pin, `N_color = 2`, and `f_comm = 2`. There are 25 active unordered pairs.

- The farthest pair spans nine links, so `C_max = 9` and the paper pair timing proxy is
  `2 * 2 * 9 / 2 = 18`.
- The exact per-link boundary-bit totals are `(5, 10, 15, 20, 25, 20, 15, 10, 5)`.
- Central link 4 therefore has `L_max = 25`; its aggregate-link and composite timing proxies are
  `2 * 2 * 25 / 2 = 50`.
- Independent summation over all 25 pair distances gives `C_tot = 125`.

This fixture proves that `C_max` can be strictly smaller than shared-link aggregation. It does not
claim that 50 is realized latency; arbitration, duplex semantics, headers, buffering, pipelining,
and inter-link overlap are unspecified.

## Complexity And Audit-Identity Decisions

1. Only pairs with positive boundary demand receive pair rows or routes. A no-edge report stores
   `K` partition summaries, `K-1` physical-link rows, and scalar possible/active pair counts.
2. Every physical link receives one aggregate-load row, including a zero-load row. This is linear
   target-topology metadata and makes missing links distinguishable from zero traffic.
3. Distinct partition labels with identical canonical `(module, qualname, repr)` keys are rejected.
   Numeric proxy optimality would survive such a collision, but deterministic tie-breaking and
   serialized audit identity would not.
4. Clock scaling is performed with exact rational arithmetic before finite-binary64 reporting.
   Extremely large color counts now raise a controlled `ValueError`, not a raw `OverflowError`.
5. Caller labels remain embedded objects in the in-memory result, and target parameters are not
   composed with `TSUSpec`. The result is therefore not claimed to be detached, immutable in the
   deep-object sense, or self-contained provenance. That integration is deferred.

Rejected alternatives included retaining zero pair rows for matrix-like convenience, summing the
pair and link proxies, continuing to expose `tau_comm`/`f_pbit_max` names, and calling the maximum
of the two diagnostics a conservative bound. Each would make either complexity or semantics less
honest than the available evidence permits.

## Remaining Limitations

- The zero-traffic case is linear, but a dense active partition graph can still materialize
  `O(K^2)` active pair rows with `O(K)` route-index tuples, for `O(K^3)` route metadata in the
  worst case. Replacing explicit routes with span endpoints is a future representation change,
  not a performance claim made by this tranche.
- Canonical partition ordering uses `(module, qualname, repr)`. Equal keys for distinct labels are
  rejected within a run, but user-defined `repr` output can contain process-specific addresses or
  other unstable content. Cross-process audit identity therefore requires caller-supplied stable
  labels or a future explicit label-serialization contract.
- A one-partition exact search evaluates its sole order and reports no reversal reduction. The
  reversal quotient is meaningful only for reflection-symmetric chains with `K >= 2`.
- The scheduling and provenance limitations above remain: link overlap and arbitration are not
  modeled, caller labels remain embedded in memory, and the result is not composed with `TSUSpec`.

## Source And Artifact

Primary source: Navid Anjum Aadit et al., "Programmable Probabilistic Computer with 1,000,000
p-bits," arXiv:2606.25313v1, Supplementary Sections S4-S5,
https://arxiv.org/abs/2606.25313.

Local source: `reference/05-theory/papers/aadit-2026-million-pbit.pdf`, 25,492,691 bytes,
SHA-256 `56475AD7733BC5EB8E58E4435B7C549E2D1E26C76EDE406D693C8C273949F268`.
No stochastic sample, benchmark corpus, or measured hardware artifact was generated by this
correction.

## Verification

Focused behavioral command:

```powershell
$env:PYTHONPATH = "src"
python -m unittest test_suite.tests.test_communication_profile `
  test_suite.tests.test_public_api_thermomap -v
```

Result after the final formatter pass: 25 tests ran and passed. The 23 communication tests include
the paper pin, central-link counterexample, 400-partition no-edge bounded-row regression, canonical
label-key collision, controlled huge-color failure, the one-partition reversal-metadata regression,
exact permutation search, JSON safety, and input/numeric guards. The two public-package tests
exercise the reviewed end-to-end analysis path.

Static and document commands:

```powershell
python -m ruff check src/gibbsiq/__init__.py src/gibbsiq/communication_profile.py `
  test_suite/tests/test_communication_profile.py test_suite/tests/test_public_api_thermomap.py
python -m ruff format --check src/gibbsiq/__init__.py src/gibbsiq/communication_profile.py `
  test_suite/tests/test_communication_profile.py test_suite/tests/test_public_api_thermomap.py
python -m mypy src/gibbsiq/__init__.py src/gibbsiq/communication_profile.py
python tools/check_markdown_math.py
git diff --check -- reference/08-evaluation/equation-audit.md `
  src/gibbsiq/__init__.py src/gibbsiq/communication_profile.py `
  test_suite/tests/test_communication_profile.py test_suite/tests/test_public_api_thermomap.py `
  reference/research-journal/2026-07-14-communication-contention-correction.md
```

Final reviewed-file checksums after formatting:

| Path | SHA-256 |
| --- | --- |
| `reference/08-evaluation/equation-audit.md` | `78427E2A0BD23C02A14CC103987EB0BAD92F8A0E14EFBF5C6421767CF5A290C5` |
| `src/gibbsiq/communication_profile.py` | `4DE7C768AEB643B095EBC42BA98135AD8DDA36C7F9DC22582357167C990DDAA9` |
| `test_suite/tests/test_communication_profile.py` | `88F9C9274FAB596193A83226F60FC4B02AB769205204533B132D259B89F188D6` |

The root integrator owns the repository-wide test run; this entry claims only the commands above.
