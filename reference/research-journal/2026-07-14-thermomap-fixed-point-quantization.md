# 2026-07-14 - ThermoMap Fixed-Point Quantization Foundation

## Paper Hook

This entry feeds the methods, numerical-validity, and hardware-assumption sections of the
Thermodynamic Roofline paper. It records the first target-parameterized ThermoMap pass: an
evidence-tagged TSU specification, offset-invariant exact Boltzmann comparison, and a
fixed-point coefficient analysis whose equilibrium-distribution error is independently
checked on small models.

## Context

The public sources do not provide a stable, production Z1 coefficient format, topology, update
time, or energy contract. Hard-coding plausible values would turn an analysis tool into a
marketing-number echo. The implementation therefore separates an Ising program from an
explicit target description and requires a source classification for every supplied target
parameter.

Aadit et al. report three workload-specific formats on a distributed FPGA p-bit system:
`s{4}{1}`, `s{4}{3}`, and `s{4}{6}`. This is useful primary evidence for a fixed-point notation
and for test fixtures, but it is not evidence that an Extropic TSU uses any of those formats.
Jelincic and Walker describe a four-color, degree-12 codon workload and give modeled TSU
energy estimates. Those workload and model values were reviewed for architecture context but
were not installed as target defaults.

The canonical project energy remains

```text
E(s) = offset + sum_i h_i s_i + sum_(i<j) J_ij s_i s_j.
```

The Gibbs law is `p(s) proportional to exp(-beta * E(s))`. EVAL-EQ-016 and EVAL-EQ-017 were
added to the equation audit before implementation.

## Hard-Parts Analysis

### H1 - Quantization must target the dimensionless Gibbs coefficients

The implementation quantizes `beta * h_i` and `beta * J_ij`, not the unscaled host
coefficients. The resulting model is an effective Hamiltonian sampled at inverse temperature
one. This makes temperature and coefficient precision inseparable in the same way they are in
the target distribution. The original offset is excluded because it cancels exactly from every
normalized probability. Optimization witnesses must still be rescored against the original
`IsingModel`; the effective model is not an objective oracle.

### H2 - Small-model verification must not overflow on irrelevant offsets

Exact enumeration computes only offset-free interaction energies. It subtracts the maximum log
weight before exponentiation and retains log probabilities even when a state probability
underflows to zero in binary64. At `beta = 0`, it returns the uniform law before evaluating any
energy, including models whose interaction-energy sum would overflow at positive beta.

An interaction energy, scaled log weight, or log-weight span outside binary64 raises the
specific `ExactDistributionNumericalError`. Quantization analysis catches that condition,
records `not_computed_numerical_range` and the reason, and preserves its finite analytic bounds.
This prevents non-finite values from entering JSON evidence without making small-state
enumeration a prerequisite for scalable analysis.

### H3 - The scalable error statement needs a distribution-level bound

For coefficient errors `delta_h` and `delta_J`, the statewise effective-energy error is bounded
by the sum of their absolute values, `epsilon`. The local Gibbs-logit error at variable `i` is
bounded by twice the absolute bias error plus incident coupling errors. If both Hamiltonians
differ by at most `epsilon` for every state, their normalized likelihood ratio lies between
`exp(-2 * epsilon)` and `exp(2 * epsilon)`, yielding

```text
TV(target, quantized) <= tanh(epsilon).
```

The exact small-model verifier independently enumerates both laws and reports total variation,
both KL directions, maximum state-probability error, all one-spin marginals, and all pair
correlations. A deterministic coefficient/beta sweep and a spin-gauge mutation check that the
measured total variation does not exceed the analytic bound within binary64 tolerance.

### H4 - Numeric-format behavior must be explicit

`FixedPointSpec` defines whether the code is signed, the integer and fractional bit counts,
rounding, and overflow behavior. Signed `s{I}{F}` means one sign bit, `I` integer bits excluding
the sign, and `F` fractional bits. The host representation is limited to 53 total code bits so
every integer code is exactly representable by binary64. Nearest-even ties are tested on both
signs; saturation is tested at both asymmetric two's-complement endpoints.

## Decisions

1. Every non-null `TSUSpec` parameter requires `measured`, `modeled`, `assumed`, or `inferred`
   provenance and a non-empty source. Unknown values remain `None`.
2. No Z1 defaults are present. The abstract target can contain no parameters at all.
3. `nearest_even` is the default rounding policy because it is deterministic and does not have
   the directional bias of truncation. `toward_zero` remains an explicit alternative.
4. `reject` is the default overflow policy. Saturation is allowed only when requested and is
   counted per coefficient. Wraparound is not supported.
5. The paper-declared `s{4}{1}`, `s{4}{3}`, and `s{4}{6}` formats are endpoint fixtures, not
   Extropic hardware assumptions.
6. The exact-enumeration default limit is 16 variables. Callers may lower or raise it explicitly;
   larger models receive analytic bounds without state enumeration.
7. `beta = 0` is valid and denotes the uniform distribution. Negative or non-finite beta is
   rejected.
8. Exact distribution evidence uses the model's canonical variable order. Models with different
   variable order are not silently realigned.
9. Distribution comparison is about equilibrium correctness. It makes no claim about mixing,
   autocorrelation, time to equilibrium, or hardware non-idealities.

## Rejected Alternatives

- Hard-coded Z1 capacity, degree, timing, energy, or coefficient precision was rejected because
  the reviewed public material does not establish a stable production contract.
- Reusing the FPGA p-bit formats as TSU defaults was rejected because those formats describe a
  different architecture and distinct workloads.
- Quantizing raw `h` and `J` independently of beta was rejected because it does not describe the
  implemented Gibbs law.
- Quantizing or retaining the offset was rejected because it cannot affect normalized samples
  and can create avoidable overflow.
- Silent saturation or wraparound was rejected because it hides a materially changed model.
- Direct exponentiation of unshifted energies was rejected because it fails on harmless common
  energy shifts and ordinary low-temperature models.
- Reporting only marginal errors was rejected because equal marginals can hide incorrect joint
  structure. Pair correlations and state-law distances are included.
- Treating exact enumeration as proof of sampler quality was rejected. It verifies a target
  equilibrium distribution, not the trajectory used to reach it.
- Modeling an accumulated local-field DAC, sigmoid distortion, stale communication, drift, or
  mismatch was rejected for this pass because the available sources do not define one common
  physical transfer function.

## Sources and Implementations Examined

- Navid Anjum Aadit et al., "Programmable Probabilistic Computer with 1,000,000 p-bits,"
  arXiv:2606.25313v1, 24 June 2026,
  https://arxiv.org/abs/2606.25313. The Methods section declares `s{4}{1}`, `s{4}{3}`, and
  `s{4}{6}` as signed formats with four integer bits and the stated fractional bits. The source
  is a separate FPGA p-bit platform, not an Extropic TSU specification.
- Andraz Jelincic and Ross C. Walker, "Energy-efficient Codon Optimization on Thermodynamic
  Hardware," arXiv:2606.17327v1, 15 June 2026,
  https://arxiv.org/abs/2606.17327. This Extropic-affiliated preprint was used for workload and
  provenance context; its modeled hardware numbers were not adopted as defaults.
- Gibbsiq equation audit, EVAL-EQ-001, EVAL-EQ-005, EVAL-EQ-016, and EVAL-EQ-017.
- Existing `IsingModel.interaction_energy` and canonical conversion contracts. Exact comparison
  recomputes energies from these coefficients and does not trust sampler-reported energies.

The reviewed PDFs and immutable file evidence are:

- `reference/05-theory/papers/aadit-2026-million-pbit.pdf`: 25,492,691 bytes,
  30 pages, SHA-256
  `56475AD7733BC5EB8E58E4435B7C549E2D1E26C76EDE406D693C8C273949F268`.
- `reference/01-architecture/papers/jelincic-2026-codon-optimization.pdf`: 2,081,289
  bytes, 27 pages, SHA-256
  `81B73F3BC67E9B323B90CB27763701B7B529D2EE5FD753735464E4385B0066F9`.

## Negative Results and Limitations

This tranche does not implement placement, routing, degree reduction, factor quadratization,
communication scheduling, target calibration, hybrid partitioning, parallel tempering, or a
roofline cost model. It therefore does not yet decide whether a workload fits a TSU or estimate
effective samples per joule.

The quantization analysis covers stored effective coefficients only. It deliberately excludes
local-field accumulator precision, nonlinear response, timing skew, delayed boundary states,
drift, and circuit mismatch. The exact distribution uses binary64 probabilities; it explicitly
records underflow and rejects ranges that cannot be represented safely. The analytic bounds are
worst-case equilibrium bounds and can be loose. No empirical performance or energy claim is
made.

No stochastic run, generated benchmark corpus, or measured hardware artifact was created, so
there are no raw samples or generated-artifact checksums to record for this change.

## Verification

Focused verification after the final source audit:

```powershell
$env:PYTHONPATH = "src"
python -m unittest test_suite.tests.test_hardware_specs test_suite.tests.test_exact_distribution test_suite.tests.test_quantization -v
```

Result: 38 tests ran in 0.007 seconds and passed. Coverage includes paper-format endpoints,
positive and negative rounding ties, both saturation endpoints, beta zero, offset shifts,
extreme numerical ranges, a deterministic coefficient/beta sweep, a spin-gauge metamorphism,
and JSON non-finite rejection.

Static checks:

```powershell
python -m ruff check src/gibbsiq/hardware.py src/gibbsiq/exact_distribution.py src/gibbsiq/quantization.py test_suite/tests/test_hardware_specs.py test_suite/tests/test_exact_distribution.py test_suite/tests/test_quantization.py
python -m ruff format --check src/gibbsiq/hardware.py src/gibbsiq/exact_distribution.py src/gibbsiq/quantization.py test_suite/tests/test_hardware_specs.py test_suite/tests/test_exact_distribution.py test_suite/tests/test_quantization.py
$env:PYTHONPATH = "src"
python -m mypy src/gibbsiq/hardware.py src/gibbsiq/exact_distribution.py src/gibbsiq/quantization.py
```

Results: Ruff lint passed; Ruff reported six files already formatted; mypy reported success in
three source files with the existing note that the `dimod.*` module section is unused.
