# 2026-07-14 - General-Field Isoenergetic Cluster Move

## Paper Hook

This entry feeds the optimization-method and limitations sections of the
auditable-sampling paper. It records a replica-coupling primitive that can be
composed with parallel tempering while preserving the combined canonical Ising
energy, and it separates that optimizer transition from independent-chain Gibbs
evidence.

## Context

Chowdhury et al., Nature Communications 16, 9193 (2025), DOI
[`10.1038/s41467-025-64235-y`](https://doi.org/10.1038/s41467-025-64235-y),
combine adaptive parallel tempering with isoenergetic cluster moves (ICM) for
three-dimensional spin-glass optimization. Their Algorithm S2 forms the overlap
of two same-temperature replicas, selects a connected component whose overlap is
$-1$, and flips that component in both replicas. Four replicas per temperature
and one sweep per swap attempt are empirical choices for their benchmark. The
present tranche implements only the ICM primitive. Parallel-tempering
orchestration, adaptive temperature construction, and runtime integration remain
separate work.

For replicas $s^{(a)}$ and $s^{(b)}$, the overlap is

$$
q_i = s_i^{(a)}s_i^{(b)}
$$

The disagreement subgraph is induced by variables with $q_i=-1$ and the nonzero
quadratic edges in `IsingModel`. A move selects one connected component and
negates its spins in both replicas.

## Hard-Parts Analysis

### H1 - The paper's large-cluster shortcut is restricted to zero field

Algorithm S2 globally flips one randomly chosen replica when the selected
cluster contains more than half of all spins. The paper studies a zero-field
Edwards-Anderson Hamiltonian, for which a global spin inversion leaves the
pairwise energy unchanged. Gibbsiq's canonical model admits arbitrary linear
fields. A global inversion changes
$\sum_i h_i s_i$ whenever a field is nonzero.

`cluster_moves.py` therefore implements the general-field disagreement-cluster
primitive rather than the complete Algorithm S2. It always flips the selected
component in both replicas. The zero-field global-flip shortcut is intentionally
absent.

### H2 - Pair-energy invariance requires a maximal disagreement component

The audited invariant is

$$
E(s^{(a)}) + E(s^{(b)})
=
E(s'^{(a)}) + E(s'^{(b)})
$$

Linear contributions cancel on every disagreement variable because
$s_i^{(b)}=-s_i^{(a)}$. An edge internal to the selected component retains each
replica product because both endpoints flip. An edge from the component to an
agreement variable cancels across replicas because the inside spins are opposite
and the outside spins agree. A selected connected component has no edge to a
different disagreement component by maximality. These cases exhaust the
canonical upper-triangle quadratic terms. The offset appears once in each
replica before and after the move and therefore remains in the recomputed audit
energies without affecting the residual.

### H3 - Selection must be reproducible and replayable

An applied move requires exactly one selection mechanism: an injected
`random.Random`, an integer seed, or a deterministic component index. Component
order follows `model.variables`, including for mixed-type labels. The result
records the selected index and labels, so an audited move can be replayed without
recovering hidden global RNG state. Identical replicas have no disagreement
component and return a deterministic no-op without requiring a selector.

### H4 - Replica coupling changes diagnostic semantics

The move returns immutable copies and metadata containing
`semantics="optimization_only_replica_coupling"` and
`replicas_are_independent=False`. ICM deliberately couples replicas. Between-chain
R-hat, ESS, and diversity calculations cannot treat the two post-move replicas as
independent chains without a diagnostic design that accounts for the coupling.

## Decisions

1. We use the canonical `IsingModel.energy` method for every before/after energy.
   No energy reported by the move is inferred from a local delta.
2. We form components from `model.graph`, which contains exactly the nonzero
   canonical quadratic interactions. Isolated disagreement variables are
   singleton components.
3. We preserve model variable order for disagreements, components, returned
   samples, and metadata. This supports arbitrary hashable labels without
   comparing unlike Python types.
4. We require exact sample-key agreement with `model.variables`. Missing and
   extra labels, boolean values, and values outside `{-1,+1}` raise before a move
   is applied.
5. We copy both inputs and expose the outputs through `MappingProxyType`. Calling
   code cannot mutate the original samples or the audited result mappings.
6. We use the established project absolute energy tolerance `1e-9` for the
   convenience `combined_energy_invariant` flag. The raw residual remains in the
   metadata. Relative tolerance is zero so a large shared offset cannot mask an
   interaction-energy defect.
7. We expose `component_index` as a replay mechanism. Supplying an index together
   with a seed or RNG is rejected because silently ignoring one source would make
   the provenance ambiguous.
8. We keep this primitive in a new small module and do not export it from
   `gibbsiq.__init__` or connect it to the runtime in this tranche.

## Rejected Alternatives

- We rejected Algorithm S2's cluster-larger-than-half global inversion because
  it is isoenergetic only under the paper's zero-field symmetry.
- We rejected module-global randomness and an implicit unseeded default. Either
  an injected source or a recorded component index determines every applied
  move.
- We rejected mutating replicas in place because mutation would destroy the raw
  pre-move evidence required for an audit.
- We rejected NetworkX for component discovery. A standard-library depth-first
  traversal is linear in the model graph and preserves the zero-dependency core.
- We rejected treating ICM output as ordinary independent-chain Gibbs output.
  The move is explicitly an optimization-only replica coupling.
- We rejected porting quantized simulated bifurcation from Yao et al. in this
  tranche. That work accelerates a continuous digital solver rather than a
  THRML/TSU Gibbs kernel.

## Primary Sources and Artifacts

### Adaptive parallel tempering with ICM

- Source: Chowdhury et al., arXiv
  [`2503.10302v3`](https://arxiv.org/abs/2503.10302), submitted 13 March 2025 and
  revised 28 July 2025; peer-reviewed article published 16 October 2025.
- Download URL: `https://arxiv.org/pdf/2503.10302`.
- Local PDF:
  `reference/05-theory/papers/chowdhury-2025-adaptive-parallel-tempering-icm.pdf`.
- Download date: 14 July 2026.
- File size: 16,392,886 bytes; page count: 28.
- SHA-256:
  `e9a7eb2fb608b7ac8c8cc24284b0b3132392fdc83d09362b11df6eb0b0834cec`.
- Extracted text:
  `tmp/pdfs/chowdhury-2025-apt-icm/extracted.txt`, 175,762 bytes, SHA-256
  `75d1d647d9ee0e546a43082116578b5e72e25120f5d67fc034c7df32b8e2801f`.
- Rendered and visually inspected pages: PDF page 5 contains the adjacent-replica
  Metropolis criterion; PDF page 24 contains Algorithm S2 and `ICMop`.
  `page-05.png` is 709,600 bytes with SHA-256
  `2e1c98b65881d33f8bba5c330b3931656d2071d3eb812be67312dfbe7c11c06f`;
  `page-24.png` is 348,656 bytes with SHA-256
  `2b2844adf17e8c55a6899f61d5a48743d63f957af28ecab891d434caa5ff4120`.
  Both are under `tmp/pdfs/chowdhury-2025-apt-icm/rendered/`.

### Digital sparse simulated bifurcation reference

Yao et al., "Precision meets speed through an FPGA-based natively sparse Ising
machine for combinatorial optimization," Nature Communications, published 11
July 2026, DOI
[`10.1038/s41467-026-75119-0`](https://doi.org/10.1038/s41467-026-75119-0),
implements quantized simulated bifurcation on a Xilinx FPGA. TCOO tiles a sparse
interaction matrix for digital sparse matrix-vector multiplication. Its Int8
mapping quantizes the continuous simulated-bifurcation state and schedule. This
paper is a digital simulated-bifurcation architecture reference. It is not TSU
sampling evidence and supplies no Boltzmann-distribution fidelity result.

- Download URL:
  `https://www.nature.com/articles/s41467-026-75119-0_reference.pdf`.
- Local PDF:
  `reference/01-architecture/papers/yao-2026-sparse-fpga-quantized-simulated-bifurcation.pdf`.
- Download date: 14 July 2026.
- File size: 3,268,296 bytes; page count: 17.
- SHA-256:
  `9d7adcb1f808bf7b046ae440fdafe54c2e84520c1a99e08b544a7181e0104fbd`.
- Extracted text: `tmp/pdfs/yao-2026-qsb-tcoo/extracted.txt`, 81,510 bytes,
  SHA-256
  `dec57b271aa3047a59fa2941601863f47806dcc98ae061add5e83d689eef455a`.
- Rendered and visually inspected pages: PDF page 5 presents TCOO; PDF page 7
  presents the Int8 quantization equation. `page-05.png` is 497,974 bytes with
  SHA-256
  `27063aea87a22d628e5c794b754f0918dc7e3010284e75c3bfdd853d17b0aaa8`;
  `page-07.png` is 416,489 bytes with SHA-256
  `09a37758a9c3f25e64c99e3635750bab47fdc0f9a36404ecf3fc79a8582a9ea4`.
  Both are under `tmp/pdfs/yao-2026-qsb-tcoo/rendered/`.

The Yao paper's reported 99% accuracy is Max-Cut solution quality relative to a
floating-point simulated-bifurcation implementation. It is not a probability-
distribution accuracy metric. The paper reports that Int8 quantization alone
worsened optimization and that retuning the integration step recovered the
result.

Paper acquisition, extraction, and rendering commands:

```powershell
curl.exe -L --fail "https://arxiv.org/pdf/2503.10302" --output "reference/05-theory/papers/chowdhury-2025-adaptive-parallel-tempering-icm.pdf"
pdfinfo "reference/05-theory/papers/chowdhury-2025-adaptive-parallel-tempering-icm.pdf"
pdftotext -layout "reference/05-theory/papers/chowdhury-2025-adaptive-parallel-tempering-icm.pdf" "tmp/pdfs/chowdhury-2025-apt-icm/extracted.txt"
pdftoppm -f 5 -l 5 -png -r 170 "reference/05-theory/papers/chowdhury-2025-adaptive-parallel-tempering-icm.pdf" "tmp/pdfs/chowdhury-2025-apt-icm/rendered/page"
pdftoppm -f 24 -l 24 -png -r 170 "reference/05-theory/papers/chowdhury-2025-adaptive-parallel-tempering-icm.pdf" "tmp/pdfs/chowdhury-2025-apt-icm/rendered/page"
Get-FileHash -Algorithm SHA256 "reference/05-theory/papers/chowdhury-2025-adaptive-parallel-tempering-icm.pdf"

curl.exe -L --fail "https://www.nature.com/articles/s41467-026-75119-0_reference.pdf" --output "reference/01-architecture/papers/yao-2026-sparse-fpga-quantized-simulated-bifurcation.pdf"
pdfinfo "reference/01-architecture/papers/yao-2026-sparse-fpga-quantized-simulated-bifurcation.pdf"
pdftotext -layout "reference/01-architecture/papers/yao-2026-sparse-fpga-quantized-simulated-bifurcation.pdf" "tmp/pdfs/yao-2026-qsb-tcoo/extracted.txt"
pdftoppm -f 5 -l 5 -png -r 170 "reference/01-architecture/papers/yao-2026-sparse-fpga-quantized-simulated-bifurcation.pdf" "tmp/pdfs/yao-2026-qsb-tcoo/rendered/page"
pdftoppm -f 7 -l 7 -png -r 170 "reference/01-architecture/papers/yao-2026-sparse-fpga-quantized-simulated-bifurcation.pdf" "tmp/pdfs/yao-2026-qsb-tcoo/rendered/page"
Get-FileHash -Algorithm SHA256 "reference/01-architecture/papers/yao-2026-sparse-fpga-quantized-simulated-bifurcation.pdf"
```

## Verification

Focused unit tests:

```powershell
$env:PYTHONPATH = "src"
python -m unittest test_suite.tests.test_cluster_moves
```

Result: 10 tests ran in 0.016 seconds and passed. The exhaustive test enumerated
all 256 ordered replica pairs on a four-spin nonzero-field graph, skipped 16
identical pairs, and exercised all 272 selectable disagreement components. The
maximum absolute independently recomputed pair-energy residual was exactly zero
for the dyadic-coefficient fixture.

The combined cluster-move and model-compatibility command ran 19 tests in 0.016
seconds and passed:

```powershell
$env:PYTHONPATH = "src"
python -m unittest test_suite.tests.test_cluster_moves test_suite.tests.test_model_compatibility
```

Static checks:

```powershell
python -m ruff check src/gibbsiq/cluster_moves.py test_suite/tests/test_cluster_moves.py
python -m ruff format --check src/gibbsiq/cluster_moves.py test_suite/tests/test_cluster_moves.py
$env:PYTHONPATH = "src"
python -m mypy src/gibbsiq/cluster_moves.py
```

Result: Ruff lint passed, both files were formatted, and mypy reported success
with no issues in the new source module.

The implementation is `src/gibbsiq/cluster_moves.py`. The focused regression
suite is `test_suite/tests/test_cluster_moves.py`.

## Limitations and Follow-Up

This module is a primitive rather than a complete APT+ICM optimizer. It does not
construct an adaptive beta ladder, pair four same-temperature replicas, schedule
odd/even temperature exchanges, update THRML states, or account for replica-
coupling work in runtime traces. Those features require a separate integration
whose tests verify PT detailed balance and preserve sampler-state identity on
rejected swaps. The primitive accepts one model and no beta values, so it records
`same_temperature_required=True` but cannot verify the caller's runtime
temperature assignment.

The component traversal allocates Python adjacency and set structures and is
$O(|V|+|E|)$ per move. A future accelerator path may use a compiled union-find or
device-side connectivity kernel after profiling demonstrates that host component
discovery is material.

The convenience invariant flag uses an absolute tolerance while retaining the raw
residual. Models whose coefficients approach floating-point overflow can fail
before or during canonical energy recomputation; `IsingModel` continues to reject
non-finite energy arithmetic.

No empirical claim is made that ICM improves arbitrary QUBO families. The primary
evidence is specific to three-dimensional spin-glass optimization. No hardware or
TSU performance claim is made by this implementation.
