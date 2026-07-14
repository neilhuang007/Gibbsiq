# 2026-07-11 - Primary-Source Integrity Audit

## Paper Hook

This entry feeds the related-work, limitations, and reproducibility sections. It records why
the Jelinčič paper provides architectural motivation while supplying no direct evidence for
Gibbsiq's QUBO quality, runtime, or hardware-performance claims.

## Context

The local file
`reference/01-architecture/papers/jelincic-2025-probabilistic-hardware-architecture.md`
described itself as a faithful transcription of all 42 PDF pages. Technical claims in that
file had propagated into its companion note and the repository's source conventions. We
compared the derivative with arXiv:2510.23972v2 and the local PDF whose SHA-256 is
`940e61b13e9387d05c9380249ad3694f32cd07b18157cbf789d82888eee6b696`.

## Hard-Parts Analysis

### H1. The derivative fails as source evidence

The derivative reports an LFSR-based Gaussian-noise circuit. The PDF attributes randomness to
shot-noise dynamics in subthreshold transistors and contains zero `LFSR` occurrences. The
derivative reports a small FPGA Boltzmann-machine demonstration; the PDF contains zero `FPGA`
occurrences. These mismatches show that the failure extends beyond formatting and
paraphrasing.

### H2. Two unit errors reverse the scale of the evidence

Appendix J, PDF page index 25, reports approximately 10 MHz at approximately 350 aJ per bit.
The derivative states approximately 1 MHz at approximately 350 microjoules per bit. The energy
unit changes from `10^-18 J` to `10^-6 J`, a 12-order-of-magnitude error.

Appendix D.4, PDF page index 29, estimates a complete denoising-model cost of approximately
`1.6 * T nJ`, where `T` is the number of denoising steps. The derivative states approximately
1.6 fJ. Even at `T = 1`, this changes the estimate by 6 orders of magnitude and drops a model
dimension.

### H3. The paper combines measurements and projections

PDF page 5 states that a GPU simulator represents a future hardware device and that a physical
model estimates generation energy. PDF page 6 reports a measured RNG autocorrelation decay of
approximately 100 ns, then combines RNG data with modeled bias, clock, and communication terms
in `E = T * K_mix * L^2 * E_cell`. The estimated `E_cell` is approximately 2 fJ. The abstract's
approximately 10,000-fold comparison is therefore a system-level projection for a simple
generative-model benchmark.

### H4. The paper's Ising convention is not Gibbsiq's convention

Equations 10 and 11 on PDF page 5 place `beta` and a leading minus sign in the paper's energy
and use an `i != j` pair sum. Gibbsiq uses an offset-preserving upper-triangular sum and applies
`beta` in the Boltzmann law. A direct formula copy risks a sign or factor-of-two error. The
equation audit remains the implementation authority.

## Decisions

- We withdrew the generated transcript claim and preserved its filename as a source guide.
  Preserving the path avoids link rot while the heading and provenance notice prevent future
  quotation as a transcript.
- We made the PDF and arXiv record authoritative and recorded the local PDF checksum.
- We retained only claims tied to PDF pages, equations, or appendices.
- We classified circuit measurements separately from physical-model estimates and
  system-level projections.
- We limited transfer to sparse topology, graph coloring, Gibbs-sign auditing, and mixing
  motivation. QUBO performance requires Gibbsiq-specific benchmarks.

## Rejected Alternatives

- Correcting only the two visible unit errors was rejected because the LFSR, FPGA, and faithful
  transcription claims demonstrate broader provenance failure.
- Deleting the Markdown path was rejected because existing research notes link to it and a
  prominent withdrawal notice is stronger evidence hygiene than a missing file.
- Regenerating a 42-page prose transcript was rejected because extraction quality would still
  require sentence-level comparison. The concise source guide has a smaller auditable surface.
- Importing the paper's Equation 11 into production documentation was rejected because the
  energy and pair-count conventions differ from Gibbsiq's canonical equation.

## Sources Read

- Jelinčič et al., arXiv:2510.23972v2, dated 2025-12-12; local 42-page PDF.
- THRML getting-started documentation:
  https://docs.thrml.ai/en/latest/examples/00_probabilistic_computing/
- THRML architecture documentation: https://docs.thrml.ai/en/latest/architecture/

## Files Updated

- `reference/01-architecture/papers/jelincic-2025-probabilistic-hardware-architecture.md`
- `reference/01-architecture/papers/jelincic-2025-probabilistic-hardware-architecture.note.md`
- `reference/README.md`
- `reference/source-map.md`
- `reference/research-journal/style.md`
- `reference/research-journal/gotchas-and-todo.md`

## Verification

The audit used these commands:

```powershell
pdfinfo reference/01-architecture/papers/jelincic-2025-probabilistic-hardware-architecture.pdf
pdftotext -layout -f 5 -l 6 reference/01-architecture/papers/jelincic-2025-probabilistic-hardware-architecture.pdf -
Get-FileHash -Algorithm SHA256 reference/01-architecture/papers/jelincic-2025-probabilistic-hardware-architecture.pdf
```

We rendered PDF pages 5 and 6 at 120 DPI and inspected the equations, topology description,
GPU-simulator statement, RNG figure, and energy-model text visually. Page-by-page text search
located `350aJ` at PDF page index 25 and `1.6 T nJ` at PDF page index 29.

`python tools/check_markdown_math.py` exited 0 after the documentation edits.
`git diff --check` reported no whitespace errors; Git emitted only the repository's existing
LF-to-CRLF working-tree warnings. No Python behavior is claimed from these documentation
checks.
