# Lab note — How well does your sampler really work?

> **Paper.** R. Turner and B. Neal. "How well does your sampler really work?"
> *Proceedings of the 34th Conference on Uncertainty in Artificial Intelligence (UAI)*, 2018.
> arXiv:[1712.06006](https://arxiv.org/abs/1712.06006) · BibTeX `turner2018`.
> Transcript: [`turner-2018-sampler-diagnostics.md`](./turner-2018-sampler-diagnostics.md).

## What the paper does

The paper builds a data-driven benchmark — explicitly modelled on the COCO platform for
optimizers — that measures how well MCMC samplers actually estimate quantities on realistic
posteriors, rather than on hand-crafted toy targets. The pipeline runs in six phases: collect a
"data set of data sets" (2,200 OpenML problems), run NUTS on a model zoo to get long chains,
fit flexible *surrogate* densities (mixture of Gaussians, RNADE, Real NVP) that admit a black-box
unnormalized density $\tilde p$ and fast exact iid sampling, run candidate samplers on those
surrogates under a fixed 15-minute CPU budget, and finally score each chain against $\sim 10^6$
ground-truth iid draws. Because exact samples exist, the authors can measure the *real* effective
sample size instead of the linear-autocorrelation estimate. The standard ESS rescales the
mean-estimation error,
$$\text{ESS} := \frac{\operatorname{Var}_{p^*}[\bar x_d]}{\mathbb{E}_q[(\hat\mu_d-\mu_d)^2]} \in \mathbb{R}^+,$$
which they generalize to arbitrary estimators $\hat\theta$ (mean, variance, KS) as the real ESS,
$\text{RESS} := RK / \sum_{k=1}^K(\bar\theta_k-\theta)^2$, and aggregate into efficiency (EFF) and
normalized (NESS) variants. A meta-analysis then GP-regresses an "ESS deviation" target on the
classical diagnostics (ESS, Gelman–Rubin, Geweke) plus dimension $D$ to ask how predictive each
diagnostic really is.

The headline empirical findings: sampler performance is *bimodal* — a chain either reaches a usable
efficiency or collapses to RESS $< 1$ (using MacKay's rule-of-12 as the iid-success threshold) — and
the standard ESS diagnostic is **optimistically biased**, falling below its own 95% lower error bar
55% of the time for the mean, 68% for variance, and 83% for the KS statistic, far above the nominal
2.5%. NUTS and HMC dominate per-sample, while cheaper random-walk Metropolis proposals trade
efficiency for raw throughput.

## Why it matters to Gibbsiq

- **Direct charter for diagnostics layer 3.** Gibbsiq promises an "ESS-style estimate" and
  best-so-far/autocorrelation traces; this paper is the cautionary evidence that an
  autocorrelation-based ESS *systematically overstates* how good a chain is. Our ESS estimator
  should be reported as a hopeful upper bound, never as a feasibility guarantee.
- **Justifies the failure-flag philosophy.** The paper's central message is that diagnostics have
  no Type-II guarantee — a poorly mixing chain can pass quietly. That is exactly why Gibbsiq treats
  health flags (`mode_collapse`, `chain_disagreement`, `no_recent_improvement`) as part of the
  solver *contract* rather than a single trusted scalar.
- **Multi-chain disagreement is the right backstop.** The Gelman–Rubin within-vs-between-chain
  variance ratio motivates Gibbsiq's R-hat-style `chain_disagreement` flag run across independent
  THRML restarts; the bimodal collapse result argues for always sampling several chains.
- **Ground-truth-against-exact-iid mirrors our benchmark oracle.** Scoring chains against exact
  samples instead of self-reported numbers is the same discipline as Gibbsiq's strict
  `benchmark_oracle.py`, which recomputes objectives from the input model rather than trusting a
  candidate's claims.

## Reading-list hooks

- Rank-normalized R-hat and ESS, the modern refinement of the diagnostics critiqued here →
  [`./vehtari-2021-rhat-ess.md`](./vehtari-2021-rhat-ess.md).
- Mixing-quality design notes for the diagnostics layer →
  [`../mixing-quality.md`](../mixing-quality.md).
- Diagnostics-first solver contract and failure flags → `CLAUDE.md` ("Architecture (target
  design)", layer 3) and the non-negotiable failure cases in
  [`../../08-evaluation/evaluation-framework.md`](../../08-evaluation/evaluation-framework.md)
  (constant trace must not yield a healthy ESS).
