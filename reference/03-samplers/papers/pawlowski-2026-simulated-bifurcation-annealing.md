# Simulated Bifurcation Quantum Annealing


> **Citation.** Canonical entry `pawlowski2026` in [`references.bib`](../../references.bib) (resolved via Crossref/DataCite). arXiv:[2604.01050](https://arxiv.org/abs/2604.01050).
>
> **Companion note.** [`pawlowski-2026-simulated-bifurcation-annealing.note.md`](./pawlowski-2026-simulated-bifurcation-annealing.note.md) — how this paper links to Gibbsiq.

J. Pawłowski,1,2 P. Tarasiuk,2 J. Tuziemski,2 L. Pawela,1,2 and B. Gardas3

1 Institute of Theoretical Physics, Faculty of Fundamental Problems of Technology,
Wrocław University of Science and Technology, 50-370 Wrocław, Poland
Quantum.io Sp. z o.o., Pułaskiego 12/3, 02-566 Warsaw

2 Institute of Theoretical and Applied Informatics,
Polish Academy of Sciences, Bałtycka 5, 44-100 Gliwice, Poland

3 M. Smoluchowski Institute of Physics, Jagiellonian University, 30-348 Kraków, Poland

## Abstract

We introduce Simulated Bifurcation Quantum Annealing (SBQA), a quantum-inspired optimization algorithm that extends simulated bifurcation by incorporating inter-replica interactions to mimic quantum tunneling. SBQA retains the efficiency and parallelism of simulated bifurcation while improving performance on sparse and rugged energy landscapes. We derive its equations of motion, analyze parameter dependence, and propose a lightweight auto-tuning strategy. A comprehensive benchmarking study on both large-scale problems and smaller instances relevant for current quantum hardware shows that SBQA systematically improves on SBM in the sparse and rugged regimes where SBM is known to struggle, while remaining competitive and versatile across a diverse set of tested problem families. These results position SBQA as a practical quantum-inspired optimization heuristic and a stronger classical baseline for the sparse and rugged regimes studied here.

## I. INTRODUCTION

Combinatorial optimization problems are ubiquitous in science and industry [1–4] and can often be formulated as the task of finding the ground state of an Ising spin-glass Hamiltonian [5]. Quantum annealing (QA) offers a promising hardware-based approach to tackling such problems by leveraging quantum superposition and tunneling effects [6–8]. However, practical implementations remain constrained by limited qubit connectivity [9, 10], noise, and finite coherence times [11, 12], which have so far prevented an unambiguous demonstration of quantum speedup or general computational advantage [13–18].

In parallel, a rapidly growing class of physics-inspired classical algorithms has emerged, offering competitive performance on standard hardware by emulating physical processes, including aspects of quantum dynamics [19–22]. Among these approaches, the Simulated Bifurcation Machine (SBM) stands out as a highly efficient and scalable optimization method based on nonlinear Hamiltonian dynamics exhibiting chaotic behavior and bifurcations. This dynamical system can be interpreted as a mean-field approximation of a network of Kerr parametric oscillators [23–26]. Despite its efficiency and versatility, SBM is known to exhibit a systematic weakness on certain classes of energy landscapes, particularly those featuring steep, isolated optima or very sparse connectivity [27, 28].

In this work, we introduce **Simulated Bifurcation Quantum Annealing (SBQA)**, an optimization algorithm designed to address these limitations by combining the efficiency of SBM with key ingredients of Discrete-Time Simulated Quantum Annealing (DTSQA). DTSQA is derived from a path-integral Monte Carlo formulation of the transverse-field Ising model at finite temperature [29, 30]. Through a Suzuki–Trotter decomposition of the quantum partition function, an additional (imaginary-time) dimension is introduced, mapping the original d-dimensional quantum system onto a (d + 1)-dimensional classical system [31]. In this representation, quantum fluctuations induced by the transverse field appear as inter-replica interactions between copies (imaginary-time slices), while the annealing process is realized by gradually reducing the transverse-field strength.

Motivated by this replica-based picture, we extend the original SBM formulation by introducing an effective inter-replica coupling between otherwise independent trajectories. This interaction acts as a classical surrogate to quantum tunneling and helps the dynamics escape local minima. Crucially, even modest performance improvements—on the order of a few percent—can be decisive in practice. Recent evidence indicates that claims of quantum advantage often hinge on such narrow margins, and the distinction between observing an advantage and failing to do so resting on quantum effects. In this sense, improvements of the magnitude considered here are not merely incremental but can qualitatively alter the outcome of quantum–classical performance comparisons [18].

Our contribution is threefold. First, we derive the modified SBM equations of motion with inter-replica interactions and show that this enhancement has only a minimal performance overhead [32]. Second, we analyze the role of the additional hyperparameters and propose a lightweight auto-tuning strategy for avoiding expensive instance-specific optimization.

Third, and most importantly, we perform a comprehensive benchmarking study divided into two parts. Part one focuses on large-scale sparse problems, where we compare SBM and SBQA in terms of asymptotic time-to-epsilon scaling. We study Zephyr graphs, which underlie the latest-generation Advantage2 quantum annealers, instances defined on the logical graphs of the Quantum Annealing Correction (QAC) error-correction scheme, recently used in an attempt to demonstrate quantum scaling advantage [32].

## II. METHODS

### A. Simulated Bifurcation Quantum Annealing

Our starting point is a classical Hamiltonian describing a system of N particles, interacting via Ising-like interactions, and subject to a time-dependent external potential:

$$H = \frac{a_0}{2} \sum_{i=1}^{N} p_i^2 + V, \tag{1}$$

$$V = \sum_{i=1}^{N} \left[ \frac{a_0 - a(t)}{2} q_i^2 - c_0 h_i q_i - \frac{c_0}{2} \sum_{j \neq i} J_{ij} f(q_j) \right], \tag{2}$$

where $a(t) = t/T$ and $T$ is the total time of the evolution. The trajectories of the particles are confined to a d-dimensional unit hypercube, which is achieved by imposing that $V = \infty$ if $|q_i| > 1$. Using Hamilton's equations, we can derive the following dynamical system, called the Simulated Bifurcation Machine (SBM):

$$\dot{q}_i = a_0 p_i, \tag{3}$$

$$\dot{p}_i = -[a_0 - a(t)] q_i - c_0 h_i q_i - \frac{c_0}{2} \sum_{j=1}^{N} J_{ij} f(q_j) + h_i, \tag{4}$$

with the condition that if $|q_i| > 1$, then $q_i \to \text{sign}(q_i)$ and $p_i \to 0$. These equations are chaotic and exhibit bifurcations.

The inter-replica modifications in our SBQA approach extend this by introducing an effective inter-replica coupling derived from the Suzuki–Trotter decomposition of the quantum partition function. For a composite system of N particles and R replicas, the SBQA Hamiltonian reads:

$$H = \sum_{i=1}^{N} \sum_{k=1}^{R} \left[ \frac{a_0}{2R} \dot{p}_{i,k}^2 + \frac{a_0 - a(t)}{2R} q_{i,k}^2 - \frac{c_0}{R}\left( h_i q_{i,k} + \frac{1}{2} \sum_{j=1}^{N} J_{ij} q_i q_{i,k} + J_{\perp}(t) q_i q_{i,k+1} \right) - J_{\perp}(t) q_i q_{i,k+1} \right], \tag{4}$$

$$J_{\perp}(t) = -\frac{1}{2\beta} \ln \tanh\left( \frac{\beta \Gamma_x(t)}{R} \right), \quad \Gamma_x(t) = \Gamma_x(0) \left[ (1 - t/T)^\alpha + 10^{-5} \right], \tag{5}$$

where $J_{\perp}$ is the inter-replica coupling strength (see Sec. SI in Ref. [38] for derivation). $\Gamma_x(0)$ is the initial transverse-field scale, $\beta$ is the inverse temperature, and $\alpha$ is the annealing schedule exponent. The additive $10^{-5}$ term is a numerical regularization used in the implementation to prevent the argument of tanh from vanishing at the final time step; without it, $J_{\perp}(t)$ becomes singular as $t \to T$.

Writing down Hamilton's equations, we obtain the equations of motion for the SBQA dynamical system:

$$\dot{q}_{i,k} = \frac{a_0}{R} p_{i,k}, \tag{6}$$

$$\dot{p}_{i,k} = -\left[ \frac{a_0 - a(t)}{R} q_{i,k} + \frac{c_0}{R} \left( \sum_{j=1}^{N} J_{ij} f(q_j) + h_i \right) \right] + J_{\perp} (q_{i,k-1} + q_{i,k+1}), \tag{7}$$

### B. Parameter sensitivity and auto-tuning

We now discuss the impact of the two new hyperparameters introduced in SBQA, namely the inverse temperature $\beta$ and the annealing schedule exponent $\alpha$. The former corresponds to the inverse temperature in the quantum partition function, while the latter governs the ramp-up of the replica interaction strength $J_{\perp}(t)$. Although $\alpha = 1$ is the standard choice in quantum annealing, we nevertheless allow it to vary and study its impact. The remaining parameters, $\alpha_0$ and $T$, as well as their tuning procedures, are inherited from the original SBM and retain their interpretation. To avoid over-tuning to a single instance family, we select a diverse set of instances of various sizes, including both dense and sparse problems, while maintaining a quantum-annealing-oriented focus. The chosen instances are:

(a) fully connected Wishart Ensemble instance with N = 500 variables and hardness parameter $\eta = 0.2$ [40],

(b) cubic lattice Ising spin glass embedded into the Pegasus $P_{16}$ graph with N ≈ 5400 variables [29, 35],

(c) 50 × 50 square lattice with random uniform couplings drawn from $[-1,1]$,

(d) Quantum Annealing Correction (QAC) instance with side length $L = 15$ and N = 1322 variables [17],

(e) Pegasus $P_4$ graph with the Corrupted Bias Ferromagnetic coupling distribution and N = 216 variables [41],

(f) Pegasus $P_{16}$ graph with NAT-7 random couplings [42].

As the figure of merit, we use the optimality gap, defined as:

$$g = \frac{E - E_0}{|E_0|}, \tag{9}$$

where $E_0$ is the best known energy (in particular the ground state energy, if known) and $E$ is the energy of the returned solution. We plot the results in Fig. 1, where each point is averaged over 10 independent runs, with a series of 128 interacting replicas per run. Based on these results, we restrict the range of hyperparameters to $\beta \in [0.5, 1.5]$ and $\alpha \in [0.5, 1.0]$. Since it is neither obvious how to select the optimal values within these ranges, nor desirable to perform costly per-instance tuning, we introduce a simple auto-tuning procedure. The total number of processed samples $N_{\text{samples}}$ is split into $N_{\text{repetitions}}$ with interacting $N_{\text{replicas}}$ replicas each. For each repetition, we randomly select $\beta$ and $\alpha$ from the above ranges, and evolve the system. Finally, we return the best solution from all repetitions. This procedure is simple, yet effective, as it allows one to explore a variety of hyperparameter combinations, without incurring significant overhead. Modern GPUs allow all $N_{\text{repetitions}}$ repetitions to be executed in parallel.

## III. RESULTS

A typical measure of performance for heuristic optimization algorithms is the time-to-solution (TTS) metric, defined as the time required to find the optimal solution with a specified probability, e.g. 99% [43]. However, in the context of large-scale combinatorial optimization, consisting on finding the optimal solution is often impractical due to the exponentially growing complexity of the energy landscape. In many real-world applications, the priority shifts from exactness to utility, and one must often settle for approximate solutions. Therefore, the critical figure of merit is not necessarily the ability to find the best possible state, but to find high-quality solutions (with some finite tolerance) within a reasonable computational time.

To rigorously quantify this performance, we follow recent works on this topic and adopt the time-to-epsilon metric [17, 18]. This metric is defined as the expected computational time required to find a solution within an energy $\epsilon$ of the ground state (or a suitable reference solution) at least once in a single run.

$$\text{TT}\epsilon = \tau \frac{\log(1 - p_{\text{target}})}{\log(1 - p_{\text{success}})} \tag{10}$$

where $\tau$ is the average time per run of the algorithm, and $p_{\text{success}}$ is the probability of finding a solution within $\epsilon$ of the ground state (or a suitable reference solution) at least once in a single run.

For this metric to be meaningful, one has to be careful with time measurements, ensuring that they reflect the actual, externally measurable computation cost of the algorithm. A common pitfall in the case of quantum annealers is to use the annealing time of a single run, instead of the total operation time, which includes annealing of multiple shots, programming, thermalization, readout, etc., and is accessible e.g. as the "QPU access time" on D-Wave machines. This is especially important when comparing quantum and classical methods, to avoid misleading conclusions about runtime supremacy, see, e.g., Ref. [16].

Time-to-epsilon can be studied from two perspectives: as a measure of asymptotic scaling with problem size, or as a practical performance metric for finite-size problems. Here, we adopt both points of view. For the former, we use the asymptotic scaling of time-to-epsilon for four classes of large problems: Zephyr graphs with random couplings and fields [32], tile-planting instances defined on square and cubic lattices [33, 34], and Sidon28 instances defined on Quantum Annealing Correction log-ical graphs [17]. For the latter, we focus on instances that are directly relevant for current-generation quantum hardware: 3D Ising spin-glass instances embedded into the Pegasus graph of D-Wave's Advantage quantum annealer [29, 35], and higher-order binary optimization problems defined on IBM's heavy-hex topology with N = 156 qubits [36]. These results demonstrate that SBQA is both a practically useful optimization heuristic for finite-size problems, and, in the spirit of Ref. [44], a tool for sharpening the threshold for quantum advantage in the asymptotic regime of large problem sizes.

### A. Asymptotic scaling of time-to-epsilon

We begin with the analysis of scaling properties of time-to-epsilon as a function of problem size. The computational efficiency and parallelizability of algorithms based on dynamical systems, such as SBM and SBQA, allow us to study much larger problem sizes than typically considered, on the order of (exceeding) $N = 10^5$ variables, which is well beyond the capabilities of current-generation quantum devices. While it still requires fitting and extrapolation to make claims about asymptotic scaling, such large sizes significantly reduce sensitivity to finite-size effects and allow for more robust extraction of the scaling exponent.

Note that TTE is a problematic metric to study asymptotic scaling since it requires great care and significant computational resources to obtain reliable results, which is crucial when it is used to compare SBQA against SBM on similar problems and assess the quantum advantage. This is not our intent here, and we do not attempt to make any advantage claims, but rather to quantitatively compare SBQA against SBM on similar problems, to assess the quantum advantage.

#### 1. Large-scale Zephyr instances

One of the major challenges for quantum hardware is the structure of couplings between individual qubits (physical or logical), which in turn in turn significantly degrades performance and limits the size of instances that can be studied. It is thus highly unlikely that near-term quantum annealers will be able to demonstrate quantum advantage on problem classes that are not natively supported by their working graph. Because of that, the Zephyr and Advantage2 quantum annealers, namely the Zephyr and Advantage architectures, have become a popular choice for assessing the performance of Ising solvers.

In this section, we focus on the Zephyr graphs across four orders of magnitude in size, from $Z_1$ with $N \sim 10^1$ variables through $Z_{12}$ with $N \sim 10^4$ variables and up to $Z_{150}$ and $Z_{190}$, with $N \sim 10^5$ and $N \sim 2 \times 10^5$ variables respectively. For each of the graphs, we generate 20 instances in the small regime ($Z_0$–$Z_{50}$) and in the large regime ($Z_{50}$–$Z_{150}$) using Zephyr with random couplings $J_{ij}$ and fields $h_i$, obtained from a QUBO matrix $Q_{ij}$ with entries drawn from a uniform distribution over $[-1, 1]$ [see Ref. [32] for details]. The reference energies are obtained by running large scale Simulated Annealing (SA) calculations, operating on timescales typically at least an order of magnitude larger than those required by SBM and SBQA.

The results are shown in Figs. 2 and 3. Figure 2 shows that the advantage of SBQA over SBM emerges in the regime of large and sparse problems, precisely where SBM is known to struggle. The solution quality, measured by the optimality gap relative to the reference energy, is visibly improved already for instances with $N \sim 10^3$ variables and continues to improve with increasing size and decreasing density. At the same time, the running overhead of SBQA becomes negligibly small as the number of variables grows.

In the moderate-to-large regime ($Z_{20}$–$Z_{150}$), we then study the scaling of time-to-epsilon with problem size. Here too SBQA exhibits better scaling than SBM, as reflected in the dependence of the scaling exponent $\gamma$ on the target optimality gap $\epsilon$ shown in panel (c) of Fig. 3.

#### 2. Large-scale Quantum Annealing Correction (QAC) problems

It is likely that genuine quantum advantage on near-term quantum annealers, if possible, will require some form of error correction. A promising approach, called Quantum Annealing Correction (QAC), was put forth in Ref. [46], and recently used in an attempt to demonstrate quantum scaling advantage in Ref. [17]. While it is clear that the QAC approach significantly improves upon the performance of uncorrected quantum annealing, the question of whether it can achieve supremacy remains open. In particular, it was shown in Ref. [18] that SBM surpasses the scaling of QAC on instances native to the topology of the logical graphs. Here, we go beyond the sizes studied in Refs. [17, 18] and consider logical QAC graphs of sizes from $L = 20$ to $L = 80$, and random couplings drawn from the Sidon28 set defined on random instances. The number of variables for these logical graphs varies from $N = 2380$ to $N = 38320$ for $L = 80$. To run these instances on a real QPU, it would have to have approximately $N = 1.5 \times 10^5$ physical qubits, arranged in the topology of Pegasus $P_{16}$ graph.

The results are shown in Figs. 4 and 5. We find that for a small number of steps SBM outperforms SBQA, but after $N_s \sim 10^3$, the advantage of SBQA emerges and grows with increasing system size. This translates to a visible improvement in the strictest achievable target optimality gaps $\epsilon \approx 0.2\%$. We thus conclude that SBQA is capable of raising the bar further for quantum advantage with QAC, and it will certainly be interesting to see how it compares to the performance of future quantum annealers with QAC.

#### 3. 2D and 3D tile planting

In the context of TTs studies, it is desirable to have access to instances spanning a wide range of sizes and hardness, with known ground state energies, to avoid the pitfalls of extrapolating from small sizes and relying on suboptimal reference energies. We thus turn our attention to the so-called planted solution instances, which are created in a way that guarantees that the ground state energy is known, regardless of the problem size.

More precisely, we consider tile-planting instances defined on square (2D) [33] and cubic (3D) [34] lattices. They are constructed by tiling the lattice sites randomly chosen plaquettes drawn from a predefined set of types with varying degrees of frustration, which allows the hardness of the problem to be tuned through the tile composition. This feature makes them a particularly useful benchmarking ground for heuristic optimization algorithms. In fact, it has already been shown that SBM tends to underperform on these instances [32], in particular in comparison to other approaches based on non-linear dynamical systems [27].

In the 2D case, we consider instances of $C_2$–$C_4$ type, with probability of each being po $= 0.6$ [34, 44]. For the 3D case, we use the gallery66 tile set, with parameter $p_0 = 0.6$ [34, 44]. Both are shown in Figs. 6-7, and for 3D tile planting in Figs. 8-9.

In the 3D case, replica coupling in SBQA leads to a significant improvement over SBM, which is especially pronounced for larger instance sizes. Since these instances are on the extremely sparse end of the density spectrum, this constitutes strong evidence for our claim that SBQA remedies one of the known weaknesses of SBM, namely poor performance on very sparse problems. While this gain diminishes for denser problems, it can still be observed for a sufficiently large number of variables, and is not accompanied by any significant runtime overhead.

### B. Instances on current-generation quantum hardware

While the asymptotic scaling of time-to-epsilon is an important theoretical benchmark, and when done properly, can serve as a measure of genuine quantum advantage in the asymptotic regime of large problem sizes, it is not always the case that an algorithm with better asymptotic scaling will be better for finite-size problems of practical relevance. In particular, near-term quantum devices operate in a regime where problem-size connectivity constraints, and hardware-specific overheads play an important role in practical performance. Therefore, it is desirable to complement asymptotic analyses with benchmarks on instances that are directly compatible with the architectures of current-generation quantum hardware.

In this section, we shift our focus to such practically relevant regimes, considering problem classes that can be natively solved on existing quantum platforms. This includes 3D Ising spin-glass instances defined on the Pegasus topology of the D-Wave quantum annealer [29, 35], as well as higher-order binary optimization problems derived from the heavy-hex topology of IBM quantum processors.

These benchmarks allow us to assess SBQA not only as an algorithm with favorable asymptotic scaling, but also as a competitive heuristic under realistic conditions.

#### 1. 3D spin glasses on D-Wave quantum annealer

We start with benchmarks on 3D spin glasses, with couplings distributed according to the standard normal distribution. This is a modification of the instances already studied in the context of combinatorial optimization and quantum annealing, for one obtained previously in Ref. [29, 35]. The logical topology of the instance is a cubic lattice with periodic boundaries in two directions and an open boundary in the third direction. We consider cubic lattices of size $L$ for $L = 6, 8, 10, 12$ and $L = 12$ for $L = 15$. For each data point, we consider 50 random instances (10 for D-Wave) and 5 independent runs (10 for D-Wave) per instance to estimate the success probability and average runtime (QPU access time for the annealer).

Despite previous results showing strong performance of quantum annealing on this topology, changing the coupling distribution severely degrades its performance.

The results of the time-to-epsilon benchmarks are shown in Fig. 10. Here, both SBQA and SBM yield solutions of very similar quality (especially for larger instances). The SBM retains a slight edge in time-to-epsilon due to the lower computational cost per step. Similarly to the embedded instances, DTSQA falls behind due to its longer runtimes, except for the largest instances and strictest optimization targets.

a result, TTS values remains finite only for the largest optimality gap considered here, $\epsilon = 0.05$. By contrast, SBQA outperforms SBM for all optimization targets except the easiest one, where the two algorithms perform identically. This reflects the fact that replica interaction improves solution quality at a fixed number of steps while introducing very little runtime overhead.

SBQA also outperforms DTSQA in most cases. The main exception is the regime of the largest instances and the strictest optimality targets, where only DTSQA is able to consistently reach the target and avoid penalty associated with very small success probabilities.

It does so, however, at the cost of significantly longer runtimes. Additional plots decomposing time-to-epsilon into solution-quality and runtime components are provided in Sec. S2 of Ref. [38].

The results for the logical instances are shown in Fig. 11. Here, both SBQA and SBM yield solutions of very similar quality (especially for larger instances), so the SBM retains a slight edge in time-to-epsilon due to the lower computational cost per step. Similarly to the embedded instances, DTSQA falls behind due to its longer runtimes, except for the largest instances and strictest optimization targets.

#### 2. Higher-order binary optimization on heavy-hex topology

For our final set of benchmarks, we consider a different class of problems, namely higher-order binary optimization (HUBO) problems constructed from the heavy-hexagon topology of IBM quantum processors [48]. These problems rarely emerge in the literature, but have recently been used in claims of runtime quantum advantage for gate-based quantum computing [36], claims that have been subsequently challenged by highly optimized classical heuristics [16]. The Hamiltonian of the problem in the Ising spin variables reads:

$$H = \sum_{(m,n) \in G_2} J_{mn} s_m s_n + \sum_{(l,m,n) \in G_3} K_{lmn} s_l s_m s_n, \tag{11}$$

where $G_2$ and $G_3$ are the sets of 2-body and 3-body interactions. The starting point of the construction is a heavy-hexagon graph of size N = 156, corresponding to the topology of IBM Quantum One Falcon, from which sets of independent 2-body and 3-body interactions (which can be executed sequentially on a real QPU) are constructed via graph coloring. A fixed number of such $S_{2a}$ and $S_{3a}$ are then included into $G_2$ and $G_3$ respectively. Finally, using one of the two-body sets, a SWAP operation is carried out between connected pairs of qubits, which modifies the underlying graph. This procedure can be repeated $N_{\text{swap}}$ times, increasing the number of interactions with each iteration. With precomputed topology, an ensemble of random HUBO instances is generated by drawing the coupling strengths $J_{mn}$ and $K_{lmn}$ from suitable distributions. See the Appendix in Ref. [16] for technical details on the construction of these HUBO instances, and repository [49] for the implementation used in this work. To obtain the reference energies, we used CPLEX optimizer running on native HUBO instances, as well as a variant of higher-order formulation of SBM [26].

The results of the time-to-epsilon benchmarks are shown in Fig. 12, where rows of panels correspond to different coupling distributions, and columns correspond to different optimality targets, with the first column containing "easy" targets and the second column to "hard" targets (dependent on the coupling distribution). For each data point, 20 random instances and 10 independent runs per instance were used to estimate the [TTs]max values, which were minimized over the number of steps of the algorithm. DTSQA performs poorly, struggling to leverage the gray structure for such complex topologies.

On the other hand, SBQA continues to perform well, matching SBM on the "easy" targets and significantly outperforming SBM for the larger instances ($N_{\text{swap}} = 9$) and the largest instances with Pareto couplings [panel (f)].

Overall, these results show that adding inter-replica coupling in SBQA does not compromise versatility, and allows the method to remain effective across a wide range of problem types and topologies.

## IV. SUMMARY AND OUTLOOK

In this work, we introduced **Simulated Bifurcation Quantum Annealing (SBQA)** and demonstrated that incorporating controlled inter-replica interactions into the simulated bifurcation framework leads to measurable and consistent performance improvements in problem classes where standard SBM is known to struggle, particularly on sparse and rugged energy landscapes. At the same time, this preservation of computational efficiency and parallelism.

Using a rigorous time-to-epsilon benchmarking methodology with real runtime measurements, we showed that SBQA achieves a favorable balance between solution quality and runtime across a diverse set of benchmarks, including large and sparse problems, where we compare SBM and SBQA in terms of asymptotic time-to-epsilon scaling. We study Zephyr graphs, which underlie the latest-generation Advantage2 quantum annealers, instances defined on the logical graphs of the Quantum Annealing Correction (QAC) error-correction scheme, recently used in an attempt to demonstrate quantum scaling advantage, and higher-order binary optimization problems defined on the logical graphs of the Quantum Annealing Correction (QAC) error-correction scheme, recently used in an attempt to demonstrate quantum scaling advantage. We demonstrated that SBQA systematically improves on SBM in the sparse and rugged regimes that motivate the method, while remaining broadly effective and versatile across a diverse set of tested problem families. These results position SBQA as a practical quantum-inspired optimization heuristic and a stronger classical baseline for the sparse and rugged regimes studied here.

Beyond its immediate performance gains, SBQA illustrates a broader algorithmic principle: modest, carefully engineered modifications inspired by quantum dynamics can yield practically significant gains in classical heuristics. In regimes where quantum–classical performance comparisons hinge on narrow margins, such improvements can materially strengthen the classical baseline used for evaluation.

Several directions for future work remain open. On the algorithmic side, further exploration of adaptive or problem-structure-aware replica coupling schedules may yield additional performance gains, as may extensions of SBQA to alternative cost-function couplings or constrained optimization settings. From a benchmarking perspective, applying SBQA to larger-scale industrial instances and real-world optimization workloads would help clarify its practical impact. Finally, SBQA provides a useful and physically motivated classical baseline for future studies comparing quantum optimization devices with classical heuristics on sparse and rugged benchmark families studied here.

## ACKNOWLEDGMENTS

This project was supported by the National Science Foundation (NSF), Poland, under Projects: Sonata Bis 10, No. 2020/38/E/ST3/00269 (B.G.) and Sonata Bis 15, No. 2025/58/E/ST6/00422 (L.P.). Quantumz.io Sp. z o.o. acknowledges support received from The National Centre for Research and Development (NCBR), Poland, under Project No. POIR.01.01.01-00-0061/22.

## References

[1] J. M. Weinand, K. Sorensen, P. San Segundo, M. Kleinebrahm, and R. Mccann, Research trends in combinatorial optimization, Ind. Trans. Oper. Res. 29, 667 (2022).

[2] M. S. Martins, J. M. Sousa, and S. Vieira, A systematic review on reinforcement learning for industrial combinatorial optimization problems, Applied Sciences 15, 1211 (2025).

[3] M. A. Rahman, R. Sokalingam, M. Othman, K. Biswas, L. Mohammadi, and M. Abdullah Elyafi, Benchmarking and recent advances, Mathematics 9, 2633 (2021).

[4] N. N. Maheen, P. L. McMahon, and T. Byrnes, Ising machines as hardware solvers of combinatorial problems, Nat. Rev. Phys. 4, 363 (2022).

[5] A. Lucas, Ising formulations of many ip problems, Front. Phys. 2, 5 (2014).

[6] S. Yarkoni, E. Raponi, T. Back, and S. Schmitt, Quantum annealing for industry applications: introduction and review, Prog. Phys. 75, 104001 (2022).

[7] P. L. Potts and K. S. Simonsen, Implementation of quantum annealing, IEEE Trans. 75, 104001 (2022).

[8] S. Abbas, A. Ambainis, B. Augustino, A. Bartschi, and H. Buhiraman, et al., Challenges and opportunities in quantum optimization, Nature Reviews Physics 6, 718 (2024).

[9] A. Peloske, Comparing three generations of d-wave quantum annealing devices for combinatorial optimization problems, Quantum Sci. Technol. 10, 025025 (2025).

[10] A. Gomez-Tejedor, E. Osaba, and E. Villar-Rodriguez, Addressing the noise-shielding problem in quantum annealing and evaluating state-of-the-art algorithm performance (2025), arXiv:2509.14376 (quant-ph).

[11] A. D. King, S. Suzuki, B. J. Raymond, A. Zucca, T. Lanting, F. Altomare, A. J. Berkley, S. Ejtemaee, E. Hoskinson, S. Huang, et al., Coherent quantum annealing in a programmable 2-qubit spin-glass, Nat. Phys. 18, 1324 (2022).

[12] E. Peloske, G. Hahn, and H. N. Djidjev, Noise dynamics of quantum annealers: estimating the effective noise using idle qubits, Quantum Sci. Technol. 8, 035025 (2023).

[13] A. D. King, A. Nocera, M. M. Rams, J. Deiamagna, R. Wiersema, N. Bernando, N. Raymond, N. Heimsdorf, R. Harris, K. Boothby, F. Altomare, M. Abudinén, A. J. Berkley, S. Ejtemaee, C. Rich, Y. Sato, P. Tsai, M. Volkmann, J. D. Whittaker, J. Yao, A. W. Sandvik, and M. Amin, Observation of topological phenomena in a programmable lattice of 1,800 qubits, Science 373, 576 (2021).

[14] A. Tindall, A. Mello, M. Fishman, M. Stoudenmire, and D. Sels, Dynamics of disordered quantum systems with two- and three-dimensional tensor networks (2025), arXiv:2503.08247 (quant-ph).

[15] L. Mauron and G. Carlo, Challenging the quantum advantage in combinatorial optimization, arXiv (2025), arXiv:2503.08247 (quant-ph).

[16] J. Tuziemski, J. Pawłowski, P. Tarasiuk, L. Pawela, and B. Gardas, Recent quantum runtime (dis)advantages (2025), arXiv:2510.0637 (quant-ph).

[17] H. Munoz-Bauza and D. Lidar, Scaling advantage in approximate optimization with quantum annealing, Phys. Rev. Lett. 134, 100601 (2025).

[18] J. Pawłowski, P. Tarasiuk, J. Tuziemski, L. Pawela, and B. Gardas, Closing the quantum-classical scaling gap in approximate optimization (2025), arXiv:2505.22514 [quant-ph].

[19] M. J. Schultz, J. K. Brubaker, and H. G. Katzgraber, Combinatorial optimization with physics-inspired graph neural networks, Nat. Mach. Intell. 4, 367 (2022).

[20] M. Henari-Latapour, M. S. Mills, and M. -A. Miri, Combinatorial optimization with photonics-inspired clock models, Commun. Phys. 5, 104 (2022).

[21] T. Zhang, Q. Luo, B. Liu, and J. Liu, A review of simulated algorithms for classical ising machines for combinatorial optimization, in 2022 IEEE International Symposium on Circuits and Systems (ISCAS) (IEEE, 2022) pp. 1877–1881.

[22] Q. -G. Zeng, X. -P. Cui, B. Liu, Y. Wang, and P. Mosharev, et al., Performance of quantum annealing-inspired algorithms for combinatorial optimization problems, Communications Physics 7, 249 (2024).

[23] H. Goto, Bifurcation-based adiabatic quantum computation with a nonlinear oscillator network, Sci. Rep. 6, 21686 (2016).

[24] H. Goto, K. Tatsumura, and A. R. Dixon, Combinatorial optimization by simulating adiabatic bifurcations in nonlinear hamiltonian systems, Sci. Adv. 5, eaav2372 (2019).

[25] K. Goto, K. Endo, M. Suzuki, Y. Sakai, and Taro et al., High-performance combinatorial optimization based on classical mechanics, Adv. 7, eabi7535 (2021).

[26] I. Kanao and H. Goto, Simulated bifurcation for higher-order functions, Applied Physics Express 16, 014501 (2022).

[27] J. Hou, A. Barzegar, and H. G. Katzgraber, Direct comparison of stochastic driven nonlinear dynamical systems for combinatorial optimization, Phys. Rev. E 112 (2025).

[28] Quantumz.io, VelocQ QUBO solver (2025), accessed: 2025-01-31.

[29] N. Chowdhury, N. A. Adit, A. Grimaldi, E. Raimond, A. Rani, P. A. Lott, J. H. Marketnik, M. M. Rams, F. Ricci-Tersenghi, M. Chiappin, L. S. Theegarajan, L. Simonelli, C. Froschi, M. Moselli, and K. V. Camisari, Pushing the boundary of quantum advantage in hard combinatorial optimization, Nature Communications 16 (2025).

[30] K. Y. Camberi, S. Chowdhury, and S. Datta, Scalable emulation of sign-problem-free hamiltonians with room-temperature rydberg atoms, Phys. Rev. Appl. 12 (2019).

[31] M. Suzuki, Relationship between d-dimensional quantum systems and (d+1)-dimensional ising systems: Equivalence, critical exponents and systematic approximants of the partition function and spin correlations, Prog. Theor. Phys. 56, 1454 (1976).

[32] J. Pawłowski, J. Tuziemski, P. Tarasiuk, L. Pawela, and B. Gardas, A first step toward the QUBO solver (2025), arXiv:2503.19221 [quant-ph].

[33] D. Perera, F. Hamze, D. Raymond, M. Weigel, and H. G. Katzgraber, Computational hardness of spin-glass problems with tile-planted ground states, Phys. Rev. E 101, 023316 (2020).

[34] F. Hamze, D. C. Jacob, A. J. Ochoa, D. Perera, W. Wade, and H. G. Katzgraber, From near to eternal: computational hardness of spin-glass problems with tile-planted ground states, Phys. Rev. E 101, 023316 (2020).

[35] A. D. King, J. Raymond, T. Lanting, R. Harris, A. Zucca, F. Altomare, E. Altomare, C. Enderud, E. Hoskjnson, S. Huang, and S. Ejtemaee, et al., Quantum critical dynamics in a 5,000-qubit programmable spin glass, Nature 617, 61–66 (2023).

[36] P. Chandarana, A. G. Cadavid, S. V. Romero, A. Simen, E. Solano, and N. N. Hegade, Runtime quantum advantage with digital quantum optimization (2025), arXiv:2505.08603 [quant-ph].

[37] J. Pawłowski, P. Tarasiuk, Tuziemski, L. Pawela, and B. Gardas, Simulated bifurcation quantum annealing - data repository, https://github.com/quantumz-io/SBQA_benchmarks (2026), GitHub repository.

[38] See Supplemental Material for a derivation of the Simulated Quantum Annealing Hamiltonian, as well as fine-grained analysis of the benchmarks on hardware-compatible instances.

[39] T. Zhang and J. Han, Quantized simulated bifurcation for the ising model, in 2023 IEEE 23rd International Conference on Nanotechnology (NANO) (2023) pp. 715–720.

[40] F. Hamze, J. Raymond, C. A. Pattison, K. Biswas, and H. G. Katzgraber, The Wishart planted ensemble: A Tuneably-Rugged pairwise ising model with a first-order phase transition, Physical Review E 101, 052102 (2020).

[41] B. Taseff, T. Albash, Z. Morrell, M. Vulfray, A. Y. Lokhov, S. Misra, and D. Coffrin, On the emerging potential of quantum annealing hardware for combinatorial optimization, J. Heuristics 30, 325 (2024).

[42] S. Schulz, D. Willsch, and K. Michielsen, Learning-driven annealing with adaptive hamiltonian modification for solving large-scale problems on quantum devices, Quantum 9, 1898 (2025).

[43] T. F. Resnnov, Z. Wang, J. Job, S. Boixo, S. V. Isakov, D. Wecker, J. M. Martinis, D. A. Lidar, and T. Troyer, Defining and detecting quantum speedup, Science 345, 420–424 (2014).

[44] A. A. Gangat, Linear-time classical approximate optimization of cubic-lattice classical spin glasses, Physical Review Applied 25 (2026).

[45] D-Wave, Minor embedding, accessed: 2025-01-30.

[46] K. L. Pudenz, T. Albash, and D. A. Lidar, Error-corrected quantum annealing with hundreds of qubits, Nat. Commun. 5, 3243 (2014).

[47] K. Boothby, P. Bunyk, J. Raymond, and A. Roy, Next-generation topology of d-wave quantum processors, arXiv:2003.00133 [quant-ph].

[48] IBM Quantum, The heavy-hex lattice: A new quantum processor topology (2021), accessed: 2026-01-17.

[49] J. Tuziemski, J. Pawłowski, P. Tarasiuk, L. Pawela, and B. Gardas, Recent quantum runtime (dis)advantages - code repository, https://github.com/quantumz-io/quantum-runtime-disadvantage (2025), GitHub repository.

[50] S. V. Romero, A. -M. Visuri, A. G. Cadavid, A. Simen, E. Solano, and N. N. Hegade, Bias-field digitized counterdiabatic quantum algorithm for higher-order binary optimization (2025), arXiv:2506.02486 [quant-ph].

---

# Supplemental Material: Simulated Bifurcation Quantum Annealing

In the Supplemental Material we present a concise derivation of the Simulated Quantum Annealing Hamiltonian, as well as fine-grained analysis of the benchmarks on hardware-compatible instances, including 3D spin glasses on the Pegasus topology and HUBO instances derived from the heavy-hex topology of IBM quantum processors.

## S1. DERIVATION OF THE INTER-REPLICA COUPLING IN SIMULATED QUANTUM ANNEALING

Simulated Quantum Annealing requires mapping a d-dimensional quantum system onto a (d + 1)-dimensional classical system [31]. We consider the quantum Hamiltonian:

$$H_Q = -\sum_{i<j} J_{ij} \sigma_i^z \sigma_j^z - \Gamma_x \sum_i \sigma_i^x \tag{S1}$$

with partition function $Z_Q = \text{Tr}[e^{-\beta H_Q}]$. Due to non-commutativity between $H_x = -\sum_{i,j} J_{ij} \sigma_i^z \sigma_j^z$ and $H_x = -\Gamma_x \sum_i \sigma_i^x$, we employ the Suzuki-Trotter decomposition to construct the equivalent classical representation:

$$e^{-\beta(H_x + H_x)} = \lim_{R \to \infty} \left[ e^{-\frac{\beta}{R} H_x} e^{-\frac{\beta}{R} H_x} \right]^R, \tag{S2}$$

where $R$ represents the number of imaginary-time replicas. This decomposition introduces $R$ copies of the system along an extra dimension. Inserting complete sets of $\sigma^z$-basis states $|\{\sigma^k\}\rangle$ with periodic boundary conditions $\sigma^{k+1} = \sigma^1$, we obtain:

$$Z_Q = \lim_{R \to \infty} \text{Tr} \left( \prod_{k=1}^{R} e^{-\frac{\beta}{R} H_x} e^{-\frac{\beta}{R} H_x} \right) = \lim_{R \to \infty} \sum_{\{\sigma^k\}} \prod_{k=1}^{R} \langle \sigma^k | e^{-\frac{\beta}{R} H_x} e^{-\frac{\beta}{R} H_x} |\sigma^{k+1}\rangle. \tag{S3}$$

Since $H_x$ is diagonal in the $\sigma^z$-basis:

$$\langle \sigma^k | e^{-\frac{\beta}{R} H_x} |\sigma^{k+1}\rangle = \exp \left( \frac{\beta}{R} \sum_{i<j} J_{ij} \sigma_i^k \sigma_j^k \right) \delta_{\sigma^k, \sigma^{k+1}}, \tag{S4}$$

whereas the non-diagonal term factors by site:

$$\langle \sigma^k | e^{-\frac{\beta}{R} H_x} |\sigma^{k+1}\rangle = \prod_i \langle \sigma_i^k | \exp \left( \frac{\beta \Gamma_x}{R} \sigma_i^x \right) |\sigma_i^{k+1}\rangle. \tag{S5}$$

The single-site matrix element evaluates to:

$$\langle \sigma_i^k | e^{\beta \Gamma_x \sigma_i^x} |\sigma_i^{k+1}\rangle = \cosh(\theta) \delta_{\sigma_i^k, \sigma_i^{k+1}} + \sinh(\theta) \delta_{\sigma_i^k, -\sigma_i^{k+1}}, \tag{S6}$$
$$= \exp(a + b\sigma_i^k \sigma_i^{k+1}),$$

where $\theta = \beta \Gamma_x / R$, and parameters $a$ and $b$ are defined as:

$$\begin{cases}
\exp(a + b) = \cosh(\theta) \\
\exp(a - b) = \sinh(\theta)
\end{cases} \tag{S7}$$

which can be solved to yield:

$$a = \frac{1}{2} \ln(\cosh(\theta) \sinh(\theta)) = \frac{1}{2} \ln \left( \frac{1}{2} \sinh(2\theta) \right), \tag{S8}$$

$$b = \frac{1}{2} \ln \left( \frac{\cosh(\theta)}{\sinh(\theta)} \right) = \frac{1}{2} \ln(\coth(\theta)). \tag{S9}$$

The spin-independent prefactor can be neglected if we are only interested in the emergent classical Hamiltonian. Combining both terms yields:

$$Z_Q = \lim_{R \to \infty} \sum_{\{\sigma^k\}} \exp \left[ \frac{\beta}{R} \sum_{k=1}^{R} \sum_{i<j} J_{ij} \sigma_i^k \sigma_j^k + \frac{1}{2} \ln \coth \left( \frac{\beta \Gamma_x}{R} \right) \sum_{k=1}^{R} \sum_i \sigma_i^k \sigma_i^{k+1} \right], \tag{S10}$$

Identifying the exponent as $-\beta H_C$ gives:

$$H_C = -\frac{1}{R} \sum_{k=1}^{R} \sum_{i<j} J_{ij} \sigma_i^k \sigma_j^k - \frac{K}{R} \sum_{k=1}^{R} \sum_i \sigma_i^k \sigma_i^{k+1}, \tag{S11}$$

with inter-replica coupling:

$$J_\perp = \frac{K}{\beta} = \frac{1}{2\beta} \ln \coth \left( \frac{\beta \Gamma_x}{R} \right) = -\frac{1}{2\beta} \ln \tanh \left( \frac{\beta \Gamma_x}{R} \right), \tag{S12}$$

This is the exact SQA-derived coupling for a given transverse field $\Gamma_x$. In the time-dependent SBQA implementation discussed in the main text, we use the regularized schedule $\Gamma_x(t) = \Gamma_x(0) \left[ (1 - t/T)^\alpha + 10^{-5} \right]$ to keep the endpoint finite.

## S2. ADDITIONAL RESULTS FOR 3D SPIN GLASS BENCHMARK

[Detailed figures showing optimization gaps and runtime measurements for various 3D spin glass instances with different lattice dimensions and problem parameters]

## S3. ADDITIONAL DETAILS ON HUBO BENCHMARK

**Table S1.** Optimal penalties by coupling distribution, $N_{\text{swap}}$, and solver

| Distribution | $N_{\text{swap}}$ | Penalty (SBM) | Penalty (SBQA) | Penalty (SA) | Penalty (DTSQA) |
|---|---|---|---|---|---|
| Cauchy | 1 | 20.0 | 20.0 | 10.0 | 30.0 |
| Cauchy | 3 | 30.0 | 40.0 | 20.0 | 30.0 |
| Cauchy | 6 | 40.0 | 75.0 | 30.0 | 30.0 |
| Cauchy | 9 | 40.0 | 75.0 | 40.0 | 30.0 |
| Normal | 1 | 4.0 | 6.0 | 4.0 | 10.0 |
| Normal | 3 | 6.0 | 8.0 | 6.0 | 8.0 |
| Normal | 6 | 8.0 | 8.0 | 6.0 | 6.0 |
| Normal | 9 | 6.0 | 8.0 | 6.0 | 6.0 |
| Sym. Pareto | 1 | 10.0 | 10.0 | 8.0 | 10.0 |
| Sym. Pareto | 3 | 10.0 | 20.0 | 10.0 | 10.0 |
| Sym. Pareto | 6 | 20.0 | 30.0 | 10.0 | 8.0 |
| Sym. Pareto | 9 | 20.0 | 20.0 | 20.0 | 10.0 |

The HUBO reduction procedure has one free parameter, the penalty coefficient, which controls the strength of the penalty terms introduced to enforce consistency between original and auxiliary variables. Its value must be large enough for the correct reproduction of the low-energy spectrum of the original HUBO problem. However, different solvers may benefit from different penalty values, due to their distinct ways of exploring the solution space. Thus, for each coupling distribution and value of $N_{\text{swap}}$, we perform a line search over penalty values for each solver, and select the value which, on average, yields the best solution quality. This procedure ensures a fair comparison between different solvers used in our benchmarks.

Finally, similar to previous appendices, in Figs. S3 and S4 we separately analyze the two components of the time-to-epsilon benchmark for HUBO instances, namely the solution quality and algorithm runtime. These plots clearly show how DTSQA fails to reach solutions of similar quality as other methods, which ultimately results in infinite time-to-epsilon values for stricter optimization targets. On the other hand, SBQA is able to consistently improve upon SBM's performance for a fixed number of steps, while maintaining only a marginal increase in runtime. This further supports the conclusions drawn in the main text, regarding the versatility of SBQA across a wide range of problem types and topologies.
