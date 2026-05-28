# p-Bits for Probabilistic Spin Logic

Kerem Y. Camsari,¹ Brian M. Sutton,¹ and Supriyo Datta¹

School of Electrical and Computer Engineering, Purdue University, West Lafayette, IN 47907, USA

(Dated: 13 March 2019)

## Abstract

We introduce the concept of a probabilistic or p-bit, intermediate between the standard bits of digital electronics and the emerging qbits of quantum computing. We show that low barrier magnets or LBM's provide a natural physical representation for p-bits and can be built either from perpendicular magnets (PMA) designed to be close to the in-plane transition or from circular in-plane magnets (IMA). Magnetic tunnel junctions (MTJ) built using LBM's as free layers can be combined with standard NMOS transistors to provide three-terminal building blocks for large scale probabilistic circuits that can be designed to perform useful functions. Interestingly, this three-terminal unit looks just like the 1T/MTJ device used in embedded MRAM technology, with only one difference: the use of an LBM for the MTJ free layer. We hope that the concept of p-bits and p-circuits will help open up new exploration spaces for this emerging technology. However, a p-bit need not involve any MTJ; any fluctuating resistor could be combined with a transistor to implement it, while completely digital implementations using conventional CMOS technology are also possible. The p-bit also provides a conceptual bridge between two active but disjoint fields of research, namely stochastic machine learning and quantum computing. First, there are the applications that are based on the similarity of a p-bit to the binary stochastic neuron (BSN), a well-known concept in machine learning. Three-terminal p-bits could provide an efficient hardware accelerator for the BSN. Second, there are the applications that are based on the p-bit being like a poor man's q-bit. Initial demonstrations based on full SPICE simulations show that several optimization problems including quantum annealing are amenable to p-bit implementations which can be scaled up at room temperature using existing technology.

## CONTENTS

I. Introduction ........................ 1
   A. Between a bit and a q-bit ........ 1
   B. Binary stochastic neuron (BSN) ... 2

II. Hardware Implementation ............ 3
   A. Three-terminal p-Bit ............ 3
   B. Weighted p-bit .................. 4

III. Applications of p-circuits ........ 5
   A. Applications: Machine learning inspired 5
   B. Applications: Quantum inspired .... 6

IV. Conclusions ....................... 8

Acknowledgments ....................... 9

V. References ......................... 9

## I. INTRODUCTION

### A. Between a bit and a q-bit

Modern digital circuits are based on binary bits that can take on one of two values, 0 and 1, and are stored using well-developed technologies at room temperature. At the other extreme are quantum circuits based on q-bits which are delicate superpositions of 0 and 1 requiring the development of novel technologies typically working at cryogenic temperatures. This article is about what we call probabilistic bits or p-bits that are classical entities fluctuating rapidly between 0 and 1. We will argue that we can use existing technology to build what we call p-circuits that should function robustly at room temperature while addressing some of the applications commonly associated with quantum computing (Fig. 1).

How would we represent a p-bit physically? Let us first consider the two extremes, namely the bit and the q-bit. A q-bit is often represented by the spin of an electron, while a bit is often represented by binary voltage levels in logic elements like flip-flops and latch transistors. However, bits can also be represented as magnets which are basically collections of a very large number of spins. In a magnet, internal interactions make the energy a minimum when the spins all point either parallel or anti-parallel to a specific direction, called the easy axis. These two directions represent 0 and 1 and are separated by an energy barrier, Eb. The barrier? A nanomagnetic flips back and forth between 0 and 1 at a rate determined by the energy barrier: $\tau \sim \tau_0 \exp(E_b/k_B T)$ where $\tau_0$ typically has a value between picoseconds and nanoseconds². Assuming a $\tau_0$ of a nanosecond, a barrier of $E_b \sim 40 \, k_B T$, for example, would retain a 0 (or a 1) for ~ 10 years, making it suitable for long-term memory while a smaller barrier of $E_b \sim 14 \, k_B T$, would give ensure a short-term memory ~ 1 ms³.

It has been recognized that this stability problem also represents an opportunity. Unstable low barrier magnets (LBM) could be used to implement useful functions like random number generation (RNG)⁴⁻⁶ by sensing the randomly fluctuating magnetization to provide a random time varying voltage. With such applications in mind, we would want magnets to have as low a barrier as possible,

so that many random numbers are generated in a given amount of time. Indeed, a "zero" barrier magnet with $E_b \lesssim k_B T$ flipping back and forth in less than a nanosecond could prove useful.

How can we reduce the energy barrier? Since $E_b = H_c M_s \Omega/2$, the most obvious is to reduce the total magnetic moment by reducing volume V₀, and/or engineer a small anisotropy field $H_c$. This can be done with perpendicular magnets (PMA) designed to be close to the in-plane transition. A less challenging approach seems to be to use circular in-plane magnets (IMA)⁷. We will refer to all these possibilities collectively as LBM's as opposed to say superlattices which have more specific connotations in different contexts.³,¹⁰⁻¹⁵

We could use LBM's to represent the probabilistic bits or p-bits that we alluded to. We have argued that if these p-bits can be incorporated into proper transistor-like structures with can, then the resulting three-terminal p-bits could be interconnected to build p-circuits that perform useful functions¹¹,¹²,¹⁶. However, unlike digital circuits these probabilistic p-circuits incorporate features reminiscent of quantum circuits.

This connection was nicely articulated by Feynman in a seminal paper¹⁷, where he described a quantum computer that could provide an efficient simulation of quantum many-body problems. But to set the stage for quantum computers, he first described a probabilistic computer which could efficiently simulate classical many-body problems:

> "... the other way to simulate a probabilistic nature, which I'll call S ... is by a computer C which itself is probabilistic, ... in which the output is not a unique function of the input ... it simulates nature in this sense; that C goes from some initial state ... to some final state with the same probability that N goes from the corresponding initial state to the corresponding final state ... if you repeat the same experiment in the computer a large number of times ... it will give the frequency of a given final state proportional to the number of times ... as it happens in nature."

There are many practical problems of great interest which involve large networks of probabilistic quantum bits. These problems should be simulated efficiently by p-computers of the type envisioned by Feynman. Our purpose here is to discuss appropriate hardware building blocks that can be used to build¹⁸ and possible applications that could be used for. In this context, let us note that although spins provide a nice unifying paradigm for illustrating the transition from bits to p-bits and q-bits, the physical realization of a p-bit need not involve spins or spintronic devices; non-spintronic implementations can be just as feasible.

### B. Binary stochastic neuron (BSN)

Interestingly the concept of a p-bit connects naturally to another concept well-known in the field of machine learning, namely that of a binary stochastic neuron (BSN)¹⁸⁻¹⁹ whose response $m_i$ to an input $I_i$ can be described mathematically by

$$m_i = \text{sgn}[\tanh I_i - r] \tag{1}$$

where $r$ is a random number uniformly distributed between −1 and 1²⁰. Here we are using bipolar variables with $m_i = \pm 1$ to represent the 0 and 1 states. If we use binary variables $m_i = 0, 1$ the corresponding equation would look different²¹. When combined with a synaptic function describing

$$I_i = \sum_j W_{ij} m_j \tag{2}$$

we have a probabilistic network that can be designed to perform a wide variety of functions through a proper choice of the weights, $W_{ij}$. A separate bias term $h_i$ is often included in Eq. 2 but we will not write it explicitly, assuming that it is included in the weighted input from an extra p-bit that is always +1.

Eqs. 1 and 2 are widely used in many modern algorithms but they are commonly implemented in software. Much work has gone into developing suitable hardware accelerators for matrix multiplication of the type described by Eq. 2 (See for example, Ref.²²). Three-terminal p-bits would provide a hardware accelerator for Eq. 1. Together they would function like a probabilistic computer.

Note that a hardware accelerator for Eq. (1) requires more than just an RNG. We need a "random" RNG whose output $m_i$ can be biased through the input terminal $I_i$ as shown in Fig. 2. Two distinct designs for a three-terminal p-bit have been described.¹²,¹³ Both of which use a magnetic tunnel junction (MTJ), a popular "spintronic" device used in magnetic random access memory (MRAM)²⁴. However, MRAM applications use stable MTJ's that can store information for many years, while a p-bit makes use of "bad" MTJ's with low barriers.

The LBM-based implementation of the BSN described here is conceptually very different from a clocked approach using stable magnets where a stochastic output is obtained every time a clock pulse is applied²⁵⁻³⁰. All of these approaches work with stable magnets, although LBM could potentially be very unclocking power that is needed.

In this paper we will focus on unclocked, asynchronous operation using LBM-based hardware accelerators for the BSN (Eq. (1))¹⁰⁻¹². But even an asynchronous circuit can provide the sequential updating of the BSN's described by Eq. (1) that is required for circuits using such dedicated sequencers that update connected p-bits sequentially. A fully digital implementation of circuits using such dedicated sequencers has been realized in Ref.³². Synchronous operation can be particularly useful if synaptic delays are large enough to interfere with mutual asynchronous operation.

Here, we focus on unclocked operation in order to bring out the role of a p-bit in providing a conceptual bridge between two very active fields of research, namely stochastic machine learning and quantum computing. On the one hand p-bits provide a hardware accelerator for the BSN (Eq. (1)) thereby enabling applications inspired by machine learning (Section III). On the other hand, p-bits are the classical analogs of q-bits: robust room temperature entities accessible with current technology that could enable applications inspired by quantum computing (Section IV). But before we discuss applications, let us briefly discuss possible hardware approaches to implementing p-bits (Section II).

## II. HARDWARE IMPLEMENTATION

### A. Three-terminal p-Bit

RNG's represent an important component of modern electronics and have been implemented using many different approaches, including Johnson-Nyquist noise of resistors³³, phase noise of ring oscillators³⁴, process variations of SRAM cells³⁵ and other physical mechanisms. However, as noted earlier, we need a "random" RNG whose output can be biased through the input terminal $I_i$ as shown in Fig. 2. Two distinct designs for a three-terminal p-bit have been described.¹²,¹³ Both of which use a magnetic tunnel junction (MTJ), a popular "spintronic" device used in magnetic random access memory (MRAM)²⁴. However, MRAM applications use stable MTJ's that can store information for many years, while a p-bit makes use of "bad" MTJ's with low barriers.

The LBM-based implementation of the BSN described here is conceptually very different from a clocked approach using stable magnets where a stochastic output is obtained every time a clock pulse is applied²⁵⁻³⁰. All of these approaches work with stable magnets, although LBM could potentially be very unclocking power that is needed.

Standard MTJ devices go to great lengths to ensure that the magnets they use are stable and can store information for many years. The resistance of bad MTJ's, on the other hand, constantly fluctuates between $R_P$ and $R_{AP}$ depending on whether the magnets are parallel (P) or antiparallel (AP). MTJ's are typically used as memory devices, though in recent years applications of MTJ's for logic and novel types of computation have been discussed.²⁶⁻⁴².

An MTJ is a device with two magnetic contacts whose electrical resistance $R_y$ takes one of two values $R_P$ and $R_{AP}$ depending on whether the magnets are parallel (P) or antiparallel (AP). MTJ's are typically used as memory devices, though in recent years applications of MTJ's for logic and novel types of computation have been discussed.²⁶⁻⁴².

Standard MTJ devices go to great lengths to ensure that the magnets they use are stable and can store information for many years. The resistance of bad MTJ's, on the other hand, constantly fluctuates between $R_P$ and $R_{AP}$ depending on whether the magnets are parallel (P) or antiparallel (AP). If we put it in series with a transistor which is

fixed layer direction. This spin-current enters the sLLG equation that can achieve an instantaneous magnetization which in turn controls the MTJ resistance.

We note that an significant pinning around zero input voltage $V_{in,i}$ has to be minimized through proper design, especially for low barrier perpendicular magnets which are relatively easy to pin. Unintentional pinning⁴³ should in general not be an issue for circular in-plane LBM's due to the strong static pinning behavior for the average (steady-state) magnetization can be qualitatively understood by numerical simulations of the sLLG equation. In the case of low-barrier perpendicular magnets, the spin-torque pinning needs to overcome the thermal noise and therefore the pinning current is of order $I_{PMA} \approx 2(\alpha/\hbar)k_B T$ where $\alpha$ is the damping coefficient of the magnet. In the case of circular in-plane magnets, the pinning current is of order $I_{IMA} \approx 2(q/\hbar)k_B T M_s W_z$ which is much larger than $I_{PMA}$ since for typical parameters ($H_D M_s$ Vol. $\gg$ $kT$).

Since the state of the magnet is not affected, if the input voltage $V_{in,i}$ in Eq. 3 is changed at t = 0, the statistics of the output voltage $V_{out,i}$ will respond within tens of picoseconds (typical transistor switching speeds)⁻ irrespective of the thermal fluctuations will determine the correlation time of the random output number r in Fig. 3.

Alternatively one can envision structures where the input controls the statistics of the fluctuating resistor itself, through phenomena such as the spin-Hall effect⁴² or the magnetoelectric effect⁴³ based on a voltage control of magnetism (see for example⁴⁴). In that case, both the speed of response and the correlation time of the random number r will be determined by the specific phenomenon involved.

Non-spintronic implementations: Note that the p-bit technology discussed above uses MTJ's and the stochastic structure involving CMOS-based units in place of the MTJ showing that the physical realization of a p-bit need not involve spins⁴⁵. For example, a linear feedback shift register (LFSR) is often used to generate a pseudo-randomly fluctuating bit stream⁴⁶. We can apply this fluctuating voltage to the gate of a transistor to obtain a fluctuating resistor which can replace the MTJ in Fig. 3a. We note that the main appeal of the structure in Fig. 3 lies in its simplicity, since a 1T/MTJ device combined with two transistors provides the tunable randomness in a compact transistor-like building block. Using completely digital p-circuit implementations⁴⁷ could offer short term scalability and reliability but they would consume a much larger area and power per p-bit.

### B. Weighted p-bit

The structure in Fig. 3 gives a "neuron" that implements Eq. 1 in hardware. Such neurons have to be used in conjunction with a "synapse" that implements

**FIG. 1.** Between a bit and a q-bit: The p-bit Digital computer sits between the extremes of a bit and a q-bit is called bits to represent information in a binary code. The emerging field of quantum computing is based on the delicate superposition of 0 and 1 that typically requires cryogenic temperatures. We envision p-bit circuits to p-computing operating robustly at room temperature with existing technology.

**FIG. 2.** Three terminal p-bit: a. A hardware implementation of the BSN (Eq. (1)) provides a central stochastic element with input and output terminals that provide the ability to read and bias the element. b. The stochastic element can be visualized as going back and forth between two energy states at a rate that depends exponentially on the energy barrier $E_b$ that separates them: $\tau \sim \tau_0 \exp(\Delta/k_B T)$. The bias terminal adjusts the relative energies of the two states thereby controlling the probabilities of finding the element in the two states.

---

$G_y^{22}$. However, the input conductance $G_0$ of FET's is typically very small, so that an external conductance has to be added to make $G_0 \gg \sum_j G_{ij}$.

## III. APPLICATIONS OF P-CIRCUITS

As noted earlier, real applications involve p-bits interconnected by a synapse that can be implemented off-chip either in software or with a hardware matrix multiplier, but then it is necessary to transfer data back and forth between Eq. 1 and Eq. 2. Therefore, a low-level compact hardware implementation of a p-bit along with a local synapse as envisioned in Fig. 4 could be the hardware accelerator for many types of applications, some of which will be discussed in this section. In the completely weighted p-bit design of Fig. 4, the weights and connectivity of the p-bit could be dynamically adjusted based on the encoding of a given problem by leveraging a network of programmable switches⁴⁸ as would be encountered in FPGAs. Such a p-bit with local interconnections would look like a compact nanodevice implementation of highly scaled digital spintronic chips such as TrueNorth⁴⁴. Alternatively, the interconnection function could be performed off-chip using standard CMOS devices such as FPGAs or GPUs while p-bits are implemented in a standalone chip by modifying embedded MRAM technology. Note however, the off-chip implementation of the interconnection matrix would impose a timing constraint for an asynchronous mode of operation, which requires the weighted summation operation (Eq. 2) to operate much faster than the p-bit operation (Eq. 1) for proper convergence⁵,⁶,⁷. A full on-chip implementation of reconfigurable p-bit function as a low-power, efficient hardware accelerator for applications in Machine Learning and Quantum Computing, but in the near term a heterogeneous multi-chip synapse / p-bit combination could also prove to be useful.

Now that we have discussed some possible approaches to implementing Eqs. 1 and 2 in hardware, let us present a few illustrative p-bit networks that implement useful functions and can be built using existing technol­ogy. Unless otherwise stated, these results are obtained from full SPICE simulations⁵⁸ that solve the stochastic Landau-Lifshitz-Gilbert equations coupled with the PTM-based transistor models in SPICE to model the embedded MTJ based 3-terminal p-bit described in Fig. 3.

### A. Applications: Machine learning inspired

**Bayesian inference:** A natural application of stochastic circuits is in the simulation of stochastic processes whose nodes are stochastic in nature (See for example⁴⁶,⁵⁷⁻⁵⁹). An archetypal example is a genetic network, a small version of which is shown in Fig. 5. A well-known concept is that of genetic correlation or relatedness between different members of a family tree. For example, assuming

that each of the children $C_1$ and $C_2$ get half their genes from their parents $F_1$ and $M_1$ we can write their correlation as:

$$(C_1 \times C_2) = \langle (0.5F_1 + 0.5M_1) \times (0.5F_1 + 0.5M_1) \rangle$$

$$= \frac{1}{4}(F_1 \times F_1) + (F_1 \times M_1) + (M_1 \times F_1) + (M_1 \times M_1)$$

$$= \frac{1}{4}(1 + 0 + 0 + 1) = 0.5 \tag{5}$$

assuming $F_1$ and $M_1$ are uncorrelated. Hence the well-known result that siblings have 50% relatedness. Similarly one can work out the relatedness of more distant relationships like that of an aunt $M_1$ and her nephew $C_3$ which turns out to be 25%.

The point is that we could construct a p-circuit with each of the nodes represented by a hardware p-bit interconnected to redact the genetic influences. The correlation between two nodes, $C_1$ and $C_2$, is given by

$$(C_1 \times C_2) = \int_0^T \frac{dt}{T} C_1(t) C_2(t) \tag{6}$$

If $C_1(t)$ and $C_2(t)$ are binary variables with allowed values of ±1 and then they can be multiplied in hardware with an AND gate. If the allowed values are bipolar, then the multiplication can be implemented with an XNOR gate. In either case the average over time can be performed with a long time constant RC circuit. A few typical results from SPICE simulations are shown in Fig. 5. The numerical results in Fig. 5 are in good agreement with Bayes theorem even though the circuit operates asynchronously without any sequencers. This is interesting since software simulations of Eqs. 1 and 2 with directed weights usually require the nodes to be updated from parent to child. Whether this behavior generalizes to larger directed networks is left for future work.

**Accelerating learning algorithms:** Networks of p-bits could be useful for implementing inference networks, where the network weights are trained offline by a learning algorithm in software and the hardware is used to repeatedly generate inference⁶⁰,⁶¹,⁶². Another common example where correlations play an important role is in the learning algorithms used to train modern neural networks like the restricted Boltzmann machine (Fig. 6)⁶³ having a visible layer and a hidden layer, with connecting weights $W_{ij}$ linking nodes of one layer to those in the other, but not within a layer. A widely used algorithm based on "contrastive divergence" can be efficiently implemented by gradient descent⁶⁴. Such networks having symmetric connections is particularly interesting since they have a close parallel with classical statistical physics where the natural connections between interacting particles are symmetric and the equilibrium probabilities are given by the celebrated Boltzmann law expressing the probability of a particular configuration σ in terms of an energy $E_σ$ associated with

**FIG. 3.** Embedded MRAM p-bit: a. An NMOS pull-down transistor in series with a stochastic-MTJ whose resistance fluctuates between $R_P$ and $R_{AP}$ as shown in b. c. Using a 14 nm FinFET model³⁴ the input voltage, $V_{in}$, versus mid-point, $V_{o}$ and output $V_{o}$ voltages is simulated in SPICE. Several fixed resistances are shown to convey how $V_{o}$ would vary with modifications to the parallel and anti-parallel resistances.

---

$$V_{in} = \frac{V_{DD} R_f(V_{in}) - R_{MTJ}}{2 \cdot R_f(V_{in}) + R_{MTJ}}$$

The magnitude of this fluctuating voltage $V_m$ is largest when the transistor is at equilibrium, either $R_P \approx R_P$ or $R_P \gg R_{AP}$, but gets suppressed if $R_P \ll R_P$ or $R_P \gg R_{AP}$. The input voltage $V_m$ thus during the stochastic output $V_{out}$ as shown in Fig. 3c. It was shown that an additional inverter provides an output that is approximately described by the expression that looks just like the BSN (Eq. 1):

$$\frac{m_0}{V_{out,i}} \approx \text{sgn}\left[\tanh\left(\frac{V_{out,i}}{V_0}\right) - r\right] \tag{3}$$

but with dimensionless variables like $m_i$ and $I_i$ replaced by scaled versions $V_{out}$ and $V_{in}$.

The scheme in Fig. 3 provides tunability through the series transistor and does not involve the physics of the fluctuating resistor. Ideally, the magnet is unaffected by the change in the transistor resistance though in principle, could pin the magnet. In our simulations that are based on Ref.¹⁴, we take the pinning current into account through a spin-polarized current, ($I_x$) proportional to an effective fixed layer polarization and the drain current $(I_D)$, $I_x = (P) I_D x$, where $x$ is

---

**FIG. 4.** Example of a weighted p-bit integrating relevant parts of the synapse onto the neurons: Leveraging floating-gate devices along the lines proposed in neMOS⁵¹ devices, a collection of synapse inputs (from 1 to n) can be summed to produce the bias voltage, $V_{in}$, for a voltage driven p-bit²⁶.

---

Eq. 2. Alternatively we could design a "weighted p-bit" that integrates each element of Eq. 1 with the relevant part of Eq. 2. For example, we could use floating gate transistors⁵⁰ devices as shown in Fig. 4. From charge conservation we can write

$$\sum(V_{out,j} - V_{in,i}) C_{ij} - V_{in,i} C_0 = 0$$

where $C_0$ is the input capacitance of the transistor. This can be rewritten as

$$V_{in,i} = \sum_j \frac{C_{ij}}{C_0 + \sum_j C_{ij}} \cdot V_{out,j}$$

By scaling $V_{in}$ and $V_{out}$ (see Eq. 3) to play the roles of the dimensionless quantities $I_i$ and $m_i$ respectively, we can recast Eq. 4 in the form similar to Eq. 2:

$$\frac{I_i}{V_{0}} = \sum \frac{V_{DD}}{2(C_0 + \sum_j C_{ij})} \cdot \frac{C_{ij}}{C_0 + \sum_j C_{ij}} \cdot \frac{V_{out,j}}{V_{DD}/2} \tag{4}$$

The weights $W_{ij}$ can be adjusted by controlling the specific capacitors $C_{ij}$ that are connected. The range of allowed weights and connections is then limited by the routing topology and device size. Note that the control of weights through $C_{ij}$ works best if $C_0 \gg \sum_j C_{ij}$ so that $W_{ij} = \frac{C_{ij}}{C_0}$. However, it is possible to design a weighted p-bit design without this assumption ($C_0 \gg \sum C_{ij}$) as discussed in detail in Ref.⁵².

Similar control can also be achieved through a network of resistors. The weights are given by the same expression, but with capacitances $C_{ij}$ replaced by conductances

---

that configuration.

$$P_\sigma = \frac{1}{Z} \exp(-E_\sigma) \tag{7}$$

$$E_\sigma = -\{m\}^T [W] \{m\}_\sigma \tag{8}$$

where $T$ denotes transpose and the constant $Z$ is chosen to ensure that all $P_\sigma$'s add up to one. This energy principle is very useful in determining the appropriate weights $W_{ij}$ for a particular problem.

This class of networks connects naturally to the world of quantum computing which is governed by Hermitian Hamiltonians⁶⁵ and is also the subject of the emerging field of Ising computing.¹⁰,¹⁶⁻⁷². 

**Invertible Boolean logic:** Suppose, for example, we wish to design a Boolean gate that will provide three outputs reducing the AND, OR and XNOR functions of the two inputs A and B. The truth table is shown in Fig. 7. Note that although we are using the binary notation 1 and 0, they actually stand for p-bit values of +1 and −1 respectively.

Since there are five p-bits, two representing the inputs and three representing the outputs, the system has $2^5 = 32$ possible states, which can be indexed by their corresponding decimal values. Each of these configurations has an associated energy, $E_n$, n = 0, 1, ..., 31. What we need is a weight matrix $W_{ij}$ such that the desired configurations 4, 9, 17 and 31 (in decimal notation) specified by the truth table have an energy lower than the rest, so that they are occupied with higher probability. This can be done either by using the principles of linear algebra⁶⁴ or by using machine learning algorithms⁶⁵ to obtain the weight matrix shown in Fig. 7.

Note that an additional p-bit labeled "h" has been introduced which is clamped to a value of +1 by applying a bias. In the unclamped mode, the system shows the states corresponding to the lines of the truth table with high probability. A and B can be clamped to produce the correct output for the XNOR, AND OR in the direct mode. In the inverse mode, one of the outputs (XNOR is shown as an example) can be clamped to a given value, and the inputs fluctuate among possible input combinations corresponding to this output, indicating that we can use these gates to provide us with all possible inputs consistent with a specified output, a mode of operation not possible with standard Boolean gates.

What is more interesting is that the gates can be run in inverse mode as shown in the lower right panel. The XNOR output is clamped to 0 corresponding to specific lines of the truth table, corresponding to A = 1, B = 0, showing that we can use these gates to provide us with all possible inputs consistent with a specified output, a mode of operation not possible with standard Boolean gates.

### B. Applications: Quantum inspired

The functionality of neural networks is determined by the weight matrix $W_{ij}$, which determines the connectivity among the neurons. They can be classified broadly by the relation between $W_{ij}$ and $W_{ji}$. In traditional feedforward networks, information flow is directed with neuron 'i' influencing neuron 'j' through a non-zero weight $W_{ij}$ but not with $W_{ji} = 0$. At the other end of the spectrum, is a network with all connections being reciprocal. $W_{ij} = W_{ji}$. In between these two extremes are the class of networks for which the weights between two nodes are asymmetric, but non-zero.

The class of networks with symmetric connections is particularly interesting since they have a close parallel with classical statistical physics where the natural connections between interacting particles are symmetric and the equilibrium probabilities are given by the celebrated Boltzmann law expressing the probability of a particular configuration σ in terms of an energy $E_σ$ associated with

---

**FIG. 5.** Genetic circuit: $C_1$ and $C_2$ are siblings with parents $F_1$, $M_1$, while $C_3$ and $C_4$ are siblings with parents $F_2$, $M_2$. Two of the parents $M_1$ and $F_2$ are siblings with parents $GF_1$, $GM_1$. Genetic correlations between different numbers can be evaluated from the correlations of the nodal voltages in a p-circuit. An XNOR gate links them together while a long RC circuit provides the time average.

---

**FIG. 6.** Restricted Boltzmann Machine (RBM): RBMs are a special class of stochastic neural networks that restrict connections within a hidden and a visible layer. Standard learning algorithms require repeated evaluations of correlations of the form $\langle v_i h_j \rangle$.

---

**FIG. 7.** Invertible Boolean logic: A multi-function Boolean gate with 6 p-bits is shown. Inputs A and B produce the output corresponding to the OR, AND or XOR gates respectively. The handle bit, "h" is used to remove the complementary low-energy states that do not belong to the truth table shown. In the unclamped mode, the system shows the states corresponding to the lines of the truth table with high probability. A and B can be clamped to produce the correct output for the XNOR, AND OR in the direct mode. In the inverse mode, one of the outputs (XNOR is shown as an example) can be clamped to a given value, and the inputs fluctuate among possible input combinations corresponding to this output.

---

The Boltzmann law, such that

$$\frac{P_{\text{desired}}}{P_{\text{undesired}}} = \exp(E_{\text{undesired}} - E_{\text{desired}})$$

Undesired peaks can be suppressed if we make the W-matrix larger, say by an overall multiplicative factor of 2. If all energies are increased by a factor of 2, the ratio of probabilities would be squared: a ratio of 10 would become a ratio of 100.

It is also possible to operate the gate in a traditional feed-forward manner where inputs are specified and an output is obtained. This mode is shown in the middle panel on the right where the inputs A and B are clamped and the outputs are set up as specified and the outputs fluctuate among the solutions consistent with the specified input, a mode of operation not possible with standard Boolean gates.

## IV. CONCLUSIONS

In summary, we have introduced the concept of a probabilistic or p-bit, intermediate between the standard bits of digital electronics and the emerging q-bits of quantum computing. Low barrier magnets or LBM's provide a natural physical representation for p-bits and can be built either from perpendicular magnets (PMA) designed to be close to the in-plane transition or from circular in-plane magnets (IMA). Magnetic tunnel junctions (MTJ) built using LBM's as free layers can be combined with standard NMOS transistors to provide three-terminal building blocks for large scale probabilistic circuits that can be designed to perform useful functions. Interestingly, this three-terminal unit looks just like the 1T/MTJ device used in embedded MRAM technology, with

---

**FIG. 8.** Combinatorial Optimization: A 5-city Traveling Salesman Problem (TSP) implemented using a network of 16 p-bits (using 61 p-bit (0). Each having two indices, the first denoting the order in which a city is visited and the second denoting the city. The interaction matrix $J$ scales all weights and acts as an inverse temperature and is slowly increased via a Simulated Annealing schedule $I_c = \{(1+\epsilon) n(I_c)$, to guide the system into the lowest energy state, providing the shortest traveling distance (Map imagery data: Google, Terrametrics).

---

vice used in embedded MRAM technology, with only one difference: the use of an LBM for the MTJ free layer. We hope that the concept of p-bits and p-circuits will help open up new application spaces for this emerging technology. However, a p-bit need not involve any MTJ; any fluctuating resistor could be combined with a transistor to implement it. It may be interesting to look for resistors that can fluctuate faster based on entities like natural and synthetic antiferromagnets⁷⁶, for example.

The p-bit also provides a conceptual bridge between two active bit disjoint fields of research, namely stochastic machine learning and quantum computing. This viewpoint suggests two broad classes of applications for p-bits. First, there are the applications that are based on the similarity of a p-bit to the binary stochastic neuron (BSN), a well-known concept in machine learning. Three-terminal p-bits could provide an efficient hardware accelerator for the BSN. Second, there are the applications that are based on the p-bit being like a poor man's q-bit. We are encouraged by the initial demonstrations based on full SPICE simulations that several optimization problems including quantum annealing are amenable to p-bit implementations which can be scaled up at room temperature using existing technology.

## ACKNOWLEDGMENTS

S.D. is grateful to Dr. Behtash Behin-Aein for many stimulating discussions leading up to Ref.¹⁶.

## V. REFERENCES

1. E. Chen, D. Apalkov, Z. Diao, A. Driskell-Smith, D. Druist, D. Lottis, V. Nikitin, X. Tang, S. Watts, S. Wang, S. Wolf, "Advances and Future Prospects for Spintronic Technology," IEEE Transactions on Magnetics 46, 1873–1878 (2010).

2. "L. López-Díaz, L. Torres, and E. Moro, "Transition from ferromagnetism to superparamagnetism on the nanosecond time scale," Physical Review B 65, 224406 (2002).

3. N. Locatelli, A. Mizrahi, A. Accioly, R. Matsumoto, H. Fukushima, H. Kubota, S. Yuasa, V. Cros, L. G. Perotta, D. Querlioz, et al., "Noise-enhanced synchronization of stochastic magnetic oscillators," Physical Review Applied 2, 034009 (2014).

4. H. Parks, B. Basna, J. Igbokwe, H. Almasi, W. Wung, and S. A. Majumbi, "Superparamagnetic magnetic tunnel junctions for true random number generators," AIP Advances 8, 056322 (2018). https://doi.org/10.1063/1.5006422.

5. D. Vodenicarevic, N. Locatelli, A. Mizrahi, J. Friedman, A. Vincent, M. Bourova, A. Fukushima, K. Yakushiji, H. Kubota, S. Yuasa, Energy Efficient Stochastic Computing with Superparamagnetic Tunnel Junctions, in 2018 IEEE International Symposium on Circuits and Systems (ISCAS) (2018), pp. 2–1.

6. "D. Vodenicarevic, N. Locatelli, A. Mizrahi, J. Freedman, A. Vincent, M. Bourova, A. Fukushima, K. Yakushiji, H. Kubota, S. Yuasa, V. Cros, L. G. Perolla, D. Querlioz, "Circuit-Level Evaluation of Truly Random Switching of Superparamagnetic Tunnel Junctions," in 2018 IEEE International Symposium on Circuits and Systems (ISCAS) (2018), pp. 1–4.

7. P. Debasish, R. Faria, K. Y. Camsari, and Z. Chen, "Designing Circuits and Systems for Probabilistic Spin Logic," IEEE Magnetics Letters (2018).

8. R. D. Devore, D. Kotsov, A. O. Adeyev, M. E. Weilandt, and D. M. Trucker, "Single-domain circular nanomagnets," Physical Review Letters 83, 1041 (1999).

9. P. Debasish, R. Faria, K. Y. Camsari, and Z. Chen, "Designs and Systems for Probabilistic Spin Logic," IEEE Magnetics Letters (2018).

10. K. Y. Camsari, S. Chowdhury, and S. Datta, "Stochastic p-Bits for Inverted Logic," Physical Review X 7, 031014 (2017).

11. K. Y. Camsari, Z. Perviz, B. M. Sutton, and S. Datta, "Implementing p-Bits with Embedded MTJ," IEEE Electron Device Letters 38, 1767–1770 (2017).

12. K. Y. Camsari, S. Raghid, and S. Datta, "Low-barrier Nanomagnets as p-Bits for Spin Logic," IEEE Magnetics Letters 8, 1–5 (2017).

13. K. Y. Camsari, R. Faria, B. M. Sutton, and S. Datta, "Stochastic p-Bits for Inverted Logic," Physical Review X 7, 031014 (2017).

14. K. Y. Camsari, S. Chowdhury, and S. Datta, "Low-barrier Nanomagnets as p-Bits for Spin Logic," Physical Review X 10, 031013 (2017).

15. K. Faria, R. Camsari, and S. Datta, "Implementing p-bits With Embedded MTJ," IEEE Electron Device Letters 38, 1767–1770 (2017).

16. M. Mizrahi, I. Hrtalin, A. Fukushima, H. Kubota, S. Yuasa, J. Grollier, and D. Querlioz, "Neural-like computing with populations of superparamagnetic nanoparticles," Scientific reports 8, 1533 (2018).

17. S. Manstruni, D. E. Nikanov, and I. A. Young, "Beyond cmos computing with spin and polarization," Nature Physics 14, 338 (2018).

18. M. Jerry, A. Periller, A. Raychoudhury, and S. Datta, "A random number generator based on nanomagnetic switching," in Proceedings of the 2017 on Design of Circuits and Systems for IoT Applications (Dynam Systems 7, 10994 (2017).

19. T. G. Lewis and W. H. Payne, "Generalized Feedback Shift Register Pseudorandom Number Algorithm," Journal of the ACM 20, 456–468 (1973).

20. T. Shibata and T. Ohmi, "A functional MOS transistor featuring gate-level voltage-sensing," IEEE Transactions on Electron Devices 39, 1444–1455 (1992).

21. G. Lendieux and D. Lewis, "Design of interconnection Networks," Programmable US: Boston, MA, 2001.

22. P. A. Merolla, J. V. Arthur, R. Alvarez-Icaza, A. S. Cassidy, J. Sawada, F. Akopyan, B. L. Jackson, B. Imam, C. Guo, and Y. Nakamura, "A million spiking-neuron integrated circuit with 100 million programmable synapses," Science 345, 668–673 (2014).

23. S. A. Pervaiz, L. A. Guntasaka, K. Y. Camsari, and S. Datta, "Hardware-efficient Compute with Stochastic Devices for Probabilistic and Quantum Computing," Scientific reports 7, 10994 (2017).

24. K. Camsari, S. Chowdhury, and S. Datta, "Modular approach to Spintronics," Scientific reports 5, 10571 (2015).

25. L. N. Chakraborty, K. Kodama, and B. E. Akgul, K. Palem, "Probabilistic system-on-chip architectures," ACM Transactions on Design Automation of Electronic Systems (TODAES) 12, 29 (2007).

26. D. Querlioz, O. Bichler, A. F. Vincent, and C. Gamrat, "Bioim-inspired programming of memory devices for implementing an inference engine," Proceedings of the IEEE 103, 1398–1416 (2015).

27. A. Serrano, M. Shin, S. Chen, A. Sengupta, and K. Roy, "Stochastic computing with spin and polarization," arXiv preprint arXiv:1801.09126 [cs] (2018).

28. G. Lendieux and D. Lewis, "Design of Interconnection Networks," Programmable Circuits and Systems US: Boston, MA, 2001.

29. P. A. Merolla, J. V. Arthur, R. Alvarez-Icaza, A. S. Cassidy, J. Sawada, F. Akopyan, B. L. Jackson, B. Imam, C. Guo, and Y. Nakamura, "A million spiking-neuron integrated circuit with 100 million programmable synapses," Science 345, 668–673 (2014).

30. J. B. Aimetti, M. C. Genetti, J. U. James, L. S. Hartz, J. O. Dickinson, M. Nakajima, J. M. Helmbrecht, A. R. Bauer, and S. Coll, "A million spiking neuron integrated circuit," Proceedings of the 2017 IEEE Custom Integrated Circuits Conference (CICC), San Antonio, TX, USA, 1–2.

31. I. Oksuz, K. Kodama, I. Zubada, and J. Knottenbelt, et al., "Training restricted Boltzmann machines: An introduction," arXiv preprint arXiv:1704.04298 (2017).

32. K. Y. Camsari, S. Chowdhury, and S. Datta, "Stochastic p-Bits for Inverted Logic," Physical Review X 7, 031014 (2017).

33. P. L. McMahon, A. Marandi, Y. Haribara, R. Hamerly, V. Langrock, S. Tamate, T. Inagaki, H. Takesue, S. Utsunomiya, and S. Modes, "A fully programmable 100-spin coherent Ising machine with all-to-all connections," Science 354, 614–617 (2016).

34. A. Narra, T. Orlando, L. Levitov, L. Tian, C. H. Van der Wal, and S. Lloyd, "Dispersive persistent-qubit control," Science 285, 1036–1039 (1999).

35. M. W. Johnson, M. H. Amin, S. Gildert, T. Lanting, F. Hamze, N. Dickson, R. Harris, A. J. Berkley, J. Johansson, P. Bunyk, et al., "Quantum annealing with a manufactured processor," Nature 473, 194 (2011).

36. S. Inokuchi, R. Harris, A. J. Berkley, J. Johansson, P. Bunyk, et al., "Quantum annealing with a manufactured processor," Nature 473, 194 (2011).

37. K. Inokuchi, and I. A. Young, "Beyond cmos computing with spin and polarization," Nature Physics 14, 338 (2018).

38. K. Albahari, and D. Lidar, "Adiabatic quantum computation," arXiv preprint arXiv:1002.1602 (2018).

39. K. Albahari, and D. Lidar, "Adiabatic quantum computation," arXiv preprint arXiv:1002.1602 (2018).

40. X. Yao, J. Harms, A. Lyle, F. Ebrahimi, Y. Zhang, and J.-P. Wang, "Nanomagnetic logic units operated by spin transfer torque," IEEE Transactions on Nanotechnology 11, 120–129 (2012).

41. J. Grollier, D. Querlioz, and M. D. Stiles, "Spintronic nanodevices for bioinspired computing," Proceedings of the IEEE 104, 2024–2039 (2016).

42. N. Locatelli, V. Cros, and J. Grollier, "Spin-torque building blocks," Nature materials 13, 11 (2014).

43. C. V. Cao, D. Sic, D. Cholemansky, and C. Hu, "Predictive technology model," internet: http://ptm, aau, edu (2002).

44. O. Heinonen, M. K. Curtarolo, and J. Grollier, "Spin-torque building blocks," Nature materials 13, 11 (2014).

45. G. Lendieux and D. Lewis, "Design of Interconnection Networks," Programmable US: Boston, MA, 2001.

46. A. Merolla, J. V. Arthur, R. Alvarez-Icaza, A. S. Cassidy, J. Sawada, F. Akopyan, B. L. Jackson, B. Imam, C. Guo, and Y. Nakamura, "A million spiking-neuron integrated circuit with 100 million programmable synapses," Science 345, 668–673 (2014).

47. M. Horowitz, R. D. S. Tan, and R. Mazumdar, "An Introduction to Probabilistic Bayesian Networks," arXiv preprint arXiv:1709.08026 (2018).

48. D. Querlioz, O. Bichler, A. F. Vincent, and C. Gamrat, "Bioinspired programming of memory devices for implementing an inference engine," Proceedings of the IEEE 103, 1398–1416 (2015).

49. S. Manipal, D. E. Nikanrov, and I. A. Young, "Beyond cmos computing with spin and polarization," Nature Physics 14, 338 (2018).

50. M. Horowitz, T. Weissman, and J. Yu, "Electrical and optical communication architectures on a single chip," in 15th Annual IEEE Symposium on Computational Complexity (CCC) (2000), pp. 1–9.

51. E. Skafidas, D. E. Nikarcov, and T. Mizuki, "Scaling probabilistic architectures through communication," ACM Transactions on Design Automation of Electronic Systems (TODAES) 12, 29 (2007).

52. D. Querlioz, O. Bichler, A. F. Vincent, and C. Gamrat, "Bioinspired programming of memory devices for implementing an inference engine," Proceedings of the IEEE 103, 1398–1416 (2015).

53. S. Manipal, D. E. Nikanrov, and I. A. Young, "Beyond cmos computing with spin and polarization," Nature Physics 14, 338 (2018).

54. A. Narra, T. Orlando, L. Levitov, L. Tian, C. H. Van der Wal, and S. Lloyd, "Dispersive persistent-qubit control," Science 285, 1036–1039 (1999).

55. G. Lendieux and D. Lewis, "Design of Interconnection Networks," Programmable US: Boston, MA, 2001.

56. S. J. Habib, M. Marzouki, and H. Amaout, "Quantum algorithms and applications," Nature Reviews Physics 1, 147–160 (1985).

57. T. G. Lewis and W. H. Payne, "Generalized Feedback Shift Register Pseudorandom Number Algorithm," Journal of the ACM 20, 456–468 (1973).

58. P. D. Mcmahor, A. Marandi, Y. Haribara, R. Hamerly, V. Langrock, S. Tamate, T. Inagaki, H. Takesue, S. Utsunomiya, and S. Modes, "A fully programmable 100-spin coherent Ising machine with all-to-all connections," Science 354, 614–617 (2016).

59. M. W. Johnson, M. H. Amin, S. Gildert, T. Lanting, F. Hamze, N. Dickson, R. Harris, A. J. Berkley, J. Johansson, P. Bunyk, et al., "Quantum annealing with a manufactured processor," Nature 473, 194 (2011).

60. X. Yao, J. Harms, A. Lyle, F. Ebrahimi, Y. Zhang, and J.-P. Wang, "Nanomagnetic logic units operated by spin transfer torque," IEEE Transactions on Nanotechnology 11, 120–129 (2012).

61. J. Grollier, D. Querlioz, and M. D. Stiles, "Spintronic nanodevices for bioinspired computing," Proceedings of the IEEE 104, 2024–2039 (2016).

62. N. Locatelli, V. Cros, and J. Grollier, "Spin-torque building blocks," Nature materials 13, 11 (2014).

63. C. V. Cao, D. Sic, D. Cholemansky, and C. Hu, "Predictive technology model," internet: http://ptm, aau, edu (2002).

64. H. G. Hinton, "Training products of experts by minimizing contrastive divergence," Neural Computation 14, 1771–1800 (2002).

65. A. Hinton, "A learning algorithm for Boltzmann machines," Cognitive science 9, 147–169 (1985).

66. T. G. Lewis and W. H. Payne, "Generalized Feedback Shift Register Pseudorandom Number Algorithm," Journal of the ACM 20, 456–468 (1973).

67. P. L. Shaih and W. H. Payne, "Polynomial-time algorithms for prime factorization and discrete logarithms on a quantum computer," SIAM review 41, 303–332 (1999).

68. E. L. Traversa and M. Di Ventra, "Polynomial-time solution of prime factorization and up-complete problems with digital memcomputing machines," Chaos: An Interdisciplinary Journal of Nonlinear Science 27, 023107 (2017).

69. M. Ventra and F. L. Traversa, "Perspective: Memcomputing: Leveraging memory and physics to compute efficiently," The Journal of Applied Physics 123, 180901 (2018). https://doi.org/10.1063/1.5026506.

70. A. Lucas, "Ising formulation of many problems," Frontiers in Physics 2, 5 (2014).

71. X. Peng, Z. Liao, N. Xu, G. Qin, X. Zhou, D. Suter, and J. Du, "Quantum adiabatic algorithm for factorization and its experimental implementation," Physical review letters 101, 220405 (2008).

72. A. Perez-Garcia, D. Lidar, and K. Riedmiller, "Adiabatic quantum computation," arXiv preprint arXiv:1002.1602 (2018).

73. K. Albahari and D. Lidar, "Adiabatic quantum computation," arXiv preprint arXiv:1002.1602 (2018).

74. K. G. Munn and S. Schaal, "Shape assemblies in guiding quadratic and nonlinear programming," Mathematical programming 23, 1 (1982).

75. P. W. Shor, "Polynomial-time algorithms for prime factorization and discrete logarithms on a quantum computer," SIAM review 41, 303–332 (1999).

76. F. L. Traversa and M. Di Ventra, "Polynomial-time solution of prime factorization and up-complete problems with digital memcomputing machines," Chaos: An Interdisciplinary Journal of Nonlinear Science 27, 023107 (2017).

77. M. Johnson, I. Rotman, D. Ciliberto, R. Hamerly, J. Inagaki, H. Takesue, T. Tamate, and S. Modes, "A fully programmable 100-spin coherent Ising machine with all-to-all connections," Science 354, 614–617 (2016).

78. T. Shiojiri, T. Ômini, "A functional MOS transistor featuring gate-level voltage-sensing," IEEE Transactions on Electron Devices 39, 1444–1455 (1992).

79. C. Lyamagedern, A. Sengupta, A. Jaiswal, and K. Roy, "Stochastic spiking neuron networks enabled by magnetic tunnel junctions," in IJCNN (2017).

80. P. Debasish, R. Faria, K. Y. Camsari, and Z. Chen, "Current control of time-averaged magnetization in supermagnetic tunnel junctions," Applied Physics Letters 111, 243107 (2017).

81. K. Lytle, S. Patil, J. Harms, B. Glass, X. Yao, D. Lilja, and J.-P. Wang, "Magnetic tunnel junction logic architecture for realization of simultaneous computation and communication," IEEE (2016).

82. J. Jackson, M. Imani, K. Islam, L. S. Katz, J. O. Lyons, and J. Burl, "Quantum annealing with a manufactured processor," Nature 473, 194 (2011).

83. S. Inokuchi, R. Harris, A. J. Berkley, J. Johansson, P. Bunyk, et al., "Quantum annealing for hardware-implemented bayesian networks," Communications in biology and medicine 69, 253–253 (2016).

84. W. J. Gross, "Vlsi implementation of deep neural network using intrinsic stochasticity in standard cmos," IEEE Transactions on Very Large Scale Integration (VLSI) Systems 26, 2688–2699 (2017).

85. G. Leon and W. H. Payne, "Generalized Feedback Shift Register Pseudorandom Number Algorithm," Journal of the ACM 20, 456–468 (1973).

86. P. Shaih and T. Woeshoiwisky, A. Nøjorolanth, M. Kasinski, T. Tylskly, Z. Kulicqa, K. Kovas, P. Matasyiuk, R. Tcmalin, and M. Wenerath, "Real-time prediction of acute cardiovascular," Biophysics and Medicine 32, 1–9 (2018).

