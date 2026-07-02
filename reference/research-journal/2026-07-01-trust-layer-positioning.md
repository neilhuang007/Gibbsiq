# 2026-07-01 - Trust-Layer Positioning Decision

## Paper Hook

Sharpens the system framing and limitations sections: Gibbsiq is the optimization and trust
layer above THRML, and its durable contribution is independent verification and diagnostics
rather than a low-level programming layer for the hardware.

## Context

The 2026-06-14 decision fixed Gibbsiq as THRML-native optimization infrastructure with
diagnostics as required telemetry. A strategic assessment on 2026-07-01, backed by fresh
research, refined two points that the documents left ambiguous. First, the general programming
layer for thermodynamic sampling units is THRML itself, which Extropic owns; Gibbsiq should
not be framed as a PyTorch-like programming layer for that hardware class. Second, ingestion
and IR-to-THRML lowering could be commoditized by a future Extropic-owned optimization SDK, so
the part of Gibbsiq that must survive is the independent verification and diagnostics contract,
which a hardware vendor cannot credibly supply for its own device.

## Decision

Encode the trust-layer framing across the authoritative documents:

- Gibbsiq is the optimization and trust layer above THRML. The accurate analogy is Ocean and
  dimod for D-Wave plus ArviZ for Stan and PyMC, applied to the THRML ecosystem.
- The durable moat is independent verification and diagnostics. Ingestion and lowering may
  later be absorbed by an Extropic-owned SDK; the verification and diagnostics contracts
  remain.
- Execution stays THRML-first. The runtime contracts — the `SampleResult` schema, the
  diagnostic inputs, and the witness-recomputing benchmark oracle — are specified to be
  backend-portable at the architectural level, as a hedge that keeps the same audited
  artifacts useful for the wider Ising-machine field if the THRML hardware path is delayed.
- Adoption and ecosystem work is an explicit parallel-track concern: flagship examples that
  reproduce third-party THRML optimization results with Gibbsiq diagnostics attached, upstream
  THRML contributions in the parallel-tempering and sampler-abstraction area, and publishing
  the ground-truth corpus as a standalone independent verification suite.

## Rejected Alternative

Rejected again: pivoting Gibbsiq into a backend-agnostic diagnostics product for QUBO samplers.
Contract-level portability is retained as a hedge, but the execution target and the design
center remain THRML. Also rejected: positioning Gibbsiq as a general PyTorch-like programming
layer for thermodynamic sampling units, because that role belongs to THRML.

## Evidence And Sources

- Z1 was announced in Oct 2025 for early access in 2026, with no evidence of general
  availability as of 2026-07; THRML (v0.1.3, ~1.1k GitHub stars) has no hardware backend and
  runs as JAX GPU simulation: https://github.com/extropic-ai/thrml and https://extropic.ai
- Extropic hardware primitives include categorical types (PBIT, PDIT, PMODE, PMOG):
  https://extropic.ai/hardware. Extropic's June 2026 optimization paper uses Ising/Potts
  sampling: arXiv:2606.17327 (codon optimization).
- Third-party THRML uptake in H1 2026 skews toward optimization: portfolio index tracking
  arXiv:2601.07792 (Jan 2026) and a Max-k-Cut Potts study arXiv:2605.06425, plus community
  Max-Cut repositories.
- Funding context: only Extropic's $14.1M seed (Dec 2023) is confirmed, while Normal Computing
  raised $50M (Samsung Catalyst, Mar 2026), indicating company-viability risk on the hardware
  bet.
- Ecosystem gap: no existing QUBO/Ising tool (Ocean/dimod, PyQUBO, OpenJij, Fixstars Amplify,
  qubolite, MQLib, simulated-bifurcation libraries) ships sampler-health diagnostics, failure
  flags, or witness-verified benchmark oracles; multiple 2025-26 papers call Ising-machine
  benchmark standardization an open problem.
- THRML parallel-tempering PR #30 remains the upstream point for beta-ladder and
  sampler-abstraction composition: https://github.com/extropic-ai/thrml/pull/30

## Files Updated

- `README.md`
- `PROJECT_BRIEF.md`
- `CLAUDE.md`
- `spec.md`
- `reference/00-roadmap/README.md`
- `reference/research-gaps.md`
- `reference/claims-evidence-map.md`

## Verification Plan

Run `python tools/check_markdown_math.py` on the edited Markdown and confirm no one-line
display-math blocks remain. Run the unit test suite
(`$env:PYTHONPATH="src"; python -m unittest discover -s test_suite/tests`) to confirm the
documentation edits did not affect code behavior.
