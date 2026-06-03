# A comprehensive benchmark of an Ising machine on the Max-Cut problem


> **Citation.** Canonical entry `shaglel2025` in [`references.bib`](../../references.bib) (resolved via Crossref/DataCite). arXiv:[2507.22117](https://arxiv.org/abs/2507.22117).
>
> **Companion note.** [`shaglel-2025-maxcut-ising-benchmark.note.md`](./shaglel-2025-maxcut-ising-benchmark.note.md) — how this paper links to Gibbsiq.

Salwa Shaglel, Markus Kirsch, Marten Winkler, Christian Münch, Stefan Walter, Fritz Schimkel, Martin Kliesch

## Abstract

Quantum-inspired computing has emerged as a promising approach to solve combinatorial optimization problems. This paper presents a comprehensive benchmarking study of Fujitsu's second-generation Digital Annealer (DAv2) and third-generation Digital Annealer (DAv3), comparing their performance against classical heuristics and state-of-the-art solvers on the Max-Cut problem. We evaluate our solvers on 2,125 instances from the Max-Cut and QUBO Instances Library (MQLib), spanning graph sizes from 200 to 53,000 variables. Our results demonstrate that DAv2 consistently finds better or matching cuts compared to the best classical MQLib heuristics on approximately 69% of the benchmarked instances. DAv3 maintains competitive performance with a success rate of about 61%. Additionally, comparisons with D-Wave's hybrid quantum-classical solver and the recently introduced quantum-inspired heuristic QIS3 reveal that the DA versions achieve shorter runtimes and better solutions in most cases. Our work demonstrates the practical utility of quantum-inspired CMOS-based devices for combinatorial optimization at scale.

## 1. Introduction

Combinatorial optimization stands as a cornerstone of computational science and industry, addressing problems from logistics to machine learning that are fundamentally difficult to solve. The Max-Cut problem—partitioning graph vertices into two sets to maximize the edges crossing the partition—exemplifies NP-hard problems that are central to computer science theory and practical applications.

Recent years have witnessed a surge in quantum computing and quantum-inspired approaches aimed at tackling such hard problems. Quantum annealing devices like D-Wave's systems and quantum-inspired digital annealers offer alternative computational paradigms. However, comprehensive, fair comparisons between these novel approaches and classical methods remain sparse. This work provides a rigorous benchmarking study of Fujitsu's Digital Annealer against established classical heuristics and other quantum-inspired solvers.

### 1.1 Previous work

The evaluation of heuristic solvers for combinatorial optimization problems has received significant attention in the literature. Dunning et al. [17] conducted a systematic evaluation of heuristics for Max-Cut and QUBO problems. Philipson [18] provides a comprehensive overview of fair benchmarking practices for emerging computing paradigms. D-Wave's hybrid solver service [19] has been benchmarked against classical solvers in various studies. More recently, quantum-inspired approaches have been evaluated on diverse problem classes [43, 50, 51].

### 1.2 Our contribution

This paper makes the following contributions:

1. A comprehensive benchmarking study on 2,125 instances from MQLib spanning graph sizes from 200 to 53,000 variables
2. Comparison of DAv2 and DAv3 against the best performing MQLib heuristics, D-Wave's Hybrid Solver, and QIS3
3. Analysis of runtime behavior and solution quality across different instance categories
4. Instance-specific time limit enforcement to ensure fair comparisons
5. Investigation of performance sensitivity with respect to instance characteristics

## 2. Background

### 2.1 QUBO problems

Quadratic Unconstrained Binary Optimization (QUBO) is a fundamental problem formulation in combinatorial optimization. A QUBO problem can be expressed as:

$$\text{minimize} \quad x^T Q x = \sum_{i \geq j} q_{ij} x_i x_j$$

where $x \in \{0, 1\}^n$ is a binary vector and $Q$ is an $n \times n$ matrix with real entries. The QUBO formulation is powerful because many combinatorial optimization problems can be reduced to it [1, 3].

### 2.2 Max-Cut problem

The Maximum Cut problem is defined on an undirected graph $G = (V, E)$ with $|V| = n$ vertices and $|E| = m$ edges. A cut is a partition of vertices into two sets $S$ and $\bar{S} = V \setminus S$. The size of the cut is the number of edges with one endpoint in $S$ and the other in $\bar{S}$. The Max-Cut problem seeks to find the cut with maximum size.

The Max-Cut problem can be formulated as a QUBO problem. For a graph with adjacency matrix $A$, the objective is:

$$\text{maximize} \quad \sum_{(i,j) \in E} (1 - x_i x_j)$$

which is equivalent to:

$$\text{minimize} \quad -\sum_{(i,j) \in E} (1 - x_i x_j) = \sum_{(i,j) \in E} x_i x_j$$

with $x_i \in \{0, 1\}$. This reformulation allows the Max-Cut problem to be cast as a QUBO optimization problem.

### 2.3 Digital Annealer

The Digital Annealer (DA) is a quantum-inspired CMOS-based application-specific integrated circuit (ASIC) developed by Fujitsu for solving QUBO problems. Unlike quantum annealers that exploit quantum mechanical phenomena, the DA uses classical computing principles with a specialized architecture to simulate annealing behavior efficiently.

The DA operates by iteratively refining solutions through a process inspired by simulated annealing and Markov Chain Monte Carlo (MCMC) methods. The core mechanism involves:

1. **Initialization**: A random initial spin configuration is selected
2. **Annealing**: Temperature parameters are gradually reduced according to a schedule
3. **Iteration**: At each temperature, the algorithm explores the solution space and accepts or rejects moves based on an acceptance criterion
4. **Termination**: The process concludes when the temperature reaches a minimum or a stopping criterion is met

The DA has been designed to efficiently handle large-scale QUBO problems, with successive generations (DAv1, DAv2, DAv3) providing improved performance and capability.

## 3. Methodology

### 3.1 Benchmark setup

We evaluated solvers on instances from the Max-Cut and QUBO Instances Library (MQLib) [21], which provides a comprehensive collection of Max-Cut problem instances across various sizes and densities. The library includes instances categorized by size:

- **x-small** (200-1024 vertices)
- **small** (1024-2048 vertices)
- **medium** (2048-4096 vertices)
- **large** (4096-8192 vertices)
- **x-large** (8192-53000 vertices)

For each size category, instances are further classified by density (sparse, balanced, dense). A total of 2,125 instances were used in this study.

### 3.2 Runtime and time limits

To ensure fair comparison, we established instance-specific time limits based on instance characteristics. For DAv2, we developed fitted runtime functions (Eqs. 6-7 in Appendix B) that estimate the annealing time and CPU time required based on the number of variables, runs, and iterations.

The runtime estimation framework accounts for:
- QUBO loading time
- Sampling time
- Communication overhead between software and hardware

For DAv3, an empirical offset approach was employed (Appendix C) due to differences in runtime behavior. An offset of 3 seconds was determined to provide optimal balance between runtime compliance and solution quality.

### 3.3 Instance categories

Following Dunning et al. [17], instances were categorized into:

- **Sparse instances** (density < 0.2): Typically easier to solve
- **Balanced instances** (0.2 ≤ density ≤ 0.8): Moderate difficulty
- **Dense instances** (density > 0.8): Generally harder due to greater connectivity

For each category, we identified the best-performing MQLib heuristic:
- **x-small sparse**: BURER2002
- **x-small balanced & dense**: PAL2004bMTS2
- **small sparse**: BURER2002
- **small dense**: PAL2004bMTS2

## 4. Results

### 4.1 DAv2 vs. classical heuristics

Figure 6 presents the progress of DAv2's cut accuracy relative to D-Wave's Hybrid Solver over the 20-minute time limit for integer and float instance sets. Each line corresponds to an individual instance, with crosses marking when the best cut was found. Colors indicate performance: green for better than D-Wave HS, yellow for equal, and blue for worse.

**Key findings:**

1. **Overall performance**: DAv2 consistently found better cuts than the best classical heuristics on approximately 69% of the benchmarked x-small and small instances.

2. **Rapid convergence**: DAv2 demonstrates rapid convergence to high-quality solutions in many instances, often finding the best cut within the first few seconds of runtime.

3. **Instance dependence**: Performance varies significantly across instances. For certain graph structures or sizes, the DA quickly finds optimal or near-optimal cuts, while for others traditional solvers perform better.

4. **Floating-point handling**: DAv3 shows lower performance on float-valued instances compared to integer-valued ones, with differences attributed to rounding errors during conversion.

### 4.2 DAv2 vs. DAv3

Comparison across the 14 instances where both versions yielded results reveals:

- DAv3 achieves better results more frequently than DAv2
- DAv2 finds larger cuts than DAv3 only on instance G63
- Both fail against DAv3 and QIS3 on G65
- DAv2's higher "win" rate (approximately 69%) versus DAv3's (approximately 61%) reflects DAv2's more consistent performance across the benchmark set

The performance difference stems partly from DAv3's greater sensitivity to floating-point conversion errors, particularly on larger instances.

### 4.3 DA vs. QIS3

During preparation of this manuscript, QIS3, a new hybrid metaheuristic solver combining branch-and-bound with gradient-descent refinement and quantum annealing-inspired acceleration, was introduced by Yang et al. [20]. QIS3 was evaluated on 16 G-set instances against eight state-of-the-art solvers: QIS2, genetic algorithms, coherent Ising machine, simulated annealing, parallel tempering, simulated bifurcation, D-Wave's simulated annealing (Neal), and Gurobi. All algorithms operated under 10-second runtime constraints.

**Configuration:** We configured DAv2 parameters (Appendix B) to achieve a runtime of approximately 10 seconds. For DAv3, runtime offsets were adjusted to yield runtimes closest to 10 seconds.

**Results (Table 4):**

| Instance | n | d | QIS3 cut | DAv2 cut | DAv2 time (sec) | DAv3 cut | DAv3 time (sec) | Limit (sec) |
|----------|-----|---------|----------|----------|-----------------|----------|-----------------|-------------|
| G11 | 800 | 0.005 | 564 | 564 | 0.866 | 564 | 10.983 | 10 |
| G32 | 2000 | 0.002 | 1404 | 1410 | 9.91 | 1410 | 9.652 | 8 |
| G48 | 3000 | 0.0013 | 6000 | 6000 | 9.838 | 6000 | 8.795 | 8 |
| G57 | 5000 | 0.0008 | 3466 | 3470 | 9.959 | 3482 | 8.737 | 6 |
| G62 | 7000 | 0.0006 | 4828 | 4838 | 9.961 | 4846 | 10.759 | 7 |
| G65 | 8000 | 0.0005 | 5502 | 5460 | 10.139 | 5534 | 12.166 | 8 |
| G66 | 9000 | 0.0004 | 6288 | 6288 | - | 6180 | 8.772 | 8 |
| G72 | 10000 | 0.0004 | 6916 | - | - | 6728 | 9.029 | 4 |
| G14 | 800 | 0.0147 | 3060 | 3064 | 9.866 | 3064 | 10.978 | 10 |
| G51 | 1000 | 0.0118 | 3846 | 3848 | 9.869 | 3848 | 11.034 | 10 |
| G35 | 2000 | 0.0059 | 7673 | 7686 | 9.903 | 7686 | 9.635 | 8 |
| G58 | 5000 | 0.0024 | 19216 | 19262 | 9.956 | 19263 | 8.893 | 8 |
| G63 | 7000 | 0.0017 | 26949 | 27012 | 9.942 | 27003 | 10.873 | 8 |
| G1 | 800 | 0.06 | 11624 | 11624 | 9.864 | 11624 | 10.995 | 10 |
| G43 | 1000 | 0.02 | 6660 | 6660 | 9.871 | 6660 | 11.041 | 9 |
| G22 | 2000 | 0.01 | 13358 | 13359 | 9.901 | 13359 | 9.725 | 9 |

**Analysis:**

In their original study, QIS3 reported the highest cut value on 15 out of 16 instances (exception: G58).

Results of DAv2, DAv3, and QIS3 are presented in Table 4. For the DA, both time limit and actual runtimes are reported; only the time limit is available for QIS3. Notably, one or both DA versions find better or matching results than QIS3 on 14 out of 16 instances, including G58. The only exceptions are instances G66 and G72, where QIS3 remains the top performer, and G65, where only DAv3 found a better cut than QIS3.

The drop in performance for DAv3 on G66 and G72 is attributed to required partitioning when the problem size exceeds the 8,192-variable capacity of a single DAU.

Comparing both DA versions across the 14 instances where results are available for both, DAv3 yields better results more frequently than DAv2. DAv2 finds a larger cut than DAv3 only on G63, while it fails against both DAv3 and QIS3 on G65.

Figure 7 shows the progress of DAv3's cut value accuracy relative to QIS3's over the 10-seconds time limit. For half of the instances, DAv3 achieves an equivalent or better cut within the first few seconds. An equivalent figure for DAv2 is not possible because it lacks the functionality to log intermediate improving cuts into a solution pool during execution. However, we also display in Fig. 7 the best cut achieved by DAv2 (dots), as reported in Table 4, along with the shortest runtime at which it was attained. These results are derived from multiple runs with time limits ranging from 1 to 10 seconds.

For 6 out of 14 instances, DAv2 found its best cut that matches or exceeds QIS3's cut in just a few seconds. For 4 instances, the cut was achieved in roughly half the time limit. This demonstrates the rapid convergence behavior of the DA toward high-quality solutions (3a).

## 5. Conclusion

We have conducted a comprehensive benchmarking study of Fujitsu's second-and third-generation Digital Annealers (DAv2 and DAv3), on the Max-Cut problem. We compare their performance against selected best-performing MQLib classical heuristics, D-Wave's hybrid quantum-classical solver (HS), and a recently introduced quantum-inspired heuristic QIS3.

Our evaluation across 2,125 instances—spanning graph sizes from 200 up to 53,000 variables—was based on the best objective value achieved within instance-specific time limits, ensuring as fair a comparison as possible. The results demonstrate that DAv2 consistently found a better cut than the best classical heuristics on approximately 69% of the benchmarked subset of instances, while DAv3 maintains competitive performance with a success rate of about 60.8%.

Notably, DAv3 showed a greater sensitivity to rounding errors resulting from converting float coefficients to integer. On 45 Max-Cut instances selected by D-Wave, DAv3 outperformed the D-Wave HS, particularly on instances with integer weights. DAv3 found lower-quality cuts for the majority of float-valued instances, though with a high solution accuracy. Finally, our comparison with QIS3 on 16 G-set instances reveals that one or both DA versions achieve shorter runtimes and better solutions in most cases. However, for two large G-set instances, QIS3 shows a surprisingly good performance. We further show that the DA can have a rapid convergence behavior already before the time limits are met. Often, high-quality solutions can be reached within the first few seconds of runtime.

Future work can expand this study in several directions. First, we aim to benchmark the DA on constrained NP-hard problems to assess its effectiveness in more complex settings. Our results also suggested that performance is highly instance-dependent: for certain graph structures or sizes, the DA quickly finds optimal or near-optimal cuts, while in other cases, traditional solvers or heuristics outperform it. This variation motivates a hybrid workflow that leverages different solvers depending on the instance features. Another promising direction is to incorporate preprocessing techniques into the DA, tailored to a specific problem class such as the Max-Cut, where it could further enhance its performance.

## 6. Conflict of interest

The DA is a Fujitsu product, and Kirsch, Münch, Schimkel, and Walter work for the *Fujitsu Germany GmbH*, which is a German Fujitsu subcompany. Their main work consists of consultations on quantum-inspired computing. Kliesch is the holder of the endowed professorship "Quantum Inspired and Quantum Optimization", which is financed by Fujitsu Services GmbH and the Dataport AöR. By German laws, all university professorships are guaranteed scientific independence, and this requirement is also accommodated in the legal framework of this endowed professorship.

The authors declare that the comparison of the DA with other methods was conducted to provide a fair and objective comparison, without giving special consideration to Fujitsu's interests. In fact, Winkler, Shaglel, and Kliesch initiated this work to independently determine the DA's performance without having to trust other sources. All authors made their best efforts to follow fair benchmarking standards as much as possible, given the technical feasibility.

## 7. Acknowledgment

We thank John Silberholz for helpful discussions about methodology of Ref. [17] and valuable comments regarding the MQLib repository [21]. We thank Mirko Arienzo, Nikolai Miklin, and Michel Krispin for discussions and valuable feedback back during the development of this project. Shaglel and Kliesch are funded by Fujitsu Germany GmbH and Dataport as part of the endowed professorship "Quantum Inspired and Quantum Optimization" and the Hamburg Quantum Computing project, which is co-financed by the ERDF of the European Union and the Fonds of the Hamburg Ministry of Science, Research, Equalities and Districts (BWFGB) within the Hamburg Quantum Computing project.

## Appendices

### A. DAv2 vs. best MQLib heuristics on x-small-small instances

We analyze the performance of DAv2 in comparison with the corresponding best-performing MQLib heuristics for x-small and small categories across all densities. As identified in Table 3 in Section 3.3, the best heuristic for x-small and small sparse instances is BURER2002, while for the balanced and dense instances it is PAL2004bMTS2. This analysis is omitted for DAv3 due to the instances in these categories exceeding the time limit specified for instances in these categories by significantly more than 10%, leading to an unfair comparison with other solvers (see Appendix D).

Figure 8 illustrates the size and density characteristics of the instances involved in this analysis, with a total of 1306 instances. Most dense instances contain fewer than approximately 1000 vertices, and the majority of x-small and small instances are sparse, as shown by the nested inset in Fig. 8a and the darker blue region of Fig. 8a.

Fig. 9 shows that on average, DAv2 provides better solutions than BURER2002 in the corresponding categories: x-small sparse and small sparse (68.8% and 64.2%). PAL2004bMTS2 outperforms DAv2 on x-small dense (31.3% vs. 15.4%). For a considerable number of instances, especially in x-small balanced and dense, both find the same cut value. On the other hand, DAv2 yields better results than PAL2004MTS2 on small balanced and small dense categories, finding a better cut in 53.7% and 58.3% of the instances, respectively. However, the number of instances in these categories is relatively small, so these results should be interpreted with caution.

Fig. 10 presents a bar plot of instance counts across accuracy ratio ranges, defined as the ratio of the cut value achieved by DAv2 to that achieved by the corresponding heuristic. The plot shows a clear skew to the values greater than 1.0 (i.e., higher green bars), highlighting an overall better performance of DAv2 over the best-performing MQLib heuristics on the x-small and small categories. Most 'losses' of DAv2 have high accuracy between [0.998, 1.000). In total, DAv2 achieves better cuts in 612 instances and equal in 506 out of 1306 instances, resulting in a 'win' rate of approximately 46.86% and a 'tie' rate of approximately 38.74%.

### B. DAv2 runtime estimation

To allow for DAv2 to terminate within a specific time range, for the purpose explained in Section 3.1, we have obtained fitted functions to estimate the annealing time and CPU time based on the input number of variables, runs, and iterations. To obtain these estimates, we generated runtime data of DAv2 across all instances using various combinations of run and iteration numbers. The number of runs was varied from minimum to maximum in steps of 16, i.e., 16, 32, 48, 64, 80, 96, 112, 128. The number of iterations was set in relation to the number of variables as $f \times n^2$ where $f \in \{1, 2, 4\}$.

The runtime strongly depends on the size category introduced in Section 3.2 to which a given instance belongs. Accordingly, the annealing time and CPU time functions are defined as:

$$\text{Annealing\_time}(\text{runs}, \text{iterations}) = a(\text{runs} \times \text{iterations}) + b \quad (6)$$

$$\text{CPU\_time}(\text{runs}, n) = c(n^2 \times \text{runs}) + d(n \times \text{runs}) + en^2$$
$$+ k(\text{runs}) + gn + h \quad (7)$$

where the fitting parameters $a, b, c, d, e, k, g, h$ are given in Table 5 for each size category. We used these equations to estimate the number of runs and iterations required for each instance to as much as possible meet a specified time limit. Specifically, we aimed to select the largest combination of run and iteration numbers that meet some enforced thresholds.

The procedure is as follows: we begin with the minimum values - 16 runs and 10,000 iterations. We first estimate the CPU time under these values using Eq. (7). From 90% of the time limit, we subtract the estimated CPU time along with other fixed overheads such as QUBO loading time, sampling time, and scaling time to determine the remaining time available for annealing. The 90% threshold allows for a buffer, and the sampling and scaling times are instance-specific constants independent from the number of runs and iterations and are extracted from the collected runtime data.

Based on this, we estimate the required number of iterations using Eq. (6). If this value exceeds the 10,000-iteration minimum, we update the iteration number accordingly. If it exceeds the maximum allowed number of iterations (2 billion iterations), the number of runs is increased and we start over with 10,000 iterations. Using these updated values, we finally compute the total time = CPU time + annealing time + fixed overheads. We check the total time if it exceeds 0.99% of the time limit to stop exploring further higher number of runs and iterations.

| Parameter | x-small: 20 ≤ n < 1024 | small: 1024 ≤ n < 2048 |
|-----------|------------------------|----------------------|
| a | $2.0081 \times 10^{-6}$ | $2.0017 \times 10^{-6}$ |
| b | 13.2942 | 48.6364 |
| c | $-0.5576 \times 10^{-7}$ | $6.2894 \times 10^{-7}$ |
| d | 0.0007 | -0.0007 |
| e | $2.9877 \times 10^{-6}$ | $3.5768 \times 10^{-6}$ |
| k | -0.0101 | 0.7396 |
| g | -0.0020 | 0.0056 |
| h | 4.3422 | 5.3949 |
| | medium: 2048 ≤ n < 4096 | large: 4096 ≤ n < 8192 |
| a | $2.0010 \times 10^{-6}$ | $2.0005 \times 10^{-6}$ |
| b | 193.8656 | 126.2170 |
| c | $7.8667 \times 10^{-7}$ | $7.4802 \times 10^{-7}$ |
| d | -0.0015 | -0.0002 |
| e | $4.1800 \times 10^{-6}$ | $-9.6817 \times 10^{-6}$ |
| k | 1.8767 | -3.7253 |
| g | -0.0056 | 0.1548 |
| h | 59.8780 | -264.9900 |

**Table 5:** Parameters of DAv2 annealing and CPU time fitted functions, Eqs. (6) and (7), respectively.

### C. DAv3 time limit offset determination

As noted in Section 3.1, DAv3 is more prone to far exceed shorter time limits, so our focus is on identifying an appropriate offset specifically for such cases. Due to its stochastic runtime behavior, we were unable to obtain a fitted runtime function as done for DAv2 in Appendix B. Instead, we determine a suitable time limit offset empirically. To this end, we executed DAv3 on all medium to x-large instances that have been assigned time limits between 0.25 and 100 seconds, with a shorter time limit defined in Eq. (5) with various offsets: 0 to 5 seconds in 1-second increments. Our goal is to identify the offset that minimizes the number of instances exceeding the 10% safety margin while achieving the highest possible average accuracy. The average accuracy for each offset is computed as

$$\text{Average\_accuracy}(\%) = \frac{1}{N} \left( \sum_{i=1}^{N} \frac{\text{cut}_i}{\text{best}_i} \right) \times 100 \quad (8)$$

where $\text{cut}_i$ is the achieved objective value for instance $i$ for each corresponding offset run, $\text{best}_i$ is the best objective value found across all available offset runs for instance $i$, and $N = 819$ is the total number of instances in the medium to x-large categories. In Fig. 11, we show how the offset affects the average cut accuracy and the number of instances whose runtime exceeds 10% of the time limit. An offset of 3 seconds fairly reduces the number of instances that violate the safety margin, with only a marginal decrease in average accuracy. Higher offsets yield minimal improvements but come with additional accuracy losses, making them less favorable.

### D. Runtime deviation of solvers from baseline time limit

Solvers do not typically terminate exactly at the specified time limit. To account for this, we define a safety margin with an upper bound of 10%. In Fig. 12, we present histograms showing instance counts by each solver's runtime-to-limit ratio. As shown in Fig. 12c, the runtime fitting of DAv2, detailed in Appendix B, was largely successful. However, it also occasionally resulted in a runtime shorter than the assigned limit. It still exceeds the time limit slightly in some cases, but it is still well below the 10% upper limit of the safety margin. Although DAv3 includes a time limit termination feature and an added buffer, it still exceeds the safety margin on a significant number of instances, especially those in the x-small and small categories (see Fig. 12b). This is partially due to a 1-second minimum runtime, as well as the communication overhead between the DAU and the software layer, making it more likely to exceed the specified time limit. As a result, we restrict our analysis for DAv3 to larger instances. The time analysis for DAv3 is presented in Fig. 12b to the medium through x-large categories.

For a large number of instances, the runtime of DAv3 is far below the time limit more so than DAv2 with runtimes dropping to as low as 50% of the limit. This could partly explain why DAv2 provides a higher 'win' ratio than DAv3. As expected, MQLib solvers also often exceed the time limit as shown in Figs. 12d to 12f. In particular, BURER2002 and PAL2004bMTS2 exceeded the safety margin for multiple instances. Overall, the DA runtimes remain lower than those of the MQLib heuristics.

## Figure Captions

**Figure 6:** Left: Progress of DAv3 cut accuracy relative to D-Wave's HS over the 20-minute time limit, separated by integer (top) and float (bottom) instance sets. Each line corresponds to an individual instance, with crosses marking the time when the best cut was found. Colors indicate the performance of the DA relative to D-Wave's HS: green for better, yellow for equal, and blue for worse. Right: Bar plot summarizing final accuracy distribution.

**Figure 7:** Progress of DAv3 solution accuracy relative to QIS3 over the 10-seconds time limit. Each line corresponds to an individual instance, with crosses marking the time when the best solution was found. Each dot corresponds to the accuracy of DAv2 on a given instance, relative to QIS3, measured at the earliest time the best cut was found across independent runs ranging from 1 to 10 seconds. Colors indicate the performance of the DA relative to QIS3: green for better, yellow for equal, and blue for worse. A progress plot for DAv2 is not possible due to the lack of the functionality to log intermediate improving cuts into a solution pool during execution. The dots of instances G11, G48, G1, and G43 for DAv2 are overlapping.

**Figure 8:** Distribution of instances by number of vertices and density for x-small and small category instances. The total number of instances is 1306. (a) Scatter plot of instances in terms of their size and density. Darker blue regions indicate a higher concentration of instances at this size and density region. (b) Histogram showing instance counts by size range; the majority of instances are below approximately 1000 variables (in the x-small category). Inset: Histogram showing instance counts by density range; the majority of instances are sparse.

**Figure 9:** Comparison of the performance of DAv2 with the best-performing MQLib heuristic on x-small and small instances across all densities. Each bar represents the proportion of instances where DAv2 yields a better cut (green), equal (yellow), or worse (blue) than the corresponding heuristic. Hashed bars indicate instances with floating-point cut values.

**Figure 10:** Distribution of all x-small and small instances over accuracy ranges, where the ratio is defined as DAv2 cut divided by that of the best-performing category heuristic. The 'tie' bar at 1.0 (yellow) shows the count of instances when both solvers found an equal cut value. The dashed line at 1.0 separates 'win' ranges (green bars) from 'loss' ranges (blue bars). Hashed bars indicate instances with floating-point cut values.

**Figure 11:** Trade-off between average accuracy and time-limit adherence across different offset values for DAv3. An offset of 3 seconds (red point) offers the best balance between runtime compliance and accuracy.

**Figure 12:** Histogram (log scale) of relevant instance counts distributed over solver runtime-to-limit ratio. The solid red line indicates the point where runtime equals the time limit, while the dashed red line marks a 10% exceedance margin that we enforced for our solvers on the majority of instances. DAv2 and MERZL999GLS remain within this margin, whereas DAv3, BURER2002, and PALUBECKIS2004bMTS2 exceed it for very few instances.

## Acronyms

| Acronym | Term | Page |
|---------|------|------|
| DAU | Digital Annealer Unit | 7 |
| HS | hybrid solver | 5 |
| Max-Cut | maximum cut | 2 |
| MQLib | Max-Cut and QUBO instances library | 5 |
| QAOA | quantum approximate optimization algorithm | 4 |
| QUBO | quadratic unconstrained binary optimization | 1 |
| DA | Digital Annealer | 2 |

## References

[1] F. Glover, G. A. Kochenberger, and Y. Du, *Applications and computational advances for solving the QUBO model*, in Springer eBooks (2022) p. 39–56.

[2] A. Lucas, *Ising formulations of many NP problems*, Frontiers in Physics **2**, 5 (2014), arXiv:1302.5843 [cond-mat.stat-mech].

[3] F. Glover, G. Kochenberger, and Y. Du, *A Tutorial on Formulating and Using QUBO Models*, arXiv:1811.11538 [cs.DS] (2018).

[4] D. Ratke, *List of QUBO formulations*, https://blog.xa0.de/post/List-of-QUBO-formulations/ (2021), accessed 2025-06-19.

[5] A. P. Punnen, ed., *The Quadratic Unconstrained Binary Optimization Problem: Theory, Algorithms, and Applications*, 1st ed. (Springer Cham, 2022) pp. XIII + 319, eBook published July 12, 2022.

[6] S. Aaronson, *The limits of quantum computers*, Scientific American (2008).

[7] H. Goto, K. Tatsumura, and A. R. Dixon, *Combinatorial optimization by simulating adiabatic bifurcations in nonlinear Hamiltonian systems*, Science Advances **5**, eaav2372 (2019), https://www.science.org/doi/pdf/10.1126/sciadv.aav2372.

[8] K. Tatsumura, M. Yamasaki, and H. Goto, *Scaling out Ising machines using a multi-chip architecture for simulated bifurcation*, Nature Electronics **4**, 208 (2021).

[9] D-Wave Quantum Inc., *Performance gains in the D-Wave Advantage2 system at the 4,400-qubit scale*, Whitepaper 14-1083A-A (D-Wave Quantum Inc., 2025) released May 12, 2025.

[10] T. Okuyama, T. Sonobe, K.-i. Kawarabayashi, and M. Yamaoka, *Binary optimization by momentum annealing*, Phys. Rev. E **100**, 012111 (2019).

[11] T. Inagaki, Y. Haribara, K. Igarashi, T. Sonobe, S. Tamate, T. Honjo, A. Marandi, P. L. McMahon, T. Umeki, K. Enbutsu, O. Tadanaga, H. Takenouchi, K. Aihara, K. ichi Kawarabayashi, K. Inoue, S. Utsunomiya, and H. Takesue, *A coherent Ising machine for 2000-node optimization problems*, Science **354**, 603 (2016).

[12] T. Honjo, T. Sonobe, K. Inaba, T. Inagaki, T. Ikuta, Y. Yamada, T. Kazama, K. Enbutsu, T. Umeki, R. Kasahara, K. ichi Kawarabayashi, and H. Takesue, *100,000-spin coherent Ising machine*, Science Advances **7**, eabh0952 (2021).

[13] H. Nakayama, J. Kovama, N. Yoneoka, and T. Miyazawa, *Third Generation Digital Annealer Technology*, Tech. Rep. (Fujitsu Laboratories, 2021) accessed: 2025-07-23.

[14] N. Mohseni, P. L. McMahon, and T. Byrnes, *Ising machines as hardware solvers of combinatorial optimization problems*, Nature Reviews Physics **4**, 363 (2022), arXiv:2204.00276 [quant-ph].

[15] M. X. Goemans and D. P. Williamson, *Improved approximation algorithms for maximum cut and satisfiability problems using semidefinite programming*, Journal of the ACM (JACM) **42**, 1115 (1995).

[16] S. Khot, G. Kindler, E. Mossel, and R. O'Donnell, *Optimal inapproximability results for MAX-CUT and other 2-variable CSPs*, SIAM Journal on Computing **37**, 319 (2007).

[17] I. Dunning, S. Gupta, and J. Silberholz, *What works best when? a systematic evaluation of heuristics for Max-Cut and QUBO*, INFORMS J. on Computing **30**, 608–624 (2018).

[18] F. Phillipson, *Fair benchmarking combinatorial optimization solvers in the era of emerging computing paradigms*, in Innovations for Community Services, Communications in Computer and Information Science, Vol. 2513, edited by S. Zielinski, G. Eichler, C. Erfurth, and G. Fahrnberger (Springer, United States, 2025) pp. 79–93, data source: 25th International Conference on Innovations for Community Services, I4CS 2025, I4CS 2025; Conference date: 11-06-2025 Through 13-06-2025.

[19] D-Wave Systems Inc., *Hybrid solver service: An overview*, https://www.dwavequantum.com/media/4bnpi53x/14-1039a-b_d-wave_hybrid_solver_service_an_overview.pdf (2020), white Paper.

[20] J. Yang, D. Wang, X. Zhao, H. Zhang, M. Gao, and L. Yang, *A Novel Solver for QUBO Problems: Performance Analysis and Comparative Study with State-of-the-Art Algorithms*, arXiv e-prints, arXiv:2506.04596 (2025), arXiv:2506.04596 [quant-ph].

[21] I. Dunning, S. Gupta, and J. Silberholz, *Mqlib: Implementations of heuristics for Max-Cut and QUBO*, (2018), accessed: 2025-07-05.

[22] Y. Ye, *Gset collection of graphs for Max-Cut benchmarking*, https://web.stanford.edu/~yyye/yyye/Gset/ (2003), accessed 2025-06-26.

[23] E. Farhi, J. Goldstone, and S. Gutmann, *A Quantum Approximate Optimization Algorithm*, arXiv:1411.4028 [quant-ph] (2014).

[24] L. Zhou, S.-T. Wang, S. Choi, H. Pichler, and M. D. Lukin, *Quantum approximate optimization algorithm: Performance, mechanism, and implementation on near-term devices*, Phys. Rev. X **10**, 021067 (2020).

[25] K. Blekos, D. Brand, A. Ceschini, C.-H. Chon, R.-H. Li, K. Pandya, and A. Summer, *A review on quantum approximate optimization algorithm and its variants*, Physics Reports **1068**, 1 (2024), a review on Quantum Approximate Optimization Algorithm and its variants.

[26] E. Farhi, J. Goldstone, and S. Gutmann, *A quantum approximate optimization algorithm applied to a bounded occurrence constraint problem*, arXiv:1412.6062 [quant-ph] (2014).

[27] B. Barak, A. Moitra, R. O'Donnell, P. Raghavendra, O. Regev, D. Steurer, L. Trevisan, A. Vijayaraghavan, D. Witmer, and J. Wright, *Beating the random assignment on constraint satisfaction problems of bounded degree*, arXiv:1505.03424 [cs.CC] (2015).

[28] J. R. McClean, S. Boixo, V. N. Smelyanskiy, R. Babbush, and H. Neven, *Barren plateaus in quantum neural network training landscapes*, Nature Communications **9**, 10.1038/s41467-018-07090-4 (2018).

[29] L. Bittel and M. Kliesch, *Training Variational Quantum Algorithms Is NP-Hard*, Phys. Rev. Lett. **127**, 120502 (2021), arXiv:2101.07267 [quant-ph].

[30] L. Bittel, S. Gharibian, and M. Kliesch, *Optimizing the depth of variational quantum algorithms is strongly QCMA-hard to approximate*, in 38th Computational Complexity Conference (CCC 2023), Leibniz International Proceedings in Informatics (LIPIcs), Vol. 264, edited by A. Ta-Shma (Schloss Dagstuhl - Leibniz-Zentrum für Informatik, Dagstuhl, Germany, 2023) pp. 34:1–34:24, arXiv:2211.12519 [quant-ph].

[31] G. G. Guerreschi and A. Y. Matsuura, *QAOA for Max-Cut requires hundreds of qubits for quantum speed-up*, Scientific Reports **9**, 10.1038/s41598-019-43176-9 (2019).

[32] S. Wang, E. Fontana, M. Cerezo, K. Sharma, A. Sone, L. Cincio, and P. J. Coles, *Noise-induced barren plateaus in variational quantum algorithms*, Nature Communications **12**, 10.1038/s41467-021-27045-6 (2021).

[33] Y. R. Sanders, D. W. Berry, P. C. Costa, L. W. Tessler, N. Wiebe, C. Gidney, H. Neven, and R. Babbush, *Compilation of fault-tolerant quantum heuristics for combinatorial optimization*, PRX Quantum **1**, 020312 (2020).

[34] Z. Cai, R. Babbush, S. C. Benjamin, S. Endo, W. J. Huggins, Y. Li, J. R. McClean, and T. E. O'Brien, *Quantum error mitigation*, Reviews of Modern Physics **95**, 045005 (2023), arXiv:2210.00921 [quant-ph].

[35] R. Hamerly, T. Inagaki, P. L. McMahon, D. Venturelli, A. Marandi, T. Onodera, E. Ng, C. Langrock, K. Inaba, T. Honjo, K. Enbutsu, T. Umeki, R. Kasahara, S. Utsunomiya, S. Kako, K.-i. Kawarabayashi, R. L. Byer, M. M. Fejer, H. Mabuchi, D. Englund, E. Rieffel, H. Takesue, and Y. Yamamoto, *Experimental investigation of performance differences between coherent Ising machines and a quantum annealer*, Science Advances **5**, 10.1126/sciadv.aau0823 (2019).

[36] K. Boothby, P. Bunyk, J. Raymond, and A. Roy, *Nert-generation topology of d-wave quantum processors (2020)*, arXiv:2003.00133 [quant-ph].

[37] P. Hauke, H. G. Katzgraber, W. Lechner, H. Nishimori, and W. D. Oliver, *Perspectives of quantum annealing: methods and implementations*, Reports on Progress in Physics **83**, 054401 (2020).

[38] C. D. Gonzalez Calaza, D. Willsch, and K. Michielsen, *Garden optimization problems for benchmarking quantum annealers*, Quantum Information Processing **20**, 10.1007/s11128-021-03226-6 (2021).

[39] D. Willsch, M. Willsch, C. D. Gonzalez Calaza, F. Jin, H. De Raedt, M. Svensson, and K. Michielsen, *Benchmarking advantage and d-wave 2000q quantum annealers with exact cover problems*, Quantum Information Processing **21**, 10.1007/s11128-022-03476-y (2022).

[40] S. Matsubara, M. Takatsu, Toshiyuki Miyazawa, T. Miyazawa, T. Shibasaki, Y. Watanabe, K. Takemoto, and H. Tamura, *Digital Annealer for High-Speed Solving of Combinatorial optimization Problems and Its Applications*, Asia and South Pacific Design Automation Conference, 667.

[41] T. Ikuta et al., *Solving the maximum cut benchmark with an optimization solver*, Research Institute for Mathematical Sciences Kokyuroku **1941**, 49 (2015), (In Japanese).

[42] F. Ma and J.-K. Hao, *A multiple search operator heuristic for the max-k-cut problem (2015)*, arXiv:1510.09156 [cs.DM].

[43] T. Huang, J. Xu, T. Luo, X. Gu, R. Goh, and W.-F. Wong, *Benchmarking quantum(-inspired) annealing hardware on practical use cases*, IEEE Transactions on Computers **72**, 1692 (2023).

[44] H. Oshiyama and M. Ohzeki, *Benchmark of quantum-inspired heuristic solvers for quadratic unconstrained binary optimization*, Scientific Reports **12**, 10.1038/s41598-022-06070-5 (2022).

[45] O. Seker, N. Tanoumand, and M. Bodur, *Digital annealer for quadratic unconstrained binary optimization: A comparative performance analysis*, Appl. Soft Comput. **127**, 10.1016/j.asoc.2022.109367 (2022).

[46] Gurobi Optimization, LLC, *Gurobi Optimizer Reference Manual* (2023).

[47] T. Achterberg, *SCIP: solving constraint integer programs*, Mathematical Programming Computation **1**, 1 (2009).

[48] S. Burer, R. D. C. Monteiro, and Y. Zhang, *Rank-two relaxation heuristics for max-cut and other binary quadratic programs*, SIAM J. Optim. **12**, 503 (2002).

[49] G. Palubeckis, *Multistart tabu search strategies for the unconstrained binary quadratic optimization problem*, Annals of Operations Research **131**, 259 (2004).

[50] J.-R. Jiang, Y.-C. Shu, and Q.-Y. Lin, *Benchmarks and recommendations for quantum, digital, and GPU annealers in combinatorial optimization*, IEEE Access **12**, 125014 (2024).

[51] M. Kowalsky, T. Albash, I. Hen, and D. A. Lidar, *3-regular three-XORSAT planted solutions benchmark of classical and quantum heuristic optimizers*, Quantum Science and Technology **7**, 025008 (2022), arXiv:2103.08464 [quant-ph].

[52] C. Münch, F. Schimkel, S. Zielinski, and S. Walter, *Transformation-Dependent Performance-Enhancement of Digital Annealer for 3-SAT*, arXiv e-prints, arXiv:2312.11645 (2023), arXiv:2312.11645 [quant-ph].

[53] Y.-T. Kao, J.-L. Liao, and H.-C. Hsu, *Solving Combinatorial Optimization Problems on Fujitsu Digital Annealer*, arXiv:2311.05196 [quant-ph] (2023).

[54] D. Leib, T. Seidel, S. Jäger, R. Heese, C. Jones, A. Awasthi, A. Niederle, M. Bortz, and et al., *An optimization case study for solving a transport robot scheduling problem on quantum-hybrid and quantum-inspired hardware*, Scientific Reports **13**, 18743 (2023).

[55] C. Lee, P.-H. Wang, and Y. J. Tseng, *Digital annealing optimization for natural product structure elucidation*, Briefings in Bioinformatics **25**, bbae600 (2024).

[56] A. A. Jha, E. L. Stoyanoff, G. Khundzakishvili, P. Kairys, H. Ushijima-Mwesigwa, and A. Banerjee, *Digital annealing route to complex magnetic phase discovery*, in 2021 International Conference on Rebooting Computing (ICRC) (2021) pp. 119–123.

[57] A. Maruo, H. Igarashi, H. Oshima, and S. Shimokawa, *Optimization of planar magnet array using digital annealer*, IEEE Transactions on Magnetics **56**, 1 (2020).

[58] J. Dornemann, S. Shaglel, M. Kliesch, and A. Taraz, *A hybrid quantum-inspired and deep learning approach for the capacitated vehicle routing problem with time windows*, in THE 19TH LEARNING AND INTELLIGENT OPTIMIZATION CONFERENCE (2025).

[59] S. Shaglel and M. Kirsch, *DA Maxcut Benchmark (DAMB)*, https://github.com/SalwaShagiel/DAMB (2025).

[60] H. Cohn and M. Fielding, *Simulated annealing: Searching for an optimal temperature schedule*, SIAM Journal on Optimization **9**, 779 (1999), https://doi.org/10.1137/S1052623497327651.

[61] S. Chen, J. S. Rosenthal, A. Dote, H. Tamura, and A. Sheikholeslami, *Optimization via rejection-free partial neighbor search*, Statistics and Computing **33**, 131 (2023).

[62] S. Chen, J. S. Rosenthal, A. Dote, H. Tamura, and A. Sheikholeslami, *Sampling via rejection-free partial neighbor search*, Communications in Statistics - Simulation and Computation **54**, 837 (2025), https://doi.org/10.1080/03610918.2023.2266157.

[63] A. Lipowski and D. Lipowska, *Roulette-wheel selection via stochastic acceptance*, Physica A: Statistical Mechanics and its Applications **391**, 2193 (2012).

[64] Fujitsu, *Digital annealer api documentation*, https://portal.aispf.global.fujitsu.com/apidoc/da/en/index.html, accessed: 2025-07-22.

[65] J. Beasley, *Or-library: A collection of test instances for or problems* (1990).

[66] T. Koch, A. Martin, D. Rehfeldt, and S. Voss, *Steinlib: A library for steiner tree problems*.

[67] D. Johnson and M. Trick, eds., *Cliques, Coloring, and Satisfiability: Second DIMACS Implementation Challenge*, DIMACS Series in Discrete Mathematics and Theoretical Computer Science (1993).

[68] *Seventh DIMACS implementation challenge: Semidefinite and related optimization problems* (2000).

[69] *11th dimacs implementation challenge: Steiner tree problems* (2013).

[70] G. Reinelt, *TSPLIB - a traveling salesman problem library*, ORSA Journal on Computing **3**, 376–384 (1991).

[71] A. Wiegele, *Big Mac library: Max-Cut and binary quadratic programming instances* (2007).

[72] J. Culberson, *Flat graph generator*.

[73] A. Hagberg, P. Swart, and D. Schult, *NetworkX - Python package for complex network analysis* (2008).

[74] G. Rinaldi, *Rudy: A Rudimental Graph Generator* (1995).

[75] P. Merz and B. Freisleben, *Genetic algorithms for binary quadratic programming*, in Proceedings of the 1st Annual Conference on Genetic and Evolutionary Computation - Volume 1, GECCO'99 (Morgan Kaufmann Publishers Inc., San Francisco, CA, USA, 1999) p. 417–424.
