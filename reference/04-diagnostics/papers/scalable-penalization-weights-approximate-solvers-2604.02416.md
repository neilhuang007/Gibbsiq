# Scalable Determination of Penalization Weights for Constrained Optimizations on Approximate Solvers

**Authors:** Edoardo Alessandrom,1,2 Sergi Ramos-Calderer,1,† Michel Krispin,‡ Fritz Schinkel,§ Stefan Walter,¶ Martin Kliesch,‡ Leandro Aolita,† and Ingo Roth†

**Affiliations:**
- 1 Quantum Research Center, Technology Innovation Institute (TII), Abu Dhabi
- 2 SISSA — Scuola Internazionale Superiore di Studi Avanzati, Trieste, Italy
- † Centre for Quantum Technologies, National University of Singapore, Singapore
- ‡ Hamburg University of Technology, Institute for Quantum Inspired and Quantum Optimization, Hamburg, Germany
- § Fujitsu Germany GmbH, Mies-van-der-Rohe-Straße 8, 80807 Munich, Germany

## Abstract

Quadratic unconstrained binary optimization (QUBO) provides problem formulations for various computational problems that can be solved with dedicated QUBO solvers, which can be based on classical or quantum computation. A common approach to constrained combinatorial optimization problems is to enforce the constraints in the QUBO formulation by adding penalty terms. Penalization introduces an additional hyperparameter that significantly affects the solver's efficacy: the relative weight between the objective terms and the penalization terms. We develop a pre-computation strategy for determining penalization weights with provable guarantees for Gibbs solvers and polynomial complexity for broad problem classes. Experiments across diverse problems and solver architectures, including large-scale instances on Fujitsu's Digital Annealer, show robust performance and order-of-magnitude speedups over existing heuristics.

## Introduction

Combinatorial optimization problems arise widely in both theoretical research and real-world applications, aiming to identify the optimal configuration of decision variables that minimizes a given objective function. The corresponding search space typically has a size scaling exponentially with the number of variables, rendering the optimization a computationally hard problem. Methods for solving these problems have been a subject of intense study in both classical and quantum computation [1]. In particular, powerful heuristics and dedicated hardware have been developed [2–11] to tackle quadratic unconstrained binary optimizations (QUBOs) [12, 13]. These include approaches based on Gibbs sampling or simulated annealing [14–21], specialized approaches for digital annealing [22–24], and quantum primitives such as adiabatic evolution [25–28] and recent variants of the Quantum Approximate Optimization Algorithm (QAOA) [29–33]. Practical solvers tend to be heuristic algorithms that yield approximate solutions. For instance, simulated annealing (or any solver based on Gibbs sampling) outputs a configuration sampled from a low-temperature distribution over the combinatorial space, with an objective value close (but in general not equal) to the optimum. The colder the distribution, the higher the probability that the output state is very close to the optimal solution of the problem. More precisely, for ideal Gibbs samplers, each configuration $x$ is sampled with a probability proportional to $e^{-\beta E(x)/\eta}$, where $E(x)$ is the energy of the configuration and $\beta$ is the inverse temperature of the system. Sampling from this probability distribution or estimating the associated partition function is generally hard, so practical solvers rely on Markov Chain Monte Carlo techniques [14, 34] and annealing schedules to approximate it. These methods, such as simulated annealing, propose new configurations and accept or reject them according to their energy and target temperature, gradually biasing the search toward lower-energy configurations. Hardware-accelerated implementations, such as Fujitsu's Digital Annealer [22–24], further enhance the exploration of the energy landscape through fast, parallelized sampling mechanisms, thereby improving the chances of finding solutions with low objective.

Importantly, general combinatorial optimization problems, arising in applications, usually include constraints that restrict the search space. Yet, a standard approach to tackle such problems with QUBO solvers is to convert constraints into penalization terms weighted by a constant, commonly referred to as the Big-$M$ prescription [35–37]. The choice of this constant crucially shapes the energy landscape. If the constant $\lambda$ is not high enough, the low-energy specificity becomes problematic: the solver is forced to prioritize constraint satisfaction at all costs, returning feasible states that may be far from optimal with respect to the original objective function. Conversely, if $\lambda$ is chosen too small, the energies of infeasible configurations may be near, or even below the optimal feasible solution, causing approximate solvers to sample disproportionately from infeasible solutions that violate constraints. Existing computationally-efficient Big-$M$ prescriptions tend to substantially overestimate the required penalty [35–37], which in practice degrades solution quality [38, 39, 40]. Although recent work [39] proposes a practical strategy that delivers significantly lower (but still sufficient) Big-$M$ values, it is primarily designed for exact solvers. Current approaches do not incorporate the degree of approximation characteristic of modern heuristic methods, such as a Gibbs sampler at finite temperature. A systematic penalization strategy for approximate solvers is missing.

In this work, we introduce a novel, broadly applicable algorithm for a priori determining the penalization term for a given constrained optimization problem and a specified approximate solver. Our approach combines analytical considerations with uniform sampling over feasible configurations, to derive efficiently evaluable bounds on the solver's output distribution, from which the penalization weight $\lambda$ is calculated. We prove that for exact Gibbs solvers at arbitrary $\beta$, the algorithm yields a QUBO reformulation with a controllable, guaranteed minimum probability of sampling feasible solutions with energy at most $E_I$. The algorithm's hyperparameters allow trading off run-time against accuracy of approximating an optimal (minimum) $\lambda$.

We further show that, for large classes of constrained optimization problems, the algorithm's runtime and memory scales polynomially in the system size. We numerically demonstrate the practical applicability of our method across representative constrained optimization problems, including the Travelling Salesman Problem (TSP), the Multiway Number Partitioning Problem (MNPP), and Portfolio Optimization (PO). Besides small-scale evaluations for exact Gibbs sampling and intermediate-scale experiments with simulated annealing, we show that our method can be used to determine penalization weights for Fujitsu's Digital Annealer (version 3) on problem instances up to several thousand bits. Although the Digital Annealer is known to deviate from our underlying assumption of thermal output distributions, we find that our method qualitatively captures its behavior sufficiently well to achieve an order-of-magnitude speedup in time-to-solution compared to direct binary searches for $\lambda$ based on simpler heuristics.

## Results

### The Big-M problem for approximate combinatorial solvers

In the following, we consider the constrained optimization problem

$$\text{minimize } E^{(o)}(x) = x^T Q x \quad \text{subject to } Ax = b \quad (P)$$

given by $Q \in \mathbb{R}^{n \times n}$, $A \in \mathbb{Z}^{m \times n}$ and $b \in \mathbb{Z}^m$. This special type of linearly constrained binary optimization (LCBO) problems is able to capture complex problem formulations such as polynomially constrained problems and integer-variable problems, which can all be cast into this form using certain gadgets [39, 41–43].

A constrained problem in the form (P) can be converted to a Quadratic Unconstrained Binary Optimization (QUBO) problem by promoting the constraints $Ax = b$ to quadratic penalty terms

$$E^{(p)}(x) = (Ax - b)^2, \tag{1}$$

weighted by a penalization constant $\lambda > 0$. The new function to minimize, now a sum of the objective and penalization contributions, is

$$\text{minimize } E(x) = x^T Q x + \lambda (Ax - b)^2. \tag{P_M}$$

The minimization is now over the entire space $\{0, 1\}^n$, but infeasible bit strings will incur an energy penalty. We consider $\lambda$ to be optimal (or the minimal value guaranteeing an exact reformulation) (P_M) with an exact combinatorial solver yields an optimal solution to the original constrained problem. For an exact solver, this runtime and required computational precision depend on $\lambda$. This insight motivates choosing a minimal penalization constant $\lambda^*_{\text{exact}}$ that still ensures an exact reformulation. As shown in [39], while finding $\lambda^*_{\text{exact}}$ is in general NP-hard, good approximations to it can be found using the following strategy: given a feasible point $x_{\text{feas}}$, a lower-bound $f_{\text{inc}}^-$ on the objective, with

$$E(x_{\text{feas}}) \geq E^{(o)}(x) \quad \text{for any } x \in \{0, 1\}^n, \text{ and any constant } \delta > 0,$$

$$\lambda := f(x_{\text{feas}}) - f_{\text{inc}}^- + \delta \tag{2}$$

is an exact reformulation of (P). A feasible point and an objective lower bound can be efficiently pre-computed using, e.g. greedy algorithms and SDP relaxations, respectively. This approach and upper bound $\lambda^*_{\text{exact}} \leq \|Q\|_{\ell_1} + \delta$ [39], which improves the trivial upper bound $\lambda^*_{\text{exact}} \leq \|Q\|_{\ell_1}$ [39], which in improves the run-time of solvers.

However, approximate solvers do not necessarily return the optimal point but a solution with a low objective value approximating the true minimum. For this reason, using the strategy described in Ref. [39] will generally not ensure feasibility of the solutions for approximate solvers. One expects that choosing a large value for $\lambda$ will rapidly deteriorate the quality of the sampled bitstrings. The mean objective value increases significantly with larger $\lambda$. Thus, to ensure low objectives, it is important to choose a value of $\lambda$ close to the transition in the feasibility probability. And the 'good' regime for $\lambda$ becomes narrower as the system size increases. Notice also that a naive choice of $\lambda$, like the one in Eq. (12),

$$\lambda := f(x_{\text{feas}}) - f_{\text{inc}}^- + \delta \tag{2}$$

is an exact reformulation of (P). A feasible point and an objective lower bound can be efficiently pre-computed using, e.g. greedy algorithms and SDP relaxations, respectively. This approach and upper bound $\lambda^*_{\text{exact}} \leq \|Q\|_{\ell_1} + \delta$ [39], which improves the trivial upper bound $\lambda^*_{\text{exact}} \leq \|Q\|_{\ell_1}$ [39], which improves the run-time of solvers.

However, approximate solvers do not necessarily return the optimal point but a solution with a low objective value approximating the true minimum. For this reason, using the strategy described in Ref. [39] will generally not ensure feasibility of the solutions for approximate solvers. One expects that choosing a large value for $\lambda$ will rapidly deteriorate the quality of the sampled bitstrings. The mean objective value increases significantly with larger $\lambda$. Thus, to ensure low objectives, it is important to choose a value of $\lambda$ close to the transition in the feasibility probability. And the 'good' regime for $\lambda$ becomes narrower as the system size increases. Notice also that a naive choice of $\lambda$, like the one in Eq. (12),

overestimates the transition point by several orders of magnitude, and consequently will return solutions with an undesired, high objective value.

These observations motivate us to devise a systematic strategy for solving the big-M problem. We begin by formalizing the problem statement with the following definition. Let $\mathcal{F} = \{x \mid Ax = b\} \subset \{0, 1\}^n$ denote the subspace of feasible points.

**Definition 1.** *The QUBO problem (P_M) is an $\eta$-reformulation of the problem (P) for a solver with guaranteed energy threshold $E_I$, or short $\eta$-reformulation, if the solver's output distribution (P_{M*}) fulfills*

$$\Pr[\{x \in \mathcal{F} \mid E(x) \leq E_I\}] \geq \eta. \tag{3}$$

In other words, such a reformulation ensures observing feasible solutions of a low energy with (at least) constant probability. We consider $\lambda$ to be optimal and denote it as $\lambda^*_\eta$. While not formally established, we expect that finding $\lambda^*_\eta$ will in general as hard as solving the original optimization problem. Thus, our goal is to devise an efficient strategy that approximates $\lambda^*_\eta$ above and benchmark the quality of its solution for different instances.

### A. The Big-M strategy

An apparent challenge in defining a strategy for solving the big-M problem is that the definition of an $\eta$-reformulation depends on the actual output distribution of the solver under consideration. This is different from the exact case, which only depends on the problem instance itself. Output distributions of approximate solvers are generally not known a priori and may depend on complex ways on optimization schedules and hyperparameters. To overcome this obstacle, we consider Gibbs samplers as the prototypical proxies of an approximate solver. Indeed, a large class of approximate optimization algorithms, including Metropolis-like dynamics, simulated annealing, and more general MCMC-based solvers, are fundamentally grounded in Gibbs sampling principles, as they are designed to progressively concentrate probability mass onto low-energy configurations of an associated Gibbs distribution [14, 15, 35].

A Gibbs sampler at inverse temperature $\beta$ has output distribution $p(x) = N_\beta^{-1} e^{-\beta E(x)}$, where $N_\beta$ is a normalization constant. The degree of approximation of a Gibbs sampler as a solver is, thus, captured by a single parameter $\beta \geq 0$, tending to an exact solver for $\beta \to \infty$.

Given the output distribution of the solver, it is in principle possible (but in general inefficient) to calculate $\lambda^*_\eta$ exactly. The general idea of an efficient strategy, illustrated in Fig. 1, is to instead calculate bounds on the probability of three distinct events: observing (i) a feasible point with objective smaller or equal than $E_I$, (ii) a feasible point with objective larger than $E_I$ and (iii) an infeasible point. These three bounds can then be combined to determine $\lambda^* \geq \lambda^*_\eta$ which will be closer to the bounds are.

Evaluating the bounds requires the following weight functions (non-normalized densities) depending on the problem instance: first, we define the *penalization degeneracy* as

$$n_{\text{pen}}(v) = |\{x \in \{0, 1\}^n : E^{(p)}(x) = v\}|. \tag{4}$$

This represents the number of bitstrings with penalty function value $E^{(p)}(x) = v$ and enables control over the distribution of infeasible points. For many problems, the penalization degeneracy can be obtained analytically. We derive the expressions for MNPP, TSP and PO in Section I. Have found that in practice it is sufficient to evaluate $n_{\text{pen}}(v)$ only for $v \leq u_{\text{cut}}$, up some constant cut-off value. Alternatively, one can resort to a coarse sampling of the penalization energies of bitstrings and subsequent fit.

Second, we introduce the feasible spectral weights

$$n_\Delta(e) = |\{x \in \mathcal{F} : e \leq E^{(o)}(x) < e + \Delta\}|. \tag{5}$$

This can be approximately estimated by randomly sampling a number $N_s$ of bit-strings from a uniform distribution over the feasible subspace $\mathcal{F}$ and counting the sampled bitstrings for which the objective energy $E^{(o)}(x)$ lies within the considered range. In practice, it is sufficient to estimate $n_\Delta(e)$ only for $e \in \Lambda = \{0, \Delta, 2\Delta, \ldots, \lfloor E_{\max} - E_{\text{LB}} \rfloor / \Delta\}$, where $E_{\max}$ is the maximal energy sampled. For structured problems like TSP, MNPP or PO, the sampling is efficient, see Section C.

Steps 5 and 3 and 4 use the computed $n_\Delta(e)$ and $n_{\text{pen}}(v)$ to evaluate, up to a common factor, the probability bounds for three classes of configurations: infeasible states, feasible states with low objective energy, and feasible states with high objective energy. Finally, in step 7, the numerical root-finding of $g$ [48] determines an integer approximation to a root of [48]. Thus, we conclude that under assumptions that are often met by problems under consideration, one can choose the parameters of the algorithm such that it is efficient and guaranteed to yield the targeted reformulation. In particular, for MNPP, TSP and PO, the sampling is efficient. Step 7 is required by the algorithm in order to determine $\lambda$ and establish its theoretical guarantees, before turning to numerical validation and benchmarking in the later section.

**Algorithm 1:** $M(E^{(o)}, E^{(p)}, E_I, \beta, \eta, v_{\text{cut}}, N_s, \Delta)$

**Input:** $E^{(o)}$ (objective), $E^{(p)}$ (penalty), $E_I$ (energy threshold), $\beta$ (inverse temperature), $\eta$ (success probability), $N_s$ (sample size), $v_{\text{cut}}$ (degeneracy cut-off), and $\Delta$ (energy resolution).

1. Determine $E_{\text{LB}}$ from SDP relaxation of $\min_{x \in \{0,1\}^n} E^{(o)}(x)$

2. Estimate $n_\Delta(e + E_{\text{LB}})$ for each $e \in \Lambda$ from $N_s$ uniform samples.

3. Calculate $B^z_F := \sum_{e \in \mathcal{K}} e^{-\beta(e+\Delta)} n_\Delta(e + E_{\text{LB}})$ with $\mathcal{K} = \{0, \Delta, \ldots, \lfloor (E_I - E_{\text{LB}})/\Delta \rfloor \Delta\} \subset \Lambda$

4. Calculate $B^z_F := \sum_{e \in \bar{\mathcal{K}}} e^{-\beta e} n_\Delta(e + E_{\text{LB}})$ for $\bar{\mathcal{K}} = \Lambda \setminus \mathcal{K}$

5. Compute the penalization degeneracy $n_{\text{pen}}(v)$ for $v \in \{1, \ldots, v_{\text{cut}}\}$ Set $B_F(M) := \sum_{v=1}^{v_{\text{cut}}} e^{-\beta M v} n_{\text{pen}}(v)$

6. Determine $M^*$ as the root of $g(M)$.

7. Return $\max(0, M^*)$ or $\{\}$ if no roots were found.

Algorithm 1 combines these estimates to compute the bounds $B^z_F$, $B^z_F$, and $B_F$ that bound the probabilities of observing feasible points with a low objective value, feasible points with a high objective value, and infeasible points, respectively. From $B^z_F$, $B^z_F$, and $B_F$ we obtain an estimate $M^*$ for $M$ in the last step. The correctness of the algorithm in the limit of infinite samples is established by the following theorem.

**Theorem 2.** *In the limit $N_s \to \infty$ and for $v_{\text{cut}} = \max_x E^{(p)}(x)$ the following holds: If Algorithm 1 returns $M^* \neq \{\}$, then $(P_M)$ with $M = M^*$ is an $\eta$-reformulation (P_{M*}) with $M = M^*$ is an $\eta$-reformulation of $(P_M)$ with guaranteed energy threshold $E_I$ for a Gibbs sampler at inverse temperature $\beta$.*

**Proof.** The proof first establishes that the three bounds evaluated in the algorithm actually bound the corresponding events, and finally that they are combined to determine a root of $M$. By the theorem's assumption, $x \in \{0, 1\}^n$ is sampled according to the Gibbs distribution $p_\beta(x) = N_\beta^{-1} e^{-\beta E(x)}$ with normalization $N_\beta = \sum_{x \in \{0, 1\}^n} e^{-\beta E(x)}$. By $\bar{\mathcal{F}}$ we denote the complement of $\mathcal{F}$. We consider the different values $v \in \mathcal{Z}$, the penalty term $E^{(p)}$ can take and decompose $\bar{\mathcal{F}}$ into the preimages of $v \neq 0$ as $\bar{\mathcal{F}} = \bigcup_{v=1}^\infty (E^{(p)})^{-1}(\{v\})$. This observation allows us to use the lower bound $E_{\text{LB}} \leq E^{(o)}(x)$ on the unconstrained objective function for all $x$. Such a bound can be efficiently computed using, e.g. greedy algorithms and SDP relaxations, respectively. This approach and upper bound $\lambda^*_{\text{exact}} \leq \|Q\|_{\ell_1}$ [39], which improves the trivial upper bound $\lambda^*_{\text{exact}} \leq \|Q\|_{\ell_1}$ [39], which improves the run-time of solvers.

serving an infeasible solution as

$$\Pr[\bar{\mathcal{F}}] = \sum_{x \in \bar{\mathcal{F}}} p_\beta(x) = N_\beta \sum_{v=1}^\infty \sum_{x \in (E^{(p)})^{-1}(\{v\})} e^{-\beta(E^{(o)}(x)+M(Ax-b)^2)}$$

$$\leq N_\beta e^{-\beta E_{\text{LB}}} \sum_{v=1}^\infty e^{-\beta M v} \sum_{x \in (E^{(p)})^{-1}(\{v\})} 1 = N_\beta e^{-\beta E_{\text{LB}}} \sum_{v=1}^\infty e^{-\beta M v} n_{\text{pen}}(v) - c B_F(M),$$

where we defined the positive constant $c = N_\beta e^{-\beta E_{\text{LB}}} > 0$ and $B_F(M) \text{ from step 5}$.

Next, we show that $B^z_F$ from step 3 is a lower bound on the probability of observing feasible points with low objective. In the limit $M \to \infty$, our estimate for $\lambda_\eta$ is exact. We divide the relevant energy interval in bins of size $\Delta$, with steps $\mathcal{K} = \{0, \Delta, \ldots, \lfloor (E_I - E_{\text{LB}})/\Delta \rfloor \Delta\}$. We denote the set of feasible states in these bins by $b(e) = \{x \in \mathcal{F} : E^{(o)}(x) \in [e, e+\Delta)\}$, with cardinality $|b(e)| = n_\Delta(e + E_{\text{LB}})$. Since $E^{(p)}(x) = 0$ for any $x \in \mathcal{F}$, we can write the probability from Eq. (3) as

$$p := \Pr[\mathcal{F} \cap \{E^{(o)} \leq E_I\}]] = N_\beta \sum_{e \in \mathcal{K}} e^{-\beta E^{(o)}(x)} - c B^z_F(M),$$

Similarly, for the feasible events with a high objective value, defining $B^z_F$ as in line 4, we ensure that

$$\Pr[\mathcal{F} \cap \{E^{(o)} > E_I\}] = N_\beta \sum_{e \in \mathcal{K}} e^{-\beta E^{(o)}(x)} \leq N_\beta e^{-\beta E_{\text{LB}}} \sum_{e \in \mathcal{K}} e^{-\beta c} n_\Delta(e + E_{\text{LB}}) = c B^z_F.$$

The events are mutually exclusive and complete. Hence,

$$\Pr[\bar{\mathcal{F}}] + \Pr[\mathcal{F} \cap \{E^{(o)} > E_I\}] + \Pr[\mathcal{F} \cap \{E^{(o)} \leq E_I\}] = 1,$$

which in terms of the bounds (6) and (8) implies that

$$c(B_F(M) + B^z_F) \geq 1 - \Pr[\mathcal{F} \cap \{E^{(o)} \leq E_I\}] = 1 - p,$$

which in terms of the bounds (6) and (8) implies that

$$c(B_F(M) + B^z_F - \frac{1-\eta}{η} B^z_F) = 1 - p, \tag{10}$$

If step 6 yields $\eta$ that has a positive root $M^*$, then

$$0 = B_F(M^*) + B^z_F - \frac{1-\eta}{\eta} B^z_F \tag{11}$$

$$\geq c^{-1}\left(1 - p - \frac{1-\eta}{\eta} p\right) = c^{-1}\left(1 - \frac{p}{\eta}\right),$$

Finally, if $\eta$ has a negative root, then $p \geq \eta$ already holds for $M^* = 0$.

A few comments on the algorithm are in order:

(i) As we can see in Section E, if no termination with guaranteed threshold $E_I$ exist, the algorithm returns $\{\}$. In this case, we can choose any permissible $\eta < \eta_{\text{crit}}$ and run the algorithm again, while ensuring the existence of a solution.

(ii) One can set $E_I = \infty$ (and truncate $\mathcal{K}$ at the last energy sampled in step 2) to not require any guarantee on the objective of the solutions. In this regime Eq. (3) becomes feasibility-only sampling.

(iii) We numerically observe that in our problem instances, the penalization degeneracy does not grow exponentially, see Section I. This allows us to use a small value for $v_{\text{cut}}$, without introducing a substantial error.

(iv) One can set $E_I = \infty$ (and truncate $\mathcal{K}$ at the last energy sampled in step 2) to not require any guarantee on the objective of the solutions. In this regime Eq. (3) becomes feasibility-only sampling.

Let us now analyze the time and memory complexity of the algorithm in more detail. In particular, we establish in the following that the algorithm is efficient for problem instances with polynomially bounded entries for $Q$, $A$, and $b$ and the problem specification [B] all can efficiently uniform sampling from the feasible subspace and (iii) efficient evaluation of $n_{\text{pen}}(v)$.

To control the algorithm's complexity, we impose assumptions on the magnitude of the objective function $E^{(o)}$ and the penalization term $E^{(p)}$. Note that if $Q_{ij}, A_i, b_i \in O(1)$ for all $i, j$, then $E^{(o)}(x) = x^T Q x \leq \|Q\|_{\infty} \leq O(n^2)$ for all $x \in \{0, 1\}^n$ and the penalization term $E^{(p)}(x) = x^T A x + 2x^T A b + b^T b$ with $m$ constraints scales as $O(\text{poly}(n, m))$.

The maximum value $v_{\max} = \max_x E^{(p)}(x)$ will thus scale like $mn^2$ for the benchmarked problems and other bounded-entries similar problems, or will be in $O(\text{poly}(m, n))$ in general.

Let us discuss each step of Algorithm 1:

The SDP in Step 1 generally takes $O(\kappa^{\prime})$ time and $O(n^4)$ memory complexity [46]. Considerable speed-ups can potentially be achieved using sketching techniques [47].

For Step 2 to be efficient, we need to choose $N_s$ to at most polynomially in $m, n$. This will, in turn, introduce a statistical error in the estimation of $n_\Delta$ and $B^z_F$ and $B^z_F$. If we choose the parameter $\Delta$ sufficiently large, i.e. the discretization sufficiently coarse, the statistical error is controlled. More precisely, extending Theorem 2, we show in Section A that with probability $1 - \delta$ a $(\epsilon, \delta)$-reformulation is provided that $N_s \geq 2/(\epsilon^2 \delta^2)$ and $\Delta = \Omega(\text{poly}(n, m) + \beta^{-1} \ln)$.

We refer to the appendix for more details. Obtaining a single uniform sample from the feasible subspace is efficient for many problems. In particular, for TSP, MNPP and PO it takes $O(n)$, $O(n)$ and $O(n^2)$ time, respectively (O(n_c^2), O(N + P)$ and $O(n^2 \text{ time}, respectively (O(n_c^2), O(N+P)$ and $O(n^2 \text{ time}, respectively). Let us discuss each step of Algorithm 1:

The SDP in Step 1 generally takes $O(\kappa^{\prime})$ time and $O(n^4)$ memory complexity [46]. Considerable speed-ups can potentially be achieved using sketching techniques [47].

For Step 2 to be efficient, we need to choose $N_s$ to at most polynomially in $m, n$. This will, in turn, introduce a statistical error in the estimation of $n_\Delta$ and $B^z_F$ and $B^z_F$. If we choose the parameter $\Delta$ sufficiently large, i.e. the discretization sufficiently coarse, the statistical error is controlled. More precisely, extending Theorem 2, we show in Section A that with probability $1 - \delta$ a $(\epsilon, \delta)$-reformulation is provided that $N_s \geq 2/(\epsilon^2 \delta^2)$ and $\Delta = \Omega(\text{poly}(n, m) + \beta^{-1} \ln)$.

We refer to the appendix for more details. Obtaining a single uniform sample from the feasible subspace is efficient for many problems. In particular, for TSP, MNPP and PO it takes $O(n)$, $O(n)$ and $O(n^2)$ time, respectively. In Step 3 and 4 are both efficient under the same assumptions in Step 5.

Step 5 is efficient under the same assumption as Step 5.

Step 7 requires constant evaluation of $g$ (Step 5) to determine an integer approximation to a root of [48]. Thus, we conclude that under assumptions that are often met by problems under consideration, one can choose the parameters of the algorithm such that it is efficient and guaranteed to yield the targeted reformulation. In particular, for MNPP, TSP and PO, the sampling is efficient.

### C. Validation and numerical benchmarks

We benchmark the proposed strategy on three classes of constrained problems: Travelling Salesman Problem (TSP), Multiway Number Partitioning Problem (MNPP) and Portfolio Optimization (PO). Complete formulations of these optimization problems are given in Section B. The problems capture distinct structures of sets of feasible points. As solvers we use an ideal Gibbs sampler, a simulated annealing algorithm, and the Digital Annealer. All instances are tested following the same scheme: Algorithm 1 is used to determine the penalization constant $\lambda$ for $\eta \in \{0.25, 0.5, 0.75\}$ and for three different temperatures (or temperatures) desired for the DA, operating at a single, automatically-selected temperature). We choose $E_I$ such that it is not impeding the success probability—i.e., so that $\eta_{\text{eff}} does not become small and under the tests limit the feasible-solutions. From multiple runs of the solvers when the effective success probability $\eta_{\text{eff}}$, i.e. the fraction of observed feasible solutions with energy smaller than $E_I$, per problem class and system size. In Fig. 3 we display the effective success probability $\eta_{\text{eff}}$ of an ideal Gibbs sampler and different choices of $E_I$, respectively. We observe $\eta_{\text{eff}}$ is larger than $\eta$ showing that the I. I used admissibly high reference lines at these values. Marker shapes indicate sampler temperature $T = \beta^{-1}$. For SA, temperatures are obtained by rescaling Digitial Annealer schedules as $T = \phi T_{\text{DA}}$ with $\phi \in [0.1, 10]$. For PO, schedules are approximated using instances of the same size from other benchmarks. Solid lines and markers show averages over 100 (ideal Gibbs sampler) or (SA) instances, with shaded standard deviation. For TSP and benchmark TSP, only dense instance per system size. Per instance, $10^3$ (ideal Gibbs) or 128 (SA) samples are drawn. PO uses $10^3$. We generally observe that $\eta_{\text{eff}}$ is larger than $\eta$ showing that I. I used admissibly high reference lines at these values. Such instances are indicated in the optimality-focused MNPP panels (bottom left) by short horizontal bars marking the reduced speedup achieved by $\eta_{\text{eff}}$.

## Figure 1

The big-$M$ problem for approximate solvers is to ensure by the choice of a penalization weight $M$ that an approximate solver samples feasible solutions with probability at least $\eta$ given a QUBO reformulation of a constrained optimization problem. Optionally, one can additionally enforce the solutions to be below a certain energy threshold $E_I$. We assume that the output distribution of a solver is qualitatively approximated by a Gibbs distribution at inverse temperature $\beta$. Our method to determine $M$, summarized to the left in terms of the energy at the probability pct of sampling a solution with energy $e$ conditioned on the solution being feasible or infeasible. The density of infeasible solutions is naturally grouped into families of equal constraint-violation value. Our method to determine $M$ summarized, calculates (1.) a lower bound $B^z_F$ and (2.) an upper bound $B^z_F$ on the probability of sampling feasible points with objectives below and exceeding $E_I$, respectively. Together with (3.) an upper bound $B_F(M)$ on the probability of infeasible families contributions this work. We prove that this method is efficient for large classes of problems, prove theoretical guarantees on its performance, and demonstrate it is practical applicability numerically.

## Figure 2

Proportion of feasible solutions observed $\eta_{\text{eff}}$ (top) and mean objective energy $E^{(o)}$ of sampled feasible solutions (bottom) on the DA solver (version 3) for different benchmarked problems (from left to right: Multiway Number Partitioning Problem (MNPP), Travelling Salesman Problem (TSP) instances with cities placed on a circle) with different values of $\lambda$ and problem size. The grey areas lack clear energy points because only infeasible bitstrings were sampled for those values of $\lambda$. We note a degradation in the quality of the sampled bitstrings. The mean of the energy $E^{(o)}$ of the output of the sampler increases for larger values of $\lambda$, beyond a seemingly sweet spot that is located around the transition. For reference, the $M$ values suggested by the trivial choice in Eq. (12) are around $10^9$ for MNPP, $10^6$ for benchmarks TSP and $10^{10}$ for circle TSP. Such extreme overshooting implies that the mean energy sampled by the solver would be far from the desired minimum, undermining the optimization's effectiveness.

## Figure 3

Effective success probability $\eta_{\text{eff}}$ of an ideal Gibbs sampler (top rows) and simulated annealing (SA) (bottom rows) for sampling feasible solutions using a QUBO reformulation with penalization weight $\lambda^*$ calculated using Algorithm 1. Different colors correspond to different benchmarked constrained optimization problems. From left to right: Multiway Number Partitioning Problem (MNPP), Travelling Salesman Problem (TSP) instances from library [40], and TSP with cities placed on a circle) with different values of $\lambda$ and problem size. The grey areas lack energy points because only infeasible bitstrings were sampled for those values of $\lambda$. We note a degradation in the quality of the sampled bitstrings. The mean of the energy $E^{(o)}$ of the output of the sampler increases for larger values of $\lambda$, beyond a seemingly sweet spot that is located around the transition. For reference, the $M$ values suggested by the trivial choice in Eq. (12) are around $10^9$ for MNPP, $10^6$ for benchmarks TSP and $10^{10}$ for circle TSP. Such extreme overshooting implies that the mean energy sampled by the solver would be far from the desired minimum, undermining the optimization's effectiveness.

## Discussion

We introduced an efficient algorithm to determine the penalization weight in unconstrained reformulations of constrained optimization problems, specifically tailored for approximate solvers that are qualitatively similar to Gibbs samplers. More precisely, given a Gibbs sampler at an arbitrary inverse temperature, our algorithm determines a penalization weight such that the solver outputs feasible solutions with objective value below a threshold with a controllable, guaranteed minimum probability. We also demonstrate the practical applicability of our technique beyond exact Gibbs sampling in numerically tests with a simulated annealing algorithm and Fujitsu's Digital Annealer (version 3), for different constrained problem classes and system sizes up to 4098 bits. Although the Digital Annealer is known to deviate from our underlying assumption of thermal output distributions, we show that our method qualitatively captures its behavior sufficiently well to achieve an order-of-magnitude speedup in time to solution on the solver by several orders of magnitude compared to strategies based on binary search for a penalization weight.

Our algorithm for addressing the big-M problem improves upon state-of-the-art general heuristics for penalization constants. It provides a tool to precisely set the penalization constant so as to control the probability of success, using knowledge of the problem structure and the solver's statistical behavior. To this end, we trade resources in the pre-processing for potentially crucial reductions in the solver's runtime. Such practical strategy that delivers significantly lower (but still sufficient) Big-$M$ values is primarily designed for exact solvers. Current approaches do not incorporate the degree of approximation characteristic of modern heuristic methods, such as a Gibbs sampler at finite temperature. A systematic penalization strategy for approximate solvers is missing.

## Acknowledgements

M. Krispin and M. Kliesch are funded by the Hamburg Quantum Computing project, which is co-financed by the ERDF of the European Union and the Funds of the Hamburg Ministry of Science, Research, Equalities and Districts (BWFGB); and by the Fujitsu Germany GmbH and Daiquiri as part of the endowed professorship "Quantum Inspired and Quantum Optimization."

## References

[1] A. Abbas, A. Ambainis, B. Augustino, A. Birtschi, H. Buhrman, C. Coffrin, G. Cortiana, V. Dunjko, D. J. Egger, B. G. Eimegreen, N. Franco, E. Fuchs, D. C. Goncalves, S. Gribling, S. Gupta, S. Hadfield, R. Heese, G. Kircher, T. Kleinert, T. Koch, G. Korniss, S. Lenl, J. Miracel, N. Mirtov, O. Mzenda, C. Mesia, N. Mohseni, G. Nannicini, C. O'Meara, E. P. Tapia, S. Poletto, M. Posski, P. Rebentrost, E. Slain, B. C. Symons, S. Tornow, V. Valls, S. Woerner, M. L. Wulf-Bauswell, J. Yard, S. Yarkoni, Z. Zehlein, S. Zollz, and Z. Zoudi, Challenges and opportunities in quantum optimization, Nature Reviews Physics 2(12), 227 (January 2021).

[2] M. Johnson, M. H. S. Amin, S. Gildert, T. Lanting, F. Hamze, N. Dickson, R. E Harris, A. E Berkley, J. Johansson, P. Bunyk, E. M. Chapple, C. Enderud, S. P. J. Hilton, K. Karimi, E. Ladizinsky, N. Ladizinsky, T. Oh, I. Perminov, C. Rich, M. C. Thom, E. Tolkacheva, C. J. S. Truncik, S. Uchaikin, J. Wang, B. Wilson, G. Rose, Quantum annealing with manufactured spins, Nature 473, 194 (2011).

[3] E. J. Crosson and D. A. Lidar, Prospects for quantum enhancement with quantum annealing, Nat. Rev. Physics 3, 466 (2021), arXiv:2008.0931 [quant-ph].

[4] E. Farhi, J. Goldstone, and S. Gutmann, A quantum approximate optimization algorithm, arXiv:1411.4028 [quant-ph] (2014).

[5] T. Inagaki, Y. Haribara, K. Igarashi, T. Sonobe, S. Tamate, T. Honjo, A. Marandi, P. L. McMahon, T. Umeki, K. Enbutsu, O. Tadanaga, H. Takenouchi, K. Aihara, K. Ichi Kawarabayashi, A coherent Ising machine for 2000-node optimization problems, Science 354, 603 (2016).

[6] T. Honjo, T. Sonobe, K. Inaba, T. Inagaki, T. Ikuta, Y. Yamada, T. Kazama, K. Enbutsu, T. Umeki, and H. Takesue, 100,000-spin coherent Ising machine, Science Advances 7, eabe7953 (2021).

[7] M. Sao, H. Watanabe, Y. Musha, and A. Utsunomiya, Application of digital annealer for faster combinatorial optimization, Fujitsu Scientific and Technical Journal 55, 45 (2019).

[8] S. Hideki, Fukutoshi and N. Kazuyoshi, E. Noda, and A. Sakai, Mathematical aspects of the Digital Annealer's simulated annealing algorithm, arXiv:2303.08902 [math.OC] (2023).

[9] T. Okuyama, T. Sonobe, K. Kawarabayashi, and M. Yamaoka, Binary optimization by nonautonomous adiabatic scheduling, Phys. Rev. E 100, 012111 (2019).

[10] H. Goto, K. Tatsumura, and A. R. Dixon, Combinatorial optimization by simulating adiabatic bifurcations in nonlinear Hamiltonian systems, Science Advances 5, eaav2372 (2019).

[11] K. Tatsumura, M. Yamasaki, and H. Goto, Scaling out Ising machines as a multi-chip architecture for simulated bifurcations, Nature Electronics 4, 208 (2021).

[12] G. Rosenberger, S. K. Hao, E. Glover, F. Lewis, M. Lewis, Z. Lu, H. Wang, and C. Wang, The unconstrained binary quadratic programming problem: a survey, Journal of Combinatorial Optimization 28, 58 (2014).

[13] D. Ratke, List of qubo formulations, https://blog.xa0.de/post/List-of-QUBO-formulations/ (2021), blog post, accessed 2026-03-02.

[14] S. Kirkpatrick, C. D. Gelatt, and M. P. Vecchi, Optimization by simulated annealing, Science 220, 671 (1983).

[15] S. Geman and D. Geman, Stochastic relaxation, Gibbs distributions, and the Bayesian analysis of images, IEEE Transactions on Pattern Analysis and Machine Intelligence PAMI, 721 (1984).

[16] R. J. Glauber, Time-dependent statistics of the Ising model, Journal of Mathematical Physics 4, 294 (1963).

[17] W. K. Hastings, Monte carlo sampling methods using markov chains and their applications, Biometrika 57, 97 (1970).

[18] K. Husidana and K. Nemoto, Exchange monte carlo method and application to spin glass simulations, Journal of the Physical Society of Japan 69, 3097 (1997).

[19] J. Mossel and A. Sly, Exact thresholds for Ising--Gibbs samplers on general graphs, The Annals of Probability 41, 10.1214/11-aop737 (2013).

[20] N. Siddique and H. Adeli, Simulated annealing and engineering optimization, International Journal on Artificial Intelligence and Engineering 25, 1630031 (2016).

[21] M. Karabin and S. J. Stuart, Simulated annealing with adaptive cooling cooling rates (2020), arXiv:2012.06124 [physics.comp-ph].

[22] S. Matsubara, H. Tamura, M. Takatsu, D. Yoo, B. Waidhalata, H. Yamada, S. Tatsuishi, S. Tsukusu, Y. Watanabe, K. Takemoto, and A. Sheikhelislami, Hamiltonian approach with parity-preserving digital gates, in Complex, Intelligent, and Software Intensive Systems, edited by L. Barolli and Q. Terzo (Springer International Publishing, Cham, 2018) pp. 432-438.

[23] H. M. Wadawasooriya, Y. Araki, and M. Hariyama, Accelerator architecture for simulated quantum annealing based on speculative and implementation using opencl, 2018 International Symposium on Intelligent Signal Processing and Communication Systems (ISPACS) (2018).

[24] S. Matsubara, M. Takahasu, T. Miyazawa, T. Shibasaki, Y. Watanabe, K. Takemoto, and H. Tamura, Digital annealer for high-speed combinatorial optimization problems and its applications, in 2020 25th Asia and South Pacific Design Automation Conference (ASP-DAC) (2020) pp. 667-672.

[25] T. Kadowaki and H. Nishimori, Quantum annealing in the transverse-ising model, Physical Review E 58, 5355 (1998).

[26] E. Farhi, J. Goldstone, S. Gutmann, J. Japan, A. Lundgren, D. Preda, and A. R. Dixon, Combinatorial optimization by simulating adiabatic bifurcations in nonlinear Hamiltonian systems, Science 292, 472 (2001).

[27] A. Rajak, S. Tomar, and S. Kumar, Quantum annealing: An overview, Philosophical Transactions of the Royal Society A 380, 20210417 (2022).

[28] H-. Maryupo-Beagle and J. Lidar, Scaling advantage in approximate optimization with quantum annealing, Physical Review Letters 134, 160601 (2025).

[29] E. Farhi, J. Goldstone, and S. Gutmann, A quantum approximate optimization algorithm (2014), arXiv:1411.4028 [quant-ph].

[30] K. Bieko, D. Brand, A. Ceschini, C-H. Chou, R-H. Li, K. Pandya, and A. Summer, A review on quantum approximate optimization algorithm and its variants, Physics Reports 1068, 1 (2024).

[31] L. Cheng, Y-Q. Chen, S-X. Zhang, and S. Zhang, Quantum machine learning algorithm with observables, Communications Physics 7, 83 (2024).

[32] D. Amosy, T. Danzig, O. Lev, E. Tarsi, and I. Reuven, Iteration-free quantum approximate optimization algorithm, arXiv:2305.07336 (2023).

[33] N. Shapeev, N. Merric, C. K. Long, and B. M. Arvidsson-Shukur, Dynamic adaptive quantum approximate optimization algorithm for shallow, noise-resilient quantum circuits, Physical Review Research 5, 2 (2024).

[34] W. Gilks, S. Richardson, and D. Spiegelhalter, eds., Markov Chain Monte Carlo in Practice (Chapman and Hall/CRC, London, 1994).

[35] S. Harwood, C. Gambella, D. Trenev, A. Simonetto, D. Bernal, and D. Groechenig, Formulating and solving routing problems on quantum computers, IEEE Transactions on Quantum Engineering 2, 1 (2021).

[36] I. D. Leonidas, A. Dakakis, B. Tan, and D. G. Angelakis, Qubit efficient quantum annealing for the isotropic problem on noisy intermediate-scale quantum processors, Advanced Quantum Technologies 3 (2024).

[37] Qubit documentation, Converters for quadratic programs - lineareqality (2022).

[38] U. Azad, B. Behera, E. A. Ahmed, P. K. Panigrahi, and A. Farole, Solving ranking problem using quantum approximate optimization algorithm, IEEE Transactions on Intelligent Transportation Systems 24, 7564 (2023).

[39] E. Alessandrom, S. Ramos-Calderer, I. Roth, E. Traversi, L. Aolita, et al., Alleviating the quantum big-m problem, arXiv Quantum Information 10, 1038/41534-025-01067-0 (2025).

[40] G. Reinelt, Tsplib95 – a library of sample instances for the travelling salesman problem and related problems, (2022).

## Appendix A: Extended theoretical guarantee for the algorithm

Theorem 2 establishes that the proposed algorithm returns a value $M^*$ that ensures an $\eta$-reformulation, Eq. (3) using infinite samples $N_s \to \infty$. We here establish the empirical estimator $\tilde{n}_\Delta(e) = |\{x \in S : e \leq E^{(o)}(x) < e + \Delta\}| \cdot \frac{|\mathcal{F}|}{n_{\text{pen}}(0)}$ denotes the number of feasible points. For structured problems, $|\mathcal{F}|$ can often be computed analytically (see Section I). We begin by quantifying the statistical error incurred in replacing $n_\Delta$ with $\tilde{n}_\Delta$ in the following lemma. We then establish $N_s = O(\epsilon^{-2})$ is sufficient to guarantee an $(\epsilon, \delta)$-reformulation provided that $N_s \geq 2/(\epsilon^2 \delta^2)$ and $\Delta = \Omega(\text{poly}(n, m) + \beta^{-1} \ln)$.

**Lemma 3.** *Let $\tilde{n}_\Delta(\epsilon)$ be the estimation of $n_\Delta(\epsilon)$ from $N_s$ uniform samples from $|\mathcal{F}|$. Then*

$$\mathbb{E}\left[\left\|\tilde{n}_\Delta - n_\Delta\right\|_{\ell_2}\right] \leq \frac{|\mathcal{F}|}{\sqrt{N_s}}$$

**Proof.** The feasible spectral weight $n_\Delta(e)$ is estimated by drawing $N_s$ i.i.d. samples $x$ uniformly at random from $\mathcal{F}$ and counting the sampled bitstrings for which the objective energy $E^{(o)}(x)$ lies within the considered range. In practice, it is sufficient to estimate $n_\Delta(e)$ only for $e \in \Lambda = \{0, \Delta, 2\Delta, \ldots, \lfloor E_{\max} - E_{\text{LB}} \rfloor / \Delta\}$, where $E_{\max}$ is the maximal energy sampled. For structured problems like TSP, MNPP or PO, the sampling is efficient, see Section C. The vector-valued random variable $X$ counting the frequencies is multinomially distributed with probability $p_\Delta(e) = n_\Delta(e) / |\mathcal{F}|$. The empirical estimator $\hat{p}_\Delta = X / N_s$ has expected error

$$\mathbb{E}\left[\left\|\hat{p}_\Delta - p_\Delta\right\|_{\ell_2}^2\right] = \frac{1}{N_s^2} \mathbb{E}\left[\|X - \mathbb{E}[X]\|_{\ell_2}^2\right] = \frac{1}{N_s^2} \sum_{k} \text{Var}[X_k] = \frac{1 - \left\|p_\Delta\right\|_{\ell_2}^2}{N_s} \leq \frac{1}{N_s},$$

where $X_k$ is the $k$–th component of $X$, counting the frequency of the $k$–th bin. Hence, by Jensen's inequality $\mathbb{E}\left[\left\|\hat{p}_\Delta - p_\Delta\right\|_{\ell_2}\right] \leq 1 / \sqrt{N_s}$. By definition, the error on $n_\Delta$ is larger by a factor of $|\mathcal{F}|$.

Let $\tilde{B}^z_F$ be the estimate of $B^z_F$ using $\tilde{n}_\Delta$ instead of $n_\Delta$. We can control the error as

$$\left|\tilde{B}^z_F - B^z_F\right| \leq \sum_{e \in \mathcal{K}} e^{-\beta(e+\Delta)} \left|\tilde{n}_\Delta(e + E_{\text{LB}}) - n_\Delta(e + E_{\text{LB}})\right|$$

$$\leq e^{-\beta \Delta} \sqrt{\frac{2|\mathcal{F}|^2}{\mathcal{N}_s}} \delta^{-1}$$

where we have used Cauchy-Schwarz's inequality, the fact that $\left\|\tilde{n}_\Delta - n_\Delta\right\|_{\ell_2} \leq \mathbb{E}\left[\left\|\tilde{n}_\Delta - n_\Delta\right\|_{\ell_2}\right] / \delta$ with probability at least $(1 - \delta)$ from Markov inequality, and

$$\sum_{e \in \mathcal{K}} e^{-2\beta e} = \sum_{k=0}^{\lfloor (E_I-E_{\text{LB}})/\Delta \rfloor} e^{-2k\beta\Delta} = \frac{1 - e^{-2\beta\Delta \lfloor (E_I-E_{\text{LB}})/\Delta \rfloor}}{1 - e^{-2\beta\Delta}} \leq 2,$$

for $\beta\Delta \geq \log(2) / 2$. Recalling that we defined $c = N_\beta e^{-\beta E_{\text{LB}}} > 0$, for $\beta\Delta \geq \log(|\mathcal{F}|) + \log(c) \geq \log(2) / 2$, we, thus, have

$$\left|\tilde{B}^z_F - B^z_F\right| \leq \sqrt{\frac{2}{N_s}} (c\delta)^{-1}.$$

Analogously, also for the bound on high-energy feasible states we have:

$$\left|\tilde{B}^z_F - B^z_F\right| \leq \sqrt{\frac{2}{N_s}} (c\delta)^{-1}.$$

Thus, we arrive at the following theorem.

**Theorem 4.** *Let $\beta\Delta \geq \log(|\mathcal{F}|) + \log(c) \geq \log(2) / 2$. For $\epsilon > 0$ and $\delta \geq 0$, suppose that*

$$N_s \geq \frac{2}{c^2\delta^2}$$

then, with probability at least $1 - \delta$, we have $p := \Pr[\{x \in \mathcal{F} : E(x) \leq E_I\}] \geq \eta - \epsilon$.

## Appendix B: Benchmarking problems

In the present section, we discuss the benchmarked optimization problems and their QUBO formulations.

### 1. MNPP

The Number Partitioning Problem (NPP), an NP-hard combinatorial problem, aims at partitioning a set of numbers into two subsets so evenly as possible. The Multiway Number Partitioning Problem (MNPP) is a generalization of this, with multiple subsets to partition the elements into. Its applications range from distributed networking and computing, resource allocation and logistics, to gerrymandering and investment portfolio diversification. More formally, given a set $S$ of $N$ positive numbers $S = \{c_1, \ldots, c_N\}$, the goal is to partition $S$ into $P$ disjoint subsets $R_1, \ldots, R_P$, such that the sums of values in each subset are as close to each other as possible. Thus problem can be stated as follows: can a set of $N$ assets with values $c_1, \ldots, c_N$ fairly be distributed between P parties? To model the problem in an optimization context [62], we define the $NP$ binary decision variables $\{x_{i,p} | i \in \{1,\ldots,N\}, p \in \{1,\ldots,P\} \}$ {$\{0, 1\}^{1}$, assigning each element $c_i$ in $S$ to a subset $R_p$, defined so that

$$x_{i,p} = \begin{cases} 1 & \text{if } c_i \in R_p \\ 0 & \text{otherwise} \end{cases}$$

The constraints will encode the fact that each element can only be assigned to one subset, that is, the decision matrix $[x]_{i,p}$ is a right-stochastic matrix: $\sum_{p=1}^P x_{i,p} = 1 \forall i$. The objective function can be stated in different ways [63]; we will consider

$$E^{(o)}(x) = \sum_{p=1}^P \left(\sum_{i=1}^N c_i x_{i,p} - \frac{1}{P} \sum_{i=1}^N c_i\right)^2$$

that sums the squared errors of the subsets sums with respect to a perfectly even distribution of $\frac{1}{P} \sum_{i=1}^N c_i$ per subset (scaled variance of the subset sums).

The QUBO model can be formulated in the following way:

$$\min_{x \in \{0,1\}^{NP}} E^{(o)}(x) + \lambda \sum_{i=1}^N \left(1 - \sum_{p=1}^P x_{i,p}\right)^2,$$

In the benchmarks considered in this work, the numbers $c_i$ to be partitioned were randomly generated from a uniform distribution over the interval $[0, 1]$. For small-scale tests involving the Gibbs sampler, the number of partitions was fixed at $P = 3$, while only the system size $N$ was increased. Conversely, for the larger-scale tests with the SA and DA solvers, both $N$ and $P$ were increased with system size, maintaining the relation $N = sP$. This choice ensured that the average number of integers per partition remained constant as the system grew, preventing the problem from becoming artificially easier and avoiding an overabundance of optimal solutions [64].

### 2. TSP

The Travelling Salesman Problem is a cornerstone of optimization problems, it is an NP-hard problem highly relevant both in theoretical computer science and for practical applications, such as logistics, circuit design, telecommunications [65]. Given a connected graph $G = (V, E)$ with $n_v = |V|$ vertices, with edge $e_{i,j}$ represents the cost of traveling from node $i$ to node $j$, the goal is to find the cheapest Hamiltonian cycle, i.e. a path that visits all the nodes in the graph, minimizing the overall total travel cost. The combinatorial problem can be encoded via the $n_v^2$ binary decision variables $\{x_{t,i} | t, i = 1, \ldots, n_v\}$ [62], defined so that

$$x_{t,i} = \begin{cases} 1 & \text{if city } i \text{ is visited at time step } t \\ 0 & \text{otherwise} \end{cases}$$

The constraints of the optimization problem enforce the decision matrix $[x]_{t,i}$ to be a permutation matrix, that is, $\sum_{t=1}^{n_v} x_{t,i} = 1 \forall i$ and $\sum_{i=1}^{n_v} x_{t,i} = 1 \forall t$. The objective function to minimize incorporates the cost (given by the sum of the edge weights) of a path represented by a particular realization of the decision matrix [62].

$$E^{(o)}(x) = \sum_{t=1}^{n_v} \sum_{i,j=1}^{n_v} c_{i,j} x_{t,i} x_{t+1,j}.$$

The QUBO model is then formulated in the following way:

$$\min_{x \in \{0,1\}^{n_v^2}} \left[\sum_{t=1}^{n_v} \left(1 - \sum_{i=1}^{n_v} x_{t,i}\right)^2 + \sum_{i=1}^{n_v} \left(1 - \sum_{t=1}^{n_v} x_{t,i}\right)^2 \right].$$

In the present work, multiple sets of TSP benchmarks are used or generated. The first, referred to as the circle TSP in the plots, consists of $n_v$ nodes deterministically positioned at equal distances along a circle of radius $10^6$. The second set, called the random TSP, contains instances where nodes are randomly placed within a square of side length $2 \times 10^6$, while the third set, named the benchmark TSP, includes instances obtained from the standard benchmark library [40].

### 3. PO

For Portfolio Optimization we use the well-known Markowitz model [66–68], i.e. the problem of selecting a set of assets maximizing returns while minimizing risk. The problem specification requires a vector $\mu$ of expected returns of a set of $N$ assets, their covariance matrix $\Sigma$, a risk aversion factor $\gamma > 0$, and a partition number $w$ defining the portfolio discretization. Denoting by the units of asset $i$ in the portfolio, the units of asset $i$ in the portfolio reads

$$\text{minimize } - \mu^T x + \gamma x^T \Sigma x \quad \text{subject to } \sum_{i=1}^N x_i = 2^w - 1.$$

The constraint forces the budget to be totally invested. The QUBO reduction requires mapping each integer decision variable into $w$ binary variables. We generate problem instances from historic financial data on S&P 500 stocks. We downloaded the stock price history, referring to the 2 years period December 2020 until November 2022 with one-month interval, of 121 out of the 500 company stocks tracked by S&P500 (namely, the ones with no missing data in said intervals). Let us denote $P_{t,a}$ such cost of an asset $a$, with time index $t$. The return at time step $t$ is defined as

$$r_{t,a} = \frac{P_{t,a} - P_{t-1,a}}{P_{t-1,a}}$$

from which the expected return vector $\mu$ and the covariance matrix $\Sigma$ can be computed as $\tilde{\mu}_a = \frac{1}{T} \sum_{t=1}^T r_{t,a}$ and $\Sigma_{a,b} = \frac{1}{T} \sum_{t=1}^T (r_{t,a} - \tilde{\mu}_a)(r_{t,a} - \tilde{\mu}_b)$. We encode the Markowitz formulation (B7). From stock market data on S&P 500 stocks.

Another parameter of the generated instances is the partition number $w$ [67], that describes the granularity of the portfolio discretization. Since a budget of $2^w - 1$ equally large chunks. Each asset decision variable $x_i$ is an integer that can take values from 0 to $2^w - 1$, indicating how many of these partitions to allocate towards asset $i$. This explains why the constraint $\sum_i x_i = 2^w - 1$ enforces the budget to be totally invested. As a consequence, $w$ is also equal to the number of bits one needs to allocate for every integer and, by extension, asset.

Notice that $\mu^T x$ is the expected return of a portfolio if $\mu$ represents the vector of the portions of the portfolio for each asset, i.e. $0 \leq p_i \leq 1$ and $\sum_i p_i = 1$. In order to make integer decision variables, the number of chunks $x_i$ from historic financial data on S&P 500 stocks.

The last parameter that one needs to set to fully specify the instance is the risk aversion factor $\gamma$, weighting differently the return and the volatility in the objective function. Common values of the risk aversion factor are $\gamma = 0.5, 1, 2$.

The parameter values used in the instances tested in this work are $\gamma = 1$ and $w = 3 (for the small- (large-) scale tests employing the Gibbs (SA and DA) solvers, respectively, yielding a portfolio granularity of 7 (31) equal chunks.

## Appendix C: Details on the algorithm subroutines

This section elaborates on the subroutines that constitute Algorithm 1.

In line 5, we take as input the penalization function $E^{(p)}$ of the problem under consideration and the violation threshold $v_{\text{cut}}$, which sets the maximum penalization value considered. For the constrained problems analyzed in this work, the penalization degeneracies values $n_{\text{pen}}(v)$ were analytically derived in Section I from the structure of $E^{(p)}$. Direct expressions can be directly construct the vector of degeneracies up to $v_{\text{cut}}$. For more general problems not considered here, where analytical expressions are unavailable, one can instead estimate the penalization degeneracies by evaluating the penalization energies of uniformly sampled bitstrings and subsequent fit.

Line 1 computes a lower bound of the objective function $E_{\text{LB}} \leq \min_{x \in \{0,1\}^n} E^{(o)}(x)$. In principle, any valid method to compute a lower bound can be employed; in this work, we use a Semi-definite Programming (SDP) relaxation for the PO case, where an analytical lower bound is not evident, while for TSP and MNPP where the lower bound is obvious in particular, for TSP, where $E_{\text{LB}} = 0$ for the other cases. The SDP relaxation consists of optimizing over the cone of semi-definite matrices intersected with linear constraints. Specifically, to lower bound $E^{(o)}(x) = x^T (Qx + L)x$, an SDP relaxation is formulated as

$$E_{\text{LB}} := \min \text{Tr}(Y^T Q)$$

s.t. $Y \geq 0,$
$$Y_{ii} = Y_{ij} \quad \forall i = 2, \ldots, n+1$$
$$Y_{i1} = Y_{ii}$$

where $Y$ is a $(n+1) \times (n+1)$ real positive semidefinite matrix, $\text{Tr}(A^T B) = \langle A, B \rangle = \sum_{ij} A_{ij} B_{ij}$ denotes the inner product between matrices and the matrix $Q$ is given by

$$Q = \begin{pmatrix} 0 & \frac{1}{2} L^T \\ \frac{1}{2} L & Q \end{pmatrix}$$

For further details on the derivation, see Ref. [39], Appendix B.

In line 2, we compute a pre-defined number $N_s$ of objective energy values $\{E_i\}_{i=1}^{N_s}$ of feasible bitstrings uniformly drawn from $\mathcal{F}$ and approximate the feasible spectral weights $n_\Delta(e)$, defined in Eq. (5). For a general constrained problem with constraints of the form $Ax = b$, uniformly sampling feasible bitstrings is generally computationally challenging [69, 70]. Nevertheless, for structured problems, efficient strategies can often be devised [71, 72]. In the present work, such strategies were implemented depending on the specific problem structure. For MNPP, each feasible bitstring corresponds to an assignment of all $N$ items into $P$ partitions, yielding $P^N$ possible solutions. Uniform sampling is achieved by independently assigning each item $i$ to a random partition $p \in \{1, \ldots, P\}$ and setting $x_{i,p}^{(j)} = 1$ and otherwise. For TSP, a feasible bitstring represents a Hamiltonian cycle, which can be uniformly generated by sampling a random permutation $\sigma$ of $1, \ldots, n_v$ and setting $x_{\sigma(j),i} = 1$ and $0$ otherwise. For PO, each valid portfolio corresponds to one of the $\binom{N+w-1}{w-1}$ ways of distributing $2^w - 1$ indistinguishable units among $N$ assets. After generating $N_s$ such portfolios, associated objective energies are computed. From this, the computation of $n_\Delta(e)$ follows straightforwardly via counting and subsequent fit.

Steps 5 and 3 and 4 use the computed $n_\Delta(e)$ and $n_{\text{pen}}(v)$ to evaluate, up to a common factor, the probability bounds for three classes of configurations: infeasible states, feasible states with low objective energy, and feasible states with high objective energy.

Finally, in step 7, the numerical root-finding of $g$ [48] determines an integer approximation to a root of [48]. Thus, we conclude that under assumptions that are often met by problems under consideration, one can choose the parameters of the algorithm such that it is efficient and guaranteed to yield the targeted reformulation. In particular, for MNPP, TSP and PO, the sampling is efficient.

## Appendix D: Direct estimation of penalization weights

In order to establish a baseline for our algorithm, we here develop a strategy for determining $\lambda$ based on standard, simple bounds of the objective function to the case of Gibbs samplers. This strategy captures typical initial considerations of practitioners when determining values of $\lambda$ using binary search. We provide a simple efficient formula for a penalty weight $\lambda$ that yields an $\eta$-reformulation for an exact Gibbs solver at known temperature. The penalty weight is the sum of the weights [35–37] and is sufficient for an exact solver, i.e. a Gibbs solver at inverse temperature $\beta \to \infty$. Second, a thermal correction proportional with the temperature of the solver gives

$$M_{\ell_1}(\beta) = \beta^{-1}(\ln 2 - \ln(1-\eta)) + \|Q\|_{\ell_1}.$$

The expression is motivated by the following guarantee:

**Lemma 5.** *For a constrained problem (P) of size $n$ and objective function $E^{(o)}(x) = x^T Q x$ a penalty weight $M_{\ell_1}(\beta)$ defined in (D1) ensures an $\eta$-reformulation (P_{M*}) for a Gibbs solver at inverse temperature $\beta$.*

**Proof.** Ensuring that the probability of sampling feasible solutions is greater than $\eta$ is equivalent to show that sampling infeasible solutions occurs with probability at most $1 - \eta$, i.e. $\Pr[x \notin \mathcal{F}] \leq 1 - \eta$. Using the fact that the energy of the QUBO formulation will be $E(x) = E^{(o)}(x) + M(\Ax - b)^2 \geq 1$, we can bound

$$\Pr[x \notin \mathcal{F}] = \sum_{x \notin \mathcal{F}} p(x) = N_\beta \sum_{x \notin \mathcal{F}} e^{-\beta(E^{(o)}(x)+M(Ax-b)^2)} \leq N_\beta e^{-\beta M} \sum_{x \notin \mathcal{F}} e^{-\beta E^{(o)}(x)},$$

where $N_\beta^{-1} = \sum_{x \in \{0,1\}^n} e^{-\beta E(x)}$ is the normalization constant of the pmf. We then define the minimal objective energy as $E_{\min} = \min_{x \in \{0,1\}^n} E^{(o)}(x)$ and bound

$$\Pr[x \notin \mathcal{F}] \leq e^{-\beta(M+E_{\min}-E_{\text{max}})}2^n,$$

To bound the normalization constant, suppose we know the energy of a feasible bitstring to be $E(x_{\text{feas}}) = E_{\text{feas}}$, which doesn't depend on $M$ since $E(x) = E^{(o)}(x)$ if $x \in \mathcal{F}$; then, $N_\beta^{-1} \geq e^{-\beta E_{\text{feas}}}$ and

$$\Pr[x \notin \mathcal{F}] \leq e^{-\beta(M+E_{\text{min}}-E_{\text{feas}})2^n.$$

To ensure that $\Pr[x \notin \mathcal{F}] \leq 1 - \eta$ it is thus sufficient to pick $M$ such that $e^{-\beta(M+E_{\text{min}}-E_{\text{feas}})2^n \leq 1 - \eta$, or equivalently,

$$M \geq \beta^{-1}(\ln 2 - \ln(1-\eta)) + E_{\text{feas}} - E_{\min}.$$

To prove the claim on $M_{\ell_1}(\beta)$, it is left to show only that $\|Q\|_{\ell_1} \geq E_{\text{feas}} - E_{\min}$. This is immediate as

$$\|Q\|_{\ell_1} = \sum_{i,j} |Q_{ij}| = \sum_{i,j} Q_{ij} - \sum_{i,j} Q_{ij} < 0 = \max_x x^T Q x \geq E_{\text{feas}} - E_{\min}.$$

Clearly, $\sum_{i,j} Q_{ij} \geq E_{\text{max}} - E_{\min}$ and proves the lemma.

Notice that the fact that $\|Q\|_{\ell_1} \geq E_{\text{feas}} - E_{\min}$ is related to the advantage for exact solvers in using the more conservative weight $M_{\text{SDP}} = E_{\text{feas}} - E_{\text{SDP}}$, rather than $M_{\ell_1} = M_{\ell_1}(\beta = \infty) = \|Q\|_{\ell_1}$, as shown in Ref. [39], where $E_{\text{SDP}}$ is a lower bound of $E_{\min}$.

## Appendix E: Triviality and existence of the solution

Sampling feasible solutions with a maximal allowed energy, with probability at least $\eta$ and using a Gibbs solver at temperature $\beta$, can range from extremely difficult to trivial. In extreme cases, the task may even become infeasible. In this section, we illustrate how the algorithm handles these two opposite cases.

For a fixed $\beta$, there is an upper bound on the sampling success probability of feasible solutions with energy not exceeding $E_I$. This bound corresponds to the probability of sampling such solutions assuming that only feasible points could be drawn, that is, in the limit of very large $M$ where infeasible configurations are fully suppressed. Formally, this upper limit is the cumulative distribution function of the Gibbs measure restricted to the feasible subspace, evaluated at $E_I$. Recall that in Algorithm 1 we determine $M$ from three bounds using

$$g(M) = B_F(M) + B^z_F - \frac{1-\eta}{\eta} B^z_F$$

The function $g$ is monotonically decreasing in $M$, and it is constructed so that its zeros (and the region where $g(M) \leq 0$) correspond to values of $M$ satisfying the requirement. The maximal $\eta$ ensuring the existence of a guaranteed sampling success, which we denote as $\eta_{\text{exist}}$, occurs when $g(M)$ tends to zero only asymptotically. Since $g(M) \xrightarrow{M \to \infty} B^z_F - \frac{1-\eta}{\eta} B^z_F$, then by setting this limit to zero we obtain

$$\eta_{\text{exist}} = \frac{B^z_F}{B^z_F + B^z_F}.$$

In the algorithm, if the required sampling success probability $\eta \geq \eta_{\text{exist}}$, then the requirement is unattainable: $g$ has no roots and the algorithm returns $\{\}$. The required sampling success can then be reduced to $\eta_{\text{exist}} - \epsilon$ for a small $\epsilon$ and the algorithm rerun to obtain an attainable solution. Conversely, if the requirement is already met even with no penalty weight ($M = 0$), the problem is considered trivial: the root of $g$ will be negative and therefore returning $\max\{0, M^*\}$ will ensure a positive and sufficient penalty weight.

## Appendix F: Robust implementation in logspace

A naive numerical implementation of the algorithm may suffer from numerical instabilities or overflow, primarily due to the exponentials involved in the computations of the terms $B_F$, $B^z_F$ and $B^z_F$. To prevent this, we implement a numerically stable formulation, described in this section.

Let us first take the function (E1), and recall that $B_F(M) = \sum_{v=1}^{v_{\text{cut}}} e^{-\beta M v} n_{\text{pen}}(v)$, $B^z_F = \sum_{e \in \mathcal{K}} e^{-\beta e} n_\Delta(e + E_{\text{LB}})$, $B^z_F = \sum_{e \in \bar{\mathcal{K}}} e^{-\beta c} n_\Delta(e + E_{\text{LB}})$ and set $c = \frac{1-\eta}{\eta}$. We can alternatively define the function

$$G(M) = \log(B_F(M) + B^z_F) - \log\left(\frac{1-\eta}{\eta}\right) - \log(B^z_F).$$

Note that the functions $g(M)$ and $G(M)$ share the same sign and root, hence, $G(M)$ can be used in place of $g(M)$ in the Algorithm 1 yielding logarithmically and stably. We compute the terms of $G$ as

$$\log(B_F(M)) = \text{LSE}[\log(n_{\text{pen}}(v)) - \beta M v]_{v=1}^{v_{\text{cut}}},$$
$$\log(B^z_F) = \text{LSE}[\log(n_\Delta(e + E_{\text{LB}})) - \beta e]_{e \in \mathcal{K}},$$
$$\log(B_F(M) + B^z_F) = \text{LSE}[\log(B_F(M)), \log(B^z_F)],$$
$$\log(B^z_F) = \text{LSE}[\log(n_\Delta(e + E_{\text{LB}})) - \beta(e + \Delta)]_{e \in \bar{\mathcal{K}}}.$$

Using the log-domain function $G(M)$ instead of $g(M)$ also affects the computation of the existence threshold discussed in Section E. By imposing $G(\infty) = 0$, one can compute $\eta_{\text{exist}} = (1 + e^\gamma)^{-1}$, with $\gamma = \log(B^z_F) - \log(B^z_F)$, properly evaluated

using the LSE function to ensure numerical stability.

## Appendix G: Dependence of the Algorithm's output on the input parameters (v_cut and E_I)

This section provides a concise analysis of the sensitivity of the algorithm's output to choices of the input parameters $E_I$, the maximal energy of the desired solutions, and $v_{\text{cut}}$, the maximal value of the penalization term considered for infeasible points. Fig. 6 illustrates, for small instances ($n_{\text{cuts}} = 16$) across all benchmarked problems, the behavior of the returned $M^*$ and its associated required success probability, compared with the effective success probability $\eta_{\text{eff}}$ of all Gibbs sampler. For MNPP and TSP instances, small values of $v_{\text{cut}}$ do not change $M^*$ accounting for most of the probability mass of infeasible points, as indicated by $\eta_{\text{pen}}(v) \geq 0$ continuing the robustness of the algorithm also in this setting.

For DA (version 3) we find that $\eta_{\text{eff}}$ is consistently higher than the targeted $\eta$ in all settings. Fig. 4. Moreover, all $\eta_{\text{eff}}$ quickly converge to the system size. This indicates that our methods overestimates $M$ for larger system sizes. We have already seen in Fig. 2 that for large systems a slight overestimation of yields quickly to nearly only observing feasible solutions. The output distribution of the DA is only qualitatively approximated by Gibbs distribution with inverse temperature $\beta$ determined in the annealing schedule. Our results show that the DA is further towards low-objective solutions than the Gibbs distribution with inverse temperature $\beta$ determined in the annealing schedule. Our results show the DA is further towards low-objective solutions than the Gibbs distribution, thus, our methods determines practical values of $M$ for Fujitsu's Digital Annealer Unit on instances with over thousand bits ensuring reliable performance of the solver.

A campaign approach to the problem of determining a suitable value for $M$, e.g. using binary search for a suitable value of $M$, e.g. using binary search, is already an efficient estimate for $M$ for initial value for $M$ the binary search. Starting from an over-estimated value for $M$, the penalization is iteratively halved and the problem is solved until an unacceptable number of infeasible solutions start appearing. This method traverses the search space exponentially fast. The practical benefit of the method can be quantified as the number of solver calls that are 'saved' when initializing the binary search with a more direct upper bound. As we show in Section D, a simple efficiently computable $M$ yielding an $\eta$-reformulation of a Gibbs sampler at inverse temperature $\beta$ is given by Eq. (D1).

So the binary search, as provided by our method developed here. So the algorithmic benefit of the method can be quantified as the number of solver calls that are 'saved' when initializing the binary search with a more direct upper bound. As we show in Section D, a simple efficiently computable $M$ yielding an $\eta$-reformulation of a Gibbs sampler at inverse temperature $\beta$ is given by Eq. (D1).

## Appendix H: Solving the inverse problem as a byproduct: from M to β

A convenient extension of the algorithms introduced in this work arises in the inverse problem to the Big-$M$ problem: determine the inverse temperature $\beta$ that allows a thermal solver to sample desired solutions with probability at least $\eta$, when the penalty weight $M$ is fixed. Such a situation may occur when increasing $M$ is not possible due to interaction strengths, hardware, or software limitations, while the solver temperature can still be adjusted to meet the sampling requirement. This inverse problem can be solved with the same strategy introduced in this work (Sec. B). To this end, we modify Algorithm 1 line 7 to calculate an optimal inverse temperature $\beta^*$ as the root of $\beta \to g(M)$ for given $M$.

## Appendix I: Penalization degeneracy

In this section, we present the analytical results on the penalization degeneracy $n_{\text{pen}}(v) = |\{x \in \{0, 1\}^n : E^{(p)}(x) = v\}|$ for the constrained optimization problems considered in this work. For the benchmarked optimization problems and their QUBO formulations, the dominant contributions to the total computational cost arise from the SDP relaxation, scaling as $O(n^3)$ and from uniformly sampling the feasible subspace and subsequent fitting or inferring the corresponding objective energies on $x$ or the parameters of each problem.

For MNPP with $N$ numbers to partition into $P$ partitions the penalization energy is $E^{(p)}(x) = \sum_{i=1}^N (1 - \sum_{p=1}^P x_{i,p})^2$ enforces a feasible decision matrix to be right-stochastic, i.e., $\sum_{p=1}^P x_{i,p} = 1 \forall i$, measuring that each number can only belong to one partition. As outlined above, the number of feasible bitstrings (i.e. $v = 0$) is $n_{\text{pen}}(0) = P^N$, since there are $P$ choices per row and $N$ rows contributing independently to the total number. Therefore, the number of bitstrings with $v = 1$ is $n_{\text{pen}}(1) = 0$, since here are $P$ choices per row and $N$ rows contributing independently to the total number. Therefore, the number of bitstrings with $v=1$ is $n_{\text{pen}}(1) = 0$ (since are $P$ choices per row and $N$ rows contributing independently to the total number. Therefore, the number of bitstrings with $v=1$ is $n_{\text{pen}}(1) = 0$, since the penalty term is zero only for perfect squares). For an instance for infeasible bitstrings (i.e. $v>0$) can be obtained by combinatorially counting methods. The following subsections detail these analytical expressions for each problem.

### 1. MNPP

For a Multiway Number Partition Problem (MNPP) instance with $N$ numbers to partition into $P$ partitions the penalization energy is $E^{(p)}(x) = \sum_{i=1}^N (1 - \sum_{p=1}^P x_{i,p})^2$ enforces a feasible decision matrix to be right-stochastic, i.e., $\sum_{p=1}^P x_{i,p} = 1 \forall i$, meaning that each element can only be assigned to one partition. Let's fix a row $i$ and determine how many distinct penalty values $E_i^{(p)}$ it can contribute. Since $\sum_{p=1}^P x_{i,p}$ can take values from 0 to $P$, the penalty contribution from row $i$ is $(1 - \sum_{p=1}^P x_{i,p})^2$, which can be $0, 1, 4, 9, 16, \ldots$ for $\sum_{p=1}^P x_{i,p} = 1, 0, -1, -2, \ldots$. Since a row (number) is a subset of $\{0, 1\}^P$ (the columns/partitions), the row-sum can at most be $P$ and at least be $0$. Therefore, $E_i^{(p)} \in \{0, 1, 4, 9, \ldots, (P)^2\}$. Feasible rows have $\sum_p x_{i,p} = 1$ and thus $E_i^{(p)} = 0$. The total penalty for the entire decision matrix is $E^{(p)}(x) = \sum_{i=1}^N E_i^{(p)}$. Since all rows are independent and can each take on energy values $\{0, 1, 4, 9, \ldots, (P)^2\}$, the penalization degeneracies can be obtained by considering all ways in which the per-row energy contributions sum to the total: 

$$n_{\text{pen}}(0) = P^N \quad \text{feasible bitstrings}$$

$$n_{\text{pen}}(v) = P^{N-s}\left(\begin{array}{c}N\\ v\end{array}\right)\left(1+\left(\frac{P}{2}\right)\right)^v \quad \forall v \in \{1,\ldots, 3\}$$

$$n_{\text{pen}}(v) = P^{N-s}\left(\begin{array}{c}N\\ v\end{array}\right)\left(1+\left(\frac{P}{2}\right)^v + (v-3)\left(\begin{array}{c}N\\ v-3\end{array}\right) P^{N-(v-3)}\left(1+\left(\frac{P}{3}\right)\right)^{v-4} \quad \forall v \in \{4, \ldots, 7\}$$

The analytical expressions are based on counting the ways to distribute rows with squared deviations among $N$ rows in the decision matrix, computing degeneracies for each value up to $v = 6$:

$$n_{\text{pen}}(0) = P^N \quad \text{feasible bitstrings} \tag{I1}$$

$$n_{\text{pen}}(v) = P^{N-s}\left(\begin{array}{c}N\\ v\end{array}\right)\left(1+\left(\frac{P}{2}\right)^v\right) \quad \forall v \in \{1, \ldots, 3\} \tag{I2}$$

$$n_{\text{pen}}(v) = P^{N-s}\left(\begin{array}{c}N\\ v\end{array}\right)\left(1+\left(\frac{P}{2}\right)^v + (v-3)\left(\begin{array}{c}N\\ v-3\end{array}\right) P^{N-(v-3)}\left(1+\left(\frac{P}{3}\right)\right)^{v-4} \quad \forall v \in \{4, \ldots, 7\} \tag{I3}$$

### 2. TSP

For a Travelling Salesman Problem instance with $n_v$ vertices, the penalization energy is $E^{(p)}(x) = \sum_{t=1}^{n_v} (1 - \sum_{i=1}^{n_v} x_{t,i})^2 + \sum_{i=1}^{n_v} (1 - \sum_{t=1}^{n_v} x_{t,i})^2$ enforces a feasible decision matrix $[x]_{t,i}$ to be stochastic, meaning that each row and each column must contain exactly a single 1. The number of feasible bitstrings corresponds to the number of permutation matrices, hence $n_{\text{pen}}(0) = n_v!$ feasible bitstrings.

$$n_{\text{pen}}(0) = n_v! \quad \text{feasible bitstrings} \tag{I4}$$

$$n_{\text{pen}}(1) = 0 \tag{I5}$$

$$n_{\text{pen}}(2) = n_v!\left[n_v + 1\left(\begin{array}{c}n_v\\ 2\end{array}\right) + \frac{3}{2}\left(\begin{array}{c}n_v\\ 3\end{array}\right)\right] \tag{I6}$$

$$n_{\text{pen}}(3) = 0 \tag{I7}$$

$$n_{\text{pen}}(4) = n_v!\left[\left(\begin{array}{c}n_v\\ 2\end{array}\right) + 21\left(\begin{array}{c}n_v\\ 3\end{array}\right) + 57\left(\begin{array}{c}n_v\\ 4\end{array}\right) + 45\left(\begin{array}{c}n_v\\ 5\end{array}\right) + \frac{45}{4}\left(\begin{array}{c}n_v\\ 6\end{array}\right)\right] \tag{I8}$$

$$n_{\text{pen}}(5) = 0 \tag{I9}$$

$$n_{\text{pen}}(6) = 5n_v! \left[\frac{47}{15}\left(\begin{array}{c}n_v\\ 3\end{array}\right) + 24\left(\begin{array}{c}n_v\\ 4\end{array}\right) + 137\left(\begin{array}{c}n_v\\ 5\end{array}\right) + 1157\left(\begin{array}{c}n_v\\ 6\end{array}\right) + \frac{567}{4}\left(\begin{array}{c}n_v\\ 7\end{array}\right) + 126\left(\begin{array}{c}n_v\\ 8\end{array}\right) + \frac{63}{2}\left(\begin{array}{c}n_v\\ 9\end{array}\right)\right] \tag{I10}$$

$$n_{\text{pen}}(7) = 0 \tag{I11}$$

### 3. PO

For a Portfolio Optimization instance with $N$ stocks and partition number $w$, the penalization energy is $E^{(p)}(x) = (\sum_{i=1}^N x_i - 2^w + 1)^2$, where each component is an integer $x_i \in \{0, \ldots, 2^w - 1\}$. The penalization is zero only for bitstrings $x$ whose components sum up to $2^w - 1$, such configurations corresponding to feasible portfolios. For infeasible bitstrings, a similar reasoning applies: if the configuration components sum up to $2^w - 1 \pm k$, then $v = k^2$. The number of feasible configurations ($v = 0$) can be computed as the number of ways to distribute $2^w - 1$ indistinguishable units among $N$ distinguishable units among $N$ distinguishable boxes:

$$n_{\text{pen}}(0) = \left(\begin{array}{c}2^w + N - 2\\ N - 1\end{array}\right) \quad \text{feasible bitstrings} \tag{I12}$$

$$n_{\text{pen}}(1) = \left(\begin{array}{c}2^w + N - 3\\ N - 1\end{array}\right) + \left(\begin{array}{c}2^w + N - 1\\ N - 1\end{array}\right) - N \tag{I13}$$

$$n_{\text{pen}}(4) = \left(\begin{array}{c}2^w + N - 4\\ N - 1\end{array}\right) + \left(\begin{array}{c}2^w + N\\ N - 1\end{array}\right) - N^2 \tag{I14}$$

$$n_{\text{pen}}(9) = \left(\begin{array}{c}2^w + N - 5\\ N - 1\end{array}\right) + \left(\begin{array}{c}2^w + N + 1\\ N - 1\end{array}\right) - N^2\frac{N + 1}{2} \quad \text{for } w \geq 2 \tag{I15}$$

$$n_{\text{pen}}(16) = \left(\begin{array}{c}2^w + N - 6\\ N - 1\end{array}\right) + \left(\begin{array}{c}2^w + N + 2\\ N - 1\end{array}\right) - N^2\frac{N + 1 N + 2}{2}\quad \text{for } w \geq 2 \tag{I16}$$

$$n_{\text{pen}}(25) = \left(\begin{array}{c}2^w + N - 7\\ N - 1\end{array}\right) + \left(\begin{array}{c}2^w + N + 3\\ N - 1\end{array}\right) - N^2\frac{N + 1 N + 2 N + 3}{2 \cdot 3 \cdot 4} \quad \text{for } w \geq 3 \tag{I17}$$

$$n_{\text{pen}}(v) = 0 \quad \forall v \neq k^2 \tag{I18}$$

</content>
