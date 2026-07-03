# Research Journal

A dated, written record of design decisions and experimental work on Gibbsiq,
kept so that the methodology can be transcribed directly into the final paper
without reconstructing it from code and git history after the fact.

Each entry is self-contained: it states what was built, *why* it was built that
way, how correctness was established, and what the resulting artifact's exact
contents and checksums are. Entries are append-only; if a decision is later
revised, add a new entry rather than rewriting an old one.

Write every entry in the tone fixed by [`style.md`](style.md): the register of the
project's anchor paper (Jelinčić et al. 2025, arXiv:2510.23972), direct and
detailed, with each claim tied to a mechanism, a measurement, or a
primary-reference identifier. That file gives the voice, the section skeleton, and
a checklist.

Before starting work, read [`gotchas-and-todo.md`](gotchas-and-todo.md): the
recurring writing and engineering pitfalls to avoid, and the live cross-stage TODO
list. Keep it current as pitfalls surface and TODOs close.

## Entries

| Date | Entry | Topic |
| --- | --- | --- |
| 2026-05-31 | [Ground-truth test set](2026-05-31-ground-truth-test-set.md) | Construction, verification, and citation of the brute-force benchmark corpus |
| 2026-06-01 | [Stage 1 model compatibility](2026-06-01-stage-01-model-compatibility.md) | The Ising IR interface and QUBO/Ising/BQM normalization decisions |
| 2026-06-02 | [Conversion scenario tests](2026-06-02-conversion-scenario-tests.md) | Scenario coverage for the model-normalization oracle and the D-Wave convention |
| 2026-06-14 | [THRML-first positioning](2026-06-14-thrml-first-positioning.md) | Reframing Gibbsiq as THRML-native optimization infrastructure |
| 2026-07-01 | [Stage 2 THRML runtime](2026-07-01-stage-02-thrml-runtime-implementation.md) | Lowering the audited Ising IR into THRML block-Gibbs programs |
| 2026-07-01 | [Trust-layer positioning](2026-07-01-trust-layer-positioning.md) | Independent verification and diagnostics as the durable moat above THRML |
| 2026-07-02 | [Stage 3 diagnostics pipeline](2026-07-02-stage-03-diagnostics-pipeline.md) | Sampler-health telemetry: ESS, split R-hat, diversity, and failure flags |
| 2026-07-03 | [Stage 3 SOTA alignment](2026-07-03-stage-03-sota-alignment.md) | Rank-normalized + folded split R-hat (EVAL-EQ-013) and magnetization chain-disagreement wiring; the median tie knife-edge |

## Conventions used throughout

- **Writing tone:** [`style.md`](style.md) — the paper register, the entry
  skeleton, and the direct-tone rules (state the positive fact; no "not X but Y"
  framing; no emojis or rhetorical emphasis).
- **Energy convention:** `E(s) = offset + Σ_i h_i s_i + Σ_{i<j} J_ij s_i s_j`,
  `s_i ∈ {-1,+1}`, quadratic terms upper-triangle only (never double-counted).
- **Max-Cut ↔ Ising:** Ising energy `= Σ_edges s_u s_v`; `cut = (|E| − energy)/2`.
- Floating-point comparisons use absolute tolerance `1e-9`.
- All randomness is seeded (`random.Random(seed)`); artifacts are reproducible
  and carry a SHA-256 content checksum.
