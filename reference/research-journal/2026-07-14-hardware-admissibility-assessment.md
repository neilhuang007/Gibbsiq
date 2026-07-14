# Direct-Target Hardware Admissibility Assessment

**Date:** 2026-07-14
**Paper hook:** Methods section and target-admissibility table: separates certified logical
constraints from unevaluated physical mapping claims and records quantization fidelity without
inventing a hardware score.

## Question

Can the implemented `IsingModel`, deterministic block coloring, `TSUSpec`, and fixed-point
quantization analysis be composed into a conservative direct-target decision without claiming a
physical mapping, energy/latency model, or mixing result that the public target facts cannot
support?

## Decision And Rejected Alternatives

1. The overall vocabulary is exactly `admissible`, `inadmissible`, or `conditional`; individual
   checks use `pass`, `fail`, or `not_evaluated`.
   - Rejected: a scalar “TSU suitability” score. No calibrated target, workload corpus, or
     evidence-weighted scoring rule exists, so such a number would be arbitrary.
2. Capacity, maximum logical degree, color phases, coefficient format, and topology/locality are
   named checks with their observed value, limit, reason, and available target provenance.
   - Rejected: silently filling missing Z1 facts with values from projections or marketing copy.
3. A deterministic coloring is constructive evidence when its count is within a phase limit.
   DSATUR itself is only a color-count upper bound. The result is labeled exact only when that
   constructive upper bound meets a separately valid lower bound: zero/one colors for edgeless
   graphs, two for a graph with at least one edge proven bipartite, three for a non-bipartite graph
   colored with three colors, or `n` for `K_n` by its clique bound.
   - Rejected: declaring a DSATUR count to be the chromatic number merely because the heuristic is
     deterministic.
   - Rejected: declaring a model inadmissible whenever DSATUR exceeds the phase limit. With a gap
     between lower and upper bounds, the correct result is `not_evaluated`.
4. A non-edgeless model has `topology_locality=not_evaluated` because the current `TSUSpec` has no
   physical topology, neighbor offsets, placement, routing, or communication constraints. An
   edgeless model passes this check vacuously.
   - Rejected: treating graph coloring as physical placement or routing.
5. Fixed-point analysis is performed on `beta*h` and `beta*J`, using the audited quantization
   equations in `reference/08-evaluation/equation-audit.md`. Reject overflow and saturation become
   explicit hard-failure evidence rather than escaping as opaque exceptions.
   - Rejected: accepting saturation as ordinary rounding; it proves that at least one requested
     effective coefficient lies outside the declared range.
   - Rejected: calling in-range rounding `pass` when it changes the model. `TSUSpec` declares no
     acceptable coefficient-error or distribution-error threshold, so a non-exact representation
     is `not_evaluated` and the assessment remains conditional. The analytic bounds and optional
     exact comparison are still returned for a later policy decision.
6. Exact distribution comparison is included only when `variable_count <= max_exact_variables`.
   Above the cap, scalable analytic coefficient, local-logit, state-log-weight, and total-variation
   bounds remain available.
   - Rejected: unbounded state enumeration inside an ostensibly scalable assessment.
7. Serialized quantization evidence is label-free. It reports aggregate and exact error metrics
   but does not emit arbitrary user labels, which may be hashable without being JSON encodable.
   - Rejected: using `repr(label)` as an identity-preserving serialization; it is not a stable or
     reversible label contract.
8. Graph facts use adjacency lists and one traversal, requiring `O(|V|+|E|)` working space. No
   dense adjacency matrix, all-pairs distance, ESS/joule, energy, or latency estimate is computed.

No energy-sign, offset, Gibbs-conditional, or quantization equation convention changed, so the
equation audit did not require a convention edit.

## Implementation

- `src/gibbsiq/hardware_assessment.py`
  - immutable `GraphFacts`, `AdmissibilityCheck`, `QuantizationEvidence`, and
    `HardwareAssessment` records;
  - `assess_target_admissibility(...)`;
  - variable/edge counts, maximum and mean degree, degree histogram, component count/sizes,
    density, bipartiteness, completeness, block sizes, lower-bound evidence, and coloring-bound
    classification;
  - explicit aggregation rule: any known failure dominates; otherwise any unevaluated check makes
    the result conditional; otherwise the target is admissible.
- `test_suite/tests/test_hardware_assessment.py`
  - path, rectangular grid, complete graph, isolated variables, capacity/degree boundaries,
    missing target facts, a DSATUR/lower-bound gap, reject overflow, saturation, beta-scaled
    binary64 overflow, saturation evidence surviving a later analytic-bound overflow, missing
    quantization tolerance, exact-enumeration cap, opaque labels, immutability/detached JSON, input
    validation, and a 20,000-variable sparse-path smoke test.

## Negative Results And Audit Corrections

1. The first test draft used an even-rim wheel while describing a four-color wheel. An even-rim
   wheel is three-colorable. The fixture was corrected to a five-vertex odd rim plus hub, whose
   deterministic schedule uses four colors while the deliberately cheap recorded lower bound is
   three.
2. The first graph-evidence draft labeled `K5`'s DSATUR result only as an upper bound. Independent
   code audit correctly identified that the five-color construction matches the five-vertex clique
   lower bound, certifying the count as exact. The classification now compares every constructive
   count with the recorded valid lower bound.
3. The first coefficient-format draft passed all in-range rounded coefficients. Audit rejected that
   wording because the target contract has no fidelity tolerance. Only exact representation now
   passes; non-exact in-range rounding remains conditional with quantitative evidence.

## Verification Evidence

Focused test command:

```powershell
$env:PYTHONPATH = "src"
python -m unittest test_suite.tests.test_hardware_assessment
```

Observed result after the audit corrections:

```text
.................
----------------------------------------------------------------------
Ran 17 tests in 0.083s

OK
```

Static checks:

```powershell
python -m ruff check src/gibbsiq/hardware_assessment.py test_suite/tests/test_hardware_assessment.py
python -m ruff format --check src/gibbsiq/hardware_assessment.py test_suite/tests/test_hardware_assessment.py
python -m mypy src/gibbsiq/hardware_assessment.py
```

Observed results: Ruff lint passed, both files were already formatted after the final change, and
mypy reported `Success: no issues found in 1 source file` (plus the repository's pre-existing note
about an unused `dimod.*` override).

Adjacent-contract test command:

```powershell
$env:PYTHONPATH = "src"
python -m unittest test_suite.tests.test_block_partition `
  test_suite.tests.test_hardware_specs `
  test_suite.tests.test_quantization `
  test_suite.tests.test_hardware_assessment
```

Observed result after the final extreme-saturation case: 63 tests ran in 0.098 seconds and passed.

The 20,000-variable path fixture has 19,999 edges, one component, maximum degree two, two blocks of
10,000 variables, and completed as part of the 0.083-second focused run. This is a smoke check for
accidental quadratic allocation, not a hardware throughput benchmark.

The root agent owns the full-suite run because concurrent agents are editing shared pre-existing
modules and tests. No full-suite result is claimed in this entry until that independent run is
recorded by the integrator.

Final code-evidence checksums after formatting and the recorded audit corrections:

| Path | SHA-256 |
| --- | --- |
| `src/gibbsiq/hardware_assessment.py` | `E26F37A77830F5A360BA0BDCE98C0EFE97F48E144CD20C3298FAFFEBA974BC71` |
| `test_suite/tests/test_hardware_assessment.py` | `7548B6A7CC40F82101BF7B75240024205ADF01B612CA3BD6173EDE51ABE9A088` |
