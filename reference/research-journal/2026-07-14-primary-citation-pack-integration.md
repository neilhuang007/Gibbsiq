# 2026-07-14 - Primary Citation Pack Integration

## Paper Hook

This entry feeds the related-work, algorithm-source, hardware-comparator, and reproducibility
sections by pinning four newly used primary papers to generated, identifier-resolved BibTeX
records and locally checksummed PDFs.

## Scope

Added four downloaded primary papers to the `MANIFEST` in `tools/build_references.py`, regenerated
the canonical `reference/references.bib`, and updated the reference index snapshot. No production
module, equation convention, roadmap status document, or solver result was changed.

The local PDF metadata and first-page front matter were checked with `pdfinfo` and layout-aware
`pdftotext`. Citation metadata was resolved independently through `tools/verify_citation.py`, which
uses DataCite for arXiv records and Crossref for DOI records.

## Identifier Resolution And Classification

| BibTeX key | Local PDF and classification | Identifier queried | Canonical result |
| --- | --- | --- | --- |
| `aadit2026millionpbit` | `reference/05-theory/papers/aadit-2026-million-pbit.pdf`; arXiv v1, distributed digital multi-FPGA p-bit computer | arXiv [`2606.25313`](https://arxiv.org/abs/2606.25313) | DataCite arXiv preprint; no non-arXiv DOI was returned |
| `jelincic2026codon` | `reference/01-architecture/papers/jelincic-2026-codon-optimization.pdf`; Extropic-affiliated arXiv v1, codon optimization and modeled thermodynamic-hardware application | arXiv [`2606.17327`](https://arxiv.org/abs/2606.17327) | DataCite arXiv preprint; no non-arXiv DOI was returned |
| `chowdhury2025apticm` | `reference/05-theory/papers/chowdhury-2025-adaptive-parallel-tempering-icm.pdf`; local arXiv v3, APT plus isoenergetic cluster moves | arXiv [`2503.10302`](https://arxiv.org/abs/2503.10302) and DOI [`10.1038/s41467-025-64235-y`](https://doi.org/10.1038/s41467-025-64235-y) | DataCite linked the arXiv record to the Crossref Nature Communications version of record, volume 16, article 9193 (2025); the manifest pins the DOI |
| `yao2026qsb` | `reference/01-architecture/papers/yao-2026-sparse-fpga-quantized-simulated-bifurcation.pdf`; peer-reviewed Nature Communications article-in-press | DOI [`10.1038/s41467-026-75119-0`](https://doi.org/10.1038/s41467-026-75119-0) | Crossref journal article (2026); the available record did not yet provide volume, issue, or article number |

Yao et al. implement quantized simulated bifurcation on a deterministic digital FPGA. It is a
classical Ising-machine comparator and possible baseline source, not evidence about Extropic TSU
circuits, sampling fidelity, or energy. Aadit et al. likewise describe a digital multi-FPGA p-bit
system, not Extropic silicon. Jelinčič and Walker is directly Extropic-affiliated, but its TSU
energy numbers are modeled projections rather than end-to-end production-device measurements.

## Decisions And Rejected Alternatives

1. **Prefer published DOIs when a real version of record resolves.** The Chowdhury manifest row
   uses the Nature Communications DOI rather than retaining the arXiv identifier. Yao was already
   supplied as a Nature DOI. Rejected citing their preprints as canonical when Crossref provides a
   peer-reviewed record.
2. **Retain arXiv identifiers where no version of record resolves.** Aadit and Jelinčič remain
   arXiv entries. Rejected inventing or borrowing a DOI from a different paper; in particular,
   the 2026 Extropic thermodynamic-computing journal article is not the codon-optimization paper.
3. **Use descriptive stable keys and filename-matching slugs.** Rejected surname-year-only keys
   for these additions because the repository already contains another Jelinčič paper and is
   likely to accumulate more p-bit and simulated-bifurcation sources.
4. **Regenerate, never hand-edit, the bibliography.** The live build also upgraded the existing
   `shaglel2025` entry from arXiv metadata to its newly linked New Journal of Physics DOI
   `10.1088/1367-2630/ae7823`. Rejected manually reverting that resolver-produced change merely to
   minimize the diff.
5. **Do not invent unavailable bibliographic fields.** Crossref did not yet return a volume,
   issue, or article number for Yao's article-in-press. Rejected copying provisional fields from
   the PDF or guessing future pagination.
6. **Preserve the hardware distinction.** Rejected classifying Yao's digital FPGA quantized
   simulated-bifurcation machine as TSU evidence. It belongs in the comparator/prior-art set.
7. **Do not add transcription-header mappings without transcription artifacts.** The four local
   additions are PDFs used by current research and implementation journals; no matching cleaned
   paper transcription was created in this task, so `tools/wire_headers.py` was not expanded.

## Commands And Results

Metadata inspection:

```powershell
pdfinfo <local-pdf>
pdftotext -f 1 -l 1 -layout <local-pdf> -
```

The titles, author lists, arXiv versions, and Yao DOI/article-in-press banner matched the local
front matter. Citation resolution:

```powershell
python tools/verify_citation.py --arxiv 2606.25313 --key aadit2026millionpbit
python tools/verify_citation.py --arxiv 2606.17327 --key jelincic2026codon
python tools/verify_citation.py --arxiv 2503.10302 --key chowdhury2025apticm
python tools/verify_citation.py --doi 10.1038/s41467-025-64235-y --key chowdhury2025apticm
python tools/verify_citation.py --doi 10.1038/s41467-026-75119-0 --key yao2026qsb
```

All five commands resolved successfully. The arXiv resolver returned DataCite preprints for Aadit
and Jelinčič, upgraded Chowdhury to the same Nature DOI confirmed by the explicit DOI query, and
Crossref resolved Yao under the supplied Nature DOI.

Bibliography generation:

```powershell
python tools/build_references.py --out reference/references.bib
```

Result: `wrote reference\references.bib (27 entries)`. The output contains four unique new keys
and the expected arXiv/DOI fields. The bibliography was not manually edited.

Validation commands:

```powershell
python -m ruff check tools/build_references.py
python -m ruff format --check tools/build_references.py
python tools/check_markdown_math.py
git diff --check -- tools/build_references.py reference/references.bib reference/README.md `
  reference/research-journal/2026-07-14-primary-citation-pack-integration.md
```

Results: Ruff lint passed and the tool was already formatted. An independent structural check
found 27 unique generated entries and confirmed all four requested keys and identifiers.
Markdown math passed. `git diff --check` passed with only the existing informational LF-to-CRLF
working-copy warnings for `reference/README.md` and `tools/build_references.py`. The root
integrator owns repository-wide verification.

## Artifact Checksums

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| `reference/05-theory/papers/aadit-2026-million-pbit.pdf` | 25,492,691 | `56475ad7733bc5eb8e58e4435b7c549e2d1e26c76ede406d693c8c273949f268` |
| `reference/01-architecture/papers/jelincic-2026-codon-optimization.pdf` | 2,081,289 | `81b73f3bc67e9b323b90cb27763701b7b529d2ee5fd753735464e4385b0066f9` |
| `reference/05-theory/papers/chowdhury-2025-adaptive-parallel-tempering-icm.pdf` | 16,392,886 | `e9a7eb2fb608b7ac8c8cc24284b0b3132392fdc83d09362b11df6eb0b0834cec` |
| `reference/01-architecture/papers/yao-2026-sparse-fpga-quantized-simulated-bifurcation.pdf` | 3,268,296 | `9d7adcb1f808bf7b046ae440fdafe54c2e84520c1a99e08b544a7181e0104fbd` |
| `tools/build_references.py` | 5,306 | `0213469cf690e16dbbffd4761217944afe83640bec13720bcda48c1f2ad65017` |
| `reference/references.bib` | 11,270 | `863ec9b7176c57dbccea22c1aec0843cbc4a02e81aea943bb3c7d8d6800c80e0` |
| `reference/README.md` | 3,782 | `e6f2c18f47f9e8d7fa3ec666d4d5d69b7a902ded3f95c5af4072ace6ddef84bd` |
