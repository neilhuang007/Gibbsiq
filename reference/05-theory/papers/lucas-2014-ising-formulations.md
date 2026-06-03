# Ising formulations of many NP problems


> **Citation.** Canonical entry `lucas2014` in [`references.bib`](../../references.bib) (resolved via Crossref/DataCite). DOI [10.3389/fphy.2014.00005](https://doi.org/10.3389/fphy.2014.00005).
>
> **Companion note.** [`lucas-2014-ising-formulations.note.md`](./lucas-2014-ising-formulations.note.md) — how this paper links to Gibbsiq.

Andrew Lucas

Lyman Laboratory of Physics, Department of Physics, Harvard University, Cambridge, MA, USA

**Edited by:** Jacob Biamonte, ISI Foundation, Italy

**Reviewed by:** Mauro Faccin, ISI Foundation, Italy; Ryan Rahman, Harvard University; Bryan A. O'Gorman, NASA, USA

**Correspondence:** Andrew Lucas, Lyman Laboratory of Physics, Department of Physics, Harvard University, 17 Oxford St., Cambridge, MA 02138, USA; e-mail: lucas@fas.harvard.edu

## Abstract

We provide Ising formulations for many NP-complete and NP-hard problems, including all of Karp's 21 NP-complete problems. This collects and extends mappings to the Ising model from partitioning, covering, and satisfiability. In each case, the required number of spins is at most cubic in the size of the problem. This work may be useful in designing adiabatic quantum optimization algorithms.

**Keywords:** spin glasses, complexity theory, adiabatic quantum computation, NP, algorithms

---

## 1. INTRODUCTION

### 1.1. QUANTUM ADIABATIC OPTIMIZATION

Recently, there has been much interest in the possibility of using adiabatic quantum optimization (AQO) to solve NP-complete and NP-hard problems [1, 2]. This is due to the following trick: suppose we have a quantum Hamiltonian $H_P$ whose ground state encodes the solution to a problem of interest, and another Hamiltonian $H_0$ whose ground state is "easy" (both to find and to prepare in an experimental setup). Then, if we prepare a quantum system to be in the ground state of $H_0$, and then adiabatically change the Hamiltonian for a time $T$ according to

$$H(t) = \left(1 - \frac{t}{T}\right)H_0 + \frac{t}{T}H_P,\tag{1}$$

then if $T$ is large enough, and $H_0$ and $H_P$ do not commute, the quantum system will remain in the ground state for all times, by the adiabatic theorem of quantum mechanics. At time $T$, measuring the quantum state will return a solution of our problem.

There has been debate about whether or not these algorithms would actually be useful; i.e., whether an adiabatic quantum optimizer would run any faster than classical algorithms [3–9], due to the fact that if the problem has size $N$, one typically finds

$$T = O\left[\exp\left(\alpha N^\beta\right)\right],\tag{2}$$

in order for the system to remain in the ground state, for positive constants $\alpha$ and $\beta$, as $N \to \infty$. This is a consequence of the requirement that exponentially small energy gaps between the ground state of $H(t)$ and the first excited state, at some intermediate time, not lead to landau-zener transitions into

excited states [5]$^2$. While it is unlikely that NP-complete problems can be solved in polynomial time by AQO, the coefficients $\alpha$, $\beta$ may be smaller than known classical algorithms, so there is still a possibility that an AQO algorithm may be more efficient than classical algorithms, on some classes of problems.

There has been substantial experimental progress toward building a device capable of running such algorithms [11–13], when the Hamiltonian $H_P$ may be written as the quantum version of an Ising spin glass. A classical Ising model can be written as a quadratic function of a set of $N$ spins $s_i = \pm 1$:

$$H(s_1,\ldots,s_N) = -\sum_{i < j} J_{ij}s_i s_j - \sum_{i=1}^N h_i s_i.\tag{3}$$

The quantum version of this Hamiltonian is simply

$$H_P = H\left(\sigma_1^z,\ldots,\sigma_N^z\right)\tag{4}$$

where $\sigma_i^z$ is a Pauli matrix (a $2 \times 2$ matrix, whose cousin $(1 + \sigma_i^z)/2$ has eigenvalues 0, 1) acting on the $i$-th qubit in a Hilbert space of $N$ qubits $\{|-, \rangle, |-\rangle\}^{\otimes N}$, and $h_i$ and $J_{ij}$ are real numbers. We then choose $H_0$ to consist of transverse magnetic fields [11]:

$$H_0 = -h_0 \sum_{i=1}^N \sigma_i^x,\tag{5}$$

so that the ground state of $H_0$ is an equal superposition of all possible states in the eigenbasis of $H_P$ [equivalent to the eigenbasis of the set of operators $\sigma_i^z$ $(i = 1, \ldots, N)$]. This means that one$^3$

$^2$ If one is only interested in approximate solutions (for example, finding a state whose energy per site is optimal, in the thermodynamic ($N \to \infty$) limit, one expects $T = O(N^\gamma)$ [5, 10].

$^3$ In this paper, when a generic statement is true for both NP-complete and NP-hard problems, we will refer to these problems as NP problems. Formally, this can be misleading as P is contained in NP; but for ease of notation we will simply write NP.

---

## 1.2. ISING SPIN GLASSES

Ising spin glasses$^4$ are known to be the NP-hard problems for classical computers [17], so it is natural to ask whether connections with all other NP problems. For the purposes of this paper, an NP-complete problem is always a decision problem with a yes or no answer (does the ground state of some $H = 0?), whereas an NP-hard problem is an optimization problem (what is the ground state energy of $H$?). The class of NP-complete problems includes a variety of notoriously hard problems, and has thus attracted much interest over the last 40 years [18, 19]. Mathematically, because the decision form of the Ising model is NP-complete, there exists a polynomial time mapping to any other NP-complete problem.

Analogies between the statistical physics of Ising spin glasses and NP problems have been frequently studied in the past [20–22], and have been used to construct simulated annealing algorithms for problems on classical computers. These connections have suggested a physical understanding of the emergence of computational hardness in these problems via a complex energy landscape with many local minima [24]. Conversely, computational hardness of solving glassy problems has applications for the difficulty of the solutions to important scientific problems ranging from polymer folding [25, 26] to monetary [27] to collective decision making in economics and social sciences [28, 29]. Problems of practical scientific interest have already been encoded and solved (in simple instances) on experimental devices using Hamiltonians [30–35].

Finally, we note that Ising glasses often go by the name QUBO (quadratic unconstrained binary optimization), in the more mathematical literature [36]. Useful tools have been developed to fix the values of some spins immediately [38] and to decompose large QUBO problems [39].

### 1.3. THE GOAL OF THIS PAPER

Mathematically, the fact that a problem is NP-complete means we can find a mapping to the decision form of the Ising model with a polynomial number of spins. This mapping can be-inclined as a pseudo-Boolean optimization problem [37]. As the constructions of these pseudo-Boolean optimization problems (or "spin glasses") often lead to three-body or higher interactions in $H$ (e.g., $[40, 41]$), we get from any NP-complete problem to the Hamiltonian of an Ising spin glass, whose decision problem encodes the ground state energy. We will thus focus the optimization problem—the NP-complete decision problem. We will thus also provide a review of some of the simple maps from partitioning and satisfiability to spin glasses. In particular, we will describe how "all of the famous NP problems"$^5$ [Karp [18] and Johnson [19]] can be written down as Ising models with a polynomial number of spins which scales no faster than $N^3$. For most of this paper, we will find it no more difficult to solve the NP-hard optimization problem vis the NP-complete decision problem, and as such we will usually focus on the optimization problems. The techniques employed in this paper, which are rare elsewhere in the quantum computation literature, are primarily a new focus, which roughly correspond to the tackling the following issues: minimas optimization problems, problems with inequalities as constraints (for example, $n = 1$), and problems which ask global questions about graphs.

The methods we use to phrase these problems as Ising glasses generically naturally.

### 1.4. WHAT PROBLEMS ARE EASY (TO EMBED) ON EXPERIMENTAL AQO DEVICES?

Before the reader may be inspired, after reading this paper, to think about solving some of these classical computing problems, or others like them, on experimental devices implementing AQO, toward this end, the reader should look for three things in the implementations in this paper. First is the number of spins required to encode the problem. In some instances, the "logical spins/bits" (the spins which are required to encode a solution of the problem) are the only spins required, but in general, we may require auxiliary "ancilla spins/bits", which are required to enforce constraints in the problem. Sometimes, the number of ancilla bits required can be quite large, and can be the dominant fraction of the spins in the Hamiltonian. Another thing to watch out for is the possible separations of energy scales required; e.g., the ratio of couplings $J_{ij}/J_{33}$ in some Ising glasses is proportional to $N$, the size of the problem being studied. A final thing to note is whether or not the graph must be highly connected: does the typical degree of vertices on the Ising embedding graph

$^4$ No offense to anyone whose problems have been left out.

---

## 2. PARTITIONING PROBLEMS

The first class of problems we will study are partitioning problems, which (as the name suggests) are problems about dividing a set into two subsets. These maps are celebrated in the spin glass community [24], as they helped physicists realize the possibility of using spin glass technology to understand computational hardness in random ensembles of computing problems. For completeness, we review these mappings here, and present a new one based on similar ideas (the clique problem).

### 2.1. NUMBER PARTITIONING

Number partitioning asks the following: given a set of $N$ positive numbers $S = \{s_1, \ldots, s_N\}$, is there a partition of this set of numbers into two disjoint subsets $R$ and $\bar{R}$, such that the sum of the elements in both sets is the same? For example, can one divide a set of assets with values $n_1, \ldots, n_N$, fairly between two people? This problem is known to be NP-complete [18]. This can be phrased initially as an Ising model as follows. Let $n_i$ $(i = 1, \ldots, N = |S|)$ describe the numbers in set $S$, and let

$$H = A\left(\sum_{i=1}^N n_i s_i\right)^2\tag{6}$$

$^5$ These devices use quantum annealing, which is the finite temperature generalization of AQO. For this paper, this is not an important issue, although it can certainly be relevant to experiments.

---

## 2.2. GRAPH PARTITIONING

Graph partitioning is the original [20] example of a map between the physics of Ising spins and NP-complete problems. Let us consider an undirected graph $G = (V,E)$, with an enum $|V| = N$ of vertices. We ask: what is a partition of the set $V$ into two subsets of equal size $N/2$ such that the number of edges connecting the two subsets is minimized? This problem has many applications: finding these partitions can allow us to run some graph algorithms in parallel on the two partitions, and then make some modifications due to the few connecting edges at the end [39]. Graph partitioning is known to be an NP-hard problem; the corresponding decision problem (are there fewer than $K$ edges connecting the two sets?) is NP-complete [18]. We will present an Ising model on each vertex $v \in V$ on the graph, and we will let $+1$ and $-1$ denote the vertex being in either the $+$ set or the $-$ set. We solve this with an energy functional consisting of two components:

$$H = H_A + H_B\tag{7}$$

where

$$H_A = A\left(\sum_{i=1}^N s_i\right)^2\tag{8}$$

is an energy which provides a penalty if the number of elements in one subset is not equal to the number in the $-$ set, and

$$H_B = B\sum_{(uv) \in E} \frac{1 - s_u s_v}{2}\tag{9}$$

is a term which provides an energy penalty $B$ for each time that an edge connects vertices from different subsets. If $B > 0$, then we wish to minimize the number of edges between the two subsets; if $B < 0$, we will choose to maximize this number. Should we choose $B < 0$, we must ensure that it is small enough so that it is never favorable to violate the constraints of $H_A$ in order to minimize energy. To determine a rather simple lower bound on the constrained optimization problem, let us ask the question: what is the minimum value of $\Delta H_p$ for violating the $A$-constraint is $\Delta H_A \geq 2A$. The best gain we can get by flipping a spin to gain an energy of $B\min(A, N/2)$, where $A$ is the maximal degree of $G^2$. We conclude

$$\frac{A}{B} = \frac{\min(2A, N)}{8}\tag{10}$$

$N$ spins on a complete graph are required to encode this problem.

When the Hamiltonian under the same gauge transformation $s_i \to -s_i$. We conclude that we can always remove one spin by fixing a gauge series to be in the $+$ set.

We have written $H$ in a slightly different form than the original [20], which employed a constraint on the space of solutions to the problem, that

$$\sum_{i=1}^N s_i = 0.\tag{11}$$

We will want none of our formulations to do this (i.e., we wish to not encode unconstrained optimization problem). Instead, we encode constraint equations by making penalty Hamiltonians which raise the energy of a state which violates them.

---

## 2.3. CLIQUES

A clique of size $K$ in an undirected graph $G = (V,E)$ is a subset $W \subseteq V$ of the vertices, of size $|W| = K$, such that the subgraph $(W, E_W)$ restricted to edges between nodes in $W)$ is a complete graph—i.e., all possible $K(K-1)/2$

$^7$ The reason we can use $N/2$ in this formula instead of $N$ has to do with the fact that we are "perfoming" a solution where $H_A = 0$. Due to the fact that the $H_A$ constraint is very penalizing if it is violated by having many spins in the same partition, it is easy to see that cases where an energy gain of $(N - 1)/8$ can be obtained by flipping a spin are very energetically penalized, and not relevant to the discussion.

edges in the graph are present, because every vertex in the clique has an edge to every other vertex in the clique. Cliques in social networks can be useful as they are "communities of friends"; finding anomalously large cliques is also a key sign that there is structure in a graph which may appear to otherwise be random [46]. The NP-complete decision problem of whether or not a clique of size $K$ exists [18] can be written as an Ising-like model, as follows. We place a spin variable $s_i = \pm1$ on each vertex $v \in V$ of the graph. In general, in this paper, for a spin variable $s_u$, we will define the binary bit variable

$$x_a \equiv \frac{s_a + 1}{2}\tag{12}$$

It will typically be more convenient to phrase the energies in terms of this variable $x_a$, as $x_a$ will be for this problem. Note that any energy functional which was quadratic in $x_a$, and twice in $x_a$, and vice versa, so we are free to use either variable. We then choose

$$H = A\left(K - \sum_a x_a\right)^2 + B\left[\frac{K(K-1)}{2} - \sum_{(uv) \in E} x_u x_v\right]\tag{13}$$

where $A, B > 0$ are positive constants. We want the ground state of this Hamiltonian is $H = 0$ if and only if a clique of size $K$ exists. It is easy to see that $H = 0$ if there is a clique of size $K$. However, we wish to now show that $H \neq 0$ for any other solution. It is easy to see that if there are $n$ x$_i$'s which are 1, that the minimum possible value of $H$ is

$$H_{\text{min}}(n) = A(n-K)^2 + B\frac{K(K-1) - n(n-1)}{2}$$

$$= (n-K)\left[A(n-K) - B\frac{n + K - 1}{2}\right]\tag{14}$$

The most "dangerous" possible value of $n = 1 + K$. We can easily see that as long as $A > KB$, $H_{\min}(K+1) > 0$. We finally note that, given a ground state solution, it is of course easy to read off from the $x_i$ which form a clique. $N$ spins on a complete graph are required to solve this problem.

A quantum algorithm for this NP-complete problem can be made slightly more efficient; so as the initial state can be carefully prepared [47].

The NP-hard version of the clique problem asks us to find (one of) the largest cliques in a graph. We can modify the above Hamiltonian to account for this, by adding an extra variable $u_i$ $(i = 2, \ldots, \Delta)$, which is 1 if the largest clique has size $i$, and 0 otherwise. Let $H = H_A + H_B + H_C$ where

$$H_A = A\left(1 - \sum_{i=2}^{\Delta} y_i\right) + A\left(\sum_{i=2}^{\Delta} iy_i - \sum_v x_v\right)^2\tag{15}$$

and

$$H_B = B\left[\frac{1}{2}\left(\sum_{i=2}^{\Delta} iy_i\right)\left(-1 + \sum_{i=2}^{\Delta} iy_i\right) - \sum_{(uv) \in E} x_u x_v\right].\tag{16}$$

---

We want cliques to satisfy $H_A = H_B = 0$, and to be the only ground states. The Hamiltonian above satisfies the constraint $H_A = 0$ are always satisfied—we can see this by noting that the first term of $H_A$ forces us to pick only one of the y_i$; the second forces only one of the y_i$ to choose $n$ vertices. Then $H_B = 0$ ensures that we have a clique. Similarly to the discussion above, we see that the absolute energy states are cliques$^8$, have to find the state with the smallest value of $y_n$. This can be obtained by choosing

$$H = -C\sum_v x_v,\tag{17}$$

where $C > 0$ is some constant. If $C$ is small enough, then the ground state energy is $H = -CK$, where $K$ is the size of the largest clique in the graph. To determine an upper bound on $C$, so that we solve the cliques problem (as opposed to some other problem), we need to make sure that it is never favorable to color an extra vertex, at the expense of mildly violating the $H_A$ constraint. The penalty for coloring an extra vertex, given $y_i = n$, is at minimum

$$A = \min(2A, n).\tag{10}$$

However, this gain might not be enough to change the energy outcome, so we use

So, for example, we could take $A = (\Lambda + 2)B$ and $B = C$.

### 2.4. REDUCING $N$ TO $\log N$ SPINS IN SOME CONSTRAINTS

There is a trick which can be used to dramatically reduce the number of extra $y_i$ spins which must be added, in the NP-hard version of the clique problem above [48]. In general, this trick is usable throughout this paper, as we will see similar constructions of auxiliary $y_i$'s appearing repeatedly.

We know that we want to encode a variable which can take the values $2, \ldots, N$ (or $\Lambda$, if we know the maximal degree of the graph—the argument is identical either way). For simplicity, suppose $M$ so that

$$2^M \leq N < 2^{M+1}.\tag{19}$$

Alternatively, $M = \lfloor\log N\rfloor$—in this paper, the base 2 is implied in the logarithm. In this case, we only need $M + 1$ binary variables: $y_0, \ldots, y_M$, instead of $N$ binary variables, $y_1, \ldots, y_N$, to encode a variable which can take $N$ values. It is easy to check that

$$\sum_{a=1}^N n_a - \sum_{n=0}^{M-1} 2^n y_n + (N + 1 - 2^M)y_M\tag{20}$$

solves the same clique problem, without loss of generality. (This is true in general for all of our NP problems.) If $N \geq 2^{M+1} - 1$, the ground state may be degenerate, as the summation of $y_i$ to a given integer is not always unique. When actually encoding these

$^8$ The ground state has $H = 0$ so as the edge set is non-empty: any connected pair of edges is a clique of size 2.

---

## 3. BINARY INTEGER LINEAR PROGRAMMING

Let $x_1, \ldots, x_N$ be $N$ binary variables, which we arrange into a vector **x**. The binary integer linear programming (ILP) problem asks: what is the largest value of **c**·**x** for some vector **c**, given a constraint

$$\mathbf{S}\mathbf{x} = \mathbf{b}\tag{21}$$

with **S** an $m \times N$ matrix and **b** a vector with $m$ components. This is NP-hard [18], with a corresponding NP-complete decision problem. Many problems can be posed as ILP; e.g., a supplier who wants to maximize profit given regulatory constraints [48].

The Ising Hamiltonian corresponding to this problem can be constructed as Ising Hamiltonian $H = H_A + H_B$ where

$$H_A = A\sum_{j=1}^m\left[b_j - \sum_{i=1}^N S_{ji}x_i\right]^2\tag{22}$$

and $A > 0$ is a constant. The ground states of $H_A = 0$ enforce (if such a ground state exists, of course) the constraint that **Sx** = **b**. Then we set

$$H_B = -B\sum_{i=1}^N c_i x_i,\tag{23}$$

with $B \ll A$ another positive constant.

To find constraints on the required ratio $A/B$, we proceed similarly to before. For simplicity, let us assume the constraint is Equation [21] is for some choice of $x$. For such a choice, the largest possible value of $-\Delta H_B$ is, in principle, $BC$, where

$$C = \sum_{i=1}^N \max(c_i, 0).\tag{24}$$

The smallest possible value of $\Delta H_A$ is related to the properties of the matrix **S**, and would occur if we only violate a single constraint, and violate that constraint by the smallest possible amount, given by

$$S = \min_{c_i \in \{0,1\}, j}\left[\max\left(1, \frac{1}{2}\sum_i(-1)^b S_{ji}\right)\right].\tag{25}$$

This bound could be made better if we knew more specific properties of **S** and/or **b**. We conclude

$$\frac{A}{B} \geq \frac{C}{S}\tag{26}$$

If the coefficients $c_i$ and $S_{ji}$ are $O(1)$ integers, we have $C \leq N\max(c_i)$, and $S \geq 1$, so we conclude $A/B \gtrsim N$.

---

## 4. COVERING AND PACKING PROBLEMS

In this section, we discuss another example class of mappings from NP problems to Ising models: "covering" and "packing" problems. These problems can often be thought of as asking: how can I pick some objects out of a set (such as vertices out of a graph's vertex set) so that they "cover" the graph in some way (e.g., removing them makes the edge set empty). In this class of problems, there are constraints which must be satisfied. Many of the problems described below are often discussed in the literature, but again we review them here for completeness. We conclude the section with the minimal maximal matching problem, which is a slightly more involved problem that has not been discussed in the AQO literature before.

These are, by far, the most popular class of problems discussed in the AQO literature. As we mentioned in the introduction, this is because this is the only class of NP problems (discussed in this paper) for which it is easy to embed the problem via a graph which is not complete (or close to complete).

### 4.1. EXACT COVER

The exact cover problem goes as follows: consider a set $U = \{1, \ldots, n\}$, and subsets $V_i \subseteq U$ $(i = 1, \ldots, N)$ such that

$$U = \bigcup_i V_i.\tag{27}$$

The question is: is there a subset of the set of sets $\{V_i\}$, called $R$, such that the elements of $R$ are disjoint sets, and the union of the elements of $R$ is $U$? This problem was described in Choi [49] but for simplicity, we repeat it here. This decision problem is NP-complete [18]. The Hamiltonian we use is

$$H_A = A\sum_{k=1}^n\left(1 - \sum_{i \in S_k} x_i\right)^2.\tag{28}$$

In the above Hamiltonian $\alpha$ denotes the elements of $U$, while $i$ denotes the subsets $V_i$. $H_A = 0$ precisely when every element is included exactly one time, which implies that the unions are disjoint. The existence of a ground state of energy $H = 0$ corresponds to the existence of a solution to the exact cover problem.

If the ground state is degenerate, there are multiple solutions. $N$ spins are required.

It is also straightforward to extend this, and find the smallest exact cover (this makes the problem NP hard). This is done by simply adding a second energy term: $H = H_A + H_B$, with $H_A$ given above, and

$$H_B = B\sum_i x_i.\tag{29}$$

The ground state of this model will be $mB$, where $m$ is the smallest number of subsets required. To find the ratio $A/B$ required to encode the correct problem, we note that the worst case scenario is that there are a very small number of subsets with a single element (it excluded [i]). 

### 4.2. SET PACKING

Let us consider the same setup as the previous problem, but now ask a different question: what is the largest number of subsets $V_i$, which are all disjoint? This is called the set packing problem; this optimization problem is NP-hard [18]. To do this, we use $H = H_A + H_B$:

$$H_A = A\sum_{u \in U}x_u x_v,\tag{30}$$

which is minimized only when all subsets are disjoint. Then, we use

$$H_B = -B\sum_i x_i\tag{31}$$

which simply counts the number of sets included. Choosing $B < A$ ensures that it is never favorable to violate the constraint $H_A$ (since there will always be a penalty of at least $A$ per extra set included [i]).

Note that an isomorphic formulation of this problem, in the context of graph theory, is to follow: let us consider the sets to be encoded in an undirected graph $G = (V,E)$, where each set $V_i$ maps to a vertex $i \in V$. An edge $i$-$e$ exists when $V_i \cap V_j \neq \emptyset$. It is straightforward to see that if we replace

$$H_A = A\sum_{uv \in E} x_u x_v\tag{32}$$

that the question of what is the maximal number of vertices which may be "colored" ($x_i = 1$) such that no two colored vertices are connected by an edge, is exactly equivalent to the set packing problem described above. This version is called the maximal independent set (MIS) problem.

### 4.3. VERTEX COVER

Given an undirected graph $G = (V,E)$, what is the smallest number of vertices that can be "colored" such that every edge is incident to at-least one colored vertex? This is NP-hard; the decision form is NP-complete [18]. Let $x_v$ be a binary variable on each vertex $v \in V$, which is 1 if it is colored, and 0 if it is not colored. The Hamiltonian we use is $H = H_A + H_B$. The constraint is that every edge has at least one colored vertex is encoded in $H_A$:

$$H_A = A\sum_{uv \in E}(1-x_u)(1-x_v).\tag{33}$$

Then, we want to minimize the number of colored vertices with $H_B$:

$$H_B = B\sum_v x_v\tag{34}$$

$^9$ The example where $V = \{\{1,2\}, \{3\}, \ldots, \{n\}, \{2, \ldots, n\}\}$ shows that to find order in $n$; this bound is optimal.

---

## 4.4. SATISFIABILITY

Satisfiability is one of the most famous NP-complete problems [18]. Every satisfiability problem can be written as a so-called 3SAT problem in conjunctive normal form (and this algorithm takes only polynomial time) and so we will focus on simplicity on this case. In this case, we ask whether

$$\Psi = C_1 \wedge C_2 \wedge \cdots \wedge C_m\tag{35}$$

can take on the value of true—i.e., every $C_i$ for $1 \leq i \leq m$ is true, where the form of each $C_i$ is:

$$C_i = y_{n} \vee y_n \vee y_{n}\tag{36}$$

Here $y_{n}$, $\bar{y}_n$, and $\bar{y}_{n}$ are selected from another set of Boolean variables: $x_1, \ldots, x_N$, $\bar{x}_1, \ldots, \bar{x}_N$. This is a very brief description of satisfiability; readers who are unfamiliar with this problem should read appropriate chapters of Mezard and Montanari [24].

There is a well-known reduction of 3SAT to MIS [49] which we reproduce here, for completeness. Consider solving the set the NP-hard version of MIS problem on a graph. To encode this problem, we construct an auxiliary graph with $3m$ nodes, which we construct as follows. For each clause $C_i$, we add 3 nodes to the graph, and connect each node to the other 3. After this step, if there is a $y_1$ such that $y_1$ and $\bar{x}_1$ are in the clause, then we add a node for $x_1$, and we only connect all equally to pick vertices corresponding to the variable which is true. If $x_1$ is true and $\bar{x}_1$ is true, we are required to connect all 3 nodes within a corresponding triangle node. However, in this case, there must be an element of each clause which is true; because the fact that the triangle nodes are related (once more clause is true, so let us denote whether one of the three y_i$'s has been colored will be 1), then the related value of the decision-making problem on the graph. So this has an edge between these two nodes. Solving MIS on this graph, and asking whether the solution (the same as a decision is solved as follows: if a solution to the 3SAT problem exists, only one element of each clause needs to be true—if more more true, then the edge set is larger, so the solution has a lower energy. We can see as an on NP-hard version of this problem (if we have to violate some clauses, what is the fewest number to violate?) by solving the optimization version of the MIS problem.

### 4.5. MINIMAL MAXIMAL MATCHING

The minimal maximal (minmax) matching problem on a graph is defined as follows: let $G = (V,E)$ denote an undirected graph, and let $C \subseteq E$ be a proposed "coloring". The constraints on $C$ are as follows: i.e., let $D = \bigcup_{e \in C} de$. We will then demand that: no two edges in $C$ (coloring any appropriate vertices) without violating the first constraint, and maximal in the sense that the trivial empty set of solution is not allowed—we must include all edges between uncolored vertices.

---

Note that, from this point on in this paper, we have not found any of the simple formulations of this problem in the literature.

We will use the spins on the graph to model whether or not an edge is colored. Let us use the binary variable $x_e$ to denote whether or not an edge is colored; thus, the number of spins is $|E| = O(\Lambda N)$, the size of the edge set; as before, $\Lambda$ represents the size of the edge set; as before, $\Delta$ represents the subset of $E$ of edges which connect to $v$. Thus the ground state consist of $H = H_A + H_B + H_C$.

The first and largest term, $H_A$, will impose the constraint that no vertices has two colored edges. This can be done by setting

$$H_A = A\sum_v \sum_{(c_1,c_2) \in \partial v}\sum_{c_1,c_2 \in \partial v} x_{c_1} x_{c_2}.\tag{38}$$

Here $A > 0$ is a positive energy, and $\partial v$ corresponds to the subset of $E$ of edges which connect to $v$. Thus the ground states consist of $H = H_A + H_B + H_C$.

The variable energy $H_B$, such that solutions to the minimax coloring problem are minimized:

$$y_v \equiv \begin{cases} 1 & \text{if } v \text{ has a colored edge} \\ 0 & \text{if } v \text{ has no colored edges} \end{cases} = \sum_{e \in \partial v} x_e.\tag{39}$$

We see that this definition is only valid for states with $H_A = 0$, since in these states each vertex has either 0 or 1 colored edges. We then define the energy $H_B$, such that solutions to the minimax coloring problem should minimize the coloring:

$$H_B = B\sum_{e = (uv)} (1 - y_u)(1 - y_v).\tag{40}$$

Note that since $1 - y_v$ can be negative, we must choose $B > 0$ to be small enough. To bound $B$, we note that the only problem (a missing term in $H_B$) occurs when $y_u = 0, y_v > 1$, and $(uv) \in E$. Suppose that of $v$'s neighbors have $y_u = 0$. Then, the contributions to $H_A$ and $H_B$ associated to node $v$ are given by

$$H_A = A\frac{y_v(y_v - 1)}{2} - B(y_v - 1)m,\tag{41}$$

Note that $m + y_v \leq k$, if $k$ is the degree of node $v$. Putting all of this together, we conclude that if $A > (\Lambda - 2)B$, then it is never favorable to have $y_v > 1$. This will ensure that ground state of $H_A + H_B$ will have $H_A = H_B = 0$; i.e., states which do not violate the minimax constraints.

Now, given the states where $H_A = H_B = 0$, we now want the ground state of $H_A + H_B + H_C$ to be the state where the fewest number of edges are colored. To do this, we simply let

$$H_C = C\sum_e x_e\tag{43}$$

count the number of colored edges. Here $C$ is an energy scale chosen to be small enough so that it is never energetically favorable to violate the constraints imposed by either $H_A$ or $H_B$ terms: one requires $C < B$, since if an energy penalty of $B$ associated to each colored edge which could be colored, yet still not violate the coloring constraint, is... The term with the smallest $H_C$ has the smallest number of edges, and is clearly the solution to the minimax problem. ground state solution of this spin model is equivalent to a solution of the minimax problem.

---

## 5. PROBLEMS WITH INEQUALITIES

We now turn to NP problems whose formulations as Ising models are more subtle, due to the fact that constraints involve inequalities as opposed to equalities. These constraints can be viewed as a generalized version of the inequalities, as opposed to as constraints only involving equalities by an expansion of the number of spins.

As with partitioning problems, we will find that these Hamiltonians require embedding highly connected graphs onto a quantum device. This may limit their usability on current hardware.

### 5.1. SET COVER

Consider a set $U = \{1, \ldots, n\}$, with sets $V_i \subseteq U$ $(i = 1, \ldots, N)$ such that

$$U = \bigcup_{i=1}^N V_a.\tag{44}$$

The set covering problem is to find the smallest possible number of $V_i$'s, such that the union of these $V_i$ is equal to $U$. This is a generalization of the exact covering problem, where we do not require each element to appear an equal number of times. Set covers are used to find multiple problems for computational purposes, and set covering is known to be NP-hard [18].

Let us denote $x_i$ to be a binary variable which is 1 if set $i$ is included, and 0 if set $i$ is not included. Let us then denote $x_{a,m}$ to be a binary variable which is 1 if the number of $V_i$ which include element $a$ is $m \geq 1$, and 0 otherwise. Set $H = H_A + H_B$. Our first energy imposes the constraints that exactly one $x_{a,m}$ must be 1, since each element of $U$ must be included a fixed number of times, and that the number of $V_i$ we have included, with $\alpha$ as an element:

$$H_A = A\sum_{a=1}^n\left(1 - \sum_{m=1}^M x_{a,m}\right)^2$$

$$+A\sum_{a=1}^n\left(\sum_{m=1}^M mx_{a,m} - \sum_{i \in V_a} x_i\right)^2.\tag{45}$$

---

### 5.2. KNAPSACK WITH INTEGER WEIGHTS

The knapsack problem is the following problem: we have a list of $N$ objects, labeled by indices $a$, with the weight each object given by $w_a$, and its value given by $c_a$, and we have a knapsack which can only carry weight $W$. If such a binary variable denoting whether (1) or not (0) object $a$ is contained in the knapsack, the total weight in the knapsack is

$$W = \sum_{a=1}^N w_a x_a\tag{47}$$

and the total cost is

$$C = \sum_{a=1}^N c_a x_a.\tag{48}$$

The NP-hard [18] knapsack problem asks us to maximize $C$ subject to the constraint that $W \leq W$. It has a huge variety of applications, particularly in economics and finance [50].

Let $y_n$ for $1 \leq n \leq W$ denote a binary variable which is 1 if the final weight of the knapsack is $n$, and 0 otherwise. Our solution consists of writing $H = H_A + H_B$, with

$$H_A = A\left(1 - \sum_{y_i} y_i\right) + A\left(\sum_{a=1}^N w_a y_a - \sum_{a=1}^N w_a x_a\right)^2\tag{49}$$

which enforces that the weight can only take on one value and that the weight of the objects in the knapsack equals the value we claimed it did, and finally

$$H_B = -B\sum_a c_a x_a.\tag{50}$$

As we require that it is not possible to find a solution where $H_A$ is weakly violated at the expense of $H_B$ becoming more negative, we require $0 < B\max(c_a) < A$ (adding one to the knapsack, which makes it too heavy, is not allowed). The number of spins required is (using the log trick) $N + [1 + \log W]$.

---

## 6. COLORING PROBLEMS

We now turn to coloring problems. Naively, coloring problems are often best phrased as Potts models [51], where the spins can

take on more than two values, but these classical Potts models can be converted to classical Ising models with an expansion of the number of spins. This simple trick forms the basis for our solution to this class of problems.

### 6.1. GRAPH COLORING

Given an undirected graph $G = (V,E)$, and a set of $n$ colors, is it possible to color each vertex in the graph with a specific color, such that no edge connects two vertices of the same color? This is one of the more famous NP-complete [18] problems, as one can prove that a map from the generalization of the problem (how many colors are needed to color a map, such that no two countries which share a border have the same color) has been useful.

Of course, in this special case$^{10}$, one can prove that a map requires at most $n \geq 4$ [52, 53]. This problem is called the graph coloring problem.

Our solution consists of the following: we denote $x_{v,i}$ to be a binary variable which is 1 if vertex $v$ is colored with color $i$, and 0 otherwise. The energy is

$$H = A\sum_{v=1}^n\left(1 - \sum_{i} x_{v,i}\right) + A\sum_{(uv) \in E} \sum_{i=1}^n x_{u,i}x_{v,i}.\tag{51}$$

The first term enforces the constraint that each vertex has exactly one color, provides an energy penalty each time this constraint is violated. In the second term, since the sum over $v$ of $x_{v,i}$ counts the number of nodes with color $i$, the first sum counts the highest possible number of edges that could exist with color $i$. The second term then checks if, in fact, this number of edges does in fact exist. Thus if a ground state exists with $H = 0$, there is a solution to the coloring problem on this with a coloring scheme by looking at which color each node (in one such coloring scheme) by looking at which color of the nodes on (one one such coloring scheme) by looking at which color of each node (in one such coloring scheme) by looking at which color of the nodes on (one one such coloring scheme) by looking at which color of each node (in one such coloring scheme) by looking at which color of each node (in one such coloring scheme) by looking at which color of each node (in one such coloring scheme) by looking at which color of each node (in one such coloring scheme) by looking at which color of each node (in one such coloring scheme) by looking at which color of each node (in one such coloring scheme) by looking at which color of each node (in one such coloring scheme) by looking at which color of the coloring scheme by looking at which color of the of the coloringg scheme by looking at which color of each one such coloring scheme) by looking at which is colored, since there is a permutation symmetry among colorings, by choosing a specific node in the graph to have the color 1, and one of its neighbors to have the color 2, for example. The total number of spins required is thus $nN$.

### 6.2. CLIQUE COVER

The clique cover problem, for an undirected graph $G = (V,E)$, is the following: given $n$ colors, we assign a distinct color to each vertex of $W_1, \ldots, W_i$, of $V$ corresponding to each color, and $E_{n_1}, \ldots, E_{n}$, the edge set restricted to edges between vertices in the $W_j$ sets. The clique cover problem asks whether or not $(W_i, E_{W_i})$ is a complete graph for each $W_i$ (i.e., does each set of colored vertices form a clique?). This problem is known to be NP-complete [18].

Again, we employ the same energy strategy variables as for graph coloring, and use a Hamiltonian very similar to the cliques problem:

$$H = A\sum_{v=1}^n\left(1 - \sum_{i=1}^n x_{v,i}\right) + B\sum_{i=1}^n\left[\frac{1}{2}\left(-1 + \sum_{v \in W_i} x_{v,i}\right)\right]$$

$$\sum_{v,i} - \sum_{(uv) \in E} x_{u,i}x_{v,i}\right].\tag{52}$$

$^{10}$ The graphs are planar—the vertices can be realized by points on $\mathbb{R}^2$, and the edges as line segments between them, such that no two line segments intersect (except at a vertex).

---

## 7. HAMILTONIAN CYCLES

In this section, we describe the solution to the (undirected) Hamiltonian cycles problem, and subsequently the traveling salesman problem, which for the Ising spin glass formulation, is a trivial extension.

### 7.1. HAMILTONIAN CYCLES AND PATHS

Let $G = (V,E)$, and $N = |V|$. The graph can either be directed or undirected; our method of solution will not change. Hamiltonian path problem is as follows: starting at some node in the graph, can one travel along an edge, visiting other nodes in the graph, such that one can visit every single node in the graph without ever returning to the same node twice? The Hamiltonian cycles problem asks that, in addition, the traveler can return to the starting point from the last node he visits. Hamiltonian cycles are a generalization of the famous Konigsberg problem [24], and is NP-complete [18].

Without loss of generality, let us label the vertices $1, \ldots, N$, and let the edge set be directed—i.e., the order in a prospective cycle. Our solution will use $N^2$ bits $x_{ij}$, where $x_{ij}$ represents the vertex $i$ and represents its order in a prospective cycle. Our energy will have components. The first two things we require are that every vertex can only appear once in a cycle, and that there must be a $j$-th element in the cycle for each $j$. Finally, for the nodes in our prospective ordering, the $x_{ij}$ and $x_{ji}$ are both spins that are excluded (if we are solving the cycles problem, these are encoded in the Hamiltonian:

$$H = A\sum_{i=1}^N\left(1 - \sum_{j=1}^N x_{i,j}\right) + A\sum_{j=1}^N\left(1 - \sum_{i=1}^N x_{i,j}\right)$$

$$+ A\sum_{(uv) \in E} \sum_{j=1}^N x_{u,j}x_{v,j+1}.\tag{56}$$

$A > 0$ is a constant. It is clear that a ground state of this system has $H = 0$ only if we have an ordering of vertices where each vertex is only included once, and there are edges on the graph—i.e., we have a Hamiltonian cycle.

To solve the Hamiltonian path problem, we ask whether or not the first and last nodes are also connected. $N^2$ spins are required to solve this problem.

It is straightforward to slightly reduce the size of the state space for the Hamiltonian cycles problem to exclude all following initial node 1 must always be included in a Hamiltonian cycle, and without loss of generality we can set $x_{1j} = \delta_{j1}$. This just means that the overall ordering of the cycle is chosen so that node 1 comes first. This reduces the number of spins to $(N - 1)^2$.

### 7.2. TRAVELING SALESMAN

The traveling salesman problem for a graph $G = (V,E)$, where each edge $uv$ in the graph has a weight $W_{uv}$ associated with it, is

---

to find the Hamiltonian cycle such that the sum of the weights of each edge in the cycle is minimized. Typically, the traveling salesman problem assumes a complete graph, but we have the technology developed to solve it on a more arbitrary graph. The decision NP-complete [18].

To solve this problem, we use $H = H_A + H_B$, with $H_A$ the Hamiltonian given for the directed (or undirected) Hamiltonian cycles problem. We then simply add

$$H_B = B\sum_{(uv) \in E} \sum_{j=1}^N W_{uv}x_{u,j}x_{v,j+1},\tag{57}$$

with $B$ small enough that it is never favorable to violate the constraints of $H_A$ one constraint is $B \leq max(W_{uv}) < A$ (we assume in complete generality $W_{uv} \geq 0$ for each $(uv) \in E$.)$^{11}$ If the traveling salesman does not have to return to his starting position, we can restrict the sum over $j$ from 1 to $N - 1$, as before. As with Hamiltonian cycles, $(N - 1)^2$ spins are required, as we may fix nodes 1 to appear first in the cycle.

---

## 8. TREE PROBLEMS

The most subtle NP problems to solve with Ising models are problems which require finding connected tree subgraphs of larger graphs.$^{12}$ Because determining whether a subgraph is a tree requires global information about the connectivity of a graph, we will rely on similar tricks to what we used to write down Hamiltonian cycles as an Ising model.

### 8.1. MINIMAL SPANNING TREE WITH A MAXIMAL DEGREE CONSTRAINT

The minimal spanning tree problem is the following: given an undirected graph $G = (V,E)$, where each edge $(uv) \in E$ is associated with a cost $c_{uv}$, what is the tree $T \subseteq G$, which contains all vertices, such that the cost of $T$, defined as

$$c(T) \equiv \sum_{(uv) \in E_T} c_{uv},\tag{58}$$

is minimized (if such a tree exists)? Without loss of generality, we take $c_{uv} > 0$ in this subsection (a positive constant can always be added to each $c_{uv}$ ensure that the smallest value of $c_{uv}$ is strictly positive). We will also add a degree constraint, that each degree $n$ be $\leq \Delta$. This makes the problem NP-hard, with a corresponding NP-complete decision problem [18].

To solve this problem, we place a binary variable $y_e$ on each edge to determine whether or not that edge is included in $T$:

---

$$y_e \equiv \begin{cases} 1 & e \in E_T \\ 0 & \text{otherwise} \end{cases}\tag{59}$$

We also place a large number of binary variables $x_{v,j}$ on each vertex, and $x_{uv}, x_{uv,i}$ on edge $(uv)$ (these are distinct spins): $x_{uv}, x_{uv,i} \in \{0, 1, \ldots, 0\}$ will be used to track of a node in the tree, if $x_{uv} = 1$, it means that it is closer to the root. Finally, we use another variable $x_{j,i}$ (i = 1, . . . $\Lambda$) to count the number of degrees of each node. We now use energy $H = H_A + H_B$, where the first two terms in $H_A$ are used to impose the constraints that: there is exactly one root to the tree, each vertex has a depth, each bond has a depth, and its two vertices must be at different depths in the tree as connected (i.e., each one edge has a depth at all lower depth), each node can have at most $\Delta$ edges, and each edge at depth points between a node at depth $i$ and $i$ respectively:

$$H_A = A\left(1 - \sum_{v,i} x_{v,i}\right) + A\sum_v\left(1 - \sum_{v,i} x_{v,i}\right)^2$$

$$+ A\sum_{(uv) \in E}\left(y_v - \sum_{v,i} x_{v,i}\right)^2$$

$$+ A\sum_v\left(y_{uv} - \sum_{(x_{u,i} + x_{u,i})} \right)^2$$

$$+ A\sum_i\left[\sum_{v=1}^{N/2}\left(x_{v,i} - \sum_{(uv) \in E} x_{u,i}x_{v,i}\right)\right]^2$$

$$+ A\sum_v\left[\sum_{i=1}^{\Lambda}\left(x_{e,i} - \sum_{(uv) \in E} x_{u,i}(2 - x_{u,i-1} - x_{v,i})\right)\right]^2$$

$$+ A\sum_{(uv) \in E \in 1}(2 - x_{u,i-1} - x_{v,i}).\tag{60}$$

The ground states with $H_A = 0$ are trees which include every vertex. In the last term in the sum over $j$ above from 1 to $N - 1$; we do not care about whether or not the first and last nodes are also connected. $N^2$ spins are required to solve this problem.

It is straightforward to slightly reduce the size of the state space for the Hamiltonian cycles problem to exclude all following initial node 1 must always be included in a Hamiltonian cycle, and without loss of generality we can set $x_{1j} = \delta_{j1}$. This just means that the overall ordering of the cycle is chosen so that node 1 comes first. This reduces the number of spins to $(N - 1)^2$.

In order to solve the correct problem, we need to make sure that we never remove any spins from $H_A$, in order to have a negative ground state energy $H$. As each constraint in $H_A$ contributes an energy $\geq 2$ if it is violated, we need

The number of spins required is $|V| \cdot (|V| + 1] + 2|E|/2 - |E|)$. The maximal possible number of edges on any graph is $|E| = O(|V|^2)$, so this Ising formulation may require a cubic number of spins in the size of the vertices set.

### 8.2. STEINER TREES

The NP-hard [18] Steiner tree problem is somewhat similar to the problem above: given our costs $c_{uv}$, we want to find a minimal spanning tree for a subset $U \subseteq V$ of the vertices (i.e., a tree such that the sum of $c_{uv}$ along all included edges is minimal).

We no longer impose degree constraints; the problem turns out to be hard to let us allow for the possibility of not including nodes which are not in $U$.

To solve this by finding the ground state of an Ising model, we use the same Hamiltonian as for the minimal spanning tree, except we add binary variables $y_v$ for $v \notin U$ which determine whether or not a node is included in the tree. We use the same Hamiltonian $H = H_A + H_B$, where $H_A$ enforces constraints as in the previous case:

$$H_A = A\left(1 - \sum_v y_v - \sum_{v \in U} x_{v,i}\right) + A\sum_v\left(1 - \sum_{v,i} x_{v,i}\right)^2$$

$$+ A\sum_{(uv) \in E}\left(y_v - \sum_{v,i} x_{v,i}\right)^2$$

$$+ A\sum_v\left[(y_{uv} - \sum_{(x_{u,i} + x_{u,i} + y_w + y_{uv})] ^2$$

$$+ A\sum_{(u,w) \in E: i =1}^{N/2}\left(x_{v,i} - \sum_{(uv) \in E} x_{u,i}x_{v,i}\right)$$

$$+ A\sum_{(uv) \in E: i=1}^{N/2} x_{u,i}(2 - x_{u,i-1} - x_{v,i})\tag{62}$$

We then use $H_B$ from the previous model to determine the minimum weight tree; the same constraints on $A/B$ apply. The number of spins is $|V|(|V| + 1] + |E|$.

### 8.3. DIRECTED FEEDBACK VERTEX SET

A feedback vertex set for a directed graph $G = (V,E)$ is a subset $F \subseteq V$ such that the subgraph $(V - F, \partial(V - F))$ is acyclic (has no cycles). We refer to $F$ as the feedback set. Solving a decision problem for whether or not a feedback set exists for $|F| \leq k$ is NP-complete [18]. We solve the optimization problem of finding the smallest size of the feedback set first for a directed graph—the extension to an undirected graph will be a bit involved.

Before solving this problem, it will help to prove two lemmas.

The first lemma is quite simple: there exists a node in a directed acyclic graph which is the end point of any edges. Suppose that for each vertex, there was an edge that ends on that vertex.

Then pick an arbitrary vertex, pick any edge ending on that vertex. Repeat this process more than $N$ times, and by a simple counting argument implies that we must have visited the same node more than once. Thus, we have traversed a cycle in reverse, which contradicts our assumption.

The second lemma is as follows: a directed graph $G = (V,E)$ is acyclic if and only if there exists a height function $h : V \to \mathbb{N}$ such that for every edge $(u,v) \in E$, $h(u) < h(v)$; i.e., every edge points from a node at

---

lower height to a higher height. That height function existence implies acyclicity is the contrapositive: suppose that a graph is cyclic. Then of a cycle of edges, we have

$$0 < \sum_{(u,i \in Cycle)} [h(u+1) - h(u_a)] = h(u_0) - h(u_a) + h(u_a)$$
$$- h(u_{a-1}) + \cdots + h(u_i) = 0\tag{63}$$

is a contradiction. To prove that an acyclic graph has a height function, we construct one recursively. Using our first lemma, we know that there exists a vertex $u$ with only outgoing edges, so let us call $h(u) = 1$. For any other vertex $u$, we will call the height of that vertex $h(v) = 1 + h(v')$, where $h(v')$ is found by repeating this process on the graph with node $u$ removed (which must also be acyclic). It is clear this process will terminate and assign exactly one height for each integer $1 \leq i \leq |V|$.

We can now exploit this lemma to write down an Ising formulation of this problem. We place a binary variable $y_v$ on each vertex, which is 0 if $v$ is part of the feedback set, and 1 otherwise. We then place a binary variable $x_{v,i}$ on each vertex, which is 1 if vertex $v$ is at height $i$. So far the heights are arbitrary, and the requirement that a height function be valid will be imposed by the energy. The energy functional we use is $H = H_A + H_B$:

$$H_A = A\sum_v\left(y_v - \sum_{i} x_{v,i}\right) + A\sum_i \sum_{(u,v) \in E} x_{u,i}x_{v,i}\tag{64}$$

The first term ensures that if a vertex is not part of the feedback set, it has a well defined height. The second term ensures that an edge only connects a node with lower height to a node at higher height.

We then find the smallest possible feedback set by adding

$$H_B = B\sum_{(1 - y_v)}.\tag{65}$$

In order to solve the correct problem, we cannot add too few nodes to the feedback set. If we set $y_v = 1$ for a node which should be part of the feedback set, we find an energy penalty of $\Delta H$ from $H_A$, and a gain of $B$ from $H_B$ and a gain of $B$ from $H_A$ which is of course many constraints in $H_A$ which rises constraint will have an energy gain of a sufficient $\Delta H$; a A is a sufficient to ensure we solve the correct problem. We have that $|V|(|V| + 1)$ spins are required.

---

## 8.4. UNDIRECTED FEEDBACK VERTEX SET

The extension to undirected graphs requires a bit more care. In this case, we have to be careful because there is no a priori distinction on whether the height of one end of an edge is larger than the other—this makes the problem much more involved. It is a well-known fact that a feedback vertex set must reduce the graph to trees, although there is no longer a requirement that these trees are connected (this is called a forest). With this in mind, we find that the problem is actually extremely similar to minimal spanning tree, but without degree constraints or connectivity constraints. The new subtlety, however, is that we cannot remove edges.

If the ground state of this Hamiltonian has $H = 0$, there is an isomorphic $N^2$ spins required.

An approximate algorithm that uses quantum annealing to distinguish between non-isomorphic graphs via the spectra of graph-dependent Hamiltonians was presented in Hen and Young [56].

---

## 9. GRAPH ISOMORPHISMS

Graphs $(V_1, E_1)$ and $G_2 = (V_2, E_2)$ with $N$ vertices each, are isomorphic if there is a labeling of vertices $1, \ldots, N$ in each graph such that the adjacency matrix for the two graphs are identical. Note carefully: Any graph $G = (V,E)$, with vertices labeled as $1, \ldots, N$, has an $N \times N$ adjacency matrix $A$ with

$$A_{ij} = \begin{cases} 1 & (ij) \in E, \\ 0 & (ij) \notin E, \end{cases}\tag{70}$$

which contains all information about the edge set $E$. Let $A_{1,2}$ be the adjacency matrices of graphs $G_1$ and $G_2$, and suppose that there is a permutation matrix $P$ such that $A_2 = P^T A_1 P$, then we say $G_{1,2}$ are isomorphic.

The question of whether two graphs $G_1 = (V_1, E_1)$ and $G_2 = (V_2, E_2)$ are isomorphic is believed to be hard in classical complexity [55]. Since it is (in practice) a hard problem, let us nevertheless describe an Ising formulation for it. An isomorphism is only possible if $|V_1| = |V_2| = N$, so we will restrict ourselves to this case, and without loss of generality, we label the vertices of $G_1$ with $1, \ldots, N$.

We write this as an Ising model as follows. Let us describe a proposed isomorphism through binary variables $x_{v,j}$ which is 1 if vertex $v$ in $G_2$ gets mapped to vertex $j$ in $G_1$. The energy:

$$H_A = A\sum_v\left(1 - \sum_i x_{v,i}\right) + A\sum_i\left(1 - \sum_v x_{v,i}\right)\tag{71}$$

ensures that this map is bijective. We then use an energy

$$H_B = B\sum_{u \in E_1, uv \notin E_2} x_{u,i}x_{v,j} + B\sum_{u \in E_2, uv \notin E_1} x_{u,i}x_{v,j}\tag{72}$$

to penalize a bad mapping; i.e., an edge that is not in $G_1$ is in $G_2$, or an edge that is in $G_1$ is not in $G_2$. As usual, assume $A, B > 0$.

---

## 10. CONCLUSION

The focus of recent input into AQO has essentially been on NP-complete/hard problems, because the Ising model is NP-hard, and because computer scientists have struggled to find efficient ways of solving these problems. In this paper, we have presented strategies for mapping a wide variety of NP problems to Ising glasses, exemplified by a demonstration of a glass for each of Karp's 21 NP-complete problems. It is an open question the extent to which AQO will help provide efficient solutions for these problems, whether these solutions are exact or approximate.

However, physicists are interested in building a universal quantum computer which is capable of solving much more than just Ising models. As an example, a universal quantum computer would also reduce the time for searching an unsorted list of $N$ items from $O(N)$ to $O(\sqrt{N})$ [57]. This would be incredibly useful for many practical applications, despite the fact that searching is an easy linear time algorithm. Analogously, it may be the case that there exists a family of "easy" problems which AQO can solve in polynomial time, yet more efficiently than a classical polynomial time algorithm. This statement may even be true with Ising-implementing AQO hardware, although if so it is not obvious.

It is certainly the case that an AQO-implementing device can be used to solve easy problems. Consider the simple problem of finding the largest integer in a list $n_1, \ldots, n_N$ (this is the searching algorithm that a universal quantum computer can perform efficiently). Introducing binary variables $x_i$ for $i = 1, \ldots, N$, the quantum device can perform efficiently, introducing binary variables $x_i$ for $i = 1, \ldots, N$, the most instances of the random field Ising model on a complete graph, and yet this has a very simple $O(N)$ classical algorithm. It would surely take longer to program this problem into a quantum device than to solve the problem itself.

The above example demonstrates that sometimes the "hardness" of a problem can be deceptive—one can phrase something that is easy in a way which makes it seem hard. It is worth discussing more closely the hardness of NP problems, because it turns out that sometimes NP problems can be easier than they first appear. To be NP-complete but not in P (if P $\neq$ NP) only needs a small family of instances of the problem to be unsolvable in polynomial time by a deterministic algorithm. However, typical instances may not be hard. Many popular NP problems can almost surely be solved exactly in polynomial time on typical instances [58, 59]$^{15}$, and there exist randomized algorithms for some NP problems which can arbitrarily close to a solution with arbitrarily low failure probability in polynomial time [60, 61] (though multiplicative error on typical instances are hard. Many recent developments focus on randomized algorithms [62–64].

---

## ACKNOWLEDGMENTS

Andrew Lucas is supported by the Smith Family Graduate Science and Engineering Fellowship at Harvard. He would like to thank Robert Lucas for pointing out that a compendium of work on random NP problems has been lacking. He would also like to thank Jacob Biamonte for encouraging publications, and Vicky Choi, Jacob Markus, Federico Spedalieri, Brian Tran, and others for many helpful comments on AQO and computer science.

---

## MATERIALS AND METHODS

This paper discusses theoretical results; no materials are needed. The methodology used was discussed throughout the paper.

---

## REFERENCES

1. Farhi E, Goldstone J, Gutmann S, Lapan J, Lundgren A, Preda D. A quantum adiabatic evolution algorithm applied to random instances of an NP-complete problem. Science (2001) 292:2292–2301. doi: 10.1126/science.1057726

2. Das A, Chakrabarti BK. Colloquium quantum annealing and analog quantum computation. Rev Mod Phys (2008) 80:1061–1081. doi: 10.1103/RevModPhys.80.1061

3. Altshuler B, Krovi H, Roland J, Anderson localization makes adiabatic quantum optimization fail. Proc Natl Acad Sci USA (2010) 107:12446–12450. doi: 10.1073/pnas.1002116107

4. Altshuler B, Krovi H, Röland J. Anderson localization makes adiabatic quantum optimization fail. Phys Rev Lett (2011) 106:050502. doi: 10.1103/PhysRevLett.2011.050502

5. Rapat V, Foin L, Kzakski F, Semerijin E, Zamponi F. First-order transitions and the performance of quantum adiabatic optimization problems on random instances of two optimization problems on regular hypergraphs. Phys Rev Lett (2012) 108:206506. doi: 10.1103/PhysRevLett.2012.206506

6. Hen I, Young AP. Exponential complexity of the quantum adiabatic algorithm for certain NP-hard problems. Phys Rev E (2011) 84:061152. doi: 10.1103/PhysRevE.84.061152

7. Santoro GE, Martoňák R, Tosatti E, Car R. Theory of quantum annealing of an Ising spin glass. Science (2002) 295:2427. doi: 10.1126/science.1068774

8. Santoro GE, Martoňák R, Tosatti E, Car R. Quantum annealing of an Ising spin glass. Science (2002) 295:2427–2432. doi: 10.1126/science.1068774

9. Ising M. Beitrag zur Theorie des Ferromagnetismus. Zeitschrift für Physik (1925) 31:253–258. doi: 10.1007/BF01352670

10. Kannan R, Kumar S, Salter M, Sharma M, Liang JM. Classical computational complexity of computing discrete logarithms. Phys Rev Lett (2013) 110:1407. doi: 10.1103/PhysRevLett.2013.1407

11. Boixo S, Ronnow TF, Isakov SV, Wang Z, Wecker D, Lidar DA, et al. Quantum annealing in the limit of large physical qubits. Science (2013) 345:202–206. doi: 10.1126/science.1250070

12. Boixo S, Ronnow TF, Isakov SV, Wang Z, Wecker D, Lidar DA, et al. Quantum annealing in the limit of large physical qubits. Nature (2013) 473:194. doi: 10.1038/nature12373

13. Deelmans JR, Young AP. Exponential complexity of the quantum adiabatic algorithm for certain NP-hard problems. Phys Rev Lett (2011) 110:1305. doi: 10.1103/PhysRevLett.2011.1305

14. Whitfield JD, Faccin M, Biamonte JD. Ground state logic. Eurphys Lett (2012) 99:20005. doi: 10.1209/0295-5075/20005

15. Whitfield JD, Love PJ. Realizable Hamiltonians for universal adiabatic quantum computation. Rev Mod Phys (2008) 80:012552. doi: 10.1103/PhysRevA.78.012552

16. Herrera SA, DiVincenzo DP, Oliveira RI, Terhal BM. The complexity of stoquastic Hamiltonian problems. Quantum Inform Comput (2008) 8:0361. Available at: http://arxiv.org/abs/quant-ph/0606140

17. Barahona F. On the computational complexity of Ising spin glass problems. J Phys A (1982) 15:3241. doi: 10.1088/0305-4470/15/10/028

18. Garey MR, Johnson DS. Computers and Intractability: A Guide to the Theory of NP-Completeness. San Francisco, CA: W.H. Freeman (1979).

19. Choi V. Minor-embedding in adiabatic quantum computation: I. The parameter setting problems. arXiv:0804.4259.

20. Do Y, Anderson P. Application of statistical mechanics to NP-complete problems in combinatorial optimization. J Phys A (1986) A19:1605. Available at: https://arxiv.org/abs/stat-mech/0606340

21. de la Linde J, Pervin G. Spin Glass Theory and Beyond. Singapore: World Scientific (1987).

22. Hartmann AK, Weigt M. Phase Transitions in Combinatorial Optimization Problems: Basics, Algorithms and Statistical Mechanics. Weinheim: Wiley-VCH (2005).

23. Kirkpatrick S, Gelatt CD, Vecchi MP. Optimization by simulated annealing. Science (1983) 220:4598. doi: 10.1126/science.220.4598.671

24. Mézard M, Parisi G, Virasoro MR. Spin Glass Theory and Beyond. Oxford: Oxford University Press (2009). doi: 10.1093/oso/9780198507837.001.0001

25. Bryngelson JD, Wolynes PG. Spin glasses and the statistical mechanics of protein folding. Phys Nat Lett (1987) 847:524. doi: 10.1038/847524

26. Frauenfelder H. Protein folding in the hydrophobic-hydrophilic (HP) model in NP-complete. J Comput Biol (1998) 5:27. doi: 10.1089/cmb.1998.5.27

27. Hendrickson D, Leland P. A Multi-level Algorithm for Partitioning Graphs. Sandia Tech. Report (1993) 93-1301.

28. Bouchard JD. Cross and collective socio-economic phenomena: simple models and challenges. Proc Natl Acad Sci USA (2002) 100:6682-6687. doi: 10.1073/pnas.0913074107

29. Bouchaud JD. Cross-collective socio-economic phenomena: simple models and challenges. Proc Natl Acad Sci USA (2002) 100:6682. doi: 10.1073/pnas.0913074107

30. Lucas A, Lee CH, Mullieable binary decision making on networks. Nat Comput (2012) 11:239-286. doi: 10.1007/s11047-012-9294-0

31. Chen DJ, Hao CR, Johnson J. Experimental and numerical studies of a potential application of a hybrid optimization. Phys Rev Lett (2013) 3:4967. doi: 10.1103/PhysRevLett.2013.3830

32. Perdomo-Ortiz A, Dickson N, Drew-Brook M, Rose G, Aspuru-Guzik A. Finding low-energy conformations of lattice protein models by quantum annealing. Sci Rep (2012) 2:571. doi: 10.1038/srep00571

33. Riboholm R, Perdomo-Ortiz A, O'Gorman B, Aspuru-Guzik A. Construction of energy functions for lattice heteropolymer models: a case study with a constraint solving paradigm and adiabatic quantum optimization (2013). Available online at: http://arxiv.org/abs/1211.3422

34. Novotini H, Mukhopadhyay W, Weise image recognition with adiabatic quantum computers. Rept (2009). Available at: http://arxiv.org/abs/1457

35. Dehmev V, Ding N, Vladimirshyn SVN, Neveu H. Robust desynchronization with adiabatic quantum optimization. Proceedings of the 29th International Conference on Machine Learning (Edinburgh, 2012): 863.

36. Boros E, Hammer PL. Pseudo-Boolean optimization. Discrete Appl Math (1991) 31:351. doi: 10.1007/BF02186053

37. Boros E, Hammer PL. Pseudo-Boolean optimization. Discrete Appl Math (2002) 123:155-190. doi: 10.1016/j/dam.2002.06490

38. Neven H, Denchev V, Drew-Brook M, Zhang J, Ding W, Marshall S, Chiaroni D, Macready WG. Training a Binary Classifier with the Quantum Adiabatic Algorithm. arXiv:0811.4423. doi: 10.1007/s11128-008-0082-9

39. Billionnaeat A, Iumaud B. A decomposition method for minimizing quadratic pseudo-Boolean functions. Oper Res Lett (1989) 8:161. doi: 10.1016/0167-6377(89)90054

40. Biamonte JD. Non-perturbative k-body to two-body commuting conversion. arXiv:1307.1809. doi: 10.1145/0394.627

41. Babbush R, O'Gorman B, Aspuru-Guzik A. Resource efficient digital quantum simulation of d-level systems by hybridizing with unitary k-body interactions. arXiv:1307.5857. doi: 10.1002/qua.22559120

42. Choi V. Minor-embedding in adiabatic quantum computation: I. The parameter setting problems. Quantum Inform Process (2008) 7:193–209. doi: 10.1007/s11128-008-0082-9

43. Choi V. Minor-embedding in adiabatic quantum computation: II. Minor-universal graph design. Quantum Inform Proc (2011) 10:343. doi: 10.1007/s11128-010-0200-3

44. Choi V. Minor-embedding in adiabatic quantum computation: II. Minor-universal graph design. Quantum Inform Proces (2011) 10:343. doi: 10.1007/s11128-010-0200-3

45. Kiyono C, Sullivan BD, Humble TS. Adiabatic quantum programming: minor embedding with hard constraints. arXiv:1210.6495. Available online at: http://arxiv.org/abs/1210.6495

46. Khasabag N, Shalker N. Finding a large hidden clique in a random graph. Proceedings of the 35th Annual ACM Symposium on Theory of Computing. San Diego (1998) 2418–2418. doi: 10.1016/0166-218X(98)3:433-CO-2

47. Choi V. Adiabatic quantum algorithms for the NP-complete maximum weight independent set, exact cover and 3SAT problems (2010). Available online at: http://arxiv.org/abs/1004.2226

48. Schrijver A. Theory of Integer and Linear Programming. Chichester, NY: Wiley (1998).

49. Choi V. Adiabatic quantum algorithms for the NP-complete maximum-weight independent set, exact cover and 3SAT problems (2010). Available online at: http://arxiv.org/abs/1004.2226

50. Kellerer H, Pferschy U. Knapsack Problems. Berlin: Springer (2004). doi: 10.1007/978-3-540-24777-7

51. Wu FY. The Potts model. Rev Mod Phys (1982) 54:1. doi: 10.1103/RevModPhys.54.1

52. Appel K, Haken W. Every planar map is four colorable. Illinois J Math (1976) 21:429. doi: 10.1215/ijm/1256049011

53. Appel K, Haken W. Every planar map is four colorable. Illinois J Math (1977) 21:429.

54. Zhou HJ. Spin glass approach to the feedback vertex set problem. arXiv:2013-06001. doi: 10.1088/1742-5468/2013-06-P06001

55. Bryingkslau JD, Wolynes PG. Spin glasses and the statistical mechanics of protein folding. Nat Lett (1987) 847:524. doi: 10.1038/847524

56. Bryan DS, Chidham S, Macready WG, Clark L, Cartan F, Dickson N, et al. Experimental determination of Ramsey numbers. Phys Rev Lett (2013) 111:130505. doi: 10.1103/PhysRevLett.2013.130505

57. Bian N, Chudak F, Macready WG, Clark L, Cartan F, Dickson N, et al. Experimental determination of Ramsey numbers. Phys Rev Lett (2013) 111:130505. doi: 10.1103/PhysRevLett.2013.130505

58. Sorkin GB, Stein C. Computers and Intractability: A Guide to the Theory of NP-Completeness. San Francisco, CA: W.H. Freeman (1979).

59. Bian N, Chudak F, Macready WG, Clark L. A polynomial-time algorithm for finding expected polynomial time algorithm. Parallsl Process Lett. 2012; 22(5). arXiv: 1211.13505

60. Dyer M, Frieze A, Kannan R. A random polynomial-time algorithm for approximating the volume of convex bodies. J ACM (1991) 38:1. doi: 10.1145/102782.102783

61. Dyer M, Frieze A, Kannan R. A random polynomial-time algorithm for approximating the volume of convex bodies. J ACM (1991) 38:1. doi: 10.1145/102782.102783

62. Xu N, Zhu J, Lu D, Zhou X, Peng X, Du J. Quantum factorization of 143 on a dipolar-coupling nuclear magnetic resonance quantum processor. Phys Rev Lett (2012) 108:130501. doi: 10.1103/PhysRevLett.2012.130501 [Uranium] (2012) 108:130902|E. doi: 10.1103/PhysRevLett.2012.130902E

63. Bian Z, Chudak F, Macready WG, Clark L. Cartan F. Experimental determination of Ramsey numbers. Phys Rev Lett (2013) 111:130505. doi: 10.1103/PhysRevLett.2013.130505

---

**Conflict of Interest Statement:** The author declares that the research was conducted in the absence of any commercial or financial relationships that could be construed as a potential conflict of interest.

**Received:** 09 November 2012; **accepted:** 24 January 2014; **published online:** 12 February 2014.

**Citation:** Lucas A. Ising formulations of many NP problems. Front. Physics 2:5. doi: 10.3389/fphy.2014.00005

This article was submitted to Interdisciplinary Physics, a section of the journal Frontiers in Physics.

**Copyright © 2014 Lucas. This is an open-access article distributed under the terms of the Creative Commons Attribution License (CC BY). The use, distribution or reproduction in other forums is permitted, provided the original author(s) or licensor are credited and that the original publication in this journal is cited, in accordance with accepted academic practice. No use, distribution or reproduction is permitted which does not comply with these terms.**
