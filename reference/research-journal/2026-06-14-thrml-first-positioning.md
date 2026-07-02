# 2026-06-14 - THRML-First Positioning Decision

## Paper Hook

Feeds the system framing, motivation, and limitations sections: Gibbsiq is THRML-native
optimization infrastructure with diagnostics as required telemetry.

## Context

The project had been described as a diagnostics-first solver. That wording was accurate but
ambiguous: it allowed future work to reinterpret Gibbsiq as a backend-agnostic diagnostics
package. The intended direction is more specific. Gibbsiq should provide the optimization
stack above THRML: QUBO/BQM/Ising ingestion, audited Ising lowering, block construction,
schedules, traces, diagnostics, baselines, and benchmark verification.

## Decision

Clarify the project goal across the authoritative documents:

- Gibbsiq is THRML-native optimization infrastructure.
- THRML is the execution substrate.
- Diagnostics are mandatory telemetry and credibility checks for THRML-backed optimization.
- dimod compatibility and classical baselines are adoption and comparison bridges into the
  THRML path.
- Stage 2 is a THRML optimization runtime. It must include lowering, block construction,
  schedule/seed metadata, trace capture, and analytic validation.

## Rejected Alternative

Rejected: pivoting the project into a generic backend-agnostic diagnostics layer for QUBO
samplers.

Reason: a backend-agnostic diagnostics package may be useful, but it does not match the
project objective. The selected position is to own the early optimization infrastructure
around THRML before that ecosystem matures.

## Evidence And Sources

- Extropic describes THRML as open-source software for developing algorithms for future TSUs:
  http://extropic.ai/writing/thermodynamic-computing-from-zero-to-one
- Tavily extraction on 2026-06-14 confirmed the Extropic essay states that `thrml` lets the
  open-source community develop TSU algorithms before hardware is commercially available.
- Tavily extraction on 2026-06-14 confirmed arXiv:2510.23972 describes THRML as a JAX/XLA
  simulation library for hardware EBMs, not as evidence of QUBO optimization speedup.
- THRML documentation describes the runtime as JAX block-Gibbs sampling over nodes, factors,
  programs, and graph-colored blocks: https://docs.thrml.ai/
- THRML architecture documentation cautions that sampling is difficult and Gibbs is not a
  universal speed solution: https://docs.thrml.ai/en/latest/architecture
- THRML parallel tempering PR #30 indicates emerging interest in composing beta-ladder
  samplers above existing block-sampling programs:
  https://github.com/extropic-ai/thrml/pull/30

## Files Updated

- `README.md`
- `PROJECT_BRIEF.md`
- `CLAUDE.md`
- `spec.md`
- `reference/00-roadmap/README.md`
- `reference/00-roadmap/stage-02-thrml-optimization-runtime.md`
- `reference/00-roadmap/stage-03-diagnostics-pipeline.md`
- `reference/research-gaps.md`
- `reference/03-samplers/thrml-optimization-runtime.md`
- `reference/01-architecture/thrml-runtime.md`
- `reference/04-diagnostics/mixing-quality.md`

## Verification Plan

Run the unit test suite after documentation edits. Also scan edited Markdown for forbidden
one-line display-math blocks.

## Prose Audit

Second pass requested a technical research tone matching the local THRML/Jelinčič paper
style. I reviewed
`reference/01-architecture/papers/jelincic-2025-probabilistic-hardware-architecture.md` and
its lab note. The useful pattern is:

- state the computational problem;
- identify the primitive mechanism;
- state what the proposed layer adds;
- state what is measured;
- state which claims are not yet supported.

Edits made in response:

- removed rhetorical framing such as "strategic premise" and "center of gravity";
- replaced positioning language with the concrete division of labor among QUBO/BQM inputs,
  THRML, and Gibbsiq;
- clarified that fixed-beta Gibbs is a validation target, not the final optimization
  strategy;
- added the missing README `Background` section heading so subsection numbering is coherent;
- checked README math rendering constraints: display equations use multiline `$$` blocks,
  and the Ising convention uses `\lt` rather than a literal `<`.
