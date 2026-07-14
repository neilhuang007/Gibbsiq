# Fixed-Beta-Zero Hardware-Assessment Correction

**Date:** 2026-07-14
**Paper hook:** Methods limitation and worked boundary case: distinguishes the interaction
topology required by one fixed-temperature program from the topology required by a reusable
temperature schedule.

## Trigger

An adversarial audit found a false-negative boundary case in direct-target admissibility. The
assessment quantized `beta * h` and `beta * J`, but degree, coloring, and topology checks always
used the source model's logical edges. At `beta = 0`, the implemented distribution is uniform and
every effective coupling is exactly zero, yet a logical edge could still cause hard maximum-degree
and color-phase failures.

Concrete pre-correction counterexample:

```text
logical model: two variables, one nonzero J edge
beta: 0
target: capacity 2, maximum degree 0, maximum color phases 1
quantization: exactly representable, exact total variation 0
old assessment: inadmissible (degree 1 and two colors from the source graph)
```

## Convention Change — Equation Audit First

`reference/08-evaluation/equation-audit.md` was updated before production code. For one fixed-beta
configuration, structural feasibility uses

```text
G_beta = (V, E_beta)
E_beta = {(i, j) in E : beta * J_ij != 0}.
```

The only structural simplification certified in this correction is the exact identity

```text
beta = 0  =>  E_beta = empty.
```

Consequences:

- p-bit capacity still counts every variable `|V|`;
- maximum degree is zero;
- one edgeless block contains every variable;
- coupling topology and locality are vacuous;
- fixed-point analysis must independently show zero effective biases/couplings and a uniform law;
- the original logical edge count remains serialized as evidence.

This result certifies one `beta = 0` configuration only. It does not certify a schedule that later
uses positive beta. At positive beta, structural checks continue to use the original nonzero
logical graph. A coupling that happens to round to zero is not removed without a separately
audited quantized-graph and fidelity-acceptance policy.

## Decisions And Rejected Alternatives

1. **Normalize signed zero to `0.0`.** Both `0.0` and `-0.0` select the same certified case and
   serialize canonically.
2. **Retain all variables.** Rejected removing variables because beta zero removes interactions,
   not states in the modeled distribution.
3. **Retain `logical_edge_count`.** Rejected overwriting the source-topology evidence with only the
   effective edgeless summary.
4. **Add an explicit `graph_basis`.** Rejected making consumers infer whether `graph` means source
   or effective topology from beta alone.
5. **Rev the serialized schema to `hardware-assessment-v2`.** Rejected silently changing the
   meaning of the v1 `graph` field at beta zero.
6. **Do not generalize to quantized positive-beta topology.** Rejected deleting rounded-to-zero
   edges because `TSUSpec` has no acceptable distribution-error threshold and the assessment must
   not turn approximation into an unrecorded structural transformation.
7. **Do not claim schedule portability.** Rejected using a beta-zero result as evidence that the
   same placement supports annealing, tempering, or any later positive-beta execution.

## Implementation

- `src/gibbsiq/hardware_assessment.py`
  - added `GraphAssessmentBasis`;
  - added `_fixed_beta_graph_model(...)`;
  - normalizes signed zero;
  - assesses an edgeless effective model only at exact beta zero;
  - records `graph_basis` and `logical_edge_count`;
  - declares the fixed-beta/non-schedule scope in serialized evidence;
  - changes the schema identifier from `hardware-assessment-v1` to
    `hardware-assessment-v2`.
- `test_suite/tests/test_hardware_assessment.py`
  - dense logical graph at `beta = -0.0`: admissible on an edgeless effective graph, exact uniform
    quantization, and strict JSON serialization;
  - capacity remains a hard failure at beta zero;
  - the same structural target at positive beta still fails degree/color checks and cannot inherit
    the beta-zero certificate.

A follow-up wording audit found two stale descriptions left from v1: `GraphFacts` still called its
contents the logical graph, and the vacuous topology check said “edgeless logical model.” Both now
say **assessed fixed-beta interaction graph**; the beta-zero test asserts that user-facing reason.
The internal helper was renamed `_assessed_graph_facts` for the same distinction. The original
logical topology remains separately evidenced by `logical_edge_count`.

No communication profiler, runtime, package export, or ThermoMap status document was edited.

## Verification Evidence

Focused command:

```powershell
$env:PYTHONPATH = "src"
python -m unittest test_suite.tests.test_hardware_assessment
```

Observed result:

```text
....................
----------------------------------------------------------------------
Ran 20 tests in 0.149s

OK
```

Adjacent-contract command:

```powershell
$env:PYTHONPATH = "src"
python -m unittest `
  test_suite.tests.test_hardware_assessment `
  test_suite.tests.test_hardware_specs `
  test_suite.tests.test_quantization `
  test_suite.tests.test_exact_distribution `
  test_suite.tests.test_block_partition
```

Observed result: 78 tests ran in 0.290 seconds and passed.

Independent deterministic exhaustive probe enumerated all 1,099 simple graphs with one through
five vertices. Every graph at beta zero was assessed with zero effective edges, zero maximum
degree, one block, its original logical edge count, exact coefficient representation, and exact
total-variation error zero. All 1,099 cases passed.

Static and document checks:

```powershell
python -m ruff check src/gibbsiq/hardware_assessment.py test_suite/tests/test_hardware_assessment.py
python -m ruff format --check src/gibbsiq/hardware_assessment.py test_suite/tests/test_hardware_assessment.py
python -m mypy src/gibbsiq/hardware_assessment.py
python tools/check_markdown_math.py
git diff --check -- reference/08-evaluation/equation-audit.md `
  src/gibbsiq/hardware_assessment.py `
  test_suite/tests/test_hardware_assessment.py `
  reference/research-journal/2026-07-14-hardware-assessment-beta-zero-correction.md
```

Observed results: Ruff lint and formatting passed; mypy reported no issues; Markdown math passed;
and `git diff --check` passed with only the repository's LF-to-CRLF working-copy warning for the
shared equation-audit file.

One failed verification invocation is retained: `ruff format` was initially passed the Markdown
equation-audit path and refused because Markdown formatting requires Ruff preview mode. It made no
file changes. The command was rerun on the two Python files only and passed.

## Checksums

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| `reference/08-evaluation/equation-audit.md` | 42,005 | `B1476C87FBF038E8BF3F432CA6B147C0EFF101916C5FFDEDFD1E84B3ECA12EAD` |
| `src/gibbsiq/hardware_assessment.py` | 26,865 | `5297CE7A506B9CFC31000E19FB08E4A1A5148E54D7771F42703DFF835374F4A3` |
| `test_suite/tests/test_hardware_assessment.py` | 20,706 | `E0F2C07AFB88C14EFF1404C23FD6925274DE6D49C4BAC67F8992C2C6B7C67CEE` |

The equation-audit file is shared with concurrent contracts; its checksum records the complete
file observed for this verification, while this correction changes only the fixed-beta paragraph
immediately before the EVAL-EQ-017 use statement.

## Remaining Limitations

- A multi-beta schedule needs a separate assessment over every structural regime it uses.
- Positive-beta quantized-graph simplification remains intentionally unsupported.
- This is a logical/effective graph correction, not physical placement or routing evidence.
- The root integrator owns the final full-suite run; no full-suite result is claimed here.
