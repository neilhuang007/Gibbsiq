# Lab Note - Probabilistic Hardware for Diffusion-Like Models

> Paper: A. Jelinčič et al., "An efficient probabilistic hardware architecture for
> diffusion-like models," arXiv:2510.23972v2, 2025.
>
> Primary source: [local PDF](./jelincic-2025-probabilistic-hardware-architecture.pdf).
> Verified source guide:
> [`jelincic-2025-probabilistic-hardware-architecture.md`](./jelincic-2025-probabilistic-hardware-architecture.md).

## What The Paper Establishes

The paper proposes a denoising thermodynamic computer architecture built from sparse
Boltzmann-machine layers and all-transistor random-bit circuits. PDF page 5 describes a GPU
simulator used to study a future device. Its common experimental topology is an `L = 70`
grid with degree-12 connectivity and two-color block-Gibbs updates. PDF page 6 combines
measured RNG behavior with modeled bias, clock, and communication costs to estimate a future
device's energy.

The evidence has distinct levels. The approximately 100 ns RNG autocorrelation on PDF page 6
and the approximately 10 MHz, 350 aJ-per-bit values in Appendix J are circuit measurements.
The approximately 2 fJ `E_cell` value and the approximately `1.6 * T nJ` complete-program
value are outputs of a system-level physical model. The abstract's approximately 10,000-fold
energy comparison is therefore a projection for a simple generative-model benchmark.

## Connection To Gibbsiq

- Sparse neighbor interactions and two-color updates motivate graph-aware blocks in the
  THRML runtime.
- The paper's local Gibbs conditional makes sign and factor auditing essential. Its Equation
  10 uses a different sign, beta placement, and pair-sum convention from Gibbsiq, so
  [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md) remains the
  implementation authority.
- The paper links autocorrelation to mixing behavior. Gibbsiq records autocorrelation, ESS,
  chain disagreement, and diversity as health telemetry rather than optimality evidence.

## Limits On Transfer

The paper supplies no QUBO benchmark, witness-verified optimum, fixed-work comparison,
fixed-time comparison, or production TSU result. Gibbsiq must establish those claims through
its own runtime artifacts, exact oracles, and independently configured classical baselines.
THRML's official documentation currently describes the public library as a JAX-based GPU
simulator for programs intended for future Extropic hardware.

## Reading Hooks

- THRML lowering and block controls: [`../thrml-runtime.md`](../thrml-runtime.md).
- Canonical energy and Gibbs sign:
  [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).
- Sampler health diagnostics: [`../../04-diagnostics/`](../../04-diagnostics/).
- Primary-source audit record:
  [`../../research-journal/2026-07-11-primary-source-integrity-audit.md`](../../research-journal/2026-07-11-primary-source-integrity-audit.md).
