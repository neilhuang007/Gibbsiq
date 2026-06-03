# Rank-Normalization, Folding, and Localization: An Improved $\hat{R}$ for Assessing Convergence of MCMC


> **Citation.** Canonical entry `vehtari2021` in [`references.bib`](../../references.bib) (resolved via Crossref/DataCite). DOI [10.1214/20-ba1221](https://doi.org/10.1214/20-ba1221).
>
> **Companion note.** [`vehtari-2021-rhat-ess.note.md`](./vehtari-2021-rhat-ess.note.md) — how this paper links to Gibbsiq.

Aki Vehtari¹, Andrew Gelman², Daniel Simpson³, Bob Carpenter⁴, and Paul-Christian Bürkner¹

¹Department of Computer Science, Aalto University, Finland. Aki.Vehtari@aalto.fi
²Department of Statistics, Columbia University, New York
³Department of Statistical Sciences, University of Toronto, Canada
⁴Center for Computational Mathematics, Flatiron Institute, New York
¹Department of Computer Science, Aalto University, Finland

Published in: *Bayesian Analysis*

DOI: [10.1214/20-BA1221](https://doi.org/10.1214/20-BA1221)

Published: 01/06/2021

## Abstract

Markov chain Monte Carlo (MCMC) methods are important in computational statistics, especially in Bayesian applications where the goal is to represent posterior inference using a sample of posterior draws. While MCMC, as well as more general iterative simulation algorithms, can usually be proven to converge to the target distribution as the number of draws approaches infinity, there are rarely strong guarantees about their behavior after finite time. Indeed, decades of experience tell us that the finite sample behavior of these algorithms can be almost arbitrarily bad.

We show that the convergence diagnostic $\hat{R}$ of Gelman and Rubin (1992) has serious flaws. Traditional $\hat{R}$ will fail to correctly diagnose convergence failures when the chain has a heavy tail or when the variance varies across the chains. In this paper we propose an alternative rank-based diagnostic that fixes these problems. We also introduce a collection of quantile-based local efficiency measures, along with a practical approach for computing Monte Carlo error estimates for quantiles. We suggest that common trace plots should be replaced with rank plots from multiple chains. Finally, we give recommendations for how these methods should be used in practice.

## 1 Introduction

Markov chain Monte Carlo (MCMC) methods are important in computational statistics, especially in Bayesian applications where the goal is to represent posterior inference using a sample of posterior draws. While MCMC, as well as more general iterative simulation algorithms, can usually be proven to converge to the target distribution as the number of draws approaches infinity, there are rarely strong guarantees about their behavior after finite time. Indeed, decades of experience tell us that the finite sample behavior of these algorithms can be almost arbitrarily bad.

### 1.1 Monitoring convergence using multiple chains

In an attempt to assuage concerns of poor convergence, we typically run multiple independent chains to see if the obtained distribution is similar across chains. We can also visually inspect the sample paths of the chains via trace plots as well as study summary statistics such as the empirical autocorrelation function.

Running multiple chains is critical to any MCMC convergence diagnostic. Figure 1 illustrates two ways in which sequences of iterative simulations can fail to converge. In the first example, two chains are in different parts of the target distribution; in the second example, the chains move but have not attained stationarity. Some mixing can arise with multimodal target distributions or when a chain is stuck in a region of high curvature with a step size too large to make an acceptable proposal for the next step. The two examples in Figure 1 make it clear that any method for assessing mixing and effective sample size should use information between and within chains.

As we are often fitting models with large numbers of parameters, it is not realistic to expect to manually inspect trace plots such as in Figure 1 for all quantities of interest. Hence we need numerical summaries that can flag potential problems.

Of the various convergence diagnostics (see reviews by Cowles and Carlin, 1996; Mengersen et al., 1999; Robert and Casella, 2004), probably the most widely used is the potential scale reduction factor $\hat{R}$ (Gelman and Rubin, 1992; Brooks and Gelman, 1998). It is recommended as the primary convergence diagnostic in widely applied software packages for MCMC sampling such as Stan (Carpenter et al., 2017), JAGS (Plummer, 2003), WinBUGS (Lunn et al., 2000), OpenBUGS (Lunn et al., 2009), PyMC3 (Salvatier et al., 2016), and NIMBLE (de Valpine et al., 2017), which together are estimated to have hundreds of thousands of users. $\hat{R}$ is computed for each scalar quantity of interest, as the standard deviation of that quantity from all the chains included together, divided by the root mean square of the separate within-chain standard deviations. The idea is that if a set of simulations have not mixed well, the variance of all the chains mixed together should be higher than the variance of individual chains. More recently, Gelman et al. (2013) introduced split-$\hat{R}$ which also compares the first half of each chain to the second half to try to detect lack of convergence within each chain. In this paper when we refer to $\hat{R}$ we are always speaking of the split-$\hat{R}$ variant.

Convergence diagnostics are most effective when computed using multiple chains initialized at a diverse set of starting points. This reduces the chance that we falsely diagnose mixing when beginning at a different point would lead to a qualitatively different posterior.

In the context of Markov chain Monte Carlo, one can interpret $\hat{R}$ with diverse seeding as an operationalization of the qualitative statement that, after warmup, convergence of the Markov chain should be relatively insensitive to the starting point, at least within a reasonable part of the parameter space. This is the closest we can come to verifying empirically that the Markov chain is geometrically ergodic, which is a critical property if we want a central limit theorem to hold for approximate posterior expectations. Without this, we have no control over the large deviation behavior of the estimates and the constructed Markov chains may be useless for practical purposes.

### 1.2 Example where traditional $\hat{R}$ fails

Unfortunately, $\hat{R}$ can fail to diagnose poor mixing, which can be a problem when it is used as a default rule. The following example shows how failure can occur.

The red histograms in Figure 2 show the distribution of $\hat{R}$ (that is, split-$\hat{R}$ from Gelman et al. (2013)) in four different scenarios. (Ignore the light blue histograms for now; they show the results using an improved diagnostic that we shall discuss later in this paper.) In all four scenarios, traditional $\hat{R}$ is well under 1.1 under all simulations, thus not detecting any convergence problems—but in fact the two scenarios on the left have been constructed so that they are far from mixed. These are problems that are not detected by traditional $\hat{R}$.

In each of the four scenarios in Figure 2, we run four chains for 1000 iterations each and then replicate the entire simulation 1000 times. The top row of the figure shows results for independent AR(1) processes with autoregressive parameter $\rho = 0.3$. The top left graph shows the distribution of $\hat{R}$ when one of the four chains is manually transformed to only have $1/3$ of the variance compared to the other three chains (see Vehtari et al. (2020), Appendix A for more details). This corresponds to a scenario where one chain fails to correctly explore the tails of the target distribution and one would hope could be identified as non-convergent. The split-$\hat{R}$ statistic defined in Gelman et al. (2013) does not detect the poor mixing, while the new variant of split-$\hat{R}$ defined later in this paper does. The right-top figure shows the same scenario but with all the chains having the same variance, and now both $\hat{R}$ values correctly identify that mixing occurs.

The second row of Figure 2 shows the behavior of $\hat{R}$ when the target distribution has infinite variance. In this case the chains were constructed as a ratio of stationary AR(1) processes with $\rho = 0.3$, and the distribution of the ratio is Cauchy. All of the simulated chains have unit scale, but in the lower-left figure, we have manually shifted one of the four chains two units to the right. This corresponds to a scenario where one chain provides a biased estimate of the target distribution. The Gelman et al. (2013) version of $\hat{R}$ would catch this behavior if the chain had finite variance, but in this case the infinite variance destroys its effectiveness—traditional $\hat{R}$ and split-$\hat{R}$ are defined based on second-moment statistics—and it inappropriately returns a value very close to 1.

This example identified two problems with traditional $\hat{R}$:

1. If the chains have different variances but the same mean parameters, traditional $\hat{R} \approx 1$.

2. If the chains have infinite variance, traditional $\hat{R} \approx 1$ even if one of the chains has a different location parameter to the others. This can also lead to numerical instability for thick-tailed distributions even when the variance is technically finite. It's typically hard to assess empirically if a chain has large but finite variance or infinite variance.

A related problem is that $\hat{R}$ is typically computed only for the posterior mean. While this provides an estimate for the convergence in the bulk of the distribution, it says little about the convergence in the tails, which is a concern for posterior interval estimates as well as for inferences about rare events.

## 2 Recommendations for practice

The traditional $\hat{R}$ statistic is general, easy to compute, and can catch many problems of poor convergence, but the discussion above reveals some scenarios where it fails. The present paper proposes improvements that overcome these problems. In addition, as the convergence of the Markov chain needs not be uniform across the parameter space, we propose a localized version of effective sample size that allows us to assess better the behavior of localized functionals and quantiles of the chain. Finally, we propose three new methods to visualize the convergence of an iterative algorithm that are more informative than standard trace plots.

In this section we lay out practical recommendations for using the tools developed in this paper. For the sake of specificity, we have provided numerical targets for both $\hat{R}$ and effective sample size (ESS), which are useful as first level checks when analyzing reliability of inference for many quantities. However, these values should be adapted as necessary for the given application, and ultimately domain expertise should be used to check that Monte Carlo standard errors (MCSE) for all quantities of interest are small enough.

In Section 4, we propose modifications to $\hat{R}$ based on rank-normalizing and folding the posterior draws, only using the sample if $\hat{R} < 1.01$. This threshold is much tighter than the one recommended by Gelman and Rubin (1992), reflecting lessons learnt over more than 25 years of use, as well as the simulation results in Appendix A. Gelman and Rubin (1992) derived $\hat{R}$ under the assumption that, as simulations went forward, the within-chain variance would gradually increase while the between-chain variance decreased, stabilizing when their ratio was 1. The potential scale reduction factor represented the factor by which the between-chain variation might decline under future simulations, and a potential scale reduction factor of 1.1 implied that there was little to be gained by running the chains longer. However, as discussed by Brooks and Gelman (1998), the dynamics of MCMC are such that the between-chain variance can decrease before it increases, if the initial part of the simulation pulls all the chains to the center of the distribution, only for them to be re-dispersed with further simulation. As a result, $\hat{R}$ cannot in general be interpreted as a potential scale reduction factor, and in practice and in simulations we have found that $\hat{R}$ can dip below 1.1 well before convergence. As a point also raised by Vats and Knudson (2018)), and we have found this to be much more rare when using the 1.01 threshold.

In addition, we recommend running at least four chains by default. Multiple chains are more likely to reveal multimodality and poor adaptation or mixing: we see examples for complex, misspecified or non-identifiable models in the Stan discussion forum all the time. Furthermore, most computers are able to run chains in parallel, giving multiple chains with no increase in computation time. Here we do not consider massive parallelization such as running 1000 chains or more; further research is needed in considering how to use such simulations most efficiently in such computational environments (see, for instance, the method discussed in Jacob et al. (2017)).

Roughly speaking, the effective sample size of a quantity of interest captures how many independent draws contain the same amount of information as the dependent sample obtained by the MCMC algorithm. The higher the ESS the better. When there might be difficulties with mixing, it is important to use between-chain as well as within-chain information in computing the ESS. A common example arises in hierarchical models with funnel-shaped posteriors, where MCMC algorithms can struggle to simultaneously adapt to a "narrow" region of high density and low volume, and a "wide" region of low density and high volume. In such a case, differences in step-size adaptation can lead to chains that have different behaviors in the neighborhood of the narrow part of the funnel (Betancourt and Girolami, 2019). For multimodal distributions with well-separated modes, the split-$\hat{R}$ adjustment leads to an ESS estimate that is close to the number of distinct modes that are found. In this situation, ESS can be drastically overestimated if computed from a single chain.

A small value of $\hat{R}$ is not enough to ensure that an MCMC sample is useful in practice (Vats and Knudson, 2018). The effective sample size must also be large enough to get stable inferences for quantities of interest. Gelman et al. (2013) proposed an ESS estimate which combines autocorrelation-based single-chain variance estimates (Hastings, 1970; Geyer, 1992) from multiple chains using between- and within-chain information as in $\hat{R}$. In Section 3.2 we propose an improved algorithm, and as with $\hat{R}$, we recommend computing the ESS on the rank-normalized sample. This does not directly compute the mean of the parameter, but instead computes a quantity that is well defined even if the chains do not have finite mean or variance. Specifically, it computes the ESS of a sample from a *rank-normalized* version of the quantity of interest, using the rank transformation followed by the inverse normal transformation. This is still indicative of the effective sample size for computing an average, and if it is low the computed expectations are unlikely to be good approximations to the actual target expectations.

To ensure reliable estimates of variances and autocorrelations needed for $\hat{R}$ and ESS, we recommend requiring that the rank-normalized ESS is greater than 400, a number we chose based on practical experience and simulations (see Appendix A) as typically sufficient to get a stable estimate of the Monte Carlo standard error.

Finally, when reporting quantile estimates or posterior intervals, we strongly suggest assessing the convergence of the chains for these quantiles. In Section 4.3, we show that convergence of Markov chains is not uniform across the parameter space, that is, convergence might be different in the bulk of the distribution (e.g., for the mean or median) than in the tails (e.g., for extreme quantiles). We propose diagnostics and effective sample sizes specifically for extreme quantiles. This is different from the standard ESS estimate (which we refer to as bulk-ESS), which mainly assesses how well the centre of the distribution is resolved. Instead, these "tail-ESS" measures allow the user to estimate the MCSE for interval estimates.

## 3 $\hat{R}$ and the effective sample size

When coupled with an ESS estimate, $\hat{R}$ is the most common way to assess the convergence of a set of simulated chains. There is a link between these two measures for a single chain (see, e.g. Vats and Knudson, 2018), but we prefer to treat these as two separate questions: "Did the chains mix well?" (split-$\hat{R}$) and "Is the effective sample size large enough to get a stable estimate of uncertainty?" In this section we define the $\hat{R}$ and ESS statistics that we propose to modify.

### 3.1 Split-$\hat{R}$

Here we present split-$\hat{R}$, following Gelman et al. (2013) but using the notation of Stan Development Team (2018b). This formulation represents the current standard in convergence diagnostics for iterative simulations. In the equations below, $N$ is the number of draws per chain, $M$ is the number of chains, $S = MN$ is the total number of draws from all chains, $\theta^{(m)}$ is the average of draws from the $m$th chain, and $\bar{\theta}^{(\cdot)}$ is average of all draws. For each scalar summary of interest $\theta$, we compute $B$ and $W$, the between- and within-chain variances:

$$B = \frac{N}{M-1} \sum_{m=1}^{M} (\bar{\theta}^{(m)} - \bar{\theta}^{(\cdot)})^2, \quad \text{where} \quad \bar{\theta}^{(m)} = \frac{1}{N} \sum_{n=1}^{N} \theta^{(m)n}, \quad \bar{\theta}^{(\cdot)} = \frac{1}{M} \sum_{m=1}^{M} \bar{\theta}^{(m)}, \tag{3.1}$$

$$W = \frac{1}{M} \sum_{m=1}^{M} s_m^2, \quad \text{where} \quad s_m^2 = \frac{1}{N-1} \sum_{n=1}^{N} (\theta^{(mn)} - \bar{\theta}^{(m)})^2. \tag{3.2}$$

The between-chain variance, $B$, also contains the factor $N$ because it is based on the variance of the within-chain means, $\bar{\theta}^{(m)}$, each of which is an average of $N$ values $\theta^{(mn)}$. We can estimate var($\theta | y$), the marginal posterior variance of the estimand, by a weighted average of $W$ and $B$, namely,

$$\widehat{\text{var}}^{+}(\theta|y) = \frac{N-1}{N} W + \frac{1}{N} B. \tag{3.3}$$

This quantity *overestimates* the marginal posterior variance assuming the starting distribution of the simulations is appropriately overdispersed compared to the target distribution, but is *unbiased* under stationarity (that is, if the starting distribution equals the target distribution), or in the limit $N \to \infty$. To have an overdispersed starting distribution, independent Markov chains should be initialized with diffuse starting values for the parameters.

Meanwhile, for any finite $N$, the within-chain variance $W$ should *underestimate* var($\theta|y$) because the individual chains haven't had the time to explore all of the target distribution and, as a result, will have less variability. In the limit as $N \to \infty$, the expectation of $W$ also approaches var($\theta|y$).

We monitor convergence of the iterative simulations to the target distribution by estimating the factor by which the scale of the current distribution for $\theta$ might be reduced if the simulations were continued in the limit $N \to \infty$. This leads to the estimator

$$\hat{R} = \sqrt{\frac{\widehat{\text{var}}^{+}(\theta|y)}{W}}, \tag{3.4}$$

which for an ergodic process declines to 1 as $N \to \infty$. We call this split-$\hat{R}$ because we are applying it to chains that have been split in half so that $M$ is twice the number of simulated chains. Without splitting, $\hat{R}$ would get fooled by non-stationary chains as in Figure 1b.

In cases, where we can be absolutely certain that a single chain is sufficient, $\hat{R}$ could be computed using only single chain marginal variance and autocorrelations (see, e.g. Vats and Knudson, 2018). However we are willing to trade off a slightly higher variance for increased diagnostic sensitivity (as described in the introduction) that running multiple chains brings.

### 3.2 The effective sample size

We estimate effective sample size by combining information from $\hat{R}$ and the autocorrelation estimates within the chains.

#### The effective sample size and Monte Carlo standard error

Given $S$ independent simulation draws, the accuracy of average of the simulations $\bar{\theta}$ as an estimate of the posterior mean $E(\theta|y)$ can be estimated as

$$\text{Var}(\bar{\theta}) = \frac{\text{Var}(\theta)}{S}. \tag{3.5}$$

This generalizes to posterior expectations of functions of parameters $E(g(\theta)|y)$. The square root of (3.5) is called the Monte Carlo standard error (MCSE).

In general, the simulations of $\theta$ within each chain tend to be autocorrelated, and Var($\theta$) can be larger or smaller in expectation. In the early days of using MCMC for Bayesian inference, the focus was on estimating the single chain estimate variance directly, for example, based on autocorrelations or batch means (Hastings, 1970; Geyer, 1992). See more different variance estimation algorithms in reviews by Cowles and Carlin (1996), Mengersen et al. (1999), and Robert and Casella (2004). Interpreting whether Monte Carlo standard error for a quantity of interest is small enough requires domain expertise.

Effective sample size (ESS) can be computed by dividing any variance estimate for an MCMC estimate by the variance estimate assuming independent draws. As convergence diagnostics in general started to be more popular (Gelman and Rubin, 1992; Cowles and Carlin, 1996; Mengersen et al., 1999; Robert and Casella, 2001), eventually ESS also became popular as description of the efficiency of the simulation (an early example of reporting ESS for Gibbs sampler is Sorensen et al., 1995). The term effective sample size had already been used before, for example, to describe amount of information in climatological time series (Laumann and Gates, 1977) and the efficiency of importance sampling in Bayesian inference (Kong et al., 1994).

Although ESS is not a replacement for MCSE, it can provide a scale-free measure of information, which can be especially useful when diagnosing the sampling efficiency for a large number of variables. The downside of the term effective sample size is that it may give a false impression that the dependent simulation sample would be equivalent to an independent sample with size ESS, while the equivalence is only for the estimation efficiency of the posterior mean, and the efficiency of the same dependent simulation sample for estimating another posterior function $E(g(\theta)|y)$ or quantiles can be very different. To simplify notation, in this section we consider the effective sample size for the posterior mean $E(\theta|y)$. This can be generalized in a straightforward manner to ESS estimates for $E(g(\theta)|y)$. Section 4.3 deals with estimating the effective sample size of quantiles, which cannot be presented as expectations.

#### Estimating the effective sample size

The first proposals of ESS estimates used information only from a single chain (see, e.g. Sorensen et al., 1995). The convergence diagnostic package coda (Plummer et al., 2006) combines (since version 0.5.7 in 2001) single chain spectral variance based ESS estimates simply by summing them, but this approach gives over-optimistic estimates if spectral variances in different chains are not equal (e.g. when different step size is used in different chains) or if chains are not mixing well. Gelman et al. (2003) proposed an ESS estimate which appropriately combines autocorrelation information from multiple chains. Stan Development Team (2018b) made some computational improvements, and the present article provides a further improved version.

For a single chain of length $N$, the effective sample size of a chain can be defined in terms of the autocorrelations within the chain at different lags,

$$N_{\text{eff}} = \frac{N}{\sum_{t=-\infty}^{\infty} \rho_t} = \frac{N}{1 + 2 \sum_{t=1}^{\infty} \rho_t}, \tag{3.7}$$

where $\rho_t$ is autocorrelation at lag $t \geq 0$. An equivalent approach was used by Hastings (1970) for estimating the variance of the mean estimate from a single chain. For a chain with joint probability function $p(\theta)$ with mean $\mu$ and standard deviation $\sigma$, $\rho_t$ is defined to be

$$\rho_t = \frac{1}{\sigma^2} \int_{\Theta} (\theta^{(n)} - \mu)(\theta^{(n+t)} - \mu) p(\theta) d\theta. \tag{3.8}$$

This is just the correlation between the two chains offset by $t$ positions. Because we know $\theta^{(n)}$ and $\theta^{(n+t)}$ have the same marginal distribution at convergence, multiplying the two difference terms and reducing yields,

$$\rho_t = \frac{1}{\sigma^2} \int_{\Theta} \theta^{(n)} \theta^{(n+t)} p(\theta) d\theta. \tag{3.9}$$

In practice, the probability function in question cannot be tractably integrated and thus neither autocorrelation nor the effective sample size can be directly calculated. Instead, these quantities must be estimated from the sample itself. Computations of autocorrelations for all lags simultaneously can be done efficiently via the fast Fourier transform algorithm (FFT; see Geyer, 2011). In our experiments, FFT-based autocorrelation estimates have also been computationally more accurate than naive autocorrelation computation. As recommended by Geyer (1992) we use the biased estimate with divisor $N$, instead of unbiased estimate with divisor $N - t$. Also in our experiments, the biased estimate provided smaller variance in the final ESS estimate.

The autocorrelation estimates $\hat{\rho}_{t,m}$ at lag $t$ from multiple chains $m \in (1, \ldots, M)$ are combined with the within-chain variance estimate $W = \frac{1}{M} \sum_{m=1}^{M} s_m^2$ and the multi-chain variance estimate $\widehat{\text{var}}^{+} = W(N-1)/N + B/N$ to compute the combined autocorrelation at lag $t$ as,

$$\hat{\rho}_t = 1 - \frac{W - \frac{1}{M} \sum_{m=1}^{M} s_m^2 \hat{\rho}_{t,m}}{\widehat{\text{var}}^{+}} \tag{3.10}$$

If $\hat{\rho}_{t,m} = 0$ for all $m$, $\hat{\rho}_t = 1 - \hat{R}^{-2}$. If in addition chains are mixing well so that $\hat{R} \approx 1$, then $\hat{\rho}_t \approx 0$. If $\hat{\rho}_{t,m} \neq 0$ and $\hat{R} \approx 1$, then $\hat{\rho}_t \approx \frac{M}{M} \sum_{m=1}^{M} \hat{\rho}_{t,m}$. If $\hat{R} \gg 1$, then $\hat{\rho}_t \approx 1 - \hat{R}^{-2}$. If chains are mixing well, this expression is equivalent to averaging autocorrelations, and if chains are not mixing well, simulations in each chain are implicitly assumed to be more correlated with each other. In our experiments, multi-chain $\hat{\rho}_t$ given by (3.10) had smaller variance than the related multi-chain $\hat{\rho}_{t,m}$ proposed by Gelman et al. (2013).

As noise in the correlation estimates $\hat{\rho}_t$ increases as $t$ increases, the large-lag terms need to be down weighted (lag window approach, see, e.g. Geyer, 1992; Pignalosi and Jones, 2010) or the sum of $\hat{\rho}_t$ can be truncated with some truncation lag $T$ to get

$$S_{\text{eff}} = \frac{NM}{1 + 2 \sum_{t=1}^{T} \hat{\rho}_t} \tag{3.11}$$

We use a truncation rule proposed by Geyer (1992), which takes into account certain properties of the autocorrelations for Markov chains. Even when the simulations are constructed using an MCMC algorithm, the time series of simulations for a scalar parameter or summary will not in general have the Markov property; nonetheless we have found these Markov-derived heuristics to work well in practice. In our experiments, Geyer's truncation had superior stability compared to flat-top (e.g. Doss et al., 2014) and slug-tail (Vats and Knudson, 2018) lag window approaches.

For Markov chains typically used in MCMC, negative autocorrelations can happen only on odd lags and by summing over pairs starting from lag $t = 0$, the paired autocorrelation is guaranteed to be positive, monotone and convex modulo estimator noise (Geyer, 1992, 2011). The effective sample size of combined chains is then defined as

$$S_{\text{eff}} = \frac{NM}{\tau}, \tag{3.12}$$

where

$$\tau = 1 + 2 \sum_{t=1}^{2\lfloor k+1 \rfloor} \hat{\rho}_t = -1 + 2 \sum_{k'=0}^{k} \hat{\rho}_{t'}, \tag{3.13}$$

and $\hat{\rho}_{t'} = \hat{\rho}_{2t'} + \hat{\rho}_{2t'+1}$. The initial positive sequence estimator is obtained by choosing the largest $k$ such that $\hat{\rho}_{t'} > 0$ for all $t' = 1, \ldots, k$. The initial monotone sequence estimator is obtained by further reducing $\hat{\rho}_{t'}$ to the minimum of the preceding values so that the estimated sequence becomes monotone.

In case of antithetic Markov chains, which have negative autocorrelations on odd lags, the effective sample size $S_{\text{eff}}$ can also be larger than $S$. For example, the dynamic Hamiltonian Monte Carlo (HMC) algorithms used in Stan (Hoffman and Gelman, 2014; Betancourt, 2017; Stan Development Team, 2018b) is likely to produce $S_{\text{eff}} > S$ for parameters with a close to Gaussian posterior (in the unconstrained space) and low dependence on the other parameters. The benefit of this kind of super-efficiency is often limited as it is unlikely to simultaneously have super-efficiency for mean and variance (or tail quantiles) as demonstrated in our experiments.

In extreme antithetic cases, magnitude of single lag autocorrelations can stay large for a large lag, even if the paired autocorrelations are close to zero. To improve the stability and reduce the variance of the ESS estimate, we determine the truncation lag as usual, but compute the average of truncated sum ending to usual odd lag and truncated sum ending to the next even lag. Sometimes these estimates are used for very short antithetic chains, and just by chance there can be strange estimates, and as highly antithetic chains, and just by chance there can be strange estimates, and as highly antithetic chains in our software implementation we have restricted the ESS estimate to an upper bound of $S \log_{10}(S)$.

The effective sample size $S_{\text{eff}}$ described here is different from similar formulas in the literature in that we use multiple chains and between-chain variance in the computation, which typically gives more conservative chains (lower values of $S_{\text{eff}}$) compared to single chain estimates, especially when mixing of the chains is poor. If the chains are not mixing at all (e.g., if the posterior is multimodal and the chains are stuck in different modes), then our $S_{\text{eff}}$ is close to the number of distinct modes that are found. Thus, our ESS estimate can also diagnose multimodality.

The values of $\hat{R}$ and ESS require reliable estimates of variances and autocorrelations (in addition to the existence of these quantities; see our Cauchy examples in Section 5.1), which can only occur if the chains have enough independent replicates. In particular, we only recommend relying on the $\hat{R}$ estimate to make decisions about the quality of the chain if each of the split chains has an average ESS estimate of at least 50. In our minimum recommended setup of four parallel chains, the total ESS should be at least 400 before we expect $\hat{R}$ to be useful.

## 4 Improving convergence diagnostics

### 4.1 Rank normalization helps $\hat{R}$ when there are heavy tails

As split-$\hat{R}$ and $S_{\text{eff}}$ are well defined only if the marginal posteriors have finite mean and variance, we propose to use rank normalized parameter values instead of the actual parameter values for the purpose of diagnosing convergence.

The use of ranks to avoid the assumption of normality goes back to Friedman (1937). Chernoff and Savage (1958) show rank based approaches have good asymptotic efficiency. Instead of using rank values directly and modifying tests for them, Fisher and Yates (1938) propose to use expected normal scores (ordered statistics) and use the normal models. Blom (1958) shows that accurate approximation of the expected normal scores can be computed efficiently from ranks using an inverse normal transformation.

Rank normalized split-$\hat{R}$ and $S_{\text{eff}}$ are computed using the equations in Section 3.1 and 3.2, but replacing the original parameter values $\theta^{(mn)}$ with their corresponding rank normalized values denoted as $z^{(mn)}$. Rank normalization proceeds as follows. First, replace each value $\theta^{(mn)}$ by its rank $r^{(mn)}$ within the pooled draws from all chains. Average rank for ties are used to conserve the number of unique values of discrete quantities. Second, transform ranks to normal scores using the inverse normal transformation and a fractional offset (Blom, 1958):

$$z^{(mn)} = \Phi^{-1} \left( \frac{r^{(mn)} - 3/8}{S - 1/4} \right). \tag{4.1}$$

Using normalized ranks (normal scores) $z^{(mn)}$ instead of ranks $r^{(mn)}$ themselves has the benefits that (1) for continuous variables the normality assumptions in computation of $\hat{R}$ and $S_{\text{eff}}$ are fulfilled (via the transformation), (2) the values of $\hat{R}$ and $S_{\text{eff}}$ are practically the same as before for nearly normally distributed variables (the interpretation doesn't change for the cases where the original $\hat{R}$ worked well), and (3) rank-normalized $\hat{R}$ and $S_{\text{eff}}$ are invariant to monotone transformations (e.g. we get the same diagnostic values when examining a variable or logarithm of a variable). The effects of rank normalization are further explored in the online appendix.

We will use the term *bulk* effective sample size (bulk-ESS or bulk-$S_{\text{eff}}$) to refer to the effective sample size based on the rank normalized draws. Bulk-ESS is useful for diagnosing problems due to trends or different locations of the chains (see Appendix A). Further, it is well defined even for distributions with infinite mean or variance, a case where previous ESS estimates fail. However, due to the rank normalization, bulk-ESS is no longer directly applicable to estimate the Monte Carlo standard error of the posterior mean. We will come back to the issue of computing Monte Carlo standard errors for relevant quantities in Section 4.4.

### 4.2 Folding reveals problems with variance and tail exploration

Both original and rank normalized split-$\hat{R}$ can be folded if the chains have the same location but different scales. This can happen if one or more chains is stuck near the middle of the distribution. To alleviate this problem, we propose a rank normalized split-$\hat{R}$ statistic not only for the original draws $\theta^{(mn)}$, but also for the corresponding *folded* draws $\zeta^{(mn)}$, absolute deviations from the median,

$$\zeta^{(mn)} = |\theta^{(mn)} - \text{median}(\theta)|. \tag{4.2}$$

We call the rank normalized split-$\hat{R}$ measure computed on the $\zeta^{(mn)}$ values *folded-split-$\hat{R}$. This measures convergence in the tails rather than in the bulk of the distribution. To obtain a single conservative $\hat{R}$ estimate, we propose to report the maximum of rank normalized split-$\hat{R}$ and rank normalized folded-split-$\hat{R}$ for each parameter.

Figure 1 demonstrates how our new version of $\hat{R}$ catches some examples of lack of convergence that were not detected by earlier versions of the potential scale reduction factor. We do not intend with this example to claim that our new $\hat{R}$ is perfect—of course, it can be detected too. Rather, we use these simple scenarios to develop intuition about problems with traditional split-$\hat{R}$ and possible directions for improvement.

### 4.3 Localizing convergence diagnostics: Assessing the quality of quantiles, the median absolute deviation, and small-interval probabilities

The new $\hat{R}$ and bulk-ESS introduced above are useful as overall efficiency measures. Next we introduce convergence diagnostics for quantiles and related quantities, which are more focused measures and help to diagnose reliability of reported posterior intervals. Estimating the efficiency of quantile estimates has a high practical relevance in particular as we observe the efficiency for tail quantiles to often be lower than for the mean or median. This especially has implications if people are making decisions based on whether or not a specific quantile is below or above a fixed value (for example, if a posterior interval contains zero).

The $\alpha$-quantile is defined as the parameter value $\theta_\alpha$ for which $\Pr(\theta \leq \theta_\alpha) = \alpha$. An estimate $\hat{\theta}_\alpha$ of $\theta_\alpha$ can be obtained by finding the $\alpha$-quantile of the empirical cumulative distribution function (ECDF) of the posterior draws $\theta^{(s)}$.

The cumulative probabilities $\Pr(\theta \leq \theta_\alpha)$ can be written as expectation which can be estimated with sample mean

$$\Pr(\theta \leq \theta_\alpha) = E(I(\theta \leq \theta_\alpha)) \approx I_\alpha = \frac{1}{S} \sum_{s=1}^{S} I(\theta^{(s)} \leq \theta_\alpha), \tag{4.3}$$

where $I(\cdot)$ is the indicator function. The indicator function transforms simulation draws to 0's and 1's, and thus the subsequent computations are objectively invariant. Efficiency estimates of the ECDF at any $\theta_a$ can now be obtained by applying rank-normalizing and subsequent computations directly on the indicator function's results. More details on the variance of the cumulative distribution function can be found in the online appendix. Raftery and Lewis (1992) proposed to focus on accuracy of cumulative or interval probabilities and also proposed a specific effective sample size estimate for these probability estimates.

Although the quantiles cannot be written directly as an expectation, the quantile estimate is strongly consistent and Doss et al. (2014) provide conditions for a quantile central limit theorem. Assuming that the CDF is a continuous function $F$ which is smooth near an $\alpha$-quantile of interest, we could compute

$$\text{Var}(\theta_\alpha) = \text{Var}(F^{-1}(I_\alpha)) = \text{Var}(I_\alpha) / f(\theta_\alpha). \tag{4.4}$$

Even if we do not usually know $F$, this shows that the variance of $\theta_\alpha$ is just the variance of $I_\alpha$ scaled by the unknown density $f(\theta_\alpha)$, and thus the effective sample size for the quantile estimate $\theta_\alpha$ is the same as for the corresponding cumulative probability.

To get a better sense of the sampling efficiency in the distributions' tails, we propose to compute the minimum of the effective sample sizes of the 5% and 95% quantiles, which we will call *tail effective sample size* (tail-ESS or tail-$S_{\text{eff}}$). Tail-ESS can help diagnosing problems due to different scales of the chains (see Appendix A).

Since the marginal posterior distributions might not have finite mean and variance, for example, the popular rstanarm package (Stan Development Team, 2018a) reports median and median absolute deviation (MAD) instead of mean and standard error. Median and MAD are well defined even when the marginal distribution does not have finite mean and variance. Since the median is same as the 50% quantile, we can get an efficiency estimate for it as for any other quantile.

Further, we can also compute an efficiency estimate for the median absolute deviation by computing the efficiency estimate of an indicator function based on the folded parameter values $\zeta$ (see (4.2)):

$$\Pr(\zeta \leq \zeta_{0.5}) \approx I_{\zeta, 0.5} = \frac{1}{S} \sum_{s=1}^{S} I(\zeta^{(s)} \leq \zeta_{0.5}), \tag{4.5}$$

where $\zeta_{0.5}$ is the median of the folded values. The efficiency estimate for the MAD is obtained by applying the same approach as for the median (and other quantiles) but with the folded parameters values.

We can get more local efficiency estimates by considering small probability intervals. We propose to compute the efficiency estimates for

$$I_{a,\delta} = \Pr(\hat{Q}_\alpha < \theta \leq \hat{Q}_{\alpha + \delta}), \tag{4.6}$$

where $\hat{Q}_\alpha$ is an empirical $\alpha$-quantile, $\delta = 1/k$ is the length of the interval for some positive integer $k$, and $\alpha \in (0, \delta, \ldots, 1 - \delta)$ changes in steps of $\delta$. Each interval has $S/k$ draws, and the efficiency measures the autocorrelation of an indicator function which indicates if the values are inside the specific interval and 0 otherwise. This gives a local efficiency measure which is more localized than efficiency measure for quantiles and can be used to build intuition about what types of posterior functionals can be computed as illustrated in the examples. While the expectation of a function that only depends on intermediates values can be usually estimated with relative ease, expectations of tail probabilities or other posterior functionals that depend critically on the tail of the distribution will be usually more difficult to estimate. In addition, small probability intervals can be used in practical equivalence testing (see, e.g., Wellek, 2010).

A natural multivariate extension of small intervals would be to consider small probability volumes using a box or sphere with dimensions determined, for example, by marginal quantiles. The visualization of the multivariate results would be easiest in 2 or 3 dimensions. In higher dimensions, for example, $k$-means clustering could be used to determine hyper-spheres. Even if it gets more difficult to visualize where the problematic region in the high dimensional space is, the diagnosing that sampling efficiency is low in some parts of the posterior can be useful.

### 4.4 Monte Carlo error estimates for quantiles

To obtain the MCSE for $\hat{\theta}_\alpha$, Doss et al. (2014) use a Gaussian kernel density estimate of $f(\theta_\alpha)$ and batch means and subsampling bootstrap method for estimating Var($I_\alpha$), and Liu et al. (2016) use a flat top kernel density estimate for $f(\theta_\alpha)$ and a spectral variance approach for Var($I_\alpha$).

We propose an alternative approach which avoids the need to estimate $f(\theta_\alpha)$. Here is how we estimate, for example, a central 90% Monte Carlo error interval for $\theta_\alpha$ (any quantiles or intervals can be computed using the same algorithm):

1. Compute the effective sample size $S_{\text{eff}}$ for estimating the expectation $E(I(\theta \leq \hat{\theta}_\alpha))$.

2. Compute $a$ and $b$ as 5% and 95% quantiles (for other than 90% interval use corresponding quantiles) of

$$\text{Beta}(S_{\text{eff}}\alpha + 1, S_{\text{eff}}(1 - \alpha) + 1). \tag{4.7}$$

Using $S_{\text{eff}}$ here takes into account the efficiency of the posterior draws. The variance of this beta distribution matches the variance of normal approximation, but using quantiles guarantees that $0 < a < 1$ and $0 < b < 1$. Asymptotically as $S_{\text{eff}} \to \infty$, this beta distribution converges towards a normal distribution. Instead of drawing random sample from the beta distribution, we get sufficient accuracy for MCSE using just two deterministically chosen quantiles.

3. Propagate $a$ and $b$ through the nonlinear inverse transforms $A = (F^{-1}(a))$ and $B = (F^{-1}(b))$. Then $A$ and $B$ are corresponding quantiles in the transformed scale. As we don't know $F$ for the quantity of interest, we use a simple numerical approximation:

$$\tilde{A} = \theta^{(s')} \quad \text{where } s' \leq Sa < s' + 1,$$
$$\tilde{B} = \theta^{(s'')} \quad \text{where } s'' - 1 < Sb \leq s'',$$

where $\theta^{(s)}$ have been sorted in ascending order. $\tilde{A}$ and $\tilde{B}$ are then estimated 5% and 95% quantiles (or other quantiles corresponding to which quantiles $a$ and $b$ were chosen to be) of the Monte Carlo error interval for $\hat{\theta}_\alpha$.

The Monte Carlo standard error for $\hat{\theta}_\alpha$ can be approximated, for example, by computing $(\tilde{B} - \tilde{A})/2$, where $\tilde{A}$ and $\tilde{B}$ are estimated 16% and 84% Monte Carlo error quantiles computed with the above algorithm. Use of deterministically chosen 16% and 84% quantiles and propagating them through the nonlinear transformation and estimating the standard error from the transformed quantiles, corresponds to uncentered transformation which is known to estimate the variance of the transformed quantity correct to the second order (Julier and Uhlmann, 1997).

The above algorithm is useful as a default, as it is more robust than density estimation based approaches for non-smooth densities, which is common case, for example, when variables are constrained in a (semi-open) range. $A$ and $B$ are likely to have high variance in case of extreme tail quantiles and thick-tailed distributions, as there are not many $\theta^{(s)}$ in extreme tails. The approaches using a density estimate for $f(\theta_\alpha)$ can provide better accuracy when the assumptions of the density estimate are fulfilled, but they can have a high bias if the density is not smooth or the shape of the kernel doesn't match well the tail properties of the distribution. To improve accuracy of extreme tail quantile estimates, common extreme value models could be used to model the tail of the distribution.

### 4.5 Diagnostic visualizations

In order to develop intuitions around the convergence of iterative algorithms, we propose several new diagnostic visualizations in addition to the numerical convergence diagnostics discussed above. We illustrate with several examples in Section 5.

**Rank plots** Extending the idea of using ranks instead of the original parameter values, we propose using rank plots for each chain instead of trace plots. Rank plots, such as Figure 6, are histograms of the ranked posterior draws (ranked over all chains) plotted separately for each chain. If all of the chains are targeting the same posterior, we expect the ranks in each chain to be uniform, whereas if one chain has a different location or scale parameter, this will be reflected in the deviation from uniformity. If rank plots of all chains look similar, this indicates good mixing of the chains. As compared to trace plots, rank plots don't tend to squeeze to a fuzzy mess when used with long chains.

**Quantile and small-interval plots** The efficiency of quantiles or small-interval probabilities may vary drastically across different quantiles and small-interval positions, respectively. We thus propose to use diagnostic plots that display efficiency of quantiles or small-interval probabilities across their whole range to better diagnose areas of the distributions that the iterative algorithm fails to explore efficiently.

**Efficiency per iteration plots** For a well-explored distribution, we expect the ESS measures to grow linearly with the total number of draws $S$, or, equivalently, that the relative efficiency (ESS divided $S$) is approximately constant for different values of $S$. For small number of draws, both bulk and tail-ESS may be unreliable and cannot necessarily reveal convergence problems. As a result, some issues may only be detectable as $S$ increases. Equivalently, in such a case, we would expect to see a relatively sharp drop in the relative efficiency measures. We therefore propose to plot the change of both bulk and tail ESS with increasing $S$. This can be done based on a single model without a need to refit, as we can just extract initial sequences of certain length from the original chains. However, some convergence problems only occur at relatively high $S$ and may thus not be detectable if the total number of draws is too small.

## 5 Examples

We now demonstrate our approach and recommended workflow on several small examples. Unless mentioned otherwise, we use dynamic Hamiltonian Monte Carlo (HMC) with multimodal sampling (Betancourt, 2017) as implemented in Stan (Stan Development Team, 2018b). We run 4 chains, each with 1000 warmup iterations, which do not form a Markov chain and are discarded, and 1000 post-warmup iterations, which are saved and used for inference.

### 5.1 Cauchy: A distribution with infinite mean and variance

Traditional $\hat{R}$ is based on calculating within and between chain variances. If the marginal distribution of a quantity of interest is such that the variance is infinite, this approach is not well justified, as we demonstrate here with a Cauchy-distributed example.

#### Nominal parameterization of the Cauchy distribution

We start by simulating from independent standard Cauchy distributions for each element of a 50-dimensional vector $x$:

$$x_j \sim \text{Cauchy}(0, 1) \quad \text{for } j = 1, \ldots, 50. \tag{5.1}$$

We monitor the convergence for each of the $x_j$ separately. As the distribution of $x$ has thick tails, we may expect any generic MCMC algorithm to have mixing problems. Several values of $\hat{R}$ greater than 1.01 and some effective sample sizes less than 400 also indicate convergence problems (in addition a HMC-specific diagnostic, "iterations exceed maximum tree depth" (Stan Development Team, 2018b) also indicated slow mixing of the chains). The online appendix contains more results with longer chains and other $\hat{R}$ diagnostics. We can further analyze potential problems using local efficiency and rank plots. We specifically investigate $x_{30}$, which, in this specific run, had the smallest tail-ESS. Figure 3 shows the local efficiency of small interval probability estimates (see Section 4.3). The efficiency of sampling is low in the tails, which is clearly caused by slow mixing in long tails of the Cauchy distribution. Figure 4 shows the efficiency of quantile estimates (see Section 4.3), which also is low in the tails.

We may also investigate how the estimated effective sample sizes change when we use more and more draws; Brooks and Gelman (1998) proposed to use similar graph for $\hat{R}$. If the effective sample size is highly unstable, does not increase proportionally with more draws, or even decreases, this indicates that simply running longer chains will likely not solve the convergence issues. In Figure 5, we see how unstable both bulk-ESS and tail-ESS are for this example. Rank plots in Figure 6 clearly show the mixing problem between chains. In case of good mixing all rank plots should be close to uniform. More experiments can be found in Appendix B and in the online appendix.

#### Alternative parameterization of the Cauchy distribution

Next, we examine an alternative parameterization of the Cauchy as a scale mixture of Gaussians:

$$a_j \sim \text{Normal}(0, 1), \quad b_j \sim \text{Gamma}(0.5, 0.5), \quad x_j = a_j / \sqrt{b_j}. \tag{5.2}$$

The model has two parameters which have thin-tailed distributions so that we may assume good mixing of Markov chains. Cauchy-distributed $x$ can be computed deterministically from $a$ and $b$. In addition to improved sampling performance, the example illustrates findings on diagnostics matters. We define two 50-dimensional parameter vectors $a$ and $b$ from which the 50-dimensional quantity $x$ is computed.

For all parameters, $\hat{R}$ is less than 1.01 and ESS exceeds 400, indicating that sampling worked much better with this alternative parameterization. The online appendix contains more results using other parameterizations of the Cauchy distribution. The vectors $a$ and $b$ used to form the Cauchy-distributed $x$ have stable quantile, mean and variance values. The quantiles of each $x_j$ are stable too, but the mean and variance estimates are widely varying. We can further analyze potential problems using local efficiency estimates and rank plots. For this example, we take a detailed look at $x_{30}$, which had the smallest bulk-ESS of 2848. Figures 7 and 8 show good sampling efficiency for the small-interval probability and quantile estimates. The rank plots in Figure 9 also look close to uniform across chains, which is consistent with good mixing. The appearances of the plots in Figures 7, 8, and 9 are what we would expect for well mixing chains in general.

### 5.2 Hierarchical model: Eight schools

The eight schools problem is a classic example (see Section 5.5 in Gelman et al., 2013), which even in its simplicity illustrates typical problems in inference for hierarchical models. We can parameterize this simple model in at least two ways. The centered parameterization ($\theta, \mu, \tau, \sigma$) is,

$$\theta_j \sim \text{Normal}(\mu, \tau),$$
$$y_j \sim \text{Normal}(\theta_j, \sigma_j).$$

In contrast, the non-centered parameterization $(\tilde{\theta}, \mu, \tau, \sigma)$ can be written as,

$$\tilde{\theta}_j \sim \text{Normal}(0, 1),$$
$$\theta_j = \mu + \tilde{\theta}_j,$$
$$y_j \sim \text{Normal}(\theta_j, \sigma_j).$$

In both cases, $\theta_j$ are the treatment effects in the eight schools, and $\mu, \tau$ represent the population mean and standard deviation of the distribution of these effects. In the centered parameterization, the $\theta$ are parameters, whereas in the non-centered parameterization, the $\tilde{\theta}$ are parameters and $\theta$ is a derived quantity.

Geometrically, the centered parameterization exhibits a funnel shape that contracts into a region of strong curvature around the population mean when faced with small values of the population standard deviation $\tau$, making it difficult for many simple Markov chain methods to adequately explore the full distribution. In the following, we will focus on analyzing convergence of $\tau$. The online appendix contains more detailed analysis of different algorithm variants and results of longer chains.

#### A centered eight schools model

Instead of the default options, we run the centered parameterization model with more conservative settings of the HMC sample to reduce the probability of getting divergent transitions, which bias the obtained estimates if they occur; for details see Stan Development Team (2018b). Still, we observe a lot of divergent transitions, which in itself is already a sufficient indicator of convergence problems. We can also use $\hat{R}$ and ESS diagnostics to recognize problematic parts of the posterior. The latter two have the advantage over the divergent transitions diagnostic that they can be used with all MCMC algorithms not only with HMC.

Bulk-ESS and tail-ESS for the between-school standard deviation $\tau$ are 67 and 82, respectively. Both are much less than 400, indicating we should investigate that parameter more carefully. Figures 11 and 12 show the sampling efficiency for the small-interval probability and quantile estimates. The sampler has difficulties in exploring small $\tau$ values. As the sampling efficiency for small $\tau$ values is practically zero, we may assume that we miss a substantial amount of posterior mass and get biased estimates. In this case, the severe sampling problems for small $\tau$ values is reflected in the sampling efficiency for all quantiles. Red tick marks show the position of iterations with divergences, have centered to small $\tau$ values, which gives us another indication of problems in exploring small values.

Figure 13 shows how the estimated effective sample sizes change when we use more and more draws. Here we do not see sudden changes, but both bulk-ESS and tail-ESS are consistently low. In line with the other findings, rank plots of $\tau$ displayed in Figure 14 clearly show problems in the mixing of the chains. In particular, the rank plot for the first chain indicates that it was unable to explore the lower-end of the posterior range, while the spike in the rank plot for chain 2 indicates that it spent too much time stuck in these values. More experiments can be found in Appendices C and D as well as in the online appendix.

#### Non-centered eight schools model

For hierarchical models, the corresponding non-centered parameterization often works better (Betancourt and Girolami, 2019). For reasons of comparability, we use the same conservative sampler settings as for the centered parameterization model. For the non-centered parameterization, we do not observe divergences or other warnings. All values of $\hat{R}$ are less than 1.01 and ESS exceeds 400, indicating a much better efficiency of the non-centered parameterization. Figures 15 and 16 show the efficiency of small-interval probability estimates and the efficiency of quantile estimates for $\tau$. Small $\tau$ values are still more difficult to explore, but the relative efficiency is good. The rank plots of $\tau$ Figure 17 show no substantial differences between chains.

## Supplementary Material

Rank-Normalization, Folding, and Localization: An Improved $\hat{R}$ for Assessing Convergence of MCMC. Supplementary Material. (DOI: [10.1214/20-BA1221SUPP](https://doi.org/10.1214/20-BA1221SUPP); .pdf).

## References

Betancourt, M. (2017). "A conceptual introduction to Hamiltonian Monte Carlo." arXiv:1701.02434. MR1699395. doi: https://doi.org/10.1017/CBO9780511470813.003. 11, 17

Betancourt, M. and Girolami, M. (2019). "Hamiltonian Monte Carlo for hierarchical models." In *Current Trends in Bayesian Methodology with Applications*, 79–101. Chapman and Hall/CRC. MR3644666. 6, 24

Blom, G. (1958). *Statistical Estimates and Transformed Beta-Variables*. Wiley; New York. MR0005553. 12

Brooks, S. P. and Gelman, A. (1998). "General Methods for Monitoring Convergence of Iterative Simulations." *Journal of Computational and Graphical Statistics*, 7(4): 434–455. MR1065662. doi: https://doi.org/10.2307/1390675. 2, 5, 17

Carpenter, B., Gelman, A., Hoffman, M., Lee, D., Goodrich, B., Betancourt, M.,

Brubakerr, M., Guo, J., Li, P., and Riddell, A. (2017). "Stan: A Probabilistic Programming Language." *Journal of Statistical Software*, *Articles*, 76(1): 1–32. 2

Chernoff, H. and Savage, I. R. (1958). "Asymptotic normality and efficiency of certain nonparametric test statistics." *Annals of Mathematical Statistics*, 29(4): 972–994. MR0100322. doi: https://doi.org/10.1214/aoms/1177706436. 12

Cowles, M. K. and Carlin, B. P. (1996). "Markov chain Monte Carlo convergence diagnostics: A comparative review." *Journal of the American Statistical Association*, 91(434): 883–904. MR1365755. doi: https://doi.org/10.2307/2291683. 2, 8

de Valpine, P., Turek, D., Paciorek, C. J., Anderson-Bergman, C., Lang, D. T., and Bodik, R. (2017). "Programming with models: Writing statistical algorithms for general model structures with NIMBLE." *Journal of Computational and Graphical Statistics*, 26(2): 403–413. MR3640196. doi: https://doi.org/10.1080/10618600.2016.1172487. 2

Doss, C. R., Flegal, J. M., Jones, G. L., and Neath, R. C. (2014). "Markov chain Monte Carlo estimation of quantiles." *Electronic Journal of Statistics*, 8(2): 2448–2478. MR3285872. doi: https://doi.org/10.1214/14-EJS957. 10, 14, 15

Fisher, R. A. and Yates, F. (1938). *Statistical Tables for Biological, Agricultural, and Medical Research*. Oliver & Boyd; Edinburgh. MR0630288. 12

Flegal, J. M. and Jones, G. L. (2010). "Batch means and spectral variance estimators in Markov chain Monte Carlo." *Annals of Statistics*, 38(2): 1034–1070. MR2604704. doi: https://doi.org/10.1214/09-AOS735. 10

Friedman, M. (1937). "The use of ranks to avoid the assumption of normality implicit in the analysis of variance." *Journal of the American Statistical Association*, 32(200): 675–701. 12

Gelman, A., Carlin, J. B., Stern, H. S., Dunson, D. B., Vehtari, A., and Rubin, D. B. (2013). *Bayesian Data Analysis, third edition*. CRC Press. MR3235677. 2, 3, 4, 6, 7, 9, 10, 21

Gelman, A., Carlin, J. B., Stern, H. S., and Rubin, D. R. (2003). *Bayesian Data Analysis, second edition*. Chapman & Hall. MR2027492. 9

Gelman, A. and Rubin, D. B. (1992). "Inference from iterative simulation using multiple sequences (with discussion)." *Statistical Science*, 7(4): 457–511. 1, 2, 5, 8

Geyer, C. J. (1992). "Practical Markov Chain Monte Carlo." *Statistical Science*, 7: 473–483. 6, 8, 10, 11

Geyer, C. J. (2011). "Introduction to Markov Chain Monte Carlo." In Brooks, S., Gelman, A., Jones, G. L., and Meng, X. L. (eds.), *Handbook of Markov Chain Monte Carlo*. CRC Press. MR3185067. 10, 11

Hastings, W. K. (1970). "Monte Carlo sampling methods using Markov chains and their applications." *Biometrika*, 57(1): 97–109. MR3363437. doi: https://doi.org/10.1093/biomet/57.1.97. 6, 8, 9

Hoffman, M. D. and Gelman, A. (2014). "The No-U-Turn Sampler: Adaptively Setting Path Lengths in Hamiltonian Monte Carlo." *Journal of Machine Learning Research*, 15: 1593–1623. URL http://jmlr.org/papers/v15/hoffman14a.html. MR3214779. 11

Jacob, P. E., O'Leary, J., and Atchadé, Y. F. (2017). "Unbiased Markov chain Monte Carlo with couplings." arXiv preprint arXiv:1708.03625. MR3949304. doi: https://doi.org/10.1093/biomet/asy074. 6

Julier, S. J. and Uhlmann, J. K. (1997). "New extension of the Kalman filter to nonlinear systems." In *Proc. SPIE 3068, Signal processing, sensor fusion, and target recognition*, 182–193. SPIE. 16

Kong, A., Liu, J. S., and Wong, W. H. (1994). "Sequential Imputations and Bayesian Missing Data Problems." *Journal of the American Statistical Association*, 89(425): 278–288. MR3738474. 9

Laumann, J. A. and Gates, W. L. (1977). "Statistical considerations in the evaluation of climatic experiments with atmospheric general circulation models." *Journal of the Atmospheric Sciences*, 34(8): 1187–1199. MR0496446. doi: https://doi.org/10.1175/1520-0469(1977)034<1187:SCITEO>2.0.CO;2. 9

Liu, J., Nordman, D. J., and Meeker, W. Q. (2016). "The number of MCMC draws needed to compute Bayesian credible bounds." *The American Statistician*, 70(3): 275–284. MR3535514. doi: https://doi.org/10.1080/00031305.2016.1135788. 15

Lunn, D., Spiegelhalter, D., Thomas, A., and Best, N. (2009). "The BUGS project: Evolution, critique and future directions." *Statistics in Medicine*, 28(25): 3049–3067. MR2779401. doi: https://doi.org/10.1002/sim.3680. 2

Lunn, D. J., Thomas, A., Best, N., and Spiegelhaltter, D. (2000). "WinBUGS— a Bayesian modelling framework: Concepts, structure, and extensibility." *Statistics and Computing*, 10(4): 325–337. 2

Mengersen, K. L., Robert, C. P., and Guihennete-Jouyaux, C. (1999). "MCMC convergence diagnostics: A review." In Bernardo, J. M., Berger, J. O., and Dawid, A. P. (eds.), *Bayesian Statistics 6*, 415–440. Oxford University Press. MR1723507. 2, 8

Plummer, M. (2003). "JAGS: A program for analysis of Bayesian graphical models using Gibbs sampling." In *Proceedings of the 3rd International Workshop on Distributed Statistical Computing*, volume 124. 2

Plummer, M., Best, N., Cowles, K., and Vines, K. (2006). "CODA: Convergence Diagnosis and Output Analysis for MCMC." *R News*, 6(1): 7–11. URL https://journal.r-project.org/archive/. 9

Raftery, A. E. and Lewis, S. M. (1992). "How many Iterations in the Gibbs Sampler?" In Bernardo, J. M., Berger, J. O., Dawid, A. P., and Smith, A. F. M. (eds.), *Bayesian Statistics 4*, 763–773. Oxford University Press. 13

Robert, C. P. and Casella, G. (2004). *Monte Carlo Statistical Methods*. Springer, second edition. MR2080278. doi: https://doi.org/10.1007/978-1-4757-4145-2. 2, 8

Salvatier, J., Wiecki, T. V., and Fonnesbeck, C. (2016). "Probabilistic programming in Python using PyMC3." *PeerJ Computer Science*, 2: e55. 2

Sorensen, D. A., Andersen, S., Gianola, D., and Korsgaard, I. (1995). "Bayesian inference in threshold models using Gibbs sampling." *Genetics Selection Evolution*, 27(3): 229. 8, 9

Stan Development Team (2018a). "RStanArm: Bayesian applied regression modeling via Stan. R package Version 2.17.4." URL http://mc-stan.org. 14

Stan Development Team (2018b). "Stan Modeling Language Users Guide and Reference Manual. Version 2.18.0." URL http://mc-stan.org. 7, 9, 11, 17, 22

Vats, D. and Knudson, C. (2018). "Revisiting the Gelman-Rubin Diagnostic." arXiv:1812.09384. 5, 6, 7, 8, 10

Vehtari, A., Gelman, A., Simpson, D., Carpenter, B., and Bürkner, P.-C. (2020). "Rank-Normalization, Folding, and Localization: An Improved $\hat{R}$ for Assessing Convergence of MCMC. Supplementary Material." *Bayesian Analysis*. doi: https://doi.org/10.1214/20-BA1221SUPP. 3

Wellek, S. (2010). *Testing Statistical Hypotheses of Equivalence and Noninferiority*. Chapman and Hall/CRC. MR2676002. doi: https://doi.org/10.1201/EBK1439808184. 14
