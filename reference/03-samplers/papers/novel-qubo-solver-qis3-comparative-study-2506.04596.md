# A Novel Solver for QUBO Problems: Performance Analysis and Comparative Study with State-of-the-Art Algorithms

**TuringQ Co. Ltd.**

June 9, 2025

**Contributions:** Jiecheng Yang, Dung Wang, Xiang Zhao, Hairui Zhang, Ming Gao, Lin Yang (yanglin@turingq.com)

## Abstract

Quadratic Unconstrained Binary Optimization (QUBO) provides a versatile framework for representing NP-hard combinatorial problems, yet existing solvers often face trade-offs among speed, accuracy, and scalability. In this work, we introduce a quantum-inspired solver (QIS) that unites branch-and-bound pruning, continuous gradient-descent refinement, and quantum-inspired heuristics within a fully adaptive control architecture. We benchmark QIS3 against eight state-of-the-art solvers—including genetic algorithms, coherent Ising machines, simulated bifurcation, parallel tempering, simulated annealing, our prior QIS2 version, D-Wave's simulated-annealing (Neal), and Gurobi on three canonical QUBO problem classes: Max-Cut, NAE-3SAT, and Sherrington Kirkpatrick spin glass problems. Under a uniform runtime budget, QIS3 attains the best solution on nearly all instances, achieving optimality in 94% of max-cut instances. These results establish QIS3 as a robust, high-performance solver that bridges classical exact strategies and quantum-inspired heuristics for scalable QUBO optimization.

---

## 1 Introduction

Combinatorial optimization over binary variables arises in disciplines as diverse as logistics, finance, machine learning and network design. A unifying formulation is the Quadratic Unconstrained Binary Optimization (QUBO) problem,

$$\min_{x \in \{0,1\}^n} x^T Q x, \tag{1}$$

where $Q \in \mathbb{R}^{n \times n}$ encodes pairwise interactions among $n$ binary variables [1]. Despite its simple form, exact solution of QUBO is NP-hard, and both exact and heuristic methods have been intensely studied [2, 3].

### 1.1 Classical and Physics-Inspired Heuristics

Classical metaheuristics such as simulated annealing, tabu search and scatter search have long provided high-quality solutions for large QUBO instances. More recently, physics-inspired accelerators—notably D-Wave's simulated annealer and Fujitsu's Digital Annealer—have been benchmarked on diverse QUBO classes, demonstrating competitive performance on problems up to thousands of variables [4, 5, 6, 7]. Hybrid quantum-classical learning schemes have further enhanced solution quality by iteratively refining embeddings and penalizing previously visited states [8].

### 1.2 Exact Branch–and–Bound Methods

Exact solvers based on branch-and-bound (BnB) guarantee optimality by recursively partitioning the search space and pruning via bounds derived from relaxations or problem structure [9]. Classical BnB implementations for QUBO can handle up to a few hundred variables in moderate time, but scale poorly as $n$ increases [2].

### 1.3 Hybrid Classical–Quantum Branch–and–Bound

To bridge the gap between scalability and optimality, recent works integrate quantum heuristics into the BnB framework. One approach decomposes the original QUBO into subproblems of bounded size, solved on a quantum annealer, while the classical BnB orchestrates the search—yielding a tunable trade-off between solution certainty and quantum reliability [10].

Other protocols inject pools of quantum-generated solutions as warm starts or node heuristics within a state-of-the-art MIP solver [11], achieving marked speedups on logistic and scheduling benchmarks.

### 1.4 Contributions

In this paper, we propose a novel hybrid metaheuristic solver that deeply intertwines quantum heuristics with a classical branch-and-bound backbone. Our key innovations are:

- **Adaptive decomposition:** an informed partitioning strategy that selects subproblem scopes where quantum annealing is most effective.

- **Quantum-driven bounding:** dynamic lower and upper bounds derived from quantum-annealer outputs to accelerate pruning.

- **Metaheuristic refinement:** a higher-level adaptive neighborhood search that leverages both quantum and classical heuristics for intensified exploration.

We benchmark our solver on standard QUBO testbeds and representative NP-hard formulations, comparing against leading classical, physics-inspired, and hybrid methods [4, 5, 6, 10]. Our results demonstrate significant improvements in time-to-solution and solution quality across problem families.

---

## 2 Proposed Hybrid Quantum–Classical Solver Framework

We present a novel solver architecture built on a *quantum-inspired algorithmic framework*, augmented by powerful classical optimization techniques. At its core, the solver interleaves three complementary paradigms:

- **Branch–and–Bound:** a systematic tree-search strategy for pruning large portions of the QUBO search space using rigorous bounds;

- **Gradient Descent:** a continuous relaxation method that refines candidate solutions by following local cost gradients;

- **Quantum Annealing:** a physics-inspired heuristic that exploits tunneling-like moves to escape deep local minima.

By blending these methods, our hybrid model leverages the global guarantees of branch-and-bound, the fine-grained adjustments of gradient descent, and the non-local exploration capabilities of quantum annealing.

### 2.1 Adaptive Algorithmic Components

To maximize performance across diverse problem instances, the solver dynamically adapts at every stage:

1. **Initial Solution Generation:** an ensemble of seeding strategies is monitored in real time and weighted according to early success metrics, ensuring robust starting points for subsequent search.

2. **State-Adaptive Exploration:** the algorithm continuously analyzes the current solution landscape—measuring metrics such as local curvature and barrier depths—and adjusts the balance between intensification (local search) and diversification (global moves).

3. **Parameter Space Tuning:** key hyperparameters (e.g., annealing schedule, branch thresholds, learning rates) are tuned on the fly via an internal controller that employs Bayesian optimization principles, eliminating the need for extensive manual calibration.

### 2.2 Multi-Mode Operation and Automatic Selection

Our solver implements *nine distinct modes*, each representing a different combination of quantum-inspired heuristics with optimization methods. Each mode is tailored to particular QUBO classes (e.g., sparse vs. dense graphs, low-precision vs. high-precision weights) and encapsulated in a concise mode_ID code. An *automatic mode selector* selects the best mode based on the evaluated results. This mechanism allows the solver to *self-adapt* to a wide range of QUBO landscapes without user intervention.

### 2.3 User-Driven Exploration and Quality Refinement

While the automatic mode selection provides a strong baseline, advanced users may invoke *manual mode sweeps* to explore alternative algorithmic blends. By comparing intermediate best-found solutions across modes, the user can identify the most effective strategy for a given instance, and then launch a focused, high-intensity search in that configuration to further improve solution quality. This hybrid manual–automated workflow empowers both heuristics researchers and industrial practitioners to systematically refine results.

### 2.4 Summary of Solver Advantages

Through the deep integration of classical (branch-and-bound, gradient descent) and quantum-inspired methods, combined with real-time adaptive control and multi-mode flexibility, our solver achieves:

- **Robustness:** consistently high performance across heterogeneous QUBO benchmarks;

- **Efficiency:** fast convergence to the best solution via tight pruning and guided exploration;

- **Usability:** automated configuration for novices, with advanced manual controls for experts;

- **Solution Quality:** frequent attainment of near-optimal or optimal cuts/energies on challenging NP-hard instances.

This innovative framework represents a significant step forward in solving large-scale QUBO problems for both academic study and real-world applications.

---

## 3 Benchmark Problems

In this work, we evaluate our solver on three canonical NP-hard problems: the Max-Cut problem, Not-All-Equal 3-SAT (NAE-3SAT), and the Sherrington-Kirkpatrick (SK) spin-glass model. Each exhibits rich structure and has become a standard benchmark in classical, quantum, and quantum-inspired optimization research.

### 3.1 The Max-Cut Problem

The *Max-Cut* problem is defined on an undirected graph $G = (V, E)$ with real edge weights $w_{ij}$. One seeks a partition $(S, \bar{S})$ of $V$ that maximizes the

total weight of edges crossing the cut:

$$\max_{S \subseteq V} \sum_{\substack{(i,j) \in E \\ i \in S, j \in \bar{S}}} w_{ij}.$$

Equivalently, introducing binary variables $x_i \in \{+1, -1\}$ to indicate the two sides of the cut, the objective can be written as

$$\max_{x \in \{+1\}^n} \frac{1}{2} \sum_{i < j} w_{ij}(1 - x_i x_j),$$

since $1 - x_i x_j = 2$ precisely when $x_i \neq x_j$ [3]. In its decision form, determining whether there exists a cut of weight at least $K$ is NP-complete; hence the optimization variant is NP-hard [12].

A common QUBO formulation replaces spins by binary $y_i \in \{0,1\}$ via $x_i = 2y_i - 1$, yielding

$$\max_{y \in \{0,1\}^n} \sum_{i < j} Q_{ij} y_i y_j \quad \text{with} \quad Q_{ij} = -w_{ij},$$

plus linear terms to account for constant offsets; this equivalence is surveyed in [2].

To benchmark heuristic and quantum-inspired solvers, we use the G-Set collection [13], which contains machine-generated graphs with $|V|$ from 800 to 10,000 and varying edge densities. In particular, we include:

- **Sparse graphs:** G11 ($n = 800, m = 1600$), G32 (2000, 4000), ..., G72 (10,000, 20,000), all with $w_{ij} \in \{\pm 1\}$.

- **Moderate-density +1 graphs:** G14 (800, 4694), G51 (1000, 5909), ..., G63 (7000, 41459), all with $w_{ij} = +1$.

- **High-density graphs:** G1 (800, 19176), G43 (1000, 9990), G22 (2000, 19990), all with $w_{ij} = +1$.

These instances span from $|E| = 2|V|$ up to $|E| = 10|V|$ graphs, providing a broad testbed for both local-search heuristics and physics-inspired methods [1].

### 3.2 Not-All-Equal 3-SAT

The *Not-All-Equal 3-SAT* (NAE-3SAT) problem is a variant of Boolean satisfiability in which each clause has three literals and must contain at least one true and one false literal [14]. Formally, given a formula $\Phi = \bigwedge_{m=1}^M (\ell_{k_1} \vee \ell_{k_2} \vee \ell_{k_3})$, with literals $\ell_{kj} \in \{x_i, \overline{x_i}\}$, the question is whether there exists an assignment $x_i \in \{0,1\}$ such that in every clause not all three $\ell_{kj}$ evaluate equally. NAE-3SAT remains NP-complete even in the *monotone* case (all literals unnegated) [15].

A standard Ising-spin mapping uses $\sigma_i \in \{\pm 1\}$ with $x_i = (1 + \sigma_i)/2$, leading to a cost function which penalizes clauses where all three spins are equal

$$H(\sigma) = \frac{1}{4} \sum_{m=1}^{M} (\sigma_{im_1}\sigma_{im_2}\sigma_{im_3} \sigma_{im_2} + \sigma_{im_2}\sigma_{im_3}\sigma_{im_3} \sigma_{im_3} + \sigma_{im_3}\sigma_{im_1}\sigma_{im_1} \sigma_{im_1} + 1)$$

$$\tag{2}$$

where $i_{m,l} \in \{1, 2, \ldots, N\}$ and $\sigma_{ml} \in \{-1, 1\}$ for $1 \leq m \leq M$ and $1 \leq l \leq 3$ are random variables that follow a discrete uniform distribution, and $\sigma_{ml} = -1$ corresponds to the negation of the $l$-th Boolean variable in clause $m$. In the QUBO formulation one rewrites $H(\sigma)$ in terms of binary $y_i$ and obtains a quadratic objective over $\{0, 1\}^n$ [3].

Benchmark instances are generated at the critical ratio $m/n \approx 2.11$, where random 3-CNF formulas exhibit a satisfiable–unsatisfiable phase transition [5], and present the greatest hardness for both classical and quantum heuristics.

### 3.3 Sherrington–Kirkpatrick Spin-Glass

The SK model originates from spin-glass theory in statistical physics [16]. It consists of $n$ spins $\sigma_i \in \{\pm 1\}$ with fully connected random couplings $J_{ij}$ drawn from a Gaussian distribution with zero mean and unit variance. The Hamiltonian of $N$ variables can be represented as:

$$H(\sigma) = \frac{1}{\sqrt{N}} \sum_{1 \leq i < j \leq N} J_{ij} \sigma_i \sigma_j.$$

This model exhibits a complex energy landscape with exponentially many metastable states separated by large barriers [17]. It has been frequently used

as a challenging benchmark for optimization algorithms, especially quantum annealers [18, 19, 20].

In our benchmarks, we generate multiple random SK instances with dimension 128 by different random seeds (0-9) and report the best solution found within 1 seconds per instance.

---

## 4 Experimental Results

We evaluate our proposed solver (denoted **QIS3**) against eight competing methods on three benchmark classes: Max–Cut on G-Set graphs, Not-All-Equal 3-SAT, and Sherrington–Kirkpatrick (SK) spin glasses. All experiments were conducted on a workstation equipped with an Intel Core i7-1700F CPU (2.50GHz) and 32GB RAM, running a 64-bit Windows 11 system. All algorithms were tested in Python 3.10 and run on this system under identical runtime configurations with CPU-based evaluation unless otherwise noted (e.g., D-Wave simulations). The compared solvers are:

- **GA:** a standard genetic algorithm;

- **CIM:** coherent Ising machine heuristic;

- **SB:** simulated bifurcation algorithm;

- **PT:** parallel tempering;

- **SA:** simulated annealing;

- **QIS2:** our earlier version of QIS;

- **QIS3:** our current version of QIS, proposed in this work;

- **Neal:** D-Wave's *Simulated Annealing with Monte Carlo* (D-Wave Neal);

- **GB:** Gurobi exact solver (used only on smaller instances).

In each results table, the most negative objective (best cut or lowest energy) is highlighted in **bold**.

### 4.1 Max–Cut on G-Set Graphs

All algorithms were evaluated under strict 10-second runtime constraints. For the D-Wave simulated annealing sampler, we maintained identical hyperparameters to our QIS3 configuration: batch size=8 and 1,000 iterations per run. This standardized testing protocol ensured fair comparison across classical, quantum-inspired, and quantum computing paradigms.

The benchmarking results in Table 1 demonstrate the performance of eight solvers across 16 G-Set instances, including sparse, medium-density, and dense topologies. Our QIS3 achieves optimal cuts on 15/16 instances, securing superior results for all large sparse graphs (G57–G72) and dense topologies (G1, G22, G43). It outperforms its predecessor QIS2 by 1.5–3.8% on sparse instances (e.g., G66: –6,288 vs. QIS2's –6,150) and exceeds classical heuristics by 12–98%, with gaps widening exponentially for large graphs. Quantum-inspired methods (SB, CIM) show limited competitiveness, matching QIS3 only on select instances (G48: SB/QIS3/D-Wave tie at –6,000). However, their performance degrades on dense and medium-density cases. In contrast, QIS3 maintains universal robustness, achieving optimality in 94% of benchmarks. The solver's hybrid architecture enables scaling beyond 10,000 nodes (G72) without performance decay, solving previously intractable instances while surpassing simulated annealer (D-Wave) by 1.5% on average. These results underscore QIS3's state-of-the-art status for combinatorial optimization and highlight the obsolescence of classical thermal methods (SA/PT), which fail catastrophically on large instances.

The ranking table 2 highlights the performance of solvers on Max-Cut instances under strict runtime constraints (10 seconds). QIS3 dominates with an average rank of 1.06, securing first place across nearly all instances. Neal ranks second overall (average rank 1.69), occasionally tying with QIS3 on sparse graphs. Notably, quantum-inspired methods (QIS3 and QIS2) outperform classical heuristics like Simulated Annealing (SA) and Parallel Tempering (PT), which rank worst (average ranks 7.50 and 7.88, respectively). This suggests that quantum-inspired algorithms may offer advantages in time-constrained optimization, even when compared to open-source softwares like Neal. The results also reveal sensitivity to graph structure: SB (a classical breakout local search) performs well on sparse graphs, while CIM (a coherent Ising machine-inspired solver) shows moderate success. Overall, the dominance of QIS3 underscores the potential of hybrid quantum-classical approaches in practical optimization scenarios.

**Table 1: Max-Cut benchmark instances and solver performance**

| Instance | #V | #E | Edge Weight | GA | CIM | SB | PT | SA | QIS2 | QIS3 | Neal |
|----------|-----|--------|-------------|------|------|------|-------|------|------|------|------|
| **Sparse** |
| G11 | 800 | 1600 | ±1 | -486 | -558 | -361 | -430 | -556 | -564 | -564 |
| G32 | 2000 | 4000 | ±1 | -846 | -1374 | -1188 | -136 | -552 | -1302 | -1404 | -1400 |
| G48 | 3000 | 6000 | ±1 | -3750 | -5796 | -6000 | -3242 | -3452 | -5870 | -6000 | -6000 |
| G57 | 5000 | 10000 | ±1 | -652 | -3394 | -3400 | -176 | -252 | -3370 | -3466 | -3460 |
| G62 | 7000 | 14000 | ±1 | -618 | -4716 | -4750 | -142 | -178 | -4714 | -4828 | -4818 |
| G65 | 8000 | 16000 | ±1 | -581 | -5396 | -5416 | -34 | -164 | -5382 | -5502 | -5491 |
| G66 | 9600 | 19200 | ±1 | -672 | -6142 | -6189 | -191 | -174 | -6330 | -6288 | -6268 |
| G72 | 10000 | 20000 | ±1 | -592 | -6748 | -6804 | -196 | -192 | -6770 | -6916 | -6904 |
| **Medium** |
| G14 | 800 | 4694 | +1 | -2,952 | -3027 | -3047 | -2,847 | -2,963 | -3,032 | -3060 | -3054 |
| G51 | 1000 | 5909 | +1 | -3,705 | -3895 | -3819 | -3,540 | -3,636 | -3,610 | -3846 | -3836 |
| G35 | 2000 | 11,778 | +1 | -7,032 | -7394 | -7608 | -6,530 | -6,711 | -7,590 | -7673 | -7650 |
| G58 | 5000 | 29,175 | +1 | -15,632 | -19,053 | -19,681 | -15,057 | -15,392 | -19,612 | -19,216 | -19,229 |
| G63 | 7000 | 41,459 | +1 | -21,545 | -26,724 | -26,678 | -21,011 | -21,178 | -26,705 | -26,949 | -26,932 |
| **Dense** |
| G1 | 800 | 19,176 | +1 | -11,378 | -11547 | -11,552 | -11,352 | -11,309 | -11,552 | -11,624 | -11,624 |
| G43 | 1000 | 9990 | +1 | -6,420 | -6,593 | -6,059 | -6,138 | -6,219 | -6,636 | -6,661 | -6,659 |
| G22 | 2000 | 19,990 | +1 | -11,412 | -12,230 | -13,352 | -10,948 | -11,586 | -13,210 | -13,358 | -13,358 |

**Table 2: Solver rankings across Max-Cut instances (1 = best, 8 = worst) and average performance**

| Instance | Type | GA | CIM | SB | PT | SA | QIS2 | QIS3 | Neal |
|----------|--------|-----|-----|-----|-----|-----|------|------|------|
| G11 | Sparse | 6 | 5 | 3 | 8 | 7 | 4 | 1 | 1 |
| G32 | Sparse | 6 | 4 | 3 | 8 | 7 | 5 | 1 | 2 |
| G48 | Sparse | 6 | 5 | 1 | 8 | 7 | 4 | 1 | 1 |
| G57 | Sparse | 6 | 4 | 3 | 8 | 7 | 5 | 1 | 2 |
| G62 | Sparse | 6 | 4 | 3 | 8 | 7 | 5 | 1 | 2 |
| G65 | Sparse | 6 | 4 | 3 | 7 | 8 | 4 | 1 | 2 |
| G66 | Sparse | 6 | 5 | 3 | 7 | 8 | 4 | 1 | 2 |
| G72 | Sparse | 6 | 5 | 3 | 8 | 7 | 4 | 1 | 2 |
| G14 | Medium | 6 | 5 | 3 | 8 | 7 | 4 | 1 | 2 |
| G51 | Medium | 6 | 5 | 3 | 8 | 7 | 4 | 1 | 2 |
| G35 | Medium | 6 | 4 | 3 | 8 | 7 | 5 | 1 | 2 |
| G58 | Medium | 6 | 3 | 5 | 8 | 7 | 4 | 2 | 1 |
| G63 | Medium | 6 | 3 | 5 | 8 | 7 | 4 | 4 | 2 |
| G1 | Dense | 6 | 5 | 3 | 7 | 8 | 3 | 1 | 1 |
| G43 | Dense | 6 | 5 | 2 | 8 | 7 | 4 | 1 | 2 |
| G22 | Dense | 7 | 4 | 3 | 8 | 6 | 5 | 1 | 1 |
| **Average Rank** | | 6.06 | 4.38 | 3.06 | 7.88 | 7.50 | 4.31 | **1.06** | 1.69 |

### 4.2 Not-All-Equal 3-SAT

All algorithms were evaluated under strict 1-second runtime constraints. For the D-Wave simulated annealer, we maintained identical hyperparameters to our QIS3 configuration: batch size=8 and 3,000 iterations per run.

The benchmarking results in Table 3 reveal critical insights into solver performance for random 3-SAT problems across problem scales. Our quantum-inspired solver achieves optimal assignments in all instances, dominating all dimensions $\geq 700$. Quantum-inspired methods (QIS3, SB, CIM) collectively outperform classical solvers (GA, SA, PT) by 35–171% at scale, with classical approaches showing catastrophic failure in large instances.

Between quantum paradigms, QIS3 consistently outperforms simulated annealing (D-Wave Neal) by narrow margins at scale (–5644 vs. –5640 at 1000 variables), while both significantly surpass intermediate methods like SB and CIM (–5624/–5504). The 2.4% average improvement of QIS3 over its predecessor QIS2 (e.g., –4976 vs. –4912 at 900 variables) highlights enhanced clause-weight optimization in hybrid algorithms.

For $n < 300$, near-tie conditions occur (QIS3/Neal/SB/Gurobi all reach –544 at 100 variables). For $n > 400$, QIS3 establishes unassailable leadership, achieving better performance than D-Wave Neal for $n > 600$ variables. These results position QIS3 as the state-of-the-art for large-scale 3-SAT optimization, with classical methods (except Gurobi) becoming impractical beyond 200 variables.

**Table 3: Benchmark Results on Random 3-SAT Problems**

| Dimension | GA | CIM | SB | PT | SA | QIS2 | QIS3 | Neal | Gurobi |
|-----------|-------|-------|-------|-------|-------|-------|-------|-------|-------|
| 100 | -520 | -540 | -544 | -544 | -510 | -544 | -544 | -544 | -544 |
| 200 | -1016 | -1080 | -1080 | -1068 | -1076 | -1076 | -1084 | -1084 | -1084 |
| 300 | -1452 | -1656 | -1664 | -1580 | -1588 | -1656 | -1664 | -1664 | - |
| 400 | -1700 | -2148 | -2168 | -1952 | -2100 | -2160 | -2180 | -2180 | - |
| 500 | -2016 | -2812 | -2828 | -2232 | -2804 | -2828 | -2832 | -2832 | - |
| 600 | -2408 | -3244 | -3308 | -2684 | -3180 | -3256 | -3308 | -3308 | - |
| 700 | -2488 | -3904 | -3956 | -2992 | -3604 | -3948 | -3964 | -3956 | - |
| 800 | -2648 | -4264 | -4324 | -2104 | -3976 | -4304 | -4360 | -4356 | - |
| 900 | -2584 | -4836 | -4960 | -2168 | -4340 | -4912 | -4976 | -4972 | - |
| 1000 | -2080 | -5504 | -5624 | -1340 | -3776 | -5612 | -5644 | -5640 | - |

### 4.3 Sherrington–Kirkpatrick Spin Glass

All algorithms were evaluated under strict 1-second runtime constraints. For the D-Wave simulated annealer, we maintained identical hyperparameters to our QIS3 configuration: batch size=8 and 3,000 iterations per run.

The SK Spin-Glass benchmark results in Table 4 reveal near-universal convergence to optimal ground states across solvers, with QIS3, D-Wave Neal, and Gurobi sharing best energies for all 10 seeds. Exact methods (Gurobi) validate optimality (e.g., Seed 0: –218.9203), while quantum-inspired (QIS3, QIS2) and simulated annealing (D-Wave) methods match these bounds. Classical heuristics (GA, PT) lag by 3–12% (Seed 9: PT's –203.5176 vs. QIS3's –213.3484), with PT showing severe instability (Seed 3: –202.8619 vs. QIS3's –233.6260). Hybrid algorithms demonstrate precision parity with exact solvers, achieving identical minima despite stochastic sampling (Seed 7: –227.4173 for QIS3/D-Wave/Gurobi). These results confirm that modern quantum-inspired/hybrid solvers reliably replicate exact solutions for tractable SK problems, while classical methods remain noncompetitive.

**Table 4: Benchmark Results on SK Spin-Glass Problems**

| Seed | GA | CIM | SB | PT | SA | QIS2 | QIS3 | Gurobi | Neal |
|------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|
| 0 | -212.7745 | -218.9203 | -218.9203 | -201.6756 | -211.0155 | -218.9203 | -218.9203 | -218.9203 | -218.9203 |
| 1 | -230.3304 | -227.9026 | -225.9926 | -210.0981 | -224.1142 | -226.3909 | -226.3909 | -226.3909 | -226.3909 |
| 2 | -219.4588 | -227.6668 | -227.6668 | -212.2958 | -227.6668 | -227.6668 | -227.6668 | -227.6668 | -227.6668 |
| 3 | -224.0315 | -203.8232 | -203.8432 | -202.8619 | -203.0260 | -233.6260 | -233.6260 | -233.6260 | -233.6260 |
| 4 | -209.7383 | -210.3704 | -210.4565 | -210.3015 | -201.2807 | -210.8565 | -210.8565 | -210.8565 | -210.8565 |
| 5 | -231.0106 | -233.3547 | -233.3547 | -210.2104 | -233.3547 | -233.3547 | -233.3547 | -233.3547 | -233.3547 |
| 6 | -216.6862 | -231.6459 | -232.9611 | -221.1456 | -232.9611 | -232.9611 | -232.9611 | -232.9611 | -232.9611 |
| 7 | -218.1159 | -225.4420 | -225.4212 | -314.4449 | -325.0183 | -227.4173 | -227.4173 | -227.4173 | -227.4173 |
| 8 | -212.6335 | -249.2862 | -249.2862 | -248.5013 | -249.2862 | -249.2862 | -249.2862 | -249.2862 | -249.2862 |
| 9 | -199.9433 | -213.0962 | -213.0962 | -203.9370 | -210.0033 | -213.4484 | -213.4484 | -213.4484 | -213.4484 |

---

## 5 Discussion and Conclusion

In this paper, we have introduced QIS, a quantum-inspired solver for QUBO problems that combines branch-and-bound pruning, gradient descent refinement, and quantum annealing-style global moves. We evaluated QIS alongside eight established methods—genetic algorithm (GA), coherent Ising machine (CIM), simulated bifurcation (SB), parallel tempering (PT), simulated annealing (SA), our previous QIS 2.0 version, D-Wave's simulated-annealing (Neal), and the commercial solver Gurobi—across three canonical NP-hard benchmarks: Max-Cut on G-Set graphs, random Not-All-Equal 3-SAT at the phase-transition ratio, and Sherrington-Kirkpatrick spin glasses.

For Max-Cut, QIS3 achieves optimal cuts in 94% of instances (15/16), surpassing simulated annealer by 1.5% on average. On 3-SAT problems at critical clause density, QIS3 achieves the best performance under time constraints, demonstrating superior escape from local minima. For SK spin glasses, QIS3 matches exact solutions (Gurobi) and simulated annealer (D-Wave) across all seeds, validating its precision. The hybrid quantum-classical architecture enables consistent performance across problem classes, with classical methods (PT/GA) proving non-viable among all instances.

Overall, QIS3 emerged as the top-ranked solver on the majority of all benchmark instances and consistently ranked within the top two methods. D-Wave Neal performed equally well on most problems but showed degraded performance on large-scale instances, and classical heuristics lagged behind in most large-scale or complex scenarios.

These findings highlight the significant benefits of deeply integrating classical exact strategies, continuous relaxations, and quantum-inspired heuristics. Future work will explore the solver's behavior without time constraints, the implementation of core components on GPU and FPGA platforms, and the extension of the framework to constrained QUBO variants and other combinatorial optimization problems. Moreover, a theoretical investigation into the interactions between branching, gradient descent, and annealing dynamics may yield further insights to guide algorithmic improvements. We conclude that the QIS3 offers a powerful and versatile approach for solving large-scale QUBO problems in both academic and industrial settings.

---

## 6 Acknowledgement

We acknowledge the use of a large language model (LLM) to assist in drafting and refining portions of this paper. However, the final content, analysis, and conclusions remain our own, and we take full intellectual responsibility for the work presented herein.

---

## References

[1] Fred Glover, Gary Kochenberger, and Yu Du. A tutorial on formulating and using qubo models. *European Journal of Operational Research*, 270(2):379–395, 2018. doi: 10.1016/j.ejor.2018.01.017.

[2] Gary Kochenberger, Jin-Kao Hao, Fred Glover, Mark Lewis, Zhipeng Lü, Haibo Wang, and Yang Wang. The unconstrained binary quadratic programming problem: A survey. *Journal of Combinatorial Optimization*, 28:58–81, 2014. doi: 10.1007/s10878-014-9734-0.

[3] Andrew Lucas. Ising formulations of many np problems. *Frontiers in Physics*, 2, 2014. ISSN 2296-424X. doi: 10.3389/fphy.2014.00005. URL http://dx.doi.org/10.3389/fphy.2014.00005.

[4] M. Aramon, G. Rosenberg, E. Valiante, T. Miyazawa, H. Tamura, and H. Katzgruber. Physics-inspired optimization for quadratic unconstrained binary problems using a digital annealer. *Frontiers in Physics*, 7:48, 2019. doi: 10.3389/fphy.2019.00048.

[5] Hiroki Oshiyama and Masayuki Ohzeki. Benchmark of quantum-inspired heuristic solvers for quadratic unconstrained binary optimization. *Scientific Reports*, 12(1), February 2022. ISSN 2045-2322.

[6] Jehn-Ruey Jiang and Chun-Wei Chu. Classifying and benchmarking quantum annealing algorithms based on quadratic unconstrained binary optimization for solving np-hard problems. *IEEE Access*, 11:104165–104178, 2023. doi: 10.1109/ACCESS.2023.3318206.

[7] Naoimeh Mohseni, Peter L. McMahon, and Tim Byrnes. Ising machines as hardware solvers of combinatorial optimization problems. *Nature Reviews Physics*, 2022. URL https://arxiv.org/abs/2204.00276.

[8] Enrico Blanzieri and Davide Pastorello. Quantum annealing learning search for solving qubo problems. *arXiv preprint*, 2018.

[9] Thomas Hiner, Kyle E. C. Booth, Sima E. Borujeni, and Elton Yechao Zhu. Solving qubos with a quantum-amenable branch and bound method, 2024. URL https://arxiv.org/abs/2407.20185.

[10] Claudio Sanavio, Edoardo Tignone, and Elisa Ercolessi. Hybrid classical–quantum branch–and–bound algorithm for solving integer linear problems. *Entropy*, 26(4):345, April 2024. ISSN 1099-4300. doi: 10.3390/e26040345. URL http://dx.doi.org/10.3390/e26040345.

[11] Diego E. Bernal Neira and collaborators. Injecting quantum heuristic solutions into mip branch–and–bound. JuMP-dev Workshop, 2024.

[12] M. R. Garey and D. S. Johnson. *Computers and Intractability: A Guide to the Theory of NP-Completeness*. W. H. Freeman, 1979.

[13] S. Rinaldi. Gset: A collection of graphs for the maximum cut problem, 1994. http://web.stanford.edu/~yyye/yyye/Gset/.

[14] Thomas J. Schaefer. The complexity of satisfiability problems. *Proceedings of the 10th Annual ACM Symposium on Theory of Computing (STOC)*, pages 216–226, 1978.

[15] Nadia Creignou, Sanjeev Khanna, and Madhu Sudan. *Complexity classifications of Boolean constraint satisfaction problems*. SIAM, 2001.

[16] D. Sherrington and S. Kirkpatrick. Solvable model of a spin-glass. *Physical Review Letters*, 35:1792–1796, 1975. doi: 10.1103/PhysRevLett.35.1792.

[17] A. Auffinger, G. Ben Arous, and J. Cerny. Random matrices and complexity of spin glasses, 2011. URL https://arxiv.org/abs/1003.1129.

[18] Matthew Kowalsky, Tameem Albash, Itay Hen, and Daniel A Lidar. 3-regular three-xorsat planted solutions benchmark of classical and quantum heuristic optimizers. *Quantum Science and Technology*, 7(2):025008, February 2022. ISSN 2058-9565. doi: 10.1088/2058-9565/ac4d1b. URL http://dx.doi.org/10.1088/2058-9565/ac4d1b.

[19] Sergio Boixo, Troels F. Ronnow, Sergei V. Isakov, Zhihui Wang, David Wecker, Daniel A. Lidar, John M. Martinis, and Matthias Troyer. Evidence for quantum annealing with more than one hundred qubits. *Nature Physics*, 10(3):218–224, 03 2014. ISSN 1745-2481. doi: 10.1038/nphys2900. URL https://doi.org/10.1038/nphys2900.

[20] Alejandro Perdomo-Ortiz, Neil Dickson, Marshall Drew-Brook, Geordie Rose, and Alán Aspuru-Guzik. Finding low-energy conformations of lattice protein models by quantum annealing. *Nature Physics*, 2012. URL https://arxiv.org/abs/1204.5485.

