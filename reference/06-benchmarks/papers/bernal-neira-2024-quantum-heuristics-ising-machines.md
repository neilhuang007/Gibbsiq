# Benchmarking the Operation of Quantum Heuristics and Ising Machines: Scoring Parameter Setting Strategies on Optimization Applications

David E. Bernal Neira$^{1,2,3}$, Robin Brown$^{1,4}$, Pratik Sathe$^{1,5}$, Filip Wudarski$^{1}$,
Marco Pavone$^{1}$, Eleanor G. Rieffel$^{2}$, and Davide Venturelli$^{1,2,*}$

1 USRA Research Institute for Advanced Computer Science (RIACS), Moffett Field, CA, USA
2 Quantum AI Laboratory (QuAIL), NASA Ames Research Center, Moffett Field, CA, USA
3 Division School of Chemical Engineering, Purdue University, West Lafayette, IN, USA
4 Autonomous Systems Laboratory, Stanford University, Palo Alto, CA, USA
5 Department of Physics and Astronomy, University of California at Los Angeles, Los Angeles, CA, USA

## Abstract

We discuss guidelines for evaluating the performance of parametrized stochastic solvers for optimization problems, with particular attention to systems that employ novel hardware, such as digital quantum processors running variational algorithms, analog processors performing quantum annealing, or coherent Ising Machines. We illustrate through an example a benchmarking procedure grounded in the statistical analysis of the expectation of a given performance metric, in test environments. In particular, we discuss the necessity and cost of setting parameters that affect the algorithm's performance. The optimal value of these parameters could vary significantly between instances of the same target problem. We present an open-source software package that facilitates the design, evaluation, and visualization of practical parameter tuning strategies for complex use of the heterogeneous components of the solver. We examine in detail an example using parallel tempering and a simulator of a photonic Coherent Ising Machine computing, and display the scoring of an illustrative baseline family of parameter-setting strategies that feature an exploration-exploitation trade-off.

**Keywords:** Benchmarking · Ising Solvers · Quantum Computing

## 1 Introduction

We present an approach to benchmarking the performance of hybrid quantum-classical algorithms and quantum-inspired algorithms based on a characterization of parametrized stochastic optimization solvers. Technological progress in quantum computing and engineering has led to the proliferation of generic quantum computational methods, algorithmic approaches, and hardware platforms where they can be tested. The Noisy Intermediate-Scale Quantum (NISQ) [1] era has catalyzed a myriad of ideas and implementations of physics-based hardware approaches to optimization that do not benefit from superposition and entanglement but whose performance is nonetheless grounded in complex, difficult-to-simulate dynamics. One class of such approaches is optimization solvers whose search algorithm is described by many coupled stochastic partial-differential equations. These methods include analog computing with oscillator [2], and optically Coherent Ising Machines (CIMs) [3]. Another approach is given by probabilistic bits, better known as *p-bits*, an intermediate between the standard bits of digital electronics and the emerging qubits of quantum computing [4, 5] and that can be physically implemented as perpendicular magnets. In perhaps an abuse of terminology, these physics-based solvers are often named quantum-inspired systems. Recent examples of the utilization of physics-inspired technologies include the design of 5G telecommunication networks via Coherent Ising Machines and Parallel Tempering [6, 7]. Another class of approaches are parametrized quantum circuits encoding variational algorithms such as the quantum approximate optimization algorithm (QAOA) or quantum annealing. This type of quantum computation has been implemented on a variety of platforms, including ion traps [8], neutral atoms [9, 10] and superconducting qubits [11, 12].

Empirical observations reveal that quantum and analog solvers can have an advantage over random search, producing probability distributions that potentially yield high-quality solutions [6, 12, 13, 14]. However, these solvers often struggle to generate samples of the global optimum and cannot guarantee its optimality, especially in the presence of noise. Existing techniques to address this issue, such as error mitigation, primarily focus on enhancing the quality of scalar observables, such as the expectation values of functions, rather than correcting the algorithm's output (bitstrings) [11]. Several other means can be employed to address this issue. First, improving the distribution of solution quality can be achieved through pre-processing techniques and tuning the algorithm's parameters. This is an issue for practical expected performance since good parameter settings might not be generalizable to other problem instances, success metrics, or available resources. Moreover, the parameter-tuning strategy is resource-consuming and must be reported when discussing the solvers' expected performance. Second, by designing solution methods that leverage the solver's capabilities to enhance the expectation value itself, the weaknesses of these methods can be mitigated by algorithmic approaches, e.g., [16, 17]. Assessing the performance of such methods becomes challenging as the specific sub-problem solution only accounts for a portion of the total solution method.

As these quantum and quantum-inspired methods improve performance and capabilities, the problems they can solve become more sophisticated. Since the purpose of NISQ systems and quantum-inspired Ising Machines is to solve problems, it is paramount to rigorously benchmark their performance [18]. There is a need to develop guidelines on evaluating the performance of new computing devices in the context of their future deployment in production, i.e., guidelines for an *operational* benchmarking as opposed to previous efforts that were mostly confined to research and development environments. A full operational evaluation must include overheads such as the cost of tuning. Without considering such overheads, it is easy to come to conclusions that would be misleading [19].

We propose a benchmark framework supported by an open-source software package intended to collect statistically relevant data when running a parametrized stochastic optimization solver attempting to solve instances from a distribution of representative problems. This work aims to provide guidelines for presenting "Window stickers" - i.e., a user-friendly and self-explanatory scorecard displaying the real-world performance expectation of a self-contained method using fixed and varying resources to solve applied problems of interest. While our considerations will mainly focus on optimization problems, this approach can be adapted to other computational tasks (e.g., sampling, learning) and platforms (e.g., neuromorphic chips).

Algorithmic benchmarking dates back to the 70s with the work in [20] on algorithm selection based on performance. These ideas have been applied to optimization algorithms, where performance profiles [21] are among the most popular proposals. These diagrams show the performance of different optimization algorithms, reporting the number of problems each method can solve with respect to time. These diagrams, although criticized for misleading conclusions when including more than two algorithms [22], have been widely used in the literature. Best practices have been proposed to provide the most informative benchmark analysis reported in [23]. Among these best practices, an automated software tool for benchmarking ensures reproducibility guarantees, for which several tools have been proposed [24, 25]. Parameter setting can be understood as an algorithm selection, where each parameterized algorithm is interpreted as a separate algorithm. Hyper-parameter tuning and benchmarking are also relevant in other fields of computational algorithms, such as machine learning [26], where hardware accelerators provide advantages that need to be quantified across the boundaries of different hardware implementations. Several tools have been proposed to automate this parameter setting in that context, e.g., Hyperopt [27].

Although there is a rich literature on algorithmic selection and parameter setting, quantum and physics-inspired optimization methods have characteristics that make their benchmarking unique and challenging [18]. For example, new performance metrics, such as time-to-target [28], have been proposed to represent the trade-offs between solution quality and efficiency for these methods, and recently there starts to be more emphasis on measuring performance as a function of resources employed and distinguishing classes of instances [29]. Note that many quantum computer benchmarks have been narrowly focused on circuit sizes that can be implemented without noise affecting their fidelity [30]. Additionally, in the NISQ era, quantum devices performance fluctuates over time, requiring frequent calibration. This introduces an extra layer of noise in the observed output distributions to be factored in in a benchmark.

For instance, this work aims to develop a methodology that adapts well to these quantum and physics-inspired methods for optimization, with supporting software to automate the benchmarking and parameter setting strategies and correctly account for these costs to provide practical and actionable information about solver performance. We list our contributions below:

- Characterization of solution methods as instantiation of parametrized stochastic optimization solvers (see Fig. 1)
- Proposal of benchmarking, visualizing and designing parameter setting strategies (see Fig. 2)
- Implementation in open-source software **Stochastic-Benchmarking** [31]

Ultimately, the question that such a pragmatic benchmarking procedure should answer can be framed as: *given well-specified resources and a new, previously unseen problem instance from a known distribution, what are the expectations for its resolution with a specific solution method?* As discussed throughout this paper, the key to answering this question is to properly define the concepts of *resources*, *expectations*, *solution*, and *solution method*. In particular, the definition of the solution method has to address hows various parameters that define the solver are set (see Fig. 1).

## 2 Solution Methods and Parametrized Stochastic Solvers

This study uses a framework focused on analyzing parametrized stochastic optimization solvers. Here, a "solver" is an integrated system, where hardware (the device) and software (algorithms) work together to solve optimization problems. Solvers have multiple parameters that can significantly affect their performance, but these effects are usually unknown beforehand. For our analysis, the solver is seen as a sampler of random variables of an unknown distribution, a concept familiar in classical optimization as stochastic optimization methods [32]. This approach is relevant for quantum heuristics and Ising machines, as they fit well within this category of optimization methods.

The raw output of such stochastic methods is a finite set, or string, of $N$ bits or binary values $\{z_i | z_i \in [0,1]\}$, obtained by a single measurement at the end of the computation $^1$, to which we associate a vector variable $z = [z_1, \ldots, z_N]$. The algorithm description does not specify how the distribution is updated or how the samples are obtained. Additionally, the stochastic nature of these solvers generates a distribution of solutions, which necessitates applying postprocessing techniques to determine the required output. A comparison between stochastic optimization algorithms and deterministic solution methods, which return the same solution to a problem every time they are executed and might even provide guarantees on the optimality of such a solution, might not be valid in general, given the heuristic nature of sampling associated with stochastic methods. From the bitstring $z$, we can define a transformed real-valued variable $X = fun(z)$, where $fun : \mathbb{B}^N \to \mathbb{R}$ is known as a pseudo-Boolean function [33].^{**}$ This variable, defined by a scalar function, also becomes a real-valued cost or objective. This variable $X$ can represent the solver's progress toward solving a single problem. The solver's performance can then be assessed through variable $X$, which can subsequently be used to learn how this solver behaves across different problem instances and compared against other solvers.

Analyzing experimental results from specific cases is crucial to accurately benchmark solvers, which perform differently across various problem instances. This helps determine the solver's effectiveness for specific problem classes or families, requiring analysis over multiple instances. In studying stochastic solvers, the objective is to estimate the probability density function (PDF) of the output variable $X$ based on the samples collected during the solution process. This PDF offers empirical insight into the distribution the solver samples from. Stochastic solvers lead to a change in the solution paradigm, where the new goal is to skew these distributions towards the desired output and sample it as efficiently as possible. In this perspective, deterministic search becomes equivalent to finding such a distribution.

Additionally, we focus on reporting the output for variable $X$ and the confidence level in ensuring a specific solution quality for a new, unknown problem instance within the targeted instance class.

**Benchmarking Framework.** Following the concepts for a reproducible benchmark, we present our framework as shown in Fig. 2. We consider an instance generation procedure, which generates a population of instances containing enough information to predict behavior over a new, unseen problem based on their solution. This procedure is followed by selecting (meta-)parameter values for evaluating the different parameter search strategies (PSSs). After establishing a performance metric, we set the benchmark.

The solution methods are run by (attempting to) solve the instances to identify promising solver parameters for the figure of merit. Recording the solution trajectory for each instance provides the information required to establish the performance profile of each method. This information can be used to choose the best solution strategy for each value along the trajectory. Considering this performance envelope, one could construct the virtual best (VB) performance profile. This would be equivalent to counting with an Oracle, which can tell which solution method is best for each resource value and each instance. This virtual best provides a bound on the performance that can be obtained for selecting solution methods. Moreover, by aggregating the different parameter settings that result in the best performances for each instance, one can define a target parameter setting strategy (PSS). This method is used extensively in the literature, where, e.g., the average of each parameter corresponding to the best parameter setting strategy across the different instances is computed for each resource value. If the aggregation results in a parameter setting not included in the PSSs, it should be re-run for all instances to verify its performance.

One observation is that fixed parameters for the solution methods might perform suboptimally over unseen instances, as the assumption that the instance population being "well-behaved" or representative might fail. A meta-parameter given to an advanced parameter tuning algorithm can address this, such as Hyperopt [27]. These meta-parameters affect the behavior of the tuning procedure itself, as well as be used to balance the exploration and exploitation procedures of the solution method parameter tuning. This exploration-exploitation balance can be expressed by determining which fraction of a total budget exploring for the best parameters and which should be spent exploiting the best-found parameters. Moreover, during the exploration stage, each parameter setting considered could be explored for a variable amount of resources, presenting a trade-off between checking many different parameter settings or realizing the potential of each one explored after investing a larger amount of resources.

All these steps result in a trajectory of (meta-)parameters for evaluation in the solvers. Depending on the solution methods and the family of instances, these trajectories might need to be made actionable. Namely, they might appear erratic due to a reduced number of instances or if outliers affect the different aggregations, e.g., across instances or parameter values. Trajectories are smoothed and then rerun if they do not correspond to any evaluated PSSs to gather information about their performance. The instance family is divided into training and testing sets to avoid overfitting. The procedure for finding good PSSs is repeated over several different instance splits, and then a cross-validation scheme aggregates these results.

The resulting "Window stickers" consist of (meta-)parameter trajectories or plots that show the value that each parameter should follow with various resources; meta-parameter trajectories that yield the different parameter settings in adaptive PSS. These analyses can then be aggregated across different problem families to show scaling performance over a feature of the instances.

PSSs, and performance profiles that show the expected merit function response to each different PSS. These analyses can then be aggregated across different problem families to show scaling performance over a feature of the instances.

## 3 The Stochastic Benchmark Framework

**Stochastic-Benchmark** is an open-source package implementing the methodology described in the previous section [31]. This open-source package introduces a statistical analysis methodology for evaluating and comparing the performance of (potentially quantum-inspired) optimization solvers. By incorporating visual presentation techniques and robust statistical analysis, **Stochastic-Benchmark** provides researchers with a comprehensive framework to assess solver performance and facilitate informed decision-making on design and production readiness in the field of quantum and quantum-inspired optimization. The **Stochastic-Benchmark** package helps particularly leverage for analyzing quantum-inspired methodologies, which often produce a large set of solutions as outputs. The analysis framework addresses these issues by providing a general performance comparison and parameter setting strategy evaluation platform.

To practically implement the methodology illustrated in Fig. 2, we provide an efficient implementation of the methods. In this section, we proceed to explain how the **Stochastic-Benchmark** framework operates. Consider that the following is given:

- Resource to be evaluated $R = \{r_0, \ldots, r_I\}$.
- Performance metric to be considered $P$.
- Set of instances $I = \{i_1, \ldots, i_n\}$.
- Set of solvers $S = \{s_1, \ldots, s_m\}$.
- Set of pre-evaluated parameters for solver $s$, $\alpha = \{\alpha_1, \ldots, \alpha_m\}$.
- Set of meta-parameters in case an adaptive PSS is to be included, $\theta$.

For each solver in each instance for each meta-parameter setting, a given performance profile $X = perf[\mathbf{s}(\alpha), i] = f(r)$. The ordered set of $R$ of resources $r \in R$ indicates the energy, time, and memory used for each call to the solver. Although some solvers provide the information of the performance metric as the progress of the resource, e.g., the logs provided in mixed-integer program solvers with incumbent solutions against time, for some quantum- and physics-based methods, only the final distribution of solution is provided. One could execute the solve for a grid of resource values, i.e., $r \in \{r_0, r_1, \ldots, r_I\}$, however, this would be highly costly considering that accessing these solvers is limited and expensive. We implement the bootstrapping in a parallelizable manner to efficiently regenerate these profiles, using only the distribution of solutions for the best resource value $r_I$, and compute confidence intervals for these metric predictions, which are then propagated along the data aggregations in the "Window stickers" framework. By incorporating confidence intervals, **Stochastic-Benchmark** provides a robust framework for evaluating solver performance and comparing different algorithms.

The performance profiles, perf$[\mathbf{s}(\alpha), i]$, are aggregated to compute the VB. (FPS automatically within **Stochastic-Benchmark**. Moreover, there is an implementation to perform adaptive PSS by connecting to the hyper-parameter optimizer Hyperopt, and an armed bandit strategy is implemented to evaluate the balance of exploration of parameter values for solvers and exploration of the best-found parameters. Thus, the main idea is that with a given amount of resource budget, a fraction of those resources (ExploFrac) are spent exploring the parameter space to get a sense of which parameters are suitable and, then, using the knowledge obtained, spend the remaining resources running the solver with the well-tuned choice of parameters.

Each of these PSS outputs a parameter strategy plot, which denotes the variation of the parameter values for different values of resources. Adaptive parameter strategy plots can be computed through callbacks in the code, which allow fitting these parameter profiles by functional forms using the Python numerical computation libraries numpy and scipy. Finally, the software automatically partitions the instance set in the training and testing sets and repeats the benchmarking procedure for each partition, ultimately applying a cross-validation technique to tackle the parameter strategies' overfitting.

## 4 Illustrative Example

This section describes results obtained by applying the **Stochastic-Benchmark** framework on an illustrative example. We describe the operational resources and constraints of the benchmark, the set of problem instances, the figure of merit, which information is accessible to solvers before the solution of the problems, the parameter setting strategy, and the test to assess a successful run. Consider these to be the elements of a conscientious benchmark.

### Operational resources and constraints: Solution methods.

We seek to minimize the energy of a class of zero-field Ising models, i.e., $\min_{i \in \{-1,1\}^N} \sum_{i,j} J_{ij}\sigma_i\sigma_j = \min_{s \in [\pm 1]^N} s^T Js$. The bitstring that minimizes the problem, $s^*$, and its corresponding objective or ground state energy, $s^* J s^*$, are desired. For this illustrative example, we consider two solvers: parallel tempering and a chaotic amplitude control coherent Ising machine simulator. Both methods were run on a single Ivy Bridge Node of the SuperComputer Pleiades, which counts with two Intel Xeon E5-2680v2 (2.8 GHz) processors per node, 3.2 GB RAM per core, 64 GB RAM node. The resource considered here was the number of reads of the problem variables, also called spins given their ±1 nature, which is proportional to the time executed.

**Cross Validated Performance Profile: CIM-CAC**

**Cross Validated Performance Profile: Simulated Annealing**

**Fig. 3:** Cross-validated performance profiles from 10 test-train splits of 50 Wishart instances with $N = 50$ and $\sigma = 0.5$ solved via (left) CIM-CAC [34] and (right) PySA [35]. The profiles of the virtual best baseline, a Hyperopt-driven exploration-exploitation strategy, and the fixed best parameters suggested from the experiments are shown. (generated by **Stochastic-Benchmark**)

**Solver 1: Coherent Ising Machine simulator.** Ising machines are a class of physical hardware that aims to find the minimum energy solution of the Ising model [15]. Coherent Ising Machines (CIMs) are an example of Ising machines that exploit mixed-state density operators in a quantum oscillator network [36]. Currently, the CIM is primarily benchmarked by simulating a quantitative model of its behavior in different applications. Although this is a widely accepted approach, no single model of the CIMs dynamics exists. Instead, different models with varying degrees of fidelity have been constructed when modeled when modeled when modeled. A specific type of CIM model is called the chaotic amplitude control coherent Ising machine, which seems to provide some advantages over other types of CIM [37, 38]. Recent improvements have also emerged on the simulated model based on machine-learning insights [39].

A set of ordinary differential equations describes the CIM dynamics. In the case of CIM-CAC, the spin variables are relaxed to continuous variables $x_i \in [-1, 1]$, and auxiliary variables $e_i$ satisfy $\frac{dx_i}{dt} = -\zeta\left(x_i^2 - a\right) c_i$, $\frac{de_i}{dt} = (R - 1)\mu - \mu x_i^2 + \beta \sum_{j=1} J_{ij} x_j$, $a(t) = a + \rho \tanh(\delta \Delta H(t))$, and $\xi = f(r - i_c)$, where $a(t)$ denotes the squared target oscillation amplitude, and $R$ the pump schedule parameter. After integrating these differential equations, the values of the variables $x_i$ are projected into the ±1 domain.

This solver considers four parameters, $a$, $\beta$, $\Gamma$, and $R$, and the resources are given by the number of shots that account for the integration of the differential equations, simulating the execution in the hardware of the CIM. We use a Python-based simulation library CIM-optimizer [34] to simulate CIM-CAC.

**Solver 2: Parallel Tempering.** Replica exchange MCMC sampling [40], which is also known as parallel tempering, aims to overcome the issues faced by simulated annealing [41] by initializing multiple 'replicas' at different temperatures. The replicas undergo some Metropolis-Hastings updates, followed by a temperature swap between two replicas. Here, we briefly describe the solver and parameters determining the solver's performance and refer the reader to [42, 43] for more details.

In parallel tempering, several replicas $n_R$ are initiated at temperatures ranging between user-determined $T_{min}$ and $T_{max}$, that control how likely a spin flip will occur in a Metropolis update. Further, $\rho_{cold}$ and $\rho_{hot}$, that control how likely a spin flip will occur in a Metropolis update. Further, $\rho_{cold}$ and $\rho_{hot}$, that control how likely a spin flip will occur in a Metropolis update. Further, $\rho_{cold}$ and $\rho_{hot}$, that control how likely a spin flip will occur in a Metropolis update. Thus, the main idea is that with a given amount of resource budget, a fraction of those resources (ExploFrac) are spent exploring the parameter space to get a sense of which parameters are suitable and, then, using the knowledge obtained, spend the remaining resources running the solver with the well-tuned choice of parameters. $p_{cold} = \max\left\{exp\left(\frac{-dE_{cold}}{T}\right)\right\}$ and $p_{hot} = \exp\left(\frac{-dE_{hot}}{T}\right)$, where $\Delta E_{cold} = 2 \min_{\mu,\nu} |U_{\mu}|$, $\Delta E_{hot} = 2 \max_{\mu,j} |U_j|$.

**Choice of Problems for Benchmarking: Wishart Instances.** The Python library Chook [45] was used to generate 50 instances for each size $N$.

### Operational resources and constraints: Solution methods.

We seek to minimize the energy of a class of zero-field Ising models, i.e., $\min_{s \in \{-1,1\}^N} \sum_{i,j} J_{ij}\sigma_i\sigma_j = \min_{s \in [\pm 1]^N} s^T J s$. The bitstring that minimizes the problem, $s^*$, and its corresponding objective or ground state energy, $s^* J s^*$, are desired. For this illustrative example, we consider two solvers: parallel tempering and a chaotic amplitude control coherent Ising machine simulator. Both methods were run on a single Ivy Bridge Node of the SuperComputer Pleiades, which counts with two Intel Xeon E5-2680v2 (2.8 GHz) processors per node, 3.2 GB RAM per core, 64 GB RAM node. The resource considered here was the number of reads of the problem variables, also called spins given their ±1 nature, which is proportional to the time executed.

The values of $J$ are selected from the Wishart ensemble [44] to generate problem instances with planted solutions. In particular, they correspond to the solution of the nullspace of a system of linear equations, i.e., $W s^* = 0$ where $W \in \mathbb{R}^{rows \times columns}$, out of which after a perturbation with Gaussian noise, the $J$ matrix is constructed. The difficulty of these problems is controlled by a parameter $\sigma$ of rows / columns, with a non-monotonic easy-hard-easy profile as $0 < \sigma < 1$ is varied, with a critical value of $\sigma = 0.2$. We choose $\sigma = 0.5$ for illustrative purposes in the following unless otherwise noted.

The Python library Chook [45] was used to generate 50 instances for each size $N$.

## Strategy Plots: Parameters

| Strategy Plots: Meta-Parameters |
|---|

**Fig. 4:** Parameter strategy plots applied to (left) CIM-CAC [34] and (right) PyS A [35]. Same instances and legends as Fig. 3. (generated by **Stochastic-Benchmark**)

In addition to $n_R$, the execution time is affected by another parameter, the number of sweeps $s$, which denotes the number of Metropolis updates to be implemented in the algorithm. Thus, the solver takes four parameters, $n_R$, $p_{cold}$, $p_{hot}$, and the resources are given by $n_R * s$ shots, accounting for a serial execution of the replicas. We benchmark the Python-based implementation of parallel tempering PyS A [35].

**Choice of Problems for Benchmarking: Wishart Instances.** The Python library Chook [45] was used to generate 50 instances for each size $N$.

### Figure of merit: Performance Ratio.

We quantify the performance using a **normalized performance score** defined as follows:

$$\text{Performance Score} = \frac{\text{(best found solution - random solution)}}{\text{(optimal solution - random solution)}}$$

Thus, the score ranges from 0, when the solver performs no better than random sampling, to 1, when the solver obtains the optimal solution. Considering that we know the solution a priori (since the Wishart instances have known solutions by design), this performance score will be closely related to the optimality gap.

### Accessible prior information.

Although the solvers did not use any particular structure of the problems when solving the Wishart instances, their developers guided us through the ranges of the parameter values discussed below for performance. This indication was based solely on the size of the instances, and the problem structure was not revealed to the developers to avoid biases in the parameter recommendation.

### Parameter setting and strategy.

We provide a search space for each of the parameters considered usually over a uniform distribution around nominal values provided by the developers, except for the transition probabilities in parallel tempering, which were varied in truncated normal distributions to avoid numerical errors of the solvers. A grid for the meta parameters for Hyperopt, namely ExploFrac and $\tau$ (the resource cost of every query during the exploration phase) and the distributions for the parameters are reported in Appendix A.

### Success test.

To obtain the performance profile the "Window stickers", we analyze the performance module like the "Window stickers". We analyze the performance module like the performance module the cross-validated results. The results are automatically produced by the **Stochastic-Benchmark** software and are part of the examples in the repository [31].

## Results.

The cross-validated performance profiles for both technologies, obtained from 10 test-train splits of 50 instances chosen from the Wishart planted ensemble corresponding to $N = 50$ and $\sigma = 0.5$ are shown in Fig. 3. The framework also returns the best average values of parameters and meta-parameters for each technique and have been plotted in Figs. 4 and 5. These values are intended as suggestions the framework generates to obtain the best performance. To generate these recommendations, instead of splitting the problem instances into test and train sets, all problem instances are treated as the training set.

**Performance: CIM-CAC vs PySA - Wishart N = 50, σ = 0.5**

**Scaling of Performance with N at Resource = 9s**

**Fig. 6:** (Left) Performance Comparison: the performance profiles of CIM-CAC [34] and PyS A [35] overlaid on the same plot, with resource chosen to be the wall clock time. (Right) Scaling of performance for both technologies with $N = \{30, 50, 80, 100\}$. (generated by **Stochastic-Benchmark**)

The resulting plots provide a succinct representation of large amounts of information, highlighting how to better execute these solvers when addressing new instances. Moreover, it allows for more specialized analysis. We include in Fig. 6 two examples, a matching of both methods with the same resource, in this case, wall-clock time, leading to a head-to-head comparison of the methods, and an instance size scaling analysis. By observing the N=50 results, it is apparent that in this illustrative case, our analysis allows to evaluate the benefit of using CIM-CAC with Hyperopt-Exploration-Exploitation [3] and F-Expl-Frac=0.3 versus all other tested options, if provided a sufficient amount of time (at least 10 seconds for this case). However, if the number of resources is not allowed to increase, it seems that PyS A with a fixed PSS is the best solver for larger problems (right plot).

## 5 Conclusions

We presented an approach to benchmarking the performance of hybrid quantum-classical algorithms and physics-based algorithms based on a characterization of parametrized stochastic optimization solvers. In addition, we introduced methods for conscientious benchmarking that provide a scheme for holistic reporting of algorithmic performance. The analysis presented here is well suited for stochastic optimization methods, among which we classify the quantum methods for optimization, e.g., quantum annealing and gate-based variational parametric algorithms. The main contribution is a set of rules that characterize what an objective benchmarking procedure needs to consider, particularly with solvers spanning different hardware architectures and software implementations. This approach can be made useful for broad usage by the community. Moreover, the methodology presented here allows for comparing different setups for a given solver, making it useful for parameter setting and tuning procedures.

## A Parameter values for illustrative examples

### A.1 CIM-CAC

Nominal values: $time\_step = 0.00625$, $R = -10.0$, $alpha = 0.25$, $beta = 0.0020$, $gamma = 0.08$, $\delta = 10$, $\mu = 0.5$, $\rho = 5$, $tau = 2000$, $noise = 0.5$, $T = 5000$.

Search spaces:
- $\beta \sim UNIFORM(\text{beta}, \min(\text{beta} - 0.5, \text{beta} * 1.5), \max(\text{beta} * 0.5, \text{beta} * 1.5))$
- $R \sim UNIFORM(R, \min(R + 0.1, R * 10.0), \max(R * 0.1, R * 10.0))$
- $T \sim UNIFORM(\text{gamma}, \min(\text{gamma} = 0, \text{gamma} * 2.0), \max(\text{gamma} = 0, \text{gamma} * 2.0))$
- $\alpha \sim UNIFORM(\text{alpha}, \min(\text{alpha} = 0.1, \text{alpha} * 10.0), \max(\text{alpha} = 0.1, \text{alpha} * 10.0))$
- $\tau = \{11, 16, 21, \ldots, 501\}$
- $ExploFrac = \{0.05, 0.10, 0.15, \ldots, 1.00\}$

### A.2 PySA

Search spaces:
- $Sweeps: s \sim LogUNIFORM(10^0, 10^4)$
- $Replicas: n_R \sim \text{round}(UNIFORM(1, 128))$
- $p_{cold} \sim \max(\text{logNORMAL}(10^0, 10^1), 0.01)$
- $p_{hot} \sim \max(\text{NORMAL}(50, 10), 0.1)$
- $\tau = \{10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000\}$
- $ExploFrac = \{0.05, 0.1, 0.2, 0.3, 0.5, 0.6, 0.75\}$

## Acknowledgments

We thank the NASA Quantum AI Laboratory (QuAIL) for valuable discussions, especially Salvatore Mandrà, Max Wilson, and Jeffrey Marshall. The authors thank the CIM-Optimizer and PyS A developers for their advice on parameter tuning and the Pleiades supercomputer team for support in running the experiments. This work was supported by NSF CCF (#1918549) and NSF CNS (#1824470) and NASA Academic Mission Services (contract NNA16BD14C - funded under 5AA2-403506) and DARPA under IAA 8839 Annex 130. R.B. acknowledges support from the NASA/USRA Feynman Quantum Academy internship program, and P.S. acknowledges support from the USRA internship program.

## Bibliography

[1] John Preskill. Quantum computing in the NISQ era and beyond. *Quantum*, 2:79, 2018.

[2] Dagur I Albertsson and Ana Rusu. Highly reconfigurable oscillator-based Ising Machine through quasiperiodic modulation of coupling strength. *IEEE Revue*, 131(4005, 2023.

[3] Peter L McMahon, Alireza Marandi, Yoshitaka Haribaru, Ryan Hamerly, Carsten Langrock, Shuhei Tamate, Takahiro Inagaki, Hiroki Takesue, Shoko Utsunomiya, Kazuyuki Aihara, et al. A fully programmable 100-spin coherent Ising machine with all-to-all connections. *Science*, 354(6312):614–617, 2016.

[4] Kerem Y Camsari, Brian M Sutton, and Supriyo Datta. *p-bits for probabilistic spin logic. *Applied Physics Reviews*, 6(1), 2019.

[5] Salaam Piroet, Philip Cicero, and Rameet Salauddin. Logically synthesized and hardware-accelerated restricted boltzmann machines for combinatorial optimization. *Nature Electronics*, 5(2):92–101, 2022.

[6] Minsung Kim, Salvatore Mandrà, David Venturelli, and Kyle Jamieson. Physics-inspired heuristics for 5g new radio and beyond. In *Proceedings of the 27th Annual International Conference on Mobile Computing and Networking*, pages 42–52, 2021.

[7] Abhishek Kumar Soni, Kyle Jamieson, Peter L McMahon, and Davide Venturelli. Ising machines' dynamics and regularization for near-optimal radio resource allocation. *IEEE Transactions on Wireless Communications*, 21(2):1003–1004, 2022.

[8] Maximillian A Perez. Transitioning quantum atomic technologies from the lab to the real world. In *Quantum Photonics: Enabling Technologies*, volume 11579, page 115790E. SPIE, 2020.

[9] Corneliu Daloeau Dabous, Louis Paul Henrich, Minjyuk Kim, Jaewook Ahn, and Loic Henriet. Exploring the impact of graph locality for the resolution of the maximum-independent-set problem on neutral atom devices. *Physical Review A*, 108(5):052423, 2023.

[10] Ruben S Javvadi, Marita M Schneezer, Pierre Minssen, Konnara Yalovetzky, Shouvanic Chakaborty, Dylan Pletman, Niraj Kumar, Grant Salton, Ruslan Shaydulin, Yue Sun, et al. Hardness of the maximum-independent-set problem on unit-disk graphs and prospects for quantum speedup. *Physical Review Research*, 5(4):043277, 2023.

[11] Youngseok Kim, Andrew Eddins, Sajant Anand, Ken Xuan Wei, Ewout Van Den Berg, Sami Rosenblatt, Hasan Nayeh, Yantao Wu, Michael Zaliel, Kristen Temme. Evidence for the utility of quantum computing before fault tolerance. *Nature*, 618(7965):500–505, 2023.

[12] Filip B Mauchley, Stuart Hadfield, Benjamin Hall, Mark Hodson, Maxime Dupont, Bram Evert, James Sud, M Sohaib Alam, Zhihui Wang, Stephen Jeffrey, et al. Design and execution of quantum circuits using tens of superconducting qubits and thousands of gates for dense ising optimization problems. *arXiv preprint arXiv:2208.12423*, 2023.

[13] Andrew D King, Juan Carrasquilla, Jack Raymond, Isil Orizdan, Evgeny Andriyash, Andrew Berkley, Mauricio Reis, Trevor Lanting, Richard Harris, ... and Mohammad H Amin. Observation of topological phenomena in a programmable lattice of 1,800 qubits. *Science*, 360(735):358–360, 2018.

[14] Carleton James Coffin. On the emerging potential of quantum annealing hardware for combinatorial optimization. Technical report, Los Alamos National Laboratory (LANL), Los Alamos, NM (United States), 2023.

[15] Naeimeh Mohseni, Peter L McMahon, and Tim Byrnes. Ising Machines as Hardware Solvers of Combinatorial Optimization Problems. *Nature Reviews Physics*, 4(6):363–379, June 2022.

[16] Robin Brown, David E Bernal Neira, Davide Venturelli, and Marco Pavone. A copasitive framework for analysis of hybrid ising-classical algorithms. *arXiv preprint arXiv:2207.13630*, 2022.

[17] Maxime Dumont, Brum Evert, Mark J Hodson, Bhuvnesh Sundar, Stephen Jeffrey, Yuki Yamaguchi, Dennis Feng, Filip B Matejewski, Stuart Hadfield, and Nikolai Alam, et al. Quantum-enhanced greedy combinatorial optimization solver. *Science Advances*, 9(9):eadi5487, 2023.

[18] Catherine C McGeoch. Benchmarking D-wave quantum annealing systems: some challenges. In *Electro-Optical and Infrared Systems: Technology and Applications, 9748*, pages 264–273. SPIE, 2015.

[19] Scott Aaronson. Quantum computing motte-and-baileys, 2019. https://scottaaronson.blog/7p-4447.

[20] John R Rice. The algorithm selection problem. In *Advances in computers*, volume 15, pages 65–118. Elsevier, 1976.

[21] Elizabeth D Dolan and Jorge J Moré. Benchmarking optimization software with performance profiles. *Mathematical programming*, 91(2):201–213, 2002.

[22] Nicholas Gould and Jennifer Scott. A note on performance profiles for benchmarking software. *ACM Transactions on Mathematical Software (TOMS)*, 43(2):1–5, 2015.

[23] Thomas Barth-Bielstein, Carola Dorer, Dean van den Berg, Jakob Bossek, Sowmya Chandraskaran, Tome Eftimov, Andreas Fischbach, Pascale Kerschke, William La Cava, Manuel Lopez-Ibanez, Katherine M Malibu, Haoqi Liu, Niels, Boris Naujoks, Patryk Orzechowski, Vanessa Volz, Markus Wagner, and Thomas Weise. Benchmarking in optimization: Best practice and open issues, 2020.

[24] Michael B Bieseick, Steven P Dirseke, and Stefan Vigerske. PAVER 2.0: an open source environment for automated performance analysis of benchmarking data. *Journal of Global Optimization*, 59:259–275, 2014.

[25] Thomas Mcenan, Mathieu Messina, Alexandre Granfort, Pierre Albin, Pierre-Antoine Bannier, Benjamin Chartier, Mathieu Da Greou, Tom Dupre la Tour, Ghislain Durif, Cassio F Duartes, et al. Benchopt: Reproducible, efficient and collaborative optimization benchmarks. *Advances in Neural Information Processing Systems*, 35:25404–25421, 2022.

[26] Wei Dai and Daniel Berletsnt. Benchmarking contemporary deep learning hardware and frameworks: A survey of qualitative metrics. In *2019 IEEE First International Conference on Cognitive Machine Intelligence (ICMI)*, pages 134–155. IEEE, 2019.

[27] James Bergstra, Daniel Yamins, and DD Cox. Hyperopt: Distributed asynchronous hyper-parameter optimization. *Astrophysics Source Code Library*, record ascl:2207.2022, 2022.

[28] James King, Sheir Yarkoni, Mayssam M. Nevisi, Jeremy P Hilton, and Catherine C. Mcgeoch. Benchmarking a quantum annealing processor with the time-to-target metric. *arXiv preprint*, 2015.

[29] Dailyh Uskov, Jonathan Wurtz, Cody Poole, Mark Saifman, Tom Noel, and Yuri Alexeev. Sampling frequency thresholds for the quantum advantage of the quantum approximate optimization algorithm. *npj Quantum Information*, 9(1):73, 2023.

[30] Daniel Mills, Severin Bruedle, Travis L Scholten, and Ross Duncan. Application-motivated, holistic benchmarking of a full quantum computing stack. *Quantum*, 5:415, 2021.

[31] David E. Bernal Neira, Robin Brown, Pratik Sathe, and Davide Venturelli. Stochastic Benchmark: toolkit for performance evaluation and parameter tuning of stochastic parametrized of stochastic optimization solvers, September 2023.

[32] Dimitris Psaraftis and David Drossos. Stochastic optimization: a review. *International Statistical Review*, 70(3):315–349, 2002.

[33] Endre Boros and Peter L. Hammer. Pseudo-boolean optimization. *Discrete applied mathematics*, 123(1-3):155–225, 2002.

[34] Francis Chen, Brian Isakov, Tyler King, Timothee Leleu, Peter McMahon, and Davide Venturelli. CIM-Optimizer: A Simulator of the Coherent Ising Machine. October 2022. https://github.com/mcmahon-lab/cim-optimizer.

[35] Salvatore Mandrà, Ato Akbari Asanjan, Lucas Brady, Aaron Lott, and David E. Bernal Neira. PyS A: Fast Simulated Annealing in Native Python. 2023. https://github.com/nasa/pysa.

[36] Zhe Wang, Alireza Marandi, Kai Wen, Robert L Byer, and Yoshihisa Yamamoto. Coherent Ising machine based on degenerate optical parametric oscillators. *Physical Review A*, 88(6):063853, 2013.

[37] Timothee Leleu, Farad Knorytae, Timothee Leleu, Ryan Hamerly, Takashi Kohno, and Kazuyuki Aihara. Scaling Advantage of Chaotic Amplitude Control for High-Performance Combinatorial Optimization. *Communications Physics*, 4(1):1–10, December 2021.

[38] Sam Biehestein, Satoshi Ikeda, Farad Knorytae, Timothee Leleu, and Yoshihisa Yamamoto. Coherent ising machines with optical error correction circuits. *Advanced Quantum Technologies*, 4(11):2100077, 2021.

[39] Robin Brown, Davide Venturelli, Marco Pavone, and David E Bernal Neira. Accelerating continuous variable coherent Ising machines via momentum. *arXiv preprint arXiv:2401.12145*, 2024.

[40] Koji Hukushima and Koji Nemoto. Exchange Monte Carlo method and application to spin glass simulations. *Journal of the Physical Society of Japan*, 65(6):1604–1608, 1996.

[41] S. Kirkpartrick, C. D. Gelatt, and M. P. Vecchi. Optimization by Simulated Annealing. *Science*, 220(4598):671–680, May 1983.

[42] Zheng Zhu, Andrew J Chison, and Helmut G Katzgraber. Efficient Cluster Algorithm for the Fully Frustrated two-dimensional Ising models. *Physical Review Letters*, 115(7):077201, August 2015.

[43] Salvatore Mandrà and Helmut G. Katzgraber. A Deep Steps towards Quantum Speedup Detection. *Quantum Science and Technology*, 3(4):04LT01, July 2018.

[44] Firar Hamze, Jack Raymond, Christopher A. Pattison, Katja Biswas, and Helmut G. Katzgraber. Wishart Planted Ensemble: A Tunable Rugged Pairwise Ising Model with a First-Order Phase Transition. *Physical Review E*, 101(5):052102, May 2020.

[45] Dilina Perera, Inanfor Akpabio, Firar Hamze, Salvatore Mandrà, Nathan Rose, Malibeh Amaron, and Helmut G Katzgraber. Chook-a comprehensive suite for generating binary optimization problems with planted solutions, 2020.
