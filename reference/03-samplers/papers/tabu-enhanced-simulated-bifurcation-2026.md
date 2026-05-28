# Tabu-Enhanced Simulated Bifurcation for combinatorial optimization

**Authors:** Xian-Zhe Tao¹ᐩ, Qing-Guo Zeng¹ᐩ, Zi-Jia Huang²ᐩ, Bo-Wei Zuo¹, Yong-Qing Liu¹, Jiapei Zhuang³ᐩ⁻ᶜ, Hideki Okawa⁴ᐩ⁻ᶜ, Man-Hong Yung¹'²'⁴ᐩ⁻ᶜ

**Affiliations:**
¹Shenzhen Institute for Quantum Science and Engineering, Southern University of Science and Technology, Shenzhen, China
²International Quantum Academy, Shenzhen, China
³College of Computer Science and Software Engineering, Shenzhen University, Shenzhen, China
⁴Lomonosov Moscow State University, Moscow, Russia
⁵Department of Physics, Southern University of Science and Technology, Shenzhen, China
⁶Institute of High Energy Physics, Chinese Academy of Sciences, Beijing, China
⁷Guangdong Provincial Key Laboratory of Quantum Science and Engineering, Southern University of Science and Technology, Shenzhen, China
⁸Shenzhen Key Laboratory of Quantum Science and Engineering of the University of Science and Technology, Shenzhen, China

**Published:** Communications Physics | (2026)9:100

---

## Abstract

Simulated Bifurcation (SB) algorithms, inspired by quantum annealing, can efficiently solve large-scale combinatorial optimization problems on classical hardware, often outperforming traditional approaches such as simulated annealing. However, their tendency to be trapped in local optima limits global solution quality. In this work, we introduce Tabu-Enhanced Simulated Bifurcation (TESB), an improved SB variant that incorporates a Tabu Search-inspired mechanism. By leveraging a dynamic penalty guided by early search history, TESB can naturally avoid revisiting suboptimal regions. On Max-Cut benchmarks, TESB achieves up to a three-order-of-magnitude reduction in Time-to-Solution compared to standard SB. When applied to particle track reconstruction in high-energy physics, TESB identifies lower-energy configurations on problems exceeding 100,000 spin variables, demonstrating enhanced scalability and performance across a wide range of combinatorial tasks.

---

## Results and discussion

### Ising problem and SB algorithms

In this section, a brief review of the Ising problem and the SB algorithms is presented. Combinatorial optimization problems, which are often NP-hard, aim to identify the optimal solution from a computationally large search space, and are inherently challenging due to their Non-deterministic Polynomial (NP)-hard nature. A significant number of combinatorial optimization problems can be formulated as finding the ground state of the Ising model, a task that can naturally be encoded using a set of qubits. In this context, the D-Wave quantum annealer, which employs superconducting qubits, presents a promising approach for future developments in the field. However, the computational advantage of quantum annealing remains constrained by the limited scale and connectivity of current hardware. Moreover, experimental studies have shown that SB algorithms outperform classical approaches on problems with dense interaction graphs, primarily due to physical noise and architectural limitations.

Quantum annealing has inspired the development of various special-purpose processors designed to solve large-scale optimization problems. Examples include coherent Ising machines (CIMs), implemented using pulsed lasers, oscillator-based fluids, FPGA-based digital annealers, memristor-based Hopfield neural networks, and stochastic computing hardware based on NISRAM. Recent benchmarking studies have highlighted the superior performance of these classical and quantum-annealing approaches.

Combinatorial optimization problems lie at the heart of numerous real-world applications, including logistics, finance, and engineering. These problems involve identifying optimal solutions from an exponentially large search space, and are inherently challenging due to their NP-hard nature. A significant number of combinatorial optimization problems can be formulated as finding the ground state of the Ising model, a task that can naturally be encoded using a set of qubits. In this context, the D-Wave quantum annealer, which employs superconducting qubits, presents a promising approach for future developments in the field. However, the computational advantage of quantum annealing remains constrained by the limited scale and connectivity of current hardware.

At the same time, various quantum-annealing-inspired algorithms that emulate quantum evolution on classical CMOS hardware have driven significant progress in the field of combinatorial optimization. These algorithms have been demonstrated to be a promising approach through their demonstrated efficiency and scalability, particularly when implemented for parallel processing on GPU architectures. The original version of SB, referred to as adiabatic SB (aSB), is susceptible to inaccuracies caused by the continuous relaxation of discrete variables. To address this issue, Volpe et al. introduced inelastic walls and discretization mechanisms, leading to two improved variants: ballistic SB (bSB) and discrete SB (dSB). Extensive comparative experiments with Simulated Annealing (SA) have demonstrated that bSB and dSB offer improved performance, particularly in solving large-scale optimization problems. These algorithms have been successfully applied to real-world applications such as MIMO detection and track reconstruction in high-energy physics. Although discrete SB shows exceptional performance on regular or sparse graphs, they exhibit reduced effectiveness on skewed graphs with highly skewed degree distributions, where they are prone to being trapped in local minima. To address this limitation, researchers have developed several enhanced variants to escape from the local minima, thereby improving the overall solution quality.

### Tabu-Enhanced Simulated Bifurcation

**Overview.** For optimization solvers such as the SB algorithms, the trap of local optima often significantly limits their performance. In tabu search, the algorithm maintains a tabu list to record information about previously visited local minima and avoids revisiting them in subsequent searches, thereby escaping these local traps. Inspired by this procedure, we introduce a mechanism into the SB algorithms. Specifically, we begin by performing low-cost computations to rapidly gather information on some approximate solutions, such as through a rough iteration process. Subsequently, by incorporating an additional term into the potential function, we effectively elevate the energy at the local minima points as depicted in Fig. 1a-c. As a result, the equations of motion for this newly constructed Hamiltonian system are likely to be trapped at these local minima. The entire process is illustrated in Fig. 1d. In standard SB, all trials can be executed in parallel on the GPU. Similarly, in Tabu-Enhanced SB (TESB), the warming up phase runs multiple trials in parallel to construct a shared tabu list, and the subsequent checking phase trials are also executed in parallel using the same tabu list. In detail, the use of the tabu list is inspired by the stochastic mini-batch strategy widely adopted in online learning optimization, such as in stochastic gradient descent (SGD). Specifically, at each iteration, only a small random subset of entries from the tabu list is sampled to construct the penalty term, rather than using the entire list. This approach also enhances the capability of the algorithms to escape from the local minima, thereby improving the overall solution quality.

Regarding convergence, the original SB dynamics form a dissipative system with monotonically decreasing total energy, and have been shown to converge in the long-energy landscape under suitable conditions on the scheduling of a(t). Our enhanced formulation preserves a state-dependent penalty term that recaptures the landscape but does not add explicit time dependency beyond a(t). Consequently, the modified dynamics retain the dissipative nature of the original system, and convergence to a local minimum of the tabu-modified landscape is similarly expected.

**Penalty term construction.** Now we present the details of our Hamiltonian construction. For convenience, we define the set of known minima points as $\mathcal{M} = \{s^{(1)}, s^{(2)}, \ldots\}$. Then we randomly generate $a$ subsets of $\mathcal{M}$, denoted as $\mathcal{S} = \{\mathcal{M}_1, \mathcal{M}_2, \ldots, \mathcal{M}_{a \in [1, a]}\}$, where $a$ is the iteration number. A modified bSB Hamiltonian, incorporating an additional penalty term, is reformulated as follows (the construction is identical for dSB):

The Ising energy evolution of a single run in bSB/dSB is presented. Combinatorial optimization problems, which are often NP-hard, aim to identify the optimal solution from a finite set of possibilities. These problems can be represented using the Ising model, thereby transforming them into energy minimization tasks. In this context, the SB algorithms have emerged as one of the most promising approaches for approximating solutions.

The objective of the Ising problem is to search the spin configuration $\{s_i\} \in \{-1, +1\}^n$ that minimizes the Ising energy given by:

$$E_{\text{Ising}} = -\frac{1}{2} \sum_{i=1}^{n} \sum_{j=1}^{n} J_{ij} s_i s_j - \sum_{i=1}^{n} h_i s_i, \tag{1}$$

where $J_{ij}$ denotes the interactions between different spins and it possesses the property of symmetry, such that $J_{ij} = J_{ji}$ and $J_{ii} = 0$. $h_i$ represents the local external field on spin $i$.

As an algorithm inspired by quantum annealing, the SB algorithms similarly require encoding the Ising problem into a Hamiltonian and then evolving it according to classical equations of motion to find its low-energy state. The Hamiltonians of bSB and dSB are defined as below:

$$H_{\text{aBB}}(x, t) = \frac{a_0}{2} \sum_{i=1}^n y_i^2 + \frac{a_0 - a(t)}{2} \sum_{i=1}^n x_i^2 - a(t) \left( \frac{1}{2} \sum_{i,j=1}^n J_{ij} x_i x_j + \sum_{i=1}^n h_i x_i \right), \tag{2}$$

$$H_{\text{aBB}}(x, t) = \frac{a_0}{2} \sum_{i=1}^n y_i^2 + \frac{a_0 - a(t)}{2} \sum_{i=1}^n x_i^2 - a(t) \left( \frac{1}{2} \sum_{i,j=1}^n J_{ij} x_i x_j + \sum_{i=1}^n h_i x_i \right), \tag{3}$$

In this formulation, the first term corresponds to the kinetic energy, with $y_i$ denoting the generalized momentum. The subsequent terms account for the potential energy, wherein $x_i$ signifies the generalized coordinates, and takes values in the interval $[-1, 1]$. The parameters $\alpha_0$ and $\omega_0$ are constants, typically set as $a_0 = 1$ and $\omega_0 = \frac{1}{2}\sqrt{\frac{N-1}{N+2}\omega^2}$.

The value of $\alpha_0$ is generally chosen to be small to ensure that the potential remains convex at the beginning. The parameter $a(t)$ varies linearly with time. For increasing from 0 to $a_0$, the $a(t)$ increases linearly, so the total potential energy transitions from being predominantly governed by a simple quadratic term at the initial stage to being dominated by the Ising term in the final state.

The iterative evolution equations of the algorithms are obtained by applying the Hamiltonian equations to the systems. The only difference between bSB and dSB lies in the use of a sign function. To solve these equations, we utilize the symplectic Euler method. At the beginning of computation, the system is randomly initialized near the origin, as it corresponds to the minimum point of the simple quadratic term in the initial Hamiltonian. The initial stage of the energy inelastic wall is introduced at the boundaries $x_i = \pm 1$. This boundary condition is implemented numerically by applying the following rule at each step:

$$\begin{cases} x_i = x_i, & y_i = y_i \text{ if } |x_i| \le 1, \\ x_i = \text{sign}(x_i), & y_i = 0, & \text{if } |x_i| > 1. \end{cases} \tag{5}$$

This means that when a particle hits the boundary, it is projected back to the boundary position and its momentum in that direction is absorbed, mimicking an inelastic collision.

Alongside algorithmic progress, the SB framework has spurred efforts toward devices that harness efficient parallelization for scalable combinatorial optimization. Volpe et al. present an open-source VHDL implementation of SB achieving scalability with problem size. Zou et al. achieve up to a 10.9-times speedup over SA via hardware software co-design on a general Ising solver. Qian et al. also provide an open-source FPGA architecture for discrete SB with configurable parallel configuration, substantially extending SB to higher-order polynomial optimization. Beyond hardware, Kanao and Goto extend SB to higher-order polynomial optimization, opening superior performance over second-order reformulations and simulated annealing, thereby broadening its applicability beyond quadratic problems.

The Hamiltonian of the modified bSB (TESbB) and Tabu-Enhanced dSB (TEdSB) will become:

$$H_{\tau}(x, t) = H_{\text{aBB}}(x, \text{kdt}) + \frac{c_{\text{d}}}{\sum_{k=1} |M_k|} \left| x + s^{\mu} \right|^{\tau}, \tag{6}$$

where $\hat{\xi}$ denotes the intensity coefficient of the penalty term. The equation can be expanded as follows:

$$H_{\tau}(x, t) = \frac{a_0}{2} \sum_{i=1}^n y_i^2 + \frac{a_0 - a(t)}{2} \sum_{i=1}^n x_i^2 - a(t) \left( \frac{1}{2} \sum_{i,j=1}^n J_{ij} x_i x_j + \sum_{i=1}^n h_i x_i \right)$$
$$+ \frac{c_{\text{d}}}{2|M|} \sum_{i=1}^n \left( |M_i| x_i^2 + \sum_{s^{\mu} \in M_k} 2 a_i^{\mu} x_i + |M_i| \right), \tag{7}$$

Let $a(t) = a(t) - c_{\text{d}} \hat{\xi}$, then:

$$H_{\tau}(x, t) = \frac{a_0}{2} \sum_{i=1}^n y_i^2 + \frac{a_0 - a(t)}{2} \sum_{i=1}^n x_i^2 - a(t) \left( \frac{1}{2} \sum_{i,j=1}^n J_{ij} x_i x_j + \sum_{i=1}^n h_i x_i \right)$$
$$+ \frac{c_{\text{d}}}{2|M|} \sum_{i=1}^n x_i^2 + \frac{c_{\text{d}}}{2|M|}, \tag{8}$$

Note the three terms introduced by the penalty in Eq. (7), $\frac{c_{\text{d}}}{2} \sum x_i^2$ is absorbed by using $a(t)$ to replace $a(t)$, and $\frac{c_{\text{d}}}{2|M|}$ is independent of $x_j, y$. Thus this penalty term will introduce an extra term $T_i$ into the equation of motion:

$$T_i(t) = -\frac{\partial}{\partial x_i} \left( \frac{c_{\text{d}}}{2|M_i|} \sum_{s^{\mu} \in M_i} y_i^{\mu} \right) = -\frac{c_{\text{d}}}{2|M_i|} \sum_{s^{\mu} \in M_i} y_i^{\mu}, \tag{9}$$

**Figure 1:** Schematic for Tabu-Enhanced Simulated Bifurcation. a) An energy landscape featuring multiple local minima. b) A penalty potential constructed around non-optimal local minima to discourage trapping. c) The combined landscape, where the penalty potential flattens regions around suboptimal minima, facilitating escape and promoting convergence toward better solutions. d) Diagram of the Tabu-Enhanced Simulated Bifurcation workflow. After an Ising problem is provided as input, the warming up phase generates initial approximations, which are subsequently refined in the checking phase. The parameter adjusts the proportion of computational cost allocated to each phase. The checking phase requires a tabu list as input, so a must be less than 1.

Finally, the equations of motion of the Tabu-Enhanced bSB (TESbB) and Tabu-Enhanced dSB (TEdSB) will become:

$$\dot{x}_i(t) = a_0 y_i^{\prime},$$

$$\dot{y}_i(t) = -[a_0 - a^{\prime}(t)] x_i + c_0 \left( \sum_{j=1}^n J_{ij} x_j + h_i \right) + T_i(t), \quad \text{TESbB}$$

$$\dot{y}_i(t) = -[a_0 - a^{\prime}(t)] x_i + c_0 \left( \sum_{j=1}^n g_0(x_j(t)) + h_i \right) + T_i(t), \quad \text{TEdSB} \tag{10}$$

It is important to note that we do not include all identified suboptimal solutions in the construction of the function $T_i$ at each iteration. Instead, we adopt a stochastic mini-batch strategy within our framework. This is motivated by the observation that early local minima may result in misleading information; incorporating them simultaneously could lead to cancellation of information in opposite directions. incorporating them simultaneously could lead to cancellation of information in opposite directions. All previously identified local solutions were used to construct $T_i$, the resulting penalty term would become static, making the algorithms only sensitive to the output of the warming up phase. By contrast, the mini-batch approach introduces diversity into the penalty mechanism by utilizing only a randomly sampled subset of suboptimal solutions at each iteration. In our experiments, we set the tabu list cardinality to $\beta = 1$ and the mini-batch size to $|M_j| = 2$. An evaluation of different parameter settings is presented in Fig. S2 of Supplementary Note 3. These parameter choices yield superior performance for both algorithms.

### Performance analysis

First, we examine the Ising energy evolution during a single run. In TESB and TEdSB, as shown in Fig. 2, the first test, we selected an Ising problem with $N = 2000$ spins. For each algorithm, a sample size of $N_{\text{samples}} = 100$ was used, and the lowest energy among the samples at each iteration was recorded to plot the energy trajectory. The red line corresponds to the warming up phase, while the green line represents the checking phase. The results show that both TESB and TEdSB with the mini-batch strategy achieve higher cut values. This observation highlights the importance of the mini-batch mechanism in maintaining search diversity and avoiding premature convergence.

We further demonstrate the advantages of employing a stochastic mini-batch strategy for constructing the tabu list. Specifically, we compare the performance of a mini-batch approach with batch size $|M_j| = 2$ against that of using the full set of known suboptimal solutions obtained during the warming up phase. Each algorithm was run in parallel on 100 independent samples, solid lines indicate the mean cut values across 100 samples, while scatter points indicate the maximum cut value observed in those samples. The results show that both TESB and TEdSB with the mini-batch strategy achieve higher cut values. This observation highlights the importance of the mini-batch mechanism in maintaining search diversity and avoiding premature convergence.

We further demonstrate the advantages of employing a stochastic mini-batch strategy for constructing the tabu list. Specifically, we compare the performance of a mini-batch approach with batch size $|M_j| = 2$ against that of using the full set of known suboptimal solutions obtained during the warming up phase. Each algorithm was run in parallel on 100 independent samples, solid lines indicate the mean cut values across 100 samples, while the scatter points indicate the maximum cut value observed in those samples. The results show that both TESB and TEdSB with the mini-batch strategy achieve higher cut values. This observation highlights the importance of the mini-batch mechanism in maintaining search diversity and avoiding premature convergence.

We further demonstrate the advantages of employing a stochastic mini-batch strategy for constructing the tabu list. Specifically, we compare the performance of a mini-batch approach with batch size $|M_j| = 2$ against that of using the full set of known suboptimal solutions obtained during the warming up phase. Each algorithm was run in parallel on 100 independent samples, solid lines indicate the mean cut values across 100 samples, while the scatter points indicate the maximum cut value observed in those samples. The results show that both TESB and TEdSB with the mini-batch strategy achieve higher cut values. This observation highlights the importance of the mini-batch mechanism in maintaining search diversity and avoiding premature convergence.

In the tests above, the warming up phase was set to 1000 iterations. To provide more compelling evidence of the effectiveness of the Tabu-Enhanced framework, we further evaluate its performance under different values of the checking phase proportion $\alpha$, which is the proportion of the checking phase within a fixed total iteration count of 10,000. As shown in Fig. 4, the approximation ratio for Max-Cut problem instances with the proportion of the checking phase is set to zero, the TESB and TEdSB reduce to their baseline counterparts, bSB and dSB, respectively. The results indicate that both algorithms achieve best performance when the checking phase proportion is between 0.3 and 0.9, as illustrated in Fig. 5.

**Experimental evaluation**

We evaluated the performance of the proposed TESB and TEdSB methods by comparing them to the original bSB and dSB algorithms. The evaluation was conducted on instances from two benchmark datasets: the Max-Cut problem, G-set, and the large formulation of the track reconstruction dataset TrackML. All experiments were conducted on a system equipped with an Intel Xeon E5-2690 v4 CPU (2.20 GHz) and an NVIDIA RTX 4090 GPU. The core optimization routine for both baseline SB algorithms and our Tabu-Enhanced SB were implemented in CUDA and executed exclusively on the GPU. This ensured a fair and symmetric hardware configuration across all compared methods.

### Results on Max-Cut problems

We first provide a visual demonstration of the proposed improvements by presenting histograms and cumulative distribution plots. Subsequently, we evaluate the computational efficiency of the algorithm using the Time-to-Solution (TTS) metric, which is widely used for performance comparison across optimization algorithms. The TTS is computed using the following formula:

$$\text{TTS} = T \frac{\log(1 - 0.99)}{\log(1 - P_s)}, \tag{11}$$

where $T$ represents the actual time taken for the algorithm to sample one result, and $P_s$ is the probability of the algorithm finding the optimal solution. TTS is a performance metric that jointly considers computational runtime and the accuracy of the obtained solution. In the Max-Cut problem instances, the best-known solutions are widely used as a reference for assessing solution quality. However, for instances where the optimal solution is unknown, we compare with practical benchmarks against known methods.

**Figure 2:** Comparison of convergence on a 2000-spin Ising problem. Performance of TESB (a) and TEdSB (b) compared to their baseline algorithms on a 2000-spin Ising problem. Each run was conducted on instances of different sizes. Over 10,000 iterations, with the first 1000 iterations used for warming up (red) and the remaining 9000 for checking (green). The blue line represents the performance of the baseline bSB and dSB algorithms, respectively. The lowest energy achieved at each iteration is plotted, demonstrating improved convergence after the checking phase.

**Figure 3:** Impact of mini-batch strategy on algorithm performance. Comparison of TESB and TEdSB performance with and without the mini-batch strategy on Max-Cut instances G22 (a, b) and G24 (c, d), each containing 2000 nodes. "mini-batch" refers to constructing the tabu item using only 2, whereas "full-batch" denotes the use of all suboptimal solutions obtained during the warming up phase. Each algorithm was run in parallel on 100 independent samples, solid lines indicate the mean cut value observed in those samples. The results show that TESB and TEdSB achieve higher probability of finding best cut value achieved.

**Figure 4:** Algorithm performance of varying checking phase proportion. Comparison of TESB (a) and TEdSB (b) under varying proportions of the checking phase within a fixed total iteration count of 10,000. As shown in Fig. 4, the approximation ratio for Max-Cut problem instances G22 (N=2000), G23 (N=2000), and G24 (N=2000). The y-axis represents the ratio between the cut value obtained by the algorithm and the best-known optimal value. Solid lines show the mean ± standard deviation over 100 samples. Unfilled markers indicate the best cut value achieved. It can be observed that setting α = 0.9 yields superior performance for both algorithms. When α = 0, TESB and TEdSB reduce to their baseline counterparts, bSB and dSB, respectively.

Experiments, each instance was evaluated over 1000 independent trials, with a budget of 10,000 iterations per trial.

**Figure 5:** Cut value distributions for different Max-Cut instances. Performance of the algorithms on Max-Cut instances of different sizes. G7 (a-d) with 800 nodes and G22 (e-h) with 2000 nodes. Results are averaged over 1000 independent samples. Histograms show the probability distribution of cut values, while solid curves depict the corresponding cumulative distribution. In the cumulative plots, the optimal cut value is marked by a red dashed line. Different colors correspond to different algorithms: panels (a, b) compare bSB and TESB, while (d) compare dSB and TEdSB. The result shows that TESB and TEdSB achieve a higher probability of finding near-optimal or optimal solutions compared to their baseline counterparts.

**Table 1: Time-to-solution for Max-Cut instances**

| Instance | bSB | TESB | dSB | TEdSB |
|----------|-----|------|-----|-------|
| G1 (N=800) | >5686 | >3586 | 3943.1 | 75.77 |
| G2 (N=800) | >5247 | >7405 | 1811 | 1562 |
| G3 (N=800) | 37.02 | 10.64 | 907.1 | 239.3 |
| G4 (N=800) | 5254 | 1.824 | 420.3 | 6.796 |
| G5 (N=800) | >2443 | 1.083 | 362.3 | 109.5 |
| G6 (N=800) | >2148 | >2598 | 172.7 | 31.72 |
| G7 (N=800) | >2141 | 14.62 | 54.83 | 4.831 |
| G8 (N=800) | 356.1 | 5.390 | 445.4 | 81.17 |
| G9 (N=800) | >2141 | 51.70 | 743.5 | 360.4 |
| G10 (N=800) | >2149 | >2955 | 2260 | 445.8 |
| G21 (N=2000) | >3283 | >5472 | >3489 | 412.9 |
| G22 (N=2000) | >6213 | >8679 | >5690 | 462.0 |
| G23 (N=2000) | >6281 | (2901) | (20.29) | (8.903) |
| G24 (N=2000) | >6213 | >8728 | >6679 | 153.2 |
| G25 (N=2000) | >6197 | >8684 | >6617 | 2327 |
| G26 (N=2000) | >6234 | >8676 | >6584 | 2317 |
| G27 (N=2000) | >6211 | >8817 | 336.7 | 75.89 |
| G28 (N=2000) | >6304 | >8775 | 974.2 | 106.0 |
| G29 (N=2000) | >6216 | >8823 | 740.0 | 404.6 |
| G30 (N=2000) | >6256 | >8876 | 679.9 | 756.7 |
| K2000 (N=2000) | >12759 | >20059 | 4325.4 | 411.3 |

TTS results obtained from 1000 independent runs under a fixed budget of 10,000 iterations per run. A > symbol indicates that the target solution was not attained in any run, implying a success probability of zero. TTS (in seconds): the time needed to find the best solution value. Reported value that is not exactly optimal. All hyperparameters are fixed to the values specified in Section Methods.

**Table 2: Results on Ising problems from track reconstruction**

|  | **bSB** |  | **TESB** |  | **dSB** |  | **TEdSB** |  |
|--|---------|--|---------|--|---------|--|----------|--|
|  | **Time (s)** | **Energy (u.i.)** | **Time (s)** | **Energy (u.i.)** | **Time (s)** | **Energy (u.i.)** | **Time (s)** | **Energy (u.i.)** |
| ev1004 (N=109498) | 8.67 | -448998 | 7.25 | -449363 | 9.02 | -447488 | 7.43 | -449349 |
| ev1014 (N=78812) | 5.06 | -263353 | 4.27 | -263650 | 5.24 | -261860 | 4.33 | -263641 |
| ev1023 (N=80113) | 5.33 | -281244 | 4.42 | -261345 | 5.48 | -260928 | 4.80 | -261362 |

For each algorithm, we recorded the runtime and the lowest energy found. The bolded values indicate the minimum energy achieved across all methods. As observed, TESB and TEdSB identify lower-energy solutions with reduced computational cost compared to bSB and dSB.

Solutions that happen to lie near forbidden regions, particularly in problems with dense clusters of near-optimal configurations. Thus, the method's effectiveness depends on the geometric structure of the solution space—a dependency that warrants deeper theoretical investigations in future work.

Our approach can be interpreted as integrating the principles of tabu search into the framework of simulated physical solvers. This hybridization demonstrates that non-conventional optimization methods can benefit from classical algorithmic strategies, paving the way for the development of more efficient and capable solvers. Future work may explore further integration of heuristic search mechanisms into physics-inspired algorithms, as well as their applications to a broader range of real-world optimization tasks.

## Methods

The proposed algorithms, referred to as TESB and TEdSB, consist of two main phases: the warming up phase and the checking phase. In the warming up phase, the standard bSB or dSB algorithms are executed numerically using Eq. (4) and Eq. (5), for a total of $(1-\alpha) N_{\text{iter}}$ iterations, where $N_{\text{iter}}$ denotes the total number of iterations. During this phase, a collection of optimal solutions is generated and stored in the set $\mathcal{M}$, which will serve for the subsequent checking phase. In the checking phase, Eq. (6) guided the system evolution, and lasts for $\alpha N_{\text{iter}}$ iterations. At each iteration $\ell$, a subset of solutions is randomly sampled from $\mathcal{M}$, and used to construct the additional term $T_i$ in Eq. (9).

The pseudo-code is presented in Algorithm 1. with a time step of dr = 1, a mini-batch size of $|M_j| = 2$ and a cardinality of $\alpha = 0.9$ and $\beta = 1$ throughout our experiments.

The parameters $\alpha_0$ and $\omega_0$ follow the prescriptions in ref. [^1]: $a_0 = 1$ and $\omega_0 = \frac{1}{2}\sqrt{\frac{N-1}{N+2}\omega^2}$.

However, in the checking phase, due to the presence of the additional term $T_i$, the standard formula for $c_0$ no longer applies. Instead, we select the optimal value from the candidates set $\{0.02, 0.05, 0.08, 0.1\}$, and use $\alpha = 0.9$ and $\beta = 1$ throughout our experiments.

### Algorithm 1. Tabu-Enhanced Simulated Bifurcation

**Input:** $I_0, h_0, c_0, a_r, \beta, N_{\text{iter}}, \phi_0$

**Output:** $s^*.

for t = 1 to nt do
- Randomly generate initial values for x, y;
- for i = 1 to N do
  - Update x and y as in Equation (1);
  - end for
- end for
- Record set $\mathcal{M} = \{s^{(1)}, s^{(2)}, \ldots, s^{(nt)}\}$.

Randomly generate $a N_{\text{iter}}$ subsets of $\mathcal{M}$ with mini-batch size $m_b$: $\{\mathcal{M}_1, \mathcal{M}_2, \ldots, \mathcal{M}_{a N_{\text{iter}}}\}$.

for t = 1 to $N_{\text{sample}}$ do

Randomly generate initial values for x, y;

for i = 1 to $N_{\text{iter}}$ do
  - Update x and y as in Equation (10);
  - end for

Record set $\mathcal{X} = \{x^{(1)}, x^{(2)}, \ldots, x^{(N_{\text{sample}})}\}$.

**Data availability**

Two types of datasets were used in this work. The first dataset is a publicly available benchmark suite from the G-set collection, which can be downloaded from https://web.stanford.edu/~yyye/Gset/. The second dataset was obtained from the TrackML Particle Identification Challenge hosted on Kaggle at https://kaggle.com/competitions/trackml-particle-identification. This dataset was subsequently used to construct the corresponding Ising model representation using the legup-galileo Python package. The corresponding Ising models involve tens of thousands of spin variables, and the interactions between spins are weighted. In terms of experimental settings, we allocated 1000 total iterations for bSB and dSB. TESB and TEdSB determine the number of iterations based on when convergence was observed in preliminary runs. Given that the global minimum energy is unknown in these cases, we determined based on when convergence was observed in preliminary runs.

## Conclusions

Simulated physical solvers, such as the SB algorithms, have demonstrated significant potential in solving combinatorial optimization problems. These methods typically map discrete problems onto continuous variable spaces and governed by differential equations. In this work, we introduce Tabu-Enhanced Simulated Bifurcation (TESB), an improved SB variant that incorporates dynamic penalty guided by early search history. This modification enables more refined local searches, thereby increasing the likelihood of obtaining optimal or near-optimal solutions.

Our numerical experiments on the G-set benchmark dataset show that the proposed method can reduce the Time-to-Solution (TTS) by up to three orders of magnitude compared to the baseline SB algorithms. Moreover, when applied to track reconstruction in high-energy physics, the method finds lower-energy solutions on problem instances with reduced computational cost.

The tabu mechanism can be viewed as a landscape regularizer that penalizes solutions close to recently visited states, thereby encouraging escape from local minima. However, this may suppress high-quality solutions that happen to lie near forbidden regions, particularly in problems with dense clusters of near-optimal configurations. Thus, the method's effectiveness depends on the geometric structure of the solution space—a dependency that warrants deeper theoretical investigations in future work.

Our approach can be interpreted as integrating the principles of tabu search into the framework of simulated physical solvers. This hybridization demonstrates that non-conventional optimization methods can benefit from classical algorithmic strategies, paving the way for the development of more efficient and capable solvers. Future work may explore further integration of heuristic search mechanisms into physics-inspired algorithms, as well as their applications to a broader range of real-world optimization tasks.

## References

1. Bartolacci, M. R., LeBlanc, L. J., Kayikci, Y. & Grossman, T. A. Optimization modeling for logistics: options and implementations. J. Bus. Logist. 30, 3–18 (2012).

2. Caunrye, A. M., Nie, X. & Pokharel, S. Optimization models in supply chain and logistics: literature review and comparative study. Int. J. Oper. Res. 13, 61–79 (2012).

3. Comellas, G. and TiTündü, R., Optimization methods in finance, Vol. volume 5 (Cambridge University Press, 2006).

4. Orús, R., Mugel, S. & Lizaso, E. Quantum computing for finance: Overview and prospects. Rev. Phys. 4, 100028 (2019).

5. Baum, M., Nau, G., W. Reinert, K. Accurate multiple sequence-structure alignment of a sequences using combinatorial optimization. Bioinformatics 23, 1803–1810 (2007).

6. Wang, L., Wang, Y. & Chang, Q. Feature selection methods for big data bioinformatics: A survey from the search perspective. Methods 111, 21 (2016).

7. Odli, J. B.. Combinatorial optimization in science and engineering. Curr. Sci. 112, 2268 (2017).

8. Papadimitriou, C.H. and Steiglitz, K., Combinatorial optimization: algorithms and complexity (Courier Corporation, 1988).

9. Lucas, A. Ising formulations of many NP problems. Front. Phys. 2, 5 (2014).

10. Bolko, S. et al. Evidence for quantum annealing with more than one hundred qubits. Nat. Phys. 10, 218 (2014).

11. Byrsk, P. L. et al. Architectural considerations in the design of a superconducting quantum annealing processor. IEEE Trans. Appl. Supercond. 26, 1 (2016).

12. Johnson, M. W. et al. Quantum annealing with manufactured spins. Nature 473, 194 (2011).

13. Kuramata, M., Katsuki, R. and Nakata, K. Larger sparse quadratic unconstrained binary optimization using quantum annealing in 2021 IEEE 8th International Conference on Industrial Engineering and Applications (ICIEA) (IEEE, 2021) pp. 556–566.

14. Osada, E., Villar-Rodriguez, E., Oregi, I. and Moreno-Fernandez de Leceta, A. Focusing on hybrid quantum-classical optimization techniques: new results on the asymmetric salesman problem. in Proc. Genetic and Evolutionary Computation Conference (ACM, 2021) pp. 1476–1482.

15. Negose, N. H. et al. Shortcuts to adiabaticity in digitized adiabatic quantum computing. Phys. Rev. Appl. 15, 024038 (2021).

16. Hamerly, R. et al. Experimental investigation of performance differences between coherent ising machines and quantum annealing. Sci. Adv. 5, eaau3033 (2019).

17. Inagaki, T. et al. A coherent ising machine for 2000-node optimization. Science 354, 603–606 (2016).

18. Marandi, A., Wang, Z., Takata, K., Byer, R. L. & Yamamoto, Y. Network all-time-multiplexed optical parametric oscillators as a coherent ising machine. Nat. Photonics 8, 937 (2014).

19. McMahon, P. L. et al. A fully programmable 100-spin coherent ising machine with all-to-all connections. Science 354, 614 (2016).

20. Yamamoto, Y., Lersu, T., Ganguli, S. & Mabuchi, H. Coherent machine quantum optics and neural networks perspectives. Appl. Phys. Lett. 117, 160501 (2020).

21. Chou, L. Breimauser, S., Ghosh, S. & Herzog, W. Analog coupled oscillator based weighted machine. Sci. Rep. 9, 14786 (2019).

22. Wong, T. and Roychowdhury, V. Quantum oscillator ising machines. Biochemical Computation and Natural Computing: 18th International Conference, UCMC 2019, Tokyo, Japan, June 3-7, 2019, Proceedings 18 (Springer-Nature, 2019, pp. 232–255.

23. Aramon, M. et al. Physics-inspired optimization for quadratic unconstrained problems using non-stoquastic hamiltonians. Nat. Rev. Phys. 1, 48 (2019).

24. Cai, F. et al. Power-efficient combinatorial optimization using intrinsic memristor hopfield neural networks. Nat. Electron. 3, 409 (2020).

25. Borders, W. A. et al. Integer factorization using stochastic magnetic tunnel junctions. Nature 573, 390 (2019).

26. Carrisan, K. Y., Sutton, B. M. & Datta, S. P-bits for probabilistic spin logic. Phys. Rev. Appl. 11 (2019).

27. Sankar, K. et al. A benchmarking study of quantum algorithms for combinatorial optimization. arXiv preprint arXiv:1602.07821 (2016).

28. Bowles, J., Dauphin, A., Huembel, P., Martinez, J. & Acin, A. Quantum-error-protected binary optimization via adiabatic quantum annealing. Phys. Rev. Appl. 8, 034016 (2022).

29. Mitra-Spiradiachenko, A. et al. A mini-field approximation algorithm. PRX Quantum 4, 033335 (2023).

30. Pichlorymaki, S., Kelso, S. Coquera, F., Landi, T. & Yamamoto, Y. Coherent ising machines with optical error correction circuits. Adv. Technol. 4, 2100007 (2022).

31. Tsunov, E. S., Ulianov, A. E. & Lvovsky, A. Annealing by simulating the coherent ising machine. Opt. Express 27, 10288 (2019).

32. Goto, H., Tatsumura, K. & Dixon, A. R. Combinatorial optimization by simulating adiabatic bifurcations with nonlinear hamiltonians. Sci. Adv. 5, eaav2372 (2019).

33. Goto, H. et al. High-performance combinatorial optimization based on classical mechanics. Sci. Adv. 7, eabe7953 (2021).

34. Zeng, Q.-G. et al. Performance of quantum annealing inspired algorithms for combinatorial optimization problems. Commun. Phys. 7, 249 (2024).

35. Takabe, S. Deep unfolded simulated bifurcation for massive MIMO signal detection. IEICE Trans. Fundam. Electron. Comput. Sci. https://doi.org/10.1587/transfun.2025STAP001 (2025).

36. Okawa, H., Zeng, Q.-G., Kao, X.-Z. & Yung, M. H. Quantum-annealing-inspired algorithms for track reconstruction at high-energy colliders. arXiv Preprint. arXiv:2404.09421 (2024).

37. Kanao, T. & Goto, H. Simulated bifurcation assisted by thermal fluctuation. Commun. Phys. 5, 153 (2022).

38. Blanzier, E., Pastorello, D., Cavecchia, V. and Mattieva, M. Evaluating the convergence of tabu-enhanced hybrid quantum optimization. Quantum. Inf. Process. 22, 205 (2023).

39. Pastorello, D., Blanzier, E. & Cavecchia, V. Learning adiabatic quantum algorithms over optimization problems. arXiv:2105.11121 (2021).

40. Laguna, M. Tabu search. in Handbook of heuristics (Springer, pp. 741–758, 2018).

41. G-set, https://web.stanford.edu/~yyye/Gset/.

42. King, J., Yarkoni, S., Nevil, M. M., Hilton, J. P. & McGeoch, C. C. Benchmarking a quantum annealing processor with the time-to-target metric. arXiv preprint arXiv:1508.05087 (2015).

43. Volpe, D., Grillo, G., Zamponi, M., Graziano, M. & Turvani, G. Improving the exploitability of Simulated Adiabatic Bifurcation through a flexible and scalable digital architecture. ACM Trans. Quantum Comput. 6, 1–50 (2025).

44. Zou, Y. & Lin, M. Massively simulating adiabatic bifurcations with FPGA to solve combinatorial optimization. Proceedings Of The 2020 ASME/IEEE/SIAM Symposium On Field-Programmable Gate Arrays, pp. 85–75 (2020).

45. Orlando, F. et al. High-Parallel FPGA-Based Discrete Simulated Bifurcation for Large-Scale Optimization. arXiv:2510.12407 (2025).

46. Kanao, T. & Goto, H. Simulated bifurcation for higher-order cost functions. Appl. Phys. Express. 16, 014501 (2022).

47. Ruder, S. An overview of gradient descent optimization algorithms. arXiv Preprint arXiv:1609.04747 (2016).

48. Kilmer, S. Ray-gradient descent optimization and Control (CDC), pp. 2880–2887 (2017).

49. Jin, S., Li, J. & Liu, J. Random batch methods (RBM) for interacting particles systems. J. Comput. Phys. 400, 108877 (2020).

50. Liu, B., Wang, K., Xiao, D. & Yu, Z. Mathematical mechanism on dynamics algorithms of the Ising model. arXiv:2012.01156 (2020).

51. Satzinger, A. et al. Realtime Particle Tracking Challenge. Kaggle. (https://kaggle.com/competitions/trackml-particle-identification, 2018).

52. ATLAS, Collaboration. ATLAS software and computing HL-LHC roadmap. Tech. Rep. (Technical report, CERN, Geneva, https://cds.cern.ch/record/2815292 (CERN, Geneva, 2022).

53. CMS Software and Computing. CMS Phase-2 Computing Model: Technical Document. Tech. Rep. (https://cds.cern.ch/record/2815292 (CERN, Geneva, 2022).

54. Barret, F. et al. A parametric algorithm for quantum annealing. Comput. Softw. Big Sci. 4, 1 (2020).

55. Shao, K. et al. Quantum annealing algorithms for track pattern recognition. EPJ Web Conf. 245, 10006 (2020).

56. Ziekapa, A. et al. Charged particle tracking with quantum annealing-inspired optimization. Quantum Mach. Intel. 3, 27 (2021).

57. Chan, W. et al. Application of quantum computing techniques in particle tracking at LHC. (CERN,2023), https://cds.cern.ch/record/2869559.

58. Derin, HEPOQR Qalise. https://github.com/derin/hepoqr-qalise, 2019.

## Acknowledgements

This work was supported by the National Natural Science Foundation of China 12188102.

## Author contributions

M.H.Y. and H.O. supervised the project. X.T. and Q.Z. performed the numerical experiments and wrote the first draft of the manuscript. X.T., Q.Z., Z.H., B.Z., Y.L., J.Z., H.O. and M.H.Y. contributed to and participated in analyzing the results and modifying the manuscript.

## Competing interests

The authors declare no competing interests.

## Additional information

**Supplementary information** The online version contains supplementary material available at https://doi.org/10.1038/s42005-026-02538-2.

**Correspondence and requests for materials** should be addressed to Jiapei Zhuang, Hideki Okawa or Man-Hong Yung.

**Peer review information** Communications Physics thanks Alexander Rumyantsev and the other, anonymous, reviewer(s) for their contribution to the peer review of this work. A peer review file is available.

## Open Access

This article is licensed under a Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License, which permits any non-commercial use, sharing, distribution and reproduction in any medium or format, as long as you give appropriate credit to the original author(s) and the source, provide a link to the Creative Commons licence, and indicate if you modified the licensed material. You do not have the permission under this licence to share adapted material derived from the article or third party material in this article are included in the article's Creative Commons licence and your intended use is not permitted by this licence, you will need to obtain permission directly from the copyright holder. To view a copy of this licence, visit http://creativecommons.org/licenses/by-nc-nd/4.0/.

© The Author(s) 2026
