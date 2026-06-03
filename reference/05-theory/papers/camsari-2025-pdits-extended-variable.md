# Extended-variable probabilistic computing with p-dits


> **Citation.** Canonical entry `duffee2025pdits` in [`references.bib`](../../references.bib) (resolved via Crossref/DataCite). arXiv:[2506.00269](https://arxiv.org/abs/2506.00269).
>
> **Companion note.** [`camsari-2025-pdits-extended-variable.note.md`](./camsari-2025-pdits-extended-variable.note.md) — how this paper links to Gibbsiq.

**Authors:** Kerem Y. Camsari¹*, Shuvro Chowdhury², Mohammad R. Saleh³, Yuki Kawada⁴, Daniele Vodenicarevic⁵, Gianvito Giordano⁶

¹Department of Electrical and Computer Engineering, Purdue University, West Lafayette, IN, USA
²Department of Electrical Engineering, Massachusetts Institute of Technology, Cambridge, MA, USA
³Department of Physics, Massachusetts Institute of Technology, Cambridge, MA, USA
⁴Department of Information and Communication Engineering, University of Tokyo, Tokyo, Japan
⁵SPINTEC, Univ. Grenoble Alpes, CEA, CNRS, Grenoble, France
⁶Dipartimento di Ingegneria dell'Informazione, Università degli Studi di Messina, Messina, Italy

*Corresponding author: kcamsari@purdue.edu

## Abstract

Probabilistic computing has emerged as a promising approach for solving hard optimization and sampling problems through physics-inspired computational paradigms. While p-bits (probabilistic bits) have shown utility in solving constraint satisfaction problems and representing combinatorial optimization, they are limited to binary states. Ising machines based on generalized spin models can represent higher-dimensional solution spaces more naturally. Here, we introduce probabilistic d-dimensional variables (p-dits) that stochastically oscillate between d discrete states, extending the concept of probabilistic computing beyond binary representations. We further specialize this to probabilistic integers (p-ints), which enable more natural representations of numeric values with regular, discrete steps. We demonstrate isotropic p-dits, a symmetric variant particularly suited for representing categorical variables. A key contribution is the implementation of p-dits in CMOS-based application-specific integrated circuits (ASICs), showing that a complete probabilistic iteration can be executed in just two clock cycles. We validate our approach through multiple benchmarks including partition problems, integer programming, and non-convex integer quadratic programming, demonstrating significant performance improvements. For a 3-partition problem with 14 numbers, the isotropic p-dit implementation achieves approximately 34× improvement over p-bit implementations. For integer linear programming tasks, p-int implementations show approximately 5.3× improvement. For non-convex integer quadratic programming problems, we achieve approximately 64× speedup compared to state-of-the-art software solvers when using FPGA implementations. These results highlight the potential of probabilistic computing based on extended-variable representations for tackling real-world optimization challenges.

## Introduction

The search for novel computational paradigms to solve hard optimization and sampling problems has motivated research across multiple disciplines. From physics-inspired approaches such as quantum annealing and simulated annealing to biologically-inspired methods like genetic algorithms and evolutionary computation, the goal remains to efficiently navigate complex energy landscapes to find good solutions. Recently, probabilistic computing, based on stochastic oscillations of magnetic tunnel junctions and other physical systems, has emerged as a promising approach.

The concept of probabilistic bits (p-bits) was introduced as a hardware-efficient means of implementing stochastic computing elements. P-bits, which stochastically oscillate between two states (+1 and −1), have been shown to be effective for solving constraint satisfaction problems and combinatorial optimization challenges. However, the restriction to binary representations introduces inefficiencies when representing multi-valued variables or categorical information. To represent a categorical variable with $d$ possible states using p-bits requires approximately $\lceil \log_2(d) \rceil$ p-bits with one-hot encoding, or more generally, multiple constraints to enforce valid configurations.

An alternative approach is to use generalized spin models that naturally support more than two states. Such models can represent d-dimensional solution spaces directly, reducing the dimensionality of the problem representation and, in some cases, eliminating the need for additional constraint-enforcement mechanisms. This motivates the introduction of probabilistic d-dimensional variables (p-dits), which extend the binary p-bit concept to stochastically oscillate between $d$ discrete states.

In this work, we introduce the mathematical framework for p-dits and their specializations, including probabilistic integers (p-ints) and isotropic p-dits. We demonstrate the hardware implementation of these constructs in CMOS-based ASICs, showcasing the practical viability of extended-variable probabilistic computing. We then benchmark these implementations against traditional approaches on a variety of optimization problems, including partition problems, integer programming, and integer quadratic programming, showing substantial performance improvements.

The organization of this paper is as follows. Section 2 introduces the mathematical formalism of probabilistic d-dimensional variables. Section 3 presents specializations of p-dits, including isotropic p-dits and probabilistic integers. Section 4 describes the ASIC implementation and hardware design considerations. Section 5 presents experimental results across multiple problem domains. Finally, Section 6 discusses the broader implications and future directions of this work.

## Probabilistic Computing and Ising Machines

### Mathematical Framework

Probabilistic computing is based on the concept of stochastically updating variables according to an energy function or Hamiltonian. The Ising model, originally developed to study ferromagnetism in statistical physics, provides a natural framework for such systems:

$$H = -\sum_{i<j} J_{ij} s_i s_j - \sum_i h_i s_i \tag{1}$$

where $s_i$ represents the state of spin $i$ (typically $\pm 1$ in the binary case), $J_{ij}$ represents the coupling strength between spins $i$ and $j$, and $h_i$ represents the external field acting on spin $i$. The system evolves according to update rules based on the Metropolis-Hastings algorithm or similar stochastic dynamics.

For the binary p-bit case, the update rule at iteration $t$ is:

$$P(s_i(t+1) = +1) = \frac{1}{1 + \exp(-2\beta \Delta H_i)} \tag{2}$$

where $\Delta H_i$ is the energy difference associated with flipping spin $i$, and $\beta = 1/(k_B T)$ is the inverse temperature parameter. When $\beta$ is large (low temperature), the system tends to move toward lower-energy states. When $\beta$ is small (high temperature), the system explores more broadly, allowing escape from local minima.

### p-bits for Constraint Satisfaction

P-bits have proven effective for solving constraint satisfaction problems (CSPs) and combinatorial optimization. The key insight is that constraints can be encoded into the Hamiltonian through appropriately chosen coupling strengths and field terms. For example, a logical constraint such as $x \vee y$ (logical OR) can be represented as:

$$H_{OR} = J_{OR} \cdot (-s_x s_y) \tag{3}$$

with $J_{OR}$ chosen to penalize configurations where both $x$ and $y$ are in the "false" state.

However, representing multi-valued variables using this binary framework requires either:
1. **One-hot encoding:** Using $d$ p-bits to represent $d$ states, with constraints ensuring exactly one p-bit is in the +1 state
2. **Binary encoding:** Using $\lceil \log_2(d) \rceil$ p-bits with appropriate constraints

Both approaches introduce additional constraints and coupling terms that can complicate the energy landscape and reduce the efficiency of the solver.

## Probabilistic d-dimensional Variables (p-dits)

### Definition and Dynamics

A probabilistic d-dimensional variable (p-dit) is a stochastic element that oscillates among $d$ discrete states. Unlike p-bits which are restricted to two states, p-dits generalize this concept to arbitrary dimensions. The state of a p-dit at time $t$ is denoted $s_i(t) \in \{0, 1, 2, \ldots, d-1\}$.

The energy of a system with p-dits can be expressed as a generalization of the Ising model:

$$H = -\sum_{i<j} \sum_{\alpha,\beta} J_{ij}^{\alpha\beta} \delta(s_i - \alpha) \delta(s_j - \beta) - \sum_i \sum_{\alpha} h_i^{\alpha} \delta(s_i - \alpha) \tag{4}$$

where $J_{ij}^{\alpha\beta}$ represents the coupling strength between states $\alpha$ and $\beta$ of p-dits $i$ and $j$, and $h_i^{\alpha}$ represents the field energy for p-dit $i$ in state $\alpha$.

The update rule for a p-dit is:

$$P(s_i(t+1) = \alpha) = \frac{\exp(-\beta E_i^{\alpha})}{\sum_{\gamma=0}^{d-1} \exp(-\beta E_i^{\gamma})} \tag{5}$$

where $E_i^{\alpha}$ is the energy of p-dit $i$ when it is in state $\alpha$. This is a softmax-style update rule that naturally generalizes the binary case.

### Matrix Representation

To efficiently implement p-dits in hardware, we represent the coupling structure using a modified Ising formulation. The effective coupling matrix $J$ encodes which p-dits interact and with what strength, while the effective field vector $h$ encodes the local preferences for each p-dit state.

For a p-dit implementation, the coupling between p-dits $i$ and $j$ can be represented as:

$$J_{ij} = \sum_{\alpha=0}^{d_i-1} \sum_{\beta=0}^{d_j-1} J_{ij}^{\alpha\beta} \tag{6}$$

This provides a convenient abstraction that allows us to use existing p-bit hardware architectures with modified coupling weights.

### Isotropic p-dits

A special case of p-dits is the isotropic p-dit, where the coupling structure respects the symmetry of the discrete space. An isotropic p-dit has the property that:

$$J_{ij}^{\alpha\beta} = J_{ij} \quad \forall \alpha, \beta \text{ such that } \alpha \neq \beta \tag{7}$$

and

$$J_{ij}^{\alpha\alpha} = 0 \tag{8}$$

Physically, this corresponds to a system where all transitions between different states are equally penalized or rewarded, independent of which states are involved. This symmetry is particularly useful for representing categorical variables, as it avoids introducing spurious energy differences based on state labels.

For isotropic p-dits, the update rule simplifies to:

$$P(s_i(t+1) = \alpha) = \frac{\exp(-\beta E_i^{\alpha})}{\sum_{\gamma=0}^{d-1} \exp(-\beta E_i^{\gamma})} \tag{9}$$

where

$$E_i^{\alpha} = -\sum_{j \neq i} J_{ij} \sum_{\beta \neq \alpha} \mathbb{1}[s_j = \beta] - h_i^{\alpha} \tag{10}$$

The isotropic constraint ensures that the representation is truly categorical, without implicit bias toward particular state values.

### Probabilistic Integers (p-ints)

While general p-dits can represent any discrete variable, probabilistic integers (p-ints) are a specialization designed to represent numeric values with regular, discrete steps. A p-int with range $r$ can represent integer values in $\{0, 1, 2, \ldots, r-1\}$.

The key advantage of p-ints over multiple p-bits is that they naturally encode the ordering and spacing of integers without requiring explicit binary representation. This is particularly beneficial when constraints involve linear combinations of integer variables, as is common in integer programming problems.

For a p-int representing values in range $r$, the energy contribution from a linear constraint $\sum_i c_i x_i \leq b$ can be naturally encoded:

$$H_{constraint} = \lambda \cdot \max(0, \sum_i c_i x_i - b) \tag{11}$$

where $\lambda$ is a penalty coefficient and $x_i$ is the integer value represented by p-int $i$.

## Hardware Implementation

### ASIC Design

The ASIC implementation of p-dits leverages existing p-bit hardware architectures with extensions to support multi-state dynamics. The core element is a probabilistic bit (p-bit) cell that can stochastically switch between two states based on coupled input signals.

For p-dits, multiple such cells are combined with state-decoding logic to represent the multi-state nature. The design utilizes:

1. **Stochastic switching elements** based on magnetic tunnel junctions (MTJs) or other stochastic devices
2. **Coupling network** for implementing the Ising Hamiltonian
3. **Temperature control** for adjusting the $\beta$ parameter
4. **State readout logic** for determining the current state of each p-dit

The ASIC was fabricated using a 130 nm CMOS process and includes:
- 576 p-bit cells
- Coupling matrix supporting up to 128 p-bits or equivalent p-dit configurations
- Integrated temperature control and random number generation
- Serial/parallel interface for problem specification and result readout

A full iteration of the p-dit update can be performed in two clock cycles, enabling rapid evaluation of the Hamiltonian and state updates.

### Implementation Details

The coupling matrix $J$ is implemented using voltage-divider networks that compute weighted sums of p-bit states. The effective temperature is controlled through a bias current that modulates the switching probability.

For p-ints, the state is represented using a unary encoding, where $d$ physical p-bits encode a d-state variable. This ensures that the p-int always maintains a valid configuration (e.g., exactly one p-bit is active for one-hot encoding with additional constraints for contiguous ranges).

Field values $h_i$ are implemented using adjustable current sources that bias each p-bit toward particular states. These can be modified dynamically during problem execution to implement adaptive solving strategies.

## Constraint Handling in Extended Variables

### Slack Variables

One challenge in using extended variables is handling inequality constraints. The traditional approach for p-bits is to introduce slack variables that represent the degree of constraint violation:

$$x + s = b \tag{12}$$

where $s \geq 0$ is the slack variable. For p-bits, this is naturally handled by introducing additional binary variables to represent the slack, along with constraints ensuring non-negativity.

However, with extended variables, the slack can be naturally represented using a p-int with appropriate range. This avoids the need for binary encoding and multiple constraints.

### Example: Partition Problem

Consider the partition problem where we seek to partition a set of numbers into two groups with equal (or nearly equal) sum. Using p-bits, this requires a binary variable for each number, indicating which group it belongs to.

With p-ints, we can instead represent the difference in sums directly:

$$H = (x - b)^2 \tag{13}$$

where $x = \sum_i c_i s_i$ is the weighted sum and $b$ is the target value. The objective is to minimize the squared deviation from the target.

However, directly constraining differences can sometimes create energy barriers. An alternative is to use violation variables, which explicitly penalize constraint violations. This is described in the next subsection.

### Violation Variables

To mitigate challenges with slack formulations, we introduce violation variables. Violation variables hold a value of 0 if a constraint is satisfied, and −1 if it is violated, which can be realized using a p-int. Their J matrix and h vector connections are constructed from an equivalent slack variable representation. Firstly, the constraints' contributions to the J matrix connections between traditional variables are zeroed, along with their J matrix self-connections and h vector offsets. Secondly, the J matrix connections *from* the slack variables *to* the traditional variables are negated, while the J matrix connections *from* the traditional variables *to* the slack variables remain the same. This results in a condensed but asymmetric J matrix. An example is shown in Supplementary Note 7.

As violation variables have a value of 0 while their corresponding constraint is satisfied, they only affect traditional variables while a constraint is violated. Additionally, the correctional input to traditional variables does not scale with the degree of violation. While it seems like the inability for the system to prioritize fixing constraints that are majorly violated over those that are only minorly violated would be a disadvantage, this prevents constraints from distorting the energy landscape and thus creating hard-to-escape local minima.

There are two additional advantages of using violation variables: While conventionally, verifying that a seemingly stable state meets all inequality constraints requires manual computation, with this approach one can simply check to see that all violation variables remain 0 for some time. A further advantage is that, due to the lack of direct iteration between problem variables, a large portion of the J matrix is known to have values of 0 and does not need to be stored in memory, resulting in significantly smaller storage space for large problems.

### Scaled Sampling

Unlike with p-bits, there is sometimes a significant difference in total range between different p-ints in the same problem formulation. Intuitively, this leads to p-ints with smaller ranges being oversampled compared to those with large ranges. One way to adjust for this is by sampling each p-bit proportionally to its range, to approximately equalize the time it takes to travel from one end of each p-int's range to the other in a heavily weighted random walk.

## Results

### |D|-Partition

The more natural representation of isotropic p-dit PIMs compared to p-bit PIMs leads to better results on the same problem. For a small problem of 14 numbers, a p-bit PIM produces valid solutions (i.e., exactly one p-bit in each number's corresponding group is in the +1 state) for a reasonable range of constraint constants and temperatures, as shown in Fig. 4a and Fig. 4b. However, as the constraint constant rises, the quality of these valid solutions falls rapidly after a local minimum— primarily from the PIM's decreased emphasis on solution quality at higher $C$ values. The isotropic p-dit PIM for the same problem does not face this trade-off and is able to have much better solution quality, with a comparison to the p-bit PIM

**Figure 4: 3-partition problem.** **A** Results from a p-bit implementation of a 3-partition problem composed of 14 randomly generated integers, ranging between 1 and 6, over trials of 512 iterations with a constant β of=$\frac{1}{3}$. As C is increased, an increasing proportion of the PIM's states during each trial are valid encodings. For valid encodings the error was calculated as the total absolute difference between each partition's sum and that of the true solution. The lowest error found in each trial increases with C for most of its range after a minimum. Notably, for low C values, few or no states were valid in 10,000 trials, resulting in a noisy or undefined mean error, respectively. Θ is kept constant at 1. **B** The same setup, except that a constant C of 94 is used and β is swept. Lower temperature correlates with a higher proportion of valid states; however the best error is minimized at a medium temperature. **C** The same problem, sweeping the number of iterations performed for a p-bit PIM with a C of 94 and an isotropic p-dit PIM, both at a β of=$\frac{2}{32}$. For low numbers of iterations, no trials resulted in the p-bit PIM finding the true ground state solution. For each number of iterations, the isotropic p-dit system had a significantly higher success rate. In both cases, results from the ASIC over at least 250 trials closely matched those from simulations over 10,000 trials.

near the mean best error local minimum shown in Fig. 4c. This is confirmed experimentally, with ASIC results closely mirroring simulation results for both the p-bit and isotropic p-dit implementations. Considering non-zero datapoints, an approximate 34x improvement is seen in trials-to-solution of the ASIC isotropic p-dit implementation compared to the ASIC p-bit implementation.

### 6-partition Problem

Additionally, a larger problem of 1,000 randomly generated numbers between 1 and 100 was investigated with isotropic p-dits. A rapidly decreasing error, starting when trial length exceeds around 2⁷ iterations, and rapidly increasing probability of finding the true ground solution, starting when trial lengths exceed around 2¹⁰ iterations, are shown in Fig. 5. For sufficiently long trial lengths, the ground solution was found in nearly every trial.

**Figure 5: 6-partition problem.** Results from an implementation of a 6-partition problem of 1,000 randomly generated numbers between 1 and 100, using isotropic p-dits. The error reduces as the number of iterations increases, with a sharp decrease starting at around 2⁷ iterations. When the error is sufficiently low, beginning around 2¹⁰ iterations, the true solution success rate grows rapidly. A linear β sweep from $\frac{1}{32}$ to 1 is used over 1,000 trials for each data point.

### Change-Making Problem

**Figure 6: Change-Making Problem.** **A** The proportion of 300 iteration-long trials using variable temperatures in which the true solution to a change-making problem was found. Specifically, the problem was composed to find change for a sum of $1.34 using the minimum number of coins worth 3¢, 4¢, 7¢, and 11¢, respectively. A C of 1 and Θ of 0 of 96 were used. **B** Simulated and ASIC results showing the p-int implementation greatly outperforming the p-bit implementation, with both using the best β found from the first plot ($\frac{1}{64}$ for p-int and $\frac{1}{128}$ for p-bit). Each simulated data point is averaged over 1,000 trials, while each experimental data point is averaged over 250 trials.

**Integer Programming**

An ILP representation of the change-making problem, in which a minimum number of coins is sought whose value sum to a selected currency amount, is explored in Fig. 6. While the p-bit and p-int implementations use the same constraints and objective, they have slightly shifted optimal constant temperatures, $\beta_{opt}$, as shown by Fig. 6a with regards to finding the ground state solution of 14 coins.

These $\beta_{opt}$ values were then used in a series of trials of variable length. These simulated results for p-bits, and both simulated and experimental results for p-ints, are shown in Fig. 6b. The simulated and ASIC p-int implementation greatly outperforms the simulated p-bit implementation across the entire trial length range. Averaged over all non-zero datapoints, an approximate 5.3x improvement is seen in trials-to-solution of the ASIC p-int implementation compared to the p-bit implementation.

### Fixed-Charge Problem

**Figure 7: Fixed-Charge Problem.** **A** Heat maps of the proportion of 500 trials of 8,192 iterations in which the optimum solution was found in a fixed-charge problem. During each trial, β was swept from the listed β₀ value to 32 times its value, using a base-2 logarithmic sweep. C was kept constant at 1. In the top left, a traditional slack variable representation of the problem with even sampling was used. A relatively wide range of both β₀ and Θ resulted in decent performance. In the top right, a slack variable representation and variable range scaled sampling were used. Compared to the even sampling, the optimal range is slightly more defined. In the bottom left, a violation variable representation with an even sampling as used. Good performance is found for a large region of β₀ and Θ. In the bottom right, a violation variable representation and scaled sampling were used. Great performance is found for a large region of the explored variables. **B** Performance of the four representations for the same problem over 1,000 trials of varying length. A pronounced increase in performance is found by using a violation variable representation over traditional slack ones. A clear increase is found by using adjusted sampling over even sampling in the violation variable case, and a lesser but still distinguishable increase is shown after 5,000 iteration trials in the slack variable case. For both slack representation formulations, β₀ = $\frac{1}{256}$ and Θ = 2, while both violation representation formulations used β₀ = $\frac{1}{8}$ and Θ = $\frac{1}{4}$.

Fig. 7 shows four approaches to a slightly modified fixed-charge ILP problem representing a hypothetical business's choice of which clothing items to manufacture, which is traditionally represented

using six variables, 14 constraints, and an objective function. For even and scaled sampling with both a traditional slack representation of the problem and a violation variable representation, a parameter sweep over the objective constant and β₀ was performed. During each trial, β was swept from β₀ to 32β₀ using a base-2 scaling. From Fig. 7a, it was found that for both sampling methods, the slack formulation had a parameter optimum near β₀ = $\frac{1}{256}$ and Θ = 2, while both violation representations had optima near β₀ = $\frac{1}{8}$ and Θ = $\frac{1}{4}$. These values were then used to explore the behavior of the four selected formulations over trials of various lengths. As Fig. 7b shows, the violation formulation offers significant improvement in finding the absolute solution compared to the traditional slack formulation. Additionally, the selected scaled sampling procedure offers major improvements for the violation formulation over the entire range, and minor improvement for the slack formulation for trial lengths of more than ~5,000 iterations. Averaged across non-zero datapoints, an ~10x improvement in trials-to-solution is seen by the violation formulation using scaled sampling compared to the traditional slack formulation using even sampling.

### Integer Quadratic Programming

A non-convex, 17-variable problem with 51 linear constraints, of which 34 were bounds, and a quadratic objective function were randomly generated. To track the value of the custom objective function, a capability not included within the ASIC design, and to allow for parallel instances of the problem, an FPGA implementation was used. The design included two cores, each of which contained two pipelined instances of the problem. As the system clock of the FPGA was 50 MHz, this was equivalent to 4 parallel instances which updated at 25 MHz. During each trial, the initial state of each instance had all variables set to a value of 0 to avoid the need for preprocessing. As the trial progressed, each instance searched for the true solution independently. If no instance found the solution within a reasonable time, each instance

**Figure 8: Non-convex IQP Problem Comparison.** A comparison of the time required to produce a solution, and the quality of solutions for an IQP problem for each solver. The generated problem includes 17 integer variables, 51 linear inequality constraints (34 being bounds), and a quadratic objective function. The p-int implementation was synthesized on an FPGA. It contained two cores with two pipelined instances each and used β₀ = 3.3 and Θ = 0.0008. If no solution was found by the iteration cutoff, the state of the system was reset, with the trial continuing. The remainder are state-of-the-art software solvers included in GAMS. The p-int data is composed from 25 trials, while the solvers data arose from a trial with the default seed. Despite the slower 50 MHz clock speed of the FPGA compared to the 4.31 GHz boost of the CPU, the p-int system in both configurations outperformed all software solvers which found the problem's true solution. Configured with a cutoff of 2²¹, a ~64x improvement in time-to-solution was observed for the p-int solver compared to the MOSEK solver.

was reset at a pre-selected cutoff iteration, without resetting the trial's timer. As the distribution of iterations-to-solution necessarily has a long right tail, smaller cutoff values were shown to be preferable.

The p-int system with both a large (2²⁸) and small (2²¹) cutoff vastly outperformed even the best state-of-the-art solver, by ~10x and ~64x respectively, in finding the true solution. The performance of the p-int system is especially impressive considering the higher 4.31 GHz boost clock of the CPU.

### Discussion and Conclusions

**Table 1: Summary of experiments.** A summary of the benchmarks implemented in this work. The table summarizes the type of problem, its complexity, the probabilistic architecture used to solve it, the size of a p-bit PIM needed to solve it (whether p-bits were used or not), the size of the p-int or isotropic p-dit PIM needed to solve it, the platform, and the observed performance improvement in trials-to-solution or time-to-solution (when applicable) compared to a stated reference.

| Problem | Complexity | Implementation Used | Required p-bits | Required p-dits | Platform | Performance Improvement |
|---------|-----------|-------------------|-----------------|-----------------|----------|------------------------|
| Change-making ILP | 8 bound constraints + 1 equality constraint + 1 objective | p-bits & p-ints | 16 | 4 | Software & ASIC | 5.3x p-int PIM vs. p-bit PIM |
| 3-partition problem | 14 values | p-bits & isotropic p-dits³ | 42 | 14 | Software & ASIC | 34x p-dit PIM vs. p-bit PIM |
| 6-partition problem | 1,000 values | isotropic p-dits⁶ | 6,000 | 1,000 | Software | - |
| Fixed-charge ILP | 12 bound constraints + 5 inequality constraints + 1 objective | p-ints (each combination of slack/violation + even/scaled) | 55 | 11 | Software | 10x violation + scaled vs. slack + even |
| Non-convex IQP | 34 bound constraints + 17 inequality constraints + 1 objective | p-ints (violation + even sampling) | 289 | 34 | FPGA | 64x p-int PIM vs. best state-of-the-art software solver |

In this work, we have described a generalized mathematical spin model which supports continuous length components along an arbitrary count of dimensions. We further formalized the probabilistic d-dimensional

bit which stochastically oscillates between discrete states within this space. As a restriction of the general p-dit definition, the concept of isotropic p-dits was introduced. A single isotropic p-dit can be used to represent the value of a categorical variable that is traditionally represented with a group of p-bits. While a one-hot encoding using p-bits results in a PIM where most configurations are invalid, an isotropic p-dit implementation will never exist in an invalid configuration. This advantage increases with the complexity of the problem, as the ratio of invalid to valid assignments grows exponentially with the number of various represented. For p-bit implementations, the one-hot constraint must be implemented within the J matrix and h vector alongside any other constraints or objectives of the problem. This necessitates careful tuning of their relative strength, which adds another non-trivial aspect to achieving optimization. If the one-hot encoding constraint is enforced to weakly, the PIM might converge to an invalid configuration where it is violated but the objective has a favorable value. On the other hand, if the one-hot encoding is enforced over-zealously, then the system will have a difficult time leaving a local minimum, as it takes at least two flips to move from one valid one-hot encoding to another. We have demonstrated experimentally, for a small 3-partition problem, a strong ~34x improvement of an isotropic p-dit³ PIM compared to a p-bit PIM, even after finding the optimum relative strength of the one-hot encoding for the p-bit implementation.

While the N-partition problem is a natural demonstration of the power of the isotropic p-dit formulation, which is also why a 1,000-node 6-partition instance was further demonstrated as solvable, we believe many other problems can be attacked in this manner.

We further introduced another useful restriction on the definition of p-dits, termed probabilistic integers, which allow for a more natural representation of numeric values with regular, discrete steps. The most promising application of p-int PIMs is to solve integer programming problems: the common language in which many real-world optimization problems are expressed. While p-bits can represent integer values in these problems, the necessary binary encoding introduces energy barriers between adjacent states: a challenge not encountered with p-ints. We have demonstrated a large performance improvement of a p-int PIM compared to a p-bit PIM for an ILP problem (~5.3x) with an ordinary Ising representation. This result, along with the others of this work, are summarized in Table 1.

It is worth noting, however, that many practical problems are complicated, composed of a mixture of equality, and inequality constraints, of small and large range variables, and of linear and quadratic objectives. We thus believe that there is much work to be done in maturing the field of p-dit-based Ising solvers to allow for their widespread adaptation for this task. We have introduced the concept of violation variables as a method of representing inequality constraints within an Ising Hamiltonian. By breaking the symmetry of the coupling matrix, they allow a PIM to more smoothly explore a problem's energy landscape compared to the traditional slack variable method. We further explored sampling p-ints with different frequencies depending on the range they represent. Finally, we implement a quadratic objective function across both the h vector and the J matrix. Using an FPGA with a 50 MHz clock to implement a p-int PIM, we were able to demonstrate a massive, ~64x improvement in time-to-solution compared to the best state-of-the-art software solvers tested, for an IQP problem. This demonstrates the potential for probabilistic computing methods to replace existing integer programming solvers.

An important aspect of the practicality of the proposed p-dits is the ability to implement them in hardware. To showcase the ability to create CMOS-based p-dit-based PIMs, we designed, fabricated, and verified a digital ASIC test chip. Crucially, it was able to perform a full iteration of the PIM within two clock cycles. This suggests that PIM ASICs of all three p-dit types shown here can be designed to achieve ultra-fast update rates.

## Methods

### ASIC design

The ASIC PIM was defined using RTL Verilog code which was processed by the OpenLane RTL to GDSII pipeline, using the Skywater 130 nm open-source process design kit (PDK). The PIM was manufactured using the Efabless multi-project wafer (MPW) service, which also provided the design for a co-integrated small CPU based on a VexRiscv minimal+debug configuration. An oscillator running at 10 MHz was used as the ASIC's clock for all experiments shown.

### Experimental code

All non-trivial problems and their Ising representations were created using self-made Python 3 code. All simulated data were gathered using self-made C++ code. Self-made C code executed on the RISC-V CPU was used to run all experimental trials. Communication with the RISC-V CPU, to upload trial code and to record results, was done using the UART protocol over a USB cable.

### IQP Comparison

Solvers used for the IQP comparison were bundled with GAMS 49.3.0 and accessed using GAMS Studio 1.20.2. To the best of our knowledge, all local, standalone (not utilizing other solvers included in GAMS as subsolvers) non-convex MIQCP solvers that were included in an academic license have been considered. For each trial, the solvers were instructed to use 4 threads, and to have a timeout of 10 minutes, with all other parameters kept at their default values, including the seed. For CPLEX, 'OptimalityTarget' was set to '3' to allow it to process a non-convex problem. The solution time for each solver was extracted from the produced logfiles, where it is reported differently for each solver. CPLEX and MOSEK reported solution time to the nearest hundredth of the second, while ALPHAECP and XPRESS reported solution time to the nearest second. Total execution time was not considered. All solvers finished execution on their own apart from XPRESS which was halted after the timeout period. This comparison was conducted on a Ryzen 7 4700U which has a frequency of 2.0 GHz and a Turbo Clock of 4.1 GHz. Memory utilization was not a limiting factor for any solver.

### FPGA design

All FPGA demonstrations were conducted using a Terasic Cyclone IV Altera DE2-115. A 50 MHz oscillator included on the FPGA was used as the driving clock. The design was defined by RTL SystemVerilog code compiled by Quartus Prime Version 23.1std.0 Build 991. One push-button was used to reset the pseudo-random number generator to an initial seed. The other independently reset the state of the PIM. The pseudo-random number generator is based on the state update procedure of the 32-bit PCG pseudo-random number generator. It has a period of 2³³ states, corresponding to ~86 seconds. For each set of initial, randomly generated seeds, 5 trials were conducted. Readout of the iteration in which the true solution was found was done through LEDs.

## References

1. Aramon, M. *et al.* Physics-inspired optimization for quadratic unconstrained problems using a digital annealer. *Frontiers in Physics* 7, 48 (2019).

2. Zou, Y. & Lin, M. Massively simulating adiabatic bifurcations with fpga to solve combinatorial optimization. In *Proceedings of the 2020 ACM/SIGDA International Symposium on Field Programmable Gate Arrays*, 65–75 (2020).

3. Finocchio, G. *et al.* Roadmap for unconventional computing with nanotechnology. *Nano Futures* (2023).

4. Feynman, R. Simulating physics with computers. *International Journal of Theoretical Physics* 21 (1982).

5. Sharma, A., Burns, M., Hahn, A. & Huang, M. Augmenting an electronic ising machine to effectively solve boolean satisfiability. *Scientific Reports* 13, 22858 (2023).

6. Zhang, T. & Han, J. Efficient traveling salesman problem solvers using the ising model with simulated bifurcation. In *2022 Design, Automation & Test in Europe Conference & Exhibition (DATE)*, 548–551 (IEEE, 2022).

7. Si, J. *et al.* Energy-efficient superparamagnetic ising machine and its application to traveling salesman problems. *Nature Communications* 15, 3457 (2024).

8. Lu, A. *et al.* Scalable in-memory clustered annealer with temporal noise of charge trap transistor for large scale travelling salesman problems. *IEEE Journal on Emerging and Selected Topics in Circuits and Systems* 13, 422–435 (2023).

9. Finocchio, G. *et al.* The promise of spintronics for unconventional computing. *Journal of Magnetism and Magnetic Materials* 521, 167506 (2021).

10. Mohseni, N., McMahon, P. L. & Byrnes, T. Ising machines as hardware solvers of combinatorial optimization problems. *Nature Reviews Physics* 4, 363–379 (2022).

11. Tanahashi, K., Takayanagi, S., Motohashi, T. & Tanaka, S. Application of ising machines and a software development for ising machines. *Journal of the Physical Society of Japan* 88, 061010 (2019).

12. Aadit, N. A. *et al.* Massively parallel probabilistic computing with sparse ising machines. *Nature Electronics* 5, 460–468 (2022).

13. Metropolis, N., Rosenbluth, A. W., Rosenbluth, M. N., Teller, A. H., & Teller, E. Equation of state calculations by fast computing machines. *The Journal of Chemical Physics* 21(6), 1087-1092 (1953).

14. Litvinenko, A. *et al.* A spinwave ising machine. *Communications Physics* 6, 227 (2023).

15. González, V., Litvinenko, A., Khymyn, R. & Ákerman, J. Global biasing using a hardwarebased artificial zeeman term in spinwave ising machines. In *2023 IEEE International Magnetic Conference-Short Papers (INTERMAG Short Papers)*, 1–2 (IEEE, 2023).

16. Litvinenko, A., Khymyn, R., Ovcharov, R. & Ákerman, J. A 50-spin surface acoustic wave ising machine. *arXiv preprint arXiv:2311.06830* (2023).

17. Goto, H., Lin, Z. & Nakamura, Y. Boltzmann sampling from the ising model using quantum heating of coupled nonlinear oscillators. *Scientific reports* 8, 7154 (2018).

18. Kanao, T. & Goto, H. High-accuracy ising machine using kerr-nonlinear parametric oscillators with local four-body interactions. *npj Quantum Information* 7, 18 (2021).

19. Marandi, A., Wang, Z., Takata, K., Byer, R. L. & Yamamoto, Y. Network of time-multiplexed optical parametric oscillators as a coherent ising machine. *Nature Photonics* 8, 937–942(2014).

20. Okawachi, Y. *et al.* Demonstration of chip-based coupled degenerate optical parametric oscillators for realizing a nanophotonic spin-glass. *Nature Communications* 11, 4119 (2020).

21. Tezak,N.*et al.* Integrated coherent ising machines based on self-phase modulation in micro ring resonators. *IEEE Journal of Selected Topics in Quantum Electronics* 26, 1–15 (2019).

22. Lo, H., Moy, W., Yu, H., Sapatnekar, S. & Kim, C. H. An ising solver chip based on coupled ring oscillators with a 48-node all-to-all connected array architecture. *Nature Electronics* 6, 771–778 (2023).

23. Karpuzcu, U. *et al.* Cobi: A coupled oscillator based ising chip for combinatorial optimization. *Nature Portfolio: Manuscript submitted for publication* (2024).

24. Bashar, M. K., Mallick, A. & Shukla, N. Experimental investigation of the dynamics of coupled oscillators as ising machines. *IEEE Access* 9, 148184–148190 (2021).

25. Mallick, A. *et al.* Using synchronized oscillators to compute the maximum independent set. *Nature communications* 11, 4689 (2020).

26. Bashar, M. K., Lin, Z. & Shukla, N. Stability of oscillator ising machines: Not all solutions are created equal. *Journal of Applied Physics* 134 (2023).

27. Bashar, M. K., Li, Z., Narayanan, V. & Shukla, N. An fpga-based max-k-cut accelerator exploiting oscillator synchronization model. In *2024 25th International Symposium on Quality Electronic Design (ISQED)*, 1–8 (IEEE, 2024).

28. Kalinin, K. P. & Berloff, N. G. Simulating ising and n-state planar potts models with nonequilibrium condensates. *Physical review letters* 121, 235302 (2018).

29. Kalinin, K. P., Amo, A., Bloch, J. & Berloff, N. G. Polarionic xy-ising machine. *Nanophotonics* 9, 4127–4138 (2020).

30. Luo, S. *et al.* Classical spin chains mimicked by room-temperature polariton condensates. *Physical Review Applied* 13, 044052 (2020).

31. Camsari, K. & Datta, S. Waiting for quantum computing? try probabilistic computing. *IEEE Spectrum* (2021).

32. Camsari, K. Y., Faria, R., Sutton, B. M. & Datta, S. Stochastic p-bits for invertible logic. *Physical Review X* 7, 031014 (2017).

33. Liu, Y. *et al.* Time-division multiplexing using computer using single stochastic magnetic tunneling junction. *IEEE Transactions on Electron Devices* 69, 4700–4707 (2022).

34. Yin, J. *et al.* Scalable ising computer based on ultra-fast field-free spin orbit torque stochastic device with extreme 1-bit quantization. In *2022 International Electron Devices Meeting (IEDM)*, 36–1 (IEEE, 2022).

35. Lu, A. *et al.* Scalable in-memory clustered annealer with temporal noise of finef for the travelling salesman problem. In *2022 International Electron Devices Meeting (IEDM)*, 22–5 (IEEE, 2022).

36. Kaiser, J. *et al.* Hardware-aware in situ learning based on stochastic magnetic tunnel junctions. *Physical Review Applied* 17, 014016 (2022).

37. Camsari, K. Y., Sutton, B. M. & Datta, S. P-bits for probabilistic spin logic. *Applied Physics Reviews* 6 (2019).

38. Kaiser, J. & Datta, S. Probabilistic computing with p-bits. *Applied Physics Letters* 119 (2021).

39. Grimaldi, A. Probabilistic and oscillatory Ising machines for combinatorial optimization: from software to hardware-acceleration with spintronics. *Ph.D. thesis, Università degli Studi di Messina* (2023).

40. Singh, N. S. *et al.* Cmos plus stochastic nanomagnets enabling heterogeneous computers for probabilistic inference and learning. *Nature Communications* 15, 2685 (2024).

41. Okuyama, T., Hayashi, M. & Yamaoka, M. An ising computer based on simulated quantum annealing by path integral monte carlo method. In *2017 IEEE international conference on rebooting computing (ICRC)*, 1–6 (IEEE, 2017).

42. Zhang, T. *et al.* A review of ising machines implemented in conventional and emerging technologies. *IEEE Transactions on Nanotechnology* (2024).

43. Zhang, T., Tao, Q., Liu, B. & Han, J. A review of simulation algorithms of classical ising machines for combinatorial optimization. In *2022 IEEE International Symposium on Circuits and Systems (ISCAS)*, 1877–1881 (IEEE, 2022).

44. Gyoten, H., Hiramoto, M., & Sato, T. Enhancing the solution quality of hardware ising-model solver via parallel tempering. In *2018 IEEE/ACM International Conference on Computer-Aided Design (ICCAD)* (pp. 1-8). (IEEE, 2018).

45. Lucas, A. Ising formulations of many np problems. *Frontiers in physics* 2, 5 (2014).

46. Mézard, M., Parisi, G. & Virasoro, M. A. Spin glass theory and beyond: An Introduction to the Replica Method and Its Applications, vol. 9 (World Scientific Publishing Company, 1987).

47. Camsari, K. Y., Faria, R., Sutton, B. M. & Datta, S. Stochastic p-bits for invertible logic. *Physical Review X* 7, 031014 (2017).

48. Zhu, J., Xie, Z. & Bermel, P. Numerical simulation of probabilistic computing to np-complete number theory problems. *Journal of Photonics for Energy* 13, 028501–028501 (2023).

49. Aadit, N. A. *et al.* Massively parallel probabilistic computing with sparse ising machines. *Nature Electronics* 5, 460–468 (2022).

50. Ackley, D. H., Hinton, G. E. & Sejnowski, T. J. A learning algorithm for boltzmann machines. *Cognitive science* 9, 147–169 (1985).

51. Whitehead, W., Nelson, Z., Camsari, K. Y. & Theogarajan, L. Cmos-compatible ising and potts annealing using single-photon avalanche diodes. *Nature Electronics* 6, 1009–1019 (2023).

52. Inaba, K. *et al.* Potts model solver based on hybrid physical and digital architecture. *Communications Physics* 5, 137 (2022).

53. Bashar, M. K., Hasan, A. & Shukla, N. Designing a k-state p-bit engine. *arXiv preprint arXiv:2403.06436* (2024).

54. Tamura, K. *et al.* Performance comparison of typical binary-integer encodings in an ising machine. *IEEE Access* 9, 81032–81039 (2021).

55. Winston, W. L. *Operations research: applications and algorithms* (Cengage Learning, 2022).

56. Wisniewski, M. & Klein, J. H. Linear programming: Critical path analysis (Palgrave, 2001).

57. Vella, D. C. *Invitation to linear programming and game theory* (Cambridge University Press, 2021).

58. Yang, Z. & Yang, C. How far can a biased random walker go? *Journal of Applied Mathematics and Physics* 3, 1159–1167 (2015).

59. Caravel management soc - litex. https://caravel-mgmt-soc-litex.readthedocs.io/en/latest/ (2022). Accessed: 2024-06-25

60. GAMS Development Corporation. General Algebraic Modeling System (GAMS) Release 49.3.0 (2025).

61. O'Neill, M. E. Pcg: A family of simple fast space-efficient statistically good algorithms for random number generation. *Tech. Rep. HMC-CS-2014-0905* (2014).

## Acknowledgments

This work was supported by the U.S. National Science Foundation (NSF) under award numbers 2322572, 2425538, and 2400463. A.G., D.V. and G.F. are members of the Petaspin team and acknowledge the support from Petaspin association (www.petaspin.com). G. F. and A.G. acknowledge the support from the project PRIN 2020LPWKH7, "The Italian factory of micromagnetic modelling and spintronics". The work of D. V. thanks the project PE000021, "Network 4 Energy Sustainable Transition – NEST", funded by the European Union – NextGenerationEU, under the National Recovery and Resilience Plan (NRRP), Mission 4 Component 2 Investment 1.3 - Call for tender No. 1561 of 11.10.2022 of Ministero dell'Università e della Ricerca (MUR) (CUP C93C22005230007).
