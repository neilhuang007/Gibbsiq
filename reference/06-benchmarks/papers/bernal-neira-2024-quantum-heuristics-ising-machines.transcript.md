---
source_pdf: E:\projects\Gibbsiq\reference\06-benchmarks\papers\bernal-neira-2024-quantum-heuristics-ising-machines.pdf
extraction_date: 2026-05-28
extraction_tool: pdftotext -raw -enc UTF-8
notes: Cleaned text-flow extraction; equations, tables, figures, and page headers/footers still require manual checking against the PDF.
---

Benchmarking the Operation of Quantum Heuristics and Ising Machines:
Scoring Parameter Setting Strategies on Optimization Applications
David E. Bernal Neira1,2,3
, Robin Brown1,4
, Pratik Sathe1,5
, Filip Wudarski1
,
Marco Pavone4
, Eleanor G. Rieffel2
, and Davide Venturelli1,2,⋆
1
USRA Research Institute for Advanced Computer Science (RIACS), Moffett Field, CA, USA
2
Quantum AI Laboratory (QuAIL), NASA Ames Research Center, Moffett Field, CA, USA
3
Davidson School of Chemical Engineering, Purdue University, West Lafayette, IN, USA
4
Autonomous Systems Laboratory, Stanford University, Palo Alto, CA, USA
5
Department of Physics and Astronomy, University of California at Los Angeles, Los Angeles, CA, USA
Abstract. We discuss guidelines for evaluating the performance of parameterized stochastic solvers for optimization
problems, with particular attention to systems that employ novel hardware, such as digital quantum processors running
variational algorithms, analog processors performing quantum annealing, or coherent Ising Machines. We illustrate
through an example a benchmarking procedure grounded in the statistical analysis of the expectation of a given per-
formance metric measured in a test environment. In particular, we discuss the necessity and cost of setting parameters
that affect the algorithm’s performance. The optimal value of these parameters could vary significantly between in-
stances of the same target problem. We present an open-source software package that facilitates the design, evaluation,
and visualization of practical parameter tuning strategies for complex use of the heterogeneous components of the
solver. We examine in detail an example using parallel tempering and a simulator of a photonic Coherent Ising Ma-
chine computing and display the scoring of an illustrative baseline family of parameter-setting strategies that feature an
exploration-exploitation trade-off.
Keywords: Benchmarking · Ising Solvers · Quantum Computing
1 Introduction
We present an approach to benchmarking the performance of hybrid quantum-classical algorithms and quantum-inspired
algorithms based on a characterization of parameterized stochastic optimization solvers. Technological progress in quan-
tum computing and engineering has led to the proliferation of generic quantum computational methods, algorithmic
applications, and hardware platforms where they can be tested. The Noisy-Intermediate-Scale-Quantum (NISQ) [1] era
has catalyzed a myriad of ideas and implementations of physics-based hardware approaches to optimization that do not
benefit from superposition and entanglement but whose performance is nonetheless grounded in complex, difficult-to-
simulate dynamics. One class of such approaches is optimization solvers whose search algorithm is described by many
coupled stochastic partial-differential equations. These methods include analog computing with oscillator [2], and opti-
cally Coherent Ising Machines (CIMs) [3]. Another approach is given by probabilistic bits, better known as p-bits, an
intermediate between the standard bits of digital electronics and the emerging qubits of quantum computing [4, 5] and
that can be physically implemented as perpendicular magnets. In perhaps an abuse of terminology, these physics-based
solvers are often named quantum-inspired systems. Recent examples of the utilization of physics-inspired technologies
include the design of 5G telecommunication networks via Coerent Ising Machines and Parallel Tempering [6, 7]. Another
class of approaches are parametrized quantum circuits encoding variational algorithms such as the quantum approximate
⋆
dventurelli@usra.edu
arXiv:2402.10255v1
[quant-ph]
15
Feb
2024
2 Benchmarking the Operation of Quantum Heuristics and Ising Machines
optimization algorithm (QAOA) or quantum annealing. This type of quantum computation has been implemented on a
variety of platforms, including ion traps [8], neutral atoms [9, 10] and superconducting qubits [11, 12].
data
power, memory, precision,
algorithmic tuning, etc.
variable resource
parameters
SOLVER
= {αn}
output
solu�on
010101101110011
strategy
SOLUTION METHOD
�me
input
Fig. 1: Abstract conceptualization of a solution method and a solver. The black box indicates the core processing optimizer
(e.g., a quantum device) primarily responsible for the method performance.
Empirical observations reveal that quantum and analog solvers can have an advantage over random search, produc-
ing probability distributions that potentially yield high-quality solutions [6, 12, 13, 14, 15]. However, these solvers often
struggle to generate samples of the global optimum and cannot guarantee its optimality, especially in the presence of
noise. Existing techniques to address this issue, such as error mitigation, primarily focus on enhancing the quality of
scalar observables, such as the expectation values of functions, rather than correcting the algorithm’s output (bitstrings)
[11]. Several other means can be employed to address this issue. First, improving the distribution of solution quality can
be achieved through pre-processing techniques and tuning the algorithm’s parameters. This is an issue for practical ex-
pected performance since good parameter settings might not be generalizable to other problem instances, success metrics,
or available resources. Moreover, the parameter-tuning strategy is resource-consuming and must be reported when dis-
cussing the solvers’ expected performance. Second, by designing solution methods that leverage the solver’s capabilities
to enhance the expectation value itself, the weaknesses of these methods can be mitigated by algorithmic approaches, e.g.,
[16, 17]. Assessing the performance of such methods becomes challenging as the specific sub-problems’ solution only
accounts for a portion of the total solution method.
As these quantum and quantum-inspired methods improve performance and capabilities, the problems they can solve
become more sophisticated. Since the purpose of NISQ systems and quantum-inspired Ising machines is to solve prob-
lems, it is paramount to rigorously benchmark their performance [18]. There is a need to develop guidelines on evaluating
the performance of new computing devices in the context of their future deployment in production, i.e., guidelines for
an operational benchmarking as opposed to previous efforts that were mostly confined to research and development en-
vironments. A full operational evaluation must include overheads such as the cost of tuning. Without considering such
overheads, it is easy to come to conclusions that would be misleading [19].
We propose a benchmarking framework supported by an open-source software package intended to collect statistically
relevant data when running a parameterized stochastic optimization solver attempting to solve instances from a distribution
of representative problems. This work aims to provide guidelines for presenting “Window stickers” - i.e., a user-friendly
and self-explanatory scorecard displaying the real-world performance expectation of a self-contained method using fixed
and varying resources to solve applied problems of interest. While our considerations will mainly focus on optimiza-
Benchmarking the Operation of Quantum Heuristics and Ising Machines 3
tion systems, this approach can be adapted to other computational tasks (e.g., sampling, learning) and platforms (e.g.,
neuromorphic chips).
Algorithmic benchmarking dates back to the 70s with the work in [20] on algorithm selection based on performance.
These ideas have been applied to optimization algorithms, where performance profiles [21] are among the most popular
proposals. These diagrams show the performance of different optimization algorithms, reporting the number of problems
each method can solve with respect to time. These diagrams, although criticized for misleading conclusions when includ-
ing more than two algorithms [22], have been widely used in the literature. Best practices have been proposed to provide
the most informative benchmark analysis reported in [23]. Among these best practices, an automated software tool for
benchmarking ensures reproducibility guarantees, for which several tools have been proposed [24, 25].
Parameter setting can be understood as an algorithm selection, where each parameterization is interpreted as a separate
algorithm. Hyper-parameter tuning and benchmarking are also relevant in other fields of computational algorithms, such
as machine learning [26], where hardware accelerators provide advantages that need to be quantified across the boundaries
of different hardware implementations. Several tools have been proposed to automate this parameter setting in that context,
e.g., Hyperopt [27].
Although there is a rich literature on algorithmic selection and parameter setting, quantum and physics-inspired op-
timization methods have characteristics that make their benchmarking unique and challenging [18]. For example, new
performance metrics, such as Time-to-target [28], have been proposed to represent the trade-offs between solution quality
and efficiency for these methods, and recently there starts to be more emphasis on measuring performance as a function
of resources employed and distinguishing classes of instances [29]. Note that many quantum computer benchmarks have
been mainly focused on circuit sizes that can be implemented without noise affecting their fidelity [30]. Additionally, in
the NISQ era, quantum devices performance fluctuates over time, requiring frequent calibration. This introduces an extra
layer of noise in the observed output distributions to be factored in in a benchmark.
For instance, this work aims to develop a methodology that adapts well to these quantum and physics-inspired methods
for optimization, with supporting software to automate the benchmarking and parameter setting strategies and correctly
account for these costs to provide practical and actionable information about solver performance. We list our contributions
below:
– Characterization of solution methods as instantiation of parameterized stochastic optimization solvers (see Fig. 1)
– Proposal of benchmarking, visualizing and designing parameter setting strategies (see Fig. 2)
– Implementation in open-source software Stochastic-Benchmarking [31]
Ultimately, the question that such a pragmatic benchmarking procedure should answer can be framed as: given well-
specified resources and a new, previously unseen problem instance from a known distribution, what are the expectations
for its resolution with a specific solution method? As discussed throughout this paper, the key to answering this question
is to properly define the concepts of resources, expectations, solution, and solution method. In particular, the definition of
the solution method has to address how various parameters that define the solver are set (see Fig. 1).
2 Solution Methods and Parameterized Stochastic Solvers
This study uses a framework focused on analyzing parameterized stochastic optimization solvers. Here, a “solver" is an
integrated system, where hardware (the device) and software (algorithms) work together to solve optimization problems.
Solvers have multiple parameters that can significantly affect their performance, but these effects are usually unknown
beforehand. For our analysis, the solver is seen as a sampler of random variables of an unknown distribution, a concept
familiar in classical optimization as stochastic optimization methods [32]. This approach is relevant for quantum heuristics
and Ising machines, as they fit well within this category of optimization methods.
4 Benchmarking the Operation of Quantum Heuristics and Ising Machines
The raw output of such stochastic methods is a finite set, or string, of N bits or binary values {zi | zi ∈ {0, 1}}, obtained
by a single measurement at the end of the computation ∥
, to which we associate a vector variable z = {z1, . . . , zN}. The
algorithm description does not specify how the distribution is updated or how the samples are obtained.
Additionally, the stochastic nature of these solvers generates a distribution of solutions, which necessitates applying
postprocessing techniques to determine the required output. A comparison between stochastic optimization algorithms
and deterministic solution methods, which return the same solution to a problem every time they are executed and might
even provide guarantees on the optimality of such a solution, might not be valid in general, given the heuristic nature
of sampling associated with stochastic methods. From the bitstring z, we can define a transformed real-valued variable
X = fun(z), where fun : BN
→ R is known as a pseudo-Boolean function [33]. ** This variable, defined by a scalar
function, takes the bitstring values and returns a real-valued cost or objective. This variable X can represent the solver’s
progress toward solving a single problem. The solver’s performance can then be assessed through variable X, which can
subsequently be used to learn how this solver behaves across different problem instances and compared against other
solvers.
Analyzing experimental results from specific cases is crucial to accurately benchmark solvers, which perform differ-
ently across various problem instances. This helps determine the solver’s effectiveness for specific problem classes or
families, requiring analysis over multiple instances. In studying stochastic solvers, the objective is to estimate the prob-
ability density function (PDF) of the output variable X based on the samples collected during the solution process. This
PDF offers empirical insight into the distribution the solver samples from. Stochastic solvers lead to a change in the solu-
tion paradigm, where the new goal is to skew these distributions towards the desired output and sample it as efficiently as
possible. In this perspective, deterministic solvers search over a Dirac delta distribution centered at the optimal solution;
in this case, sampling becomes irrelevant, and the deterministic search becomes equivalent to finding such a distribution.
Additionally, we focus on reporting the output for variable X and the confidence level in ensuring a specific solution
quality for a new, unknown problem instance within the targeted instance class.
Benchmarking Framework. Following the concepts for a reproducible benchmark, we present our framework as shown
in Fig. 2. We consider an instance generation procedure, which generates a population of instances containing enough in-
formation to predict behavior over a new, unseen problem based on their solution. This procedure is followed by selecting
(meta-)parameter values for evaluating the different parameter search strategies (PSSs). After establishing a performance
metric, we set the benchmark.
The solution methods are then run by (attempting to) solve the instances to identify promising solver parameters for
the figure of merit. Recording the solution trajectory for each instance provides the information required to establish the
performance profile of each method. This information can be used to choose the best solution strategy for each value along
the trajectory. Considering this performance envelope, one could construct the virtual best (VB) performance profile. This
would be equivalent to counting with an Oracle, which can tell which solution method is best for each resource value
and each instance. This virtual best also provides a bound on the performance that can be obtained for selecting solution
methods. Moreover, by aggregating the different parameter settings that result in the best performances for each instance,
one can define a fixed parameter setting strategy (fPSS). This method is used extensively in the literature, where, e.g., the
average of each parameter corresponding to the best parameter setting strategy across the different instances is computed
for each resource value. If the aggregation results in a parameter setting not initially included in the PSSs, it should be
rerun for all instances to verify its performance.
One observation is that fixed parameters for the solution methods might perform suboptimally over unseen instances,
as the assumption that the instance population being “well-behaved” or representative might fail. A meta-parameter given
∥
In case of an Ising model framework, it is a spin configuration {σi | σi ∈ {−1, 1}}, however without loss of generality, both
representations are equivalent up to a linear transformation.
**It is well known that any pseudo-Boolean function can be written uniquely as a multilinear polynomial, i.e., fun(z) = c0 +
PN
i=1 c1,izi +
PN
j=i+1 c2,ijzizj +
PN
k= j+1 c3,ijkzizjzk + · · · .
Benchmarking the Operation of Quantum Heuristics and Ising Machines 5
Fig. 2: Flowchart with the main steps to generate the “Window stickers” implemented in Stochastic-Benchmark [31]
to an advanced parameter tuning algorithm can address this, such as Hyperopt [27]. These meta-parameters affect the
behavior of the tuning procedure itself, as well as be used to balance the exploration and exploitation procedures of the
solution method parameter tuning. This exploration-exploitation balance can be expressed by determining which fraction
of a total budget is spent looking for the best parameters and which should be spent exploiting the best-found parameter.
Moreover, during the exploration stage, each parameter setting considered could be explored for a variable amount of
resources, presenting a trade-off between checking many different parameter settings or realizing the potential of each one
explored after investing a larger amount of resources.
All these steps result in a trajectory of (meta-)parameters for evaluation in the solvers. Depending on the solution
methods and the family of instances, these trajectories might need to be made actionable. Namely, they might appear
erratic due to a reduced number of instances or if outliers affect the different aggregations, e.g., across instances or
parameter values. Trajectories are smoothed and then rerun if they do not correspond to any evaluated PSSs to gather
information about their performance. The instance family is divided into training and testing sets to avoid overfitting the
results. The procedure for finding good PSSs is repeated over several different instance splits, and then a cross-validation
scheme aggregates these results.
The resulting “Window stickers” consist then of parameter trajectories or plots that show the value that each parameter
should follow with various resources; meta-parameter trajectories that yield the different parameter settings in adaptive
6 Benchmarking the Operation of Quantum Heuristics and Ising Machines
PSSs, and performance profiles that show the expected merit function response to each different PSS. These analyses can
then be aggregated across different problem families to show scaling performance over a feature of the instances.
3 The Stochastic Benchmark Framework
Stochastic-Benchmark is an open-source package implementing the methodology described in the previous section
[31]. This open-source package introduces a statistical analysis methodology for evaluating and comparing the perfor-
mance of (potentially quantum and quantum-inspired) optimization solvers. By incorporating visual presentation tech-
niques and robust statistical analysis, Stochastic-Benchmark provides researchers with a comprehensive framework
to assess solver performance and facilitate informed decision-making on design and production readiness in the field of
quantum and quantum-inspired optimization. The Stochastic-Benchmark package holds particular relevance for ana-
lyzing quantum-inspired methodologies, which often produce a large set of solutions as outputs. The analysis framework
addresses these issues by providing a general performance comparison and parameter-setting strategy evaluation platform.
To practically implement the methodology illustrated in Fig. 2, we provide an efficient implementation of these meth-
ods. In this section, we proceed to explain how the Stochastic-Benchmark framework operates. Consider that the
following is given:
- Resource to be evaluated R = {r0, . . . rf }.
- Performance metric to be considered P.
- Set of instances I = {i1, . . . , i|I|}.
- Set of solvers S = {s1, . . . , s|S |}.
- Set of pre-evaluated parameters for solver s, α
α
α = {α
α
α1, . . . ,α
α
α|α
α
α|}.
- Set of meta-parameters in case an adaptive PSS is to be included, θ
θ
θ.
For each solver in each parameter setting, s(α
α
αn), a given performance profile is evaluated for each instance, X =
perf[s(α
α
αn), i] = P(r). The ordered set R of resources r ∈ R indicates the energy, time, and memory used for each call
to the solver. Although some solvers provide the information of the performance metric as the progress of the resource,
e.g., the logs provided in mixed-integer programming solvers with incumbent solutions against time, for some quantum-
and physics-based methods, only the final distribution of solution is provided. One could execute the solve for a grid
of resource values, i.e., ∀r ∈ {r0, ..., rf }; however, this would be highly costly considering that access to these solvers is
limited and expensive. We implement the bootstrapping in a parallelizable manner to efficiently regenerate these profiles,
using only the distribution of solutions for the largest result value rf , and compute confidence intervals for these metric
predictions, which are then propagated along the data aggregations in the “Window stickers” framework. By incorporat-
ing confidence intervals, Stochastic-Benchmark provides a robust framework for evaluating solver performance and
comparing different algorithms.
The performance profiles, perf[s(α
α
αn), i], are aggregated to compute the VB, fPPS automatically within Stochastic-
Benchmark. Moreover, there is an implementation to perform adaptive PSS by connecting to the hyper-parameter opti-
mizer Hyperopt, and an armed bandit strategy is implemented to evaluate the balance of exploration of parameter values
for solvers and exploitation of the best-found parameters. Thus, the main idea is that with a given amount of resource
budget, a fraction of those resources (ExploreFrac) are spent exploring the parameter space to get a sense of which
parameters are suitable and then, using the knowledge obtained, spend the remaining resources running the solver with
one well-informed choice of parameters.
Each of these PSS outputs a parameter strategy plot, which denotes the variation of the parameter values for dif-
ferent values of resources. Actionable parameter strategy plots can be computed through callbacks in the code, which
allow fitting these parameter profiles by functional forms using the Python numerical computation libraries numpy and
scipy. Finally, the software automatically partitions the instance set in the training and testing sets and repeats the bench-
marking procedure for each partition, ultimately applying a cross-validation technique to tackle the parameter strategies’
overfitting.
Benchmarking the Operation of Quantum Heuristics and Ising Machines 7
4 Illustrative Example
This section describes results obtained by applying the Stochastic-Benchmark framework on an illustrative example.
We describe the operational resources and constraints of the benchmark, the set of problem instances, the figure of merit,
which information is accessible to solvers before the solution of the problems, the parameter setting strategy, and the test
to assess a successful run. We consider these to be the elements of a conscientious benchmark.
Operational resources and constraints: Solution methods. We seek to minimize the energy of a class of zero-
field Ising models, i.e., mins
s
s∈{±1}N
PN
i, j=1 siJijsj = mins
s
s∈{±1}N s
s
s
′
Js
s
s. The bitstring that minimizes the problem, s
s
s∗
, and its
corresponding objective or ground state energy, s
s
s∗′
Js
s
s∗
, are desired. For this illustrative example, we consider two solvers:
parallel tempering and a chaotic amplitude control coherent Ising machine simulator. Both methods were run on a single
Ivy Bridge Node of NASA’s supercomputer Pleiades, which counts with two ten-core Intel Xeon E5-2680v2 (2.8 GHz)
processors per node, and 3.2 GB RAM per core, 64 GB RAM per node. The resource considered here was the number of
reads of the problem variables, also called spins given their ±1 nature, which is proportional to the time executed.
102
103
Resource
0.88
0.90
0.92
0.94
0.96
0.98
1.00
Performance
Score
Cross Validated Performance Profile: CIM-CAC
Virtual Best
Fixed Suggested Parameters
Hyperopt Exploration-Exploitation
104
105
Resource
0.90
0.92
0.94
0.96
0.98
1.00
Performance
Score
Cross Validated Performance Profile: Simulated Annealing
Virtual Best
Fixed Suggested Parameters
Hyperopt Exploration-Exploitation
Fig. 3: Cross-validated performance profiles from 10 test-train splits of 50 Wishart instances with N = 50 and α = 0.5 solved via (left)
CIM-CAC [34] and (right) PySA [35]. The profiles of the virtual best baseline, a Hyperopt-driven exploration-exploitation strategy,
and the fixed best parameters suggested from the experiments are shown. (generated by Stochastic-Benchmark)
Solver 1: Coherent Ising Machine simulator. Ising machines are a class of solvers based on the dynamics of physical
hardware that aims to find the minimum energy solution of the Ising model [15]. Coherent Ising Machines (CIMs) are
an example of Ising machines that exploit mixed-state density operators in a quantum oscillator network [36]. Currently,
the CIM is primarily benchmarked by simulating a quantitative model of its behavior in different applications. Although
this is a widely accepted approach, no single model of the CIMs dynamics exists. Instead, different models with varying
degrees of fidelity have been constructed when modeling quantum mechanical effects. A specific type of CIM model
is called the chaotic amplitude control (CIM-CAC), which seems to provide some advantages over other types of CIM
[37, 38]. Recent improvements have also emerged on the simulated model based on machine-learning insights [39].
A set of ordinary differential equations describes the CIM dynamics. In the case of CIM-CAC, the spin variables are
relaxed to continuous variables xi ∈ [−1, 1], and auxiliary variables ei satisfy dei
dt = −ξ

x2
i − a

ei, dxi
dt = (R − 1)xi − µx3
i +
βei
PN
j=1 Jijxj, a(t) = α+ρ tanh(δ∆H(t)), and ξ = Γ(t−tc), where a(t) denotes the squared target oscillation amplitude, and
R the pump schedule parameter. After integrating these differential equations, the values of the variables xi are projected
into the ±1 domain.
8 Benchmarking the Operation of Quantum Heuristics and Ising Machines
This solver considers four parameters, α, β, Γ, and R, and the resources are given by the number of shots that account
for the integration of the differential system in the time domain, simulating the execution in the hardware of the CIM. We
use a Python-based simulation library CIM-optimizer [34] to simulate CIM-CAC.
Solver 2: Parallel Tempering. Replica exchange MCMC sampling [40], which is also known as parallel tempering,
is a state-of-the-art heuristic to solve Ising-like optimization problems. Parallel tempering aims to overcome the issues
faced by simulated annealing [41] by initializing multiple ‘replicas’ at different temperatures. The replicas undergo some
Metropolis-Hastings updates, followed by a temperature swap between two replicas. Here, we briefly describe the solver
and the parameters determining the solver’s performance and refer the reader to [42, 43] for more details.
In parallel tempering, several replicas nR are initiated at temperatures ranging between user-determined Tmin and Tmax
that can be encoded in terms of two probabilities pcold and phot, that control how likely a spin flip occurs in a Metropolis
update at the Tmin and Tmax respectively. pcold quantifies the probability of the least likely spin flip at the lower temperature,
and phot denotes the likelihood of the most likely spin flip at the higher temperature. Both these probabilities depend on
the J matrix values and can be approximated as pcold = Nmin-gap exp

−−∆Ecold
Tmin

and phot = exp

−∆Ehot
Tmax

, where ∆Ecold
i =
2 minj|Jij,0 |Jij|, ∆Ecold = mini ∆Ecold
i , Nmin-gap is the count of Ecold
i being equal to ∆Ecold, and ∆Ehot = 2 maxi
P
j |Jij|.
0.00105
0.00110
0.00115
Beta
−34
−32
R
1.25
1.50
Alpha
102
103
Resource
0.08
0.09
Gamma
0.96
0.97
0.98
0.99
Performance
Score
Strategy Plots: Parameters
Virtual Best Fixed Suggested Parameters
0
500
Sweeps
0
25
Replicas
1.00
1.25
Pcold
104
105
Resource
25
50
75
Phot
0.92
0.94
0.96
0.98
Performance
Score
Strategy Plots: Parameters
Virtual Best
Projection from TrainingStats
Fixed Suggested Parameters
Fig. 4: Parameter strategy plots applied to (left) CIM-CAC [34] and (right) PySA [35]. Same instances and legends as Fig. 3
. (generated by Stochastic-Benchmark)
In addition to nR, the execution time is affected by another parameter, the number of sweeps s, which denotes the
number of Metropolis updates to be implemented in the algorithm. Thus, the solver takes four parameters, nR, s, pcold and
phot, and the resources are given by nR ∗ s∗ shots, accounting for a serial execution of the replicas. We benchmark the
Python-based implementation of parallel tempering PySA [35].
Choice of Problems for Benchmarking: Wishart Instances. The values of J are selected from the Wishart ensemble
[44] to generate problem instances with planted solutions. In particular, they correspond to the solution of the nullspace
of a system of linear equations, i.e., Ws
s
s∗
= 0 where W ∈ Rrows×columns
, out of which after a perturbation with Gaussian
noise, the J matrix is constructed. The difficulty of these problems is controlled by a parameter α = rows/columns, with
a non-monotonic easy→hard→easy profile as 0 < α ≤ 1 is varied, with a critical value of α ≈ 0.2. We choose α = 0.5 for
illustrative purposes in the following unless otherwise noted.
The Python library Chook [45] was used to generate 50 instances for each size N.
Benchmarking the Operation of Quantum Heuristics and Ising Machines 9
102
103
Resource
0.1
0.2
0.3
0.4
0.5
0.6
0.7
Explorefrac
Strategy Plots: Exploration Fraction
Hyperopt Exploration-Exploitation
0.25
0.50
0.75
Explorefrac
104
105
Resource
0
5000
10000
Tau
Strategy Plots: Meta-Parameters
Hyperopt Exploration-Exploitation
Fig. 5: Meta-parameter strategy plots for exploration-exploitation strategy, applied to (left) the CIM-CAC [34] and (right) PySA [35].
For CIM-CAC, the meta-parameter τ = 1 for all resources probed. The dashed line represents those meta-parameters with best-found
performance, and the continuous line represents the actionable implementation. Same instances and legends as Fig. 3.(generated by
Stochastic-Benchmark)
Figure of merit: Performance Ratio. We quantify the performance using a normalized performance score defined as
follows:
Performance Score =
(best found solution - random solution)
(optimal solution - random solution)
.
Thus, the score ranges from 0, when the solver performs no better than random sampling, to 1, when the solver obtains the
optimal solution. Considering that we know the solution a priori (since the the Wishart instances have known solutions by
design), this performance score would be closely related to the optimality gap.
Accesible prior information. Although the solvers did not use any particular structure of the problems when solving
the Wishart instances, their developers guided us through the ranges of the parameter values discussed below for per-
formance. This indication was based solely on the size of the instances, and the problem type was not revealed to the
developers to avoid biases in the parameter recommendation.
Parameter setting and run strategy. We provide a search space for each of the parameters considered usually over a
uniform distribution around nominal values provided by the developers, except for the transition probabilities in parallel
tempering, which were varied in truncated normal distributions to avoid numerical errors of the solvers. A grid for the
meta-parameters for Hyperopt, namely ExplorFrac and τ (the resource expense of every value queried during the
exploration phase) and the distributions for the parameters are reported in Appendix A.
Success test. To obtain the performance profile (the “Window stickers”), we analyze the performance profiles for ten
test-train splits, with 80% of the instances chosen as training instances and the rest as testing instances. We combine the
confidence intervals and the aggregated value (mean or median) for the performance across all splits to provide cross-
validated results. The results are automatically produced by the Stochastic-Benchmark software and are part of the
examples in the repository [31].
10 Benchmarking the Operation of Quantum Heuristics and Ising Machines
Results. The cross-validated performance profiles for both technologies, obtained from 10 test-train splits of 50 in-
stances chosen from the Wishart planted ensemble corresponding to N = 50 and α = 0.50 are shown in Fig. 3. The
framework also returns the best average values of parameters and meta-parameters for each technique and have been
plotted in Figs. 4 and 5. These values are intended as suggestions the framework generates to obtain the best performance
on unseen problem instances. To generate these recommendations, instead of splitting the problem instances into test and
train sets, all problem instances are treated as the training set.
100
101
Resource = wallclock time [s]
0.93
0.94
0.95
0.96
0.97
0.98
0.99
1.00
Performance
Score
Performance: CIM-CAC vs PySA - Wishart N=50, α=0.5
CIM-CAC
Virtual Best
Fixed Suggested Parameters
Hyperopt
Exploration-Exploitation
PySA
Virtual Best
Fixed Suggested Parameters
Hyperopt
Exploration-Exploitation
PySA
Virtual Best
Fixed Suggested Parameters
Hyperopt
Exploration-Exploitation
30 50 80 100
N
0.5
0.6
0.7
0.8
0.9
1.0
Performance
Score
Scaling of Performance with N at Resource=9s
CIM-CAC
Virtual Best
Fixed Suggested Parameters
Hyperopt
Exploration-Exploitation
PySA
Virtual Best
Fixed Suggested Parameters
Hyperopt
Exploration-Exploitation
PySA
Virtual Best
Fixed Suggested Parameters
Hyperopt
Exploration-Exploitation
Fig. 6: (Left) Performance Comparison: The performance profiles of CIM-CAC [34] and PySA [35] overlaid on the same plot, with
resource chosen to be the wall clock time. (Right) Scaling of performance for both technologies with N = {30, 50, 80, 100}. (generated
by Stochastic-Benchmark)
The resulting plots provide a succinct representation of large amounts of information, highlighting how to better
execute these solvers when addressing new instances. Moreover, it allows for more specialized analysis. We include in
Fig. 6 two examples, a matching of both methods with the same resource, in this case, wall-clock time, leading to a
head-to-head comparison of the methods, and an instance size scaling analysis. By observing the N=50 results, it is
apparent that in this illustrative case, our analysis allow to evaluate the benefit of using CIM-CAC with Hyperopt with
ExplorFrac=0.3 and τ=1 versus all other tested options, if provided a sufficient amount of resources (at least 10 seconds
for this case). However, if the number of resources is not allowed to increase, it seems that PySA with a fixed PSSs is the
best solver for larger problems (right plot).
5 Conclusions
We presented an approach to benchmarking the performance of hybrid quantum-classical algorithms and physics-based
algorithms based on a characterization of parameterized stochastic optimization solvers. In addition, we introduced meth-
ods for conscientious benchmarking that provide a scheme for holistic reporting of algorithmic performance. The analysis
presented here is well fitted for stochastic optimization methods, among which we classify the quantum methods for opti-
mization, e.g., quantum annealing and gate-based variational parametric algorithms. The main contribution is a set of rules
Benchmarking the Operation of Quantum Heuristics and Ising Machines 11
that characterize what an objective benchmarking procedure needs to consider, particularly with solvers spanning different
hardware architectures and software that implements this for broad usage by the community. Moreover, the methodology
presented here allows for comparing different setups for a given solver, making it useful for parameter setting and tuning
procedures.
A Parameter values for illustrative examples
A.1 CIM-CAC
Nominal values: time_step = 0.00625, R = −10.0, alpha = 0.25, beta = 0.0020, gamma = 0.08, δ = 10, µ = 0.5, ρ = 5,
tau = 2000, noise = 0.5, T = 5000.
Search spaces:
– β ∼ UNIFORM(beta, min(beta ∗ 0.5, beta ∗ 1.5), max(beta ∗ 0.5, beta ∗ 1.5))
– R ∼ UNIFORM(R, min(R ∗ 0.1, R ∗ 10.0), max(R ∗ 0.1, R ∗ 10.0))
– Γ ∼ UNIFORM(gamma, min(gamma ∗ 0, gamma ∗ 2.0), max(gamma ∗ 0, gamma ∗ 2.0))
– α ∼ UNIFORM(alpha, min(alpha ∗ 0.1, alpha ∗ 10.0), max(alpha ∗ 0.1, alpha ∗ 10.0))
– τ = {11, 16, 21, ..., 501}
– ExplorFrac = {0.05, 0.10, 0.15, ..., 1.00}
A.2 PySA
Search spaces:
– Sweeps:s ∼ LogUNIFORM(100
, 104
)
– Replicas: nR ∼ round(UNIFORM(1, 128))
– pcold ∼ max(logNORMAL(100
, 101
), 0.01)
– phot ∼ max(NORMAL(50, 10), 0.1)
– τ = {10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000}
– ExplorFrac = {0.05, 0.1, 0.2, 0.3, 0.5, 0.6, 0.75}
Acknowledgments
We thank the NASA Quantum AI Laboratory (QuAIL) for valuable discussions, expeciallly Salvatore Mandrà, Max Wilson, and Jeffrey
Marshall. The authors thank the CIM-Optimizer and PySA developers for their advice on parameter tuning and the Pleiades supercom-
puter team for support in running the experiments. This work was supported by NSF CCF (#1918549) and NSF CNS (#1824470) and
NASA Academic Mission Services (contract NNA16BD14C – funded under SAA2-403506) and DARPA under IAA 8839 Annex 130.
R.B. acknowledges support from the NASA/USRA Feynman Quantum Academy internship program, and P.S. acknowledges support
from the USRA internship program.
Bibliography
[1] John Preskill. Quantum computing in the NISQ era and beyond. Quantum, 2:79, 2018.
[2] Dagur I Albertsson and Ana Rusu. Highly reconfigurable oscillator-based Ising Machine through quasiperiodic modulation of
coupling strength. Scientific Reports, 13(1):4005, 2023.
[3] Peter L McMahon, Alireza Marandi, Yoshitaka Haribara, Ryan Hamerly, Carsten Langrock, Shuhei Tamate, Takahiro Inagaki,
Hiroki Takesue, Shoko Utsunomiya, Kazuyuki Aihara, et al. A fully programmable 100-spin coherent Ising machine with all-to-all
connections. Science, 354(6312):614–617, 2016.
[4] Kerem Y Camsari, Brian M Sutton, and Supriyo Datta. P-bits for probabilistic spin logic. Applied Physics Reviews, 6(1), 2019.
[5] Saavan Patel, Philip Canoza, and Sayeef Salahuddin. Logically synthesized and hardware-accelerated restricted boltzmann ma-
chines for combinatorial optimization and integer factorization. Nature Electronics, 5(2):92–101, 2022.
[6] Minsung Kim, Salvatore Mandrà, Davide Venturelli, and Kyle Jamieson. Physics-inspired heuristics for soft mimo detection in
5g new radio and beyond. In Proceedings of the 27th Annual International Conference on Mobile Computing and Networking,
pages 42–55, 2021.
[7] Abhishek Kumar Singh, Kyle Jamieson, Peter L McMahon, and Davide Venturelli. Ising machines’ dynamics and regularization
for near-optimal mimo detection. IEEE Transactions on Wireless Communications, 21(12):11080–11094, 2022.
[8] Maximillian A Perez. Transitioning quantum atomic technologies from the lab to the real world. In Quantum Photonics: Enabling
Technologies, volume 11579, page 1157906. SPIE, 2020.
[9] Constantin Dalyac, Louis-Paul Henry, Minhyuk Kim, Jaewook Ahn, and Loïc Henriet. Exploring the impact of graph locality for
the resolution of the maximum-independent-set problem with neutral atom devices. Physical Review A, 108(5):052423, 2023.
[10] Ruben S Andrist, Martin JA Schuetz, Pierre Minssen, Romina Yalovetzky, Shouvanik Chakrabarti, Dylan Herman, Niraj Kumar,
Grant Salton, Ruslan Shaydulin, Yue Sun, et al. Hardness of the maximum-independent-set problem on unit-disk graphs and
prospects for quantum speedups. Physical Review Research, 5(4):043277, 2023.
[11] Youngseok Kim, Andrew Eddins, Sajant Anand, Ken Xuan Wei, Ewout Van Den Berg, Sami Rosenblatt, Hasan Nayfeh, Yantao
Wu, Michael Zaletel, Kristan Temme, et al. Evidence for the utility of quantum computing before fault tolerance. Nature,
618(7965):500–505, 2023.
[12] Filip B Maciejewski, Stuart Hadfield, Benjamin Hall, Mark Hodson, Maxime Dupont, Bram Evert, James Sud, M Sohaib Alam,
Zhihui Wang, Stephen Jeffrey, et al. Design and execution of quantum circuits using tens of superconducting qubits and thousands
of gates for dense ising optimization problems. arXiv preprint arXiv:2308.12423, 2023.
[13] Andrew D. King, Juan Carrasquilla, Jack Raymond, Isil Ozfidan, Evgeny Andriyash, Andrew Berkley, Mauricio Reis, Trevor
Lanting, Richard Harris, ..., and Mohammad H. Amin. Observation of topological phenomena in a programmable lattice of 1,800
qubits. Nature, 560(7719):456–460, August 2018.
[14] Carleton James Coffrin. On the emerging potential of quantum annealing hardware for combinatorial optimization. Technical
report, Los Alamos National Laboratory (LANL), Los Alamos, NM (United States), 2023.
[15] Naeimeh Mohseni, Peter L. McMahon, and Tim Byrnes. Ising Machines as Hardware Solvers of Combinatorial Optimization
Problems. Nature Reviews Physics, 4(6):363–379, June 2022.
[16] Robin Brown, David E Bernal Neira, Davide Venturelli, and Marco Pavone. A copositive framework for analysis of hybrid
ising-classical algorithms. arXiv preprint arXiv:2207.13630, 2022.
[17] Maxime Dupont, Bram Evert, Mark J Hodson, Bhuvanesh Sundar, Stephen Jeffrey, Yuki Yamaguchi, Dennis Feng, Filip B Ma-
ciejewski, Stuart Hadfield, M Sohaib Alam, et al. Quantum-enhanced greedy combinatorial optimization solver. Science Ad-
vances, 9(45):eadi0487, 2023.
[18] Catherine C McGeoch. Benchmarking D-wave quantum annealing systems: some challenges. In Electro-Optical and Infrared
Systems: Technology and Applications XII; and Quantum Information Science and Technology, volume 9648, pages 264–273.
SPIE, 2015.
[19] Scott Aaronson. Quantum computing motte-and-baileys, 2019. https://scottaaronson.blog/?p=4447.
[20] John R Rice. The algorithm selection problem. In Advances in computers, volume 15, pages 65–118. Elsevier, 1976.
[21] Elizabeth D Dolan and Jorge J Moré. Benchmarking optimization software with performance profiles. Mathematical program-
ming, 91(2):201–213, 2002.
Benchmarking the Operation of Quantum Heuristics and Ising Machines 13
[22] Nicholas Gould and Jennifer Scott. A note on performance profiles for benchmarking software. ACM Transactions on Mathe-
matical Software (TOMS), 43(2):1–5, 2016.
[23] Thomas Bartz-Beielstein, Carola Doerr, Daan van den Berg, Jakob Bossek, Sowmya Chandrasekaran, Tome Eftimov, Andreas
Fischbach, Pascal Kerschke, William La Cava, Manuel Lopez-Ibanez, Katherine M. Malan, Jason H. Moore, Boris Naujoks,
Patryk Orzechowski, Vanessa Volz, Markus Wagner, and Thomas Weise. Benchmarking in optimization: Best practice and open
issues, 2020.
[24] Michael R Bussieck, Steven P Dirkse, and Stefan Vigerske. PAVER 2.0: an open source environment for automated performance
analysis of benchmarking data. Journal of Global Optimization, 59:259–275, 2014.
[25] Thomas Moreau, Mathurin Massias, Alexandre Gramfort, Pierre Ablin, Pierre-Antoine Bannier, Benjamin Charlier, Mathieu Da-
gréou, Tom Dupre la Tour, Ghislain Durif, Cassio F Dantas, et al. Benchopt: Reproducible, efficient and collaborative optimization
benchmarks. Advances in Neural Information Processing Systems, 35:25404–25421, 2022.
[26] Wei Dai and Daniel Berleant. Benchmarking contemporary deep learning hardware and frameworks: A survey of qualitative
metrics. In 2019 IEEE First International Conference on Cognitive Machine Intelligence (CogMI), pages 148–155. IEEE, 2019.
[27] James Bergstra, Daniel Yamins, and DD Cox. Hyperopt: Distributed asynchronous hyper-parameter optimization. Astrophysics
Source Code Library, pages ascl–2205, 2022.
[28] James King, Sheir Yarkoni, Mayssam M. Nevisi, Jeremy P. Hilton, and Catherine C. McGeoch. Benchmarking a quantum
annealing processor with the time-to-target metric, 2015.
[29] Danylo Lykov, Jonathan Wurtz, Cody Poole, Mark Saffman, Tom Noel, and Yuri Alexeev. Sampling frequency thresholds for the
quantum advantage of the quantum approximate optimization algorithm. npj Quantum Information, 9(1):73, 2023.
[30] Daniel Mills, Seyon Sivarajah, Travis L Scholten, and Ross Duncan. Application-motivated, holistic benchmarking of a full
quantum computing stack. Quantum, 5:415, 2021.
[31] David E. Bernal Neira, Robin Brown, Pratik Sathe, and Davide Venturelli. Stochastic Benchmark: toolkit for performance evalu-
ation and parameter tuning of stochastic parameterized stochastic optimization solvers, September 2023.
[32] Dimitris Fouskakis and David Draper. Stochastic optimization: a review. International Statistical Review, 70(3):315–349, 2002.
[33] Endre Boros and Peter L Hammer. Pseudo-boolean optimization. Discrete applied mathematics, 123(1-3):155–225, 2002.
[34] Francis Chen, Brian Isakov, Tyler King, Timothée Leleu, Peter McMahon, and Tatsuhiro Onodera. Cim-Optimizer: A Simulator
of the Coherent Ising Machine, October 2022. https://github.com/mcmahon-lab/cim-optimizer.
[35] Salvatore Mandra, Ata Akbari Asanjan, Lucas Brady, Aaron Lott, and David E. Bernal Neira. PySA: Fast Simulated Annealing
in Native Python, 2023. https://github.com/nasa/pysa.
[36] Zhe Wang, Alireza Marandi, Kai Wen, Robert L Byer, and Yoshihisa Yamamoto. Coherent Ising machine based on degenerate
optical parametric oscillators. Physical Review A, 88(6):063853, 2013.
[37] Timothée Leleu, Farad Khoyratee, Timothée Levi, Ryan Hamerly, Takashi Kohno, and Kazuyuki Aihara. Scaling Advantage of
Chaotic Amplitude Control for High-Performance Combinatorial Optimization. Communications Physics, 4(1):1–10, December
2021.
[38] Sam Reifenstein, Satoshi Kako, Farad Khoyratee, Timothée Leleu, and Yoshihisa Yamamoto. Coherent ising machines with
optical error correction circuits. Advanced Quantum Technologies, 4(11):2100077, 2021.
[39] Robin Brown, Davide Venturelli, Marco Pavone, and David E Bernal Neira. Accelerating continuous variable coherent ising
machines via momentum. arXiv preprint arXiv:2401.12135, 2024.
[40] Koji Hukushima and Koji Nemoto. Exchange Monte Carlo method and application to spin glass simulations. Journal of the
Physical Society of Japan, 65(6):1604–1608, 1996.
[41] S. Kirkpatrick, C. D. Gelatt, and M. P. Vecchi. Optimization by Simulated Annealing. Science, 220(4598):671–680, May 1983.
[42] Zheng Zhu, Andrew J. Ochoa, and Helmut G. Katzgraber. Efficient Cluster Algorithm for Spin Glasses in Any Space Dimension.
Physical Review Letters, 115(7):077201, August 2015.
[43] Salvatore Mandrà and Helmut G. Katzgraber. A Deceptive Step towards Quantum Speedup Detection. Quantum Science and
Technology, 3(4):04LT01, July 2018.
[44] Firas Hamze, Jack Raymond, Christopher A. Pattison, Katja Biswas, and Helmut G. Katzgraber. Wishart Planted Ensemble: A
Tunably Rugged Pairwise Ising Model with a First-Order Phase Transition. Physical Review E, 101(5):052102, May 2020.
[45] Dilina Perera, Inimfon Akpabio, Firas Hamze, Salvatore Mandra, Nathan Rose, Maliheh Aramon, and Helmut G Katzgraber.
Chook–a comprehensive suite for generating binary optimization problems with planted solutions, 2020.

