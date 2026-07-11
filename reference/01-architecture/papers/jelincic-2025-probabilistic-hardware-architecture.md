# Jelinčič 2025 Source Guide and Withdrawal Notice

> Citation: A. Jelinčič, O. Lockwood, A. Garlapati, P. Schillinger, I. L. Chuang,
> G. Verdon, and T. McCourt, "An efficient probabilistic hardware architecture for
> diffusion-like models," arXiv:2510.23972v2, 2025.
>
> Primary sources: [arXiv record](https://arxiv.org/abs/2510.23972) and the
> [local PDF](./jelincic-2025-probabilistic-hardware-architecture.pdf).
>
> Local PDF SHA-256:
> `940e61b13e9387d05c9380249ad3694f32cd07b18157cbf789d82888eee6b696`.

## Integrity Status

This file replaces a generated Markdown document that described itself as a faithful
transcription of all 42 PDF pages. A primary-source audit on 2026-07-11 found invented prose,
incorrect circuit descriptions, and unit errors spanning at least 6 to 12 orders of
magnitude. The previous derivative is withdrawn. This replacement is a page-scoped reading
guide and must not be cited as a transcript or quoted as the authors' prose.

The PDF and arXiv version are authoritative. Mathematical conventions used by Gibbsiq are
authoritative only in
[`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).

## Verified Claims

- The paper proposes an all-transistor probabilistic computer for denoising models. Its
  abstract reports a system-level projection of approximately 10,000 times less energy than
  GPUs at performance parity on a simple image benchmark. This is a modeled projection for a
  proposed device architecture.
- PDF page 5 states that the authors developed a GPU simulator of a future hardware device,
  trained a denoising thermodynamic model on Fashion-MNIST, and estimated device energy with
  a physical model.
- Equations 10 and 11 on PDF page 5 define the paper's Boltzmann-machine energy and Gibbs
  conditional. The experimental models usually use `L = 70` grids, degree-12 connectivity,
  and bipartite two-color block updates.
- PDF page 6 reports an approximately 100 ns measured RNG autocorrelation decay. It gives the
  system model `E = T * K_mix * L^2 * E_cell`, uses `K_mix = 250` for the DTM, and estimates
  `E_cell` at approximately 2 fJ.
- Appendix J, PDF page index 25, reports random-bit generation at approximately 10 MHz and
  approximately 350 aJ per bit from shot noise in subthreshold transistors.
- Appendix D.4, PDF page index 29, estimates the complete denoising-model cost at
  approximately `1.6 * T nJ`, where `T` is the number of denoising steps. The paper labels
  this an estimate derived from a physical model.

## Convention Boundary

The paper places `beta` and a leading minus sign inside its Equation 10 energy and sums over
`i != j`. Gibbsiq instead defines one canonical upper-triangular objective:

```text
E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j
```

The paper's Equation 11 therefore cannot be copied directly into Gibbsiq without reconciling
the sign, placement of `beta`, and pair-counting convention. Gibbsiq's audited conditional is
`sigmoid(-2 * beta * gamma_i)` under its own energy definition.

## Scope Boundary

The paper studies generative-model sampling and device-level projections. It does not report
a Gibbsiq run, a QUBO optimization benchmark, a production TSU backend measurement, or a
comparison against the classical optimization baselines required by this repository.
Consequently, its energy and speed projections provide architectural motivation only.

## Withdrawn Derivative Errors

The 2026-07-11 audit confirmed these failures in the previous Markdown derivative:

| Previous derivative claim | Primary PDF evidence |
| --- | --- |
| RNG implemented with an LFSR and Gaussian filtering | The device uses shot-noise dynamics of subthreshold transistors; the PDF contains no `LFSR` occurrence. |
| Approximately 1 MHz at approximately 350 microjoules per bit | Appendix J reports approximately 10 MHz at approximately 350 attojoules per bit. |
| Approximately 1.6 fJ for a complete denoising run | Appendix D.4 reports approximately `1.6 * T nJ`. |
| A small FPGA Boltzmann-machine validation | The PDF contains no `FPGA` occurrence. |
| Every page was faithfully transcribed | Sentence-level comparison and the errors above disprove that provenance claim. |

See the companion
[`jelincic-2025-probabilistic-hardware-architecture.note.md`](./jelincic-2025-probabilistic-hardware-architecture.note.md)
for the limited connection to Gibbsiq.
