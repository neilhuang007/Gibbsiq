# Reference Index

Research snapshot: 2026-07-11.

## Start Here

- [Source map](source-map.md)
- [Glossary](glossary.md)
- [Claims evidence map](claims-evidence-map.md)
- [Research gaps](research-gaps.md)
- [Roadmap](00-roadmap/README.md)

## Technical Notes

- [THRML runtime](01-architecture/thrml-runtime.md)
- [QUBO/BQM API](02-interfaces/qubo-bqm-api.md)
- [THRML optimization runtime](03-samplers/thrml-optimization-runtime.md)
- [Baseline solvers](03-samplers/baseline-solvers.md)
- [Diagnostics](04-diagnostics/mixing-quality.md)
- [Theory](05-theory/probabilistic-computing-and-pbits.md)
- [Benchmark plan](06-benchmarks/benchmark-plan.md)
- [Inspector design](07-inspector/inspector-design.md)
- [Evaluation framework](08-evaluation/README.md)

## Citations and Paper Notes

- [`references.bib`](references.bib) is the single canonical citation source: one
  verified entry per paper, each resolved through Crossref (DOI) or DataCite
  (arXiv) by [`tools/build_references.py`](../tools/build_references.py). Cite by
  BibTeX key; do not hand-type bibliographies. Regenerate, don't hand-edit.
- Each paper under `<section>/papers/` carries up to three files:
  - `<slug>.md` - a checked reading guide, source-derived text, or a clearly labeled
    withdrawal notice. Its provenance statement defines which of these it is.
  - `<slug>.note.md` — a Gibbsiq "lab note": what the paper does and how it links
    to the project's layers and conventions.
  - `<slug>.transcript.md` - where present, the raw `pdftotext` provenance dump
    (frontmatter-stamped; not authoritative - see the equation audit).
- [`tools/verify_citation.py`](../tools/verify_citation.py) resolves a single DOI
  or arXiv id on demand; [`tools/transcribe_pdf.py`](../tools/transcribe_pdf.py)
  extracts text from a PDF for comparison. Extraction does not establish transcription
  fidelity; page-scoped claims still require comparison with the PDF.

## Rules for Future Agents

- Prefer primary sources: official docs, papers, source repos.
- Use [the equation audit](08-evaluation/equation-audit.md) for math; local Markdown
  derivatives and raw PDF transcripts cannot override the primary PDF.
- Run or preserve [evaluation fixtures](08-evaluation/fixtures/README.md) before changing conventions.
- Keep docs short and implementation-oriented.
- Record assumptions and sign conventions.
- Do not assume THRML provides QUBO/BQM conversion, diagnostics, inspector, or baselines.
