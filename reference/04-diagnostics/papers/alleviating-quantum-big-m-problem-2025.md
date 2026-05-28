# Alleviating the quantum Big-*M* problem

**Edoardo Alessandroni¹,²**, **Sergi Ramos-Calderer¹,²**, **Ingo Roth¹**, **Emiliano Traversi³** & **Leandro Aolita¹**

¹Quantum Research Centre, Technology Innovation Institute (TII), Abu Dhabi, UAE. ²SISSA — Scuola Internazionale Superiore di Studi Avanzati, Trieste, Italy. ³Department of Física Quàntica i Astrofísica and Institut de Ciències del Cosmos (ICCUB), Universitat de Barcelona, Barcelona, Spain. ⁴Department of Information Systems, Data Analytics and Operations, ESSEC Business School, Cergy-Pontoise, France. e-mail: alessandroni@sissa.it

## Abstract

A major obstacle for quantum optimizers is the reformulation of constraints as a quadratic unconstrained binary optimization (QUBO). Current QUBO translators exaggerate the weight $M$ of the penalty terms. Classically known as the "Big-$M$" problem, the issue becomes even more daunting for quantum solvers, since it affects the physical energy scale. We take a systematic, encompassing look at the quantum big-$M$ problem, revealing NP-hardness in finding the optimal $M$ and establishing bounds on the Hamiltonian spectral gap $\Delta$ as a function of the weight $M$, inversely related to the expected run-time of quantum solvers. We propose a practical translation algorithm, based on SDP relaxation, that outperforms previous methods in numerical benchmarks. Our algorithm gives values of $M$ orders of magnitude greater, e.g. for portfolio optimization instances. Solving such instances with an adiabatic algorithm on 6-qubits of an IonQ device, we observe significant advantages in time to solution and average solution quality. Our findings are relevant to quantum and quantum-inspired solvers alike.

---

Quantum computing holds a great potential for speeding up combinatorial optimization¹. From a distant future perspective, the prospects are rooted in the fact that fault-tolerant quantum computers are envisioned to run quantum versions of state-of-the-art classical algorithms more efficiently. In fact, there is sound theoretical evidence that such quantum algorithms offer a quantum asymptotic speed-up over their classical "counterparts"². In the short run, there is a direct relation between the ground state of physical systems and optimization. The paradigm example is Ising models encoding quadratic unconstrained binary optimization (QUBO) problems. This has fueled a quest for ground-state preparation algorithms implementable on near-term quantum hardware. These include quantum annealing³, quantum imaginary time evolution⁴, and heuristics such as the quantum approximate optimization algorithm⁵. Moreover, apart from quantum solvers, the QUBO paradigm is proving use to a variety of interesting quantum-inspired solvers as well⁶,⁷.

A prerequisite to apply such paradigm to more general quadratically constrained integer optimization problems is to recast them into an equivalent QUBO form. Technically, although QUBO appeared⁸,⁹, the translation consists of lifting the constraints to penalty terms in the objective function. To ensure that the solution to the reformulated (unconstrained) problem coincides with that of the original (constrained) one, the weight of the penalty terms—often denoted as $M$—has to be sufficiently large. At the same time, choosing an excessively large $M$ causes an increase in precision issues in numerical solvers and, for quantum solvers, issues in providing an accurate quantum-classical correspondence. In the classical optimization community this problem is referred to as the *Big-M problem*.

In contrast, quantum QUBO solvers are closer in spirit to *analog* computing devices. There, the value of $M$ directly affects the energy scale of the Hamiltonian whose ground state encodes the solution. When performing unconstrained computations with an actual physical quantum system its admissible energies are limited. For ground-state preparation schemes based on adiabatic evolution adiabaticity also requires the energy scale of the encoding Hamiltonian²⁺³. More precisely, the penalty terms tend to have the undersized side effect of decreasing the spectral gap of the Hamiltonian. As a consequence, the precision required to resolve the states, and, hence, also the run-time, increases. A general rule of thumb is to choose $M$ as small as possible, but doing so with full adiabatic fidelity enforcing the constraints is highly non-trivial. In fact, the known computationally-efficient big-$M$ recipes end up largely over-estimate the required value²⁵,²⁶,²⁷. Clearly, an efficient QUBO translator with improved spectral properties is highly desirable. Moreover, a paramount aspect of the quantum big-$M$ problem is a fundamental concept between quantum physics and computer science is missing: viz, given a framework that should characterize the impact on quantum solvers of the computational complexity of QUBO reformulations.

Here, we fill in this gap. We develop a theory of the quantum big-$M$ problem and its impact on the classical QUBO reformulations. We start with rigorous definitions for the notions of optimal $M$ and exact QUBO reformulations. We prove that finding the optimal $M$ is NP-hard and establish relevant upper bounds on the Hamiltonian spectral gap $\Delta$, both in terms of the original set of and of $M$. One of the formulas emphasizes the intuition that $\Delta = O(M^{-1})$. Most importantly, we present a universal QUBO reformulation method with improved spectral properties. This is a simple but

---

## Results

### The quantum Big-*M* problem

Our starting point is a *linearly-constrained binary quadratic optimization* (LCBO) problem with binary decision variables and $m$ constraints,

$$\text{minimize } f(x) = x^T Qx \quad \text{subject to} \quad Ax = b. \quad (P)$$

specified in terms of $Q \in \mathbb{Z}^{n \times n}$, $A \in \mathbb{Z}^{m \times n}$, and $b \in \mathbb{Z}^m$. Note that a general polynomially-constrained polynomial optimization problem with integer variables can always be cast into a linearly-constrained binary quadratic optimization problem of the form (P) by standard gadgets, as summarized in Supplementary Information. A furthermore, for the sake of clarity, we consider throughout *exact optimization solvers*. Clearly, near-quantum optimization solvers are envisioned to be approximation solvers. However, our discussion can be extended to approximate solvers, e.g. by describing all feasible approximate solutions as optimal points of problem (P).

To arrive at a QUBO reformulation of (P), the best-known strategy (see Fig. 1) is to promote the constraints to a penalty term in the objective function using a suitable weight $M \geq 0$. The resulting QUBO reads,

$$\text{minimize } x^T Qx + M(Ax - b)^2. \quad (P_M)$$

We say that $(P_M)$ is an *exact reformulation* of (P) if their optimal points coincide. The penalty term in $(P_M)$ vanishes for every feasible point. To

---

arrive at an exact reformulation, $M$ has to be chosen large enough for every unfeasible point ($\tilde{x}$) to have a greater objective value than the original optimal, i.e. an optimal point of (P), we have an exact reformulation if and only if there exists a gap $\delta > 0$ s.t.

$$f(x^*) + \delta \leq f(x) + M(Ax - b)^2 \tag{1}$$

for all unfeasible points $x$. There are simple choices of $M$ to ensure this condition, such as

$$M_g = \|Q\|_\infty + \delta, \tag{2}$$

with the vector $\ell_1$-norm being the sum of all absolute entries. Since $M_g$ can be computed in polynomial time, it follows that $(P)$ and $(P_{\delta})$ with $M = M_g$ belongs in the same complexity class. This choice of $M$ is common²⁵,²⁶, but, as we show below, it typically yields excessively large values.

**Observation 1.** Finding optimal $M$ is NP-hard. Intuitively, Eq. (1) already hints at the possibility that finding the optimal $M$ can be as hard as determining the optimal objective value of the original optimization problem. In Section "On the hardness of the quantum Big-M problem", we provide a polynomial reduction of the problem of deciding if there exists a gap $\delta$ with minimal $M$. Note that the minimal choice of $M$ guarantees only a difference $> 0$ between the objective value and those of the unfeasible points. To avoid an arbitrarily small gap, $\delta$ can be chosen as a constant independent of the system size in Eq. (1). For specific classes of problems it is not hard to formulate strategies for optimal choices of $M_i$, an example being the problem of finding maximum independent sets, where the optimal value of $M$ is apparent²⁸. In general, however, this is intractable.

**Observation 2.** Let $x_{\text{min}}$ be a feasible point of (P), $\delta > 0$, and choose $f_{\text{min}} = \min\{f(x) \mid x \in (0, 1)^n\}$, i.e. as a lower bound on the objective

---

function of (P) when omitting the linear constraints. Then, $(P_M)$ with

$$M = f(x_{\text{min}}) - f_{\text{min}} + \delta \tag{3}$$

is an exact reformulation of (P) with gap (at least) $\delta$.

**Proof.** Let $x$ be an unfeasible point and $M$ chosen according to Eq. (3). Since $(Ax - b)^2 \geq 1$, $M(Ax - b)^2 \geq M$. The second inequality follows from the definition of $f_-$ and the fact that $f(x^*) \geq f(x_{\text{min}})$ for any feasible point $x_{\text{min}}$. Thus, Eq. (1) holds.

While any choice of feasible point $x_{\text{min}}$ yields an admissible value of $M$ good choices of $M$ are those with small objective $f(x_{\text{min}})$ and the bound $f_- \leq$ $\arg \min_x f(x)$ is tight as possible. A universal strategy to determine good points is the following Semi-Definite Programming (SDP) relaxation (SDP Supplementary Information B) of the unconstrained minimization of $J$. The resulting objective value as $f_{\text{SDP}}$. This strategy is our main numerical tool. We use the value given by $M_{\text{SDP}}$ = $f_{\text{SDP}} - f_{\text{min}} + \delta$.

We note that there exist problem instances where even finding a feasible point is hard. In practice, however, exist efficient heuristics to determine feasible points. For finding our heuristic is based on standard SDP relaxation²⁷. We perform exhaustive numerical tests on sparse linearly constrained binary optimizations, set partition problems (SPPs), and portfolio optimizations from real S&P 500 data. For all three classes, we systematically obtain values of $M$ one order of magnitude smaller than $M_g$ from one to two orders of magnitude greater.

---

**Observation 3.** If $(P_M)$ is an exact reformulation, then (i) $E_0 = f(x^*)$; (ii) $\Delta \leq \Delta_0$ for all $M$, with $\Delta$ the spectral gap of the constrained optimization problem (P). To avoid an arbitrarily small gap, $\Delta$ can be chosen as a constant independent of the system size in Eq. (1). For specific classes of problems it is not hard to formulate strategies for optimal choices of $M_i$, an example being the problem of finding maximum independent sets, where the optimal value of $M$ is apparent²⁸. In general, however, this is intractable.

The spectral gap normalization is imperative since the constant error ground-state approximation is $\Omega(\Delta_u^{-1})^{1+\gamma}$. For variational algorithms, also the training is affected: as $M$ grows, the sensitivity of the cost function (the energy) to parameter changes becomes increasingly dominated by $H_c$ and $H_t$ increasingly irrelevant²⁹. Hence, we propose $\Delta_M$ as a natural measure for the big-$M$ problem of a QUBO reformulation. This allows us to quantitatively benchmark our big-$M$ recipe against the previous heuristics bounds, which we do next.

### Spectral gap as a measure of the Big-*M* problem

Near-term quantum computation (and inspired algorithms) relies on ground-state optimization of an Ising Hamiltonian $H = H_C + M H_P$ (see Section "Experimental implementation" for explicit expressions) that encodes the objective function. The Hamiltonian $H_C$ encodes the objective while $H_P$ encodes the constraint part. Hence, the choice of $M$ directly affects the spectral gap

$$\Delta_M := \frac{E_1 - E_0}{E_{\max} - E_0}, \tag{4}$$

where $E_0$, $E_1$, and $E_{\max}$ are respectively the lowest, next-to-lowest and maximum energies of $H_M$. The spectral gap normalization is imperative since the constant-error ground-state approximation is $\Omega(\Delta_u^{-1})^{1+\gamma}$. For variational algorithms, also the training is affected: as $M$ grows, the sensitivity of the cost function (the energy) to parameter changes becomes increasingly dominated by $H_c$ and $H_t$ increasingly irrelevant²⁹. Hence, we propose $\Delta_M$ as a natural measure for the big-$M$ problem of a QUBO reformulation. This allows us to quantitatively benchmark our big-$M$ recipe against the previous heuristics bounds, which we do next.

Let $H_M = H_C + MH_P$ be a Hamiltonian encoding of (P_M). The normalized spectral gap of $H_M$ is defined as

$$\Delta_M := \frac{E_1 - E_0}{E_{\max} - E_0}, \tag{4}$$

where $E_0$, $E_1$, and $E_{\max}$ are the respective lowest, next-to-lowest and maximum energies of $H_M$. We will study the behavior of $\Delta_M$ compared to the corresponding one of the unconstrained optimization problem (P). To this end, let $x^*$ be an optimal point as before and hereafter $x_i$ a next-to-optimal point of (P), i.e. the constraint set has $\{x \mid f(x) \in [x_i A(x = b)\} \subseteq \{x\}$ constraint added $\{x \mid A x = b\}$. Denote by $C = |x(A x - b)|$ the constraint set shifted objective $f_C = \max \{f(x) - f(x^*)\}$ and shifted objective $f_C = \max \{f(x) - f(x^*)\}$ and

$$\Delta_0 = \frac{f(x_i) - f(x^*)}{f} \tag{10}$$

as the spectral gap of (P).

(i) The Ising encoding ensures that $(x|H_0|x) = f(x)$ for all $x$, where $|x|$ denotes the basis vector that encodes $x$ in the kernel of $H_C$. Thus, when $M$ is chosen such that $(P_M)$ is an exact reformulation of (P), we have $E_0 = f(x^*)$.

(ii) Analogously, $J(x_i)$ is still in the spectrum of $H_M$. Thus, $E_1 \leq J(x_i)$. This establishes that $\Delta_0 \leq f_C / \{E_1 \}$ where $\{E_0 \leq E_1 \}$. We conclude that if one is to set to fully specify the instance is to restrict our focus in the integer to $k > 0$ and assume that $f(0) > 0$, where decided. We choose $\delta = \max \{f(x) - \min \{f(x) : f(0) = e, e.g. d = M_g + f(0) - d$ using $M_g$ defined in Eq. (2) for the quadratic form $Q$ defining $f$. Consider the following optimization problem:

$$\text{minimize } \{f(x) + \alpha \|x\| \|x - k\| \quad \text{subject to} \quad x = 0. \tag{6}$$

The optimal point of $(6)$ is the only feasible point $x^* = 0$ with objective value $f(0)$. In other words, the constraint renders the optimization problem $(6)$ trivial. Still if we can be recast as the following binary quadratic problem:

$$\text{minimize } f(x) + g(x, p, m) \quad \text{subject to} \quad x = 0. \tag{7}$$

with $g(x, p, m) = \alpha\|(p - m) + \alpha r^T \|_{(p-m) - k}\|^2 + k\rangle$. Here the non-negative integer variables $p$ and $m$ can each be encoded with $\lceil \log n \rceil$ binary variables. The last constraint in the objective function for all values of $x, p$, and $m$. Thus, at optimal $p$ and $m$, it enforces the constraint $p - m = \lceil s - k\rceil$ while the other variable spans $p$ and $m$ is equal to $\lceil s - k\rceil$ while the other variable $p$ and $m$ is equal to $\lceil s - k\rceil$ while the other variable $p$ and $m$ spans the full constraint. Since $(7)$ is an instance of (P), this distances the claim **Lemma 1.** The problem $\text{decideM}$ reduces to $\text{decideM}$.

**Proof.** Consider an instance $(f, (0, 1)^n, a, \delta)$ of $\text{decideM}$: W.l.o.g., we assume that the instance $(0, 1)^n$ unconstrained. For the constraint problem there exist a polynomial reduction to an unconstrained problem, c.g. using (2.7) with the value of $M$ defined in Eq. (3).

---

**Fig. 1 | In a linearly-constrained binary quadratic optimization (LCBO, left) with optimal point $x^*$, unfeasible points (red-shaded sub-domain) are excluded from the feasible set (blue). In the reformulation as a quadratic unconstrained binary optimization (QUBO, center), the native formulation for quantum solvers, penalty term for quantum solvers, penalty term variable on the feasible region, achieving better weights $M$ is scaled to the objective function. The reformulation is exact ($f(x^*) \leq f(x)$ remains optimal) if $M$ is

sufficiently large, lifting the objective values of all unfeasible points above $(x^*)$. However, the penalty term affects the physical energy scale; the larger $M$, the smaller the spectral gap $\Delta$ of the Hamiltonian encoding the QUBO (right). This has a detrimental effect on the runtime of exact solvers as well as the quality of the solution of approximate solvers. While NP-hard in general (as we prove), we present an efficient classical strategy to find 'good' choices of $M$.**

remarkably powerful heuristic recipe for $M$, based on standard SDP relaxation²⁷. We perform exhaustive numerical tests on sparse linearly constrained binary optimizations, set partition problems (SPPs), and portfolio optimizations from real S&P 500 data. For all three classes, we systematically obtain values of $M$ one order of magnitude smaller than $M_g$ from one to two orders of magnitude greater.

---

$$f(x^*) + \delta \leq f(x) + M(Ax - b)^2 \tag{1}$$

for all unfeasible points $x$. There are simple choices of $M$ to ensure this condition, such as

$$M_g = \|Q\|_\infty + \delta, \tag{2}$$

with the vector $\ell_1$-norm being the sum of all absolute entries. Since $M_g$ can be computed in polynomial time, it follows that (P) and (P_δ) with $M = M_g$ belongs in the same complexity class. This choice of $M$ is common²⁵,²⁶, but, as we show below, it typically yields excessively large values.

---

### Methods

#### On the hardness of the quantum Big-*M* problem

Here we formally establish that determining an optimal $M$ is in general as hard as finding the objective value of the original problem. We do this by proving a simple reduction from the decision-problem version of the latter to that of the former.

The highlight of the objective value of a function $f$ under constraints $C$ is equivalent to an associated decision problem, $\text{decideF}$, which, given a threshold $k$ and a gap $\delta > 0$, decides if $\min \{f(x) \mid x \in C\} \leq k$ (or $\min\{f(x) \mid x \in C\} \geq k + \delta$ ('greater'). Note that having access to an oracle for $\text{decideF}$ allows one to efficiently find the optimal objective value by binary search. We want to reduce complexity of $\text{decideF}$ to the following decision problem:

**Problem:** Given an instance of (P), an $\Delta$, and a gap $\delta > 0$, decide if $\min \{f(x) \mid x \in (0, 1)^n\}$ with constant Hamming weight $k$ is (smaller) or ('greater'). Note that having access to an oracle for $\text{decideF}$ allows one to efficiently find the optimal objective value by binary search. We want to reduce complexity of $\text{decideF}$ to the following decision problem:

**Lemma 1.** The problem $\text{decideM}$ reduces to $\text{decideF}$.

**Proof.** Consider an instance $(f, (0, 1)^n, a, \delta)$ of $\text{decideM}$: W.l.o.g., we assume that the instance is unconstrained. For the constraint problem there exist a polynomial reduction to an unconstrained problem, c.g. using (2.7) with the value of $M$ defined in Eq. (3).

---

$$= (f(0) - \alpha)/k > 0 \text{ has an objective function that attains its minimum over the unfeasible points for } k = |x|. \text{ Thus, this minimum fulfills}$$

$$\min_k \left\{ f(x) + \alpha \|x\| |x - k| + \frac{f(0)-\alpha}{k} |x| \right\}$$

$$= \min \{ f(x) + f(0) - \alpha \leq \delta / f(0) . \tag{8}$$

Due to the trivializing constraint, $f(0)$ is the optimal value of $\tau$. Hence, $\delta$ establishes the criterion Eq. (1) for an exact reformulation. As required in this case, decideM, this returns 'yes' and we decide correctly.

Second, let us consider the case 'smaller', i.e. $\min_x f(x) \leq a + \delta$ ('greater'). Note that having access to an oracle for decideF allows one to efficiently find the optimal objective value by binary search. We want to reduce complexity of decideF to the following decision problem:

Since $\text{decideF}$ encompasses NP-complete problems like 3SAT, as a corollary of Lemma 1, we establish that finding the optimal value of $M$ is NP-hard.

**Bounds on the spectral gap of Big-*M* QUBO reformulations**

Next, we provide the detailed argument for Observation 3 of the main text, and expand on some of its implications.

Let $H_M = H_C + MH_P$ be a Hamiltonian encoding of $(P_M)$. The normalized spectral gap of $H_M$ is defined as

$$\Delta_M := \frac{E_1 - E_0}{E_{\max} - E_0}, \tag{9}$$

where $E_0$, $E_1$, and $E_{\max}$ are the respective lowest, next-to-lowest and maximum energies of $H_M$. We will study the behavior of $\Delta_M$ compared to the corresponding one of the unconstrained optimization problem (P). To this end, let $x^*$ be an optimal point as before and hereafter $x_i$ a next-to-optimal point of (P), i.e. the constraint set has the additional constraint $\{x \mid Ax = b\}$. Denote by $C = |x(Ax - b)|$ the constraint set shifted objective $f_C = \max \{f(x) - f(x^*)\}$ and

$$\Delta_0 = \frac{f(x_i) - f(x^*)}{f} \tag{10}$$

as the spectral gap of (P).

(i) The Ising encoding ensures that $(x \mid H_0 \mid x) = f(x)$ for all $x$, where $|x|$ denotes the basis vector that encodes $x$ in the kernel of $H_C$. Thus, when $M$ is chosen such that $(P_M)$ is an exact reformulation of (P), we have $E_0 = f(x^*)$.

(ii) Analogously, $J(x_i)$ is still in the spectrum of $H_M$. Thus, $E_1 \leq J(x_i)$. This establishes that $\Delta_0 \leq E_1/E_0$ where we used that $E_0 \leq E_1 \}$. We conclude that if one is to set to fully specify the instance is to restrict our focus in the integer to $k > 0$ and assume that $f(0) > 0$, where decided. We choose $\delta = \max \{f(x) - \min \{f(x) : f(0) = e, e.g. d = M_g + f(0) - d$ using $M_g$ defined in Eq. (2) for the quadratic form $Q$ defining $f$. Consider the following optimization problem:

$$\text{minimize} \{ f(x) + \alpha\|x\| |x - k\| \quad \text{subject to} \quad x = 0. \tag{6}$$

The optimal point of $(6)$ is the only feasible point $x^* = 0$ with objective value $f(0)$. In other words, the constraint renders the optimization problem $(6)$ trivial. Still if we can be recast as the following binary quadratic problem:

$$\text{minimize} f(x) + g(x, p, m) \quad \text{subject to} \quad x = 0. \tag{7}$$

with $g(x, p, m) = \alpha\|(p - m) + \alpha r^T \|_{(p-m) - k}\|^2 + k\rangle$. Here the non-negative integer variables $p$ and $m$ can each be encoded with $\lceil \log n \rceil$ binary variables. The last constraint in the objective function for all values of $x, p$, and $m$. Thus, at optimal $p$ and $m$, it enforces the constraint $p - m = \lceil s - k \rceil$ while the other variable spans $p$ and $m$ is equal to $\lceil s - k\rceil$ while the other variable spans the full constraint. Since $(7)$ is an instance of (P), this distances the claim $\Delta_M = \Omega(\Delta_0/M)$ asymptotically. This substantiates the initial intuition that extremely small penalty $\Delta$ is determined inversely into the time-to-solution. This behavior is consistently observed across instances. Figure 2g shows the average approximation ratio—quantifying the quality of an approximate solution—over all measured outcomes that satisfy the budget constraint per instance. The $M_{\text{SDP}}$ formulations yield high ratios for most instances while the $M_t$ formulations perform comparable to classical uniform random sampling of solutions. Already for small instances, the results presented in Fig. 1 support that the improvement due to a tighter reformulation will persist for larger instances.

Even when other big-$M$ recipes are available, our method can assist such recipes. By providing a suitable feasible point with reasonable classical resources, one can determine a good value for $M$ to be used during quantum hardware. For example, using multiple calls to the solver, one can determine a feasible point with near-feasible classical resources. For all increased when using available classical resources. For all increased when using available classical resources, one can determine $\delta$ by performing classical random sampling or gradient-based heuristics. For instance, using multiple calls to the solver, one can determine $\delta$ by performing available classical resources. For example, using multiple calls to the solver, one can determine a feasible point with near-feasible classical resources.

**Beyond new-run quantum devices, our analysis of the big-M problem applies to future fault-tolerant quantum hardware, for instance in adiabatic schemes**²⁸ or quantum imaginary time evolution simulations²⁹. Besides, a particular interest in exploring the quantum-question to explore is how to generate a heuristic bigM recipe for a general big-M recipes for quantum-inspired, classical solvers⁷⁹. Computing our approach with modern suitable randomized algorithms for general instances, nuances of specific problems can enable heuristic tools for tighter lower bounds of feasible points, as already exemplified with the greedy heuristic for PO instances.

### Benchmarked models

The present section illustrates the model definition and relevant details of the optimization problems tested, together with further results.

**Benchmark models**

Linearly-constrained binary quadratic optimization problems (LCBO) instances, whose formulation is (P), have been generated. We choose a subset of size $S \subseteq \\{1, ..., m\\}$ to be a subset of $S \subseteq \\{1, ..., n\\}$ for discrete portfolio partitioning by dividing the portfolio discretization Denoting by $\mathsf{x}_i$ the units of the portfolio, the problem formulation reads

$$\text{minimize} c^T x \quad \text{subject to} \quad \sum_i x_i = 1 \gamma a \in S. \tag{11}$$

The constraint forces the total budget to be invested. The QUBO reduction requires a vector of $n$ expected returns of a set of $N$ assets, their covariance matrix $\Sigma$ with unit partition value $y > 0$, and a partition $n$ defining the portfolio discretization.

---

**Portfolio Optimization (PO).** The present paragraph illustrates the data used in Portfolio Optimization instances were fetched from real data and adapted to Markowitz formulation²⁷. From stock market index S&P 500, we downloaded stock price history, referring to the 2-years period December 2020 until November 2022 with one-month interval. Of these 121 out of the 500 stocks tracked by S&P 500 (namely, the ones with no missing data in said intervals), Let us call $r_{t,i}$ such cost of an asset $i$. The return at time step $i$ is defined as

$$r_{i,t} = \frac{P_{i,t} - P_{i,t-1}}{P_{i,t-1}}, \tag{12}$$

from which the expected return vector $\mu$ and the covariance matrix $\Sigma$ can be computed as $\mu_i = \frac{1}{T} \sum_{t=1}^T r_{i,t}$ and $\Sigma_{i,j} = \frac{1}{T} \sum_{t=1}^T (r_{i,t} - \mu_i)(r_{j,t} - \mu_j)$. We encode the real financial stock market data with decimal precision of $10^{-3}$.

The number of stocks in an instance is determined by the partition $y$. Let describes the granularity of the portfolio discretization. The budget is divided into $2^n - 1$ equally sized units. Each asset decision variable $x_i$ is an integer that can take values from $0$ to $2^n - 1$, indicating how many of these partitions to allocate towards asset $i$. Therefore, we need $x_i = 2^n - 1$ ensures that all $2^n - 1$ units are invested in one of the stock assets. The latter partitions, each asset decision variable requires $\log n$ binary variables. We obtain 100 random PO instances by sampling a subset of 5 assets from the feasible universe of these stocks.

**Set partitioning problem (SPP).** A general class of linearly-constrained binary optimization problems, whose formulation is (P), have been generated. We choose a subset of size $S \subseteq \\{1, ..., m\\}$ where $m$ is a partition of $S \subseteq \\{1, ..., m\\}$. Let $R_i$ denote a subset and $R_i$ is a subset and $R_i = \\{\\} $ for all $i, j \\in \\mathcal{P}$. The SPP consists of finding a partition of $S$ with minimal total cost:

$$\text{minimize} c^T x \quad \text{subject to} \quad \sum_i x_i = 1 \gamma a \in S. \tag{11}$$

The constraint forces the family to be a partition of $S$. We generate random SPP instances by sampling a subset of constraints directly. To this problem class, the SPP can be hard to define. To define the instances are determined by the partition $y$. $q_j$ describes the granularity of the portfolio discretization. The budget is divided into $2^n - 1$ equally sized units. Each asset decision variable $x_i$ is an integer that can take values from $0$ to $2^n - 1$, indicating how many of these partitions to allocate towards asset $i$. Therefore, we need $x_i = 2^n - 1$ ensures that all $2^n - 1$ units are invested in one of the stock assets. The latter partitions, each asset decision variable requires $\log n$ binary variables. We obtain 100 random PO instances by sampling a subset of 5 assets from the feasible universe of these stocks.

---

**Set partitioning problem (SPP).** Let $\mathcal{P} = \\{R_1, ..., R_m\\}$ be a collection of subsets of $S = \\{1, ..., n\\}$ for discrete portfolio partitioning. Denoting by $x_i$ the units of the portfolio in the ith subset, the problem formulation reads

$$\text{minimize} c^T x \quad \text{subject to} \quad \sum_i x_i = 1 \gamma a \in S. \tag{11}$$

The constraint forces the family to be a partition of $S$. We generate random SPP instances by sampling a subset of constraints directly. We generate random SPP instances by sampling a subset of constraints directly, with a random budget sampling. The problem specification requires a vector of $q$ expected returns of a set of $N$ assets. The number of constraints $m$ describes the granularity of the portfolio discretization.

**Random sparse LCBOs.** A general class of linearly-constrained binary quadratic optimization problems, whose formulation is (P), have been generated. We choose a subset of size $S \subseteq \\{1, ..., m\\}$ and $A$ with a bounded row-sparsity $s$. [For $Q_ij = 0 | ≤ i ∀ j$, and similarly for $A$. The non-vanishing entries of $Q$ and $A$ are uniformly drawn at random. We let the number of constraints $m$ grow linearly with the number of binary variables $n$ specifically, $m$ [For $n \leq m ≤ 2$, i.e. as a version of $n = 60$ $100$, $150$, and $200$ stocks. For LCBO, we test the set size $n = 6$, $12$, $18$ and $25$ binary variables.

---

## Experimental implementation

The adiabatic theorem² states that a quantum system will remain in its instantaneous ground state through adiabatic perturbations to its Hamiltonian. Adiabatic quantum computation exploits this fact by preparing a system under the Hamiltonian

$$H(t) = (1 - s)H_0 + sH_P, \tag{13}$$

where $H_0$ is a Hamiltonian with an easy to prepare ground state, $H_P$ encodes the solution of a problem, and the schedule $s$ is evolved from 0 to 1. If the adiabatic condition is met at the end of the evolution, hence solving the problem.

A QUBO instance can be mapped into an Ising Hamiltonian by promoting each binary variable to an Ising spin, and substituting $x_i$ for $(1 - \sigma_i^Z)/2$, where $\sigma_i^Z$ is the Pauli matrix acting on qubit $i$. Our problem Hamiltonian is usually chosen as $H_P = -\sum_i \sigma_i^x$, as it has an easy to prepare ground state, the equal superposition of all computational basis states. This is important, as the rest of the adiabatic evolution, which we will discuss.

A QUBO instance can be mapped into an Ising Hamiltonian by promoting each binary variable to an Ising spin, and substituting $x_i$ for $(1 - \sigma_i^Z)/2$, where $\sigma_i^Z$ is the Pauli matrix acting on qubit $i$. The problem Hamiltonian is the following:

$$H(t) = (1 - s)H_0 + sH_P, \tag{13}$$

where $H_0$ is a Hamiltonian with an easy to prepare ground state, $H_P$ encodes the solution of a problem, and the schedule $s$ is evolved from 0 to 1. If the adiabatic condition is met at the end of the evolution, hence solving the problem.

Deployment of algorithms on available quantum hardware requires precise fine-tuning as well as knowledge of the physical implementations of the device. In this work, the starting point of such implementations on the device. In this work, the starting point of such implementations on the device. In this work, the starting point of such implementations on the device. In this work, the starting point of such implementations on the device. In this work, the starting point of such implementations on the device. In this work, the starting point of such implementations on the device. In this work, the starting point of such implementations on the device. In this work, the starting point of such implementations on the device. In this work, the starting point of such implementations on the device. In this work, the starting point of such implementations on the device.

The adiabatic theorem states that a quantum system will remain in its instantaneous ground state through adiabatic perturbations to its Hamiltonian. Adiabatic quantum computation exploits this fact by preparing a system under the Hamiltonian $H(t) = (1 - s)H_0 + sH_P$, with the schedule $s$ evolved from 0 to 1. If the adiabatic condition is met at the end of the evolution, hence solving the problem.

A QUBO instance can be mapped into an Ising Hamiltonian by promoting each binary variable to an Ising spin, and substituting $x_i$ for $(1 - \sigma_i^Z)/2$, where $\sigma_i^Z$ is the Pauli matrix acting on qubit $i$. Our problem Hamiltonian is usually chosen as $H_0 = -\sum_i \sigma_i^x$, as it has an easy to prepare ground state, the equal superposition of all computational basis states. This is important, as the rest of the adiabatic evolution, which we will discuss.

Deployment of algorithms on available quantum hardware requires precise fine-tuning as well as knowledge of the physical implementations of the device. In this work, the starting point of such implementations on the device. In this work, the starting point of such implementations on the device. In this work, the starting point of such implementations on the device. In this work, the starting point of such implementations on the device. In this work, the starting point of such implementations on the device. In this work, the starting point of such implementations on the device. In this work, the starting point of such implementations on the device.

The native interactions available in the device are the following. Single qubit gates are fixed and $\pi/2$ rotations along the $X-Y$ plane, with precise control over the relative phase. Using this method, rotations around the $Z$ axis are done virtually. Using this method, rotations around the $Z$ axis are done virtually. With this method, rotations around the $Z$ axis are done virtually, and incur no noise. The IonQ aria-1 device allows for partially-entangling Mølmer-Sørensen²⁹ gates, that allow for a native XX interaction. We will perform a change of basis for the Hamiltonian, so that the two-body terms in $H_M$ are combinations of $\sigma_i^+\sigma_j^-$ and $H_c$ comprises of $\sigma_j^+$ terms.

Crucially, the ground state of the circuit configuration becomes the starting state of the device, resulting in an even easier preparation for the purposes of our evolution.

The adiabatic evolution, ideally performed by slowly sweeping over the interaction parameters of the device, will need to be Trotterized¹⁵. By selecting a total evolution time and a discretization step, the evolution can be approximated by decomposing it into into equal starting point to test different QUBO encodings, which provides us with equal starting point to test different QUBO encodings, which provides us equal starting point to test different QUBO encodings, which provides us

In order to conform with the device specifications, we limit the number of applied gate to 150. This corresponds to a maximum run time of approximately $150 \text{ ms}$ for solving instances with $M_{\text{SDP}}$ formulations yield high ratios, for most instances while the $M_t$ formulations perform comparable to classical uniform random sampling of solutions. Already for small instances, the results presented in Fig. 1 support that the improvement due to a tighter reformulation will persist for larger instances.

Even when other big-$M$ recipes are available, our method can assist such recipes. By providing a suitable feasible point with reasonable classical resources, one can determine a good value for $M$ to be used during quantum hardware. For example, using multiple calls to the solver, one can determine a feasible point with near-feasible classical resources. For all increased when using available classical resources. For all increased when using available classical resources, one can determine $\delta$ by performing classical random sampling or gradient-based heuristics. For instance, using multiple calls to the solver, one can determine a feasible point with near-feasible classical resources.

---

## Discussion

On the conceptual side, we formalized the quantum big-$M$ problem, giving rigorous definitions, establishing its computational complexity, and giving bounds on the impact of $M$ on the spectral gap of a QUBO Hamiltonian.

The latter relates the big-$M$ problem to performance guarantees of different solvers. From a practitioner's viewpoint, our main contribution is a versatile QUBO reformulation algorithm with enhanced spectral properties, based on the SDP relaxation. Our mindset that classical solvers should be exploiting quantum hardware to its maximal potential—near-term devices in particular.

In numerical benchmarks, including Markowitz portfolio optimization and S&P 500 data, we consistently observe significant improvements in $M$ and the spectral gap using the proposed algorithm. In a six-qubit proof-of-principle experiment with trapped ions, we find that these improvements translate into a tangible advantage in the probability of measuring the correct solution as well as the average solution quality.

---

## Greedy algorithm for portfolio optimization

Any strategy to get a feasible point $x_{\text{min}}$ using classical resources is a viable option to obtain an upper bound on $M$. For various classes of optimization problems, it is possible to apply a greedy heuristic algorithm to efficiently obtain an approximate feasible point. For example, just as a simple example to describe the algorithm aims at obtaining solutions by sequentially assigning each portfolio position to the asset that maximizes the objective function when evaluated on the existing segment of the portfolio.

**Algorithm 1. GreedyPortfolio($\Sigma, \mu, N, w$)**

```
1   x ← 0 ∈ Z^N          // Initialize empty portfolio
2   for i ← 1 ... 2^w - 1 do
3      for k ← 1 ... N do
4         x̃ ← x
5         x̃_k ← x_k + 1
6         f' ← -μ'x̃ + x̃'Σx̃
7         if f' ≤ f' then
8            k^* ← k
9            f' ← f'
10        end
11       end
12      x_i^* ← x_i^* + 1       // Assign a unit to best asset
13   return optimized portfolio x
```

---

## Data availability

The datasets generated and analyzed for the IonQ experiment implementation are available in the IonQ quantum trotterization tree repository https://github.com/igres26/quantum-bigM-trotterization/tree/main/data^48.

All the other datasets generated and analysed during the current study are available in the qubo_mapper repository, https://github.com/Edoardo-Alessandroni/qubo_mapper^49.

---

## References

1. Abbas, A. et al. Quantum optimization: potential, challenges, and the path forward. Preprint at https://arxiv.org/abs/2312.02279 (2023).
2. Montanaro, A. Quantum algorithms: an overview. *npj Quantum Information* **2**, 15623 (2015).
3. Durr, C. & Hoyer, P. A quantum algorithm for finding the minimum. Preprint at https://arxiv.org/abs/quant-ph/0304014 (1996).
4. Ambainis, A. et al. Quantum speedups for exponential-time dynamic programming algorithms. In *Proceedings of the Thirtieth Annual ACM-SIAM Symposium on Discrete Algorithms*, 1773-1793 SIAM, (2019).
5. Farhi, E., Goldstone, J., Gutmann, S. The quantum approximate optimization algorithm. Preprint at https://arxiv.org/abs/1411.4028 (2014).
6. Chowdhury, A. N. & Somma, R. D. Quantum algorithms for Gibbs sampling and hitting-time estimation. *Quantum Inf. Comput.* **17**, 41 (2017).
7. Wang, Y., Li, S. & Wright, J. Variational quantum pulse optimization. *Phys. Rev. A* **96**, 054035 (2021).
8. Silva, T. L., Tsutsui, M., Carrascal, S. & Aolita, L. Hampered imaginary-time evolution for early-stage quantum signal processors. *Sci. Rep.* **13**, 12398 (2023).
9. Kyaw, T. H. et al. Boosting quantum amplitude exponentially in variational quantum algorithms. *Quantum Sci. Technol.* **9**, 01LT01 (2023).
10. Hegde, P. R., Passarelli, G., Soccio, A. & Lucinano, P. Genetic optimization on a quantum annealer. *Phys. Rev. Lett.* **130**, 240502 (2023).
11. McAllis, S. et al. Variational quantum simulation of imaginary time evolution. *npj Quantum Inform.* **5**, 75 (2019).
12. Motta, M. et al. Determining eigenstates and thermal states on a quantum computer using quantum imaginary time evolution. *Nat. Phys.* **16**, 205 (2020).
13. Nishi, H., Kiwoy, T. & Matsushita, Y. Implementation of quantum imaginary-time evolution method on nisq devices by introducing imaginal approximation. *npj Quantum Inform.* **7**, 85 (2021).
14. Poulin, D. & Wocjan, P. Sampling from the Thermal Quantum Gibbs distribution and evaluating partition functions with a quantum computer. *Phys. Rev. Lett.* **103**, 220502 (2009).
15. Chowdhury, A. N. & Somma, R. D. Quantum algorithms for Gibbs sampling and hitting-time estimation. *Quantum Inf. Comput.* **17**, 41 (2017).
16. Wang, Y., Li, S. & Wright, J. Variational quantum pulse optimization. *Phys. Rev. A* **96**, 054035 (2021).
17. Silva, T. L., Tsutsui, M., Carrascal, S. & Aolita, L. Hampered imaginary-time evolution for early-stage quantum signal processors. *Sci. Rep.* **13**, 12398 (2023).
18. Kyaw, T. H. et al. Boosting quantum amplitude exponentially in variational quantum algorithms. *Quantum Sci. Technol.* **9**, 01LT01 (2023).
19. Farhi, E., Goldstone, J. & Gutmann, S. A quantum approximate optimization algorithm. Preprint at https://arxiv.org/abs/1411.4028 (2014).
20. Basso, J., Farhi, E., Marwaha, K., Villalonga, B. & Zhou, L. The quantum approximate optimization algorithm at high depth for MaxCut on large-girth regular graphs and the Sherrington-Kirkpatrick model. In *Theory of Quantum Computation, Communication and Cryptography (TQC 2022)*, vol. 232, 7:1–7:21, https://doi.org/10.4230/LIPIcs.TQC.2022.7 (2022).
21. He, Z. et al. Alignment between initial states and mixer improves QAOA performance for constrained optimization. *Quantum Inf.* **8**, 121 (2023).
22. Goto, H., Tatsumura, K. & Dixon, A. R. Combinatorial optimization by adiabatic diabatic assisted thermal fluctuation. *Nat. Commun. Phys.* **5**, 153 (2022).
23. Morisaki, N., McMahon, P. L. & Byrnes, T. Ising machines as hardware solvers of combinatorial optimization problems. *Nat. Rev. Phys.* **4**, 363-379 (2022).
24. Hassan, T. & Macdonough, S. Converters for quadratic programs - linearequality topennity. https://qiskit.org/documentation/tutorials/01_quadratic_program_qiskit_optimization_linear_equality_to_penalty/ (2022).
25. QISKIT. LinearEqualityToPenalty. https://qiskit.org/ecosystem/optimization/tutorials/02_converters_for_quadratic_programs.html#Linear-Equality-To-Penalty (2022).
26. Noe, J. T., Whitfield, S. & Kaszynski, S. Pyqubo: Python library for mapping combinatorial optimization problems to qubo. *IEEE Trans. Comput.* **71**, 838 (2021).
27. Karimi, S. & Ronagh, P. Practical integer-to-binary mapping for quantum annealing. *Prog. Comput. Res.* **18**, 1 (2019).
28. Harwood, S. et al. Formulating and solving routing problems on quantum computers. *IEEE Trans. Quantum Eng.* **2**, 7564 (2023).
29. Azad, U., Behera, B. K., Ahmed, E. A., Panigrahi, P. K. & Farouk, A. Solving vehicle routing problem using quantum approximate optimization algorithm. *IEEE Trans. Quantum Eng.* **24**, 7564 (2023).
30. Leontidis, I. D., Dukakis, A., Tan, B. & Angelakis, D. G. Qubit quantum algorithms for the vehicle routing problem on noisy intermediate-scale quantum processors. *Adv. Quantum Technol.* **7**, 2300309 (2024).
31. Goemans, M. X. & Williamson, D. P. Improved approximation algorithms for maximum cut and satisfiability problems using semidefinite programming. *J. ACM* **42**, 1115 (1995).
32. Ebadi, S. et al. Quantum optimization of maximum independent set using rydberg atom arrays. *Science* **376**, 5208 (2022).
33. Lucas, A. Ising formulations of many np problems. *Front. Phys.* **2.5** (2014).
34. Ayodele, M., Penalty weights in qubo formulations: permutation problems. In *Evolutionary Computation in Combinatorial Optimization*, vol. 13222, 159-174 (Springer International Publishing, 2022).
35. Markowitz, H. Portfolio selection. *J. Financ.* **7**, 77 (1952).
36. Osen, E., Humble, T. S. & Stump, B. Benchmarking quantum annealing controls with portfolio optimization. *Phys. Rev. Appl.* **15**, 014012 (2021).
37. Rosenberg, G. et al. Solving the optimal trading trajectory problem using a quantum annealer. *Phys. Rev. E* **Top. Signal Process.* **10**, 1053 (2016).
38. Yurtsever, A., Tropp, J. A., Fercoq, O., Udell, M. & Cevher, V. Scalable semidefinite embeddings. *SIAM J. Math. Data Sci.* **3**, 171 (2021).
39. McKay, D. C., Wood, C. J., Sheldon, S., Chow, J. M. & Gambetta, J. M. Efficient 2-qubit gates in superconducting quantum computing. *Phys. Rev.* **A 96**, 022330 (2017).
40. Mølmer, K. & Sørensen, A. Multipartite entanglement of trapped ions. *Phys. Rev. Lett.* **82**, 1835 (1999).
41. Solano, E. de Melo, Matos, R. L. & Zozour, N. Deterministic bell states and measurement of the motional state of two trapped ions. *Phys. Rev. A* **59**, R2539 (1999).
42. Trotter, H. F. On the product of semi-groups of operators. *Proc. Am. Math. Soc.* **10**, 545 (1959).
43. Hatano, N. & Suzuki, M. Finding exponential product formulas of higher orders. In *Quantum annealing and other optimization methods*, vol. 679, 37-68 (Springer Berlin Heidelberg, 2005).
44. Ethymou, S. et al. Qibo: a framework for quantum simulation with hardware acceleration. *Quantum Sci. Technol.* **7**, 015018 (2021).
45. Ramos-Calderer, S. quantum-trotterization https://github.com/igres26/quantum-bigM-trotterization (2023).
46. The Qibo team. qiboteam/qibo: Qibo 0.1.15 https://doi.org/10.5281/ zenodo.8633453 (2023).

---

## Author contributions

E.A., M.F. and N.H. implemented the numerical and carried out the experimental deployment on IonQ. E.A. and S.R. derived the analytical scaling of the gap. I.R., E.T. and L.A. conceived the project and provided guidance in all steps. All authors contributed to the conception and write-up of the paper.

---

## Competing interests

The authors declare no competing interests.

---

## Additional information

**Supplementary information** The online version contains supplementary material available at https://doi.org/10.1038/s41534-025-01067-0.

**Correspondence** and requests for materials should be addressed to Edoardo Alessandroni.

**Reprints and permissions information** is available at http://www.nature.com/reprints.

**Publisher's note** Springer Nature remains neutral with regard to jurisdictional claims in published maps and institutional affiliations.

---

## Open Access

This article is licensed under a Creative Commons Attribution 4.0 International License, which permits use, sharing, adaptation, distribution and reproduction in any medium or format, as long as you give appropriate credit to the original author(s) and the source, provide a link to the Creative Commons licence, and indicate if any changes were made. The images or other third party material in this article are included in the article's Creative Commons licence, unless indicated otherwise in a credit line to the material. If material is not included in the article's Creative Commons licence and your intended use is not permitted by statutory regulation or exceeds the permitted use, you will need to obtain permission directly from the copyright holder. To view a copy of this licence, visit http://creativecommons.org/licenses/by/4.0/.

© The Author(s) 2025
