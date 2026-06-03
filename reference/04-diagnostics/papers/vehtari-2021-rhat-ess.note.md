# Lab note — An Improved $\hat{R}$ for Assessing MCMC Convergence

> **Paper.** A. Vehtari, A. Gelman, D. Simpson, B. Carpenter, and P.-C. Bürkner.
> "Rank-Normalization, Folding, and Localization: An Improved $\hat{R}$ for
> Assessing Convergence of MCMC (with Discussion)." *Bayesian Analysis* 16(2)
> (2021).
> DOI: [10.1214/20-ba1221](https://doi.org/10.1214/20-ba1221) · BibTeX `vehtari2021`.
> Transcript: [`vehtari-2021-rhat-ess.md`](./vehtari-2021-rhat-ess.md).

## What the paper does

The paper repairs the two diagnostics every multi-chain MCMC run leans on: the
potential scale reduction factor $\hat{R}$ and the effective sample size (ESS).
Split-$\hat{R}$ compares the between-chain variance $B$ and within-chain variance
$W$ via the overestimating mixture $\widehat{\mathrm{var}}^{+}(\theta\mid y) =
\tfrac{N-1}{N}W + \tfrac{1}{N}B$ and reports $\hat{R} = \sqrt{\widehat{\mathrm{var}}^{+}/W}$,
which should decline to 1 as the chains mix. The authors show this fails silently in
two regimes: chains that share a mean but differ in variance, and heavy-tailed
(e.g. Cauchy) targets where the second moments $\hat{R}$ depends on do not exist —
in both, traditional $\hat{R}\approx 1$ despite gross non-convergence. Their fix is
to compute $\hat{R}$ on *rank-normalized* draws: replace each value by its pooled
rank $r^{(mn)}$, then apply the Blom inverse-normal transform
$z^{(mn)} = \Phi^{-1}\!\big(\tfrac{r^{(mn)} - 3/8}{S - 1/4}\big)$. Ranks make the
statistic invariant to monotone reparameterization and well-defined without finite
moments. To catch equal-location/different-scale failures they also *fold* about the
median, $\zeta^{(mn)} = |\theta^{(mn)} - \mathrm{median}(\theta)|$, and report the
maximum of rank-normalized split-$\hat{R}$ and folded-split-$\hat{R}$.

For efficiency the paper combines per-chain autocorrelations $\hat{\rho}_{t,m}$ with
the multi-chain variance into $\hat{\rho}_t = 1 - (W - \tfrac{1}{M}\sum_m s_m^2\hat{\rho}_{t,m})/\widehat{\mathrm{var}}^{+}$,
then truncates via Geyer's initial-positive-sequence rule to get
$S_{\mathrm{eff}} = NM/\big(1 + 2\sum_t \hat{\rho}_t\big)$. Because between-chain
information enters, stuck chains drive $S_{\mathrm{eff}}$ down toward the number of
distinct modes, so ESS itself flags multimodality. They localize this into *bulk-ESS*
(rank-normalized draws) and *tail-ESS* (minimum of the 5%/95% quantile efficiencies),
plus a quantile-MCSE method and rank plots replacing trace plots. The headline
practice rules: run $\ge 4$ chains, treat $\hat{R} < 1.01$ as the convergence
threshold, and require rank-normalized ESS $> 400$ before trusting any estimate.

## Why it matters to Gibbsiq

- **It is the reference spec for the diagnostics layer (layer 3).** Gibbsiq's
  planned R-hat-style `chain_disagreement` flag and ESS estimate should be the
  rank-normalized split-$\hat{R}$ and bulk/tail $S_{\mathrm{eff}}$ defined here, not
  the legacy second-moment versions — the paper's whole point is that the naive forms
  pass non-converged chains.
- **The folded-$\hat{R}$ + bulk/tail-ESS split maps onto our failure flags.** Equal-
  location/different-scale stalls (caught by folding) and mode-stuck chains (caught by
  multi-chain ESS collapsing to the mode count) are exactly the `mode_collapse` and
  `chain_disagreement` conditions Gibbsiq must raise; the paper gives the principled
  estimators behind those flags.
- **It supplies concrete numeric contracts.** The $\hat{R} < 1.01$ and ESS $> 400$
  thresholds, the $\ge 4$-chain default, and the rank-then-inverse-normal transform are
  the defaults the diagnostics layer and its fixtures should encode.
- **It motivates a non-negotiable failure case.** A constant or near-constant trace
  must never yield a healthy ESS; the autocorrelation/initial-positive-sequence
  machinery here is what an honest implementation owes, and is among the cases the
  evaluation framework forbids passing.

## Reading-list hooks

- Diagnostics-layer design and mixing metrics →
  [`../mixing-quality.md`](../mixing-quality.md).
- Sampler diagnostic benchmarks that exercise these estimators →
  [`./turner-2018-sampler-diagnostics.md`](./turner-2018-sampler-diagnostics.md).
- Where ESS / R-hat-style flags live in the stack and the constant-trace failure case
  → `CLAUDE.md` ("Architecture" layer 3; evaluation "Non-Negotiable Failure Cases").
