# Research Journal

A dated, written record of design decisions and experimental work on Gibbsiq,
kept so that the methodology can be transcribed directly into the final paper
without reconstructing it from code and git history after the fact.

Each entry is self-contained: it states what was built, *why* it was built that
way, how correctness was established, and what the resulting artifact's exact
contents and checksums are. Entries are append-only; if a decision is later
revised, add a new entry rather than rewriting an old one.

## Entries

| Date | Entry | Topic |
| --- | --- | --- |
| 2026-05-31 | [Ground-truth test set](2026-05-31-ground-truth-test-set.md) | Construction, verification, and citation of the brute-force benchmark corpus |

## Conventions used throughout

- **Energy convention:** `E(s) = offset + Σ_i h_i s_i + Σ_{i<j} J_ij s_i s_j`,
  `s_i ∈ {-1,+1}`, quadratic terms upper-triangle only (never double-counted).
- **Max-Cut ↔ Ising:** Ising energy `= Σ_edges s_u s_v`; `cut = (|E| − energy)/2`.
- Floating-point comparisons use absolute tolerance `1e-9`.
- All randomness is seeded (`random.Random(seed)`); artifacts are reproducible
  and carry a SHA-256 content checksum.
