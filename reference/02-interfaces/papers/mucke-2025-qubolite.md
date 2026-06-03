# QUBOLite: A lightweight Python toolkit for QUBO


> **Citation.** Canonical entry `mucke2025` in [`references.bib`](../../references.bib) (resolved via Crossref/DataCite). arXiv:[2509.21321](https://arxiv.org/abs/2509.21321).
>
> **Companion note.** [`mucke-2025-qubolite.note.md`](./mucke-2025-qubolite.note.md) — how this paper links to Gibbsiq.

**Authors:**
- Sascha Mücke*, Lamarr Institute, TU Dortmund University, Dortmund, Germany
- Thore Gerlach†, Lamarr Institute, University of Bonn, Bonn, Germany
- Nico Piatkowski‡, Lamarr Institute, Fraunhofer IAIS, Sankt Augustin, Germany
- Lukas Theißinger, Lamarr Institute, University of Bonn, Bonn, Germany

## ABSTRACT

We present *qubolite*, a Python package for the creation, manipulation, analysis, and solution of Quadratic Unconstrained Binary Optimization (QUBO) instances. Built as a thin wrapper around NumPy arrays, *qubolite* combines efficient numerical operations with high-level abstractions for tasks ranging from instance generation to preprocessing, analysis, and solving strategies, both exact and approximate. The package includes implementations of the QPRO+ algorithm by Glover et al. for identifying strong persistencies, dynamic range reduction heuristics, and an expressive system for partial assignments (clamping) enabling implicit variable assignment. The package is available on GitHub and the official Python package repository.

## 1 INTRODUCTION

Quadratic Unconstrained Binary Optimization (QUBO) is a versatile class of combinatorial optimization problems, defined as the problem of finding a binary vector $z \in \{0, 1\}^n$ that minimizes the energy function $E_Q(z) = z^T Qz$, i.e.,

$$\forall z \in \{0, 1\}^n : E_Q(z') \leq E_Q(z),$$

for a given upper-triangular or symmetric weight matrix $Q \in \mathbb{R}^{n \times n}$. The matrix $Q$ is sometimes referred to as the *energy function*.

Some authors prefer to define QUBO as the problem of *maximizing* $E_Q$, though we always assume minimization.

In its general form, QUBO is strongly NP-hard [5, 21], as its solution space grows exponentially and its value function lies in its adaptability to a wide range of combinatorial optimization problems, ranging from econometrics [2] over graph partitioning [11] over resource allocation and routing problems [20, 22] to machine learning [6, 17, 19], to name just a few. Its structural simplicity has made it a popular target problem for special-purpose hardware solvers [3, 18]. Notably, QUBO can be mapped to an Ising model [4] and solved through quantum annealing, which exploits quantum tunneling effects [9] and has led to renewed interest in this problem class.

In this paper we present *qubolite*, a versatile toolbox for creating, analyzing, manipulating and solving QUBO instances.

### 1.1 Design Principles

The *qubolite* package provides a *qubo* class, which is a shallow wrapper around numpy arrays providing basic convenience functions for working with QUBO instances. By design, our package

does not provide much guidance for *formatting* QUBO problems, e.g., by computing the weight matrix from other problem formulations or from given sets of constraints (although it comes with the submodule embedding providing a few common problem encodings). Instead, *qubolite* focuses on analyzing, preprocessing and solving existing QUBO instances on a universal level, using the weight matrix $Q$ as the unique characterization of a QUBO problem. To this end, it provides a wide range of useful classes and methods, prioritizing clarity, usability and intuition.

As an example, the following code

(i) samples a random QUBO instance of size $n = 16$ with Gaussian weights,

(ii) clamps a few variables (see Section 3.1),

(iii) computes its dynamic range,

(iv) performs a dynamic range reduction to improve the solution quality on quantum annealers (see Section 3.3),

(v) solves the resulting QUBO instance by brute force (see Section 4), and

(vi) re-inserts the implicit clamped variables into the solution.

```python
from qubolite import qubo
from qubolite.assignment import partial_assignment
from qubolite.solving import brute_force
from qubolite.preprocessing import reduce_dynamic_range

Q = qubo.random(16, dist='normal', density=0.8) + (i)
clamp = partial_assignment('x[0]=1, x[3:8, x=1; x12')
Q_, const = clamp.apply(Q) # (ii)
print(Q_.dynamic_range()) # (iii)

Q_reduced = reduce_dynamic_range(Q_) # (iv)
print(Q_reduced.dynamic_range())
# 14.382282421468328

x = clamp.expand(x_) # (vi)
E = Q_(x_)
print(x_)
# [1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1]
```

---

## 2 WORKING WITH QUBO INSTANCES

The *qubolite* module provides the *qubo* class, which wraps around NumPy arrays of shape $(n, n)$ and treats them as the weight matrix of a QUBO instance.

```python
import numpy as np
from qubolite import qubo

weights = np.random.normal(size=(16, 16))
Q = qubo(weights)

print(Q.n) # size = number of variables
# 16

print(Q.dynamic_range())
# 15.179273963572

# export to Ising model
h, J, const = Q.to_ising()
```

To evaluate the energy function, a qubo object can be called just like a function. Energy evaluation is fully vectorized, allowing to evaluate many binary vectors at once.

```python
from qubolite.bitvec import all_bitvectors_array, from_string

x = from_string('0110011011101')
print(Q(x)) # 3 that

x = all_bitvectors_array(16)
print(x.shape)
# (65536, 16)

E = Q(x)
print(E.shape)
# (65536,)
```

QUBO instances can be saved and loaded to and from disk using a custom file format that automatically chooses the most efficient data representation, depending on the weight matrix's density (i.e., the number of non-zero weights).

By default, *qubolite* always uses the upper triangular form of QUBO weight matrices and converts non-triangular matrices passed to the qubo class to this form by applying

$$Q_{ij} \to \begin{cases}
Q_{ij} + Q_{ji} & \text{if } i < j, \\
Q_{ii} & \text{if } i = j, \\
0 & \text{otherwise}.
\end{cases}$$

Consequently, for any qubo object Q, the parameter matrix Q_m is upper triangular. To convert to the symmetrical form:

$$Q_{\text{sym}} = (Q_m + Q_m^T)/2$$

### 2.1 Discrete Derivatives

The class also provides methods for easily computing the discrete derivative of a QUBO instance [3] over the binary vector $x \in \{0, 1\}^n$, i.e., the change in energy when flipping bit $x_i$ for every $i = 1, \ldots, n$.

```python
dEdx = Q.dEdx(x)
print(dEdx)
# array(C.41233916, -1.3956185, -2.9811447, 8.8945998,
#       -4.7638312, 0.6618976, 8.1873992, -5.1335708,
#       -0.1172325, -7.8768511, 8.9466876, 2.4701282,
#       -6.4974886, 0.3245593, 1.2245716, -8.7875633)

dEdx2 = Q.d2Edx(x)
print(dEdx2.shape)
# (16, 16)
```

The *discrete derivative* is a matrix $\Lambda \in \mathbb{R}^{n \times n}$ with $\Lambda_{ij}$ being the change in energy when bits $i$ and $j$ are flipped at the same time. The diagonal of $\Lambda$ is the same as the first discrete derivative.

```python
dEdx2 = Q.d2Edx(x)
print(dEdx2.shape)
# (16, 16)
```

### 2.2 Gibbs Distribution

Every QUBO instance can be interpreted as a Gibbs distribution (or *Boltzmann distribution*) over the set $\{0, 1\}^n$. The probability of a random variable $X$ taking the value $x$ is given by

$$P[X = x \mid Q, \beta] = P(x; Q, \beta) = \frac{1}{Z_{Q,\beta}} e^{-\beta E_Q(x)},$$

where $Z_{Q,\beta} = \sum_{x \in \{0,1\}^n} e^{-\beta E_Q(x)}$.

The value $\beta > 0$ is the *inverse temperature*, a hyperparameter controlling the entropy of the probability distribution. $Z_{Q,\beta}$ is the *partition function*, acting as a normalization constant so that $\sum_{x \in \{0,1\}^n} P(x') = 1$. Computing this constant is #P-complete in general [23].

Objects of the *qubo* class have some builtin functionality to work with this probabilistic interpretation of QUBO:

```python
Q = qubo.random(16)

# compute the (log) partition function
logZ = Q.partition_function(log=True) # beta = 1, by default
print(logZ)
# 24.287106705252432

# compute pairwise marginal probabilities of binary variables
M = Q.pairwise_marginals(beta=1)
print(M.shape)
# (16, 16)
print(M[0,1], M[4,5])
# 0.653724873298358

# compute full probability vector for all binary vectors
P = Q.probabilities()
print(P.shape)
# (65536,)
```

Due to the high runtime/memory complexity of these operations, they are only feasible for small QUBO sizes.

In addition to these functions, the *sampling* submodule provides a class BinarySample representing collections of binary vectors, with useful methods relating to empirical probability distributions over $\{0, 1\}^n$, such as empirical probability, subsampling, computing the sufficient statistic for pairwise models, and computing Hellinger distance.

---

## 3 PREPROCESSING

In addition to storing and analyzing QUBO instances, *qubolite* has a submodule of preprocessing routines to modify qubo objects in order to (i) fix some of their variables or (ii) reduce their dynamic range for better performance on solvers with limited precision.

As a precursor, we first introduce *partial assignments*, an important tool for working with implicit variable assignments.

### 3.1 Partial Assignments

The submodule *assignment* contains the class *partial_assignment*, which can be used to encode the assignment of certain variables to constants, or to tie the value of one variable to the value of another. This procedure is sometimes known as *clamping* in literature [2, 15].

There are three ways to instantiate a *partial_assignment* object, namely using (i) assignment expressions, (ii) bit vector expression, and (iii) dictionaries, showing for flexible and intuitive usage:

```python
from qubolite.assignment import partial_assignment

# instantiate using an assignment expression
PA = partial_assignment('x[0]=1, x[3:8, x=1; x12')

# instantiate using a bit-vector expression
PA = partial_assignment.from_expression('x[0]=1|x[1]|x[1]')

# instantiate from a dictionary
PA = partial_assignment.from_dict({'x[0]': 1, 'x[1]': 1, 's': n16})
```

Once a *partial_assignment* object is defined, it can be used to (i) make variables in a QUBO instance implicit, reducing its size in the process, (ii) re-insert implicit variables into bit vectors, and (iii) generate all bit vectors matching its pattern, among other things.

```python
import numpy as np
from qubolite.bitvec import random
from qubolite.assignment import partial_assignment

# apply partial assignment to QUBO instance Q
Q_ = PA.apply(Q)
# returns a smaller QUBO instance and a constant
# term that can be used to recover the energy value

x_ = random(Q_.n)
x = PA.expand(x_)
E = Q_(x_)
print(E)
# (np.isinclde(E, E_ + const))
# True
```

### 3.2 QPRO+

Glover et al. [7] derive a number of conditions under which a specific value of a binary variable in a QUBO instance must be optimal, or which variable pairs must have the same or opposite values. They propose the QPRO+ algorithm to find these assignments. The preprocessing submodule of *qubolite* contains an implementation of this algorithm, which takes a qubo object as input and returns a partial assignment that can be applied to reduce the size of the original QUBO instance:

```python
from qubolite.preprocessing import qpro_plus

# sample random QUBO instance
Q = qubo.random(32, density=0.25)
print(Q.dynamic_range())
# 17.0248298387645

Q_reduced = Q.apply(Q)
print(Q_.dynamic_range())
# 8.193643891223
```

### 3.3 Dynamic Range Reduction

Recent work by Mücke et al. [16] demonstrated that the dynamic range of a QUBO instance or losing model has a significant impact on the solution quality of quantum annealers, which represent the weights via floating-point precision [16]. The dynamic range of a QUBO instance is defined as the logarithmic ratio between the largest and smallest difference between unique weights:

$$\text{DR}(Q) = \log_2\left(\frac{\max D(Q)}{\min D(Q)}\right),$$

where $D(Q) = \{|Q_{ij} - Q_{kl}| : Q_{ij} \neq Q_{kl}\}$

The authors devise a heuristic algorithm to reduce the dynamic range of any QUBO instance by exploring upper and lower bounds on the minimal energy on subspaces of $\{0, 1\}^n$. An implementation of this algorithm can be found in the preprocessing submodule:

```python
from qubolite.preprocessing import reduce_dynamic_range

# sample random QUBO instance
Q = qubo.random(32, density=0.25)
print(Q.dynamic_range())
# 17.0248298387645

Q_reduced = reduce_dynamic_range(Q)
print(Q_reduced.dynamic_range())
# 8.193643891223
```

This heuristic algorithm works best for small instances or instances with low density.

---

## 4 SOLVING

The submodule *solving* provides a few common methods for solving QUBO instances approximately, such as Simulated Annealing [10] and other local search heuristics. However, the focus of *qubolite* is not to provide highly efficient implementations of QUBO solvers.

A notable feature is our fast parallel C implementation of a brute-force solver, which uses Gray codes to compute the energy of all vectors efficiently [14]. While brute force is not a feasible strategy for larger QUBO instances beyond around 30 variables, this implementation is useful for testing and research purposes.

---

## 5 USAGE

You can install *qubolite* either from PyPI or directly from the repository on GitHub:

```
pip install qubolite
pip install git+https://github.com/smuecke/qubolite@dev
```

It requires at least Python version 3.8. For the most up-to-date features, you can install the package directly from the branch, at the risk of encountering a few unstable or undocumented features:

```
pip install git+https://github.com/smuecke/qubolite@dev
```

The *qubolite* package may be used freely for research and private purposes. If you use this package in your research, please cite this paper as a reference. For other uses, e.g., in commercial applications, please contact:

```
sascha.muecke@tu-dortmund.de
```

---

## ACKNOWLEDGMENTS

This research has been funded by the Federal Ministry of Education and Research of Germany and the state of North-Rhine Westphalia as part of the Lamarr Institute for Machine Learning and Artificial Intelligence.

---

## REFERENCES

[1] Christian Raunkjæl, Cesar Opda, Rufel Sifa, and Stefan Wrobel. 2018. Adiabatic Quantum Computing for Kernel k-2 Means Clustering. In Proceedings of the Conference on "Lernen, Wisssen, Daten, Analysen" (CCEUR Workshop Proceedings).

[2] M. Booth, S. P. Reinhardt, and A. Roy. 2017. Partitioning optimization problems for hybrid classical/quantum execution. arXiv Systems. https://docs.ocean.dwavesys.com/projects/qbsolv/en/latest/ downloads/bdl542bdd5e95c9ff9c6d5f31cc-qbsolv_factSuspent.pdf

[3] Emile Aarts and Jan Korst. 1989. Simulated annealing and Boltzmann machines. In Discrete Unconstrained Binary Optimization (QUBO). Journal of Heuristics 13, 2 (2007), 99–132. https://doi.org/10.1007/s10732-007-9000-7

[4] Stephen G. Brush. 1967. History of the Lenz-Ising Model. Rev. Mod. Phys. 39 (1967), 883–893. Issue 4. https://doi.org/10.1103/RevModPhys.39.883

[5] Daniel S. Johnson. 1985. The NP-completeness column: An ongoing guide. Journal of Algorithms 6, 3 (1985), 434–451.

[6] Prasanna Date, Davis Arthur, and Lauren Pusey-Nazzaro. 2021. QUBO formulations for training machine learning models. Scientific Reports 11, 1 (2021).

[7] Fred W. Glover, Mark W. Lewis, and Gary A. Kochenberger. 2018. Logical and inequality implications for reducing the size and difficulty of quadratic unconstrained binary optimization problems. Eur. J. Oper. Res. 265, 3 (2018), 829–842. https://doi.org/10.1016/j.ejor.2017.08.025

[8] P. Hansen and B. Jaumard. 1990. Algorithms for the maximum satisfiability problem. Journal of Heuristics 1, 1 (1990), 1–16.

[9] Tadashi Kadowaki and Hidetoshi Nishimori. 1998. Quantum annealing in the transverse Ising model. Physical Review E 58, 5 (1998), 53–52.

[10] Scott Kirkpatrick, C. D. Gelati, and M. F. Vecchi. 1983. Optimization by Simulated Annealing. Science 220 (1983), 671–680. https://doi.org/10.1126/science.220.4598.671

[11] Gary Kochenberger, Fred Glover, Bahram Alidaee, and Karen Lewis. 2005. Using the unconstrained quadratic program to model and solve Max 2-SAT problems. International Journal of Operational Research 1, 3/4 (2005), 89–100.

[12] David E. Knuth. 1992. Long Range Reduction of Quadratic Functions. Oper. Res. 38, 3 (1970), 454–461. https://doi.org/10.1287/opre.18.3.454

[13] Satoshi Matsubara, Hirotaka Tamura, Motomi Takatsu, Dany Yos, Behnaz Yaskshkhsisdin, Hiromisu Yamashaki, Tomoyuki Miyazawa, Sarukka Tatsumura, and Wael Amin. 2020. Ising Model Optimizer with Parallel-Trial Bit-Sieve Engine. In Proceedings of the 11th International Conference on Complex, Intelligent, and Software Intensive Systems (Advances in Intelligent Systems and Computing), Vol. 811. Springer, 825–434. https://doi.org/10.1007/978-3-319-93554-1

[14] Erich Segal. 2016. Gray code. arXiv eprint arXiv:1510.01973. https://arxiv.org/abs/2310.1973

[15] Sascha Mücke. 2024. A Simple QUBO Formulation of Sudoku. In Companion Proceedings of the Association for Computing Machinery, ACM, 1958–. https://doi.org/10.1145/3686350.3664106

[16] Sascha Mücke, Thore Gerlach, and Nico Piatkowski. 2025. Optimum-Preserving QUBO Parameter Compression. Quantum Machine Intelligence 7 (2025). https://doi.org/10.1007/s42484-025-00219-3

[17] Serena Samuels, Yasmine Merrill, and Nico Piatkowski. 2023. Feature selection on quantum computers. Quantum Machine Intelligence 5, 1 (2023), 1–16. https://doi.org/10.1007/s42484-023-00104-5

[18] Sascha Mücke, Nico Piatkowski, and Katharina Morik. 2019. Hardware Acceleration of Machine Learning Beyond Linear Algebra. In Proceedings of Machine Learning and Knowledge Discovery in Databases (Communications in Computer Science and Engineering). Springer.

---

*Correspondence concerning this article should be addressed to Sascha Mücke, sascha.muecke@tu-dortmund.de*

and *Information Science*, Vol. 1167. Springer, 342–347. https://doi.org/10.1007/978-3-030-62024-8

[19] Sascha Mücke, Nico Piatkowski, and Katharina Morik. 2019. Learning Bit by Bit: Extracting the Essence of Machine Learning. In Proceedings of the Conference on "Lernen, Wissen, Daten, Analysen" (CCEUR Workshop Proceedings), Vol. 2454. CCEUR-WS.org. https://doi.org/10.1145/3356454

[20] Ewald Ding and Michael Luck. 1992. Long-Cycle Computation Searching. In Compound Heuristics and Polynomial Solvable Cases of QUBO. Springer International Publishing, 57–95. https://doi.org/10.1007/978-3-031-04530-3

[21] Panos M. Pardalos and Sumeth Ika. 1992. Complexity and Polynomially Solvable Cases of the Quadratic 0-1 Programming. Operations research letters 13, 2 (1992).

[22] Tobias Stellenwerck, Elisabeth Lobe, and Martin Jung. 2017. Flight Gate Assignment: an Interdisciplinary Aircraft in the Proceedings of the Workshop on Quantum Technology and Optimization Problems (Lecture Notes in Computer Science), Vol. 11413. Springer, 99–116. https://doi.org/10.1007/978-3-030-14928-8

[23] Leslie G. Valiant. 1979. The Complexity of Enumeration and Reliability Problems. SIAM J. Comput. 8, 3 (1979), 416–425. https://doi.org/10.1137/0208032
