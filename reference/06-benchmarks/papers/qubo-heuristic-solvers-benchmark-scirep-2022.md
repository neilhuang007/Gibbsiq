# Benchmark of quantum-inspired heuristic solvers for quadratic unconstrained binary optimization

**Hiroki Oshiyama** & **Masayuki Ohzeki**

Graduate School of Information Sciences, Tohoku University, Sendai 980-8579, Japan. Institute of Innovative Research, Tokyo Institute of Technology, Yokohama 226-8503, Japan. Sigma-1 Co., Ltd., Tokyo 108-0075, Japan.

*Email: hiroki.oshiyama.e@tohoku.ac.jp*

---

## Abstract

Recently, inspired by quantum annealing, many solvers specialized for unconstrained binary quadratic programming problems have been developed. For further improvement and application of these solvers, it is important to clarify the differences in their performance for various types of problems. In this study, the performance of four quadratic unconstrained binary optimization problem solvers, namely D-Wave Hybrid Solver Service (HSS), Toshiba Simulated Bifurcation Machine (SBM), Fujitsu Digital Annealer (DA), and simulated annealing on a personal computer, was benchmarked. The problems used for benchmarking were instances of real problems in MOLib, instances of the SAT-UNSAT phase transition point of random not-all-equal 3-SAT (NAE 3-SAT), and the Ising spin glass Sherrington-Kirkpatrick-Ising-Sherrington-Kirkpatrick (SK) model. Concerning MOLib instances, the HSS performance ranked first; for NAE 3-SAT, DA performance ranked first; and regarding the SK model, SBM performance ranked first. These results may help understand the strengths and weaknesses of these solvers.

---

## Introduction

Quantum annealing (QA), which is a quantum heuristic algorithm for solving combinatorial optimization problems, has attracted a great deal of attention because it is implemented using real quantum systems by D-Wave Systems Inc. At becoming more powerful than classical algorithms such as simulated annealing (SA). In use the current D-Wave QA device, a combinatorial optimization problem must be mapped to a quadratic unconstrained binary optimization (QUBO) problem. QUBO is an optimization problem of binary variables $x_i \in \{0, 1\}$, where $i = \{1, 2, \ldots, N\}$, and the objective function to be minimized is defined as

$$E(x) = \sum_{i,j} Q_{ij} x_i x_j \tag{1}$$

where $Q_{ij}$ is a real number called QUBO matrix element. In general, QUBO is NP-hard, and many NP-complete problems and combinatorial optimization problems are mapped to QUBO.

Although current QA devices have limited capability owing to hardware implementation limitations, in anticipation of future developments of QA devices, methods using QUBO models for solving real-world problems in a variety of fields have been actively studied. Inspired by this trend, several sophisticated heuristic QUBO solvers have been developed and commercialized. It is highly non-trivial to determine whether a particular algorithm is more powerful than another because the performance of heuristic algorithms varies depending on the target problem. For successful application to real-world problems and further development of these QUBO solvers, it is necessary to clarify the strengths and weaknesses of each solver for various types of QUBO problems.

In this study, we benchmarked the performance of three commercialized QUBO solvers including one using a real QA device: D-Wave Hybrid Solver Service (HSS), Toshiba Simulated Bifurcation Machine (SBM), and Fujitsu Digital Annealer (DA). In order to understand the characteristics of the solvers, we benchmark various types of problems, including Ising spin glass problems and real-world problems. This is in contrast to a similar benchmark study reported recently, which used only a single kind of constraint satisfaction problem (specifically, 3-regular 3-XOR-SAT). While in Ref., the use-dependence of the time to obtain an optimal solution with a certain probability is analyzed in detail, in this study, the performance of the solver is evaluated by comparing the value of the cost function obtained for a given execution time. Such a performance evaluation will be helpful in application cases where approximate solutions are acceptable.

The remainder of this paper is organized as follows. In "QUBO solvers" section, we briefly explain the solvers benchmarked. In "Problem instances for benchmarking" section, the definition of the problem instances used

---

## QUBO solvers

In this section, we briefly explain the four solvers used in this study. Three commercial solvers were benchmarked. For comparison, we also experimented with SA on a personal computer.

### D-Wave Hybrid Solver Service (HSS)

The first solver is HSS, commercialized by D-Wave Systems Inc. This solver is a so-called quantum-classical hybrid algorithm that employs QA as an accelerator. Note that the actual implementation of the algorithm is not open to the public. Thus, it is unclear how QA is used internally. We used HSS's Leap cloud. We accessed HSS via Leap cloud.

### Toshiba Simulated Bifurcation Machine (SBM)

The second solver is SBM, commercialized by Toshiba. The QA inspired algorithm of SBM, so-called simulated bifurcation (SB) algorithm, uses the adiabatic time evolution of Kerr nonlinear parametric oscillators. The dynamics in the classical limit of KPOs can be quickly computed in classical computers by solving the independent equations of motion in parallel. To overcome accuracy degradation caused by analog errors due to the use of continuous variables, a variant of the SB algorithm called ballistic SB (bSB) algorithm was developed, which mitigates the analog error by discretizing the potential term of the equation of motion. As a further improvement of the bSB algorithm, the discrete SB (dSB) algorithm was also developed, which reduces the analog error by discretizing the potential term of the bSB algorithm. We use SBM evaluation version 1.5.1 which is in publicly available), that uses dSB algorithm and can manage all-to-all coupling of up to $10^6$ variables and $10^8$ nonzero couplings. Parallelization is 80 or 160 per GPU. In this study, we used the annealing solver hyper-parameters automatically searched by the solver.

### Fujitsu Digital Annealer (DA)

The third solver is DA, computerized by Fujitsu. DA uses an SA-specific hardware architecture to accelerate the parallel tempering Markov chain Monte Carlo (MCMC) calculation. Although DA does not use quantum algorithms, it is inspired by D-Wave devices in the sense that the hardware is specialized for QUBO solving. We used FujitsuDA2PT solver, which can manage all-to-all coupling of up to 8192 variables. We accessed DA via DA Center Japan.

### Simulated Annealing (SA)

For comparison with these commercial solvers, we ran SA using the open-source software D-Wave neal, version 0.5.7, on a personal computer with Ubuntu 20.04.3 LTS and Python 3.8.2. D-Wave neal implements SA with MCMC without parallel tempering method. The CPU used in the experiment was Intel Core i9-9900K and single-threaded runs were performed.

---

## Problem instances for benchmarking

In this section, we explain the three problem sets used in the conducted benchmarking.

### MOLib repository instances

We used the same set of 45 problems used in the benchmarks presented in HIB. white paper. This problem set is extracted from the MOLib repository, and some of the problems have their origin in real-world problems, such as image segmentation. This problem set was reported to be time-consuming to solve because of all the heuristics contained in the MOLib library. Concerning benchmarking, a 20-minute run is recommended for each problem. The 45 problems are uniformly classified into nine classes: three classes according to size: small: $N \le 2500$, medium: $2500 < N \le 10000$, and large: $5000 < N \le 10000$), and three classes according to edge density (sparse: $d < 0.1$, medium: $0.1 \le d \le 0.5$, and dense: $0.5 < d$), where $d$ is the number of edges in a complete graph of the same size.

### Not-All-Equal 3-SAT

Satisfiability problem (SAT) is one of the most fundamental NP-hard problems and therefore it is good benchmark problem for heuristic solvers. Not-all-equal 3-SAT (NAE 3-SAT) is a variant of the Boolean SAT problem. NAE 3-SAT requests a truth assignment and at least one literal to be false in each clause with three literals. The cost function of a random NAE 3-SAT with $N$ variables and $M$ clauses is expressed in a straightforward manner in the Ising model with $x_i \in \{-1, 1\}$,

$$E(\sigma) = \frac{1}{4} \sum_{m=1}^M (s_m 1 s_m 3 y_m s_m 2 + s_m 2 s_m 3 y_m s_m 3 + s_m 3 s_m 1 y_m s_m 1 + 1). \tag{2}$$

where $i_m \in \{1, 2, \ldots, N\}$ and $c_m \in \{-1, 1\}$ for $1 \le m \le M$ and $1 \le 1 \le 3$ are random variables that follow a discrete uniform distribution. For instance, $c_m = -1$ corresponds to the negation of the $i$-th Boolean variable in clause $m$. If the minimum of $E(\sigma)$ in Eq. (2) is 0 for a given formula, it is satisfiable (SAT); otherwise, it is unsatisfiable (UNSAT). The QUBO formulation can be easily obtained from this Ising formulation by the variable transformation $x_i = (1 + \sigma_i) / 2$. Because NAE 3-SAT has such benchmark problem for QUBO solvers among SAT variants, as it is one of the most difficult to solve. In this study, we used randomly generated instances with this critical clause-to-variable ratio for benchmarking.

### Sherrington-Kirkpatrick model

The Sherrington-Kirkpatrick (SK) model is an Ising spin glass model with infinite spatial dimensions. The cost function of $N$ variables with no external field is expressed as

$$E(\sigma) = \frac{1}{\sqrt{N}} \sum_{i<j} J_{ij} \sigma_i \sigma_j, \tag{3}$$

where $J_{ij}$ is a random Gaussian variable. As previously explained, the QUBO formulation can be easily obtained. The mean field analysis shows that the energy landscape of the SK model has a many-valley structure separated by asymptotically infinitely large energy barriers, which implies that it is extremely difficult to find the exact solution. In this study, we used randomly generated instances with $J_{ij}$ presenting zero mean and unity standard deviation for benchmarking.

---

## Results

In this section, we present benchmarking results for each of the three problem sets introduced in the previous section. In the results shown below, the network time required to send the instance and receive the result was ignored in the measurement of execution time. Regarding HSS, the number of seconds specified in time_limit was used as the execution time. For SBM, the time specified in timeout was used as the execution time. Concerning DA, there was no parameter to specify the execution time directly, so total_elapsed_time recorded in the response file was used as the execution time. Finally, for SA with D-Wave neal, we measured the time taken for the sample function to finish.

### MOLib instances

First, we present the results of a 5-min experiment of the instances from the MOLib repository. For HSS and SBM, the execution time was set to 5 min. For DA, number_replicas was set to 128 and number_iterations was adjusted for each instance so that the deviation of execution time in 5 min was within 20 s. Concerning SA, num_sweeps was adjusted for each instance such that the execution time was 5 min.

---

**Figure 1.** Number of wins (left axis) and average score (right axis) for a 5-min experiment of MOLib instances. Each panel shows the result for a class categorized by problem size. (a) Small, (b) Medium, and (c) Large; (d) Total number of wins and average score for all instances. The score for each instance is defined by Eq. (4). In calculating the average score, instance g000644 was ignored due to absence of data for DA.

$$E(\sigma) = \frac{1}{\sqrt{N}} \sum_{i<j} |J_{ij}| \sigma_i \sigma_j, \tag{3}$$

where $J_{ij}$ is a random Gaussian variable. As previously explained, the QUBO formulation can be easily obtained. The mean field analysis shows that the energy landscape of the SK model has a many-valley structure separated by asymptotically infinitely large energy barriers, which implies that it is extremely difficult to find the exact solution. In this study, we used randomly generated instances with $J_{ij}$ presenting zero mean and unity standard deviation for benchmarking.

---

### Results

| Input | Size | Density | HSS | SBM | DA | SA |
|-------|------|---------|-----|-----|----|----|
| g000989 | 2319 | 0.00086 | 1.0 | 1.0 | 1.0 | 0.998708 |
| g003215 | 2306 | 0.00093 | 1.0 | 0.999457 | 0.998193 | 0.997983 |
| g001269 | 2294 | 0.0017 | 1.0 | 1.0 | 1.0 | 0.999847 |
| g000121 | 2031 | 0.0038 | 1.0 | 1.0 | 0.985010 | 0.999503 |
| g002340 | 2345 | 0.044 | 1.0 | 1.0 | 0.999213 | 1.0 |

**Table 1.** Values of score, defined by Eq. (4) for small and sparse classes. The first row shows the instance name, the second row presents the number of variables, the third row contains the edge density, and the fourth and subsequent rows show the results for each solver. The values are computed in single precision from the obtained solution of binary variables; they are shown with six decimal places. The best solutions obtained in this benchmarking are shown in bold.

| Input | Size | Density | HSS | SBM | DA | SA |
|-------|------|---------|-----|-----|----|----|
| g000132 | 2153 | 0.11 | 1.0 | 0.999958 | 0.999945 | 0.999974 |
| g000524 | 2218 | 0.14 | 1.0 | 1.0 | 1.0 | 1.0 |
| g002586 | 2879 | 0.16 | 1.0 | 1.0 | 0.999102 | 0.999899 |
| g001327 | 2318 | 0.3 | 1.0 | 1.0 | 0.999300 | 0.999928 |
| g001469 | 2412 | 0.46 | 1.0 | 0.999624 | 0.998105 | 0.999911 |

**Table 2.** Results for small and medium classes, same as Table 1.

| Input | Size | Density | HSS | SBM | DA | SA |
|-------|------|---------|-----|-----|----|----|
| g002600 | 3432 | 0.85 | 1.0 | 0.999999 | 0.999505 | 0.999976 |
| g000969 | 2453 | 0.86 | 1.0 | 1.0 | 0.995138 | 0.999645 |
| g002898 | 2041 | 0.86 | 1.0 | 1.0 | 1.0 | 0.999996 |
| g001581 | 2383 | 0.86 | 0.999999 | 1.0 | 0.999640 | 1.000000 |
| g000788 | 2342 | 0.88 | 1.0 | 0.999869 | 0.999492 | 0.999539 |

**Table 3.** Results for small and dense classes, same as Table 1.

| Input | Size | Density | HSS | SBM | DA | SA |
|-------|------|---------|-----|-----|----|----|
| g000377 | 3398 | 0.00069 | 0.998763 | 0.999890 | 1.0 | 0.998333 |
| g002569 | 2815 | 0.0011 | 1.0 | 0.999439 | 0.983877 | 0.998564 |
| g001086 | 3706 | 0.0016 | 0.998313 | 0.996673 | 0.983668 | 1.0 |
| g001337 | 3450 | 0.051 | 0.999975 | 0.999923 | 1.0 | 0.999931 |
| g000283 | 3364 | 0.072 | 0.999946 | 0.999905 | 0.997073 | 1.0 |

**Table 4.** Results for medium and sparse classes, same as Table 1.

| Input | Size | Density | HSS | SBM | DA | SA |
|-------|------|---------|-----|-----|----|----|
| g002512 | 4731 | 0.12 | 0.999913 | 0.999861 | 1.0 | 0.999980 |
| g000802 | 3856 | 0.13 | 0.999990 | 1.0 | 0.988419 | 0.999619 |
| g003659 | 3447 | 0.14 | 0.999973 | 0.999939 | 1.0 | 0.999962 |
| g002332 | 3181 | 0.22 | 0.999991 | 0.999996 | 0.999156 | 1.0 |
| g002034 | 3328 | 0.35 | 1.0 | 0.999997 | 0.999281 | 0.999979 |

**Table 5.** Results for medium and medium classes, same as Table 1.

| Input | Size | Density | HSS | SBM | DA | SA |
|-------|------|---------|-----|-----|----|----|
| g003198 | 3972 | 0.74 | 1.0 | 0.999956 | 0.999616 | 0.999979 |
| g002207 | 3677 | 0.74 | 1.0 | 1.0 | 1.0 | 0.999934 |
| g001913 | 3165 | 0.75 | 1.0 | 0.999786 | 0.999333 | 0.999643 |
| g001393 | 3438 | 0.83 | 0.999987 | 1.0 | 1.0 | 0.999886 |
| g002370 | 3884 | 0.84 | 0.999716 | 0.999843 | 0.997744 | 1.0 |

**Table 6.** Results for medium and dense classes, same as Table 1.

| Input | Size | Density | HSS | SBM | DA | SA |
|-------|------|---------|-----|-----|----|----|
| miqseg-216041 | 7724 | 0.00039 | 1.0 | 0.999919 | 0.996163 | 0.995890 |
| miqseg-373028 | 7435 | 0.00049 | 1.0 | 0.999522 | 0.989190 | 0.998111 |
| i301833 | 6831 | 0.00059 | 1.000000 | 1.0 | 0.999489 | 0.999998 |
| g000644 | 10680 | 0.0016 | 0.999307 | 1.0 |  | 0.999752 |
| g00476 | 8000 | 0.002 | 0.999457 | 0.999766 | 1.0 | 0.999860 |

**Table 7.** Results for large and sparse classes, same as Table 1. For input g001883, HSS and SBM had almost the same value of the cost function, while the solution configurations were truly different from each other. The result of DA for input g000644 is blank because DA can only manage 8192 variables.

| Input | Size | Density | HSS | SBM | DA | SA |
|-------|------|---------|-----|-----|----|----|
| g002312 | 8393 | 0.19 | 0.999557 | 0.999834 | 1.0 | 0.999930 |
| g002563 | 6279 | 0.19 | 0.999842 | 0.999966 | 1.0 | 0.999945 |
| g000495 | 5438 | 0.21 | 0.999941 | 0.999980 | 1.0 | 0.999958 |
| g002204 | 5368 | 0.44 | 1.0 | 1.0 | 1.0 | 0.999903 |
| g000303 | 5046 | 0.45 | 0.999954 | 0.999966 | 1.0 | 0.999983 |

**Table 8.** Results for large and medium classes, same as Table 1.

| Input | Size | Density | HSS | SBM | DA | SA |
|-------|------|---------|-----|-----|----|----|
| g002527 | 5378 | 0.59 | 0.999949 | 0.999574 | 1.0 | 0.999885 |
| g001345 | 5066 | 0.74 | 0.999252 | 0.999603 | 0.473147 | 1.0 |
| p700-2 | 7801 | 0.8 | 0.999992 | 0.999748 | 1.0 | 0.999563 |
| g002300 | 5038 | 0.94 | 0.999970 | 0.999988 | 1.0 | 0.999995 |
| g001651 | 5819 | 0.97 | 0.999949 | 0.999913 | 1.0 | 0.999930 |

**Table 9.** Results for large and dense classes, same as Table 1.

Figure 1 shows the number of wins for each solver; this number was counted when the solver obtained the best solution. If there were more than one solver with the best solution, the number of wins was counted for all of them. The total result for all classes was that HHS won most of the problems (22), followed by DA (20), SBM (16), and SA (2). The results for each class classified by size show that HSS won the most for the small class, while DA won the most for the medium and large classes. The results for each class classified by edge density show that, for Sparse, HSS won the most; for Dense, SBM won the most. The number of wins of SA was only 2 at most, and most of the time, it was 0 or 1 for each of the nine classes.

Furthermore, we evaluate the quality of the obtained solution using a score defined as the ratio of the value of cost function

$$(E_{solver} = [E_{HSS}, E_{SBM}, E_{DA}, E_{SA}]) \text{ to the best value obtained in this experiment}$$

$$E_{b} = \min (E_{HSS}, E_{SBM}, E_{DA}, E_{SA}).$$

$$S_{solver} = E_{solver} / E_b \text{ (solver } \in \{\text{HSS, SBM, DA, SA}\}).$$

**Table 10.** The lowest values of cost function found in this benchmarking for MOLib instances.

| Input | Value of cost function | Solvers |
|-------|------------------------|---------|
| g000989 | -2332 | HSS, SBM, DA |
| g003215 | -821.734 | HSS |
| g001269 | -45,661 | HSS, SBM, DA |
| g000121 | -41,680.2 | HSS, SBM |
| g002340 | -2,000,460 | HSS, SBM, SA |
| g000132 | -188,363.1 | HSS |
| g000524 | -3,335,388 | HSS, SBM, DA, SA |
| g002586 | -7,161,694 | HSS, SBM |
| g001327 | -9,287,492 | HSS, SBM |
| g001469 | -1.42274e+07 | HSS |
| g002600 | -41,194.45 | HSS |
| g000969 | -6,647,406 | HSS, SBM |
| g002898 | -1.22764486+07 | HSS, SBM, DA |
| g001581 | -740,413.1 | SBM |
| g000788 | -1,962,898 | HSS |
| g000377 | -445,529 | DA |
| g002569 | -5,084731e+08 | HSS |
| g001086 | -3819,935 | SA |
| g001337 | -4,634,450 | DA |
| g000283 | -337,340.8 | SA |
| g002312 | -327,679.6 | DA |
| g000802 | -2,819,460 | SBM |
| g003659 | -3,782,885 | DA |
| g002332 | -4,586,683 | SA |
| g002034 | -698,788.1 | HSS |
| g003198 | -1.32365e+08 | HSS |
| g002207 | -6,781,175 | HSS, SBM, DA |
| g001913 | -1,177,302 | HSS |
| g001393 | -588,732 | SBM, DA |
| g002370 | -5.62536e+07 | SA |
| miqseg-216041 | -9,572,357 | HSS |
| miqseg-373028 | -1.35626486+07 | HSS |
| i301833 | -403,013.1 | SBM |
| g000644 | -132,420 | SBM |
| g000376 | -106,294 | DA |
| g002312 | -2.867646e+07 | DA |
| g002563 | -5.44186e+07 | DA |
| g000495 | -1.63816726+07 | DA |
| g002208 | -1.229112e+08 | HSS, SBM, DA |
| g000303 | -8.260626e+07 | DA |
| g002527 | -8,261,389 | DA |
| g001345 | -4.011876e+07 | SA |
| p700-2 | -1.824996e+07 | DA |
| g002300 | -9.449276e+07 | DA |
| g001651 | -150,005.8 | DA |

---

Tables 1, 2, 3, 4, 5, 6, 7, 8 and 9 show the score for each instance, and Figure 1 shows the average of the scores for Small, Medium, and Large classes, and for all instances. The original lowest values of the cost function found in this benchmarking are listed in Table 10. The average scores of HSS and SBM are almost identical and higher than other solvers. This implies that HSS and SBM have stable performance on a wide range of problems. On the other hand, DA has an excellent solution for the instance g001345, which is why the average score drops significantly in the Large class. In addition, in the Small and Medium classes, the average score of DA is about 0.01 lower than the other solvers. This implies that DA is slightly less stable, because even for SA, which has the fewest wins, the difference in average score from HSS is within 0.001.

---

## NAE 3-SAT instances

Next, we present the results for the random NAE 3-SAT instances with a number of variables $N = 8192$ and a number of clauses $M = 17285$, i.e., instances with $\alpha = M / N = 2.11$. Figure 2a shows the average of randomly generated instances of the cost function as a function of the execution time. It is shown in the main text for the time metric of each solver. As previously shown in Figure 2b, results of 100 s, DA presented the lowest value of energy and then HSS and SBM showed lower energy than DA. After a long time calculation at around 100-600 s, DA presented the lowest value of energy, still not as good as SBM and HSS presented the highest level. In the result of 100 s run of DA, Interestingly, the performance of SBM and SA is almost identical for a wide range of execution time.

shows the results of six different instances. SBM clearly outperformed the other solvers, achieving the best solutions at the 100 s mark, with little energy change for longer runs. HSS and DA showed almost the same time dependence, although HSS provided a slightly better solution. It is interesting that this pair, SBM and SA, that exhibits similar performance in NAE 3-SAT instances. In runs longer than 600 s, SA obtained a good solution as HSS and showed improvement over HSS for some instances. However, due to the all-to-all coupling, its pre-processing calculation was expensive, requiring at least approximately 500 s for the total calculation time.

---

**Figure 2.** Value of the cost function per class as a function of the execution time, obtained for NAE 3-SAT with a number of variables $N = 8192$ and a number of clauses $M = 17285$, i.e., $\alpha = M / N = 2.11$. Each data point was obtained from an independent run. See the main text for the time metric of each solver. (a) Average of ten instances. The error bars denote standard deviation. For DA and SA, the execution time was also averaged. (b) Results for ten different instances.

---

**Figure 3.** Value of cost function per variable as a function of the execution time, obtained for the SK model with a number of variables $N = 8192$ and $l = 1$. Each data point was obtained from an independent run. See the main text for the time metric of each solver. (a) Average of ten instances. The error bars denote standard deviation. For DA and SA, the execution time was also averaged. (b) Results for six different instances.

---

### SK model

Finally, we present the results for the SK model with 8192 variables. As with the NAE 3-SAT instances, the experiments were performed by varying the execution time. Figure 3a shows the average of six randomly generated instances of the cost function as a function of the execution time. As a reference, Fig. 3b

---

## Listings

**Listing 1.** Python program that generate the NAE 3-SAT instances used in this study in Ising formulation. Ten seed values from 0 to 9 were used.

```python
import numpy
import random
import itertools

seed = 0 #in range(10)
random.seed(a=seed)

N = 8192  # number of variables
M = 17285 # number of clauses
variables = range(0, N)
signs = range(-1, 2, 2)
J = {} # Ising interaction

for i in range(M):
    clause = random.sample(variables, 3)
    negations = random.choices(signs, k=3)
    v_pairs = itertools.combinations(clause, 2)
    s_pairs = itertools.combinations(negations, 2)
    for pair, sign in zip(v_pairs, s_pairs):
        J[pair] = J.get(pair, 0) + numpy.prod(sign)
```

**Listing 2.** Python program that generate the SK model instances used in this study in Ising formulation. Six seed values from 1 to 6 were used.

```python
import numpy
import random

seed = 0 #in range(6)
random.seed(a=seed)

N = 8192  # number of variables
J = {} # Ising interaction

for i in range(N):
    for j in range(i+1, N):
        J[(i, j)] = random.gauss(0, 1)/numpy.sqrt(N)
```

shows the results of six different instances. SBM clearly outperformed the other solvers, achieving the best solutions at the 100 s mark, with little energy change for longer runs. HSS and DA showed almost the same time dependence, although HSS provided a slightly better solution. It is interesting that this pair, SBM and SA, that exhibits similar performance in NAE 3-SAT instances. In runs longer than 600 s, SA obtained a good solution as HSS and showed improvement over HSS for some instances. However, due to the all-to-all coupling, its pre-processing calculation was expensive, requiring at least approximately 500 s for the total calculation time.

---

## Discussion and conclusion

We benchmarked heuristic QUBO solvers, HSS, SBM, DA, and SA, using the instances from the MOLib repository, random NAE 3-SAT, and the SK model. Benchmarking with problems of various origins revealed some of the characteristics of the strengths and weaknesses of each solver. For MOLib instances, which are a set of various problem instances including real-world problems, HSS showed the best performance on average, and SBM also showed stable performance that was not so different from HSS. DA outperformed other solvers on large instances, but it gave slightly poor solutions to some instances. It is rather natural result that the performance of DA varied depending on the instances because instances in general, and it is somewhat surprising that HSS and SBM showed stable performance. In this experiment, with a run time of 5 min, the difference in the value of cost function of the obtained solutions is often less than 0.01%, which is probably negligible in some application cases. Therefore, a possible direction for further study is to investigate how the results change in experiments with shorter run times. For random NAE 3-SAT instances at the SAT-UNSAT transition point, which is a typical hard optimization problem, DA performed best for most of the execution time steps, while SBM and SA at almost the same level, and HSS was the worst. It is believed that local search methods such as the parallel tempering method used in DA do not work well for SAT instances. Regarding the SAT-UNSAT transition point that have few solutions, there is probably no efficient algorithm. Therefore, the result that DA still performed best implies that other solvers are also not particularly effective, which is not surprising that SBM, rather than DA, showed outstanding performance as opposed to the case of NAE 3-SAT. It

is an important challenge to understand the characteristics of each solver found in this study from the viewpoint of their algorithm and hardware architecture.

---

## Data availability

All other data used in this study are available from the corresponding authors upon reasonable request. The problem instances of MOLib is available from the MOLib repository. The NAE 3-SAT and SK model instance was generated by the python program shown in Listings 1 and 2 with Python 3.8.2 on Ubuntu20.04.3 LTS.

Received: 6 September 2021; Accepted: 14 January 2022
Published online: 09 February 2022

---

## References

1. Aarts, E. & Ausiuam adiabatic evolution algorithm applied to random instances of an np-complete problem. *Science* 292, 472–475. https://doi.org/10.1126/science.1057726 (2001).
2. Dia, & Siddharth, B. C. Colloquium: Quantum annealing and analog quantum computation. *Rev. Mod. Phys.* 80, 1061–1081. https://doi.org/10.1103/RevModPhys.80.1061 (2008).
3. Johnson, M. et al. Quantum annealing with manufactured spins. *Nature* 473, 194–198. https://doi.org/10.1038/nature10012 (2011).
4. Harris, T. D. et al. Phase transitions in a programmable quantum spin glass processor. *Science* 361, 162–165. https://doi.org/10.1126/science.aat2025 (2018).
5. Salihoglu, S., Cirac, C. D. & Bosch, N. E. Optimization by simulated annealing. *Science* 220, 671–680. https://doi.org/10.1126/science.220.4598.671 (1983).
6. Fu, Y. & Anderson, P.W. Application of statistical mechanics to np-complete problems in combinatorial optimization. *J. Phys. A:* Math. Gen. 15, 3241–3253. https://doi.org/10.1088/0305-4470/15/10/028 (1986).
7. Barahona, F. On the computational complexity of Ising spin glass models. *J. Phys. A:* Math. Gen. 15, 3241–3253. https://doi.org/10.1088/0305-4470/15/10/028 (1982).
8. Lucas, A. Ising formulations of many np problems. *Front. Phys.* 2, 5. https://doi.org/10.3389/fphy.2014.00005 (2014).
9. Perdomo-Ortiz, A., Dickson, N., Drew-Brook, M., Rose, G. & Aspuru-Guzik, A. Finding low-energy conformations of lattice protein models by quantum annealing. *Sci. Rep.* 2, 571. https://doi.org/10.1038/srep00571 (2012).
10. Cessac, S., Zamora, E. P., Lidar, D. A. & Aspuru-Guzik, A. Adiabatic quantum algorithm for search engine ranking. *Science* 319, 787. https://doi.org/10.1126/science.1052242 (2010).
11. Babbush, R., Love, P. J. & Aspuru-Guzik, A. Adiabatic quantum simulation of quantum chemistry. *Sci. Reports* 4, DOI:https://doi.org/10.1038/srep06603 (2014).
12. Venturelli, D., Marchand, D. J. I. & Rojo, G. Quantum annealing implementation of job-shop scheduling (2016). 1506.08479.
13. More, A., Job, J. T., Lidar, D. & Spiropulu, M. Solving a Higgs optimization problem with quantum annealing for machine learning. *Nature* 550, 375. https://doi.org/10.1038/nature24370 (2017).
14. Benedetti, M., Realpe-Gómez, J., Biswas, R. & Perdomo-Ortiz, A. Quantum-assisted learning of hardware-embedded probabilistic graphical models. *Nat. Phys.* 13, 1149–1152. https://doi.org/10.1038/nphys4273 (2017).
15. Li, R. Y., Di Felice, R., Rohs, R. & Lidar, D. A. Quantum annealing versus classical machine learning applied to a simplified computational biology problem. *NPJ Quantum Inf.* 4, 14. https://doi.org/10.1038/s41534-018-0060-8 (2018).
16. D-wave hybrid solver service. An overview. https://www.dwavesys.com/sites/default/files/14-1038A_A_D-Wave_Hybrid_Solver_Service_An_Overview.pdf.
17. Lucas, A. Ising formulations of many np problems. *Science* 354, 603–606. https://doi.org/10.1126/science.aah4243 (2016).
18. Goto, H., Tatsumura, K. & Dixon, A. R. Combinatorial optimization by simulating adiabatic bifurcation on nonlinear Hamiltonian systems. *Sci. Adv.* https://doi.org/10.1126/sciadv.aay2372 (2019).
19. Goto, H. et al. Physics-inspired optimization for quadratic unconstrained binary problems using a digital annealer. *Front. Phys.* 7, 48. https://doi.org/10.3389/fphy.2019.00048 (2019).
20. Kawaba, M., Aihara, T., Han, T. & Lidar, D. A 3-regular 3-xorsat planted solutions benchmark of classical and quantum heuristic solvers. *arXiv* preprint arXiv:1908.02319 (2019).
21. D-wave hybrid solver service a advantage. Technology update. https://www.dwavesys.com/sites/default/files/14-1038A_A_D-Wave_Hybrid_Solver_Service_A_Advantage_Technology_Update.pdf.
22. Goto, H. Bifurcation-based adiabatic quantum computation with a nonlinear oscillator network. Toward quantum soft computing. *Sci. Rep.* https://doi.org/10.1038/srep21686 (2016).
23. Goto, H. et al. High-performance combinatorial optimization based on classical mechanics. *Sci. Adv.* 7, eabe7953 (2021). https://doi.org/10.1126/sciadv.abe7953.
24. Uchida, S. & Chauduri, T. Parameter optimization with quasi-xorsat planted solutions benchmark of classical and quantum heuristic solvers. In *Complex, Intelligent, and Software Intensive Systems* (eds Barolli, L. & Terzo, O.) 432–438 (Springer, 2018).
25. Takahashi, S., Tokuda, M., Matsubara, S. & Utsuno, H. An accelerator architecture for combinatorial optimization problems. *Fujitsu Sci. Tech. J.* 53, 8–13 (2017).
26. dwave-neal. https://github.com/dwavesystems/dwave-neal.
27. D-wave neal. https://github.com/dwavesystems/dwave-neal.
28. Shanying, L., Gupta, S. & Silberholz, J. What works best when? A systematic evaluation of heuristics for max-cut and QUBO. *DISCOP2018* Comp. 96, 603–624 (2018).
29. Darmann, A. & Döcker, J. On simplified np-complete variants of not-equal 3-SAT and 3-SAT (2019). 1908.04198.
30. Achlioptas, D., Chcierba, A., Istrate, G. & Moore, C. The phase transition in 1-in-k-SAT and NAE 3-SAT. In *Proceedings of the Annual ACM Symposium on Discrete Algorithms*, https://doi.org/10.1145/365411.365426 (2001).
31. Clark, J. A. et al. Local search and the number of solutions. In *Principles and Practice of Constraint Programming—CP96* (ed. Freuder, E.) 325–339. Springer (1996).
32. Gent, I. P. & Walsh, T. The phase transition. In *ECAI* (1994).
33. Sherrington, D. & Kirkpatrick, S. Solvable model of a spin glass. *Phys. Rev. Lett.* 35, 1792–1796. https://doi.org/10.1103/PhysRevLett.35.1792 (1975).
34. Mezard, M., Parisi, G. & Virasoro, M. *Spin Glass Theory and Beyond: An Introduction to the Replica Method and its Applications.* World Scientific Lecture Notes in Physics (World Scientific Publishing Company, 1987).
35. Thouless, D. J., Anderson, P. W. & Palmer, R. G. Solution of 'solvable model of a spin glass'. *Phys. Mag. A. Theor. Exp. Appl. Phys.* 35, 593–601. https://doi.org/10.1080/14786437708235992 (1977).
36. MOlib. https://github.com/MOLib/MOLib.

---

## Acknowledgements

We thank Murray Thom, Catherine McGeogh, Hayato Goto, and Yoshihiko Nishikawa for fruitful discussion on our benchmark tests. In addition, we acknowledge research supports on various aspects from D-Wave Systems Inc. and TOSHIBA CORPORATION. M. O. thanks financial support from JSPS KAKENHI Grant Number 20H02168, the Next Generation High-Performance Computing Infrastructures and Applications R & D Program by MEXT, and MEXT-Quantum Leap Flagship Program Grant Number JPMXS1203520009.

---

## Author contributions

H.O. and M.O. wrote the main manuscript. All authors reviewed the manuscript.

---

## Competing interests

The authors declare no competing interests.

---

## Additional information

Correspondence and requests for materials should be addressed to H.O.

**Reprints and permissions** information is available at www.nature.com/reprints.

**Publisher's note** Springer Nature remains neutral with regard to jurisdictional claims in published maps and institutional affiliations.

---

**Open Access** This article is licensed under a Creative Commons Attribution 4.0 International License, which permits use, sharing, adaptation, distribution and reproduction in any medium or format, as long as you give appropriate credit to the original author(s) and the article, provide a link to the Creative Commons licence, and indicate if changes were made. The images or other third party material in this article are included in the article's Creative Commons licence, unless indicated otherwise in a credit line to the material. If material is not included in the article Creative Commons licence and your intended use is not permitted by statutory regulation or exceeds the permitted use, you will need to obtain permission directly from the copyright holder. To view a copy of this licence, visit http://creativecommons.org/licenses/by/4.0/.

© The Author(s) 2022
