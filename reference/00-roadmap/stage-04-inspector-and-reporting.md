# Stage 4 - Inspector and Reporting

**Status: Partial as of 2026-07-15.** `GQ-INSPECT-01` implements the production artifact-only
`Inspector.from_result(result, *, model=None)` core with deterministic JSON/Markdown summaries,
stored traces/diagnostics/metadata, explicit unavailable sections, and optional all-row model
verification. HTML, CLI, comparison, topology, profiler, baseline, and compiled-manifest
integration remain assigned to `TM-REP-001`.

## Goal

Generate notebook-friendly and exportable reports from `SampleResult`.

## Deliverables

- `Inspector.from_result(result)`.
- Static HTML or markdown report.
- Topology and block summary.
- Energy and best-so-far plots.
- Autocorrelation / ESS summary.
- Best-state table.
- Sample-frequency table.
- Diversity view.
- Constraint section.
- Warning summary.
- Exported `summary.json`, samples, traces, metadata.

## Exit Criteria

- THRML result produces a report without custom notebook code.
- Report includes topology, traces, diagnostics, best states, warnings.
- Report artifacts are benchmark-consumable.
- Summary comparison works for at least two results.

## Implementation Notes

Every visual must answer a solver question:

- improvement over time;
- chain disagreement;
- mode collapse;
- stuck blocks;
- constraint failures;
- baseline delta.

## References

- Inspector note: ../07-inspector/inspector-design.md
- Diagnostics note: ../04-diagnostics/mixing-quality.md
- D-Wave Inspector docs: https://docs.dwavequantum.com/en/latest/ocean/api_ref_inspector/
- `dwave.inspector.show`: https://docs.dwavequantum.com/en/latest/ocean/api_ref_inspector/generated/dwave.inspector.show.html
- D-Wave Inspector repo: https://github.com/dwavesystems/dwave-inspector
- ArviZ docs: https://python.arviz.org/
