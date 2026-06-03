# p-Bits for Probabilistic Spin Logic

> **Citation.** K. Y. Camsari, B. M. Sutton, and S. Datta. "p-bits for probabilistic
> spin logic." *Applied Physics Reviews* 6(1):011305 (2019).
> DOI: [10.1063/1.5055860](https://doi.org/10.1063/1.5055860).
> Preprint: [arXiv:1809.04028](https://arxiv.org/abs/1809.04028) (v2, 11 Mar 2019).
> BibTeX key: `camsari2019pbits` (see [`references.bib`](../../references.bib)).
>
> **Source.** Faithful transcription of the published text layer
> (`camsari-2018-probabilistic-spin-logic.pdf`) via
> [`tools/transcribe_pdf.py`](../../../tools/transcribe_pdf.py); section headings
> reconstructed and load-bearing equations rendered to LaTeX. Figure bitmaps are
> not reproduced; their captions are retained inline. This file is the transcript;
> the Gibbsiq-facing reading notes live in
> [`camsari-2018-probabilistic-spin-logic.note.md`](./camsari-2018-probabilistic-spin-logic.note.md).

**Kerem Y. Camsari, Brian M. Sutton, and Supriyo Datta**
School of Electrical and Computer Engineering, Purdue University, West Lafayette, IN 47907, USA
(Dated: 13 March 2019)

## Abstract

We introduce the concept of a probabilistic or p-bit, intermediate between the
standard bits of digital electronics and the emerging q-bits of quantum computing.
We show that low barrier magnets or LBM's provide a natural physical representation
for p-bits and can be built either from perpendicular magnets (PMA) designed to be
close to the in-plane transition or from circular in-plane magnets (IMA). Magnetic
tunnel junctions (MTJ) built using LBM's as free layers can be combined with
standard NMOS transistors to provide three-terminal building blocks for large scale
probabilistic circuits that can be designed to perform useful functions.
Interestingly, this three-terminal unit looks just like the 1T/MTJ device used in
embedded MRAM technology, with only one difference: the use of an LBM for the MTJ
free layer. We hope that the concept of p-bits and p-circuits will help open up new
application spaces for this emerging technology. However, a p-bit need not involve
an MTJ, any fluctuating resistor could be combined with a transistor to implement
it, while completely digital implementations using conventional CMOS technology are
also possible. The p-bit also provides a conceptual bridge between two active but
disjoint fields of research, namely stochastic machine learning and quantum
computing. First, there are the applications that are based on the similarity of a
p-bit to the binary stochastic neuron (BSN), a well-known concept in machine
learning. Three-terminal p-bits could provide an efficient hardware accelerator for
the BSN. Second, there are the applications that are based on the p-bit being like a
poor man's q-bit. Initial demonstrations based on full SPICE simulations show that
several optimization problems including quantum annealing are amenable to p-bit
implementations which can be scaled up at room temperature using existing technology.

## I. Introduction

### A. Between a bit and a q-bit

Modern digital circuits are based on binary bits that can take on one of two values,
0 and 1, and are stored using well-developed technologies at room temperature. At
the other extreme are quantum circuits based on q-bits which are delicate
superpositions of 0 and 1 requiring the development of novel technologies typically
working at cryogenic temperatures. This article is about what we call probabilistic
bits or p-bits that are classical entities fluctuating rapidly between 0 and 1. We
will argue that we can use existing technology to build what we call p-circuits that
should function robustly at room temperature while addressing some of the
applications commonly associated with quantum circuits (Fig. 1).

How would we represent a p-bit physically? Let us first consider the two extremes,
namely the bit and the q-bit. A q-bit is often represented by the spin of an
electron, while a bit is often represented by binary voltage levels in digital
elements like flip-flops and floating-gate transistors. However, bits can also be
represented by magnets which are basically collections of a very large number of
spins. In a magnet, internal interactions make the energy a minimum when the spins
all point either parallel or anti-parallel to a specific direction, called the easy
axis. These two directions represent 0 and 1 and are separated by an energy barrier,
$E_b$, that ensures their stability.

How large is the barrier? A nanomagnet flips back and forth between 0 and 1 at a
rate determined by the energy barrier: $\tau \sim \tau_0 \exp(E_b / k_B T)$ where
$\tau_0$ typically has a value between picoseconds and nanoseconds. Assuming a
$\tau_0$ of a nanosecond, a barrier of $E_b \sim 40\, k_B T$, for example, would
retain a 0 (or a 1) for $\sim 10$ years, making it suitable for long term memory
while a smaller barrier of $E_b \sim 14\, k_B T$ would only ensure a short term
memory $\sim 1$ ms.

It has been recognized that this stability problem also represents an opportunity.
Unstable low barrier magnets (LBM) could be used to implement useful functions like
random number generation (RNG) by sensing the randomly fluctuating magnetization to
provide a random time varying voltage. With such applications in mind, we would want
magnets to have as low a barrier as possible, so that many random numbers are
generated in a given amount of time. Indeed a "zero" barrier magnet with
$E_b \leq k_B T$ flipping back and forth in less than a nanosecond would be ideal.

How can we reduce the energy barrier? Since $E_b = H_K M_s \Omega / 2$, the basic
approach is to reduce the total magnetic moment by reducing volume $\Omega$, and/or
engineer a small anisotropy field $H_K$. This can be done with perpendicular magnets
(PMA) designed to be close to the in-plane transition. A less challenging approach
seems to be to use circular in-plane magnets (IMA). We will refer to all these
possibilities collectively as LBM's as opposed to say superparamagnets which have
more specific connotations in different contexts.

We could use LBM's to represent the probabilistic bits or p-bits that we alluded to.
We have argued that if these p-bits can be incorporated into proper transistor-like
structures with gain, then the resulting three-terminal p-bits could be
interconnected to build p-circuits that perform useful functions, not unlike the way
transistors are interconnected to build useful digital circuits. However, unlike
digital circuits these probabilistic p-circuits incorporate features reminiscent of
quantum circuits.

This connection was nicely articulated by Feynman in a seminal paper, where he
described a quantum computer that could provide an efficient simulation of quantum
many-body problems. But to set the stage for quantum computers, he first described a
probabilistic p-computer which could efficiently simulate classical many-body
problems:

> ... "the other way to simulate a probabilistic nature, which I'll call N ... is by
> a computer C which itself is probabilistic, ... in which the output is not a unique
> function of the input ... it simulates nature in this sense: that C goes from some
> ... initial state ... to some final state with the same probability that N goes
> from the corresponding initial state to the corresponding final state ... If you
> repeat the same experiment in the computer a large number of times ... it will give
> the frequency of a given final state proportional to the number of times, with
> approximately the same rate ... as it happens in nature."

There are many practical problems of great interest which involve large networks of
probabilistic quantities. These problems should be simulated efficiently by
p-computers of the type envisioned by Feynman. Our purpose here is to discuss
appropriate hardware building blocks that can be used to build them and possible
applications they could be used for. In this context, let us note that although
spins provide a nice unifying paradigm for illustrating the transition from bits to
p-bits and q-bits, the physical realization of a p-bit need not involve spins or
spintronics; non-spintronic implementations can be just as feasible.

> **FIG. 1. Between a bit and a q-bit: The p-bit.** Digital computers use
> deterministic strings of 0's and 1's called bits to represent information in a
> binary code. The emerging field of quantum computing is based on q-bits
> representing a delicate superposition of 0 and 1 that typically requires cryogenic
> temperatures. We envision a class of probabilistic computers or p-computers
> operating robustly at room temperature with existing technology based on p-bits
> which are classical entities fluctuating rapidly between 0 and 1. Although spins
> provide a nice unifying paradigm for illustrating the transition from bits to
> p-bits and q-bits, it should be noted that the physical realization of a p-bit need
> not involve spins or spintronics; non-spintronic implementations can be just as
> feasible.

### B. Binary stochastic neuron (BSN)

Interestingly the concept of a p-bit connects naturally to another concept
well-known in the field of machine learning, namely that of a binary stochastic
neuron (BSN) whose response $m_i$ to an input $I_i$ can be described mathematically
by

$$m_i = \mathrm{sgn}[\tanh I_i - r] \tag{1}$$

where $r$ is a random number uniformly distributed between $-1$ and $+1$. Here we
are using bipolar variables $m_i = \pm 1$ to represent the 0 and 1 states. If we use
binary variables $m_i = 0, 1$ the corresponding equation would look different. When
combined with a synaptic function described by

$$I_i = \sum_j W_{ij} m_j \tag{2}$$

we have a probabilistic network that can be designed to perform a wide variety of
functions through a proper choice of the weights, $W_{ij}$. A separate bias term
$h_i$ is often included in Eq. 2 but we will not write it explicitly, assuming that
it is included as the weighted input from an extra p-bit that is always $+1$.

Eqs. 1 and 2 are widely used in many modern algorithms but they are commonly
implemented in software. Much work has gone into developing suitable hardware
accelerators for matrix multiplication of the type described by Eq. 2 (See for
example, Ref. 22). Three-terminal p-bits would provide a hardware accelerator for
Eq. 1. Together they would function like a probabilistic computer.

Note that a hardware accelerator for Eq. (1) requires more than just an RNG. We need
a tunable RNG whose output $m_i$ can be biased through the input terminal $I_i$ as
shown in Fig. 2. Two distinct designs for a three-terminal p-bit have been described,
both of which use a magnetic tunnel junction (MTJ), a popular "spintronic" device
used in magnetic random access memory (MRAM). However, MRAM applications use stable
MTJ's that can store information for many years, while a p-bit makes use of "bad"
MTJ's with low barriers.

The LBM-based implementation of the BSN described here is conceptually very different
from a clocked approach using stable magnets where a stochastic output is obtained
every time a clock pulse is applied. All of these approaches work with stable
magnets, although LBM's could be used to reduce the switching power that is needed.

In this paper we will focus on unclocked, asynchronous operation using LBM-based
hardware accelerators for the BSN (Eq. (1)). But can an asynchronous circuit provide
the sequential updating of the BSN's described by Eq. (1) that is required for Gibbs
sampling and is commonly enforced in software through a for loop? The answer is "yes"
as shown both in SPICE simulations as well as arduino-based emulations, provided the
synaptic function in Eq. (2) has a delay that is less than or comparable to the
response time of the BSN, Eq. (1).

It should be noted that unclocked operation is a rarity in the digital world and most
applications will probably use a clocked, sequential approach with dedicated
sequencers that update connected p-bits sequentially. A fully digital implementation
of p-circuits using such dedicated sequencers has been realized in Ref. 32.
Synchronous operation can be particularly useful if synaptic delays are large enough
to interfere with natural asynchronous operation.

Here, we focus on unclocked operation in order to bring out the role of a p-bit in
providing a conceptual bridge between two very active fields of research, namely
stochastic machine learning and quantum computing. On the one hand p-bits could
provide a hardware accelerator for the BSN (Eq. (1)) thereby enabling applications
inspired by machine learning (Section III). On the other hand, p-bits are the
classical analogs of q-bits: robust room temperature entities accessible with
current technology that could enable at least some of the applications inspired by
quantum computing (Section IV). But before we discuss applications, let us briefly
discuss possible hardware approaches to implementing p-bits (Section II).

## II. Hardware Implementation

### A. Three-terminal p-Bit

RNG's represent an important component of modern electronics and have been
implemented using many different approaches, including Johnson-Nyquist noise of
resistors, phase noise of ring oscillators, process variations of SRAM cells and
other physical mechanisms. However, as noted earlier, we need what appears to be a
completely new 3-terminal device whose input $I_i$ biases its stochastic output
$m_i$ as shown in Fig. 2c.

> **FIG. 2. Three terminal p-bit.** (a) A hardware implementation of the BSN
> (Eq. (1)) requires a central stochastic element with input and output terminals
> that provide the ability to read and bias the element. (b) The stochastic element
> can be visualized as going back and forth between two low energy states at a rate
> that depends exponentially on the barrier $E_b$ that separates them:
> $\tau = \tau_0 \exp(\Delta / k_B T)$. (c) The bias terminal adjusts the relative
> energies of the two states thereby controlling the probabilities of finding the
> element in the two states.

A recent paper shows that such a 3-terminal tunable RNG can be built simply by
combining a 2-terminal fluctuating resistance with a transistor (Fig. 3). This seems
very attractive at least in the short run, since the basic structure (Fig. 3a)
closely resembles the 1T/MTJ structure commonly used for MRAM applications. The first
modification that is required is to replace the stable free layer of the MTJ with an
LBM. The second modification is to add an inverter to the drain output that amplifies
the fluctuations caused by the MTJ resistance.

An MTJ is a device with two magnetic contacts whose electrical resistance
$R_{MTJ}$ takes on one of two values $R_P$ and $R_{AP}$ depending on whether the
magnets are parallel (P) or antiparallel (AP). MTJs are typically used as memory
devices, though in recent years applications of MTJs for logic and novel types of
computation have been discussed.

Standard MTJ devices go to great lengths to ensure that the magnets they use are
stable and can store information for many years. The resistance of bad MTJ's, on the
other hand, constantly fluctuates between $R_P$ and $R_{AP}$. If we put it in series
with a transistor which is a voltage controlled resistance $R_T(V_{in})$ then the
voltage $V_m$ (Fig. 3) can be written as

$$V_m = \frac{V_{DD}}{2}\, \frac{R_T(V_{in}) - R_{MTJ}}{R_T(V_{in}) + R_{MTJ}}$$

> **FIG. 3. Embedded MRAM p-bit.** (a) An NMOS pull-down transistor in series with a
> stochastic-MTJ whose resistance fluctuates between $R_P$ and $R_{AP}$ as shown in
> (b). (c) Using a 14 nm HP-FinFET model the input voltage $V_{in}$ versus mid-point
> $V_m$ and output $V_{out}$ voltages is simulated in SPICE. Several fixed resistances
> are shown to convey how $V_m$ would vary with modifications to the parallel and
> antiparallel resistances.

The magnitude of this fluctuating voltage $V_m$ is largest when the transistor
resistance $R_T \sim R_P$ or $R_{AP}$ but gets suppressed if $R_T \gg R_P$ or if
$R_T \ll R_{AP}$. The input voltage controls $R_T$ thereby tuning the stochastic
output $V_m$ as shown in Fig. 3c. It was shown that an additional inverter provides
an output that is approximately described by an expression that looks just like the
BSN (Eq. 1)

$$\underbrace{\frac{V_{out,i}}{V_{DD}/2}}_{m_i} \approx \mathrm{sgn}\left[\tanh \underbrace{\frac{V_{in,i}}{V_0}}_{I_i} - r\right] \tag{3}$$

but with dimensionless variables like $m_i$ and $I_i$ replaced by scaled circuit
voltages $V_{out}$ and $V_{in}$.

The scheme in Fig. 3 provides tunability through the series transistor and does not
involve the physics of the fluctuating resistor. Ideally, the magnet is unaffected by
the change in the transistor resistance though the drain current, in principle, could
pin the magnet. In our simulations that are based on Ref. 13, we take the pinning
current into account through a spin-polarized current ($I_s$) proportional to an
effective fixed layer polarization and the drain current ($I_D$),
$I_s = (P) I_D \hat{x}$, where $\hat{x}$ is the fixed layer direction. This
spin-current enters the sLLG equation that calculates an instantaneous magnetization
which in turn controls the MTJ resistance.

We note that any significant pinning around zero input voltage $V_{in,i}$ has to be
minimized through proper design, especially for low barrier perpendicular magnets
which are relatively easy to pin. Unintentional pinning should in general not be an
issue for circular in-plane LBM's due to the strong demagnetizing field. The pinning
behavior for the average (steady-state) magnetization can be qualitatively understood
by numerical simulations of the sLLG equation. In the case of low-barrier
perpendicular magnets the spin-torque pinning needs to overcome the thermal noise and
therefore the pinning current is of order $I_{PMA} \approx 2(q/\hbar)\alpha k T$ where
$\alpha$ is the damping coefficient of the magnet. In the case of circular in-plane
magnets, the pinning current is of order
$I_{IMA} \approx 2(q/\hbar)\alpha H_D M_s \mathrm{Vol.}$, which is much larger than
$I_{PMA}$ since for typical parameters ($H_D M_s \mathrm{Vol.} \gg kT$).

Since the state of the magnet is not affected, if the input voltage $V_{in,i}$ in
Eq. 3 is changed at $t=0$, the statistics of the output voltage $V_{out,i}$ will
respond within tens of picoseconds (typical transistor switching speeds) irrespective
of the fluctuation rates of the magnet. However, the magnet fluctuations will
determine the correlation time of the random number $r$ in Eq. 3.

Alternatively one can envision structures where the input controls the statistics of
the fluctuating resistor itself, through phenomena such as the spin-Hall effect or
the magneto-electric effect based on a voltage control of magnetism (see for
example). In that case, both the speed of response and the correlation time of the
random number $r$ will be determined by the specific phenomenon involved.

**Non-spintronic implementations:** Note that the structure in Fig. 3 could use any
fluctuating resistor including CMOS-based units in place of the MTJ showing that the
physical realization of a p-bit need not involve spins. For example, a linear
feedback shift register (LFSR) is often used to generate a pseudo-randomly
fluctuating bit stream. We can apply this fluctuating voltage to the gate of a
transistor to obtain a fluctuating resistor which can replace the MTJ in Fig. 3a. We
note that the main appeal of the structure in Fig. 3 lies in its simplicity, since a
1T/1MTJ design coupled with two more transistors provide the tunable randomness in a
compact transistor-like building block. Using completely digital p-circuit
implementations could offer short term scalability and reliability but they would
consume a much larger area and power per p-bit.

### B. Weighted p-bit

The structure in Fig. 3 gives us a "neuron" that implements Eq. 1 in hardware. Such
neurons have to be used in conjunction with a "synapse" that implements Eq. 2.

> **FIG. 4. Example of a weighted p-bit integrating relevant parts of the synapse
> onto the neurons.** Leveraging floating-gate devices along the lines proposed in
> neuMOS devices, a collection of synapse inputs (from 1 to $n$) can be summed to
> produce the bias voltage $V_{IN,i}$ for a voltage driven p-bit.

Alternatively we could design a "weighted p-bit" that integrates each element of
Eq. 1 with the relevant part of Eq. 2. For example, we could use floating gate
devices along the lines proposed in neuMOS devices as shown in Fig. 4. From charge
conservation we can write

$$\sum_j (V_{out,j} - V_{in,i}) C_{i,j} - V_{in,i} C_0 = 0$$

where $C_0$ is the input capacitance of the transistor. This can be rewritten as

$$V_{in,i} = \sum_j \frac{C_{i,j}}{C_0 + \sum_j C_{i,j}}\, V_{out,j}$$

By scaling $V_{in}$ and $V_{out}$ (see Eq. 3) to play the roles of the dimensionless
quantities $I_i$ and $m_i$ respectively, we can recast Eq. 4 in a form similar to
Eq. 2:

$$\underbrace{\frac{V_{in,i}}{V_0}}_{I_i} = \sum_j \underbrace{\frac{V_{DD}}{2 V_0} \frac{C_{i,j}}{C_0 + \sum_j C_{i,j}}}_{W_{ij}} \underbrace{\frac{V_{out,j}}{V_{DD}/2}}_{m_i} \tag{4}$$

The weights $W_{ij}$ can be adjusted by controlling the specific capacitors $C_{ij}$
that are connected. The range of allowed weights and connections is then limited by
the routing topology and neuMOS device size. Note that the control of weights through
$C_{ij}$ works best if $C_0 \gg \sum_j C_{ij}$ so that $W_{i,j} \approx C_{i,j}/C_0$,
however it is possible to design a weighted p-bit design without this assumption
($C_0 \ll \sum C_{ij}$) as discussed in detail in Ref. 52. Similar control can also
be achieved through a network of resistors. The weights are given by the same
expression, but with capacitances $C_{ij}$ replaced by conductances $G_{ij}$.
However, the input conductance $G_0$ of FET's is typically very low, so that an
external conductance has to be added to make $G_0 \gg \sum_j G_{ij}$.

## III. Applications of p-circuits

As noted earlier, real applications involve p-bits interconnected by a synapse that
can be implemented off-chip either in software or with a hardware matrix multiplier,
but then it is necessary to transfer data back and forth between Eq. 1 and Eq. 2.
Therefore, a low-level compact hardware implementation of a p-bit along with a local
synapse as envisioned in Fig. 4 could be a hardware accelerator for many types of
applications, some of which will be discussed in this section. In the capacitively
weighted p-bit design of Fig. 4, the weights and connectivity of the p-bit could be
dynamically adjusted based on the encoding of a given problem by leveraging a network
of programmable switches as would be encountered in FPGAs. Such a p-bit with local
interconnections would look like a compact nanodevice implementation of highly scaled
digital spiking neurons of neuromorphic chips such as TrueNorth. Alternatively, the
interconnection function could be performed off-chip using standard CMOS devices such
as FPGAs or GPUs while p-bits are implemented in a standalone chip by modifying
embedded MRAM technology. Note however, the off-chip implementation of the
interconnection matrix would impose a timing constraint for an asynchronous mode of
operation, which requires the weighted summation operation (Eq. 2) to operate much
faster than the p-bit operation (Eq. 1) for proper convergence. A full on-chip
implementation of a reconfigurable p-bit could function as a low-power, efficient
hardware accelerator for applications in Machine Learning and Quantum Computing, but
in the near term a heterogenous multi-chip synapse / p-bit combination could also
prove to be useful.

Now that we have discussed some possible approaches to implementing Eqs. 1 and 2 in
hardware, let us present a few illustrative p-bit networks that can implement useful
functions and can be built using existing technology. Unless otherwise stated, these
results are obtained from full SPICE simulations that solve the stochastic
Landau-Lifshitz-Gilbert equation coupled with the PTM-based transistor models in
SPICE to model the embedded MTJ based 3-terminal p-bit described in Fig. 3.

### A. Applications: Machine learning inspired

**Bayesian inference:** A natural application of stochastic circuits is in the
simulation of networks whose nodes are stochastic in nature. An archetypal example is
a genetic network, a small version of which is shown in Fig. 5. A well-known concept
is that of genetic correlation or relatedness between different members of a family
tree. For example, assuming that each of the children $C_1$ and $C_2$ get half their
genes from their parents $F_1$ and $M_1$ we can write their correlation as:

$$\langle C_1 \times C_2 \rangle = \langle (0.5 F_1 + 0.5 M_1) \times (0.5 F_1 + 0.5 M_1) \rangle$$
$$= \tfrac{1}{4}\big(\langle F_1 \times F_1\rangle + \langle F_1 \times M_1\rangle + \langle M_1 \times F_1\rangle + \langle M_1 \times M_1\rangle\big) = \tfrac{1}{4}(1 + 0 + 0 + 1) = 0.5 \tag{5}$$

assuming $F_1$ and $M_1$ are uncorrelated. Hence the well-known result that siblings
have 50% relatedness. Similarly one can work out the relatedness of more distant
relationships like that of an aunt $M_1$ and her nephew $C_3$ which turns out to be
25%.

The point is that we could construct a p-circuit with each of the nodes represented
by a hardware p-bit interconnected to reflect the genetic influences. The correlation
between two nodes, say $C_1$ and $C_2$, is given by

$$\langle C_1 \times C_2 \rangle = \int_0^T \frac{dt}{T}\, C_1(t) C_2(t) \tag{6}$$

If $C_1(t)$ and $C_2(t)$ are binary variables with allowed values of 1 and 0, then
they can be multiplied in hardware with an AND gate. If the allowed values are
bipolar, $-1$ and $+1$, then the multiplication can be implemented with an XNOR gate.
In either case the average over time can be performed with a long time constant RC
circuit. A few typical results from SPICE simulations are shown in Fig. 5. The
numerical results in Fig. 5 are in good agreement with Bayes theorem even though the
circuit operates asynchronously without any sequencers. This is interesting since
software simulations of Eqs. 1 and 2 with directed weights usually require the nodes
to be updated from parent to child. Whether this behavior generalizes to larger
directed networks is left for future work.

We use this genetic circuit as a simple illustration of the concept of nodal
correlations which appear in many other contexts in everyday life. Medical diagnosis,
for example, involves symptoms such as, say high temperature, which can have multiple
origins or parents and one can construct Bayesian networks to determine different
causal relationships of interest.

> **FIG. 5. Genetic circuit.** $C_1$ and $C_2$ are siblings with parents $F_1$,
> $M_1$, while $C_3$ and $C_4$ are siblings with parents $F_2$, $M_2$. Two of the
> parents $M_1$ and $F_2$ are siblings with parents $GF_1$, $GM_1$. Genetic
> correlations between different members can be evaluated from the correlations of
> the nodal voltages in a p-circuit. An XNOR gate finds their product while a long
> time constant RC circuit provides the time average.

**Accelerating learning algorithms:** Networks of p-bits could be useful in
implementing inference networks, where the network weights are trained offline by a
learning algorithm in software and the hardware is used to repeatedly perform
inference tasks efficiently. Another common example where correlations play an
important role is in the learning algorithms used to train modern neural networks
like the restricted Boltzmann machine (Fig. 6) having a visible layer and a hidden
layer, with connecting weights $W_{ij}$ linking nodes of one layer to those in the
other, but not within a layer. A widely used algorithm based on "contrastive
divergence" adjusts each weight $W_{ij}$ according to

$$\Delta W_{ij} \sim \langle v_i h_j \rangle_{t=0} - \langle v_i h_j \rangle_{t \to \infty}$$

which requires the repeated evaluation of the correlations $\langle v_i h_j \rangle$.
Computing such correlations exactly becomes intractable due to their exponential
complexity in the number of neurons, therefore contrastive divergence is often
limited by a fixed number of steps (CDn) to limit the number of repeated evaluation
of these correlations. This process could be accelerated through an efficient
physical representation of the neuron and the synapse.

> **FIG. 6. Restricted Boltzmann Machine (RBM).** RBMs are a special class of
> stochastic neural networks that restrict connections within a hidden and a visible
> layer. Standard learning algorithms require repeated evaluations of correlations of
> the form $\langle v_i h_j \rangle$.

### B. Applications: Quantum inspired

The functionality of neural networks is determined by the weight matrix $W_{ij}$
which determines the connectivity among the neurons. They can be classified broadly
by the relation between $W_{ij}$ and $W_{ji}$. In traditional feedforward networks,
information flow is directed with neuron 'i' influencing neuron 'j' through a non-zero
weight $W_{ij}$ but with no feedback from neuron 'j', such that $W_{ji} = 0$. At the
other end of the spectrum, is a network with all connections being reciprocal
$W_{ij} = W_{ji}$. In between these two extremes are the class of networks for which
the weights between two nodes are asymmetric, but non-zero.

The class of networks with symmetric connections is particularly interesting since
they have a close parallel with classical statistical physics where the natural
connections between interacting particles is symmetric and the equilibrium
probabilities are given by the celebrated Boltzmann law expressing the probability of
a particular configuration $\alpha$ in terms of an energy $E_\alpha$ associated with
that configuration.

$$P_\alpha = \frac{1}{Z} \exp(-E_\alpha) \tag{7}$$

$$E_\alpha = -\{m\}_\alpha^T [W] \{m\}_\alpha \tag{8}$$

where $T$ denotes transpose and the constant $Z$ is chosen to ensure that all
$P_\alpha$ add up to one. This energy principle is only available for reciprocal
networks, and can be very useful in determining the appropriate weights $W_{ij}$ for
a particular problem. This class of networks connects naturally to the world of
quantum computing which is governed by Hermitian Hamiltonians, and is also the
subject of the emerging field of Ising computing.

**Invertible Boolean logic:** Suppose, for example, we wish to design a Boolean gate
which will provide three outputs reflecting the AND, OR and XNOR functions of the two
inputs A and B. The truth table is shown in Fig. 7. Note that although we are using
the binary notation 1 and 0, they actually stand for p-bit values of $+1$ and $-1$
respectively.

Since there are five p-bits, two representing the inputs and three representing the
outputs, the system has $2^5 = 32$ possible states, which can be indexed by their
corresponding decimal values. Each of these configurations has an associated energy,
$E_n$, $n = 0, 1, \dots, 31$. What we need is a weight matrix $W_{ij}$ such that the
desired configurations 4, 9, 17 and 31 (in decimal notation) specified by the truth
table have a low energy $E_\alpha$ (Eq. (8)) compared to the rest, so that they are
occupied with higher probability. This can be done either by using the principles of
linear algebra or by using machine learning algorithms to obtain the weight matrix
shown in Fig. 7. Note that an additional p-bit labeled "h" has been introduced which
is clamped to a value of $+1$ by applying a large bias.

On the right of Fig. 7, a histogram is showing the frequency of all the possible (32)
configurations obtained from a simulation of Eq. (1) and Eq. (2) using this weight
matrix. Similar results are obtained from a SPICE simulation of a p-circuit of
weighted p-bits. Note the peaks at the desired truth table values, with smaller peaks
at some of the undesired values. The peaks closely follow the Boltzmann law, such
that

$$\frac{P_{\text{desired}}}{P_{\text{undesired}}} = \exp\big(E_{\text{undesired}} - E_{\text{desired}}\big)$$

Undesired peaks can be suppressed if we make the W-matrix larger, say by an overall
multiplicative factor of 2. If all energies are increased by a factor of 2, the ratio
of probabilities would be squared: a ratio of 10 would become a ratio of 100.

> **FIG. 7. Invertible Boolean logic.** A multi-function Boolean gate with 6 p-bits
> is shown. Inputs A and B produce the output for a 2-input XNOR, AND and OR gate,
> respectively. The handle bit "h" is used to remove the complementary low-energy
> states that do not belong to the truth table shown. In the unclamped mode, the
> system shows the states corresponding to the lines of the truth table with high
> probability. A and B can be clamped to produce the correct output for the XNOR, AND
> and OR in the direct mode. In the inverse mode, any one of the outputs (XNOR is
> shown as an example) can be clamped to a given value, and the inputs fluctuate among
> possible input combinations corresponding to this output.

It is also possible to operate the gate in a traditional feed-forward manner where
inputs are specified and an output is obtained. This mode is shown in the middle
panel on the right where the inputs A and B are clamped to 1 and 0 respectively. Only
one of the four truth table peaks can be seen, namely the line corresponding to
A=1, B=0, which is labeled 17.

What is more interesting is that the gates can be run in inverse mode as shown in the
lower right panel. The XNOR output is clamped to 0 corresponding to specific lines of
the truth table corresponding to 9 and 17. The inputs now fluctuate between the two
possibilities, indicating that we can use these gates to provide us with all possible
inputs consistent with a specified output, a mode of operation not possible with
standard Boolean gates.

> **FIG. 8. Combinatorial Optimization.** A 5-city Traveling Salesman Problem (TSP)
> implemented using a network of 16 p-bits (fixing city 0), each having two indices,
> the first denoting the order in which a city is visited and the second denoting the
> city. The interaction parameter $I_0$ scales all weights and acts as an inverse
> temperature and is slowly increased via a simple annealing schedule
> $I_0(t + t_{eq}) = (1/0.99) I_0(t)$ to guide the system into the lowest energy
> state, providing the shortest traveling distance (Map imagery data: Google,
> TerraMetrics).

This invertible mode is particularly interesting because there are many cases where
the direct problem is relatively easy compared to the inverse problem. For example,
we can find a suitable weight matrix to implement an adder that provides the sum S of
numbers A, B and C. But the same network also solves the inverse problem where a sum
S is provided and it finds combinations of k numbers that add up to S. This inverse
k-sum or subset sum problem is known to be NP-complete and is clearly much more
difficult than direct addition. Similarly we can design a weight matrix such that the
network multiplies any two numbers. In inverse mode the same network can factorize a
given number, which is a hard problem. This ability to factorize has been shown with
relatively small numbers. How well p-circuits will scale to larger factorization
problems remains to be explored.

It is worth mentioning that this method of solving integer factorization and the
subset sum problem is similar to the deterministic "memcomputing" framework where a
"self-organizing logic circuit" is set up to solve the direct problem and operated in
reverse to solve the inverse problem.

**Optimization by classical annealing:** It has been shown that many optimization
problems can be mapped onto a network of classical spins with an appropriate weight
matrix, such that the optimal solution corresponds to the configuration with the
lowest energy. Indeed, even the problem of integer factorization discussed above in
terms of inverse multiplication can alternatively be addressed in this framework by
casting it as an optimization problem.

A well-known example of an optimization problem is the classic N-city traveling
salesman problem (TSP). It involves finding the shortest route by which a salesman can
visit all cities once starting from a particular one. This problem has been mapped to
a network of $(N-1)^2$ spins where each spin has two indices, the first denoting the
order in which a city is visited and the second denoting the city.

Fig. 8 shows a 5-city TSP mapped to a 16 p-bit network and translated into a
p-circuit that is simulated using SPICE. The overall W-matrix is slowly increased and
with increasing interaction the network gradually settles from a random state into a
low energy state. This process is often called simulated annealing based on the
similarity with the freezing of a liquid into a solid with a lowering of temperature
in the physical world, which reduces the random thermal energy relative to a fixed
interaction.

Note that at high values of interaction the p-bits settle to the correct solution
with four p-bits highlighted corresponding to (1,1), (2,3), (3,2) and (4,4), showing
that the cities should be visited in the order 1-3-2-4. Unfortunately things may not
work quite so smoothly as we scale up to problems with larger numbers of p-bits. The
system tends to get stuck in metastable states just as in the physical world solids
develop defects that keep them from reaching the lowest energy state.

**Optimization by quantum annealing:** An approach that has been explored is the
process of quantum annealing using a network of quantum spins implemented with
superconducting q-bits. However, it is known that for certain classes of quantum
problems classified by "stoquastic" Hamiltonians, a network of q-bits can be
approximated with a larger network of p-bits operating in hardware (Fig. 9). We have
made use of this equivalence to design p-circuits whose SPICE simulations show
correlations and averages comparable to those obtained with quantum annealers.

## IV. Conclusions

In summary, we have introduced the concept of a probabilistic or p-bit, intermediate
between the standard bits of digital electronics and the emerging q-bits of quantum
computing. Low barrier magnets or LBM's provide a natural physical representation for
p-bits and can be built either from perpendicular magnets (PMA) designed to be close
to the in-plane transition or from circular in-plane magnets (IMA). Magnetic tunnel
junctions (MTJ) built using LBM's as free layers can be combined with standard NMOS
transistors to provide three-terminal building blocks for large scale probabilistic
circuits that can be designed to perform useful functions. Interestingly, this
three-terminal unit looks just like the 1T/MTJ device used in embedded MRAM
technology, with only one difference: the use of an LBM for the MTJ free layer. We
hope that this concept will help open up new application spaces for this emerging
technology. However, a p-bit need not involve an MTJ, any fluctuating resistor could
be combined with a transistor to implement it. It may be interesting to look for
resistors that can fluctuate faster based on entities like natural and synthetic
antiferromagnets, for example.

> **FIG. 9. Mapping a q-bit network into a p-bit network.** A special class of
> quantum many body Hamiltonians that are "stoquastic" can be solved by mapping them
> to a classical network of p-bits that consist of a finite number of replicas of the
> original system that are interacting in the "vertical" direction. This approach
> implemented in software is also known as the Path Integral Monte Carlo method. A
> hardware implementation would constitute a p-computer that is capable of performing
> quantum annealing.

The p-bit also provides a conceptual bridge between two active but disjoint fields of
research, namely stochastic machine learning and quantum computing. This viewpoint
suggests two broad classes of applications for p-bit networks. First, there are the
applications that are based on the similarity of a p-bit to the binary stochastic
neuron (BSN), a well-known concept in machine learning. Three-terminal p-bits could
provide an efficient hardware accelerator for the BSN. Second, there are the
applications that are based on the p-bit being like a poor man's q-bit. We are
encouraged by the initial demonstrations based on full SPICE simulations that several
optimization problems including quantum annealing are amenable to p-bit
implementations which can be scaled up at room temperature using existing technology.

## Acknowledgments

S.D. is grateful to Dr. Behtash Behin-Aein for many stimulating discussions leading
up to Ref. 16.

## References

1. E. Chen, D. Apalkov, Z. Diao, A. Driskill-Smith, D. Druist, D. Lottis, V. Nikitin, X. Tang, S. Watts, S. Wang, S. Wolf, A. W. Ghosh, J. Lu, S. J. Poon, M. Stan, W. Butler, S. Gupta, C. K. A. Mewes, T. Mewes, and P. Visscher, "Advances and Future Prospects of Spin-Transfer Torque Random Access Memory," *IEEE Transactions on Magnetics* 46, 1873–1878 (2010).
2. L. Lopez-Diaz, L. Torres, and E. Moro, "Transition from ferromagnetism to superparamagnetism on the nanosecond time scale," *Physical Review B* 65, 224406 (2002).
3. N. Locatelli, A. Mizrahi, A. Accioly, R. Matsumoto, A. Fukushima, H. Kubota, S. Yuasa, V. Cros, L. G. Pereira, D. Querlioz, et al., "Noise-enhanced synchronization of stochastic magnetic oscillators," *Physical Review Applied* 2, 034009 (2014).
4. B. Parks, M. Bapna, J. Igbokwe, H. Almasi, W. Wang, and S. A. Majetich, "Superparamagnetic perpendicular magnetic tunnel junctions for true random number generators," *AIP Advances* 8, 055903 (2018), https://doi.org/10.1063/1.5006422.
5. D. Vodenicarevic, N. Locatelli, A. Mizrahi, J. Friedman, A. Vincent, M. Romera, A. Fukushima, K. Yakushiji, H. Kubota, S. Yuasa, S. Tiwari, J. Grollier, and D. Querlioz, "Low-Energy Truly Random Number Generation with Superparamagnetic Tunnel Junctions for Unconventional Computing," *Physical Review Applied* 8, 054045 (2017).
6. D. Vodenicarevic, N. Locatelli, A. Mizrahi, T. Hirtzlin, J. S. Friedman, J. Grollier, and D. Querlioz, "Circuit-Level Evaluation of the Generation of Truly Random Bits with Superparamagnetic Tunnel Junctions," in *2018 IEEE International Symposium on Circuits and Systems (ISCAS)* (2018) pp. 1–4.
7. P. Debashis, R. Faria, K. Y. Camsari, and Z. Chen, "Designing stochastic nanomagnets for probabilistic spin logic," *IEEE Magnetics Letters* (2018).
8. R. P. Cowburn, D. K. Koltsov, A. O. Adeyeye, M. E. Welland, and D. M. Tricker, "Single-domain circular nanomagnets," *Physical Review Letters* 83, 1042 (1999).
9. P. Debashis, R. Faria, K. Y. Camsari, J. Appenzeller, S. Datta, and Z. Chen, "Experimental demonstration of nanomagnet networks as hardware for Ising computing," in *2016 IEEE International Electron Devices Meeting (IEDM)* (2016) pp. 34.3.1–34.3.4.
10. B. Sutton, K. Y. Camsari, B. Behin-Aein, and S. Datta, "Intrinsic optimization using stochastic nanomagnets," *Scientific Reports* 7, 44370 (2017).
11. R. Faria, K. Y. Camsari, and S. Datta, "Low-barrier nanomagnets as p-bits for spin logic," *IEEE Magnetics Letters* 8, 1–5 (2017).
12. K. Y. Camsari, R. Faria, B. M. Sutton, and S. Datta, "Stochastic p-Bits for Invertible Logic," *Physical Review X* 7, 031014 (2017), https://doi.org/10.1103/PhysRevX.7.031014.
13. K. Y. Camsari, S. Salahuddin, and S. Datta, "Implementing p-bits With Embedded MTJ," *IEEE Electron Device Letters* 38, 1767–1770 (2017).
14. A. Mizrahi, T. Hirtzlin, A. Fukushima, H. Kubota, S. Yuasa, J. Grollier, and D. Querlioz, "Neural-like computing with populations of superparamagnetic basis functions," *Nature Communications* 9, 1533 (2018).
15. M. Bapna and S. A. Majetich, "Current control of time-averaged magnetization in superparamagnetic tunnel junctions," *Applied Physics Letters* 111, 243107 (2017).
16. B. Behin-Aein, V. Diep, and S. Datta, "A building block for hardware belief networks," *Scientific Reports* 6, 29893 (2016).
17. R. P. Feynman, "Simulating physics with computers," *International Journal of Theoretical Physics* 21, 467–488 (1982).
18. D. H. Ackley, G. E. Hinton, and T. J. Sejnowski, "A Learning Algorithm for Boltzmann Machines," *Cognitive Science* 9, 147–169 (1985).
19. R. M. Neal, "Connectionist learning of belief networks," *Artificial Intelligence* 56, 71–113 (1992).
20. Eq. 1 can be equivalently written as $m_i = \mathrm{sgn}[\tanh I_i + r]$.
21. The signum function (sgn) would be replaced by the step function ($\Theta$) and the tanh function would be replaced by the sigmoid function ($\sigma$) such that $m_i = \Theta[\sigma(2 I_i) - r_0]$ where the random number $r_0$ is uniformly distributed between 0 and 1.
22. M. Hu, J. P. Strachan, Z. Li, E. M. Grafals, N. Davila, C. Graves, S. Lam, N. Ge, J. J. Yang, and R. S. Williams, "Dot-product engine for neuromorphic computing: programming 1t1m crossbar to accelerate matrix-vector multiplication," in *Proceedings of the 53rd Annual Design Automation Conference* (ACM, 2016) p. 19.
23. S. Bhatti, R. Sbiaa, A. Hirohata, H. Ohno, S. Fukami, and S. Piramanayagam, "Spintronics based random access memory: A review," *Materials Today* (2017).
24. B. Behin-Aein, A. Sarkar, and S. Datta, "Modeling circuits with spins and magnets for all-spin logic," in *Solid-State Device Research Conference (ESSDERC), 2012 Proceedings of the European* (IEEE, 2012) pp. 36–40.
25. B. Behin-Aein, "Computing multi-magnet based devices and methods for solution of optimization problems," (2014), US Patent 8,698,517.
26. W. H. Choi, Y. Lv, J. Kim, A. Deshpande, G. Kang, J.-P. Wang, and C. H. Kim, "A magnetic tunnel junction based true random number generator with conditional perturb and real-time output probability tracking," in *Electron Devices Meeting (IEDM), 2014 IEEE International* (IEEE, 2014) pp. 12–5.
27. A. Fukushima, T. Seki, K. Yakushiji, H. Kubota, H. Imamura, S. Yuasa, and K. Ando, "Spin dice: A scalable truly random number generator based on spintronics," *Applied Physics Express* 7, 083001 (2014).
28. A. F. Vincent, J. Larroque, N. Locatelli, N. B. Romdhane, O. Bichler, C. Gamrat, W. S. Zhao, J. Klein, S. Galdin-Retailleau, and D. Querlioz, "Spin-transfer torque magnetic memory as a stochastic memristive synapse for neuromorphic systems," *IEEE Transactions on Biomedical Circuits and Systems* 9, 166–174 (2015).
29. A. Sengupta, M. Parsa, B. Han, and K. Roy, "Probabilistic deep spiking neural systems enabled by magnetic tunnel junction," *IEEE Transactions on Electron Devices* 63, 2963–2970 (2016).
30. Y. Lv and J.-P. Wang, "A single magnetic-tunnel-junction stochastic computing unit," in *Electron Devices Meeting (IEDM), 2017 IEEE International* (IEEE, 2017) pp. 36–2.
31. S. Geman and D. Geman, "Stochastic relaxation, Gibbs distributions, and the Bayesian restoration of images," *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 721–741 (1984).
32. A. Z. Pervaiz, B. M. Sutton, L. A. Ghantasala, and K. Y. Camsari, "Weighted p-bits for FPGA implementation of probabilistic circuits," *IEEE Transactions on Neural Networks and Learning Systems* (2018).
33. S. Cheemalavagu, P. Korkmaz, K. V. Palem, B. E. S. Akgul, and L. N. Chakrapani, "A probabilistic CMOS switch and its realization by exploiting noise," in *the Proceedings of the IFIP International* (2005).
34. M. Bucci, L. Germani, R. Luzzi, A. Trifiletti, and M. Varanonuovo, "A high-speed oscillator-based truly random number source for cryptographic applications on a smart card IC," *IEEE Transactions on Computers* 52, 403–409 (2003).
35. D. E. Holcomb, W. P. Burleson, and K. Fu, "Power-Up SRAM State as an Identifying Fingerprint and Source of True Random Numbers," *IEEE Transactions on Computers* 58, 1198–1210 (2009).
36. J. Wang, H. Meng, and J.-P. Wang, "Programmable spintronics logic device based on a magnetic tunnel junction element," *Journal of Applied Physics* 97, 10D509 (2005).
37. S. Matsunaga, J. Hayakawa, S. Ikeda, K. Miura, H. Hasegawa, T. Endoh, H. Ohno, and T. Hanyu, "Fabrication of a nonvolatile full adder based on logic-in-memory architecture using magnetic tunnel junctions," *Applied Physics Express* 1, 091301 (2008).
38. H. Ohno, T. Endoh, T. Hanyu, N. Kasai, and S. Ikeda, "Magnetic tunnel junction for nonvolatile CMOS logic," in *Electron Devices Meeting (IEDM), 2010 IEEE International* (IEEE, 2010) pp. 9–4.
39. A. Lyle, S. Patil, J. Harms, B. Glass, X. Yao, D. Lilja, and J.-P. Wang, "Magnetic tunnel junction logic architecture for realization of simultaneous computation and communication," *IEEE Transactions on Magnetics* 47, 2970–2973 (2011).
40. X. Yao, J. Harms, A. Lyle, F. Ebrahimi, Y. Zhang, and J.-P. Wang, "Magnetic tunnel junction-based spintronic logic units operated by spin transfer torque," *IEEE Transactions on Nanotechnology* 11, 120–126 (2012).
41. J. Grollier, D. Querlioz, and M. D. Stiles, "Spintronic nanodevices for bioinspired computing," *Proceedings of the IEEE* 104, 2024–2039 (2016).
42. N. Locatelli, V. Cros, and J. Grollier, "Spin-torque building blocks," *Nature Materials* 13, 11 (2014).
43. Y. Cao, T. Sato, D. Sylvester, M. Orshansky, and C. Hu, "Predictive technology model," Internet: http://ptm.asu.edu (2002).
44. C. M. Liyanagedera, A. Sengupta, A. Jaiswal, and K. Roy, "Stochastic spiking neural networks enabled by magnetic tunnel junctions: From nontelegraphic to telegraphic switching regimes," *Physical Review Applied* 8, 064017 (2017).
45. D. E. Nikonov and I. A. Young, "Benchmarking of beyond-CMOS exploratory devices for logic integrated circuits," *IEEE Journal on Exploratory Solid-State Computational Devices and Circuits* 1, 3–11 (2015).
46. K. Y. Camsari, R. Faria, O. Hassan, B. M. Sutton, and S. Datta, "Equivalent circuit for magnetoelectric read and write operations," *Phys. Rev. Applied* 9, 044020 (2018).
47. A. K. Biswas, H. Ahmad, J. Atulasimha, and S. Bandyopadhyay, "Experimental demonstration of complete 180° reversal of magnetization in isolated Co nanomagnets on a PMN–PT substrate with voltage generated strain," *Nano Letters* 17, 3478–3484 (2017).
48. S. Manipatruni, D. E. Nikonov, and I. A. Young, "Beyond CMOS computing with spin and polarization," *Nature Physics* 14, 338 (2018).
49. M. Jerry, A. Parihar, A. Raychowdhury, and S. Datta, "A random number generator based on insulator-to-metal electronic phase transitions," in *Device Research Conference (DRC), 2017 75th Annual* (IEEE, 2017) pp. 1–2.
50. T. G. Lewis and W. H. Payne, "Generalized Feedback Shift Register Pseudorandom Number Algorithm," *J. ACM* 20, 456–468 (1973).
51. T. Shibata and T. Ohmi, "A functional MOS transistor featuring gate-level weighted sum and threshold operations," *IEEE Transactions on Electron Devices* 39, 1444–1455 (1992).
52. O. Hassan, K. Y. Camsari, and S. Datta, "Voltage-driven Building Block for Hardware Belief Networks," arXiv:1801.09026 [cs] (2018).
53. G. Lemieux and D. Lewis, *Design of Interconnection Networks for Programmable Logic* (Springer US, Boston, MA, 2004).
54. P. A. Merolla, J. V. Arthur, R. Alvarez-Icaza, A. S. Cassidy, J. Sawada, F. Akopyan, B. L. Jackson, N. Imam, C. Guo, Y. Nakamura, et al., "A million spiking-neuron integrated circuit with a scalable communication network and interface," *Science* 345, 668–673 (2014).
55. A. Z. Pervaiz, L. A. Ghantasala, K. Y. Camsari, and S. Datta, "Hardware emulation of stochastic p-bits for invertible logic," *Scientific Reports* 7, 10994 (2017).
56. K. Y. Camsari, S. Ganguly, and S. Datta, "Modular approach to spintronics," *Scientific Reports* 5, 10571 (2015).
57. L. N. Chakrapani, P. Korkmaz, B. E. Akgul, and K. V. Palem, "Probabilistic system-on-a-chip architectures," *ACM Transactions on Design Automation of Electronic Systems (TODAES)* 12, 29 (2007).
58. D. Querlioz, O. Bichler, A. F. Vincent, and C. Gamrat, "Bioinspired programming of memory devices for implementing an inference engine," *Proceedings of the IEEE* 103, 1398–1416 (2015).
59. Y. Shim, S. Chen, A. Sengupta, and K. Roy, "Stochastic spin-orbit torque devices as elements for bayesian inference," *Scientific Reports* 7, 14101 (2017).
60. W. Tylman, T. Waszyrowski, A. Napieralski, M. Kamiński, T. Trafidlo, Z. Kulesza, R. Kotas, P. Marciniak, R. Tomala, and M. Wenerski, "Real-time prediction of acute cardiovascular events using hardware-implemented bayesian networks," *Computers in Biology and Medicine* 69, 245–253 (2016).
61. A. Ardakani, F. Leduc-Primeau, N. Onizawa, T. Hanyu, and W. J. Gross, "VLSI implementation of deep neural network using integral stochastic computing," *IEEE Transactions on Very Large Scale Integration (VLSI) Systems* 25, 2688–2699 (2017).
62. R. Zand, K. Y. Camsari, S. D. Pyle, I. Ahmed, C. H. Kim, and R. F. DeMara, "Low-energy deep belief networks using intrinsic sigmoidal spintronic-based probabilistic neurons," in *Proceedings of the 2018 on Great Lakes Symposium on VLSI* (ACM, 2018) pp. 15–20.
63. R. Salakhutdinov, A. Mnih, and G. Hinton, "Restricted boltzmann machines for collaborative filtering," in *Proceedings of the 24th International Conference on Machine Learning* (ACM, 2007) pp. 791–798.
64. G. E. Hinton, "Training products of experts by minimizing contrastive divergence," *Neural Computation* 14, 1771–1800 (2002).
65. M. N. Bojnordi and E. Ipek, "Memristive Boltzmann machine: A hardware accelerator for combinatorial optimization and deep learning," in *High Performance Computer Architecture (HPCA), 2016 IEEE International Symposium on* (IEEE, 2016) pp. 1–13.
66. R. Faria, J. Kaiser, O. Hassan, K. Y. Camsari, and S. Datta, "Accelerating machine learning using stochastic embedded MTJ," (2018), unpublished.
67. D. J. Amit, *Modeling Brain Function: The World of Attractor Neural Networks* (Cambridge University Press, 1992).
68. M. Yamaoka, C. Yoshimura, M. Hayashi, T. Okuyama, H. Aoki, and H. Mizuno, "A 20k-spin Ising chip to solve combinatorial optimization problems with CMOS annealing," *IEEE Journal of Solid-State Circuits* 51, 303–309 (2016).
69. P. L. McMahon, A. Marandi, Y. Haribara, R. Hamerly, C. Langrock, S. Tamate, T. Inagaki, H. Takesue, S. Utsunomiya, K. Aihara, et al., "A fully programmable 100-spin coherent Ising machine with all-to-all connections," *Science* 354, 614–617 (2016).
70. Y. Shim, A. Jaiswal, and K. Roy, "Ising computation based combinatorial optimization using spin-Hall effect (SHE) induced stochastic magnetization reversal," *Journal of Applied Physics* 121, 193902 (2017).
71. T. Wang and J. Roychowdhury, "Oscillator-based Ising machine," arXiv preprint arXiv:1709.08102 (2017).
72. T. Van Vaerenbergh, R. Bose, D. Kielpinski, G. J. Mendoza, J. S. Pelc, N. A. Tezak, C. Santori, and R. G. Beausoleil, "How coherent Ising machines push circuit design in silicon photonics to its limits (conference presentation)," in *Silicon Photonics XIII*, Vol. 10537 (International Society for Optics and Photonics, 2018) p. 105370D.
73. D. H. Ackley, G. E. Hinton, and T. J. Sejnowski, "A learning algorithm for Boltzmann machines," *Cognitive Science* 9, 147–169 (1985).
74. K. G. Murty and S. N. Kabadi, "Some NP-complete problems in quadratic and nonlinear programming," *Mathematical Programming* 39, 117–129 (1987).
75. P. W. Shor, "Polynomial-time algorithms for prime factorization and discrete logarithms on a quantum computer," *SIAM Review* 41, 303–332 (1999).
76. F. L. Traversa and M. Di Ventra, "Polynomial-time solution of prime factorization and NP-complete problems with digital memcomputing machines," *Chaos: An Interdisciplinary Journal of Nonlinear Science* 27, 023107 (2017).
77. M. Di Ventra and F. L. Traversa, "Perspective: Memcomputing: Leveraging memory and physics to compute efficiently," *Journal of Applied Physics* 123, 180901 (2018), https://doi.org/10.1063/1.5026506.
78. A. Lucas, "Ising formulations of many NP problems," *Frontiers in Physics* 2, 5 (2014).
79. X. Peng, Z. Liao, N. Xu, G. Qin, X. Zhou, D. Suter, and J. Du, "Quantum adiabatic algorithm for factorization and its experimental implementation," *Physical Review Letters* 101, 220405 (2008).
80. P. Henelius and S. Girvin, "A statistical mechanics approach to the factorization problem," arXiv:1102.1296 [cond-mat] (2011).
81. S. Jiang, K. A. Britt, T. S. Humble, and S. Kais, "Quantum annealing for prime factorization," arXiv preprint arXiv:1804.02733 (2018).
82. S. Kirkpatrick, C. D. Gelatt, and M. P. Vecchi, "Optimization by simulated annealing," *Science* 220, 671–680 (1983).
83. J. Mooij, T. Orlando, L. Levitov, L. Tian, C. H. Van der Wal, and S. Lloyd, "Josephson persistent-current qubit," *Science* 285, 1036–1039 (1999).
84. M. W. Johnson, M. H. Amin, S. Gildert, T. Lanting, F. Hamze, N. Dickson, R. Harris, A. J. Berkley, J. Johansson, P. Bunyk, et al., "Quantum annealing with manufactured spins," *Nature* 473, 194 (2011).
85. T. Albash and D. A. Lidar, "Adiabatic quantum computation," *Rev. Mod. Phys.* 90, 015002 (2018).
86. K. Y. Camsari, S. Chowdhury, and S. Datta, "Scaled quantum circuits emulated with room temperature p-bits," arXiv preprint arXiv:1810.07144 (2018).
87. K. Y. Camsari, A. Z. Pervaiz, R. Faria, E. E. Marinero, and S. Datta, "Ultrafast spin-transfer-torque switching of synthetic ferrimagnets," *IEEE Magnetics Letters* 7, 1–5 (2016).
88. U. Atxitia, T. Birk, S. Selzer, and U. Nowak, "Superparamagnetic limit of antiferromagnetic nanoparticles," arXiv preprint arXiv:1808.07665 (2018).
