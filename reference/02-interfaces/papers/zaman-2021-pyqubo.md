# PyQUBO: Python Library for Mapping Combinatorial Optimization Problems to QUBO Form


> **Citation.** Canonical entry `zaman2021` in [`references.bib`](../../references.bib) (resolved via Crossref/DataCite). arXiv:[2103.01708](https://arxiv.org/abs/2103.01708).
>
> **Companion note.** [`zaman-2021-pyqubo.note.md`](./zaman-2021-pyqubo.note.md) — how this paper links to Gibbsiq.

Mashiyat Zaman, Kotaro Tanahashi, and Shu Tanaka

## Abstract

We present PyQUBO, an open-source, Python library for constructing quadratic unconstrained binary optimizations (QUBOs) from the objective functions and the constraints of optimization problems. PyQUBO enables users to prepare QUBOs or Ising models for various combinatorial optimization problems with ease thanks to the abstraction of expressions and the extensibility of the program. QUBOs and Ising models formulated using PyQUBO are solvable by Ising machines, including quantum annealing machines. We introduce the features of PyQUBO with applications in the number partitioning problem, knapsack problem, graph coloring problem, and integer factorization using a binary multiplier. Moreover, we demonstrate how PyQUBO can be applied to production-scale problems through integration with quantum annealing machines. Through its flexibility and ease of use, PyQUBO has the potential to make quantum annealing a more practical tool among researchers.

**Index Terms** — Quantum annealing, QUBO, Ising machine, combinatorial optimization, Python

---

## 1 INTRODUCTION

COMBINATORIAL optimization is the calculation of the maxima or minima of a function within a discrete domain. Various combinatorial optimization problems, such as schedule and shift planning, delivery, and traffic flow, exist in daily life. Such problems often contain numerous possible solutions, making an exhaustive search intractable and hence creating an increasing demand for more efficient technologies.

To overcome such computational limitations, a new type of computation technology known as the Ising machine was developed. In 2011, the first commercial quantum annealing machine was presented [1]. The hardware of existing quantum annealing machines has been developed based on the theories of quantum annealing [2] and adiabatic quantum computation [3]. Ising machines are inspired not only by quantum annealing but also other principles that have been developed since the emergence of the first commercial quantum annealing machine [4], [5], [6], [7], [8], [9], [10]. A number of studies utilizing Ising machines have been conducted on various fields: portfolio optimization [11], traffic optimization [12], rectangle packing optimization [13], item optimization for e-commerce websites [14], and materials design [15].

To use Ising machines in solving a problem, the energy function of Ising model or quadratic unconstrained binary optimization (QUBO) corresponding to the objective function and constraints of the problem must be prepared. Here, we refer to the energy function as Hamiltonian. However, programming Ising models and QUBOs for Ising machines may be challenging when the objective function and constraints are complicated. Thus, we developed PyQUBO as a Python library for programming QUBOs and Ising models. Using PyQUBO's high-level class objects, users can construct Hamiltonians intuitively. Not only does PyQUBO make it easier to read and write code, but it also makes it more extensible, thereby allowing users to solve combinatorial optimization problems more efficiently. Through its accessibility and extensibility, PyQUBO has the potential to make quantum annealing a more common among researchers across a wide range of fields.

In this paper, we demonstrate how PyQUBO can be used to express QUBO and the Hamiltonian of Ising model as easily readable Python code. The remainder of this paper is organized as follows. In Section 2, we introduce the Ising machine and explain how use cases are solved using combinatorial optimization problem. In Section 3, we formulate the combinatorial optimization problem, and in Section 4, we demonstrate how it can be expressed in terms of a QUBO or Ising model. In Section 5, we introduce PyQUBO and explore the motivation for its development. In Section 6, we demonstrate how combinatorial optimization problems can be solved by simply using the fundamentals of PyQUBO. In Section 7, we present advanced PyQUBO methods for writing and debugging complex expressions. In Section 8, we explain PyQUBO for logical gates. In Section 9, we address the use of PyQUBO in conjunction with the D-Wave Ocean System software and D-Wave Advantage quantum annealing machine. In Section 10, we present internal implementations of PyQUBO and benchmark the performance with different implementations including other packages. Section 11 is devoted to the conclusion of the paper.

---

## 2 USE OF ISING MACHINES

In this section, we explain how Ising machines are used to solve combinatorial optimization problems. In general, five steps are involved in using Ising machines to solve optimization problems [16] as follows:

1) Discern a combinatorial optimization problem from the issue.
2) Represent the combinatorial optimization problem using an Ising model.
3) Embed the Ising model into the Ising machine according the hardware specifications and determine the hyperparameters.
4) Search for the low-energy states of the Ising model.
5) Interpret the final state to obtain feasible solutions to the original combinatorial optimization problem.

First, we need to identify the combinatorial optimization problem from the issue in question. Next, we formulate the optimization problem as an Ising model or QUBO. In this process, constraint terms are introduced to the Hamiltonian to satisfy the constraints. If the original optimization problem contains non-binary discrete variables, such as integer variables, these must be encoded using binary variables. The details of this process are explained in Sections 3 and 4.

Third, we map our logical Ising model into the physical Ising model, which consists of variables and interactions between variables that are implemented on the Ising machine. This mapping process is known as embedding. Because embedding is itself a combinatorial optimization problem, several efficient embedding algorithms have been proposed [17], [18], [19]. We also need to specify the hyperparameters, that is, the coefficients of the constraint terms. Fourth, we use the Ising machine to obtain the low-energy states of the physical Ising model. Finally, we interpret the variable states from the Ising machine and obtain the states corresponding to the logical Ising model. We determine whether the solution satisfies the problem constraints: if not, we repeat step 3 and update the hyperparameters. Through these five steps, we can obtain feasible solutions to combinatorial optimization problems using the Ising machine.

---

## 3 COMBINATORIAL OPTIMIZATION

The mathematical formulation for a combinatorial optimization problem expressed as follows:

$$z^* = \arg \min_{z} f(z), \quad z \in S,$$
$$g_\ell(z) = 0 \quad (\ell = 1, \ldots, L),$$
$$h_m(z) \leq 0 \quad (m = 1, \ldots, M),$$

where $z$ represents discrete integer decision variables of which number is $n$, $f(z)$ is the cost function, and $\mathcal{S}$ is the set of decision variables satisfying the given equality and inequality constraints [20].

Equation (1) can be rewritten as an optimization problem without any constraints using the penalty function method. Given the equality constraint $g(z) = 0$, we can consider the equation

$$z^* = \arg \min_{z} [f(z) + \lambda |g(z)|^2], \quad z \in \mathbb{Z}^n,$$

Similarly, given the inequality constraint $h(z) \leq 0$, Eq. (1) can be rewritten as

$$z^* = \arg \min_{z} \{f(z) + \lambda \max[h(z), 0]\}, \quad z \in \mathbb{Z}^n.$$

In both equations, $\lambda \in \mathbb{Z}^n$ denotes that the decision variables must be integers. For sufficiently large values of the coefficient $\lambda$, Eqs. (2) and (3) produce feasible solutions that satisfy the constraints with greater probability.

---

## 4 THE QUBO AND ISING MODEL

Ising machines use the QUBO or the Hamiltonian of the Ising model to solve combinatorial optimization problems. The Ising model and QUBO are defined on an undirected graph $G = (V, E)$, where $V$ and $E$ are the sets of vertices and edges on $G$, respectively.

### 4.1 Ising Model

The Hamiltonian of the Ising model on $G$ is expressed by

$$H_{Ising}(s) = \sum_{i \in V} h_i s_i + \sum_{(i,j) \in E} J_{ij} s_i s_j, \quad s_i \in \{-1, 1\},$$

where $s_i$ is the decision variable called spin at $i \in V$, $h_i$ is the magnetic field at $i \in V$, and $J_{ij}$ is the interaction at the edge $i, j$. Here $h_i$ and $J_{ij}$ are real numbers.

### 4.2 QUBO

The QUBO represents the cost function of a binary combinatorial optimization problem with linear and quadratic terms. Let $x_i$ be the $i$-th binary variable. Given graph $G$, it is formulated as

$$H_{QUBO}(x) = \sum_{i \in V} a_i x_i + \sum_{(i,j) \in E} b_{ij} x_i x_j, \quad x_i \in \{0, 1\}$$

where $a_i$ and $b_{ij}$ are real numbers. Here $b_{ij} = b_{ji}$ for arbitrary $i$ and $j$. A QUBO defined on the undirected graph $G = (V, E)$ is illustrated in Fig. 1.

Let us confirm the equivalence between QUBO and Ising model except for a constant value. QUBO can be expressed in matrix form. Let $Q_{ij}$ be a $|V| \times |V|$ matrix whose elements are given by

$$Q_{ij} = \begin{cases} a_i & [i = j, \forall i \in V] \\ b_{ij} & [\forall (i,j) \in E \text{ and } i < j] \\ 0 & \text{[otherwise]} \end{cases}$$

By using $Q_{ij}$ and a column vector $x$ generated by arranging binary variables, $H_{QUBO}(x)$ is rewritten by

$$H_{QUBO}(x) = \sum_{i,j} Q_{ij} x_i x_j = x^T Q x,$$

where $x^T$ represents the transpose of vector $x$.

### 4.3 Combinatorial Optimization Problem represented by Ising Model or QUBO

The equality and inequality constraints described by Eqs. (2) and (3) must be added as penalty terms that are written as QUBOs. That is, the Hamiltonian of Ising model or QUBO can be rewritten as

$$H = H_{cost} + \lambda H_{const},$$

where $\lambda$ determines the constraint term weight, $H_{cost}$ is the cost function, and $H_{const}$ is the penalty term, which is 0 when the constraint is satisfied and non-zero otherwise.

Methods to construct $H_{const}$ are explained in [21], [22], [23]. In summary, a combinatorial optimization problem can be made solvable by a Ising machines by representing the cost function and constraints of the original problem using the linear and quadratic terms of the binary variables.

---

## 5 INTRODUCTION TO PYQUBO

Thus far, we have observed that the general combinatorial optimization problem needs to be formulated as a QUBO (or Ising model) to solve the problem using Ising machines. Practically, we take the following steps to obtain the QUBO corresponding to the optimization problem.

1) Formulate the problem as an integer programming (IP) problem.
2) Reformulate the optimization problem without constraints by introducing constraint terms to the objective function.
3) Encode the integer variables with binary variables.
4) Expand the objective function.
5) Reduce the degree of higher-order terms.
6) Obtain the QUBO matrix from the coefficient of the polynomial.

In the first step, we formulate the general combinatorial optimization problem presented in Eq. (1) as an IP problem. The formulations for various combinatorial optimization problems are IP problems have been studied in depth [24]. This process is also required when we solve the combinatorial optimization problem with general optimization solvers, such as Gurobi [25]. In the second step, we introduce the constraint terms into the objective function by using the penalty method, so that the optimization problem does not include any additional conditions (see Section 3). In the third step, the integer variable in the objective function are encoded with binary variables. As there are several means of encoding an integer variable and each type has different characteristics, we need to select the appropriate one carefully. In the fourth step, the objective function is expanded into a sum of products. If the products in the expanded polynomial have a degree greater than two, the order of the products needs to be reduced by introducing new variables and constraint terms into step 5. Finally, the QUBO matrix can be obtained from the coefficient of the polynomial (see Section 6). If the order of the products in the polynomial exceeds two, the PyQUBO compiler automatically reduces the order and produces the corresponding QUBO matrix. PyQUBO provides several class modules, including multi-dimensional arrays (Supplementary Section A), integer classes with different encodings (Section 7.3), and integral rates (Section 8.1). These classes enable not only complicated expressions to be implemented quickly and easily but also the construction of modules on top of these (Section 5.2). As explained in Section 8.2, when we compile the model, the order of the polynomial can be automatically reduced. Thus, if we can transform the problem into QUBO rapidly, we can create different formulations and obtain superior results more efficiently.

To facilitate the creation of QUBOs, we developed a software tool known as PyQUBO. Using PyQUBO, one can define the Hamiltonian, that is, the objective function, with variable objects in a generic form. By calling the compile method of the expression, the QUBO matrix can be obtained instantly without knowing the expanded form of the Hamiltonian (Section 6). If the order of the products in the polynomial exceeds two, the PyQUBO compiler automatically reduces the order and produces the corresponding QUBO matrix. PyQUBO provides several class modules, including multi-dimensional arrays (Supplementary Section A), integer classes with different encodings (Section 7.3), and integral rates (Section 8.1). These classes enable not only complicated expressions to be implemented quickly and easily but also the construction of modules on top of these (Section 5.2). As explained in Section 8.2, when we attempt to solve the problem with Ising machines, we generally try to create several formulations and encoding types to test different results. Thus, if we can transform the problem into QUBO rapidly, we can create different formulations and obtain superior results more efficiently.

### 5.1 Quick Reference

A quick reference to each section, according to what the users wish to accomplish with PyQUBO, is provided below.

- **Automatic creation of QUBO:** PyQUBO automatically expands the terms of the Hamiltonian to produce the QUBO matrix, which is compilation (Section 6.2). In addition, PyQUBO automatically reduces the order of the polynomials during compilation (Sec. 6.2.3).

- **Validation of constraint satisfaction:** By using the Model.decode_sample() method, one can verify whether the given solutions are valid (Sec. 7.1).

- **Update of specific variables:** By defining a value with a Placeholder, when creating the Hamiltonian, the value we want to change can be specified even after compilation (Sec. 7.2).

- **Usage of integer decision variables instead of continuous decision variables:** Continuous variables can be approximately represented using the Integer class. For example, the continuous value $x \in [0,1]$ is approximated by $x \approx 0.1 \cdot \mathbb{1}_{\{0,0.1,\ldots,1.0\}}$. In PyQUBO, $x$ can be defined as `x=0.1*LogEncInteger("x", 0, 10)`.

- **Usage of categorical variables:** In certain problems, such as the graph coloring problem [26], a categorical variable is used to represent the category $C \in \{C_1, C_2, \ldots, C_n\}$. This variable is known as a categorical variable. In PyQUBO, categorical variables can be defined using the OneHotEncInteger class. Refer to Supplementary Section B for further details.

- **Usage of integer variables when inequality constraints:** PyQUBO provides various types of integer classes that can be used to create inequality constraints (Sec. 7.3).

- **Usage of logical variables:** PyQUBO provides logical gate classes and logical gate constraint classes, which are useful for formulating the satisfiability problem (SAT) or integer factoring as a QUBO (see 8).

- **Connection to D-Wave machines and other Ising solvers:** As PyQUBO is included in the D-Wave Ocean package, PyQUBO can easily be integrated with the D-Wave Ocean solver for D-Wave machines [26]. The format of QUBOs produced by PyQUBO is a key-value dictionary, which is compatible with other software tools for Ising solvers, such as OpenIJ [27].

- **Validation of a QUBO created using PyQUBO:** The PyQUBO utility method utils.asserts.assert_qubo_equal() checks the equality of given QUBOs, which are summarized as they can be compared.

---

## 6 PYQUBO FUNDAMENTALS

In this section, we will explain the essential classes of PyQUBO required to write and solve basic combinatorial optimization problems.

PyQUBO can be installed using `pip` as follows:

```
pip install pyqubo
```

Alternatively, GitHub users can install it from the source code:

```
git clone https://github.com/recruit-communications/pyqubo.git
cd pyqubo
python setup.py install
```

Supported Python versions are listed on the Github repository page.

### 6.1 Defining the Hamiltonian with the Express Class

The `Express` class is the abstract class of all operations used to write Hamiltonians in PyQUBO. Once defined, the Hamiltonian can be converted into a binary optimization problem using the `compile()` class method.

#### 6.1.1 Spin and Binary

The fundamentals of combinatorial optimization problems can be expressed in terms of the `Spin` ($-1, 1$) and `Binary` ($0, 1$) classes, corresponding to the Ising model and QUBO formulations, respectively. A `Binary` or `Spin` that is assigned to a variable must also be provided with a unique label. The labels of `Binary`/`Spin` variables can be used to interpret the coefficients of a QUBO or Ising problem more efficiently.

```python
>>> from pyqubo import Binary, Spin
>>> a, b, c = Binary("a"), Binary("b"), Binary("c")
>>> x, y, z = Spin("x"), Spin("y"), Spin("z")
```

**Codeblock 1:** Creating spins and binaries in PyQUBO.

#### 6.1.2 Add, Mul, and Num

PyQUBO interprets the built-in addition, multiplication, and power operators of Python, as well as the `int` and `float` values, as `Express` instances. `Spin` and `Binary` can also be added or multiplied using the `Add` and `Mul` classes, whereas numerical constants can be written using the `Num` class. The following example is a simple Hamiltonian that is minimized when one of the binary variables $a$ or $b$ is 1:

$$H = (a \times b - 1)^2, \quad a, b \in \{0, 1\}.$$

**Codeblock 2:** Arithmetic of `Binary` or `Spin` express variables is made possible using Python operators.

```python
>>> from pyqubo import Binary
>>> H = (a * b - 1) ** 2 + c * 2
>>> model = H.compile()
```

**Codeblock 3:** Creating a model from a PyQUBO expression.

#### 6.2 Compilation of Express Instances

##### 6.2.1 From Expression to Model

A `Model` instance is created from an `Expression` class using the `compile()` method. `Model` contains information regarding the Hamiltonian of the QUBO formulation. Codeblock 3 shows how we compile Eq. (11) from the previous section.

##### 6.2.2 From Model to QUBO or Ising

A model's QUBO or Ising formulations can be retrieved as Python dictionaries using the model class' `to_qubo()` and `to_ising()` methods. The `to_qubo()` method returns the QUBO and its energy offset. The `to_ising()` method returns the Ising model as two dictionaries, corresponding to linear and quadratic terms, as well as the energy offset. The linear and quadratic outputs take the form `dict([label, label], value)`, where each label corresponds to a variable in the Ising model as two dictionaries. The `to_ising()` method returns the Ising model as two dictionaries. Linear and quadratic outputs take the form `dict([label, label], value)`, where each label corresponds to a variable. The `to_ising()` method returns the Ising model as two dictionaries, corresponding to linear and quadratic terms, as well as the energy offset. The linear and quadratic outputs take the form $\text{dict}(\text{[label, label], value})$, where each label corresponds to a variable. The `to_ising()` method returns the Ising model as two dictionaries.

```python
>>> from pyqubo import Binary
>>> H = (a * b - 1) ** 2 + c * 2
>>> model = H.compile()
>>> qubo, qubo_offset = model.to_qubo()
>>> linear, quadratic, ising_offset = model.to_ising()
```

**Codeblock 4:** Converting a model into a QUBO or Ising model returns an energy offset as well.

##### 6.2.3 Order Reduction through Compilation

During compilation, if a Hamiltonian includes k-body interactions among `Binary` or `Spin` variables for $k > 2$, PyQUBO automatically reduces the expression to a quadratic by creating auxiliary variables representing the products of individual spins or binaries.

Reducing the order of the Hamiltonian by hand can be complicated, even for 3-body interactions. For example, given the Hamiltonian $H = xyz$, where $x, y$, and $z$ are binary variables, we introduce the auxiliary binary $a$, which represents the product of the individual binary variables. However, to maintain the relationship between $a$ and the products of $x$ and $y$, we must also include the penalty term $\lambda D(a, x, y)$ to the Hamiltonian. The final Hamiltonian is $H = az + \lambda D(a, x, y)$ where $D$ is the penalty strength.

Meanwhile, PyQUBO performs this reduction automatically, as demonstrated in Codeblock 5. The QUBO created in line 5 introduces a new variable $x \cdot y$ representing the product of the individual binary variables.

```python
>>> from pyqubo import Binary
>>> alpha = 2.0
>>> qubo, offset = model.to_qubo()
>>> print(qubo)
```

**Codeblock 5:** Model.compile() reduces the degree of an expression if it is greater than two.

#### 6.2.4 Decode Solutions

The `Model.decode_sample()` method can interpret the solution from any PyQUBO or quantum annealing solver as an easy-to-read Python dictionary with labels and their corresponding values (0 or 1 for `vartype="BINARY"`, −1 or 1 for `vartype="SPIN"`). The function returns a `DecodedSample` object, which provides a dictionary of label-value pairs via the `sample` property, the energies of constraints via the `constraints()` method, and the energy of the solution. We will discuss the `constraints()` method in greater detail in Section 7.1.

```python
>>> decoded_sample = model.decode_sample(
...     sample, vartype="BINARY"
... )
>>> decoded_sample.sample
>>> decoded_sample.constraints()
>>> decoded_sample.energy
```

**Codeblock 6:** Decoding a solution.

---

## 6.3 The Number Partitioning Problem

Using the classes described in Sections 6.1 and 6.2, we solve the **number partitioning problem**, which is described as follows. Given a set $S$ of $N$ positive integers, create two disjoint subsets of integers $S_1$ and $S_2$ such that their sums are equal. The Ising formulation of the number partitioning problem is

$$H = \left(\sum_{i=1}^{N} n_i s_i\right)^2$$

where $n_i$ describes the numbers in the set $S$ and $s_i$ is a spin variable. Given that $s_i$ takes the value 1 or −1, the sum of two equally sized sets will be zero for optimal solutions.

Codeblock 7 shows how the Hamiltonian of the number partitioning problem with $S = \{4, 2, 7, 1\}$ can be prepared and solved using PyQUBO.

```python
>>> from pyqubo import Spin, solve_Ising
>>> import numpy as np
>>> S = [4, 2, 7, 1]
>>> s = [Spin("s" + str(i)) for i in range(len(S))]
>>> # compile
>>> model, offset = model.to_qubo()
>>> sampler = sampler.SimulatedAnnealingSampler()
>>> sampleset = sampler.sample_qubo(qubo)
>>> decoded_sample = model.decode_sample(sampleset)
>>> # check constraints by comparing labels
>>> for label in decoded_sample.sample.keys():
...     lambda xi x.energy)
...
>>> best = min(dec_samples, key=lambda xi: x.energy)
>>> best
```

**Codeblock 7:** We use `Spin` variables to distinguish the two sets of integers, which are represented by the coefficient values.

Here the detail explanation of Codeblock 7 is given as follows. The sum of the multiplied terms and its exponent are represented using the corresponding Python addition (+), multiplication (*), and power (**) operators, as indicated in line 4. In lines 5 and 6, the Hamiltonian is compiled and converted into a QUBO, and in line 8, a possible solution is identified using the `sample_qubo()` method of `SimulatedAnnealingSampler`. In line 9, the sample is converted to labels using the `decode_sample()` method. The solution can easily be validated by comparing the sum of the coefficients in corresponding to the labels used in the 3. The solution demonstrates one manner in which the given set of integers can be separated into subsets such that their sums are equal. That is, other solutions where the difference is 0 may exist, whereas in other cases, depending on the set provided, none may exist at all.

---

## 7 PYQUBO ADVANCED USE

Numerous combinatorial optimization problems can be written and solved using the PyQUBO classes explained in Section 6. Advanced users interested in representing larger or more complicated problems can take advantage of PyQUBO's own Hamiltonian class using the `UserDefinedExpression` class. In this section, we explain the `Constraint`, `Placeholder`, and `Integer` classes of PyQUBO and demonstrate the manner in which these can be used to write more complicated combinatorial optimization problems.

### 7.1 Constraint

In Section 6.3, we observed that a solution to the number partitioning problem, given a small set $S$ is easily validated by hand. However, this process becomes difficult and time consuming for larger problems with many auxiliary variables, such as the knapsack problem. The `Constraint` class provides automatic validation regarding whether a solution satisfies the given constraints. The `Constraint` class specifies the parts of a Hamiltonian that must be satisfied by a valid solution to an optimization problem.

Each `Constraint` instance takes the section of the Hamiltonian comprising a constraint and string label as its parameters. When a Hamiltonian defined with the `Constraint` class is compiled as a model, the `decode_sample()` function returns a `DecodedSample` object that also provides information about the constraints via the `constraints()` method. The information is represented as a dictionary of constraint labels and tuples containing a boolean value and number, which correspond to whether the constraint is satisfied and the energy of the constraint, respectively. The `DecodedSample` object also contains the energy of a given solution via the energy property, as well as corresponding variable and value pairs in the sample property.

Codeblock 8 shows a simple application of the `Constraint` class. In line 3, we create a sum of two binary variables with a penalty term that is minimized when one of the variables is 1 and the other is 0. Because the penalty term is wrapped with the `Constraint` class, we are able to use the `decode_sample()` method to check whether a given solution satisfies the constraint represented by the penalty term. Lines 5 to 8 show that both binary value solutions without a label `one_hot` indicating the constraint is not satisfied. When the feasible solution $(\mathbf{a} = 1, \mathbf{b} = 0)$ is given, the `constraints()` method returns a true value with a label `one_hot` indicating the constraint is satisfied.

```python
>>> from pyqubo import Binary, Constraint
>>> y, a = Binary("x'y"), Binary("y'f'), Placeholder('a')
>>> exp = a+b+Constraint((a+b-1)**2, label='one_hot')
>>> model = exp.compile()
>>> usage, qubo = model.to_qubo(feed_dict=('a': 3.0))
>>> qubo_1
>>> qubo_2 = model.to_qubo(feed_dict=('a': 5.0))
>>> qubo_2
```

**Codeblock 9:** Placeholder values can be updated after compiling a model.

### 7.2 Placeholder

Depending on the given Hamiltonian, the compilation of models can be computationally expensive. If any value in the Hamiltonian is changed, the model must be recompiled in order to calculate the new QUBO. The `Placeholder` class makes it possible to update the coefficients within the Hamiltonian without recompiling the model, thereby saving a significant amount of time. In the situation where we need to update some values in Hamiltonian, such as parameter tuning of the penalty strength. Placeholders substitute constants and are identified by their string labels. When creating a QUBO or Ising model, or when decoding a solution, `Placeholder` values must be specified using a Python dictionary or label-value pairs as in Codeblock 9.

Codeblock 9 shows how the `Placeholder` can be used after compiling a model. In lines 5 and 7, when converting the `Model` into a QUBO, we include a `feed_dict` specifying the value of the `Placeholder` a.

### 7.3 Integer

The `Integer` class can easily create integer encodings of variables using the `Binary` terms with various encoding types. PyQUBO supports four types of integer encoding classes: `OneHotEncInteger`, `UnaryEncInteger`, `LogEncInteger`, and `CodedEncInteger` (Supplementary Section B). All four classes require a label, a tuple of lower bound, upper bound, and represent values in the range $[\text{lower}, \text{upper}]$, where $\text{lower}$ and $\text{upper}$ are the lower and upper bound value, respectively.

---

## 7.4 The Knapsack Problem

We use the PyQUBO classes described above to create and solve the **knapsack problem**, which is described as follows. Given a set of $N$ items with integer weights and values, determine which items to include in a collection such that the total weight is less than or equal to a weight limit $W$ and the total value $V$ is as large as possible. The total weight and total value of the knapsack is represented by

$$W = \sum_{a=1}^{N} w_a x_a, \quad w_a \in \mathbb{Z}$$

$$V = \sum_{a=1}^{N} v_a x_a, \quad v_a \in \mathbb{Z},$$

where $x_a$ takes the value 0 or 1 depending on whether the object is in the knapsack, and $w_a$ and $v_a$ are the integer weight and value of each item $a$, respectively. The Hamiltonian of the knapsack problem is $H = H_A - H_B$, where $H_A$ represents the weight constraint and $H_B$ is the total value of the items collected. Here, since Ising machines solve minimization problem, the sign of the second term is set to minus. The definitions of $H_A$ and $H_B$ are as follows:

$$H_A = \lambda_1 \left(1 - \sum_{n=1}^{N} y_n\right) + \lambda_2 \left(\sum_{n=1}^{N} n y_n - \sum_{\alpha=1}^{N} w_\alpha x_\alpha\right)^2,$$

$$H_B = \sum_{\alpha=1}^{N} v_\alpha x_\alpha,$$

where $y_n$ takes either the value 1 if the knapsack weight is $n$ or 0 otherwise [21], [23].

Below, we demonstrate how the knapsack problem can be written and solved using PyQUBO.

```python
from pyqubo import Binary, Constraint, Placeholder, Array, OneHotEncInteger

# weights and values
weights = [10, 2, 3, 6]
values = [10, 2, 3, 6]
N = len(weights)
W = 10

# create the array of 0-1 binary variables
x = [Binary('item_' + str(i)) for i in range(N)]
# len(values)
n = len(values)

# define the sum of weights and values using variables
H_weight = sum([x[i] * weights[i] for i in range(N)])
H_knapsack_value = sum(values[i] * items[i] for i in range(n))

# define the cost functions of penalty terms
lmd1 = Placeholder("lmd1")
lmd2 = Placeholder("lmd2")
H = Constraint([(weight_one_hot - knapsack_value, strength=lmd1),
    value_range=[1, lmd_weight], strength=lmd2),
        "weight_constraint")

# create Hamiltonian and model
Ha = Constraint([(weight_one_hot - knapsack_value, strength=lmd1])
HB = knapsack_value
model = H.compile()

# use simulated annealing with neal package
sampler = neal.SimulatedAnnealingSampler()
feed_dict = {'lmd1': lmd1_value, 'lmd2': lmd2_value}
sampleset = sampler.sample_qubo(qubo)
dec_samples = model.decode_sample(sampleset,
    feed_dict)
best = min(dec_samples, key=lambda x: x.energy)

# After the feasible solution
if not best.constraints(only_broken=True):
    feasible_sols.append(best)

best_feasible = min(feasible_sols, key=lambda xi: x.energy)
```

**Codeblock 10:** While the knapsack problem can be expressed and solved using the classes introduced in Section 6, the `Constraint`, `Placeholder`, `Array`, and `Integer` classes are useful for both debugging and streamlining the knapsack problem.

The detail of Codeblock 10 is as follows. In lines 3–5, we define the weights and values of the items in our set, as well as an weight limit $W$. In line 10, we use the `Array` class to create the set of `Binary` variables $x_a$ with its size set equal to the number of items. Thereafter, we calculate the knapsack weight and value sums $\sum_{\alpha=1}^{N} w_\alpha x_\alpha$ and $\sum_{\alpha=1}^{N} v_\alpha x_\alpha$ in lines 13 and 14, respectively.

Next, we prepare the Hamiltonian. In lines 19–20, we define the coefficients of the penalty terms, `lmd1` and `lmd2`, using `Placeholder` classes. In line 22, the QUBO is written as the knapsack value sum. In line 25, we create a `Constraint` with the `Placeholder` values. If `Placeholder` values are changed after compilation, the QUBO, the normalized QUBO matrix of both using `to_qubo` and `normalize` in order to make it easy to tune the solver parameters, sample solutions through simulated annealing using the `SimulatedAnnealingSampler` of the neal package, and then retrieve the `DecodedSample` instances using `decode_samplesset()`. The BQM class is defined in the D-Wave's `dimod` package and represents QUBOs or Ising models. The method `decode_samplesset()` like `decode_sample()` method.

In lines 46–47, we retrieve the broken constraints using the `only_broken` argument set to `true`. If the solution to the list `feasible_sols`, in line 49, we obtain the feasible solution with the lowest energy. We obtained the final solution to select 1st and 4th items with the value sum equal to 16.

---

## 8 PYQUBO FOR LOGICAL GATES

A logical gate is an electronic device that implements a boolean function by taking binary inputs, performing a logic operation, and providing a single binary output.

The AND, OR, NOT, and XOR logic operations can be represented using the logical gate and logical constraint classes of PyQUBO. In the following, we present the corresponding circuit component and truth table of each logical class, as well as examples of its application in PyQUBO.

### 8.1 Logical Gates

The PyQUBO logical gate classes `Not`, `And`, `Or`, and `Xor` correspond to the four logic operations. Like their electronic analogs, the logical gate classes perform the specified logic operation on given binary inputs.

We summarize the analytical representations of the logic operations below:

$$NOT(a) = 1 - a$$
$$AND(a,b) = ab$$
$$OR(a,b) = a + b - ab$$
$$XOR(a,b) = a + b - 2ab,$$

where $a$ and $b$ represent binary inputs. Figure 2 shows each operation's circuit element and truth table.

### 8.2 Logical Constraints

The logical constraint classes `NotConst`, `AndConst`, `OrConst`, and `XorConst` are constraints based on the four operators discussed. However, unlike the logical gates in Section 8.1, each constraint requires three `Express` class inputs (for two inputs of `NotConst`), corresponding to the logical expression operands, as well as the expected output and a label. In other words, the logical constraint classes, instead of performing the specified operation, represents entire logical expression as a constraint.

As discussed in Section 6.2.4, the `decode_sample()` function determines whether a given solution violates the constraint. A logical approach to verify the solution of an expression wrapped by a logical constraint is to determine the model energy. When the provided variables satisfy the constraint, the energy is 0.0, but when they break the constraint, the energy is 1.0. Therefore, unlike the logical gates in Section 8.1, logical constraints do not provide solutions themselves.

**Codeblock 11:** The energy of a compiled logical constraint expression indicates whether or not the provided operand and output satisfy the operator logic. In this example, the energy is 0.0 when the expression is true and 1.0 when it is false.

```python
>>> from pyqubo import Binary, OrConst
>>> a, b, c = Binary('a'), Binary('b'), Binary('c')
>>> exp = OrConst(a, b, c, label='or')
>>> model = exp.compile()
>>> model.energy({'a': 0, 'b': 1, 'c': 1}, vartype="BINARY")
```

**Codeblock 11:** The energy of a compiled logical constraint expression indicates whether or not the provided operand and output satisfy the operator logic. In this example, the energy is 0.0 when the expression is true and 1.0 when it is false.

### 8.2.1 Preparing a Multi-Bit Binary Multiplier

A digital binary multiplier is an electronic circuit that is used to multiply two binary numbers, namely, a multiplier and multiplicand. The unit size of the resulting product corresponds to the sum of the two input sizes. Digital multipliers consist of AND gates as well as half- and full-adders. For a $j$-bit and $k$-bit multiplicand, a $j \times k$ AND gate and $(j - 1) \times k$ adders and $j$-bit multipticand, a multiplier circuit requires $j \times k$ AND gates and $(j - 1) \times k$ adders, as illustrated in Fig. 3. The logical gates of PyQUBO can be used to represent the AND, OR, and XOR gates that comprise the multiplier as well as its half- and full-adders. By using logical constraints instead of logical gates, the binary multiplier can be adapted to solve integer factorization problems. For example, given a large product $p$ as a constraint, the multiplier QUBO can be solved for all integer pairs $a$ and $b$ satisfying the product [28]. To prepare the digital multiplier, first we need to construct the half-adder and full-adder constraints. The half-adder adds two single

```python
>>> from pyqubo import XorConst, AndConst, OrConst
>>> from pyqubo import Binary, Spin, UserDefinedExpression
>>>
>>> class HalfAdderConst(UserDefinedExpression):
...     def __init__(self, a, b, s, c, label):
...         self.xor_const = XorConst(a, b, s, f'[label]_xor')
...         self.and_const = AndConst(a, b, c, f'[label]_and')
...
>>> a, b, s, c = Binary("a"), Binary("b"), Binary("c"), Binary("s")
>>> model = HalfAdderConst(a, b, s, c, 'ha').compile()
>>> sampler = d_wmod.ExactSolver().sample_qubo(qubo)
>>> for d_smpl in model.decode_sample(sampleset):
...     print(d_smpl['a'], d_smpl['b'], d_smpl['c'], 
...           d_smpl['c'])
...     d_smpl['s'].energy)
...
# Output
# 0 0 0 0.0
# 0 1 1 0.0
# 0 1 1 0.0
# 1 0 1 0.0
# 1 0 1 0.0
# 1 1 0 1.0
# ...
```

**Codeblock 12:** Half-adder built using PyQUBO's logical constraint classes. Note that the outputs $s$ and $c$ must be included as arguments.

The detail of Codeblock 12 is as follows. We create a new class `HalfAdderConst` that creates the Hamiltonian for a half-adder given two inputs, as well as the sum and carry. In lines 7 and 8, we define the XOR and AND constraints, which provide the sum and carry. In line 16 we use the `d_wmod.ExactSolver()` to calculate all possible solutions of the half-adder Hamiltonian. As shown in Codeblock 12, and Codeblock 16 uses the `d_wmod.ExactSolver()` to calculate all possible solutions of the half-adder Hamiltonian. As shown in Codeblock 12 and 16, the half-adder can be constructed from two single

```python
Inputs  Outputs
   A B |S Co
-------|---
   0 0 |0  0
   0 1 |1  0
   1 0 |1  0
   1 1 |0  1
```

**Fig. 4:** Half-adder circuit and truth table.

binary digits and returns their sum and carry values as shown in the circuit diagram in Fig. 4. The logical gates of PyQUBO can be used to represent the AND, OR, and XOR gates that comprise the multiplier as well as its half- and full-adders. By using logical constraints instead of logical gates, the binary multiplier can be adapted to solve integer factorization problems. For example, given a large product $p$ as a constraint, the multiplier QUBO can be solved for all integer pairs $a$ and $b$ satisfying the product [28]. To prepare the digital multiplier, first we need to construct the half-adder and full-adder constraints. The half-adder adds two single

For the purpose of encoding the full-adder and its corresponding circuit diagram, as shown in Fig. 5, in the case of $A$, $B$, and $C_{in}$ are binary inputs.

$$\begin{array}{c|cc}
\text{Inputs} & \text{Outputs} \\
A & B & C_{in} & S & C_{out} \\
\hline
0 & 0 & 0 & 0 & 0 \\
0 & 0 & 1 & 1 & 0 \\
0 & 1 & 0 & 1 & 0 \\
0 & 1 & 1 & 0 & 1 \\
1 & 0 & 0 & 1 & 0 \\
1 & 0 & 1 & 0 & 1 \\
1 & 1 & 0 & 0 & 1 \\
1 & 1 & 1 & 1 & 1 \\
\end{array}$$

**Fig. 5:** Full-adder circuit diagram and truth table, where $A$, $B$, and $C_{in}$ are binary inputs.

A simple 3-bit binary multiplier uses three half-adders, three full-adders, and nine AND constraints. It takes the product of the multiplier, multiplier, and product as lists or arrays of binary values (as well as a unique label (a prefix)) and creates a Hamiltonian. Users interested in designing a binary multiplier using PyQUBO should refer to the PyQUBO GitHub repository [29].

---

## 9 PYQUBO WITH D-WAVE OCEAN

In this section, we demonstrate how PyQUBO and D-Wave can be used in tandem to solve the knapsack problem once again (Eqs. (13) and (16)).

### 9.1 Introduction to D-Wave

To use a D-Wave machine to solve a given problem, the logical graph representing the corresponding QUBO or Ising model must be embedded into the physical graph of D-Wave hardware. D-Wave machines use the Chimera or Pegasus architecture, depending on the hardware generation [30]. Here, we define the embedding process as shown in [17], [18], [19]. In addition to the problem QUBO, chained qubits are assigned the interaction with a constant chain strength so that their values are the same across all low-energy solutions. While the magnitude of the chain strength must be tuned depending on the problem, the embedding process even for complex structures to be mapped onto the D-Wave machine.

D-Wave System solvers are configured to solve problems on corresponding working graphs, which are the qubits and couplers that are available for computation. Here, couplers adjust the value of the interaction.

### 9.2 Programming with PyQUBO and D-Wave Ocean

Model written in PyQUBO can be used as inputs for the D-Wave Ocean sampler. Samplers provide a sample of set of solutions from the low-energy states of the objective function of an optimization problem. Creating a D-Wave sampler requires an endpoint, a D-Wave Application Programming Interface (API) token, which is available to all D-Wave accounts with a specific solver name. Based on Codeblock 13, a method for solving a knapsack problem using the D-Wave sampler is specifically described. In lines 13–24, we define the Hamiltonian of the knapsack problem. Here, we used `LogEncInteger` instead of `OneHotEncInteger` as suggested in Codeblock 10 to show the integer class object can be easily replaced. In line 26, we create an embedding, which we map onto the quantum annealing machine using the `FixedEmbeddingComposite` class in line 40. Defining our embedding before the QUBO saves time, however finding the optimal embedding could in turn lead to more efficient problem solving. In lines 42–49, we define the sampler's keyword arguments, which depend on the selected D-Wave solver. The following parameters are common across all hardware solvers: `num_reads`, which corresponds to the number of annuals and time per annual respectively, which sets the number of gauge transformations to be performed on the gauge scale, which indicates whether $h_i$ and $J_{ij}$ of the Ising model (Eq. (4)) are rescaled.

The next two parameters `chain_strength` and `chain_break_fraction` in lines belong to the `FixedEmbeddingComposite` class, which map problems to the sampler using the given embedding. As discussed above, the `chain_strength` parameter must be tuned for the sampler using the given embedding. As discussed above, the `chain_strength` parameter must be tuned for the problem.

Next, we create an objective function, which provides the solution to a QUBO, its energy, as well as broken constraints, given a feed dictionary for `Placeholder` values and the pre-determined keyword arguments. In line 52, we create a QUBO as `BQM` from a `Model` instance. In line 53, we normalize the QUBO such that the parameter tuning is not affected by the scale of the problem. In line 54, we use the sampler to retrieve a set of solutions to the normalized QUBO, and in line 55, we use the PyQUBO function `Model.decode_sample()` to interpret these solutions. The decode method's arguments are `samples`, and `feed_dict`, which, as discussed above, the `chain_strength` parameter must be tuned for the problem.


Finally, in lines 59–64, we execute the objective function using different `Placeholder` values and append each feasible solution to the list `feasible_sols`. In this code, we search only one parameter `lmd` since we are using `LogEncInteger`, which does not have an extra constraint like `OneHotEncInteger`. Finally, we show the sum of the values of the best feasible solution.

```python
import dimod
from dwave.system.samplers import DWaveSampler
from dwave.system.composites import FixedEmbeddingComposite
from pyqubo import Binary, Constraint, Placeholder, LogEncInteger

# weights, values and the maximum weight of the knapsack problem
weights = [10, 3, 7, 6]
values = [10, 2, 3, 6]
max_weight = 10

# create list item
items = Array.create('item', shape=vartype="BINARY")
n = len(values)
knapsack_weight = sum(weights[i] * items[i] for i in range(n))
weight_one_hot = LogEncInteger("weight_one_hot", value_range=[1, lmd_weight])
H = - Constraint([(weight_one_hot - knapsack_value, strength=lmd1),
value_range=[1, lmd_weight], strength=lmd2),
         "weight_constraint")

# create Hamiltonian and model
Ha = Constraint([(weight_one_hot - knapsack_value, strength=lmd1])
HB = knapsack_value
model = H.compile()

dw_sampler = DWaveSampler(solver='Advantage_system1.1')
endpoint="https://cloud.dwave.sys/sapi",
token="your-token",
solver= AdvantageSystem1.1')
graph_size=16
sampler_size=len(model.variables)
pls_working_graph = dw_sampler.properties['working_graph']
embedding = find_clique_embedding(sampler_size, pls_working_graph)

sampler = FixedEmbeddingComposite(dw_sampler, embedding)
sampler_kwargs = {
    "num_reads": 100,
    "annealing_time": 20,
    "num_spin_reversals": 8,
    "auto_scale": True,
    "chain_strength": 1.0,
    "chain_break_fraction": True,
}

def objective(feed_dict):
    bqm = model.to_bqm(index_label=True, feed_dict=feed_dict)
    bqm_normalize = bqm.normalize()
    sampleset = sampler.sample(bqm, **sampler_kwargs)
    dec_samples = model.decode_sampleset(sampleset, **sampler_kwargs)
    return min(dec_samples, key=lambda x: x.energy)

# search best parameters lmd within [1,2,...,5]
feasible_sols = []
for lmd_value in range(1, 5):
    feed_dict = {'lmd': lmd_value}
    s = objective(feed_dict)
    if not s.constraints(only_broken=True):
        feasible_sols.append(s)

best_feasible = min(feasible_sols, key=lambda xi: x.energy)
print(f"Sum of the values = {best_feasible.energy}")
```

**Codeblock 13:** Using the D-Wave sampler to find a solution to the knapsack problem.

---

## 10 IMPLEMENTATION AND BENCHMARKING

In this section, we show how PyQUBO is implemented internally and benchmark the performance with different implementations including other packages.

### 10.1 Internal Representation of Expressions

In PyQUBO, the expression of a Hamiltonian is represented by a binary tree, which is called AST (Abstract Syntax Tree). For example, the expression created by the Codeblock 14 is represented by the binary tree shown in Fig. 6(left). The leaves of the tree are composed of "number" and "variable" nodes, shown as rectangles in Fig. 6(left). The internal nodes are composed of "sum" or "product" nodes, shown as circles in Fig. 6(left). The generated polynomials by expand() function at each node, are shown in Fig. 6(right) as a hash map. The Python-like pseudo code to expand the expression is shown in Codeblock 15. If we pass the root node of the binary tree to the function, the expanded polynomial is returned as a hash map. The functions `poly_sum`, `poly_prod` and the product of the input polynomials, respectively. We assume that the input node has the property type, which indicates the type of the node (i.e., number, variable, sum or product). The "product" or "sum" node has the properties `left` and `right`, each of which contains the child node corresponding to the inputs of the product or sum operation. The "number" node has the property `value` which contains the number itself. The generated polynomials by expand() function at each node, are shown in Fig. 6(right) as a hash map.

```python
x, y = Binary("x"), Binary("y")
H = (x + 2) * (x*y + 3)
```

**Codeblock 14:** An example expression created by PyQUBO objects. It corresponds to the binary tree in Fig. 6(left).

```python
def expand(node):
    if node.type == 'sum':
        return poly_sum(
            expand(node.left), expand(node.right))
    elif node.type == 'product':
        return poly_prod(
            expand(node.left), expand(node.right))
    elif node.type == 'variable':
        return {(node.label,): 1}
    elif node.type == 'number':
        return {(): node.value}
```

**Codeblock 15:** The Python-like pseudo code to expand the expression.

### 10.3 Data Structure of Product of Variables

The products of variables in polynomials are represented by a set. In calculating the product of polynomials (i.e., `poly_prod` function in Codeblock 15), we need to calculate the product of two products of variables. This operation can be implemented by the union operation of the two input sets representing the product of variables. In the following example, we calculate the product of $xy$ and $yz$:

$$xy \times yz = xyz,$$

where $x, y, z \in \{0,1\}$. We can confirm that the set $\{x, y\}$ is a union of the two sets: $\{x, y\}$ and $\{y, z\}$. Since a polynomial is implemented as a hash map, the product of variables needed to work as a key of the hash map. This means that the set representation needs the equal function and the hash function. We assume that the equal function is called the most frequently among the operations above. Let us consider the appropriate implementation of the set. First, we considered using the set provided by the C++ standard library, i.e., tree-based set (`std::set`) and the hash-based set (`std::unordered_set`). The time complexity of equality operation is $O(k)$ in the worst case, where $k$ is the size of the set. Therefore, the tree-based set is suitable in the case where the equality operation needs to run fast.

Second, we considered using a sorted array to represent a set. By comparing elements from the head of the sorted array, we found that the time complexity of the equality operation is $O(k)$ in the worst case. By merging elements from the head of the array, we discovered that the time complexity of the union operation is $O(k)$ in the worst case. By merging elements from the head of the array, we discovered that the time complexity of the union operation of the sorted array is expected to be faster than that of the tree-based set [35]. Since the time complexity of union operation of the sorted array is $O(k)$ in the worst case, where $k$ is the size of the set. Therefore, the tree-based set is suitable in the case where the equality operation needs to run fast.

### 10.4 Benchmark of Memory Size and Running Time

We measured the memory size and the running time required to construct the expression and the QUBO matrix with a couple of types of combinatorial problems: graph partition problems (GP) and traveling salesman problems (TSP) [21]. Graphs used in GP are generated as a binomial graph with the edge density set to 0.3. While the QUBO matrix of GP is dense, i.e., all elements of the matrix are non-zero, the QUBO matrix of TSP contains about $n^2$ non-zero elements out of $n^2$, where $n$ is the number of cities in TSP. We chose these two problems for the benchmark since each QUBO matrix has different characteristics in terms of the density. In the measurement of the memory size, we measured the maximum memory size for all processes (i.e., from constructing the expression through producing the QUBO matrix). We measured the running time to construct the expression and produce the QUBO matrix separately.

We compared the following implementations in this benchmark:

- **SymPy:** Using SymPy [36] package to create QUBOs from the expression.
- **Python QUBO:** Other PyQUBO (version 0.4.0) implemented entirely in Python.
- **Set(C++):** Using tree-based `std::set` for products of variables, implemented in C++. Equivalent to PyQUBO (version 1.0.7).
- **Array(C++):** Using sorted array for the products of variables, implemented in C++. Equivalent to PyQUBO (version 1.0.7) but with a different implementation including other packages.

### 10.5 Result of Benchmark

We show the dependence of memory size and running time on the number of variables in a QUBO (Fig. 7). We could not run SymPy and Python with larger problem sizes because of the time limit. We observed that the running time of the PyQUBO in C++ are better than that of PyQUBO in Python or SymPy. We also confirmed that Array(C++) is superior compared to Set(C++). In graph partition problems, we also confirmed that the memory size and the running time of Array(C++) are superior compared to Set(C++). In graph partition problems, we could not observe a significant difference in the memory usage of Array(C++) and Set(C++), as the problem sizes increase.

**TABLE 1:** The estimated time complexity with respect to the number of terms $n$ in the Hamiltonian, based on the benchmark result (Fig. 7).

| Implementation | Expression time | Compile Time |
|---|---|---|
| SymPy | $O(n^2)$ | $O(n)$ |
| Python | $O(n^2)$ | $O(n)$ |
| Set(C++) | $O(n)$ | $O(n)$ |
| Array(C++) | $O(n)$ | $O(n)$ |

and traveling salesman problems, the number of terms $n$ is $m^2$ and $m^2$, respectively, where $n$ is the number of variables of QUBO. Based on the benchmark results, we can estimate the time complexity with respect to the number of terms $n$ in the Hamiltonian as shown in Table 1. While the time complexity of constructing expressions in SymPy and Python is $O(n^2)$, in C++, it is reduced to $O(n)$ because the expression is represented by binary trees like Fig. 6(left), i.e., an added new term to the expression, which does not require objects to be copied when we add a new term to the expression, which leads to the complexity of $O(n^2)$ because the expression is represented by binary trees like Fig. 6(left), i.e., an added new term to the expression does not require objects to be copied when we add a new term to the expression. A new term to the added term from the original expression, which does not require objects to be copied when we add a new term to the expression.

---

## 11 CONCLUSION

The increasing availability of Ising machines including quantum annealing machines has been an advantage for research into more practical solutions to large combinatorial optimization problems. However, Ising machines are limited in solving QUBOs and Ising model Hamiltonians, which are difficult to read and implement for many, if not most, optimization problems. The PyQUBO package offers a means of writing QUBOs and Ising model Hamiltonians in an intuitive and readable manner. Not only does it accommodate a wide variety of problems, but it also supports the automatic validation of constraints and parameter tuning, which are essential for debugging large problems. Furthermore, as an open-source library, it enables users to contribute new functions that are suited to their needs. We expect that many researchers will use PyQUBO as they integrate Ising machines including quantum annealing into their fields.

---

## ACKNOWLEDGMENTS

One of the authors (S. T.) was partially supported by JST, PRESTO Grant Number JPMJPR16G5, Japan and JSPS KAKENHI Grant Number 19H01553.

---

## REFERENCES

[1] M. W. Johnson, M. H. Amin, S. Gildert, T. Lanting, F. Hamze, N. Dickson, R. Harris, A. J. Berkley, J. Johansson, P. Bunyk et al., "Quantum annealing with manufactured spins," *Nature*, vol. 473, no. 7346, pp. 194–198, 2011.

[2] I. Kadowaki and H. Nishimori, "Quantum annealing in the transverse ising model," *Physical Review E*, vol. 58, no. 5, p. 5355, 1998.

[3] E. Farhi, J. Goldstone, S. Gutmann, J. Lapan, A. Lundgren, and D. Preda, "A quantum adiabatic evolution algorithm applied to random instances of an NP-complete problem," *Science*, vol. 292, no. 5516, pp. 472–475, 2001.

[4] E. Farhi, J. Goldstone, S. Gutmann, J. Lapan, A. Lundgren, and D. Preda, "A quantum adiabatic evolution algorithm applied to random instances of an NP-complete problem," *Science*, vol. 292, no. 5516, pp. 472–475, 2001.

[5] M. Yamaoka, C. Yoshimura, M. Hayashi, T. Okuyama, H. Aoki, and H. Mizuno, "A 20k-spin Ising chip to solve the combinatorial optimization problems with cmos annealing," *IEEE Journal of Solid-State Circuits*, vol. 51, no. 7, pp. 303–309, 2015.

[6] T. Inagaki, Y. Haribara, K. Igarashi, T. Sonobe, S. Tamate, T. Honjo, A. Marandi, P. L. McMahon, T. Umeda, K. Enbutsu et al., "A coherent Ising machine for 2000-node optimization problems," *Science*, vol. 354, no. 6312, pp. 603–606, 2016.

[7] D. T. Tanasiia, M. Marandi, P. L. McMahon, T. Umeda, K. Enbutsu, S. Tanaka, and T. Inagaki, "A coherent Ising machine for 2000-node optimization problems," *Science*, vol. 354, no. 6312, pp. 614–617, 2016.

[8] M. Aramon, G. Rosenberg, E. Valiante, T. Miyazawa, H. Tamura, and H. Katzgraber, "Physics-inspired optimization for quadratic unconstrained binary optimization problems," *Frontiers in Physics*, vol. 7, p. 48, 2019.

[9] M. Yamazaki, C. Fujii, M. Hidaka, K. Imaoka, K. Kikuchi, Y. Mizuno, C. Ramsay, and J. D. Ciliberto, "Towards practical scale quantum annealing machine for prime factoring," *Journal of the Physical Society of Japan*, vol. 88, no. 6, p. 061012, 2019.

[10] H. Goto, K. Tatsumura, and A. R. Dixon, "Combinatorial optimization by simulating adiabatic bifurcations in nonlinear hamiltonain systems," *Science Advances*, vol. 5, no. 4, eaav2372, 2019.

[11] G. Rosenberg, P. Haghnegahdar, P. Goddard, P. Carr, K. Wu, and M. L. De Prado, "Solving the optimal trading execution problem using a quantum annealer," *IEEE Journal of Selected Topics in Quantum Electronics*, vol. 24, no. 6, pp. 1–12, 2018.

[12] S. Tanaka, S. Tamura, and B. K. Chakrabarti, "Quantum annealing and Adiabatic computation." Cambridge Bridge University Press, May 2017.

[13] K. Terabe, D. Oku, S. Kanamaru, S. Tanaka, M. Hayashi, M. Yamamoto, and N. Togawa, "Ising model mapping in traveling salesman problems," in *2018 International Symposium on VLSI Design, Automation and Test (VLSDAT)*, April 2018, pp. 1–4.

[14] N. Nishimura, K. Tanahashi, K. Suganuma, M. J. Miyama, and M. Sugawara, "Ising model mapping for e-commerce websites based on diversity," in *Computers in Science and Technology*, vol. 1, p. 2, 2018.

[15] K. Kitai, J. Guo, S. Ju, S. Tanaka, K. Tsuda, J. Shiomi, and R. Tamura, "Designing materials with target properties by machine learning," *Physical Review Research*, vol. 2, no. 1, p. 013320, 2020.

[16] S. Tanaka, Y. Matsuda, and N. Togawa, "Theory of Ising machines," in *Theory of Ising machines and a quantum software platform for Ising machines, 25th Asia and South Pacific Design Automation Conference*, pp. 659–666, 2020.

[17] P. Goddyn, "Finding Graph Minors," *arXiv preprint arXiv:1406.2741*, 2014.

[18] V. Choi, "Minor-embedding in adiabatic quantum computation: I. the parameter setting problem," *Quantum Information Processing*, vol. 7, no. 5, pp. 193–209, 2008.

[19] T. Boothby, A. D. King, and A. Roy, "Fast clique minor generation in adiabatic quantum computation," *Quantum Information Processing*, vol. 15, no. 2, pp. 495–508, 2016.

[20] S. Kanamaru, K. Kawamura, and N. Togawa, "Mapping constrained problems to Ising models and evaluations by computational experiments," *IEEE Consumer Electronics (ICCE-Berlin), Berlin, Germany*, pp. 221–226, 2018.

[21] A. Lucas, "Ising formulations of many NP problems," *Frontiers in Physics*, vol. 2, p. 5, 2014.

[22] S. Tanaka, R. Tamura, and B. K. Chakrabarti, "Quantum Spin Glasscs, Annealing and Computation." Cambridge Bridge University Press, May 2017.

[23] K. Tanahashi, S. Takayanagi, T. Motohashi, and S. Tanaka, "Application of Ising machines and a software development for Ising machines," *Journal of the Physical Society of Japan*, vol. 88, no. 6, p. 061010, 2019.

[24] L. A. Wolsey and G. L. Nemhauser, *Integer and combinatorial optimization*. John Wiley & Sons, 1999, vol. 55.

[25] Gurobi Optimization, LLC, "Gurobi optimizer reference manual," 2020. [Online]. Available: https://www.gurobi.com/.

[26] D. O'Malley and V. V. Vesselinov, "Toq.jl: A high-level programming language based on Julia," in *IEEE High Performance Extreme Computing Conference (HPEC)*, IEEE, 2016, pp. 1–7.

[27] J. Inc, 2019. [https://github.com/OpenIJ/OpenIJ](https://github.com/OpenIJ/OpenIJ)

[28] M. Maezawa, K. Imafuku, M. Hidaka, H. Koiko, and S. Kawabata, "Design of quantum annealing machine for prime factoring," pp. 1–3, 2017.

[29] Recruit Communications Co., Ltd., "Pyqubo," 2018. [https://github.com/recruit-communications/pyqubo](https://github.com/recruit-communications/pyqubo)

[30] M. Boixo, T. F. Ronnow, S. V. Isakov, Z. Wang, D. Wecker, D. A. Lidar, I. M. Martinis, and M. Troyer, "Characterization of quantum-annealing-machine with more than one hundred qubits," *Nature Physics*, vol. 10, no. 3, pp. 218–224, 2014.

[31] D-Wave Systems Inc., "D-wave qpu architecture: Topologies," 2020. [https://docs.dwavesys.com/docs/latest/c_gs_4.html](https://docs.dwavesys.com/docs/latest/c_gs_4.html)

[32] S. Boixo, T. F. Ronnow, S. V. Isakov, Z. Wang, D. Wecker, D. A. Lidar, I. M. Martinis, and M. Troyer, "Evidence for quantum annealing with more than one hundred qubits," *Nature Physics*, vol. 8, no. 3, pp. 218–225, 2014.

[33] G.P reference, "C++ parallel container," 2020. [Online]. Available: https://en.cppreference.com/w/cpp/container/set/operator_cmp

[34] "operators," 2020. [Online]. Available: https://en.cppreference.com/w/cpp/container/unordered_set/operator_cmp

[35] "std::merge," 2020. [Online]. Available: https://en.cppreference.com/w/cpp/algorithm/merge

[36] A. Meurer, C. P. Smith, M. Paprocki, O. Cortik, S. B. Kirpichev, M. Rocklin, A. Kumar, S. Ivanov, J. K. Moore, S. Singh, T. Rathnayake, S. Vig, B. E. Gromov, R. H. Rourke, A. Kosov, T. Levin, F. Stepanov, R. Reusch, A. Saboo, I. Fernando, S. Kulal, R. Cimrman, and A. Scopatz, "Sympy: symbolic computing in Python," *PeerJ Computer Science*, vol. 3, p. e103, 2017. [Online]. Available: https://doi.org/10.7717/peerj-cs.103

---

## AUTHOR BIOGRAPHIES

**Mashiyat Zaman** received a B.A. from Amherst College in 2018. He is currently a data engineer at Recruit Communications Co., Ltd.

**Kotaro Tanahashi** received the M.Eng from Kyoto University in 2015. He currently works for Recruit Communications Co., Ltd. as a machine learning engineer. He is also a project manager for the Project for Promotion of Computational Science and Technology (PRESTO) Information Technology Promotion (IPA).

**Shu Tanaka** received the Dr. Sci. degrees from The University of Tokyo in 2008. He is presently an associate professor in Department of Applied Physics and Physico-Informatics, Keio University and a visiting associate professor in Department of Applied Physics, Waseda University. His research interests are quantum annealing, Ising machine, statistical mechanics, and materials science. He is a member of JPS.
