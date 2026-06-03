# Lab note — Probabilistic hardware for diffusion-like models

> **Paper.** A. Jelinčič, O. Lockwood, A. Garlapati, P. Schillinger, I. Chuang,
> G. Verdon, and T. McCourt. "An efficient probabilistic hardware architecture for
> diffusion-like models." arXiv preprint, 2025.
> arXiv:[2510.23972](https://arxiv.org/abs/2510.23972) · BibTeX `jelincic2025`.
> Transcript: [`jelincic-2025-probabilistic-hardware-architecture.md`](./jelincic-2025-probabilistic-hardware-architecture.md).

## What the paper does

The paper proposes a transistor-level hardware accelerator that performs Gibbs
sampling for energy-based and diffusion-like generative models by exploiting the
locality of sparse probabilistic graphical models. An EBM defines
$p(\mathbf{x}) = \tfrac{1}{Z}\exp(-\beta E(\mathbf{x}))$, and Gibbs sampling updates
each variable from its conditional, which for a sparse model depends only on a
variable and its graph neighbors:
$p(x_i \mid \mathbf{x}_{\neg i}) \propto \exp\!\big(-\beta\,\tfrac{\partial E}{\partial x_i}\,x_i\big)$.
The design instantiates one sampling cell per variable — each holding state,
receiving neighbor states, computing a local bias, and emitting a stochastic bit —
so cells run in parallel with only nearest-neighbor communication, optionally
synchronized by graph color classes. For a Boltzmann machine the cell realizes the
binary conditional $p(x_i = 1 \mid \mathbf{x}_{\text{neighbors}}) = \sigma(\theta_i)$,
where the bias $\theta_i$ is a linear combination of neighbor states and weights. A
resistor-network biasing circuit computes the multiply-accumulate
$V_b = \sum_j G_j V_{dd}\, y_j$ (with $y_j = x_j \oplus s_j$ encoding signed weights),
and a comparator fed by a Gaussian noise source produces a bit with probability
$P(\text{out}=1) = \sigma(V_b / V_T)$, matching the sigmoid conditional in silicon.

The authors give a full energy model,
$E = T(E_{\text{samp}} + E_{\text{init}} + E_{\text{read}})$ with
$E_{\text{samp}} = KN(E_{\text{rng}} + E_{\text{bias}} + E_{\text{clock}} + E_{\text{nb}})$,
finding neighbor communication and biasing dominate, and report fJ-scale energy per
sample for a 1024-node denoising model — orders of magnitude below GPU sampling.
Appendix G ties sampler quality to spectral mixing: the normalized autocorrelation
decays asymptotically as $r_{yy}[k] \approx C\,\sigma_2^{k}$ in the second-largest
transition-matrix eigenvalue, and an Adaptive Correlation Penalty tunes the energy
landscape during training using the measured autocorrelation so the chain mixes
within the available number of Gibbs steps.

## Why it matters to Gibbsiq

- **It is the hardware statement of the THRML block-Gibbs runtime (layer 2).** The
  per-variable cell with local-field bias, neighbor messaging, and color-class
  synchronization is exactly the lowering Gibbsiq's runtime performs onto THRML
  nodes/blocks/factors; the color-synchronized update maps to block Gibbs over a
  graph coloring.
- **The cell conditional is the audited Gibbs sign.** The Boltzmann cell draws
  $x_i = 1$ with probability $\sigma(\theta_i)$ where $\theta_i$ is the local bias —
  the same single-site conditional Gibbsiq fixes as `sigmoid(-2 * beta * gamma_i)`
  with $\gamma_i = h_i + \sum_j J_{ij} s_j$. Reconciling the $\{0,1\}$ hardware
  convention and signed-weight encoding ($y_j = x_j \oplus s_j$) against Gibbsiq's
  $\{-1,+1\}$ upper-triangle energy is the kind of sign/factor check the equation
  audit exists to catch.
- **Autocorrelation and $\sigma_2$ mixing are the diagnostics contract (layer 3).**
  The paper's $r_{yy}[k] \approx C\,\sigma_2^{k}$ analysis and its mixing-time-driven
  penalty are the physical-side justification for Gibbsiq's autocorrelation / ESS /
  mode-collapse diagnostics: a slowly decaying autocorrelation (large $\sigma_2$) is
  precisely the unhealthy-mixing condition Gibbsiq must flag.

## Reading-list hooks

- THRML lowering and block-Gibbs schedule/seed/color controls →
  [`../thrml-runtime.md`](../thrml-runtime.md).
- Single-site Gibbs conditional and sign convention → `CLAUDE.md` → "Canonical
  conventions", audited in
  [`../../08-evaluation/equation-audit.md`](../../08-evaluation/equation-audit.md).
- p-bit / probabilistic-computing lineage this hardware extends →
  [`../../05-theory/papers/camsari-2018-probabilistic-spin-logic.note.md`](../../05-theory/papers/camsari-2018-probabilistic-spin-logic.note.md).
- Autocorrelation / ESS / R-hat mixing diagnostics this informs →
  [`../../04-diagnostics/`](../../04-diagnostics/).
