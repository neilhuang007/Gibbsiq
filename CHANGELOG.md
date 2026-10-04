# Changelog

## 0.2.0a1 — Unreleased

- Add stochastic qualification with frozen run plans, independent references,
  confidence intervals, and reproducible evidence bundles.
- Add `gibbsiq qualify`, `inspect`, `compare`, `tune`, and `doctor`.
- Add THRML, Torx, and Z1T adapters with pinned integration environments.
- Add complete-model evaluation, document-aware token losses, projection
  observations, and trained-checkpoint verification tools.
- Add a frozen equal-work trained-checkpoint policy comparison with explicit
  uncertainty, per-operation sampling budgets, and measured CPU cost boundaries.
- Add policy search with separate calibration, development, and evaluation
  inputs, plus validated policy export.
- Add cost accounting, synchronized timing, and regression reports.
- Add PyPI Trusted Publishing of tested CI artifacts, with artifact hashes
  and an isolated installation check after upload.
- Accept equivalent Windows and Unix line endings in pinned backend sources.
- Preserve the QUBO/Ising APIs, integer `SampleResult`, and
  `gibbsiq-evaluate` command.
