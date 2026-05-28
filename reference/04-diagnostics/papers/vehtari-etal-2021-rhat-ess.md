# Rank-normalization, folding, and localization: An improved $\hat{R}$ for assessing convergence of MCMC

Aki Vehtari^1, Andrew Gelman^2, Daniel Simpson^3, Bob Carpenter^4, and Paul-Christian Bürkner^5

^1 Department of Computer Science, Aalto University, Finland.
^2 Department of Statistics, Columbia University, New York.
^3 Department of Statistical Sciences, University of Toronto, Canada.
^4 Center for Computational Mathematics, Flatiron Institute, New York.
^5 (Affiliation details)

## Abstract

Markov chain Monte Carlo is a key computational tool in Bayesian statistics, but it can be challenging to monitor the convergence of an iterative stochastic algorithm. In this paper we show that the convergence diagnostic $\hat{R}$ of Gelman and Rubin (1992) has serious flaws. Traditional $\hat{R}$ will fail to correctly diagnose convergence failures when the chain has a heavy tail or extreme values across the chains. In this paper we propose an alternative rank-based diagnostic that fixes these problems. We also introduce a collection of quantile-based local efficiency measures, along with a practical approach for computing Monte Carlo error estimates for quantiles. We suggest that common trace plots should be replaced with rank plots from multiple chains. Finally, we give recommendations for how these methods should be used in practice.

## 1 Introduction

Markov chain Monte Carlo (MCMC) methods are important in computational statistics, especially in Bayesian applications where the goal is to represent posterior inference using a sample of posterior draws. While MCMC, as well as more general iterative simulation algorithms, can usually be proven to converge to the target distribution as the number of draws approaches infinity, there are rarely strong guarantees about their behavior after finite time. Indeed, decades of experience tell us that the finite sample behavior of these algorithms can be almost arbitrarily bad.

### 1.1 Monitoring convergence using multiple chains

In an attempt to assuage concerns of poor convergence, we typically run multiple independent chains to see if the obtained distribution is similar across chains. We can also visually inspect the sample paths of the chains via trace plots as well as study summary statistics such as the empirical autocorrelation function.

Running multiple chains is critical to any MCMC convergence diagnostic. Figure 1 illustrates two ways in which sequences of iterative simulations can fail to converge. In the first example, two chains are in different parts of the target distribution; in the second example, the chains move but have not attained stationarity. Slow mixing can arise with multimodal target distributions or when a chain is stuck in a region of high curvature with a step size too large to make an acceptable proposal for the next step. The two examples in Figure 1 make it clear that any method for assessing mixing and effective sample size should use information between and within chains.

As we are often fitting models with large numbers of parameters, it is not realistic to expect to make and interpret trace plots such as in Figure 1 for all quantities of interest. Hence we need numerical summaries that can flag potential problems.

*To appear in Bayesian Analysis. We thank Ben Bales, Ian Langmore, the editor, and anonymous reviewers for useful comments. We also thank Academy of Finland, the U.S. Office of Naval Research, National Science Foundation, Institute for Education Sciences, the Natural Science and Engineering Research Council of Canada, Finnish Center for Artificial Intelligence, and Technology Industries of Finland Centennial Foundation for partial support of this research. All computer code and an even larger variety of numerical experiments are available in the online appendix at https://aehluri.github.io/rhat_ess/rhat_ess.html.*

Of the various convergence diagnostics (see reviews by Cowles and Carlin, 1996; Mengersen et al., 1999; Robert and Casella, 2004), probably the most widely used is the potential scale reduction factor $\hat{R}$ (Gelman and Rubin, 1992; Brooks and Gelman, 1998). It is recommended as the primary convergence diagnostic in widely applied software packages for MCMC sampling such as Stan (Carpenter et al., 2017), JAGS (Plummer, 2003), WinBUGS (Lunn et al., 2000), OpenBUGS (Lunn et al., 2009), PyMC3 (Salvatier et al., 2016), and NIMBLE (de Valpine et al., 2017), which together are estimated to have hundreds of thousands of users. $\hat{R}$ is computed for each scalar quantity of interest, as the scaled deviation of that quantity from all the chains included together, divided by the root mean square of the separate within-chain standard deviations. The idea is that if a set of simulations have not mixed well, the variance of all the chains mixed together should be higher than the variance of individual chains. More recently, Gelman et al. (2013) introduced split-$\hat{R}$ which compares the first half of each chain to the second half, to try to detect lack of convergence within each chain. In this paper we use refer to $\hat{R}$ we are always assuming the split-$\hat{R}$ variant.

Convergence diagnostics are most effective when computed using multiple chains initialized at a diverse set of starting points. This reduces the chance that we falsely diagnose mixing when beginning at a different point would lead to a qualitatively different posterior.

In the context of Markov chain Monte Carlo, one can interpret $\hat{R}$ with diverse seeding as an operationalization of the qualitative statement that, after warmup, convergence of the Markov chain should be relatively insensitive to the starting point, at least within a reasonable part of the parameter space. This is the closest we can come to verifying empirically that the Markov chain is geometrically ergodic, which is a critical property if we want a central limit theorem to hold for approximate posterior expectations. Without this, we have no control over the large deviation behavior of the estimates and the constructed Markov chains may be useless for practical purposes.

### 1.2 Example where traditional $\hat{R}$ fails

Unfortunately, $\hat{R}$ can fail to diagnose poor mixing, which can be a problem when it is used as a default rule. The following example shows how failure can occur.

The red histograms in Figure 2 show the distribution of $\hat{R}$ (that is, split-$\hat{R}$ from Gelman et al. (2013)) in four different scenarios. (Ignore the light blue histograms for now; they show the results using an improved diagnostic that we shall discuss later in this paper.) In all four scenarios, traditional $\hat{R}$ is well under 1.1 under all simulations, thus not detecting any convergence problems—but in fact the two scenarios on the left have been constructed so that they are far from

mixed. These are problems that are not detected by traditional $\hat{R}$.

In each of the four scenarios in Figure 2, we run four chains for 1000 iterations each and then replicate the entire simulation 1000 times. The top row of the figure shows results for independent AR(1) processes with autoregressive parameter $\rho = 0.3$. The top left graph shows the distribution of $\hat{R}$ when one of the four chains is manually transformed to have only $1/3$ of the variance compared to the other three chains (see Appendix A for more details). This corresponds to a scenario where one chain fails to correctly explore the tails of the target distribution and one would hope could be identified as non-convergent. The split-$\hat{R}$ statistic defined in Gelman et al. (2013) does not detect the poor mixing, while the new variant of split-$\hat{R}$ defined later in this paper does. The top-right figure shows the same scenario but with all the chains having the same variance, and now both $\hat{R}$ values correctly identify that mixing occurs.

The second row of Figure 2 shows the behavior of $\hat{R}$ when the target distribution has infinite variance. In this case the chains were constructed as a ratio of stationary AR(1) processes with $\rho = 0.3$, and the distribution of the ratio is Cauchy. All of the simulated chains have unit scale, but in the lower-left figure, we have manually shifted one of the four chains two units to the right. This corresponds to a scenario where one chain provides a biased estimate of the target distribution. The Gelman et al. (2013) version of $\hat{R}$ would catch this behavior if the chain had finite variance, but in this case the infinite variance destroys its effectiveness—traditional $\hat{R}$ and split-$\hat{R}$ are defined based on second-moment statistics—and it inappropriately returns a value close to 1.

This example identified two problems with traditional $\hat{R}$:

1. If the chains have different variances but the same mean parameters, traditional $\hat{R} \approx 1$.
2. If the chains have infinite variance, traditional $\hat{R} \approx 1$ even if one of the chains has a different location parameter to the others. This can also lead to numerical instability for thick-tailed distributions even when the variance

is technically finite. It's typically hard to assess empirically if a chain has large but finite variance or infinite variance.

A related problem is that $\hat{R}$ is typically computed only for the posterior mean. While this provides an estimate for the convergence in the bulk of the distribution, it says little about the convergence in the tails, which is a concern for posterior interval estimates as well as for inferences about rare events.

## 2 Recommendations for practice

The traditional $\hat{R}$ statistic is general, easy to compute, and can catch many problems of poor convergence, but the discussion above reveals some scenarios where it fails. The present paper proposes improvements that overcome these problems. In addition, as the convergence of the Markov chain needs not be uniform across the parameter space, we propose a localized version of effective sample size that allows us to assess whether the behavior of localized functionals and quantiles of the chain. Finally, we propose three new methods to visualize the convergence of an iterative algorithm that are more informative than standard trace plots.

In this section we lay out practical recommendations for using the tools developed in this paper. In the interest of specificity, we have provided numerical targets for both $\hat{R}$ and effective sample size (ESS), which are useful as first level checks when analyzing reliability of inference for many quantities. However, these values should be adapted as necessary for the particular application, and ultimately domain expertise should be used to check that Monte Carlo standard errors (MCSE) for all quantities of interest are small enough.

In Section 4, we propose modifications to $\hat{R}$ based on rank-normalizing and folding the posterior draws, only using the sample if $\hat{R} < 1.01$. The threshold is much tighter than the one recommended by Gelman and Rubin (1992), reflecting lessons learnt over more than 25 years of use, as well as the simulation results in Appendix A. Gelman and Rubin (1992) derived $\hat{R}$ under the assumption that, as simulations went forward, the within-chain variance would gradually increase while the between-chain variance decreased, stabilizing when their ratio was 1. The potential scale reduction factor represents the factor by which the between-chain variation might decline under future simulations, and a potential scale reduction factor of 1.1 implied that there was little to be gained in inferential precision by running the chains longer. However, as discussed in Brooks and Gelman (1998), the dynamics of MCMC are such that the between-chain variance can decrease before it increases, if the initial part of the simulation pulls all the chains to the center of the distribution, only to rebound after further simulation. As a result, $\hat{R}$ can fall below 1.1 before convergence in some examples (a point also raised by Vats and Knudson (2018)), and we have found this to be much more rare when using the 1.01 threshold.

In addition, we recommend running at least four chains by default. Multiple chains are more likely to reveal multimodality and poor adaptation or mixing, we see examples for complex, misspecified or non-identifiable models in the Stan discussion forum all the time. Furthermore, most computers are able to run chains in parallel, giving multiple chains with no increase in computation time. Here we do not consider massive parallelization such as running 1000 chains or more; further research is needed in considering how to use such simulations most efficiently in such computational environments (see, for instance, the method discussed in Jacob et al. (2017)).

Roughly speaking, the effective sample size of a quantity of interest captures how many independent draws contain the same amount of information as the dependent sample obtained by the MCMC algorithm. The higher the ESS the better. When there might be difficulties with mixing, it is important to use between-chain as well as within-chain information in computing the ESS. A common example arises in hierarchical models with long-tailed or multi-shaped posteriors, where MCMC algorithms can struggle to simultaneously adapt to a "narrow" region of high density and low volume, and a "wide" region of low density and high volume. In such a case, differences in step-size adaptation can lead to chains that have different behavior in the neighborhood of the narrow part of the funnel (Betancourt and Girolami, 2019). For multimodal distributions with well-separated modes, the split-$\hat{R}$ adjustment leads to an ESS estimate that is close to the number of distinct modes that are found. Thus, our ESS estimate can be also be diagnostic of multimodality.

A small value of $\hat{R}$ is not enough to ensure that an MCMC sample is useful in practice (Vats and Knudson, 2018).

The effective sample size must also be large enough to get stable inferences for quantities of interest. Gelman et al. (2019) proposed an ESS estimate which combines autocovariance-based single-chain variance estimates (Hastings, 1970; Geyer, 1992) from multiple chains using between- and within-chain information in $\hat{R}$. In Section 3.2 we propose an improved algorithm, and as with $\hat{R}$, we recommend computing the ESS on the rank-normalized sample. This does not directly compute the ESS relevant for computing the mean of the parameter, but instead computes a quantity that is well defined even if the chains do not have finite mean or variance. Specifically, it computes the ESS of a sample from a rank-normalized version of the quantity of interest, using the rank transformation followed by the inverse normal transformation. This is still indicative of the effective sample size for computing an average, and if it is low the computed expectations are unlikely to be good approximations to the true target expectations.

To ensure reliable estimates of variances and autocorrelations needed for $\hat{R}$ and ESS, we recommend requiring that the rank-normalized ESS is greater than 400, a number we chose based on practical experience and simulations (see Appendix A). As typically sufficient to get a stable estimate of the Monte Carlo standard error.

Finally, when reporting quantile estimates or posterior intervals, we strongly suggest assessing the convergence of the chains for these quantiles. In Section 4.3, we show that convergence of Markov chains is not uniform across the parameter space. Specifically, convergence might be different in the bulk of the distribution (e.g., for the mean or median) than in the tails (e.g., extreme quantiles). We propose diagnostics and effective sample sizes specifically for extreme quantiles. This is different from the standard ESS estimate (which we refer to as bulk-ESS), which mainly assesses how well the centre of the distribution is resolved. Instead, these "tail-ESS" measures allow the user to estimate the MCSE for interval estimates.

## 3 $\hat{R}$ and the effective sample size

When coupled with an ESS estimate, $\hat{R}$ is the most common way to assess the convergence of a set of simulated chains. There is a link between these two measures for a single chain (see, e.g. Vats and Knudson, 2018), but we prefer to treat these as two separate questions: "Did the chains mix well?" (split-$\hat{R}$) and "Is the effective sample size large enough to get a stable estimate of uncertainty?" In this section we define the $\hat{R}$ and ESS statistics that we propose to modify.

### 3.1 Split-$\hat{R}$

Here we present split-$\hat{R}$, following Gelman et al. (2013) but using the notation of Stan Development Team (2018b). This formulation represents the current standard in convergence diagnostics for iterative simulations. In the equations below, $N$ is the number of iterations per chain, $S = MN$ is the total number of draws from all chains, $\theta$ is the number of chains, $\theta^{(m)}$ is the $m$th draw from $m$th chain, $\bar{\theta}^{(m)}$ is the average of draws from $m$th chain, and $\bar{\theta}^{(\cdot)}$ is average of all draws. For each scalar summary of interest $\theta$, we compute $B$ and $W$, the between- and within-chain variances:

$$B = \frac{N}{M-1}\sum_{m=1}^{M}(\bar{\theta}^{(m)} - \bar{\theta}^{(\cdot)})^2, \quad \text{where} \quad \bar{\theta}^{(m)} = \frac{1}{N}\sum_{n=1}^{N}\theta^{(m,n)}, \quad \bar{\theta}^{(\cdot)} = \frac{1}{M}\sum_{m=1}^{M}\bar{\theta}^{(m)} \tag{1}$$

$$W = \frac{1}{M}\sum_{m=1}^{M}s_m^2, \quad \text{where} \quad s_m^2 = \frac{1}{N-1}\sum_{n=1}^{N}(\theta^{(m,n)} - \bar{\theta}^{(m)})^2. \tag{2}$$

The between-chain variance, $B$, also contains the factor $N$ because it is based on the variance of the within-chain means, $\bar{\theta}^{(m)}$, each of which is an average of $N$ values $\theta^{(m,n)}$. We can estimate $\text{var}(\theta|y)$, the marginal posterior variance of the estimand, by a weighted average of $W$ and $B$, namely,

$$\widehat{\text{var}}^+(\theta|y) = \frac{N-1}{N}W + \frac{1}{N}B. \tag{3}$$

This quantity overestimates the marginal posterior variance assuming the starting distribution of the simulations is appropriately overdispersed compared to the target distribution, but is unbiased under stationarity (that is, if the starting distribution equals the target distribution), or in the limit $N \to \infty$. To have an overdispersed starting distribution, independent Markov chains should be initialized with diffuse starting values for the parameters.

Meanwhile, for any finite $N$, the within-chain variance $W$ should underestimate $\text{var}(\theta|y)$ because the individual chains haven't had the time to explore all of the target distribution and, as a result, will have less variability. In the limit as $N \to \infty$, the expectation of $W$ also approaches $\text{var}(\theta|y)$.

We monitor convergence of the iterative simulations to the target distribution by estimating the factor by which the scale of the current distribution for $\theta$ might be reduced if the simulations were continued in the limit $N \to \infty$. This leads to the estimator

$$\hat{R} = \sqrt{\frac{\widehat{\text{var}}^+(\theta|y)}{W}} \tag{4}$$

which for an ergodic process declines to 1 as $N \to \infty$. We call this split-$\hat{R}$ because we are applying it to chains that have been split in half so that $M$ is twice the number of simulated chains. Without splitting, $\hat{R}$ would get fooled by non-stationary chains as in Figure 1b.

In cases, where we can be absolutely certain that a single chain is sufficient, $\hat{R}$ could be computed using only single chain marginal variance and autocorrelations (see, e.g. Vats and Knudson, 2018). However we are willing to trade off a slightly higher variance for increased diagnostic sensitivity (as described in the introduction) that running multiple chains brings.

### 3.2 The effective sample size

We estimate effective sample size by combining information from $\hat{R}$ and the autocorrelation estimates within the chains.

#### The effective sample size and Monte Carlo standard error

Given $S$ independent simulation draws, the accuracy of average of the simulations $\bar{\theta}$ as an estimate of the posterior mean $E(\theta|y)$ can be estimated as

$$\text{Var}(\bar{\theta}) = \frac{\text{Var}(\theta)}{S}. \tag{5}$$

This generalizes to posterior expectations of functionals of parameters $E(g(\theta)|y)$. The square root of (5) is called the Monte Carlo standard error (MCSE).

In general, the simulations of $\theta$ within each chain tend to be autocorrelated, and $\text{Var}(\bar{\theta})$ can be larger or smaller in expectation. In the early days of using MCMC for Bayesian inference, the focus was on estimating the single chain estimate variance directly, for example, based on autocorrelations or batch means (Hastings, 1970; Geyer, 1992). See more different variance estimation algorithms in reviews by Cowles and Carlin (1996), Mengersen et al. (1999), and Robert and Casella (2004). Interpreting whether Monte Carlo standard error for a quantity of interest is small enough requires domain expertise.

Effective sample size (ESS) can be computed by dividing any variance estimate for an MCMC estimate by the variance estimate assuming independent draws. As convergence diagnostics in general started to be more popular (Gelman and Rubin, 1992; Cowles and Carlin, 1996; Mengersen et al., 1999; Robert and Casella, 2004), eventually ESS also became popular as description of the efficiency of the simulation (an early example of reporting ESS for Gibbs sampler is Sorensen et al., 1995). The term effective sample size had already been used before, for example, to describe amount of information in climatological time series (Laurmann and Gates, 1977) and the efficiency of importance sampling in Bayesian inference (Kong et al., 1994).

Although ESS is not a replacement for MCSE, it can provide a scale-free measure of information, which can be especially useful when diagnosing the sampling efficiency for a large number of variables. The downside of the term effective sample size is that it may give a false impression that the dependent simulation sample would be equivalent to an independent simulation sample with size ESS, while the equivalence is only for the estimation efficiency of the posterior mean, and the efficiency of the same dependent simulation sample for estimating another posterior functional

$E(g(\theta)|y)$ or quantiles can be very different. To simplify notation, in this section we consider the effective sample size for the posterior mean $E(\theta|y)$. This can be generalized in a straightforward manner to ESS estimates for $E(g(\theta)|y)$, Section 4.3 deals with estimating the effective sample size of quantiles, which cannot be presented as expectations.

#### Estimating the effective sample size

The first proposals of ESS estimates used information only from a single chain (see, e.g. Sorensen et al., 1995). The convergence diagnostic coda (Plummer et al., 2006) combines (since version 0.57 in 2001) single chain spectral variance based ESS estimates simply by summing them, but this approach gives over-optimistic estimates if, e.g. when different step size is used in different chains) or if chains are not mixing well. Gelman et al. (2003) proposed an ESS estimate,

$$S_{\text{eff},\text{BDA2}} = M N \frac{\widehat{\text{var}}^+}{B}, \tag{6}$$

where $\widehat{\text{var}}^+$ is a marginal posterior variance estimate and $B$ is between-chain variance estimate as given in Section 3.1. This approach works well in each chain being one batch. As there are usually only a small number of batches (chains), and information from autocorrelations is not used, this ESS estimate has high variance. Gelman et al. (2013) proposed an ESS estimate which appropriately combines autocorrelation information from multiple chains. Stan Development Team (2018b) provides some computational improvements, and the present article provides a further improved version.

For a single chain of length $N$, the effective sample size of a chain can be defined in terms of the autocorrelations within the chain at different lags,

$$N_{\text{eff}} = \frac{N}{\sum_{t=-\infty}^{\infty} \rho_t} = \frac{N}{1+2\sum_{t=1}^{\infty}\rho_t}, \tag{7}$$

where $\rho_t$ is autocorrelation at lag $t \geq 0$. An equivalent approach was used by Hastings (1970) for estimating the variance of the mean estimate from a single chain. For a chain with joint probability function $p(\theta)$ with mean $\mu$ and standard deviation $\sigma$, $\rho_t$ is defined to be

$$\rho_t = \frac{1}{\sigma^2}\int_{\Theta}(\theta^{(n)} - \mu)(\theta^{(n+t)} - \mu) p(\theta) d\theta. \tag{8}$$

This is just the correlation between the two chains offset by $t$ positions. Because we know $\theta^{(n)}$ and $\theta^{(n+t)}$ have the same marginal distribution at convergence, multiplying the two difference terms and reducing yields,

$$\rho_t = \frac{1}{\sigma^2}\int_{\Theta}\theta^{(n)}\theta^{(n+t)} p(\theta)d\theta. \tag{9}$$

In practice, the probability function in question cannot be tractably integrated and thus neither autocorrelation nor the effective sample size can be directly calculated. Instead, these quantities must be estimated from the sample itself. Computations of autocorrelations for all lags simultaneously can be done using the fast Fourier transform algorithm (FFT; see Geyer, 2011). In our experiments, FFT-based autocorrelation estimates have also been computationally more accurate than naive autocovariance computation. As recommended by Geyer (1992) we use the biased estimate with divisor $N$, instead of unbiased estimate with divisor $N - t$. Also in our experiments, the biased estimate provided smaller variance in the final ESS estimate.

The autocorrelation estimates $\hat{\rho}_m$ at lag $t$ from multiple chains $m \in (1, \ldots, M)$ are combined with the within-chain variance estimate $W = \frac{1}{M}\sum_{m=1}^{M}s_m^2$ and the multi-chain variance estimate $\widehat{\text{var}}^+ = W(N-1)/N + B/N$ to compute the combined autocorrelation at lag $t$ as,

$$\hat{\rho}_t = 1 - \frac{W - \frac{1}{M}\sum_{m=1}^{M}s_m \rho_{t,m}}{{\widehat{\text{var}}^+}} \tag{10}$$

If $\hat{\rho}_{t,m} = 0$ for all $m$, $\hat{\rho}_t = 1 - \hat{R}^{-2}$. If in addition chains are mixing well so that $\hat{R} \approx 1$, then $\hat{\rho}_t \approx 0$. If $\hat{\rho}_{t,m} \neq 0$ and $\hat{R} \approx 1$, then $\hat{\rho}_t \approx \frac{1}{M}\sum_{m=1}^{M}\rho_{t,m}$. If chains are mixing well, this expression is

equivalent to averaging autocorrelations, and if chains are not mixing well, simulations in each chain are implicitly assumed to be more correlated with each other. In our experiments, multi-chain $\hat{\rho}_t$ given by (10) and FFT-based $\hat{\rho}_{t,m}$ had smaller variance than the related multi-chain $\rho_t$ proposed by Gelman et al. (2013).

As noise in the correlation estimates $\hat{\rho}_t$ increases as $t$ increases, the large-lag terms need to be down weighted (lag window approach, see, e.g. Geyer, 1992; Flegal and Jones, 2010) or the sum of $\hat{\rho}_t$ can be truncated with some truncation lag $T$ to get

$$S_{\text{eff}} = \frac{NM}{1 + 2\sum_{t=1}^{T}\hat{\rho}_t}, \tag{11}$$

We use a truncation rule proposed by Geyer (1992), which takes into account certain properties of the autocorrelations for Markov chains. Even when the simulations are constructed using an MCMC algorithm, the time series of simulations for a scalar parameter or summary will not in general have the Markov property; nevertheless we have found these Markov-derived heuristics to work well in practice. In our experiments, Geyer's truncation had superior stability compared to lag-taper (Flegal and Jones, 2014) and slug-tail (Vats and Knudson, 2018) lag window approaches.

For Markov chains typically used in MCMC, negative autocorrelations can happen only on odd lags and by summing over pairs starting from lag $t = 0$, the paired autocorrelation is guaranteed to be positive, monotone and convex modulo estimator noise (Geyer, 1992, 2011). The effective sample size of combined chains is then defined as

$$S_{\text{eff}} = \frac{NM}{\hat{\tau}}, \tag{12}$$

where

$$\hat{\tau} = 1 + 2\sum_{t=1}^{2k+1}\hat{\rho}_t = -1 + 2\sum_{\ell=0}^{k}\hat{\rho}_{\ell}, \tag{13}$$

and $\hat{\rho}_{\ell} = \hat{\rho}_{2\ell} + \hat{\rho}_{2\ell+1}$. The initial positive sequence estimator is obtained by choosing the largest $k$ such that $\hat{\rho}_{\ell} > 0$ for all $\ell' = 1, \ldots, k$. The initial monotone sequence estimator is obtained by further reducing $\hat{\rho}_{\ell}$ to the minimum of the preceding values so that the estimated sequence becomes monotone.

In case of antithetic Markov chains, which have negative autocorrelations on odd lags, the effective sample size $S_{\text{eff}}$ can also be larger than $S$. For example, the dynamic Hamiltonian Monte Carlo algorithms used in Stan (Hoffman and Gelman, 2014; Betancourt, 2017; Stan Development Team, 2018b) is likely to produce $S_{\text{eff}} > S$ for parameters with a dense to Gaussian posterior (in the unconstrained space) and low dependence on the other parameters. The benefit of this kind of super-efficiency is often limited as it is unlikely to simultaneously have super-efficiency for mean and variance (or tail quantiles) as demonstrated in our experiments.

In extreme antithetic cases, magnitude of single lag autocorrelations can stay large for a large lag $t$, even if the paired autocorrelations are close to zero. To improve the stability and reduce the variance of the ESS estimate, we determine the truncation lag as a usual, but compute the average of truncated sum ending to usual odd lag and truncated sum ending to the next even lag. Sometimes these estimates are used for very short antithetic chains, and just by chance there can be strange estimates, and as highly antithetic chains are unlikely, in our software implementation we have restricted the ESS estimate to an upper bound of $\log_{10}(S)$.

The values of $\hat{R}$ and ESS require reliable estimates of variances and autocorrelations (in addition to the existence of these quantities; see our Cauchy examples in Section 5.1), which can only occur if the chains have enough independent replicates. In particular, we only recommend relying on the $\hat{R}$ estimate to make decisions about the quality of the chain if each of the split chains has an average ESS estimate of at least 50. In our minimum recommended setup of four parallel chains, the total ESS should be at least 400 before we expect $\hat{R}$ to be useful.

## 4 Improving convergence diagnostics

### 4.1 Rank normalization helps $\hat{R}$ when there are heavy tails

As split-$\hat{R}$ and $S_{\text{eff}}$ are well defined only if the marginal posteriors have finite mean and variance, we propose to use rank normalized parameter values instead of the actual parameter values for the purpose of diagnosing convergence.

The use of ranks to avoid the assumption of normality goes back to Friedman (1937). Chernoff and Savage (1958) show that rank based approaches have good asymptotic efficiency. Instead of using rank values directly and modifying tests for them, Fisher and Yates (1938) propose to use expected normal scores (ordered statistics) and use the normal models. Blom (1958) shows that accurate approximation of the expected normal scores can be computed efficiently from ranks using an inverse normal transformation.

Rank normalized split-$\hat{R}$ and $S_{\text{eff}}$ are computed using the equations in Section 3.1 and 3.2, but replacing the original parameter values $\theta^{(m,n)}$ with their corresponding rank normalized values (normal scores) denoted as $z^{(m,n)}$. Rank normalization proceeds as follows: First, replace each value $\theta^{(m,n)}$ by its rank $r^{(m,n)}$ within the pooled draws from all chains. Average rank for ties are used to conserve the number of unique values of discrete quantities. Second, transform ranks to normal scores using the inverse normal transformation and a fractional offset (Blom, 1958):

$$z^{(m,n)} = \Phi^{-1}\left(\frac{r^{(m,n)} - 3/8}{S - 1/4}\right). \tag{14}$$

Using normalized ranks (normal scores) $z^{(m,n)}$ instead of ranks $r^{(m,n)}$ themselves has the benefits that (1) for continuous variables the normality assumptions in computation of $\hat{R}$ and $S_{\text{eff}}$ are fulfilled (via the transformation), (2) the values of $\hat{R}$ and $S_{\text{eff}}$ are practically the same as before for nearly normally distributed variables (the interpretation doesn't change for cases where the original $\hat{R}$ worked well), and (3) rank-normalized $\hat{R}$ and $S_{\text{eff}}$ are invariant to monotone transformations (e.g. we get the same diagnostic values when examining a variable or logarithm of a variable). The effects of rank normalization on online appendix.

We will use the term bulk effective sample size (bulk-ESS or bulk-$S_{\text{eff}}$) to refer to the effective sample size based on the rank normalized draws. Bulk-ESS is useful for diagnosing problems due to trends or different locations of the chains (see Appendix A). Further, it is well defined even for distributions with infinite mean or variance (see Appendix A). Further, it is well defined even for distributions with infinite mean or variance (see previous example with Cauchy distribution). More experiments with various applications can be found in the online appendix at https://aehluri.github.io/rhat_ess/rhat_ess.html.

We will use the term bulk effective sample size (bulk-ESS or bulk-$S_{\text{eff}}$) to refer to the effective sample size based on the rank normalized draws. Bulk-ESS is useful for diagnosing problems due to trends or different locations of the chains (see Appendix A). Further, it is well defined even for distributions with infinite mean or variance.

### 4.2 Folding reveals problems with variance and tail exploration

Both original and rank normalized split-$\hat{R}$ can be fooled if the chains have the same location but different scales. This can happen if one or more chains is stuck near the middle of the distribution. To alleviate this problem, we propose a rank normalized split-$\hat{R}$ statistic not only for the original draws $\theta^{(m,n)}$, but also for the corresponding folded draws $\zeta^{(m,n)}$, absolute deviations from the median,

$$\zeta^{(m,n)} = \left|\theta^{(m,n)} - \text{median}(\theta)\right|. \tag{15}$$

We call the rank normalized split-$\hat{R}$ measure computed on the $\zeta^{(m,n)}$ values folded-split-$\hat{R}$. This measures convergence in the tails rather than in the bulk of the distribution. To obtain a single conservative $\hat{R}$ estimate, we propose to report the maximum of rank normalized split-$\hat{R}$ and rank normalized folded-split-$\hat{R}$ for each parameter.

Figure 1 demonstrates how our new version of $\hat{R}$ catches some examples of lack of convergence that were not detected by earlier versions of the potential scale reduction factor. We do not intend with this example to claim that our new $\hat{R}$ is perfect—of course, it can be defeated to. Rather, we use these simple scenarios to develop intuition about problems with traditional split-$\hat{R}$ and possible directions for improvement.

### 4.3 Localizing convergence diagnostics: assessing the quality of quantiles, the median absolute deviation, and small-interval probabilities

The new $\hat{R}$ and bulk-ESS introduced above are useful as overall efficiency measures. Next we introduce convergence diagnostics for quantiles and related quantities, which are more focused measures and help to diagnose reliability of reported posterior intervals. Estimating the efficiency of quantile estimates has a high practical relevance in particular as we observe the efficiency for tail quantiles is often lower than for the mean or median. This especially has implications if people are making decisions based on whether or not a specific quantile is below or above a fixed value (for example, if a posterior contains zeros).

The $\alpha$-quantile is defined as the parameter value $\theta_\alpha$ for which $\text{Pr}(\theta \leq \theta_\alpha) = \alpha$. An estimate $\hat{\theta}_\alpha$ of $\theta_\alpha$ can be obtained by finding the $\alpha$-quantile of the empirical cumulative distribution function (ECDF) of the posterior draws $\theta^{(s)}$.

The cumulative probabilities $\text{Pr}(\theta \leq \theta_\alpha)$ can be written as expectation which can be estimated with sample mean

$$\text{Pr}(\theta \leq \theta_\alpha) = E(I(\theta \leq \theta_\alpha)) \approx I_\alpha = \frac{1}{S}\sum_{s=1}^{S}I(\theta^{(s)} \leq \theta_\alpha), \tag{16}$$

where $I(\cdot)$ is the indicator function. The indicator function transforms simulation draws to 0's and 1's, and thus the subsequent computations are objective invariant. Efficiency estimates of the ECDF at any point can be obtained by applying rank-normalizing and subsequent computations directly on the indicator function's results. More details on the variance of the cumulative distribution function can be found in the online appendix. Raftery and Lewis (1992) proposed to focus on accuracy of cumulative or interval probabilities and also proposed a specific effective sample size estimate for these probability estimates.

Although the quantiles cannot be written directly as an expectation, the quantile estimate is strongly consistent and Doss et al. (2014) provide conditions for a quantile central limit theorem. Assuming the CDF is a continuous function $F$ which is smooth near an $\alpha$-quantile of interest, we could compute

$$\text{Var}(\hat{\theta}_\alpha) = \text{Var}(F^{-1}(I_\alpha)) = \text{Var}(I_\alpha)/f(\theta_\alpha). \tag{17}$$

Even if we do not usually know $F$, this shows that the variance of $\hat{\theta}_\alpha$ is just the variance of $I_\alpha$, scaled by the unknown density $f(\theta_\alpha)$, and thus the effective sample size for the quantile estimate $\hat{\theta}_\alpha$ is the same as for the corresponding cumulative probability.

To get a better sense of the sampling efficiency in the distributions' tails, we propose to compute the minimum of the effective sample size of the 5% and 95% quantiles, which we will call tail-ESS (or tail-$S_{\text{eff}}$). Tail-ESS can help diagnosing problems due to different scales of the chains (see Appendix A).

Since the marginal posterior distributions might not have finite mean and variance, for example, the popular rstanarm package (Stan Development Team, 2018a) reports median and median absolute deviation (MAD) instead of mean and standard error. Median and MAD are well defined even when the marginal distribution does not have finite mean and variance. Since the median is the same as the 50% quantile, we can get an efficiency estimate for it as for any other quantile.

Further, we can also compute an efficiency estimate for the median absolute deviation by computing the efficiency estimate of an indicator function based on the folded parameter values $\zeta$ (see (15)).

$$\text{Pr}(\zeta \leq \zeta_{0.5}) \approx I_{\zeta, 0.5} = \frac{1}{S}\sum_{s=1}^{S}I(\zeta^{(s)} \leq \zeta_{0.5}), \tag{18}$$

where $\zeta_{0.5}$ is the median of the folded values. The efficiency estimate for the MAD is obtained by applying the same approach as for the median (and other quantiles) but with the folded parameters values.

We can get more local efficiency estimates by considering small probability intervals. We propose to compute the efficiency estimates for

$$I_{a,\delta} = \text{Pr}(Q_a < \theta \leq Q_{a+\delta}), \tag{19}$$

where $Q_\alpha$ is an empirical $\alpha$-quantile, $\delta = 1/k$ is the length of the interval for some positive integer $k$, and $\alpha \in (0, \ldots, 1-\delta)$ changes in steps of $\delta$. Each interval has $S/k$ draws, and the efficiency measures the autocorrelation of the indicator function which is 1 when the values are inside the specific interval and 0 otherwise. This gives us a local efficiency measure for quantiles and can be used to build intuition about what types of posterior functionals can be computed as illustrated in the examples. While the expectation of a function that only depends on intermediate values can be usually estimated with relative ease, expectations of other posterior functionals that depend critically on the tail of the distribution will be usually more difficult to estimate. In addition, small probability intervals can be used in practical equivalence testing (see, e.g. Wells, 2010).

A natural multivariate extension of small intervals would be to consider small probability volumes using a box or sphere with dimensions determined for example, by marginal quantiles. The visualization of the multivariate results would be easiest in 2 or 3 dimensions. In higher dimensions, for example, k-means clustering could be used to determine hyper-spheres. Even if it gets more difficult to visualize where the problematic region in the high dimensional space is, the diagnosing that sampling efficiency is low in some parts of the posterior can be useful.

### 4.4 Monte Carlo error estimates for quantiles

To obtain the MCSE for $\hat{\theta}_\alpha$, Doss et al. (2014) use a Gaussian kernel density estimate of $f(\theta_\alpha)$ and batch means and subsampling bootstrap method for estimating $\text{Var}(I_\alpha)$, and Liu et al. (2016) use a flat top kernel density estimate for $f(\theta_\alpha)$ and a spectral variance approach for $\text{Var}(I_\alpha)$.

We propose an alternative approach which avoids the need to estimate $f(\theta_\alpha)$. Here is how we estimate, for example, a central 90% Monte Carlo error interval for $\hat{\theta}_\alpha$ (any quantiles or intervals can be computed using the same algorithm):

1. Compute the effective sample size $S_{\text{eff}}$ for estimating the expectation $E(\theta \leq \hat{\theta}_\alpha)$.
2. Compute $a$ and $b$ as 5% and 95% quantiles (for other than 90% interval use corresponding quantiles) of

$$\text{Beta}(S_{\text{eff}}\alpha + 1, S_{\text{eff}}(1-\alpha) + 1). \tag{20}$$

Using $S_{\text{eff}}$ here takes into account the efficiency of the posterior draws. The variance of this beta distribution matches the variance of normal approximation, but using quantiles guarantees that $0 < a < 1$ and $0 < b < 1$. Asymptotically, as $S_{\text{eff}} \to \infty$, this beta distribution converges towards a normal distribution. Instead of drawing random sample from the beta distribution, we get sufficient accuracy for MCSE using just two deterministically chosen quantiles.

3. Propagate $a$ and $b$ through the nonlinear inverse transforms $A = (F^{-1}(a))$ and $B = (F^{-1}(b))$. Then $A$ and $B$ are corresponding quantiles in the transformed scale. As we don't know $F$ for the quantity of interest, we use a simple numerical approximation:

$$\tilde{A} = \theta^{(s')} \text{ where } s' \leq S\alpha < s' + 1$$
$$\tilde{B} = \theta^{(s'')} \text{ where } s'' - 1 < Sb \leq s'',$$

where $\theta^{(s)}$ have been sorted in ascending order. $A$ and $B$ are then estimated 5% and 95% quantiles (or other quantiles, depending on which quantiles $a$ and $b$ were chosen) via unscented transformation which is known to estimate the standard error from the transformed quantity correct to the second order (Julier and Uhlmann, 1997).

The Monte Carlo standard error for $\hat{\theta}_\alpha$ can be approximated, for example, by computing $(\tilde{B} - \tilde{A})/2$, where $\tilde{A}$ and $\tilde{B}$ are estimated 16% and 84% Monte Carlo error quantiles computed with the above algorithm. Use of deterministically chosen 16% and 84% quantiles $a$ and $b$, propagating them through the nonlinear transformation and estimating the standard error from the transformed quantity correct to the second order (Julier and Uhlmann, 1997).

The above algorithm is useful as a default, as it is more robust than density estimation based approaches for non-smooth densities, for example, when variables are constrained in a normal case. For example, when variables are constrained in a normal case. A and B are likely to have high variance in case of extreme tail quantities and thick-tailed distributions, as there are not many $\theta^{(s)}$ in extreme tails. The approaches using a density estimate for $f(\theta_\alpha)$ can provide better accuracy when the assumptions of the density estimate are fulfilled, but can have a high bias if the density is not smooth or the shape of the kernel doesn't match well with the tail properties of the distribution. To improve accuracy of extreme tail quantile estimates, common extreme value models could be used to model the tail of the distribution.

### 4.5 Diagnostic visualizations

In order to develop intuitions around the convergence of iterative algorithms, we propose several new diagnostic visualizations in addition to the numerical convergence diagnostics discussed above. We illustrate with several examples in Section 5.

**Rank plots.** Extending the idea of using ranks instead of the original parameter values, we propose using rank plots for each chain instead of trace plots. Rank plots, such as Figure 6, are histograms of the ranked posterior draws (ranked over all chains) plotted separately for each chain. If all of the chains are targeting the same posterior, we expect the ranks in each chain to be uniform. When one chain has a different location or scale parameter, this will be reflected in the deviation from uniformity. If rank plots of all chains look similar, this indicates good mixing of the chains. As compared to trace plots, rank plots don't tend to squeeze to a fuzzy mess when used with long chains.

**Quantile and small-interval plots.** The efficiency of quantiles or small-interval probabilities may vary drastically across different quantiles and small-interval positions, respectively. We thus propose to use diagnostic plots that display efficiency of quantiles or interval probabilities across their whole range to better diagnose areas of the distributions that the iterative algorithm fails to explore efficiently.

**Efficiency per iteration plots.** For a well-explored distribution, we expect the ESS measures to grow linearly with the total number of draws $S$; equivalently, that the relative efficiency (ESS/$S$) is approximately constant for different values of $S$. For small number of draws, both bulk and tail-ESS may be unreliable and cannot necessarily detect convergence problems. As a result, some bases may only be detectable as $S$ increases. Equivalently, in such a case, we would expect to see a relatively sharp drop in the relative efficiency measure. We therefore propose to plot the change of both bulk and tail ESS with increasing $S$. This can be done based on a single model without a need to refit, as we can just extract initial sequences of certain length from the original chains. However, some convergence problems only occur at relatively high $S$ and may thus not be detectable if the total number of draws is too small.

## 5 Examples

We now demonstrate our approach and recommended workflow on several small examples. Unless mentioned otherwise, we use dynamic Hamiltonian Monte Carlo with multinomial sampling (Betancourt, 2017) as implemented in Stan (Stan Development Team, 2018b). We run 4 chains, each with 1000 warmup iterations, which do not form a Markov chain and are discarded, and 1000 post-warmup iterations, which are saved and used for inference.

### 5.1 Cauchy: A distribution with infinite mean and variance

Traditional $\hat{R}$ is based on calculating within and between chain variances. If the marginal distribution of a quantity of interest is such that the variance is infinite, this approach is not well justified, as we demonstrate here with a Cauchy-distributed example.

#### Nominal parameterization of the Cauchy distribution

We start by simulating from independent standard Cauchy distributions for each element of a 50-dimensional vector $x$:

$$x_j \sim \text{Cauchy}(0,1) \quad \text{for } j = 1, \ldots, 50. \tag{21}$$

Figure 3: Local efficiency of small-interval probability estimates for the Cauchy model with nominal parameterization. Results are displayed for the element of $x$ with the smallest tail-ESS. The dashed line shows the recommended threshold of 400. Orange ticks show the position of iterations that exceeded the maximum tree depth in the dynamic HMC algorithm.

Figure 4: Efficiency of quantile estimates for the Cauchy model with nominal parameterization. Results are displayed for the element of $x$ with the smallest tail-ESS. The dashed line shows the recommended threshold of 100.

We monitor the convergence for each of the $x_j$ separately. As the distribution of $x$ has thick tails, we may expect any generic MCMC algorithm to have mixing problems. Several values of $\hat{R}$ greater than 1 and some effective sample size less than 400 also indicate convergence problems (in addition a HMC-specific diagnostic, "iterations exceed maximum tree depth" (Stan Development Team, 2018b) also indicated slow mixing of the chains). The online appendix contains more results with longer chains and other $\hat{R}$ diagnostics. We can further analyze potential problems using local efficiency estimates and rank plots. For this example, we take a detailed look at $x_{30}$, which had the smallest bulk-ESS of 2848. Figures 7 and 8 show good sampling efficiency for the small-interval probability and quantile estimates (see Section 4.3). The efficiency of small-interval probability estimates decreases Section 4.3). The efficiency of sampling is low in the tails, which is clearly caused by slow mixing in long tails of the Cauchy distribution. Figure 4 shows the efficiency of quantile estimates (see Section 4.3), which is also low in the tails.

We may also investigate the estimated effective sample sizes change when we use more and more draws: Brooks and Gelman (1998) proposed to use split graph for $\hat{R}$. If the effective sample size is highly unstable, does not increase proportionally with more draws, or even decreases, this indicates that simply running longer chains will likely not solve the convergence issues. In Figure 5, we see how unstable both bulk-ESS and tail-ESS are in the example. In Figure 6 clearly show the mixing problem between chains. In case of good mixing all rank plots should be close to uniform. More experiments can be found in Appendix B and in the online appendix.

analyze potential problems using local efficiency estimates and rank plots. For this example, we take a detailed look at $x_{30}$, which had the smallest tail-ESS of 34. Figure 3 shows the local efficiency of small-interval probability estimates (see Section 4.3). The efficiency of sampling is low in the tails, which is clearly caused by slow mixing in long tails of the Cauchy distribution. Figure 4 shows the efficiency of quantile estimates (see Section 4.3), which is also low in the tails.

We may also investigate how the estimated effective sample sizes change when we use more and more draws: Brooks and Gelman (1998) proposed to use split graph for $\hat{R}$. If the effective sample size is highly unstable, does not increase proportionally with more draws, or even decreases, this indicates that simply running longer chains will likely not solve the convergence issues. In Figure 5, we see how unstable both bulk-ESS and tail-ESS are in the example. In Figure 6 clearly show the mixing problem between chains. In case of good mixing all rank plots should be close to uniform. More experiments can be found in Appendix B and in the online appendix.

#### Alternative parameterization of the Cauchy distribution

Next, we examine an alternative parameterization of the Cauchy as a scale mixture of Gaussians:

$$a_j \sim \text{Normal}(0,1), \quad b_j \sim \text{Gamma}(0.5, 0.5), \quad x_j = a_j/\sqrt{b_j}. \tag{22}$$

The model has two parameters which have thin-tailed distributions so that we may assume good mixing of Markov chains. Cauchy-distributed $x$ can be computed deterministically from $a$ and $b$. In addition to improved sampling performance, the example illustrates that focusing on diagnostics matters. We define two 50-dimensional parameter vectors $a$ and $b$ from which the 50-dimensional quantity $x$ is computed.

For all parameters, $\hat{R}$ is less than 1.01 and ESS exceeds 400, indicating that sampling worked much better with this alternative parameterization. The online appendix contains more results using other parameterizations of the Cauchy distribution. The vectors $a$ and $b$ used to form the Cauchy-distributed $x$ have stable quantile, mean and variance values. We can further

### 5.2 Hierarchical model: Eight schools

The eight schools problem is a classic example (see Section 5.5 in Gelman et al., 2013), which even in its simplicity illustrates typical problems in inference for hierarchical models. We can parameterize this simple model in at least two ways. The centered parameterization ($\theta, \mu, \tau, \sigma$) is,

$$\theta_j \sim \text{Normal}(\mu, \tau)$$
$$y_j \sim \text{Normal}(\theta_j, \sigma_j).$$

Figure 7: Local efficiency of small-interval probability estimates for the Cauchy model with alternative parameterization. Results are displayed for the element of $x$ with the smallest tail-ESS. The dashed line shows the recommended threshold of 400.

Figure 8: Efficiency of quantile estimates for the Cauchy model with alternative parameterization. Results are displayed for the element of $x$ with the smallest tail-ESS. The dashed line shows the recommended threshold of 400.

Figure 9: Rank plots of posterior draws from four chains for the Cauchy model with alternative parameterization. Results are displayed for the element of $x$ with the smallest tail-ESS.

In contrast, the non-centered parameterization $(\tilde{\theta}, \mu, \tau, \sigma)$ can be written as,

$$\tilde{\theta}_j \sim \text{Normal}(0,1)$$
$$\theta_j = \mu + \tau\tilde{\theta}_j$$
$$y_j \sim \text{Normal}(\theta_j, \sigma_j).$$

In both cases, $\theta_j$ are the treatment effects in the eight schools, and $\mu, \tau$ represent the population mean and standard deviation of the distribution of these effects. In the centered parameterization, the $\theta$ are parameters, whereas in the non-centered parameterization, the $\theta$ is a derived quantity.

Geometrically, the centered parameterization exhibits a funnel shape that contracts into a region of strong curvature around the population mean when faced with small values of the population standard deviation $\tau$, making it difficult for many simple Markov chain methods to adequately explore the full distribution of this parameter. In the following, we will focus on analyzing convergence of $\tau$. The online appendix contains more detailed analysis of different algorithm variants and results of longer chains.

#### A centered eight schools model

Instead of the default options, we run the centered parameterization model with more conservative settings of the HMC sample to reduce the probability of getting divergent transitions, which bias the obtained estimates if they occur; for details see Stan Development Team (2018b). Still, we observe a lot of divergent transitions and the estimated Bayesian fraction of missing information (Betancourt, 2017) is also low, which indicate convergence problems. We can also use $\hat{R}$ and ESS diagnostics to recognize problematic parts of the posterior. The latter two have the advantage over the divergent transitions diagnostic that they can be used with all MCMC algorithms not only with HMC.

Bulk-ESS and tail-ESS for the between-school standard deviation $\tau$ are 67 and 82, respectively. Both are much less than 400, indicating we should investigate that parameter more carefully. Figures 11 and 12 show the sampling efficiency for the small-interval probability and quantile estimates. The sampler has difficulties in exploring small $\tau$ values. As the sampling efficiency for small $\tau$ values is practically zero, we may assume that we miss substantial amount of posterior mass and get biased estimates. In this case, the severe sampling problems for small $\tau$ values is reflected in the sampling efficiency on all quantile values. Figure 13 shows how the estimated effective sample sizes change when we use more and more draws. Here we do not see sudden changes, but both bulk-ESS and tail-ESS are consistently low. In line with the other findings, rank plots of $\tau$

displayed in Figure 14 clearly show problems in the mixing of the chains. In particular, the rank plot for the first chain indicates that it was unable to explore the lower-end of the posterior range, while the spike in the rank plot for chain 2 indicates that it spent too much time stuck in these values. More experiments can be found in Appendices C and D as well as in the online appendix.

#### Non-centered eight schools model

For hierarchical models, the corresponding non-centered parameterization often works better (Betancourt and Girolami, 2019). For reasons of comparability, we use the same conservative sampler settings as for the centered parameterization model. For the non-centered parameterization, we do not observe divergences or other warnings. All values of $\hat{R}$ are less than 1.01 and ESS exceeds 400, indicating a much better efficiency of the non-centered parameterization. Figures 15 and 16 show the efficiency of small-interval probability estimates and the efficiency of quantile estimates for $\tau$. Small $\tau$ values are still more difficult to explore, but the relative efficiency is good. The rank plots of $\tau$ Figure 17

show no substantial differences between chains.

## References

Michael Betancourt. A conceptual introduction to Hamiltonian Monte Carlo. arXiv preprint arXiv:1701.02434, 2017.

Michael Betancourt and Mark Girolami. Hamiltonian Monte Carlo for hierarchical models. In *Current Trends in Bayesian Methodology with Applications*, pages 79–101. Chapman and Hall/CRC, 2019.

Gunnar Blom. *Statistical Estimates and Transformed Beta-Variables*. Wiley; New York, 1958.

Stephen P. Brooks and Andrew Gelman. General methods for monitoring convergence of iterative simulations. *Journal of Computational and Graphical Statistics*, 7(4):434–455, 1998.

Bob Carpenter, Andrew Gelman, Matthew Hoffman, Daniel Lee, Ben Goodrich, Michael Betancourt, Marcus Brubaker, Jiqiang Guo, Allen Riddell. Stan: A probabilistic programming language. *Journal of Statistical Software*, 76(1):1–32, 2017. doi: 10.18637/jss.v076.i01.

Herman Chernoff and I. Richard Savage. Asymptotic normality and efficiency of certain nonparametric test statistics. *Annals of Mathematical Statistics*, 29(4):972–994, 1958.

Mary Kathryn Cowles and Bradley P. Carlin. Markov chain Monte Carlo convergence diagnostics: A comparative review. *Journal of the American Statistical Association*, 91(434):883–904, 1996.

Perry de Valpine, Daniel Turek, Christopher J. Paciorek, Clifford Anderson-Bergman, Duncan Temple Lang, and Rastislav Bodik. Programming with models: Writing statistical algorithms for general model structures with NIMBLE. *Journal of Computational and Graphical Statistics*, 26(2):403–413, 2017.

Charles R. Doss, James M. Flegal, Garin L. Jones, and Ronald C. Neath. Markov chain Monte Carlo estimation of quantiles. *Electronic Journal of Statistics*, 8(2):2448–2478, 2014.

Ronald A. Fisher and Frank Yates. *Statistical Tables for Biological, Agricultural, and Medical Research*. Oliver & Boyd; Edinburgh, 1938.

James M. Flegal and Galin L. Jones. Batch means and spectral variance estimators in Markov chain Monte Carlo. *Annals of Statistics*, 38(2):1034–1070, 2010.

Milton Friedman. The use of ranks to avoid the assumption of normality implicit in the analysis of variance. *Journal of the American Statistical Association*, 32(200):675–701, 1937.

Andrew Gelman and Donald B. Rubin. Inference from iterative simulation using multiple sequences (with discussion). *Statistical Science*, 7(4):457–511, 1992.

Andrew Gelman, John B. Carlin, Hal S. Stern, and Donald R. Rubin. *Bayesian Data Analysis*, second edition. Chapman & Hall, 2003.

Andrew Gelman, Zaiying Huang, David van Dyk, and W. John Boscardin. Using redundant parameters to fit hierarchical models. *Journal of Computational and Graphical Statistics*, 17:95–122, 2008.

Andrew Gelman, John B. Carlin, Hal S. Stern, David B. Dunson, Aki Vehtari, and Donald R. Rubin. *Bayesian Data Analysis*, third edition. CRC Press, 2013.

Charles J. Geyer. Practical Markov chain Monte Carlo. *Statistical Science*, 7:473–483, 1992.

Charles J. Geyer. Introduction to Markov chain Monte Carlo. In S. Brooks, A. Gelman, G. L. Jones, and X. L. Meng, editors, *Handbook of Markov Chain Monte Carlo*. CRC Press, 2011.

W. K. Hastings. Monte Carlo sampling methods using Markov chains and their applications. *Biometrika*, 57(1):97–109, 1970.

Matthew D. Hoffman and Andrew Gelman. The No-U-Turn Sampler: Adaptively setting path lengths in Hamiltonian Monte Carlo. *Journal of Machine Learning Research*, 15:1593–1623, 2014. URL http://jmlr.org/papers/v15/hoffman14a.html.

Pierre E. Jacob, John O'Leary, and Yves F. Atchadé. Unbiased Markov chain Monte Carlo with couplings. arXiv preprint arXiv:1708.03025, 2017.

Simon J Julier and Jeffrey K Uhlmann. New extension of the kalman filter to nonlinear systems. In *Proc. SPIE 3068, Signal processing, sensor fusion, and target recognition VI*, pages 182–193. SPIE, 1997.

Augustine Kong, Jun S. Liu, and Wing Hung Wong. Sequential imputations and Bayesian missing data problems. *Journal of the American Statistical Association*, 89(425):278–288, 1994.

John A. Laurmann and W. Lawrence Gates. Statistical considerations in the evaluation of climatic experiments with atmospheric general circulation models. *Journal of the Atmospheric Sciences*, 34(8):1187–1199, 1977.

Jia Liu, Daniel J. Nordman, and William Q. Meeker. The number of MCMC draws needed to compute Bayesian credible bounds. *The American Statistician*, 70(3):275–284, 2016.

David Lunn, David Spiegelhalter, Andrew Thomas, and Nicky Best. The BUGS project: Evolution, critique and future directions. *Statistics in Medicine*, 28(25):3049–3067, 2009.

David J Lunn, Andrew Thomas, Nicky Best, and David Spiegelhalter. WinBUGS—a Bayesian modelling framework: Concepts, structure, and extensibility. *Statistics and Computing*, 10(4):325–337, 2000.

Kerrie L. Mengersen, Christian P. Robert, and Chantal Guihenneuc-Jouyaux. MCMC convergence diagnostics: A review. In *Jose M. Bernardo, James O. Berger, A. P. David, editors, Bayesian Statistics 6*, pages 415–440. Oxford University Press, 1999.

Radford M. Neal. Slice sampling. *Annals of Statistics*, 31(3):705–767, 2003.

Martyn Plummer. JAGS: A program for analysis of Bayesian graphical models using Gibbs sampling. In *Proceedings of the 3rd International Workshop on Distributed Statistical Computing*, 2003.

Martyn Plummer, Nicky Best, Kate Cowles, and Karen Vines. CODA: Convergence diagnosis and output analysis for MCMC. *R News*, 6(1):7–11, 2006. URL https://journal.r-project.org/archive/.

Adrian E. Raftery and Steven M. Lewis. How many iterations in the Gibbs sampler? In *J. M. Bernardo, J. O. Berger, A. P. David, and A. F. Smith*, editors, *Bayesian Statistics 4*, pages 763–773. Oxford University Press, 1992.

Christian P. Robert and George Casella. *Monte Carlo Statistical Methods*. Springer, second edition, 2004.

John Salvatier, Thomas V. Wiecki, and Christopher Fonnesbeck. Probabilistic programming in Python using PyMC3. *PeerJ Computer Science*, 2:e55, 2016.

D. A. Sorensen, S. Andersen, D. Gianola, and I. Korsgaard. Bayesian inference in threshold models using Gibbs sampling. *Genetics Selection Evolution*, 27(3):229, 1995.

Stan Development Team. RStanArm: Bayesian applied regression modeling via Stan. R package version 2.17.4, 2018a. URL http://mc-stan.org.

Stan Development Team. Stan Modeling Language Users Guide and Reference Manual. version 2.18.0, 2018b. URL http://mc-stan.org.

Dootika Vats and Christina Knudson. Revisiting the Gelman-Rubin diagnostic. *arXiv preprint arXiv:1812.09384*, 2018.

Stefan Wellek. *Testing Statistical Hypotheses of Equivalence and Noninferiority*. Chapman and Hall/CRC, 2010.
