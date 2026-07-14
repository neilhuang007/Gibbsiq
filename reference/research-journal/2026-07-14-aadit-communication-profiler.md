# 2026-07-14 - Aadit Communication And Chain-Mapping Profiler

## Paper Hook

This entry feeds the methods, hardware-cost model, limitations, and worked-example sections
of a future ThermoMap paper. It contributes an auditable implementation of the distributed
boundary-traffic equations and documents two ambiguities that must be resolved before the
model can support a hardware-performance claim.

## Scope

Implemented a production evaluator for a caller-supplied partition of a canonical
`IsingModel` and a caller-supplied physical chain order. The evaluator computes the
communication metrics in Aadit et al. 2026, Supplementary Sections S4-S5. It does not
partition a graph, place individual variables, route a general network, simulate stale-state
dynamics, or claim a measured TSU clock.

Added:

- `src/gibbsiq/communication_profile.py`;
- `test_suite/tests/test_communication_profile.py`;
- equation contracts EVAL-EQ-018 and EVAL-EQ-019 in
  `reference/08-evaluation/equation-audit.md`.

The module is intentionally not exported from `gibbsiq.__init__` and is not integrated into
`THRMLSampler` in this tranche. API-surface and runtime integration remain separate review
gates.

## Primary Source

Navid Anjum Aadit et al., "Programmable Probabilistic Computer with 1,000,000 p-bits,"
arXiv:2606.25313v1, 24 June 2026, specifically Supplementary Sections S4.1-S4.6 and S5,
equations S.2-S.8.

- URL: https://arxiv.org/abs/2606.25313
- Local PDF: `reference/05-theory/papers/aadit-2026-million-pbit.pdf`
- Bytes: 25,492,691
- SHA-256: `56475ad7733bc5eb8e58e4435b7c549e2d1e26c76ede406d693c8c273949f268`

The PDF was inspected directly, including rendered page structure and layout-aware text from
the supplementary equations. Search transcripts were used only for navigation; the PDF is
the authority.

## Implemented Equations

For each pair of supplied partitions, the implementation computes:

```text
b_(a->b) = unique vertices in a incident to one or more edges into b
b_(b->a) = unique vertices in b incident to one or more edges into a
b_ab = max(b_(a->b), b_(b->a))
d_ab = physical chain hop distance
P_ab = minimum usable-pin count along the complete route
C_ab = b_ab * d_ab / P_ab
C_tot = sum C_ab
C_max = max C_ab
tau_ab = 2 * C_ab / f_comm
tau_comm = 2 * N_color * C_max / f_comm
eta_required = 2 * N_color * C_max
f_pbit_max = f_comm / eta_required
```

For a supplied Potts assignment, the optional evaluator computes equation S.7 using
`abs(J_ij)`, the supplied cluster order, the S.8 near/far kernel, and the quadratic balance
penalty. It returns the interaction and balance terms separately and performs no search.

## Source Critique And Ambiguities

### A1 - The paper's `b_ab` is directionally under-specified

Supplementary S4.1 introduces `b_ab` for an unordered pair while defining it as states sent
from cluster `a` to cluster `b`. On a general graph, the number of unique boundary vertices
on the two sides can differ. Later equations sum only over `a < b`, so the text does not say
which directed count to use.

The implementation exposes both directed counts and uses the explicit policy
`max_directed`. This gives a conservative equal duplex-frame allocation and is invariant to
the arbitrary orientation of the unordered pair. The output says that this is Gibbsiq's
policy, not an interpretation attributed to the authors.

### A2 - The paper's reversal quotient conflicts with its asymmetric pin profile

Supplementary S4.3 states that a six-node chain has `6!/2 = 360` distinct orders up to
reversal. Supplementary S4.6 then declares DSIM-1 link pins
`[54, 30, 54, 26, 54]`, which is not reflection-symmetric. If those capacities remain
attached to indexed physical links, reversing only the partition order can change `P_ab`
and the objective. Reversal is therefore not a cost symmetry for that profile.

The exact search reduces by reversal only when the supplied pin tuple is palindromic. It
evaluates all `K!` orders otherwise and records that the reversal reduction was invalid. The
paper's DSIM-1 numerical example is evaluated at its stated order; it is not used to claim a
360-class exact search.

## Decisions And Rejected Alternatives

1. **Count unique directed boundary vertices.** Rejected cut-edge counts because S4.1 says
   one state bit is sent per boundary p-bit; repeated edges from one source do not require
   repeated copies of that state in this model.
2. **Collapse with `max_directed`.** Rejected selecting whichever direction happened to be
   named first because that makes results depend on arbitrary partition labels. Rejected
   summing the directions because the paper models duplex transfer and then uses one
   `b_ab`, not a serialized sum of both directions.
3. **Require exact partition coverage.** Rejected silently dropping, duplicating, or accepting
   unknown variables because every boundary count would then be uninterpretable.
4. **Accept a supplied chain mapping only.** Rejected writing a homemade partitioner or node
   placer: Aadit et al. use METIS/KaHIP and a Potts optimization method, neither of which can
   be reproduced faithfully by an undocumented local heuristic.
5. **Use the route's minimum usable pins.** Rejected endpoint or average pin counts because
   S4.1 explicitly defines the multi-hop bottleneck as the narrowest link.
6. **Use exact rational objectives in permutation search.** Rejected float tie-breaking because
   `b*d/P` is rational and exact comparison is inexpensive at the hard `K <= 6` limit.
7. **Refuse search beyond six partitions.** Rejected an unvalidated greedy fallback. A
   deterministic heuristic could be useful later, but it must be labeled unproven and
   benchmarked independently before landing.
8. **Apply reversal reduction only when valid.** Rejected blindly copying the paper's `K!/2`
   statement onto heterogeneous indexed links because doing so can discard the optimum.
9. **Serialize no-traffic frequency as null plus status.** Rejected IEEE infinity because
   JSON permits it only as a non-standard extension. Rejected numeric zero because the
   communication equation is inactive, not a zero-frequency constraint.
10. **Reject numerical underflow and overflow.** Rejected converting a mathematically positive
    cost or time to serialized zero, which could falsely classify real traffic as absent.
11. **Evaluate Potts S.7 but do not optimize it.** Rejected calling the evaluator a partitioner
    or SOTA mapper. It is an exact objective calculation for one assignment.
12. **Require explicit clocks, colors, pins, partition, and order.** Rejected speculative TSU
    defaults. The only 100 MHz clock in the paper-value unit test is a declared test input;
    the dimensionless `eta_required` does not depend on that choice.

## Worked Paper Pin

The focused fixture independently builds 660 distinct vertices in partition 4, all incident
to one vertex in partition 6. It therefore records directed demands 660 and 1, conservatively
collapses to 660, and uses the stated chain pins `[54, 30, 54, 26, 54]`:

```text
d_46 = 2
P_46 = min(26, 54) = 26
C_46 = 660 * 2 / 26 = 50.76923076923077
eta_required = 2 * 3 * C_46 = 304.61538461538464
```

These reproduce the paper's rounded `C_max ~= 50.8` and `eta ~= 305`. The fixture does not
claim that the synthetic graph reproduces the paper's proprietary partition; it isolates the
published equation and values.

## Test Evidence

The 18 focused tests independently cover:

- the `b_46`, distance, bottleneck-pin, cost, time, eta, and clock-bound calculation;
- directed unique boundary vertices versus cut edges;
- asymmetric boundary-demand label invariance;
- multi-hop bottleneck pins;
- different reversed-order costs under non-palindromic pins;
- exact `6!/2 = 360` enumeration only on a reflection-symmetric six-slot chain;
- all `K!` orders when reversal is not a symmetry;
- refusal above the declared exact limit;
- disconnected logical components and zero cross-partition traffic;
- single-partition behavior;
- missing, unknown, duplicate, empty, and invalid partition/route inputs;
- finite-result guards, including positive cost/time underflow;
- monotonicity in communication clock, usable pins, and color count;
- arbitrary mixed labels and strict JSON serialization;
- independent hand evaluation of Potts equations S.7-S.8.

## Verification Commands And Results

Focused tests:

```powershell
$env:PYTHONPATH = "src"
python -m unittest test_suite.tests.test_communication_profile -v
```

Result: 18 tests ran in 0.018 seconds and passed.

Static and document checks:

```powershell
python -m ruff check src/gibbsiq/communication_profile.py test_suite/tests/test_communication_profile.py
python -m ruff format --check src/gibbsiq/communication_profile.py test_suite/tests/test_communication_profile.py
python -m mypy src/gibbsiq/communication_profile.py
python tools/check_markdown_math.py
git diff --check -- reference/08-evaluation/equation-audit.md src/gibbsiq/communication_profile.py test_suite/tests/test_communication_profile.py
```

Results: Ruff lint passed; both files were formatted; mypy reported no issues; Markdown math
passed; `git diff --check` passed with only the existing LF-to-CRLF working-copy warning for
the equation audit. The root agent owns the final full-suite run.

## Artifact Checksums

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| `reference/08-evaluation/equation-audit.md` | 38,895 | `c1e196db2352f62b3dddabed7e24a73ce0f058a6019392b25b063aaa0a559eac` |
| `src/gibbsiq/communication_profile.py` | 24,237 | `9736aa6f3ecc6eb42254ee5c0194d7905ca165ae382e52a04fa59a891c2bfdce` |
| `test_suite/tests/test_communication_profile.py` | 20,845 | `bbc9b433c38bffdfab0b0da51f4dd665534a73e790dd42503ef10beb1a1b1de9` |

The checksums pin the reviewed inputs and implementation. The equation-audit checksum covers
the entire shared file, including earlier concurrent contracts EVAL-EQ-016 and EVAL-EQ-017.

## Limitations And Next Gates

- `C_max` is the paper's pair-route cost, not an aggregate per-link contention calculation
  across several pairs. Multiple routes sharing one physical link may require an additional
  link-load model before this becomes a tight hardware bound.
- `max_directed` is an explicit conservative resolution of an under-specified paper symbol;
  it should be revisited if the authors publish their duplex framing convention.
- The model assumes positive fixed usable-pin counts and a connected linear chain. It does
  not cover meshes, switches, packet headers, arbitration, buffering, bit errors, or
  time-varying link capacity.
- The clocking equation is a conservative freshness bound. It does not establish stationary
  distribution accuracy at a given eta; that requires stale-boundary simulation and exact
  small-model comparison.
- The implementation does not report energy or effective samples per joule.
- The Potts calculation evaluates one assignment. A partition optimizer, if added, needs an
  independently verified objective oracle, balance checks, deterministic seeds, resource
  accounting, and comparison to established partitioners.

Next evidence gate: inject delayed/stale boundary states into a small exact model, compare
the implemented stationary behavior with the monolithic target, and distinguish pair-route
cost from aggregate shared-link congestion before using this model in a thermodynamic
roofline report.
