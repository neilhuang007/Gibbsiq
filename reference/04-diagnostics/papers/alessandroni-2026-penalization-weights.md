# Scalable Determination of Penalization Weights for Constrained Optimizations on Approximate Solvers


> **Citation.** Canonical entry `alessandroni2026weights` in [`references.bib`](../../references.bib) (resolved via Crossref/DataCite). arXiv:[2604.02416](https://arxiv.org/abs/2604.02416).
>
> **Companion note.** [`alessandroni-2026-penalization-weights.note.md`](./alessandroni-2026-penalization-weights.note.md) — how this paper links to Gibbsiq.

**Authors:**

- Edoardo Alessandroni (Corresponding author: ealessan@sissa.it) -- Quantum Research Center, Technology Innovation Institute (TII), Abu Dhabi; SISSA -- Scuola Internazionale Superiore di Studi Avanzati, Trieste, Italy
- Sergi Ramos-Calderer -- Centre for Quantum Technologies, National University of Singapore, Singapore; Quantum Research Center, Technology Innovation Institute (TII), Abu Dhabi
- Michel Krispin -- Hamburg University of Technology, Institute for Quantum Inspired and Quantum Optimization, Hamburg, Germany
- Fritz Schinkel -- Fujitsu Germany GmbH, Mies-van-der-Rohe-Strasse 8, 80807 Munich, Germany
- Stefan Walter -- Fujitsu Germany GmbH, Mies-van-der-Rohe-Strasse 8, 80807 Munich, Germany
- Martin Kliesch -- Hamburg University of Technology, Institute for Quantum Inspired and Quantum Optimization, Hamburg, Germany
- Leandro Aolita -- Quantum Research Center, Technology Innovation Institute (TII), Abu Dhabi
- Ingo Roth -- Quantum Research Center, Technology Innovation Institute (TII), Abu Dhabi

## ABSTRACT

Quadratic unconstrained binary optimization (QUBO) provides problem formulations for various computational problems that can be solved with dedicated QUBO solvers, which can be based on classical or quantum computation. A common approach to constrained combinatorial optimization problems is to enforce the constraints in the QUBO formulation by adding penalization terms. Penalization introduces an additional hyperparameter that significantly affects the solver's efficacy: the relative weight between the objective terms and the penalization terms. We develop a pre-computation strategy for determining penalization weights with provable guarantees for Gibbs solvers and polynomial complexity for broad problem classes. Experiments across diverse problems and solver architectures, including large-scale instances on Fujitsu's Digital Annealer, show robust performance and order-of-magnitude speedups over existing heuristics.

## INTRODUCTION

Combinatorial optimization problems arise widely in both theoretical research and real-world applications, aiming to identify the optimal configuration of discrete decision variables that minimizes a given objective function. The corresponding search space typically has a size scaling exponentially with the number of variables, rendering the optimization a computationally hard problem. Methods for solving these problems have been a subject of intense study in both classical and quantum computation [1]. In particular, powerful heuristics and dedicated hardware have been developed [2-11] to tackle quadratic unconstrained binary optimizations (QUBOs) [12, 13]. These include approaches based on Gibbs sampling or simulated annealing [14-21], special-purpose chips for digital annealing [22-24], and quantum primitives such as adiabatic evolution [25-28] and different variants of the Quantum Approximate Optimization Algorithm (QAOA) [29-33].

Practical solvers tend to be heuristic algorithms that yield approximate solutions. For instance, simulated annealing (or any solver based on Gibbs sampling) outputs a configuration sampled from a low-temperature thermal distribution over the combinatorial space, with an objective value close (but in general not equal) to the optimum. The colder the distribution, the higher the probability that the output state is very close to the optimal solution of the problem. More precisely, for ideal Gibbs samplers, each configuration $\mathbf{x}$ is sampled with a probability proportional to $e^{-E(\mathbf{x})\beta}$, where $E(\mathbf{x})$ is the energy of the configuration and $\beta$ is the inverse temperature of the system. Sampling from this probability distribution or estimating the associated partition function is generally hard, so practical solvers rely on Markov Chain Monte Carlo techniques [14, 34] and annealing schedules to approximate it. These methods, such as simulated annealing, propose new configurations and accept or reject them according to their energy and target temperature, gradually biasing the search toward low-energy configurations. Hardware-accelerated implementations, such as Fujitsu's Digital Annealer [22-24], further enhance the exploration of the energy landscape through fast, parallelized sampling mechanisms, thereby improving the chances of finding solutions with low objective.

Importantly, general combinatorial optimization problems, arising in applications, usually include constraints that restrict the search space. Yet, a standard approach to tackle such problems with QUBO solvers is to convert constraints into penalization terms weighted by a constant, commonly referred to as Big-$M$. The choice of this constant crucially shapes the energy landscape. If the constant $M$ is set too high, the low-energy spectrum becomes uninformative: the solver is forced to prioritize constraint satisfaction at all costs, returning feasible states that may be far from optimal with respect to the original objective function. Conversely, if $M$ is chosen too small, the energies of infeasible configurations may lie near, or even below, the optimal feasible region, causing approximate solvers to sample disproportionately from infeasible solutions that violate constraints. Existing computationally-efficient Big-$M$ prescriptions tend to substantially overestimate the required penalty [35-37], which in practice degrades solution quality [35, 38, 39]. Although recent work [39] proposes a practical strategy that delivers significantly lower (but still sufficient) Big-$M$ values, it is primarily designed for exact solvers. Current approaches do not incorporate the degree of approximation characteristic of modern heuristic methods, such as a Gibbs sampler at finite temperature. A systematic penalization strategy for approximate solvers is missing.

In this work, we introduce a novel, broadly applicable algorithm for a priori determining the penalization term for a given constrained optimization problem and a specified approximate solver. Our approach combines analytical considerations with uniform sampling over feasible configurations, to derive efficiently evaluable bounds on the solver's output distribution, from which the penalization weight $M$ is calculated. We prove that for exact Gibbs solvers at arbitrary $\beta$, the algorithm yields a QUBO reformulation with a controllable, guaranteed minimum probability of sampling feasible solutions with energy at most $E_f$. The algorithm's hyperparameters allow trading off run-time against accuracy of approximating an optimal (minimal) $M$.

We further show that, for large classes of constrained optimization problems and appropriate hyperparameters, the algorithm's runtime and memory scales polynomially in the system size. We numerically demonstrate the practical applicability of our method across relevant parameter regimes, diverse problem instances and solver architectures. In particular, we benchmark the approach on representative constrained optimization problems, including the Traveling Salesman Problem (TSP), the Multiway Number Partitioning Problem (MNPP), and Portfolio Optimization (PO). Besides small-scale evaluations for exact Gibbs sampling and intermediate-scale experiments with simulated annealing, we show that our method can be used to determine penalization weights for Fujitsu's Digital Annealer (version 3) on problem instances of up to several thousand bits. Although the Digital Annealer is known to deviate from our underlying assumption of thermal output distributions, we find that our method still qualitatively captures its behavior sufficiently well to achieve an order-of-magnitude speedup in time-to-solution compared to direct binary searches for $M$ based on simpler heuristics.

## RESULTS

We start the presentation of our results with formalizing the problem of determining penalization weights and empirically demonstrating the importance of the big-$M$ problem for approximate solvers using Fujitsu's Digital Annealer (version 3). In the subsequent section we describe our algorithm for determining $M$ and establish its theoretical guarantees, before turning to numerical validation and benchmark in the last section.

### A. The Big-$M$ problem for approximate combinatorial solvers

In the following, we consider the constrained optimization problems

$$\min_{\mathbf{x}\in\{0,1\}^n} E^{(o)}(\mathbf{x}) = \mathbf{x}^t Q \mathbf{x} \quad \text{subject to} \quad A\mathbf{x} = \mathbf{b} \tag{P}$$

given by $Q \in \mathbb{R}^{n\times n}$, $A \in \mathbb{Z}^{m\times n}$, and $\mathbf{b} \in \mathbb{Z}^m$. This special type of linearly constrained binary optimization (LCBO) problems is able to capture complex problem formulations such as polynomially constrained problems and integer-variable problems, which can all be cast into this form using certain *gadgets* [39, 41-44].

A constrained problem in the form (P) can be converted to a Quadratic Unconstrained Binary Optimization (QUBO) problem by promoting the constraints $A\mathbf{x} = \mathbf{b}$ to quadratic penalty terms

$$E^{(p)}(\mathbf{x}) = (A\mathbf{x} - \mathbf{b})^2, \tag{1}$$

weighted by a penalization constant $M > 0$. The new function to minimize, now a sum of the objective and penalization contributions, reads

$$\min_{\mathbf{x}\in\{0,1\}^n} E(\mathbf{x}) = \mathbf{x}^t Q \mathbf{x} + M(A\mathbf{x} - \mathbf{b})^2. \tag{$P_M$}$$

The minimization is now over the entire space $\{0,1\}^n$, but infeasible bit strings will incur an energy penalization. We consider ($P_M$) an *exact reformulation* of (P) when the optimal points remain unchanged. Thus, solving an exact reformulation ($P_M$) with an exact combinatorial solver yields an optimal solution to the original constrained problem. For an exact solver, its runtime and required computational effort depend on $M$. This insight motivates choosing a minimal penalization constant $M^*_{\text{exact}}$ that still ensures an exact reformulation. As shown in [39], while finding $M^*_{\text{exact}}$ is NP-hard, good approximations to it can be found using the following strategy: given a feasible point $\mathbf{x}_{\text{feas}}$, a lower-bound $f_{\widehat{\text{unc}}}$ on the objective, with $f_{\widehat{\text{unc}}} \leq E^{(o)}(x)$ for any $x\in\{0,1\}^n$, and any constant $\delta > 0$, Eq. ($P_M$) with

$$M := f(\mathbf{x}_{\text{feas}}) - f_{\widehat{\text{unc}}} + \delta \tag{2}$$

is an exact reformulation of (P). A feasible point and an objective lower bound can be efficiently pre-computed using, e.g. greedy algorithms and SDP relaxations, respectively. This approach leads to a tighter upper bound to $M^*_{\text{exact}}$ than the trivial upper bound $M^*_{\text{exact}} \leq \|Q\|_{\ell_1} + \delta$ [39], which in turn improves the run-time of solvers.

However, approximate solvers do not necessarily return the optimal point but a solution with a low objective value approximating the true minimum. For this reason, using the strategy described in Ref. [39] will generally not ensure feasibility of the solution for an approximate solver. At the same time, also for approximate solvers, one expects that choosing a large value for $M$ will rapidly deteriorate the quality of the solver's results, manifesting the *big-$M$ problem*.

As a first result, we establish the need for 'fine-tuning' $M$ in the case of Fujitsu's Digital Annealer Unit (DAU) for some examples. Fig. 2 shows the frequency of feasible solutions and their mean energy using different values of $M$ for different problem instances and sizes. We observe that, in the regime where the majority of solutions are feasible, the mean objective value increases significantly with larger $M$. Thus, to ensure low objectives, it is important to choose a value of $M$ close to the transition in the feasibility probability. And the 'good' regime for $M$ becomes narrower as the system size increases. Notice also that a naive choice of $M$, like the one in Eq. (12), overestimates the transition point by several orders of magnitude, and consequently will return solutions with an undesired, high objective value.

These observations motivate us to devise a systematic strategy for solving the *big-$M$ problem*. We begin by formalizing the problem statement with the following definition. Let $\mathcal{F} = \{\mathbf{x} \mid A\mathbf{x} = \mathbf{b}\} \subset \{0,1\}^n$ denote the subspace of feasible points.

**Definition 1.** *The QUBO problem* ($P_M$) *is an $\eta$-reformulation of the problem* (P) *for a solver with guaranteed energy threshold $E_f$, or short $\eta$-reformulation, if the solver's output distribution on* ($P_M$) *fulfills*

$$\Pr[\{x\in\mathcal{F} \mid E(x) \leq E_f\}] \geq \eta. \tag{3}$$

In other words, such a reformulation ensures observing feasible solutions of a low energy with (at least) constant probability. We consider $M$ to be optimal if it is the minimal value guaranteeing an $\eta$-reformulation and denote it as $M^*_\eta$. While not formally established, we expect that finding $M^*_\eta$ will be in general as hard as solving the original optimization problem. Thus, our goal is to devise an efficient strategy that approximates $M^*_\eta$ from above and benchmark the quality of its solution for different instances.

### B. A Big-$M$ strategy

An apparent challenge in defining a strategy for solving the Big-$M$ problem is that the definition of an $\eta$-reformulation depends on the actual output distribution of the solver under consideration. This is different from the exact reformulation, which only depends on the problem instance itself. Output distributions of approximate solvers are generally not known a priori and may depend in complex ways on optimization schedules and other hyperparameters. To overcome this obstacle, we consider Gibbs samplers as the prototypical proxies of an approximate solver. Indeed, a large class of approximate optimization algorithms, including Metropolis-like dynamics, simulated annealing, and more general MCMC-based solvers, are fundamentally grounded in Gibbs sampling principles, as they are designed to progressively concentrate probability mass onto low-energy configurations of an associated Gibbs distribution [14, 15, 45].

A Gibbs sampler at inverse temperature $\beta$ has output distribution $p(\mathbf{x}) = \mathcal{N}_\beta e^{-\beta E(\mathbf{x})}$, where $\mathcal{N}_\beta$ is a normalization constant. The degree of approximation of a Gibbs sampler as a solver is, thus, captured by a single parameter $\beta \geq 0$, tending to an exact solver for $\beta \to \infty$.

Given the output distribution of the solver, it is in principle possible (but generally inefficient) to calculate $M^*$ exactly. The general idea for an efficient strategy, illustrated in Fig. 1, is to instead calculate bounds on the probability of three distinct events: observing (i) a feasible point with objective smaller or equal than $E_f$, (ii) a feasible point with objective larger than $E_f$ and (iii) an infeasible point. These bounds can then be combined to determine $M^* \geq M^*_\eta$ which will be closer to $M^*_\eta$ the tighter the bounds are.

Evaluating the bounds requires the following weight functions (non-normalized densities) depending on the problem instance: first, we define the *penalization degeneracy* as

$$n_{\text{pen}}(v) = |\{\mathbf{x}\in\{0,1\}^n : E^{(p)}(\mathbf{x}) = v\}|. \tag{4}$$

This represents the number of bitstrings with penalty function value $E^{(p)}(\mathbf{x}) = v$ and enables control over the distribution of infeasible points. For many problems, the penalization degeneracy can be obtained analytically. We derive the expressions for MNPP, TSP and PO in Section I for small $v$. We have found that in practice it is sufficient to evaluate $n_{\text{pen}}(v)$ only for $v \leq v_{\text{cut}}$ up-to some small constant $v_{\text{cut}}$. Alternatively, one can resort to a coarse sampling of the penalization energies of bitstrings and subsequent fit.

Second, we make use of a lower bound $E_{\text{LB}} \leq E^{(o)}(\mathbf{x})$ on the unconstrained objective function. Such a bound can be efficiently computed using an SDP relaxation.

Third, we introduce the *feasible spectral weights*

$$n_\Delta(e) = |\{\mathbf{x}\in\mathcal{F} : e \leq E^{(o)}(\mathbf{x}) < e + \Delta\}|. \tag{5}$$

This can be approximately estimated by randomly sampling a number $N_s$ of bit-strings from a uniform distribution over the feasible subspace $\mathcal{F}$ and counting the sampled strings $\mathbf{x}$ for which the objective energy $E^{(o)}(\mathbf{x})$ lies within the considered range. In practice, it is sufficient to estimate $n_\Delta(e)$ only for $e \in \Lambda = \{0, \Delta, 2\Delta, \ldots, \lceil (E_{\max} - E_{\text{LB}})/\Delta \rceil \Delta\}$, where $E_{\max}$ is the maximal energy sampled. For structured problems like TSP, MNPP or PO, the sampling is efficient, see Section C.

**Figure 1.** The big-$M$ problem for approximate solvers is to ensure by the choice of a penalization weight $M$ that an approximate solver samples feasible solutions with probability at least $\eta$ when given a QUBO reformulation of a constrained optimization problem. Optionally, one can additionally enforce the solution to be below a certain energy threshold $E_f$. We assume that the output distribution of a solver is qualitatively approximated by a Gibbs distribution at known inverse temperature, illustrated to the left in terms of the probability $p(e)$ of sampling a solution with energy $e$ conditioned on the solution being feasible or infeasible. The density of infeasible solutions is naturally grouped into families ('humps'), each one characterized by $E^{(p)}(x)$ taking a certain value. Our method to determine $M$, summarized to the right, calculates (1.) a lower bound $B^<_{\mathcal{F}}$ and (2.) an upper bound $B^>_{\mathcal{F}}$ on the probabilities of sampling feasible points with objective below and exceeding $E_f$, respectively. Together with (3.) an upper bound $B_{\overline{\mathcal{F}}}$ on the probability of infeasible events, (4.) the penalization weight $M$ is determined as the unique root of the scalar function $g(M)$, that depends on the targeted success probability $\eta$. We argue that this method is efficient for large classes of problems, prove theoretical guarantees on its performance, and demonstrate its practical applicability numerically. The algorithm sketch reads: 1. Lower bound target feasible states $\to B^<_{\mathcal{F}}$; 2. Upper bound high-energy feasible states $\to B^>_{\mathcal{F}}$; 3. Upper bound infeasible families contributions $\to B_{\overline{\mathcal{F}}}(M)$; 4. Return root of $g(M) = B_{\overline{\mathcal{F}}}(M) + B^>_{\mathcal{F}} - \frac{1-\eta}{\eta} B^<_{\mathcal{F}}$.

**Figure 2.** Proportion of feasible solutions observed $\eta_{\text{eff}}$ (top) and mean objective energy $E^{(o)}$ of sampled feasible solutions (bottom) on the DA solver (version 3) for different benchmarked problems (from left to right: Multiway Number Partitioning Problem (MNPP), Traveling Salesman Problem (TSP) instances from library [40], and TSP with cities placed on a circle) with different values of $M$ and problem size. The gray areas lack mean energy points because only infeasible bitstrings were sampled for those values of $M$. In the top panels, we observe a phase transition from infeasible to feasible solutions as $M$ increases, indicating that selecting optimized values of $M$ is needed. However, on the bottom panels, we notice a degradation in the quality of the sampled bitstrings. The mean of the energy $E^{(o)}$ of the outputs of the sampler increases for larger values of $M$, beyond a seemingly sweet spot that is located around the transition. For reference, the $M$ values suggested by Eq. (12) are several orders of magnitude larger than the shown scales: around $10^9$ for MNPP, $10^8$ for benchmarks TSP and $10^{10}$ for circle TSP. Such extreme overshooting implies that the mean energy sampled by the solver would lie far from the desired minimum, undermining the optimization's effectiveness.

The procedure of our strategy is summarized in Algorithm 1.

---

**Algorithm 1:** $M(E^{(o)}, E^{(p)}, E_f, \beta, \eta, v_{\text{cut}}, N_s, \Delta)$

**Input:** $E^{(o)}$ (objective), $E^{(p)}$ (penalty), $E_f$ (energy threshold), $\beta$ (inverse temperature), $\eta$ (success probability), $N_s$ (sample size), $v_{\text{cut}}$ (degeneracy cut-off), and $\Delta$ (energy resolution).

1. Determine $E_{\text{LB}}$ from SDP relaxation of $\min_{\mathbf{x}\in\{0,1\}^n} E^{(o)}(\mathbf{x})$
2. Estimate $n_\Delta(e + E_{\text{LB}})$ for each $e \in \Lambda$ from $N_s$ uniform samples from $\mathcal{F}$
3. Calculate $B^<_{\mathcal{F}} := \sum_{e\in\Lambda^<} e^{-\beta(e+\Delta)} n_\Delta(e + E_{\text{LB}})$ with $\Lambda^< := \{0, \Delta, \ldots, \lfloor (E_f - E_{\text{LB}})/\Delta \rfloor \Delta\} \subset \Lambda$
4. Calculate $B^>_{\mathcal{F}} := \sum_{e\in\overline{\Lambda^<}} e^{-\beta e} n_\Delta(e + E_{\text{LB}})$ for $\overline{\Lambda^<} := \Lambda \setminus \Lambda^<$
5. Compute the penalization degeneracy $n_{\text{pen}}(v)$ for $v \in \{1, \ldots, v_{\text{cut}}\}$. Set $B_{\overline{\mathcal{F}}}(M) := \sum_{v=1}^{v_{\text{cut}}} e^{-\beta M v} n_{\text{pen}}(v)$
6. Set $g(M) := B_{\overline{\mathcal{F}}}(M) + B^>_{\mathcal{F}} - \frac{1-\eta}{\eta} B^<_{\mathcal{F}}$
7. Determine $M^*$ as the root of $g(M)$.
8. **Return** $\max\{0, M^*\}$ or $\{\}$ if no roots were found.

---

Algorithm 1 combines these estimates to compute the bounds $B^<_{\mathcal{F}}$, $B^>_{\mathcal{F}}$, and $B_{\overline{\mathcal{F}}}$, that bound the probabilities of observing feasible points with a low objective value, feasible points with a high objective value, and infeasible points, respectively. From $B^<_{\mathcal{F}}$, $B^>_{\mathcal{F}}$, and $B_{\overline{\mathcal{F}}}$ we obtain an estimate $M^*$ for $M$ in the last step. The correctness of the algorithm in the limit of infinite samples is established by the following theorem.

**Theorem 2.** *In the limit $N_s \to \infty$ and for $v_{\text{cut}} = \max_\mathbf{x} E^{(p)}(\mathbf{x})$ the following holds: If Algorithm 1 returns $M^* \neq \{\}$, then* ($P_M$) *with $M = M^*$ is an $\eta$-reformulation with guaranteed energy threshold $E_f$ for a Gibbs sampler at inverse temperature $\beta$.*

*Proof.* The proof first establishes that the three bounds evaluated in the algorithm actually bound the corresponding events, and finally that they are combined into a bound of $M$.

By the theorem's assumption, $\mathbf{x}\in\{0,1\}^n$ is sampled according to the Gibbs distribution $p_\beta(\mathbf{x}) = \mathcal{N}_\beta e^{-\beta E(\mathbf{x})}$ with normalization $\mathcal{N}_\beta^{-1} = \sum_{\mathbf{x}} e^{-\beta E(\mathbf{x})}$. By $\overline{\mathcal{F}} := \{0,1\}^n \setminus \mathcal{F}$ we denote the complement of $\mathcal{F}$. We consider the different values $v\in\mathbb{Z}_+$ the penalty term $E^{(p)}$ can take and decompose $\overline{\mathcal{F}}$ into the preimages of $v \neq 0$ as $\overline{\mathcal{F}} = \bigcup_{v=1}^\infty (E^{(p)})^{-1}(\{v\})$. This observation allows us to use the lower bound $E_{\text{LB}} \leq E^{(o)}(\mathbf{x})$ from step 1 of the algorithm to bound the probability of observing an infeasible solution as

$$
\begin{aligned}
\Pr[\overline{\mathcal{F}}] &= \sum_{x\in\overline{\mathcal{F}}} p_\beta(\mathbf{x}) = \mathcal{N}_\beta \sum_{v=1}^\infty \sum_{\mathbf{x}\in(E^{(p)})^{-1}(\{v\})} e^{-\beta(E^{(o)}(\mathbf{x}) + Mv)} \\
&\leq \mathcal{N}_\beta e^{-\beta E_{\text{LB}}} \sum_{v=1}^\infty e^{-\beta M v} \sum_{\mathbf{x}\in(E^{(p)})^{-1}(\{v\})} 1 \\
&= \mathcal{N}_\beta e^{-\beta E_{\text{LB}}} \sum_{v=1}^\infty e^{-\beta M v} n_{\text{pen}}(v) = c B_{\overline{\mathcal{F}}}(M),
\end{aligned} \tag{6}
$$

where we defined the positive constant $c = \mathcal{N}_\beta e^{-\beta E_{\text{LB}}} > 0$ and $B_{\overline{\mathcal{F}}}(M)$ from step 5.

Next, we show that $B^<_{\mathcal{F}}$ from step 3 is a lower bound on the probability of observing feasible points with low objective. In the limit of $N_s \to \infty$, our estimate for $n_\Delta$ is exact. We divide the relevant energy interval in bins of size $\Delta$, with steps $\Lambda^< = \{0, \Delta, \ldots, \lfloor (E_f - E_{\text{LB}})/\Delta \rfloor \Delta\}$. We denote the set of feasible states in these bins by $b(e) = \{\mathbf{x}\in\mathcal{F} : E^{(o)}(\mathbf{x}) - E_{\text{LB}} \in [e, e + \Delta)\}$, with cardinality $|b(e)| = n_\Delta(e + E_{\text{LB}})$. Since $E^{(p)}(\mathbf{x}) = 0$ for any $\mathbf{x}\in\mathcal{F}$, we can write the probability from Eq. (3) as

$$
\begin{aligned}
p &:= \Pr[\mathcal{F} \cap \{E^{(o)} \leq E_f\}] = \mathcal{N}_\beta \sum_{e\in\Lambda^<} \sum_{\mathbf{x}\in b(e)} e^{-\beta E^{(o)}(\mathbf{x})} \\
&\geq \mathcal{N}_\beta e^{-\beta E_{\text{LB}}} \sum_{e\in\Lambda^<} e^{-\beta(e+\Delta)} n_\Delta(e + E_{\text{LB}}) = c B^<_{\mathcal{F}}.
\end{aligned} \tag{7}
$$

Similarly, for the feasible events with a high objective value, defining $B^>_{\mathcal{F}}$ as in line 4, we ensure that

$$
\begin{aligned}
&\Pr[\mathcal{F} \cap \{E^{(o)} > E_f\}] \\
&= \mathcal{N}_\beta \sum_{e\in\overline{\Lambda^<}} \sum_{\mathbf{x}\in b(e)} e^{-\beta E^{(o)}(\mathbf{x})} \\
&\leq \mathcal{N}_\beta e^{-\beta E_{\text{LB}}} \sum_{e\in\overline{\Lambda^<}} e^{-\beta e} n_\Delta(e + E_{\text{LB}}) = c B^>_{\mathcal{F}}.
\end{aligned} \tag{8}
$$

The events are mutually exclusive and complete. Hence,

$$\Pr[\overline{\mathcal{F}}] + \Pr[\mathcal{F} \cap \{E^{(o)} > E_f\}] + \Pr[\mathcal{F} \cap \{E^{(o)} \leq E_f\}] = 1, \tag{9}$$

which in terms of the bounds (6) and (8) implies that

$$c(B_{\overline{\mathcal{F}}}(M) + B^>_{\mathcal{F}}) \geq 1 - \Pr[\mathcal{F} \cap \{E^{(o)} \leq E_f\}] = 1 - p. \tag{10}$$

If step 6 yields $g$ that has a positive root $M^*$, then

$$
\begin{aligned}
0 &= B_{\overline{\mathcal{F}}}(M^*) + B^>_{\mathcal{F}} - \frac{1-\eta}{\eta} B^<_{\mathcal{F}} \\
&\geq c^{-1}\left(1 - p - \frac{1-\eta}{\eta} p\right) = c^{-1}\left(1 - \frac{p}{\eta}\right),
\end{aligned} \tag{11}
$$

and thus, with $M = M^*$, we have $p \geq \eta$.

Finally, if $g$ has a negative root, then $p \geq \eta$ already holds for $M^* = 0$. $\square$

A few comments on the algorithm are in order:

(i) As we argue in Section E, if no $\eta$-formulation with guaranteed threshold $E_f$ exist, the algorithm returns $\{\}$. In this case, we can choose any permissible $\eta < \eta_{\text{exist}} = (1 + B^>_{\mathcal{F}}/B^<_{\mathcal{F}})^{-1}$ and rerun the algorithm, while ensuring the existence of a solution.

(ii) One can set $E_f = \infty$ (and truncate $\Lambda^<$ at the last energy sampled in step 2) to not require any guarantee on the objective of the solutions. In this regime $B^>_{\mathcal{F}} = 0$ and Theorem 2 continues to hold. The algorithm then effectively targets feasibility-only sampling.

(iii) We numerically observe that in our problem instances, the penalization degeneracy does not grow exponentially, see Section I. Thus, summands with larger $v$ entering $B_{\overline{\mathcal{F}}}$ are eventually exponentially suppressed. This allows one to use a small value for $v_{\text{cut}}$ in practice without introducing an error.

Let us now analyze the run-time and memory complexity of the algorithm in more detail. In particular, we establish in the following that *the algorithm is efficient for problem instances with (i) polynomially bounded entries for $Q$, $A$, and $b$ in the problem specification* (P), *(ii) efficient uniform random sampling from the feasible subspace and (iii) efficient evaluation of $n_{\text{pen}}(v)$.* To control the algorithm's complexity, we impose assumptions on the magnitude of the objective function $E^{(o)}$ and the penalization term $E^{(p)}$. Note, that if $Q_{ij}, A_{ij}, b_j \in \mathcal{O}(1)$ for all $i, j$, then $E^{(o)}(\mathbf{x}) = \mathbf{x}^t Q \mathbf{x} \leq \|Q\| \in \mathcal{O}(n^2)$ for all $\mathbf{x}\in\{0,1\}^n$ and the penalization term $E^{(p)}(\mathbf{x}) = \mathbf{x}^t A^t A \mathbf{x} + 2\mathbf{x}^t A^t b + b^t b$ with $m$ constraints scales as $\mathcal{O}(mn^2)$ dominated by its first summand. The examples in our work (MNSP, TSP and PO) indeed all have entries in $A$ and $b$ of constant magnitude independent of the system size. More generally, we also directly conclude that if the entries of $Q$, $A$, and $b$ grow at most polynomially with the system size, $E^{(o)} \in \mathcal{O}(\text{poly}(n))$ and $E^{(p)} \in \mathcal{O}(\text{poly}(n, m))$.

The maximum penalization value $v_{\max} = \max_\mathbf{x} E^{(p)}(\mathbf{x})$ will thus scale like $mn^2$ for the benchmarked problems and other bounded-entries similar problems, or will be in $\text{poly}(m, n)$ in general.

Let us discuss each step of Algorithm 1:

The SDP in *Step 1* generally takes $O(n^6)$ time and $O(n^4)$ memory complexity [46]. Considerable speed-ups can potentially be achieved using sketching techniques [47].

For *Step 2* to be efficient, we need to choose $N_s$ to be at most polynomially in $m, n$. This will, in turn, introduce a statistical error in the estimation of $n_\Delta$ and, thus, $B^>_{\mathcal{F}}$ and $B^<_{\mathcal{F}}$. If we choose the parameter $\Delta$ sufficiently large, i.e. the discretization sufficiently coarse, the statistical error is controlled. More precisely, extending Theorem 2, we show in Section A that with probability $1 - \delta$ Algorithm 1 yields an $(\eta - \epsilon)$-reformulation provided that $N_s \geq 2/(\epsilon\delta)^2$ and $\Delta \in \mathcal{O}(\text{poly}(n, m) + \beta^{-1}n)$. We refer to the appendix for more details. Obtaining a single uniform sample from the feasible subspace is efficient for many problems. In particular, for TSP, MNPP and PO it takes $\mathcal{O}(n)$, $\mathcal{O}(n)$ and $\mathcal{O}(n^2)$ time, respectively ($\mathcal{O}(n_v^2)$, $\mathcal{O}(N + P)$ and $\mathcal{O}(N^2)$, in the individual problem parameters, see Section B). In all three cases, the memory requirements are of the same order or smaller than the corresponding time complexity. Thus, for these instances and $\beta$ inverse polynomially in the system size $n$, Step 2 is efficient.

When the objective function is polynomially bounded and $\Delta \in \mathcal{O}(\text{poly}(n, m))$, also the cardinality of the lattice $\Lambda$ is at most polynomial. Thus, the summations in *Steps 3 and 4* are efficient.

*Step 5* computes the penalization degeneracy. Even setting $v_{\text{cut}} \to \infty$, this involves evaluating $n_{\text{pen}}(v)$ for $v \in \{1, \ldots, v_{\max} = \max_\mathbf{x} E^{(p)}(\mathbf{x})\}$. For $Q$, $A$, and $b$ with polynomially bounded entries in $n, m$, we compute $n_{\text{pen}}$ for polynomially many arguments. For instances where a single evaluation of $n_{\text{pen}}$ is efficient, the step is, thus, overall efficient.

*Step 5* is efficient under the same assumption as Step 5.

*Step 7* requires constant evaluation of $B_{\overline{\mathcal{F}}}$ (Step 5) to determine an integer approximation to a root of $g$ [48].

Thus, we conclude that under assumptions that are often met by problems under consideration, one can choose the parameters of the algorithm such that it is efficient and guaranteed to yield the targeted reformulation. In particular, for MNPP, TSP, and PO, we have $O(1)$ entries of $A$ and $b$ and $v_{\max}$ will scale like $mn^2$, which simplifies the overall complexity analysis.

Putting everything together and under reasonable assumptions, the dominant contributions to the total computational cost arise from the SDP relaxation, scaling as $\mathcal{O}(n^6)$ and from uniformly sampling the feasible subspace ($\mathcal{O}(N_s n^2) = \mathcal{O}(\epsilon^{-2} n^2)$). Since, for a fixed target success probability $\eta$, the precision parameter $\epsilon$ can be treated as a constant, the overall complexity is polynomial in the system size $n$ and ultimately dominated by the $\mathcal{O}(n^6)$ cost of the SDP relaxation. Finally, note that a trivial lower bound exists ($E_{\text{LB}} = 0$) and thus does not require explicit computation.

Note that generally speaking, we are here trading computational effort with the tightness of the bounds on the events and, thus, the degree of approximation of the optimal value of $M$.

Further results concerning the algorithm are presented in the appendix. In particular, a numerically robust modification of the algorithm is described in Section F, a brief study of the output $M^*$ dependence on the hyperparameters $E_f$ and $v_{\text{cut}}$ is reported in Section G, and the applicability of the algorithm to the inverse problem of determining an appropriate solver temperature $\beta$ for a fixed penalty weight $M$ is detailed in Section H.

**Figure 3.** Effective success probability $\eta_{\text{eff}}$ of an ideal Gibbs sampler (top rows) and simulated annealing (SA) (bottom rows) for sampling feasible points, using a QUBO reformulation with penalization weight $M^*$ calculated by Alg. 1 for different constrained optimization problems (columns, see Section B for details) and system sizes. For each solver, in the first row we only require feasibility ($E_f = \infty$), while for the second row we further require solutions with objective smaller than a finite, problem-dependent $E_f$. Different colors denote target success probabilities $\eta \in 0.25, 0.5, 0.75$, with horizontal reference lines at these values. Marker shapes indicate sampler temperature $T = \beta^{-1}$. For SA, temperatures are obtained by rescaling Digital Annealer schedules as $T = \phi T_{\text{DA}}$, with $\phi \in 1, 10, 100$; for PO, schedules are approximated using instances of the same size from other benchmarks. Solid lines and markers show averages over 100 (ideal Gibbs sampler) or 4 (SA) instances, with shaded standard deviation; circle TSP and benchmark TSP only define a single instance per system size. Per instance, $10^3$ (ideal Gibbs) or 128 (SA) samples are drawn. PO uses $10^5$. We generally observe that $\eta_{\text{eff}}$ is larger than $\eta$ showing that Alg. 1 yields admissible $\eta$-reformulations. For finite $E_f$, some combinations of $T$, $\eta$, and $E_f$ make the target $\eta$ unattainable (see Section E); in these cases, $\eta$ is reduced. Such instances are indicated in the optimality-focused MNPP panels (bottom left) by short horizontal bars marking the reduced target below the achieved $\eta_{\text{eff}}$.

### C. Validation and numerical benchmarks

We benchmark the proposed strategy on three classes of constrained problems: Traveling Salesman Problem (TSP), Multiway Number Partitioning Problem (MNPP) and Portfolio Optimization (PO). Complete formulations of these optimization problems are given in Section B. The problems capture distinct structures of sets of feasible points. As solvers we use an ideal Gibbs sampler, a simulated annealing algorithm, and the Digital Annealer. All instances are tested following the same scheme: Algorithm 1 is used to determine the penalization constant $M$ for $\eta \in \{0.25, 0.5, 0.75\}$ and for three different target temperatures (except for the DA, operating at a single, automatically selected temperature). We choose $E_f$ such that it is not impeding the success probability -- i.e., so that $\eta_{\text{exist}}$ does not become small and render the tests uninformative (see Section E). We set $E_f = \alpha n^2$, where $n$ is the number of bits in the instance and choose $\alpha$ accordingly or we set $E_f = \infty$, only enforcing feasibility. From multiple runs of the solvers we then estimate the effective success probability $\eta_{\text{eff}}$, i.e. the fraction of observed feasible solutions with energy smaller than $E_f$, per problem class and system size.

In Fig. 3 top rows, we display the effective success probability for an ideal Gibbs sampler and different choices of $E_f$, respectively. We observe that, with one exception, $\eta_{\text{eff}}$ is consistently above the desired threshold. The ideal Gibbs sampler exactly fulfills the assumptions underlying our method development. Its output distribution is fully characterized by a known inverse temperature $\beta$ used to determine $M$. The gap between $\eta_{\text{eff}}$ and $\eta$ for MNPP and TSP, thus, indicates that the bounds evaluate in Algorithm 1 are not tight. For PO, in contrast, we observe that $\eta_{\text{eff}}$ is indeed very close to $\eta$.

For MNPP with $E_f = \alpha n^2$, we encounter the only exception where $\eta_{\text{eff}} < \eta \in \{0.5, 0.75\}$ for $T = \beta^{-1} = 10^6$ and small system sizes (Fig. 3 second row, first plot, squares). Here, it is indeed impossible to sample feasible solutions *below* the specified target energy $E_f$ with sufficient probability (see Section E for details). The algorithm terminated with $\{\}$ and the points were obtained re-running the algorithm with an $\eta < \eta_{\text{exist}}$. The updated $\eta$ is shown as the horizontal bar. We observe that $\eta_{\text{eff}}$ is consistently above this threshold, confirming the robustness of the algorithm also in this setting.

The lower two rows of Fig. 3 show the effective success probability $\eta_{\text{eff}}$ for simulated annealing. The simulated annealing uses the same temperature schedule as the Digital Annealer, when available; for PO, the schedule from other instances of the same size was used. We mostly observe comparable results to the Gibbs sampler. For high temperatures $\eta_{\text{eff}}$ is found slightly below for TSP and PO. The solver is not guaranteed to have converged to a stationary Gibbs distribution at the end of the annealing and potentially deviates from our idealized assumptions underlying our method. Nonetheless, our algorithm determines values of $M$ with a comparable success probability $\eta_{\text{eff}}$ to the targeted one in this setting.

For DA (version 3) we find that $\eta_{\text{eff}}$ is consistently higher than the targeted $\eta$ in all settings, Fig. 4. Moreover, all $\eta_{\text{eff}}$ quickly converges to 1 in the system sizes. This indicates that our methods overestimate $M$ for larger system sizes. We have already seen in Fig. 2 that for large systems a slight overestimation of $M$ yields quickly to nearly only observing feasible solutions. The output distribution of the DA is only qualitatively approximated by a Gibbs distribution with inverse temperature $\beta$ determined in the annealing schedule. Our results show the DA is further biased towards low-objective values than the Gibbs distribution. Our methods determines pratical values for $M$ for Fujitsu's Digital Annealer Unit on instances with over thousand variables ensuring reliable performance of the solver.

A common approach in practice is to perform a brute-force search for a suitable value for $M$, e.g. using binary search. Starting from an over-estimated value for $M$, the penalization is iteratively halved and the problem is solved until an unacceptable number of unfeasible solutions start appearing. This method traverses the search space exponentially fast. The overall cost of the method, however, depend on the complexity of the individual solver calls. Depending on the solver, its hardware platform and the problem sizes, the costs can be prohibitive already for a small number of iterations. This still motivates using a good estimate for $M$ as the initial value of the binary search, as provided by our method developed here. So the practical benefit of the method can be quantified as the number of solver calls that are 'saved' when initializing binary search using Algorithm 1 instead of with a more direct upper bound. As we show in Section D, a simple efficiently computable $M$ yielding an $\eta$-reformulation of a Gibbs sampler at inverse temperature $\beta$ is given by

$$M_{\ell_1}(\beta) = \beta^{-1}(n\ln 2 - \ln(1-\eta)) + \|Q\|_{\ell_1}. \tag{12}$$

Note that this definition makes use of the direct upper bound $\|Q\|_{\ell_1}$ on the objective function that is often used to estimate $M$ for an exact solver. The number of 'saved' solver calls is, thus, computed as $\log_2(M_{\ell_1}/M^*)$ and depicted for the benchmarking instances in Fig. 5. We observe that across all temperatures studied, our algorithm results in reductions of the number of solver calls, often reducing the runtime by factors of 10 or more. This shows that our method can yield practical advantages in the time to solution.

**Figure 4.** Effective success probability $\eta_{\text{eff}}$ of the Fujitsu Digital Annealer (version 3) as a function of the system size using penalizations weigths $M^*$ determined by Alg. 1. Structure of the figure is identical to Fig. 3 and refer to its captions for details. The temperatures of the annealing process here have been automatically selected internally in the Digital Annealer. For MNPP, solid lines and markers are averages over 4 instances, with shaded standard deviation. For TSP and circle TSP only one instance was considered per system size. For each instance, 512 solutions were sampled for all problems.

**Figure 5.** Multiplicative speedup compared to binary search from direct bound, computed as $\log_2(M_{\ell_1}/M^*)$, as a function of the system size for the different benchmarked problems. Here $M^*$ is the output of Alg. 1 and $M_{\ell_1}$ is a direct bound for $M$ (see Theorem 5). Colors indicate different target probabilities $\eta_r \in \{0.25, 0.5, 0.75\}$, and marker shapes different temperatures $T = \beta^{-1}$. For MNPP, random TSP and PO, lines and markers are averages over 10 instances and the standard deviation is shaded. Circle TSP defines one instance per system size. As shown in Fig. 2, directly using $M_{\ell_1}$ substantially degrades the solution quality. A binary search reducing $M_{\ell_1}$ to $M^*$ requires iterations $\log_2(M_{\ell_1}/M^*)$ with repeated calls to the QUBO solver. Thus, the advantage of using $M^*$ is a reduction in overhead proportional to this factor.

## DISCUSSION

We introduced an efficient algorithm to determine the penalization weight in unconstrained reformulations of constrained optimization problems, specifically tailored for approximate solvers that are qualitatively similar to Gibbs samplers. More precisely, given a Gibbs sampler at an arbitrary inverse temperature, our algorithm returns a penalization weight such that the solver outputs feasible solutions with objective value below a threshold with a controllable, guaranteed minimum probability. We also demonstrate the practical applicability of our technique beyond exact Gibbs sampling in numerically tests with a simulated annealing algorithm and Fujitsu's Digital Annealer (version 3), for different constrained problem classes and system sizes up to 4098 bits. We show that, using our algorithm, one can reduce the time to solution on the solver by an order of magnitude compared to strategies based on binary search for a penalization weight.

Our algorithm for addressing the big-$M$ problem improves on state-of-the-art general heuristics for penalization constants. It provides a tool to precisely set the penalization constant so as to control the probability of success, using knowledge of the problem structure and the solver's statistical behavior. To this end, we trade resources in the pre-processing for potentially crucial reductions in the solver's runtime. Such practical methods for addressing the big-$M$ problem are also especially relevant for quantum solvers, e.g. quantum annealers [25-28] or QAOA [29, 30, 49, 50], which typically operate on unconstrained problem formulations. Akin to custom hardware solvers as the Fujitsu's Digital Annealer (version 3), classical computational power for the pre-processing is abundant compared to the resource costs of the quantum solver. Interestingly, recent work started establishing connections between quantum solvers and Gibbs samplers [49-52]. This work can serve as a starting point for extending our method to quantum solvers in future work, complementing existing approaches [53-60].

## ACKNOWLEDGEMENTS

M. Krispin and M. Kliesch are funded by the Hamburg Quantum Computing project, which is co-financed by the ERDF of the European Union and the Fonds of the Hamburg Ministry of Science, Research, Equalities and Districts (BWFGB); and by the Fujitsu Germany GmbH and Dataport as part of the endowed professorship "Quantum Inspired and Quantum Optimization."

## Appendix A: Extended theoretical guarantee for the algorithm

Theorem 2 establishes that the proposed algorithm returns a value $M^*$ that ensures an $\eta$-reformulation, Eq. (3) using infinite samples $N_s \to \infty$. We here establish that using an inverse polynomial number of samples in the error controls the finite sample error to the bound of the success probability. Let $S = \{\mathbf{x}_1, \ldots, \mathbf{x}_{N_s}\}$ be a set of $N_s$ samples drawn uniformly from the feasible subspace $\mathcal{F}$. We define the empirical estimator $\hat{n}_\Delta(e) = |\{\mathbf{x}\in S : e \leq E^{(o)}(\mathbf{x}) < e + \Delta\}| \frac{|\mathcal{F}|}{N_s}$, where $|\mathcal{F}| = n_{\text{pen}}(0)$ denotes the number of feasible points. For structured problems, $|\mathcal{F}|$ can often be computed analytically (see Section I). We begin by quantifying the statistical error incurred in replacing $n_\Delta$ with $\hat{n}_\Delta$ in the following lemma. We then show $N_s = \mathcal{O}(\epsilon^{-2})$ is sufficient to guarantee an $(\eta - \epsilon)$-reformulation. We conclude with a discussion of the scaling of $\Delta$.

**Lemma 3.** *Let $\hat{n}_\Delta(e)$ be the estimation of $n_\Delta(e)$ from $N_s$ uniform samples from $|\mathcal{F}|$. Then*

$$\mathbb{E}[\|\hat{n}_\Delta - n_\Delta\|_{\ell_2}] \leq \frac{|\mathcal{F}|}{\sqrt{N_s}}. \tag{A1}$$

*Proof.* The feasible spectral weight $n_\Delta(e)$ is estimated by drawing $N_s$ i.i.d. samples $\mathbf{x}$ uniformly at random from $\mathcal{F}$ and counting the frequency of observing $E^{(o)}(\mathbf{x}) \in [e, e + \Delta)$. Thus, the vector-valued random variable $X$ counting the frequencies is multinomially distributed with probability $p_\Delta(e) = n_\Delta(e)/|\mathcal{F}|$. The empirical estimator $\hat{p}_\Delta = X/N_s$ has expected error

$$\mathbb{E}[\|\hat{p}_\Delta - p_\Delta\|_{\ell_2}^2] = \frac{1}{N_s^2}\mathbb{E}[\|X - \mathbb{E}[X]\|_{\ell_2}^2] = \frac{1}{N_s^2}\sum_k \text{Var}[X_k] = \frac{1 - \|p_\Delta\|_{\ell_2}^2}{N_s} \leq \frac{1}{N_s}, \tag{A2}$$

where $X_k$ is the $k$-th component of $X$, counting the frequency of the $k$-th bin. Hence, by Jensen's inequality $\mathbb{E}[\|\hat{p}_\Delta - p_\Delta\|_{\ell_2}] \leq 1/\sqrt{N_s}$. By definition, the error on $n_\Delta$ is larger by a factor of $|\mathcal{F}|$. $\square$

Let's denote by $\hat{B}^<_{\mathcal{F}}$ the estimate of $B^<_{\mathcal{F}}$ using $\hat{n}_\Delta$ instead of $n_\Delta$. We can control the error as

$$
\begin{aligned}
|\hat{B}^<_{\mathcal{F}} - B^<_{\mathcal{F}}| &\leq \sum_{e\in\Lambda^<} e^{-\beta(e+\Delta)} |\hat{n}_\Delta(e + E_{\text{LB}}) - n_\Delta(e + E_{\text{LB}})| \\
&\leq e^{-\beta\Delta}\sqrt{\frac{2|\mathcal{F}|^2}{N_s}}\delta^{-1}
\end{aligned} \tag{A3}
$$

where we have used Cauchy-Schwarz's inequality, the fact that $\|\hat{n}_\Delta - n_\Delta\|_{\ell_2} \leq \mathbb{E}[\|\hat{n}_\Delta - n_\Delta\|_{\ell_2}]/\delta$ with probability at least $(1 - \delta)$ from Markov inequality, and that

$$\sum_{e\in\Lambda^<} e^{-2\beta e} = \sum_{k=0}^{\lfloor (E_f - E_{\text{LB}})/\Delta \rfloor} e^{-2k\beta\Delta} = \frac{1 - e^{-2\beta\Delta\lfloor (E_f - E_{\text{LB}})/\Delta \rfloor}}{1 - e^{-2\beta\Delta}} \leq 2, \tag{A4}$$

for $\beta\Delta \geq \log(2)/2$. Recalling that we defined $c = \mathcal{N}_\beta e^{-\beta E_{\text{LB}}} > 0$, for $\beta\Delta \geq \log(|\mathcal{F}|) + \log(c) \geq \log(2)/2$, we, thus, have that, with probability at least $(1 - \delta)$, it holds

$$|\hat{B}^<_{\mathcal{F}} - B^<_{\mathcal{F}}| \leq \sqrt{\frac{2}{N_s}}(c\delta)^{-1}. \tag{A5}$$

Analogously, also for the bound on high-energy feasible states we have:

$$|\hat{B}^>_{\mathcal{F}} - B^>_{\mathcal{F}}| \leq \sqrt{\frac{2}{N_s}}(c\delta)^{-1}. \tag{A6}$$

Thus, we arrive at the following theorem.

**Theorem 4.** *Let $\beta\Delta \geq \log(|\mathcal{F}|) + \log(c) \geq \log(2)/2$. For $\epsilon > 0$ and $\delta \geq 0$, suppose that*

$$N_s \geq \frac{2}{\epsilon^2\delta^2}, \tag{A7}$$

*then, with probability at least $1 - \delta$, we have $p = \Pr[\{x\in\mathcal{F} \mid E(x) \leq E_f\}] \geq \eta - \epsilon$.*

*Proof.* Analogously to Eq. (11), since the algorithm uses the approximated bounds $\hat{B}^<_{\mathcal{F}}$ and $\hat{B}^>_{\mathcal{F}}$ to find a root $M^*$, we have

$$0 = B_{\overline{\mathcal{F}}}(M^*) + \hat{B}^>_{\mathcal{F}} - \frac{1-\eta}{\eta} \hat{B}^<_{\mathcal{F}}. \tag{A8}$$

Given that $|\hat{B}^<_{\mathcal{F}} - B^<_{\mathcal{F}}| \leq \sqrt{\frac{2}{N_s}}(c\delta)^{-1}$ and $|\hat{B}^>_{\mathcal{F}} - B^>_{\mathcal{F}}| \leq \sqrt{\frac{2}{N_s}}(c\delta)^{-1}$ under the theorem assumptions, we have

$$
\begin{aligned}
0 &\geq B_{\overline{\mathcal{F}}}(M^*) + B^>_{\mathcal{F}} - \sqrt{\frac{2}{N_s}}(c\delta)^{-1} - \frac{1-\eta}{\eta}\left(B^<_{\mathcal{F}} + \sqrt{\frac{2}{N_s}}(c\delta)^{-1}\right) \tag{A9} \\
&= B_{\overline{\mathcal{F}}}(M^*) + B^>_{\mathcal{F}} - \frac{1-\eta}{\eta}B^<_{\mathcal{F}} - (c\delta\eta)^{-1}\sqrt{\frac{2}{N_s}} \tag{A10} \\
&\geq c^{-1}\left(1 - \frac{p}{\eta}\right) - (c\delta\eta)^{-1}\sqrt{\frac{2}{N_s}} = c^{-1}\left(1 - \frac{p + \delta^{-1}\sqrt{2/N_s}}{\eta}\right). \tag{A11}
\end{aligned}
$$

where we used the inequalities (7), (10). Since by definition $c > 0$, we have $p \geq \eta - \delta^{-1}\sqrt{\frac{2}{N_s}}$. Thus, taking $N_s \geq \frac{2}{\beta^2 \epsilon^2}$ ensures $p \geq \eta - \epsilon$ with probability at least $(1 - \delta)$. $\square$

Notice that choosing a small value for $\Delta$ makes the bound $B^<_{\mathcal{F}}$ tighter, thereby yielding an estimate $M^*$ closer to the optimal penalty $M$. However, as required by the theorem's assumption, $\Delta$ must be sufficiently large to control the deviation between the bound and its empirical approximation $|\hat{B}^<_{\mathcal{F}} - B^<_{\mathcal{F}}|$. To quantify this requirement, first note that $\log(|\mathcal{F}|) \leq \log(2^n) \in \mathcal{O}(n)$. Moreover, $\log(c) = -\beta E_{\text{LB}} - \log(\sum_{\mathbf{x}} e^{-\beta E(\mathbf{x})})$. Using the bound $\sum_{\mathbf{x}} e^{-\beta E(\mathbf{x})} \geq 2^n e^{-\beta E_{\max}}$, where $E_{\max}$ is the maximal energy (or an upper bound for that), we obtain $\log(c) \leq -\beta E_{\text{LB}} + \beta E_{\max} - \log(2^n)$. In general, this scales as $\mathcal{O}(\beta \, \text{poly}(n, m) + n)$, and as $\mathcal{O}(\beta mn^2 + n)$ when the entries of the problem matrices are bounded by constants (see the complexity discussion in Sec. B). Since the theorem requires $\beta\Delta \geq \log(|\mathcal{F}|) + \log(c)$, it follows that choosing $\Delta \in \Omega(\text{poly}(n, m) + \beta^{-1}n)$ is sufficient to ensure the theorem's guarantee. For instances with bounded-entries, it suffices to take $\Delta \in \Omega(mn^2 + \beta^{-1}n)$.

## Appendix B: Benchmarking problems

In the present section, we discuss the benchmarked optimization problems and their QUBO formulations.

### 1. MNPP

The Number Partitioning Problem (NPP), an NP-hard combinatorial problem, aims at partitioning a set of numbers into two subsets as evenly as possible. The Multiway Number Partitioning Problem (MNPP) is a generalization of this, with multiple subsets to partition the elements into. Its applications range from distributed networking and computing, to gerrymandering and investment portfolio [61].

More formally, given a set $S$ of $N$ positive elements $S = \{c_1, \ldots, c_N\}$, the goal is to partition of $S$ into $P$ disjoint subsets $R_1, \ldots, R_P$, such that the sums of values in each subset are as close to each other as possible. This problem can be stated as follows: can a set of $N$ assets with values $c_1, \ldots, c_N$ fairly be distributed between $P$ parties? To model the problem in an optimization context [62], we define the $NP$ binary decision variables $\{x_{i,p}\}_{i\in\{1,\ldots,N\}, p\in\{1,\ldots,P\}} \in \{0,1\}^{NP}$, assigning each element $c_i$ in $S$ to a subset $R_p$, defined so that

$$x_{i,p} = \begin{cases} 1 & \text{if } c_i \in R_p \\ 0 & \text{otherwise} \end{cases}. \tag{B1}$$

The constraints will encode the fact that each element can only be assigned to one subset, that is, the decision matrix $[x]_{i,p}$ is a right-stochastic matrix: $\sum_{p=1}^P x_{i,p} = 1 \; \forall i$. The objective function can be stated in different ways [63]; we will consider

$$E^{(o)}(x) = \sum_{p=1}^P \left(\sum_{i=1}^N c_i x_{i,p} - \frac{1}{P}\sum_{i=1}^N c_i\right)^2 \tag{B2}$$

that sums the squared errors of the subsets sums with respect to a perfectly even distribution of $\frac{1}{P}\sum_{i=1}^N c_i$ per subset (scaled variance of the subset sums).

The QUBO model can be formulated in the following way:

$$\min_{x\in\{0,1\}^{NP}} E^{(o)}(x) + M\sum_{i=1}^N \left(1 - \sum_{p=1}^P x_{i,p}\right)^2, \tag{B3}$$

In the benchmarks considered in this work, the numbers $c_i$ to be partitioned were randomly generated from a uniform distribution over the interval $[0, 10^3]$. For small-scale tests involving the Gibbs sampler, the number of partitions was fixed to $P = 3$, while only the system size $N$ was increased. Conversely, for the larger-scale tests with the SA and DA solvers, both $N$ and $P$ were increased with system size, maintaining the relation $N = 8P$. This choice ensured that the average number of integers per partition remained constant as the system grew, preventing the problem from becoming artificially easier and avoiding an overabundance of optimal solutions [64].

### 2. TSP

The Traveling Salesman Problem is a cornerstone of optimization problems, it is a NP-hard problem highly relevant both in theoretical computer science and for practical applications, such as logistics, circuit design, telecommunications [65]. Given a connected graph $G = (V, E)$ with $n_v = |V|$ vertices, where each edge $e_{i,j}$ represents the cost of traveling from node $i$ to node $j$, the goal is to find the cheapest Hamiltonian cycle, i.e. the path that visits all the nodes in the graph, minimizing the overall total travel cost. The combinatorial problem can be encoded via the $n_v^2$ binary decision variables $\{x_{t,i}\}_{t,i=1,\ldots,n_v} \in \{0,1\}^{n_v^2}$, ordering the temporal visit of each city [62], defined so that

$$x_{t,i} = \begin{cases} 1 & \text{if city } i \text{ is visited at time step } t \\ 0 & \text{otherwise.} \end{cases} \tag{B4}$$

The constraints of the optimization problem enforce the decision matrix $[x]_{t,i}$ to be a permutation matrix, that is $\sum_{i=1}^{n_v} x_{t,i} = 1 \; \forall t$ and $\sum_{t=1}^{n_v} x_{t,i} = 1 \; \forall i$. The objective function to minimize incorporates the cost (given by the sum of the edge weights) of a path represented by a particular realization of the decision matrix [62]

$$E^{(o)}(x) = \sum_{t=1}^{n_v} \sum_{i\neq j=1}^{n_v} e_{i,j} x_{t,i} x_{t+1,j}. \tag{B5}$$

The QUBO model is then formulated in the following way:

$$\min_{x\in\{0,1\}^{n_v^2}} E^{(o)}(x) + M\left[\sum_{i=1}^{n_v}\left(1 - \sum_{t=1}^{n_v} x_{t,i}\right)^2 + \sum_{t=1}^{n_v}\left(1 - \sum_{i=1}^{n_v} x_{t,i}\right)^2\right]. \tag{B6}$$

In the present work, multiple sets of TSP benchmarks are used or generated. The first, referred to as the *circle TSP* in the plots, consists of $n_v$ nodes deterministically positioned at equal distances along a circle of radius $10^6$. The second set, called the *random TSP*, contains instances where nodes are randomly placed within a square of side length $2 \times 10^6$, while the third set, named the *benchmark TSP*, includes instances obtained from the standard benchmark library [40].

### 3. PO

For Portfolio Optimization we use the well-known Markovitz model [66-68], i.e. the problem of selecting a set of assets maximizing returns while minimizing risk. The problem specification requires a vector $\boldsymbol{\mu}$ of expected returns of a set of $N$ assets, their covariance matrix $\Sigma$, a risk aversion $\gamma > 0$, and a partition number $w$ defining the portfolio discretization. Denoting by $x_i$ the units of asset $i$ in the portfolio, the problem formulation reads

$$\min_{\mathbf{x}\in\mathbb{N}^N} -\boldsymbol{\mu}^t\mathbf{x} + \gamma \mathbf{x}^T\Sigma\mathbf{x} \quad \text{subject to} \quad \sum_{i=1}^N x_i = 2^w - 1. \tag{B7}$$

The constraint forces the budget to be totally invested. The QUBO reduction requires mapping each integer decision variable into $w$ binary variables. We generate problem instances from historic financial data on S&P 500 stocks.

In what follows, we illustrate how the data used in Portfolio Optimization instances were fetched from real data and adapted to Markowitz formulation (B7). From stock market index S&P500, we downloaded the stock price history, referring to the 2 years period December 2020 until November 2022 with one-month interval, of 121 out of the 500 company stocks tracked by S&P500 (namely, the ones with no missing data in said intervals). Let us call $P_{t,a}$ such cost of an asset $a$, with time index $t$. The return at time step $t$ is defined as

$$r_{t,a} = \frac{P_{t,a} - P_{t-1,a}}{P_{t-1,a}} \tag{B8}$$

from which the expected return vector $\tilde{\boldsymbol{\mu}}$ and the covariance matrix $\tilde{\Sigma}$ can be computed as $\tilde{\mu}_a = \frac{1}{T}\sum_{t=1}^T r_{t,a}$ and $\tilde{\Sigma}_{a,b} = \frac{1}{T-1}\sum_{t=1}^T (r_{t,a} - \mu_a)(r_{t,b} - \mu_b)$. We encode the real financial stock market data with decimal precision of $10^{-4}$.

Another parameter of the generated instances is the partition number $w$ [67], that describes the granularity of the portfolio discretization, since the budget is divided in $2^w - 1$ equally large chunks. Each asset decision variable $x_i$ is an integer that can take values from 0 up to $2^w - 1$, indicating how many of these partitions to allocate towards asset $i$. This explains why the constraint $\sum_i x_i = 2^w - 1$ enforces the budget to be totally invested. As a consequence, $w$ is also equal to the number of bits one needs to allocate for every integer and, by extension, asset.

Notice that $\tilde{\boldsymbol{\mu}}^t \boldsymbol{p}$ is the expected return of a portfolio if $\boldsymbol{p}$ represents the vector of the *portions* of the portfolio for each asset, i.e. $0 \leq p_i \leq 1$ and $\sum_i p_i = 1$. In order to have integer decision variables, the number of chunks $x_i = (2^w - 1)p_i$ is used, and in the final formulation (B7) the factors are absorbed in the objective function, defining $\boldsymbol{\mu} = \tilde{\boldsymbol{\mu}}/(2^w - 1)$ and $\Sigma = \tilde{\Sigma}/(2^w - 1)^2$.

The last parameter that one needs to set to fully specify the instance is the risk aversion factor $\gamma$, weighting differently the return and the volatility in the objective function. Common values of the risk aversion factor are $\gamma = 0.5, 1, 2$.

The parameter values used in the instances tested in this work are $\gamma = 1$ and $w = 3$ (5) for the small- (large-) scale tests employing the Gibbs (SA and DA) solvers, respectively, yielding a portfolio granularity of 7 (31) equal chunks.

## Appendix C: Details on the algorithm subroutines

This section elaborates on the subroutines that constitute Algorithm 1.

In line 5, we take as input the penalization function $E^{(p)}$ of the problem under consideration and the violation threshold $v_{\text{cut}}$, which sets the maximum penalization value considered. For the constrained problems analyzed in this work, the penalization degeneracies values $n_{\text{pen}}(v)$ were analytically derived in Section I from the structure of $E^{(p)}$. Using these expressions, one can directly compute the vector of degeneracies up to $v_{\text{cut}}$. For more general problems not considered here, where analytical degeneracies are unavailable, one can instead estimate the penalization degeneracies by evaluating the penalization energies of uniformly sampled bitstrings followed by a fitting procedure.

Line 1 computes a lower bound of the objective function $E_{\text{LB}} \leq \min_{\mathbf{x}\in\{0,1\}^n} E^{(o)}(\mathbf{x})$. In principle, any valid method to compute such a lower bound can be employed; the tighter the bound, the better the algorithm's performance. In this work, we use a Semi-definite Programming (SDP) relaxation for the PO case, where an analytical lower bound is not evident, while we set $E_{\text{LB}} = 0$ for the other cases, TSP and MNPP, where this value is an obvious bound (in particular, for TSP, where $\min_{\mathbf{x}\in\{0,1\}^n} E^{(o)}(\mathbf{x}) = 0$). The SDP relaxation consists of optimizing over the cone of semi-definite matrices intersected with linear constraints. Specifically, to lower bound $E^{(o)}(\mathbf{x}) = \mathbf{x}^t Q \mathbf{x} + L^t\mathbf{x}$, an SDP relaxation is formulated as

$$E_{\text{LB}} := \min_Y \text{Tr}\{Y^t\tilde{Q}\} \tag{C1}$$

$$\text{s.t. } Y \geq 0 \tag{C2}$$

$$Y_{1i} = Y_{ii} \quad \forall i = 2, \ldots, n+1 \tag{C3}$$

$$Y_{11} = 1, \tag{C4}$$

where $Y$ is a $(n+1)\times(n+1)$ real positive semidefinite matrix, $\text{Tr}\{A^t B\} = \langle A, B\rangle = \sum_{ij} A_{ij}B_{ij}$ denotes the inner product between matrices and the matrix $\tilde{Q}$ is given by

$$\tilde{Q} = \begin{bmatrix} 0 & \frac{1}{2}L^t \\ \frac{1}{2}L & Q \end{bmatrix}. \tag{C5}$$

For further details on the derivation, see Ref. [39], Appendix B.

In line 2, we compute a pre-defined number $N_s$ of objective energy values $\{E_i\}_{i=1}^{N_s}$ of feasible bitstrings uniformly drawn from $\mathcal{F}$ and approximate the feasible spectral weights Eq. (5). For a general constrained problem with constraints of the form $A\mathbf{x} = b$, uniformly sampling feasible bitstrings is generally computationally challenging [69, 70]. Nevertheless, for structured problems, efficient strategies can often be devised [71, 72]. In the present work, such strategies were implemented depending on the specific problem structure. For MNPP, each feasible configuration corresponds to an assignment of all $N$ items into $P$ partitions, yielding $P^N$ possible solutions. Uniform sampling is achieved by independently assigning each item $i$ to a random partition $p(i) \in 1, \ldots, P$ and setting $\mathbf{x}_{i,p(i)} = 1$ (and 0 otherwise). For TSP, a feasible bitstring represents a Hamiltonian cycle, which can be uniformly generated by sampling a random permutation $\sigma$ of $1, \ldots, n_v$ and setting $\mathbf{x}_{\sigma(i),i} = 1$ (and 0 otherwise). For PO, each valid portfolio corresponds to one of the $\binom{2^w + N - 2}{N - 1}$ ways of distributing $2^w - 1$ indistinguishable units among $N$ assets. After generating $N_s$ uniform samples, associated objective energies are computed. From this, the computation of $n_\Delta(e)$ follows from the definition Eq. (5).

Steps 5, 3 and 4 use the computed $n_\Delta(e)$ and $n_{\text{pen}}(v)$ to evaluate, up to a common factor, the probability bounds for three classes of configurations: infeasible states, feasible states with low objective energy, and feasible states with high objective energy.

Finally, in step 7, the numerical root-finding of $g$ is straightforward, enabled by the function's favorable analytical properties.

## Appendix D: Direct estimation of penalization weights

In order to establish a baseline for our algorithm, we here develop a strategy for determining $M$ based on standard, simple bounds of the objective function to the case of Gibbs samplers. This strategy captures typical initial considerations of practitioneers when determining values of $M$ using binary search. We provide a simple efficient formula for a penalty weight $M$ that yields an $\eta$-reformulations for an exact Gibbs solver at known temperature. The penalty weight is the sum of two terms: First, the penalty weight that is widely used [35-37] and sufficient for an exact Gibbs solver, i.e. a Gibbs solver at inverse temperature $\beta = \infty$. Second, a thermal correction proportional to the temperature of the solver:

$$M_{\ell_1}(\beta) = \beta^{-1}(n\ln 2 - \ln(1-\eta)) + \|Q\|_{\ell_1} \tag{D1}$$

The expression is motivated by the following guarantee:

**Lemma 5.** *For a constrained problem* (P) *of size $n$ and objective function $E^{(o)}(\mathbf{x}) = \mathbf{x}^t Q \mathbf{x}$ a penalty weight $M_{\ell_1}(\beta)$ defined in* (D1) *ensures an $\eta$-reformulation* ($P_M$) *for a Gibbs solver at inverse temperature $\beta$.*

*Proof.* Ensuring that the probability of sampling feasible solutions is greater than $\eta$ is equivalent to show that sampling infeasible solutions occurs with probability at most $1 - \eta$, i.e. $\mathbb{P}[\mathbf{x} \notin \mathcal{F}] \leq 1 - \eta$. Using the fact that the energy of the QUBO formulation will be $E(\mathbf{x}) = E^{(o)}(\mathbf{x}) + M(A\mathbf{x} - b)^2$ and for infeasible points $(A\mathbf{x} - b)^2 \geq 1$, we can bound:

$$\mathbb{P}[\mathbf{x} \notin \mathcal{F}] = \sum_{\mathbf{x}\notin\mathcal{F}} p(\mathbf{x}) = \mathcal{N}_\beta \sum_{\mathbf{x}\notin\mathcal{F}} e^{-\beta(E^{(o)}(\mathbf{x}) + M(A\mathbf{x}-b)^2)} \leq \mathcal{N}_\beta e^{-\beta M}\sum_{\mathbf{x}\notin\mathcal{F}} e^{-\beta E^{(o)}(\mathbf{x})}, \tag{D2}$$

where $\mathcal{N}_\beta^{-1} = \sum_{\mathbf{x}\in\{0,1\}^n} e^{-\beta E(\mathbf{x})}$ is the normalization constant of the pmf. We then define the minimal objective energy as $E_{\min} = \min_{\mathbf{x}\in\{0,1\}^n} E^{(o)}(\mathbf{x})$ and bound

$$\mathbb{P}[\mathbf{x} \notin \mathcal{F}] \leq \mathcal{N}_\beta e^{-\beta(M + E_{\min})}\sum_{\mathbf{x}\notin\mathcal{F}} 1 \leq \mathcal{N}_\beta e^{-\beta(M + E_{\min})}2^n. \tag{D3}$$

To bound the normalization constant, suppose we know the energy of a feasible bitstring to be $E(\mathbf{x}_{\text{feas}}) = E_{\text{feas}}$, which doesn't depend on $M$ since $E(\mathbf{x}) = E^{(o)}(\mathbf{x})$ if $\mathbf{x} \in \mathcal{F}$; then, $\mathcal{N}_\beta^{-1} = \sum_{\mathbf{x}\in\{0,1\}^n} e^{-\beta E(\mathbf{x})} \geq e^{-\beta E_{\text{feas}}}$ and

$$\mathbb{P}[\mathbf{x} \notin \mathcal{F}] \leq e^{-\beta(M + E_{\min} - E_{\text{feas}})}2^n. \tag{D4}$$

To ensure $\mathbb{P}[\mathbf{x} \notin \mathcal{F}] \leq 1 - \eta$ it is thus sufficient to pick $M$ such that $e^{-\beta(M + E_{\min} - E_{\text{feas}})}2^n \leq 1 - \eta$, or, equivalently,

$$M \geq \beta^{-1}(n\ln(2) - \ln(1-\eta)) + E_{\text{feas}} - E_{\min}. \tag{D5}$$

To prove the claim on $M_{\ell_1}(\beta)$, it is left to show only that $\|Q\|_{\ell_1} \geq E_{\text{feas}} - E_{\min}$. This is immediate as

$$\|Q\|_{\ell_1} = \sum_{ij} |Q_{ij}| = \sum_{i,j:Q_{ij}\geq 0} Q_{ij} - \sum_{i,j:Q_{ij}<0} Q_{ij}. \tag{D6}$$

Clearly, $\sum_{i,j:Q_{ij}\geq 0} Q_{ij} \geq \max_\mathbf{x} \mathbf{x}^t Q \mathbf{x} \geq E_{\text{feas}}$; on the other hand, $\sum_{i,j:Q_{ij}<0} Q_{ij} \leq \min_\mathbf{x} \mathbf{x}^t Q \mathbf{x} = E_{\min}$. This shows that $\|Q\|_{\ell_1} \geq E_{\text{feas}} - E_{\min}$ and proves the lemma. $\square$

Notice that the fact that $\|Q\|_{\ell_1} \geq E_{\text{feas}} - E_{\min}$ is related to the advantage for exact solvers in using the more conservative weight $M_{\text{SDP}} = E_{\text{feas}} - E_{\text{SDP}}$, rather than $M_{\ell_1} = M_{\ell_1}(\beta = \infty) = \|Q\|_{\ell_1}$ as shown in Ref. [39], where $E_{\text{SDP}}$ is a lower bound of $E_{\min}$.

## Appendix E: Triviality and existence of the solution

Sampling feasible solutions with a maximal allowed energy, with probability at least $\eta$ and using a Gibbs solver at temperature $\beta$, can range from extremely difficult to trivial. In extreme cases, the task may even become infeasible. In this section, we illustrate how the algorithm handles these opposite cases.

For a fixed $\beta$, there is an upper bound on the sampling probability of feasible solutions with energy not exceeding $E_f$. This bound corresponds to the probability of sampling such solutions assuming that only feasible points could be drawn, that is, in the limit of very large $M$ where infeasible configurations are fully suppressed. Formally, this upper limit is the cumulative distribution function of the Gibbs measure restricted to the feasible subspace, evaluated at $E_f$. Recall that in Algorithm 1 we determine $M$ from three bounds using

$$g(M) = B_{\overline{\mathcal{F}}}(M) + B^>_{\mathcal{F}} - \frac{1-\eta}{\eta} B^<_{\mathcal{F}}. \tag{E1}$$

The function $g$ is monotonically decreasing in $M$, and it is constructed so that its zeros (and the region where $g(M) \leq 0$) correspond to values of $M$ satisfying the requirement. The maximal $\eta$ ensuring the existence of a guaranteed sampling success, which we denote as $\eta_{\text{exist}}$, occurs when $g(M)$ tends to zero only asymptotically. Since $g(M) \xrightarrow{M\to\infty} B^>_{\mathcal{F}} - \frac{1-\eta}{\eta}B^<_{\mathcal{F}}$, then by setting this limit to zero we obtain

$$\eta_{\text{exist}} = \frac{B^<_{\mathcal{F}}}{B^<_{\mathcal{F}} + B^>_{\mathcal{F}}}. \tag{E2}$$

In the algorithm, if the required sampling success satisfies $\eta \geq \eta_{\text{exist}}$, then the requirement is unattainable: $g$ has no roots and the algorithm returns $\{\}$. The required sampling success can then be reduced to $\eta_{\text{exist}} - \epsilon$ for a small $\epsilon$ and the algorithm rerun to obtain an attainable solution. Conversely, if the requirement is already met even with no penalty weight ($M = 0$), the problem is considered trivial: the root of $g$ will be negative and therefore returning $\max\{0, M^*\}$ will ensure a positive and sufficient penalty weight.

## Appendix F: Robust implementation in logspace

A naive numerical implementation of the algorithm may suffer from numerical instabilities or overflow, primarily due to the exponentials involved in the computations of the terms $B_{\overline{\mathcal{F}}}$, $B^<_{\mathcal{F}}$ and $B^>_{\mathcal{F}}$. To prevent this, we implement a numerically stable formulation, described in this section.

Let us first take the function (E1), and recall that $B_{\overline{\mathcal{F}}}(M) = \sum_{v=1}^{v_{\text{cut}}} e^{-\beta M v} n_{\text{pen}}(v)$, $B^>_{\mathcal{F}} = \sum_{e\in\overline{\Lambda^<}} e^{-\beta e} n_\Delta(e + E_{\text{LB}})$, $B^<_{\mathcal{F}} = \sum_{e\in\Lambda^<} e^{-\beta(e+\Delta)} n_\Delta(e + E_{\text{LB}})$ and set $c = \frac{1-\eta}{\eta}$. We can alternatively define the function

$$G(M) = \log(B_{\overline{\mathcal{F}}}(M) + B^>_{\mathcal{F}}) - \log\left(\frac{1-\eta}{\eta}\right) - \log(B^<_{\mathcal{F}}). \tag{F1}$$

Note that the functions $g(M)$ and $G(M)$ share the same sign and root. hence, $G(M)$ can be used in place of $g(M)$ in the Algorithm 1 yielding logarithmically smaller values in the evaluation. To compute the terms of $G(M)$ efficiently and stably, we introduce the LogSumExp (LSE) function [73], defined as $\text{LSE}(x_1, \ldots, x_n) = \log\left(\sum_{i=1}^n e^{x_i}\right)$, which is commonly used to avoid underflow and overflow, among other things. Using the LSE, we compute the terms of $G$ as

$$\log(B_{\overline{\mathcal{F}}}(M)) = \text{LSE}[\log(n_{\text{pen}}(v)) - \beta M v]_{v=1}^{v_{\text{cut}}}, \tag{F2}$$

$$\log(B^>_{\mathcal{F}}) = \text{LSE}[\log(n_\Delta(e + E_{\text{LB}})) - \beta e]_{e\in\overline{\Lambda^<}}, \tag{F3}$$

$$\log(B_{\overline{\mathcal{F}}}(M) + B^>_{\mathcal{F}}) = \text{LSE}[\log(B_{\overline{\mathcal{F}}}(M)), \log(B^>_{\mathcal{F}})], \tag{F4}$$

$$\log(B^<_{\mathcal{F}}) = \text{LSE}[\log(n_\Delta(e + E_{\text{LB}})) - \beta(e + \Delta)]_{e\in\Lambda^<}. \tag{F5}$$

Using the log-domain function $G(M)$ instead of $g(M)$ also affects the computation of the existence threshold discussed in Section E. By imposing $G(\infty) = 0$, one can compute $\eta_{\text{exist}} = (1 + e^\gamma)^{-1}$, with $\gamma = \log(B^>_{\mathcal{F}}) - \log(B^<_{\mathcal{F}})$, properly evaluated using the LSE function to ensure numerical stability.

## Appendix G: Dependence of the Algorithm's output on the input parameters ($v_{\text{cut}}$ and $E_f$)

This section provides a concise analysis of the sensitivity of the algorithm's output to choices of the input parameters $E_f$, the maximal energy of desired solutions, and $v_{\text{cut}}$, the maximal value of the penalization term considered for infeasible points. Fig. 6 illustrates, for small instances ($n_{\text{bits}} \approx 16$) across all benchmarked problems, the behavior of the returned weight $M^*$ and its associated required success probability $\eta$, compared with the effective success probability $\eta_{\text{eff}}$ of an ideal Gibbs sampler. For the MNPP and TSP instances, small values of $v_{\text{cut}}$ do not change $M^*$ accounting for most of the probability mass of infeasible points, as indicated by $\eta_{\text{eff}} \geq \eta$, confirming the robustness of the guarantee. In contrast, for PO, values $v_{\text{cut}} < 16$ fail to capture all relevant infeasible configurations. Here $M^*$ increases stepwise (because $n_{\text{pen}}(v)$ is non-zero only for perfect squares $v$) and $\eta_{\text{eff}} < \eta$, indicating an unfulfilled guarantee. Only for $v_{\text{cut}} \geq 16$, $M^*$ converges and the effective success probability is close to its target. Similar behaviour was observed for larger problem sizes. Accordingly, $v_{\text{cut}}$ was fixed to 4 for MNPP and TSP, and to 16 for PO instances.

Fig. 7 shows the dependence of $M^*$ and $\eta$ on the parameter $E_f$ for an exemplary MNPP instance with 18 bits. As $E_f$ decreases, $M^*$ increases to ensure a success probability of $\eta = 0.5$, as long as this target remains achievable (filled markers). For sufficiently small $E_f$, however, the requirement becomes unattainable. In this regime, the algorithm is re-run with $\eta = \eta_{\text{exist}} - \epsilon$, where $\eta_{\text{exist}}$ is the maximal success probability for which the existence of a solution $M$ is ensured; see Section E for details. When this happens (empty markers), both the maximal attainable success $\eta_{\text{exist}}$ and $\eta$ alongside, decrease as $E_f$ is lowered, as expected.

**Figure 6.** Output dependence on $v_{\text{cut}}$. Algorithm output $M^*$ (top) and associated effective success probability $\eta_{\text{eff}}$ (bottom) as functions of the hyperparameter $v_{\text{cut}}$ for the tested benchmarks, shown for small system sizes. In the bottom plots, the thin blue line denotes the required probability $\eta$ and orange markers the effective success $\eta_{\text{eff}}$ measured from an ideal Gibbs sampler. For MNPP and TSP, $M^*$ stabilizes already at small $v_{\text{cut}}$, with $\eta_{\text{eff}} > \eta$ in the corresponding plots -- indicating that small $v_{\text{cut}}$ values capture most infeasible samples and ensure a robust guarantee that is respected. In contrast, for PO instances, values $v_{\text{cut}} \geq 16$ are required to capture all relevant infeasible configurations, stabilize $M^*$, and achieve an $\eta_{\text{eff}}$ close to the target $\eta$. The required probability $\eta$ has been set to 0.5 (0.25 for PO), the inverse temperature to $\beta = 10^{-5}$ and the problem-specific parameters to $N, P = 4, 3$ (MNPP), $n_c = 4$ (TSP) and $N, w = 4, 3$ (PO).

**Figure 7.** Output dependence on $E_f$. Algorithm output $M^*$ (left) and success probability used for the output computation $\eta$ (right) as functions of the input parameter $E_f$, for a small instance of MNPP ($N, P = 9, 2$), illustrating the parameter's effect. Filled blue markers denote the region where the required probability $\eta$ can be satisfied and thus the output $M^*$ is computed using the required $\eta$, while empty markers denote the region where the requirement becomes unattainable, and the guarantee is thus reduced to $\eta = \eta_{\text{exist}}(E_f) - \epsilon$, where $\eta_{\text{exist}}$ is the maximal probability for which the existence of a solution $M$ is ensured (see Section E). The required probability is set to $\eta = 0.5$, the inverse temperature to $\beta = 10^{-5}$ and $\epsilon = 0.01$.

## Appendix H: Solving the inverse problem as a byproduct: from $M$ to $\beta$

A convenient extension of the algorithms introduced in this work arises in the inverse problem to the Big-$M$ problem: determine the inverse temperature $\beta$ that allows a thermal solver to sample desired solutions with probability at least $\eta$, when the penalty weight $M$ is fixed. Such a situation may occur when increasing $M$ is not possible due to interaction strengths, hardware, or software limitations, while the solver temperature can still be adjusted to meet the sampling requirement. This inverse problem can be solved with the same strategy introduced in this work (Sec. B). To this end, we modify Algorithm 1 line 7 to calculate an optimal inverse temperature $\beta^*$ as the root of $\beta \mapsto g(M)$ for given $M$.

## Appendix I: Penalization degeneracy

In this section, we present the analytical results on the penalization degeneracy $n_{\text{pen}}(v) = |\{\mathbf{x}\in\{0,1\}^n : E^{(p)}(\mathbf{x}) = v\}|$ for the constrained optimization problems considered in this work. For the benchmarked problems MNPP, TSP and PO, the penalization degeneracy can be obtained analytically through combinatorial counting methods. The following subsections detail these analytical expressions for each problem. Note that alternatively one can also estimate $n_{\text{pen}}(v)$ for $v \in \{1, \ldots, v_{\text{cut}}\}$ by uniformly sampling bitstrings $\mathbf{x} \in \{0,1\}^n$, evaluating their penalization energy $E^{(p)}(\mathbf{x})$ and then fitting or inferring the corresponding values.

Importantly, the analytical argument used to derive the penalization degeneracies $n_{\text{pen}}(v)$, suggests that, for any fixed value of $v$, computing $n_{\text{pen}}(v)$ takes at most polynomial time and memory in $n$. For the benchmark problems, MNPP, TSP and PO, the entries of the constraint matrix $A$ are upper bounded by 1. Consequently, as stated in the main text, the penalization term is bounded $v_{\max} = \max_\mathbf{x} E^{(p)}(\mathbf{x}) \in \mathcal{O}(mn^2)$. Therefore, evaluating $n_{\text{pen}}(v)$ for all $v$ also takes overall polynomial time and memory in the problem size. Expressed in terms of the parameters of each problem, $v_{\max}$ reads as follows: for TSP, we have $m = n_v$, the number of vertices, and $n = n_v^2$, hence $v_{\max} \in \mathcal{O}(n_v^5)$; for MNPP ($N$ numbers in $P$ partitions), we have $m = P$ and $n = NP$, hence $v_{\max} \in \mathcal{O}(N^2P^3)$; for PO, we have $m = 1$ and $n = wN$, the resolution $w$ times number of stocks $N$, hence $v_{\max} \in \mathcal{O}(w^2N^2)$.

In Fig. 8 we illustrate the results of the remainder of this appendix. We show the penalization degeneracies computed analytically for small values of the penalization at a fixed system size. We observe that $n_{\text{pen}}$ scales sub-exponentially for all three problems. This indicates that one can often introduce rather small values of the cut-off $v_{\text{cut}}$ until which $n_{\text{pen}}$ is computed in our Algorithm 1.

**Figure 8.** Penalization degeneracies for the problems studied and stretched exponential fit. $n_{\text{pen}}(v)$ is shown as a function of the violation $v$ on a logarithmic scale for the benchmarked problems (from left to right, MNPP, TSP and PO) at a fixed problem size. The problem parameters were chosen such that each instance requires 255 bits; specifically, for MNPP $N = 45$, $P = 5$, for TSP $n_v = 25$ and for PO $N = 45$, $w = 5$. Dots represent the analytical values reported in Section I, while dashed lines show a stretched exponential fit, defined as $n_{\text{pen}}(v) = \exp(a + bv^k)$. Note that for $k = 1$ the stretched exponential reduces to a standard exponential, whereas $k < 1$ corresponds to sub-exponential growth. The fit closely follows the data, with fitted exponents for the three cases (from left to right) given by $k_{\text{MNPP}} = 0.79 \pm 0.05$, $k_{\text{TSP}} = 0.83 \pm 0.02$ and $k_{\text{PO}} = 0.46 \pm 0.05$, where the errors correspond to three standard deviations. In all cases, $n_{\text{pen}}(v)$ exhibits sub-exponential scaling with $v$.

### 1. MNPP

For a Multiway Number Partition Problem (MNPP) instance with $N$ numbers to partition into $P$ partitions the penalization $E^{(p)}(\mathbf{x}) = \sum_{i=1}^N (1 - \sum_{p=1}^P x_{i,p})^2$ enforces a feasible decision matrix $[\mathbf{x}]_{i,p}$ to be right-stochastic, i.e., $\sum_{p=1}^P x_{i,p} = 1 \; \forall i$, meaning that each row of the binary matrix contains exactly one 1. Note that in the penalization term the rows contribute independently to the total energy. Therefore, the number of feasible bitstrings ($v = 0$) is $n_{\text{pen}}(0) = P^N$, since there are $P$ valid choices per row and $N$ rows. Similarly, the number of bitstrings with $v = 1$ can be counted by considering the number of configurations with exactly one incorrect row and multiplying by the number of ways this row can contain either 0 or 2 ones instead of 1, thus, giving $E^{(p)}(\mathbf{x}) = 1$. The same reasoning extends to higher values ($v = 2, 3$). For $v = 4, \ldots, 7$ one must also include rows with 3 ones instead of 1, which contribute a factor of four to $E^{(p)}(\mathbf{x})$. In this way, the following expressions are obtained:

$$n_{\text{pen}}(0) = P^N \quad \text{feasible bitstrings} \tag{I1}$$

$$n_{\text{pen}}(v) = P^{N-v}\binom{N}{v}\left(1 + \binom{P}{2}\right)^v \quad \forall v \in \{1, \cdots, 3\} \tag{I2}$$

$$n_{\text{pen}}(v) = P^{N-v}\binom{N}{v}\left(1 + \binom{P}{2}\right)^v + (v-3)\binom{N}{v-3}P^{N-(v-3)}\binom{P}{3}\left(1 + \binom{P}{2}\right)^{v-4} \quad \forall v \in \{4, \cdots, 7\} \tag{I3}$$

### 2. TSP

For a Travelling Salesman Problem instance with $n_v$ vertices, the penalization $E^{(p)}(\mathbf{x}) = \sum_{i=1}^{n_v}(1 - \sum_{t=1}^{n_v} x_{t,i})^2 + \sum_{t=1}^{n_v}(1 - \sum_{i=1}^{n_v} x_{t,i})^2$ enforces a feasible decision matrix $[\mathbf{x}]_{t,i}$ to be stochastic, meaning that each row *and* each column must contain exactly a single 1. The number of feasible points thus corresponds to the number of permutation matrices, hence $n_{\text{pen}}(0) = n_v(n_v - 1)\ldots 1 = n_v!$. Unlike the MNPP case, here row and column errors are not independent (e.g., flipping a bit in a valid configuration introduces an error in both a row and a column), so their contributions to the total penalty are not independent. Consequently, no configurations exist with $v = 1$. Indeed, having a total number of ones different from $n_v$ inevitably produces at least one faulty row (with zero or two ones) *and* one faulty column, producing a minimum of $v = 2$. Conversely, if the matrix contains exactly $n_v$ ones, faulty rows (and columns) must occur in pairs, so $v$ is always even. Similarly, all odd-valued violations considered (up to $v = 7$) yield no configuration. The coupling between rows and columns rapidly complicates the combinatorial counting as $v$ increases. To determine $n_{\text{pen}}(v)$, one must first identifies all distinct patterns in which a given $v$ can occur, and then count the configurations realizing each pattern. For instance, for $v = 2$ we must account for several distinct scenarios: matrices with two faulty rows and no faulty columns, yielding $n_v!\binom{n_v}{2}$ configurations; matrices with two faulty columns and no faulty rows (the same number by symmetry); matrices with one faulty row and one faulty column containing $n_v - 1$ ones in total (rather than $n_v$ like a valid configuration), that are $n_v!n_v$; matrices with one faulty row and one faulty column with $n_v + 1$ ones in total and a 1 at the intersection of the faults, giving $n_v!2\binom{n_v}{2}$; and finally, matrices with one faulty row and one faulty column containing $n_v + 1$ ones in total but a 0 at the intersection of the faults, resulting in $n_v!\frac{3}{2}\binom{n_v}{3}$. Analogous decompositions, based on the number of ones and the distribution of horizontal or vertical faults, were performed to avoid overcounting and to compute degeneracies up to $v = 6$:

$$n_{\text{pen}}(0) = n_v! \quad \text{feasible bitstrings} \tag{I4}$$

$$n_{\text{pen}}(1) = 0 \tag{I5}$$

$$n_{\text{pen}}(2) = n_v!\left[n_v + 4\binom{n_v}{2} + \frac{3}{2}\binom{n_v}{3}\right] \tag{I6}$$

$$n_{\text{pen}}(3) = 0 \tag{I7}$$

$$n_{\text{pen}}(4) = n_v!\left[\binom{n_v}{2} + 21\binom{n_v}{3} + 57\binom{n_v}{4} + 45\binom{n_v}{5} + \frac{45}{4}\binom{n_v}{6}\right] \tag{I8}$$

$$n_{\text{pen}}(5) = 0 \tag{I9}$$

$$n_{\text{pen}}(6) = 5n_v!\left[\frac{47}{15}\binom{n_v}{3} + 24\binom{n_v}{4} + 137\binom{n_v}{5} + 1157\binom{n_v}{6} + \frac{567}{4}\binom{n_v}{7} + 126\binom{n_v}{8} + \frac{63}{2}\binom{n_v}{9}\right] \tag{I10}$$

$$n_{\text{pen}}(7) = 0 \tag{I11}$$

### 3. PO

For a Portfolio Optimization instance with $N$ stocks and partition number $w$, the penalization energy is $E^{(p)}(\mathbf{x}) = (\sum_{i=1}^N x_i - 2^w + 1)^2$, where each component is an integer $x_i \in \{0, \ldots, 2^w - 1\}$. The penalization is zero only for bitstrings $\mathbf{x}$ whose components sum up to $2^w - 1$. Since $E^{(p)}$ is the square of an integer, non-zero configurations exist only for perfect-square values $v = k^2$. The number of feasible configurations ($v = 0$) can be computed as the number of ways to distribute $2^w - 1$ indistinguishable 'coins' (portfolio fragments) among $N$ distinguishable 'boxes' (stocks) by standard combinatorial arguments. For infeasible bitstrings, a similar reasoning applies: if the configuration components sum up to $2^w - 1 \pm k$, then $v = k^2$. The corresponding number of configurations is the sum of two terms: the ways to distribute $2^w - 1 - k$ (indistinguishable) coins among $N$ (distinguishable) boxes, and the ways to distribute $2^w - 1 + k$ coins among $N$ boxes, constrained so that no box can contain more than $2^w - 1$ coins, since each $x_i$ is bounded by that value. This procedure yields the following penalization degeneracies:

$$n_{\text{pen}}(0) = \binom{2^w + N - 2}{N - 1} \quad \text{feasible bitstrings} \tag{I12}$$

$$n_{\text{pen}}(1) = \binom{2^w + N - 3}{N - 1} + \binom{2^w + N - 1}{N - 1} - N \tag{I13}$$

$$n_{\text{pen}}(4) = \binom{2^w + N - 4}{N - 1} + \binom{2^w + N}{N - 1} - N^2 \tag{I14}$$

$$n_{\text{pen}}(9) = \binom{2^w + N - 5}{N - 1} + \binom{2^w + N + 1}{N - 1} - N^2\frac{N + 1}{2} \quad \text{for } w \geq 2 \tag{I15}$$

$$n_{\text{pen}}(16) = \binom{2^w + N - 6}{N - 1} + \binom{2^w + N + 2}{N - 1} - N^2\frac{N + 1}{2}\frac{N + 2}{3} \quad \text{for } w \geq 2 \tag{I16}$$

$$n_{\text{pen}}(25) = \binom{2^w + N - 7}{N - 1} + \binom{2^w + N + 3}{N - 1} - N^2\frac{N + 1}{2}\frac{N + 2}{3}\frac{N + 3}{4} \quad \text{for } w \geq 3 \tag{I17}$$

$$n_{\text{pen}}(v) = 0 \quad \forall v : \nexists k \in \mathbb{N} : v = k^2 \tag{I18}$$

## References

[1] A. Abbas, A. Ambainis, B. Augustino, A. Bartschi, H. Buhrman, C. Coffrin, G. Cortiana, V. Dunjko, D. J. Egger, B. G. Elmegreen, N. Franco, F. Fratini, B. Fuller, J. Gacon, C. Gonciulea, S. Gribling, S. Gupta, S. Hadfield, R. Heese, G. Kircher, T. Kleinert, T. Koch, G. Korpas, S. Lenk, J. Marecek, V. Markov, G. Mazzola, S. Mensa, N. Mohseni, G. Nannicini, C. O'Meara, E. P. Tapia, S. Pokutta, M. Proissl, P. Rebentrost, E. Sahin, B. C. B. Symons, S. Tornow, V. Valls, S. Woerner, M. L. Wolf-Bauwens, J. Yard, S. Yarkoni, D. Zechiel, S. Zhuk, and C. Zoufal, Challenges and opportunities in quantum optimization, Nature Reviews Physics 6, 718 (2024), arXiv:2312.02279 [quant-ph].

[2] M. W. Johnson, M. H. S. Amin, S. Gildert, T. Lanting, F. Hamze, N. Dickson, R. Harris, A. J. Berkley, J. Johansson, P. Bunyk, E. M. Chapple, C. Enderud, J. P. Hilton, K. Karimi, E. Ladizinsky, N. Ladizinsky, T. Oh, I. Perminov, C. Rich, M. C. Thom, E. Tolkacheva, C. J. S. Truncik, S. Uchaikin, J. Wang, B. Wilson, and G. Rose, Quantum annealing with manufactured spins, Nature 473, 194 (2011).

[3] E. J. Crosson and D. A. Lidar, Prospects for quantum enhancement with diabatic quantum annealing, Nat. Rev. Phys. 3, 466 (2021), arXiv:2008.09913 [quant-ph].

[4] E. Farhi, J. Goldstone, and S. Gutmann, A quantum approximate optimization algorithm, arXiv:1411.4028 [quant-ph] (2014).

[5] T. Inagaki, Y. Haribara, K. Igarashi, T. Sonobe, S. Tamate, T. Honjo, A. Marandi, P. L. McMahon, T. Umeki, K. Enbutsu, O. Tadanaga, H. Takenouchi, K. Aihara, K. ichi Kawarabayashi, K. Inoue, S. Utsunomiya, and H. Takesue, A coherent Ising machine for 2000-node optimization problems, Science 354, 603 (2016).

[6] T. Honjo, T. Sonobe, K. Inaba, T. Inagaki, T. Ikuta, Y. Yamada, T. Kazama, K. Enbutsu, T. Umeki, R. Kasahara, K. ichi Kawarabayashi, and H. Takesue, 100,000-spin coherent Ising machine, Science Advances 7, eabh0952 (2021).

[7] M. Sao, H. Watanabe, Y. Musha, and A. Utsunomiya, Application of digital annealer for faster combinatorial optimization, Fujitsu Scientific and Technical Journal 55, 45 (2019).

[8] B. Hideki Fukushima-Kimura, N. Kawamoto, E. Noda, and A. Sakai, Mathematical aspects of the Digital Annealer's simulated annealing algorithm, arXiv:2303.08392 [math.OC] (2023).

[9] T. Okuyama, T. Sonobe, K.-i. Kawarabayashi, and M. Yamaoka, Binary optimization by momentum annealing, Phys. Rev. E 100, 012111 (2019).

[10] H. Goto, K. Tatsumura, and A. R. Dixon, Combinatorial optimization by simulating adiabatic bifurcations in nonlinear Hamiltonian systems, Science Advances 5, eaav2372 (2019), https://www.science.org/doi/pdf/10.1126/sciadv.aav2372.

[11] K. Tatsumura, M. Yamasaki, and H. Goto, Scaling out Ising machines using a multi-chip architecture for simulated bifurcation, Nature Electronics 4, 208 (2021).

[12] G. Kochenberger, J.-K. Hao, F. Glover, M. Lewis, Z. Lu, H. Wang, and Y. Wang, The unconstrained binary quadratic programming problem: a survey, Journal of Combinatorial Optimization 28, 58 (2014).

[13] D. Ratke, List of qubo formulations, https://blog.xa0.de/post/List-of-QUBO-formulations/ (2021), blog post, accessed 2026-03-02.

[14] S. Kirkpatrick, C. D. Gelatt, and M. P. Vecchi, Optimization by simulated annealing, Science 220, 671 (1983).

[15] S. Geman and D. Geman, Stochastic relaxation, gibbs distributions, and the bayesian restoration of images, IEEE Transactions on Pattern Analysis and Machine Intelligence PAMI-6, 721 (1984).

[16] R. J. Glauber, Time-dependent statistics of the ising model, Journal of Mathematical Physics 4, 294 (1963).

[17] W. K. Hastings, Monte carlo sampling methods using markov chains and their applications, Biometrika 57, 97 (1970).

[18] K. Hukushima and K. Nemoto, Exchange monte carlo method and application to spin glass simulations, Journal of the Physical Society of Japan 65, 1604 (1996), arXiv:cond-mat/9512035.

[19] E. Mossel and A. Sly, Exact thresholds for ising-gibbs samplers on general graphs, The Annals of Probability 41, 10.1214/11-aop737 (2013).

[20] N. Siddique and H. Adeli, Simulated annealing, its variants and engineering applications, International Journal on Artificial Intelligence Tools 25, 1630001 (2016), https://doi.org/10.1142/S0218213016300015.

[21] M. Karabin and S. J. Stuart, Simulated annealing with adaptive cooling rates (2020), arXiv:2002.06124 [physics.chem-ph].

[22] S. Matsubara, H. Tamura, M. Takatsu, D. Yoo, B. Vatankhahghadim, H. Yamasaki, T. Miyazawa, S. Tsukamoto, Y. Watanabe, K. Takemoto, and A. Sheikholeslami, Ising-model optimizer with parallel-trial bit-sieve engine, in Complex, Intelligent, and Software Intensive Systems, edited by L. Barolli and O. Terzo (Springer International Publishing, 2018) pp. 432-438.

[23] H. M. Waidyasooriya, Y. Araki, and M. Hariyama, Accelerator architecture for simulated quantum annealing based on resource-utilization-aware scheduling and its implementation using opencl, in 2018 International Symposium on Intelligent Signal Processing and Communication Systems (ISPACS) (2018) pp. 335-340.

[24] S. Matsubara, M. Takatsu, T. Miyazawa, T. Shibasaki, Y. Watanabe, K. Takemoto, and H. Tamura, Digital annealer for high-speed solving of combinatorial optimization problems and its applications, in 2020 25th Asia and South Pacific Design Automation Conference (ASP-DAC) (2020) pp. 667-672.

[25] T. Kadowaki and H. Nishimori, Quantum annealing in the transverse ising model, Physical Review E 58, 5355 (1998).

[26] E. Farhi, J. Goldstone, S. Gutmann, J. Lapan, A. Lundgren, and D. Preda, A quantum adiabatic evolution algorithm applied to random instances of an np-complete problem, Science 292, 472 (2001).

[27] A. Rajak, S. Tomar, and S. Kumar, Quantum annealing: An overview, Philosophical Transactions of the Royal Society A 380, 20210417 (2022).

[28] H. Munoz-Bauza and D. Lidar, Scaling advantage in approximate optimization with quantum annealing, Physical Review Letters 134, 160601 (2025).

[29] E. Farhi, J. Goldstone, and S. Gutmann, A quantum approximate optimization algorithm (2014), arXiv:1411.4028 [quant-ph].

[30] K. Blekos, D. Brand, A. Ceschini, C.-H. Chou, R.-H. Li, K. Pandya, and A. Summer, A review on quantum approximate optimization algorithm and its variants, Physics Reports 1068, 1 (2024).

[31] L. Cheng, Y.-Q. Chen, S.-X. Zhang, and S. Zhang, Quantum approximate optimization via learning-based adaptive optimization, Communications Physics 7, 83 (2024).

[32] O. Amosy, T. Danzig, O. Lev, et al., Iteration-free quantum approximate optimization algorithm using neural networks, Quantum Machine Intelligence 6, 38 (2024).

[33] N. Yanakiev, N. Mertig, C. K. Long, and D. R. M. Arvidsson-Shukur, Dynamic adaptive quantum approximate optimization algorithm for shallow, noise-resilient circuits, Physical Review A 109, 032420 (2024).

[34] W. Gilks, S. Richardson, and D. Spiegelhalter, eds., Markov Chain Monte Carlo in Practice (Chapman and Hall/CRC, London, 1996).

[35] S. Harwood, C. Gambella, D. Trenev, A. Simonetto, D. Bernal, and D. Greenberg, Formulating and solving routing problems on quantum computers, IEEE Transactions on Quantum Engineering 2, 1 (2021).

[36] I. D. Leonidas, A. Dukakis, B. Tan, and D. G. Angelakis, Qubit efficient quantum algorithms for the vehicle routing problem on noisy intermediate-scale quantum processors, Advanced Quantum Technologies 7, 2300309 (2024).

[37] Qiskit documentation, Converters for quadratic programs - linearequalitytopenalty (2022).

[38] U. Azad, B. K. Behera, E. A. Ahmed, P. K. Panigrahi, and A. Farouk, Solving vehicle routing problem using quantum approximate optimization algorithm, IEEE Transactions on Intelligent Transportation Systems 24, 7564 (2023).

[39] E. Alessandroni, S. Ramos-Calderer, I. Roth, E. Traversi, L. Aolita, et al., Alleviating the quantum big-m problem, npj Quantum Information 11, 10.1038/s41534-025-01067-0 (2025).

[40] G. Reinelt, Tsplib95 -- a library of sample instances for the travelling salesman problem and related problems, http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/ (1991), accessed: 2025-10-22.

[41] H. P. Williams, Model Building in Mathematical Programming, 5th ed. (Wiley, Chichester, UK, 2013).

[42] F. Glover, Improved linearization of nonlinear binary programming problems, Operations Research 13, 111 (1965).

[43] I. G. Rosenberg, Reduction of Bivalent Maximization Problems to the Quadratic Case, Research Memorandum RM-P-2470 (RAND Corporation, Santa Monica, CA, 1975).

[44] G. L. Nemhauser and L. A. Wolsey, Integer and Combinatorial Optimization (Wiley, New York, 1988).

[45] N. Metropolis, A. W. Rosenbluth, M. N. Rosenbluth, A. H. Teller, and E. Teller, Equation of state calculations by fast computing machines, The Journal of Chemical Physics 21, 1087 (1953).

[46] Y. Nesterov and A. Nemirovskii, Interior-Point Polynomial Algorithms in Convex Programming, Studies in Applied Mathematics, Vol. 13 (Society for Industrial and Applied Mathematics (SIAM), Philadelphia, PA, 1994).

[47] A. Yurtsever, M. Udell, J. A. Tropp, and V. Cevher, Sketchy decisions: Convex low-rank matrix optimization with optimal storage, in Proceedings of the 20th International Conference on Artificial Intelligence and Statistics, Proceedings of Machine Learning Research, Vol. 54, edited by A. Singh and J. Zhu (PMLR, 2017) pp. 1188-1196.

[48] R. L. Burden, J. D. Faires, and A. M. Burden, Numerical Analysis, 10th ed. (Cengage Learning, 2015).

[49] P. Diez-Valle, F. J. Gomez-Ruiz, D. Porras, and J. J. Garcia-Ripoll, Universal resources for qaoa and quantum annealing (2025), arXiv:2506.03241 [quant-ph].

[50] H. Oshiyama, S. Suzuki, and N. Shibata, Classical simulation and theory of quantum annealing in a thermal environment, Phys. Rev. Lett. 128, 170502 (2022).

[51] C. F. CAIAFA and A. N. PROTO, Temperature estimation in the two-dimensional ising model, International Journal of Modern Physics C 17, 29 (2006), https://doi.org/10.1142/S0129183106008356.

[52] M. Benedetti, J. Realpe-Gomez, R. Biswas, and A. Perdomo-Ortiz, Estimation of effective temperatures in quantum annealers for sampling applications: A case study with possible applications in deep learning, Phys. Rev. A 94, 022308 (2016).

[53] S. Hadfield, Z. Wang, B. O'Gorman, E. G. Rieffel, D. Venturelli, and R. Biswas, From the quantum approximate optimization algorithm to a quantum alternating operator ansatz, Algorithms 12, 34 (2019).

[54] D. Herman, R. Shaydulin, Y. Sun, S. Chakrabarti, S. Hu, P. Minssen, A. Rattew, R. Yalovetzky, and M. Pistoia, Quantum zeno dynamics for constrained optimization, Communications Physics 6, 219 (2023), arXiv:2209.15024 [quant-ph].

[55] P. Diez-Valle, J. Luis-Hita, S. Hernandez-Santana, F. Martinez-Garcia, A. Diaz-Fernandez, E. Andres, J. Jose Garcia-Ripoll, E. Sanchez-Martinez, and D. Porras, Multiobjective variational quantum optimization for constrained problems: an application to cash handling, Quantum Science and Technology 8, 045009 (2023).

[56] D. Bucher, J. Stein, S. Feld, and C. Linnhoff-Popien, Penalty-free approach to accelerating constrained quantum optimization, Phys. Rev. A 112, 062605 (2025).

[57] D. Bucher, D. Porawski, M. Janetschek, J. Stein, C. O'Meara, G. Cortiana, and C. Linnhoff-Popien, Efficient qaoa architecture for solving multi-constrained optimization problems, in 2025 IEEE International Conference on Quantum Computing and Engineering (QCE) (IEEE, 2025) p. 356-367.

[58] T. Shirai and N. Togawa, Compressed space quantum approximate optimization algorithm for constrained combinatorial optimization, IEEE Transactions on Quantum Engineering 6, 1-14 (2025).

[59] B. Bako, A. Glos, O. Salehi, and Z. Zimboras, Prog-QAOA: Framework for resource-efficient quantum optimization through classical programs, Quantum 9, 1663 (2025).

[60] S. Egginger, K. Kirova, S. Bruckner, S. Hillmich, and R. Kueng, A rigorous quantum framework for inequality-constrained and multi-objective binary optimization (2026), arXiv:2510.13983 [quant-ph].

[61] E. L. Schreiber, R. E. Korf, and M. D. Moffitt, Optimal multiway number partitioning, J. ACM 65, 10.1145/3184400 (2018).

[62] A. Lucas, Ising formulations of many np problems, Frontiers in Physics 2, 10.3389/fphy.2014.00005 (2014).

[63] R. Korf, Objective functions for multi-way number partitioning, (2010).

[64] I. Gent and T. Walsh, Phase transitions and annealed theories: Number partitioning as a case study (1996) pp. 170-174, proc ECAI-96.

[65] R. Matai, S. Singh, and M. Mittal, Traveling salesman problem: an overview of applications, formulations, and solution approaches (2010).

[66] H. Markowitz, Portfolio selection, The Journal of Finance 7, 77 (1952).

[67] E. Grant, T. S. Humble, and B. Stump, Benchmarking quantum annealing controls with portfolio optimization, Phys. Rev. Applied 15, 014012 (2021).

[68] G. Rosenberg, P. Haghnegahdar, P. Goddard, P. Carr, K. Wu, and M. L. de Prado, Solving the optimal trading trajectory problem using a quantum annealer, IEEE Journal of Selected Topics in Signal Processing 10, 1053 (2016).

[69] M. R. Jerrum, L. G. Valiant, and V. V. Vazirani, Random generation of combinatorial structures from a uniform distribution, Theoretical Computer Science 43, 169 (1986).

[70] M. Jerrum, Counting, Sampling and Integrating: Algorithms and Complexity, Lectures in Mathematics ETH Zurich (Birkhauser, 2003).

[71] E. Vigoda, Approximately counting knapsack solutions and related problems, Lecture notes, Georgia Institute of Technology (2014).

[72] G. Pesant, C.-G. Quimper, and A. Zanarini, Counting solutions of CSPs: A structural approach, in Proceedings of the Twenty-Fourth International Joint Conference on Artificial Intelligence (IJCAI 2015) (2015) p. 337-343.

[73] S. Boyd and L. Vandenberghe, Convex Optimization (Cambridge University Press, 2009).
