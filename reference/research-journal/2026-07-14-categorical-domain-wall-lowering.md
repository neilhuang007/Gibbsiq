# 2026-07-14 - Pairwise Categorical Domain-Wall Lowering

## Paper Hook

This entry feeds the compiler-methods, representation-overhead, and limitations sections of
the Thermodynamic Roofline paper. It records an exact, auditable lowering from heterogeneous
finite-state pairwise energies to Gibbsiq's existing QUBO/Ising contract, together with the
tests that separate algebraic energy preservation from unsupported mixing claims.

## Context

The downloaded Extropic-affiliated preprint derives a domain-wall encoding in Supplementary
Note 1. The reusable result is domain-neutral: an ordered categorical state is represented by
a prefix of one-valued wall bits, unary tables become first differences, pair tables become
mixed second differences, and reverse walls receive a quadratic penalty.

Only that abstract finite-state mathematics was implemented. No application model, schedule,
target capacity, timing, or hardware-energy value from the paper enters the production API or
tests. The source's performance figures are modeled rather than end-to-end measurements on a
production TSU and are outside this pass.

EVAL-EQ-020 was added to the equation audit before production code. The compiler constructs a
QUBO first and invokes the existing `compile_qubo` conversion so EVAL-EQ-003 remains the only
QUBO-to-Ising sign and offset authority.

## Hard-Parts Analysis

### H1 - An ordered domain is part of the mathematical program

Domain-wall adjacency depends on category order. `CategoricalModel` therefore requires an
explicit variable sequence and an explicit non-empty ordered domain for every variable.
Arbitrary hashable variable and category labels are retained, but unordered domain containers
are rejected. Pair interactions are sorted by canonical variable positions so mapping insertion
order cannot alter evaluation order, emitted evidence, or artifact checksums.

A supplied pair table is interpreted in the orientation of its pair key. If that key is reverse
to the declared variable order, the table is transposed once and the reversal count is recorded.
Supplying both orientations is rejected rather than summed. This prevents a superficially
symmetric API from silently corrupting asymmetric pair tables.

### H2 - The reduction is a discrete Abel transform

For category index `k` and zero-based wall threshold `i`, the binary variable is

```text
q_i = 1[k > i].
```

Unary energy is its state-zero value plus first differences times wall bits. Pair energy is its
`(0, 0)` value, first differences along both axes, and a rectangular grid of mixed second
differences. The implementation accumulates every contribution with `math.fsum` through the
existing finite-sum helper and rejects coefficients whose finite-difference or accumulated QUBO
value cannot be represented as finite binary64.

The original categorical offset, unary bases, and pair bases form the QUBO offset. Exhaustive
tests compare a raw-table oracle, the categorical evaluator, the constructed QUBO, and the
compiled Ising energy for every valid state. A second exhaustive test compares QUBO and Ising
energies for every valid and invalid binary word of a six-wall fixture.

### H3 - Penalty positivity is not a sufficiency theorem

A reverse `0 -> 1` wall contributes

```text
P * q_(i+1) * (1 - q_i).
```

The compiler requires the caller to supply finite `P > 0`; it has no default. This makes each
violation visible but does not prove that every invalid word lies above every valid assignment.
That stronger property depends on the complete objective range and optimization goal. Metadata
therefore records `caller_supplied_not_proven_sufficient`.

The penalty test uses a four-bit word with two reverse walls. Recompiling with penalties `1.5`
and `4.0` changes its energy by exactly `(4.0 - 1.5) * 2`, while every valid thermometer word
has penalty-independent energy.

### H4 - Singleton domains need no artificial spin

A one-state variable contributes zero wall variables. Its unary energy becomes a base-offset
term, and each pair involving it becomes either another base term or first differences on the
other variable. An all-singleton fixture lowers to a zero-variable Ising model with the complete
constant energy preserved. Adding a dummy wall spin was rejected because it would introduce a
spurious stochastic degree of freedom.

### H5 - Compiler labels must be safe and reproducible

Wall variables use a private frozen typed label containing canonical variable and wall
positions. This cannot collide accidentally with ordinary string, number, tuple, or user-class
labels and avoids delimiter/repr collisions from generated strings. Position-only labels make
repeated compilation deterministic: the same categorical model produces equal wall variables,
equal Ising IR, and equal compiler evidence.

The rejected identity-namespace design made separately compiled IRs unequal and broke
reproducible checksums. The accepted tradeoff is that two independently compiled encoded models
cannot be merged by raw label union alone; any future composition pass must apply an explicit
outer namespace. Composition is not part of this compiler pass.

The first evidence serializer used private objects as dictionary keys and failed JSON encoding.
The final serializer emits ordered integer positions, wall-chain rows, and coefficient rows.
`json.dumps(..., allow_nan=False)` is a regression contract.

### H6 - Algebraic exactness does not preserve sampling dynamics

The compiler reports wall-spin count, constraint-edge count, potential mixed-coefficient count,
actual nonzero QUBO edges, maximum degree, and the loose graph-theoretic `Delta + 1` color upper
bound. It does not claim an optimized coloring schedule. Category order changes one-bit
adjacency, mixed differences can densify the graph, and invalid wall words add state-space
regions. A mathematically exact lowering can therefore improve or severely worsen mixing.
Sampler diagnostics and empirical comparisons remain necessary.

## Decisions

1. Variables and category domains use caller-declared sequence order. Sets and other unordered
   domain containers are rejected.
2. Domains must be non-empty and contain unique hashable categories. Heterogeneous and singleton
   domains are supported.
3. Omitting a whole unary table means a complete zero table. Once supplied, unary and pair
   tables must be complete; missing individual cells are errors.
4. Self-pairs are rejected and must be folded into the unary table explicitly.
5. Reversed pair keys are accepted by transposing their complete tables. Both orientations for
   one unordered pair are rejected.
6. The wall convention is prefix ones followed by zeros, with `q_i = 1[k > i]`.
7. `encode`, `decode`, `is_valid`, and `violation_count` accept explicit binary or spin vartypes.
   Malformed samples raise; `is_valid` is not a schema-suppression path.
8. The penalty is a required keyword argument, must be finite and positive, and is never labeled
   sufficient automatically.
9. QUBO construction precedes `compile_qubo`; no second direct Ising derivation is maintained.
10. Wall labels are private, frozen, typed, and deterministic from canonical positions.
11. The color value is labeled a loose `Delta + 1` upper bound. No coloring or placement quality
    is implied.
12. Compiler metadata carries a strong mixing warning and no hardware-performance estimate.

## Rejected Alternatives

- Inferring order by sorting arbitrary labels was rejected because repr-based order is not a
  semantic category adjacency contract.
- Treating absent cells inside a supplied table as zero was rejected because a typo would become
  a different objective without an error.
- Summing forward and reversed pair-table declarations was rejected because asymmetric tables
  would be orientation-dependent and duplicates could be accidental.
- String-generated wall labels were rejected because user labels and escaped delimiters can
  collide.
- Random or object-identity namespaces were rejected because recompiling the same input produced
  unequal IR and evidence.
- A dummy spin for singleton domains was rejected because its state has no categorical meaning.
- A library-selected penalty was rejected because no universal positive value guarantees invalid
  states are irrelevant for every objective.
- Direct Ising coefficient assembly was rejected because it would duplicate the audited QUBO
  conversion and create another sign/offset failure surface.
- Reporting a DSATUR count without returning and validating the corresponding schedule was
  rejected for this small pass. The recorded `Delta + 1` result is always safe and explicitly
  loose.
- Treating valid-state equality as a mixing or hardware-speed claim was rejected.

## Sources and Artifacts

- Andraz Jelincic and Ross C. Walker, "Energy-efficient Codon Optimization on Thermodynamic
  Hardware," arXiv:2606.17327v1, 15 June 2026,
  https://arxiv.org/abs/2606.17327. Only Supplementary Note 1, equations S1-S20, supplies the
  implemented finite-state transform.
- Local source: `reference/01-architecture/papers/jelincic-2026-codon-optimization.pdf`,
  2,081,289 bytes, 27 pages, SHA-256
  `81B73F3BC67E9B323B90CB27763701B7B529D2EE5FD753735464E4385B0066F9`.
- Visual verification: PDF pages 12-15 were rendered at 144 DPI and inspected for the wall
  convention, reverse-wall penalty, unary first differences, mixed second differences, and
  complete Hamiltonian.
- Gibbsiq equation audit EVAL-EQ-003 and EVAL-EQ-020.
- Existing `gibbsiq.conversions.compile_qubo`, used as the sole QUBO-to-Ising conversion.

The rendered page images are temporary inspection files, not research results. No stochastic
samples, generated benchmark corpus, or measured hardware artifact was created.

## Negative Results and Limitations

The first wall-label design used an identity namespace. It passed energy tests but failed the
reproducibility audit because repeated compilation produced unequal labels and IR. It was
replaced with canonical position labels. The first `to_dict` representation similarly passed
energy tests but could not be serialized to JSON because it used private objects as mapping
keys. It was replaced with ordered numeric rows. Both negative results are retained here rather
than hidden.

The compiler handles finite pairwise categorical tables only. It does not lower higher-order
factors, choose category order, choose a sufficient penalty, optimize coloring, place or route
the graph, estimate ESS, or model target hardware. Complete pair tables require memory
proportional to each domain-product size. Binary64 arithmetic can introduce ordinary rounding;
the exhaustive fixtures use exactly representable dyadic coefficients so equality checks are
not weakened by a tolerance.

## Verification

Source-artifact verification:

```powershell
Get-FileHash -Algorithm SHA256 reference/01-architecture/papers/jelincic-2026-codon-optimization.pdf
Get-Item reference/01-architecture/papers/jelincic-2026-codon-optimization.pdf | Select-Object Length
pdfinfo reference/01-architecture/papers/jelincic-2026-codon-optimization.pdf
```

Result: SHA-256
`81B73F3BC67E9B323B90CB27763701B7B529D2EE5FD753735464E4385B0066F9`, size
2,081,289 bytes, and 27 pages.

Focused verification after the final reproducibility and serializer audit:

```powershell
$env:PYTHONPATH = "src"
python -m unittest test_suite.tests.test_categorical_model test_suite.tests.test_domain_wall_encoding -v
```

Result: 22 tests ran in 0.008 seconds and passed. The tests exhaust all 24 valid assignments of
a heterogeneous `3 x 2 x 1 x 4` model and all 64 valid/invalid binary words of its six-wall
encoding. They also cover arbitrary hashable labels, reverse orientation, mapping-order
metamorphism, singleton folding, offset shifts, two-wall invalid penalty sensitivity, codec
validation, deterministic frozen labels, overhead accounting, and JSON-safe evidence.

Static checks:

```powershell
python -m ruff check src/gibbsiq/categorical.py src/gibbsiq/domain_wall.py test_suite/tests/test_categorical_model.py test_suite/tests/test_domain_wall_encoding.py
python -m ruff format --check src/gibbsiq/categorical.py src/gibbsiq/domain_wall.py test_suite/tests/test_categorical_model.py test_suite/tests/test_domain_wall_encoding.py
$env:PYTHONPATH = "src"
python -m mypy src/gibbsiq/categorical.py src/gibbsiq/domain_wall.py
```

Results: Ruff lint passed; Ruff reported four files already formatted; mypy reported success in
two source files with the existing note that the `dimod.*` module section is unused.
