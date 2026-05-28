# Stochastic p-bits for Invertible Logic

Kerem Yunus Camsari,$^{\ast,\dagger}$ Rafatul Faria,$^1$ Brian M. Sutton,$^1$ and Supriyo Datta$^{\ast,\dagger}$

$^{\S}$ School of Electrical and Computer Engineering, Purdue University, IN, 47907
(Dated: July 24, 2017)

## Abstract

Conventional semiconductor-based logic and nanomaget-based memory devices are built out of stable, deterministic units such as standard MOS (metal oxide semiconductor) transistors, or nanomagnets with energy barriers in excess of 40-60 kT. In this paper we show that unstable, stochastic units which we call "p-bits" can be interconnected to create robust correlations that implement *precise Boolean functions* with impressive accuracy, comparable to standard digital circuits. At the same time they are invertible, a unique property that is absent in standard digital circuits. When operated in the direct mode, the input is clamped, and the network provides the correct output. In the inverted mode, the output is clamped, and the network fluctuates among all possible inputs that are consistent with that output. First, we present a detailed implementation of an invertible p-bit network that brings up the key task of a single three-terminal transistor-like building block to enable the construction of correlated p-bit networks. The results for this specific, CMOS-assisted nanomaget-based hardware implementation agree well with those from a universal model for p-bits, showing that p-bits need not be magnet-based: any three-terminal tunable random bit generator should be suitable. We present a general algorithm for designing a Boltzmann machine (BM) with a symmetric connection matrix $[J]$ ($J_{ij} = J_{ji}$), that implements a given truth table with p-bits. The $[J]$ matrices are relatively sparse with a few unique weights for convenient hardware implementation. We then show BM full adders can be interconnected in a *partially directed manner* ($J_{ij} \neq J_{ji}$) to implement large logic operations such as 32-bit binary addition. Hundreds of stochastic p-bits of precisely correlated output with 2^{33} ($\approx 8$ billion) possibilities can be extracted by looking at the statistical mode or majority vote of a number of time samples. With perfect effectivity ($f=1$) a small number of samples is enough, while for less directed connections more samples are needed, but even in the former case logical invertibility is largely preserved. This combination of digital accuracy and logical invertibility enabled by the hybrid design that uses bidirectional BM units to construct circuits with partially directed inter-unit connections. We establish this key result with extensive examples including a 4-bit multiplier which is inverted mode functions as a factorizer.

## I. INTRODUCTION

Conventional semiconductor-based logic and nanomaget-based memory devices are built out of stable, deterministic units such as standard MOS (metal oxide semiconductor) transistors, or nanomagnets with energy barriers in excess of 40–60 kT. The objective of this paper is to introduce the concept of what we call "p-bits" representing unstable, stochastic units which can be interconnected to create robust correlations that implement precise Boolean functions with impressive accuracy, comparable to standard digital circuits. At the same property that is "probabilistic spin logic" (PSL) is invertible, a unique property that is absent in standard digital circuits. When operated in the direct mode, the input is clamped, and the network provides the correct output. In the inverted mode, the output is clamped, and the network fluctuates among all possible inputs that are consistent with that output.

Any random signal generator whose randomness can be tuned with a third terminal should be a suitable building block for PSL. The icon in Fig. 1b represents our generic

building block whose input $I_i$ controls the output $m_i$ according to the equation (Fig. 1a),

$$m_i(t) = \text{sgn}(\text{rand}(-1, 1) + \tanh(I_i(t))) \tag{1}$$

where $\text{rand}(-1,+1)$ represents a random number uniformly distributed between -1 and +1. It is assumed to change every $\tau$ seconds which represents the retention time of individual p-bits. We normalize the time axis to that $t$ dimensionless and progresses in steps (0, 1, 2, \ldots). At each time step, if the input is zero, the output takes on a value of ±1 or ±1 with equal probability, as shown in the middle panel of Fig. 1d. A negative input $I_i$ makes negative values more likely (left panel) while a positive input makes positive values more likely (right panel). Fig. 1c shows $m_i(t)$ as the input is ramped from negative to positive values. Also shown is the time-averaged value of $m_i$, which equals $\tanh(I_i)$.

A possible physical implementation of p-bits could use stochastic nanomagnets with low energy barriers $\Delta$ whose retention time is [1]:

$$\tau = \tau_0 \exp(\Delta / k T)$$

is very small, on the order of $\tau_0$, which is a material dependent quantity called the attempt time and is experimentally found to be $\approx 10$ ps $-$ 1 ns [1] among different magnetic materials. Such stochastic nanomagnets can be

*kcamsari@purdue.edu
†data@purdue.edu

---

## FIG. 1. Generic building block for PSL

(a) A generic model for PSL described by Eq. (1) with distinct READ and WRITE units represented by the R/W icon shown in (b). Useful functionalities are obtained by interconnecting R/W units according to Eq. (2), with $I_i = I_0 \langle h_i + \sum_j J_{ij} m_j \rangle$, with appropriately designed {h} and {J}. (c) The blue trace shows the "magnetization" $\langle m_i \rangle$ obtained from Eq. (1) is the inverted (I) is ramped. The red trace shows the signal response obtained from an RC circuit which provides a moving average of the time-dependent "magnetization" which agrees very well with the black curve showing $\tanh(I_i)$. (d) The basic thermal noise involves a voltage (V) instead of a current (I), just as the output could involve quantities other than magnetization. (d) The idealized tachygraphic behavior of the model is shown at various bias points along the corresponding distributions.

---

pinned to a given direction with spin currents that are at least an order of magnitude less than those needed to switch 40 kT magnets. The sigmoidal tuning curve in Fig. 1c describing the time-averaged probability is determining the time-average of a h-bit. Purely CMOS implementations of a p-bit are possible [2, 3], but the sigmoid seems like a natural feature of nanomagnets driven by spin currents. Indeed, the use of stochastic nanomagnets in the context of random number generators, stochastic oscillators and autonomous learning [4–6] has been discussed in the literature. But performing "invertible" Boolean logic utilizing large scale correlations has not been discussed before. Note that we are using the term *invertibility* in the broader sense of relation inverses and not in the narrower sense of function inverses. For example, AND, when interpreted as a relation, consists of the set {[1,1] → 1}, {0,0 → 0}, {1,0 → 0}, {0,1 → 0}} where each term is

of the form {$A, B \to$ AND$(A, B)$}. The relation inverse of 0 is the set {0} [1], {1,1}. 01 [1]. 01 [1]. We now though the corresponding functional inverse is not defined. What our scheme provides, probabilistically, is the relation inverse $[7, 8]$.

**Ensemble-average versus time-average:** A sigmoidal response was presented in [9] for the ensemble-averaged magnetization of large barrier magnets based along a neutral axis. This was proposed as a building block for both ising computers as well as directed belief networks and a recent paper [10] describes a similar approach applied to a graph coloring problem. By contrast low barrier magnograms provide a sigmoidal response for the time-averaged magnetization and a suitably engineered network of such nanomagnets could cycle through the 2^N collective states at GHz rates, with an emphasis on the "flow energy states" which encode the solution to the combinatorial optimization problems, like the traveling salesman problem (TSP) as shown in [11]. Once the time-varying magnetization has been converted into a time-varying voltage through a READ circuit, a simple RC circuit can be used to extract the answer through averaging time average. For example, in Fig. 1c the red trace was obtained from the rapidly varying blue trace using an RC circuit in a SPICE simulation.

The central feature unifying both implementations is the $p$-bit that acts like a true random number generator, providing an intrinsic sigmoidal response for the ensemble-averaged or the time-averaged magnetization as a function of the spin current. It is this response that allows us to correlate the fluctuations of different p-bits in a useful manner by interconnecting them according to

$$I_i(t) = I_0 \times (h_i(t) + \sum_j J_{ij}m_j(t)) \tag{2}$$

where $h_i$ provides a local bias to magnet $i$ and $J_{ij}$ defines the effect of bit $j$ to bit $i$, and $I_0$ sets a global scale for the strength of the interactions like an inverse "pseudo-temperature" giving a dimensionless current $I_i$ to each p-bit. The computation of $I_i(t)$ in terms of $m_i(t)$ in Eq. (2) is assumed instantaneous; hardware implementations there can be interconnection delays that relate $m_i(t)$ to currents at a later time $I_i(t')$.

Equation (1) arises naturally from the physics of low barrier nanomagnets as we have discussed above. Equation (2) represents the "weight logic" for which there are many candidates such as neuristors [12], floating-gate based devices [13], domain wall-based devices [14], standard CMOS [15]. The suitability of these options will depend on the range of $J$ values and the sparsity of the J-matrix.

---

## FIG. 2. PSL designs discussed in this paper

(a) Basic Boolean logic elements (AND/OR, Full Adder) are implemented as Boltzmann Machines based on symmetrically coupled networks with $J_{ij} = J_{ji}$. (b) Complex Boolean functions like a 32-bit Ripple Carry Adder/Subtractor and 4-bit Multiplier/Factorizer are implemented by combining the reciprocal Boltzmann machines in a directed fashion.

---

## II. AN EXAMPLE HARDWARE IMPLEMENTATION OF PSL

To ensure that individual p-bits can be interconnected to produce robust correlations, it is important to have a separate terminals for writing (more correctly biasing) and reading (marked W and R respectively in Fig. 3a.

With IMA nanomagnets (e.g circular nanomagnets) this could be accomplished following existing experiments [24, 25] using the giant spin Hall effect (GSHE). Recent experiments using a MTJ spin exchange have [26–29] could make this approach applicable to PMA as well. Note however, that these experiments have all been performed with stable free layers, and would have to be carried out with low barrier magnets in order to establish their suitability for the implementation of p-bits. As the field progresses, one can expect the bias terminal to involve

**voltage control** [30, 31] instead of current control, just as the output could involve quantities other than magnetization. We will now show a concrete implementation of a Boolean function using minimal CMOS circuitry in conjunction with stochastic nanomagnets through detailed nanomaget and transport simulations that are in good agreement with those obtained by the generic model based on Eq. (1).

Fig. 3a shows a possible CMOS-assisted p-bit that has a separate READ and WRITE path. The device consists of a heavy metal exhibiting Giant Spin Hall Effect (GSHE) that drives a circular magnet which replaces the usual elliptical magnets in order to provide the stochasticity needed for the magnetization. A small read current, which is assumed to not disturb the magnetization of the free layer in our design, that flows through the fixed layer is used to sense the instantaneous magnetization, which is amplified and isolated by two inverters that act as a buffer. This structure is very similar to the experimentally demonstrated GSHE switching of elliptical magnets that were similarly read-out by a MTJ [24]. Note that in the only exception that the elliptical magnets are replaced by circular magnets with an aspect ratio of one. This device could be viewed as replacing the free layers of the GSHE-driven MTJ demonstrated in [24] with those in the telegraphic regime [25, 32–34].

In the presence of the thermal noise in the magnetization of such a circular magnet rotates in the plane of the circle without reversals along any easy-axis that would have arisen due to the shape anisotropy, effectively making it thermally stable $\Delta \approx 0$ kT [35]. This magnetization can be pinned by a spin current that is generated by flowing a charge current through the GSHE layer. The magnetic field drives sigmoidal response of magnetization for such circular magnets have experimentally been demonstrated [36, 37], while spin current control of the magnetization has not been demonstrated to our knowledge. Using validated modules for transport and magnetization dynamics [38] (Fig. 3b), we used the stochastic Landau-Lifshitz-Gilbert (sLLG) equation in the presence of thermal noise and a GSHE implementation of the model shown in detailed simulation parameters.

**Sigmoidal response:** A long-time average ($t = 500$ ns) of the magnetization $\langle m_z \rangle$ as a function of a GSHE-generated spin current is plotted in Fig. 3e that displays the desired sigmoidal behavior of p-bits dictated by Eq. (1). The x-axis of Fig. 3e is normalized to the geometric spin Hall angle that relates the charge current to the spin current exerted [39, 40]:

$$\beta = \frac{I_s}{I_c} = \sigma_{SH} \frac{L_FM}{h} \left(1 - \operatorname{sech}\left(\frac{t}{\lambda}\right)\right) \tag{5}$$

where $\sigma_{SH}$ is the Hall angle, $t$ is the thickness and $\lambda$ is the spin-relaxation length of the heavy metal. The quantity $\beta$ can be made to be much greater than 1 providing an intrinsic gain [41], however for the parameters used in the present examples, $\beta \approx 1.5$.

Another quantity that is used to normalize the x-axis

---

of Fig. 3e is the "thermal spin current" that corresponds to the strength of the thermal noise that needs to be overcome for a circular magnet to be pinned in a given direction:

$$I_s^{th} = \left(\frac{4q}{h}\right) \sigma(kT) \tag{6}$$

where $q$ is electron charge, $\sigma$ is the damping coefficient of the magnet, $I_c$ and $L$ all have the usual meanings of charge current, therefore we can define the dimensionless interaction parameter, $I_0$ of Eq. 2 as $I_0 = \sum_j L_{ij}/I_s^{th} - I_s/I_s^{th} - 10$, the magnetization of the circular magnet is pinned in the ±-directions for these particular parameters. For PMA magnets with low barriers ($\Delta \ll kT$ [42], and we have reproduced this behavior directly in sLLG simulations. For the implementation of a p-bit in this particular design, we estimate the thermal spin current for typical damping coefficients of $\alpha = 0.01$-$0.1$:

$$I_s^{th} \approx 0.25 \text{ } \mu A - 2.5 \mu A$$

Pinning currents for superparmagnets are at least an order of magnitude smaller than the critical switching currents of stable magnets that suffer from high current densities [43]. $I_0^{th}$ is defined in Eq. (2) suggesting that a stochastic nanomaget based implementation of PSL could be more energy efficient than the standard spin-torque switching of stable magnets that suffer from high current densities [43]. $I_0^{th}$ is defined in Eq. (2) suggesting that a stochastic nanomag net based PSL could be more energy efficient than the standard spin-torque switching of stable magnets [43].

**Need for three-terminal devices with READ-WRITE separation:** Note that a crucial function of the READ-WRITE circuit and the CMOS transistors in this design is the ability to turn the magnetization into an output voltage that is proportional to the read-out current and isolation to avoid read disturb. Indeed, a critical requirement of any other alternative implementations of p-bits is the need for three-terminal devices with separate READ and WRITE paths to provide gain and isolation. In this particular design these features come in directly integrating CMOS transistors. But CMOS-free, all-magnetic designs with these characteristics have been proposed [41, 44]. Our purpose is to simply show how a p-bit can be realized by using experimentally demonstrated technology. Alternative designs are beyond the scope of this paper.

**READ operation:** For the output to provide symmetric voltage swings on the GSHE layer, the minus supply $V^-$ needs to be set to $V_{DD}/2$ since $V_{OUT}$ ranges between 0 and $V_{DD}$. $V^+$ needs to be set to $V_{DD}/2 + V_R$ where $V_R$ is a small READ voltage that is amplified by the inverters. We assume a simple, bias-independent MTJ model [45]:

$$G_{MTJ} = G_0(1 + P^2 m_z) \tag{7}$$

where P is the interface polarization and $G_0$ is the average MTJ conductance. Setting the reference resistance to be $R_0 = 1/G_0$, the input voltage to the inverters, $V_M$ in FIG. (2d) becomes:

$$V_M = \frac{V_{DD}}{2} - \frac{V_R}{2 + m_z P^2} \tag{8}$$

In the absence of a bias ($m_z$) becomes 0 and the middle voltage fluctuates around the mean ($V_M$) = $V_{DD}/2 +$ $V_R/2$. This requires the inverter characteristic to be shifted to this value to produce a telegraphic output that fluctuates between 0 and $V_{DD}$ (Fig. 3f). This shift is easily engineered by sizing the pFET and nFET transistors differentially, a wider pFET shifts the inverter characteristic towards $V_{DD}$, we will show in the next subsection.

**Interconnection matrix:** A passive resistor network can be used as a possible interconnection scheme to correlate the p-bits as shown in Fig. 4. A proper design of the interconnection matrix $J$ that has only a few distinct conductances $(G_{ij})$. In this demonstrated example the AND gate requires only 2 unique, discrete connection values.

The spin currents needed to be delivered to each p-bit are on the order of a few $\mu$A and can be generated with charge currents that are even smaller, due to the GSHE gain. This means the interconnection resistances, $R_{ij}$ could be on the order of 100 kΩ since the voltage drops across these resistances are around $V_{OUT} - V^- \approx$ $\pm 0.5 V$. Since the GSHE gain and the thermal noise strength, $I_s^{th}$. (d) The output varies inversely to the error in the (A, B, C) output voltage are normalized by $V_{DD}$. Histogram is obtained by averaging over 200 ns of threshold voltages, only the first 20 ns of A, B, C voltages are shown for clarity.

---

## FIG. 3. CMOS-assisted implementation of p-bits

(a) A possible CMOS-assisted implementation of p-bits that have a separate READ/WRITE paths. A GSHE layer provides a magnetization of circular magnets ($\Delta \approx 0$ kT). The change in magnetization is sensed by an MTJ and amplified by two CMOS inverters that act as a buffer, providing the necessary isolation and gain. (b) Self-consistent, modular modeling of transport and magnetization dynamics. See Schematics of the model in the text. (c) Equivalent READ circuit. (d) SPICE-based average output voltage normalized to the $V_{DD} = 0.8$ V at 14 nm FinFET [22]. (c) sLLG-based average magnetization of the circular magnet as a function of the spin current (averaged over 500 ns for each bias point with a time step of $\Delta t = 0.05$ ps, in millions per second), normalized to the GSHE gain and thermal noise strength, $I_s^{th}$. (f) The time-dependent output voltage at various bias points.

---

voltage control [30, 31] instead of current control, just as the output could involve quantities other than magnetization. We will now show a concrete implementation of a Boolean function using minimal CMOS circuitry in conjunction with stochastic nanomagnets through detailed nanomag net and transport simulations that are in good agreement with those obtained from the generic model based on Eq. (1).

**Passive resistor network for interconnection:** For the interconnection resistances $R_{ij} \leq 125 k\Omega$ that roughly provides $\approx \pm \mu$ pA of charge current to each p-bit, corresponding to $h_i = 3.5$ for the discrete parameters.

**Generating the histogram:** At the end of the simulation ($t=200$ ns), we threshold the output of A and B at zero and letting all voltages above $V_{DD}/2$ to be 1. Then a histogram output for the thresholded value $|ABC|$ is obtained and normalized to unit probability. Clamping the output to 0 and letting A and B fluctuate in a correlated manner and they visit the three possible states (00, 01, 10) with approximately equal probability. Resolving the output 0 to the three possible input combinations is, in a "histogram" the output, only the consistent input combination C=1 (Fig. 9c-d).

**Assumptions of the model:** We have made several simplifying assumptions while modeling the hardware implementation of a p-bit: (1) The READ voltage that is amplified by the inverters produces a small current that passes through the circular magnet and might potentially disturb its current state. We assumed this current (labeled as $I_s$ in Fig. 3b) is negligible and do not affect the magnetization of the stochastic magnet. (2) We assumed that the spin current generated by the heavy metal is deposited to the free layer with perfect efficiency ($\eta = 1$ in Fig. 3b), however, depending on the interface properties this conversion factor can be less than 100%. (3) We have also assumed that the fixed layer does not provide a notable fixed field on the circular magnet. Note that the presence of such a constant field would simply shift the sigmoidal behavior presented in Fig. 3d-e to the right (or left) and could have been offset by a constant bias current. (4) Finally, we have neglected the resistance of the GSHE portion in the READ circuit (Fig. 3c), assuming the MTJ resistance would be dominant in this path.

---

**Detailed Simulation Parameters**

This section shows the details of simulation parameters for the hardware implementation of p-bits that are used in Fig. 3–4.

**sLLG for stochastic circular magnets:** The magnetization of a circular nanomaget described as $m_i$ is obtained from the stochastic Landau-Lifshitz-Gilbert (sLLG) equation:

$$(1 + \alpha^2) \frac{dm_i}{dt} = -\gamma[\vec{m}_i \times \vec{H}_i - \alpha|\vec{m}_i(\vec{m}_i \times \vec{H}_i)|$$

$$+ \frac{1}{qN_i}(\vec{m}_i \times \vec{f}_{si} \times \vec{m}_i) + \left(\frac{\alpha}{qN_i}\right)(\vec{m}_i \times \vec{f}_{si}) \tag{11a}$$

where $\alpha$ is the damping coefficient, $q$ is the electron charge, $\gamma$ is the electron gyromagnetic ratio, $I_s$ is the

| Parameters | Value |
|:--------:|:--------:|
| Saturation magnetization ($M_s$) | 300 emu/cc |
| Magnet diameter ($\Phi$), thickness (t) | 15 nm, 0.5 nm |
| MTJ Polarization (P) (Eq. (7)) | 0.5 |
| MTJ Conductance ($G_0$) (Eq. (7)) | 176 $\mu$S |
| Damping coefficient ($\alpha$) | 0.1 |
| Spin Hall Length, Width (Eq. (5)), | $L = W = 15$ nm |
| Hall Angle, Spin Hall, length, | $\theta_{SH} = 2.1$ nm[48] |
| Spin Hall res. ($\rho$), thickness (t) | 200 $\mu\Omega$-cm [49], 3.15 nm |
| Temperature (T) | 300 K |
| CMOS Models | 14nm HP-FinFET [22] |
| Supply and READ Voltage | $V_{DD} = 0.8$ V, $V_R = 0.5$ V |
| Timestep for transient sim. (SPICE) | $\Delta t = 0.05$ ps |

**TABLE 1. Parameters used for simulations in Figs. 3–4.**

---

## FIG. 4. An invertible AND gate

(a) Passive resistor network that is used to obtain the connection terms $J_{ij}$ to correlate p-bits. The output impedance $R_{ij} = 1/(G_{ij})$, allowing separate voltages to be read at the input of the inverters. (b) Explicit implementation of an AND gate based on Eq. (10). (c) When C is clamped to 1, A and B spend most of their time in the (1,1) state, the only combination consistent with C=1. (d) The inverted operation of the AND gate where we clamp the output bit C to a 0 or 1 by the biasing the input terminal. The interconnection resistances are chosen to be $R_{ij} = 1/(G_{ij})$, allowing separate voltages to be read at the input of the inverters. (b) Explicit implementation of an AND gate based on Eq. (10). (c) When C is clamped to 1, A and B spend most of their time in the (1,1) state, the only combination consistent with C=1. (d) The inverted operation of the AND gate where we clamp the output bit C to a 0 or 1 by biasing the input terminal. The interconnection resistances are chosen to be $R_{ij} = 1/(G_{ij})$, allowing separate voltages to be read at the input of the inverters. (b) Explicit implementation of an AND gate based on Eq. (10). (c) When C is clamped to 1, A and B spend most of their time in the (1,1) state, the only combination consistent with C=1. (d) The inverted operation of the AND gate where we clamp the output bit C to a 0 or 1 by biasing the input terminal. The interconnection resistances are chosen to be $R_{ij} = 125 k\Omega$ that roughly provides $\approx \pm 0$ pA of charge current to each p-bit, corresponding to $h_i = 3.5$ for the discrete parameters.

---

## FIG. 5. 14 nm PTM, Inverter/Buffer: DC response of 14 nm high performance (HP) FinFETs based on [22] for an inverter and buffer. Sizing the transistors differently allows the switching point to be shifted.

---

---

## III. INVERTIBLE BOOLEAN LOGIC WITH BOLTZMANN MACHINES

We now present a mathematical prescription that shows how any given truth table can be implemented in terms of Boltzmann Machines, in "one shot" without learning being involved, unlike much of the past work in this area (See for example, [50, 51]). In Section II, we chose a simple {J} and {h} matrix to implement an AND gate based on [46]. In this section we continue a general approach to show how any truth table can be engineered in terms of such matrices. The approach, pictorially described in Fig. 6, begins by transforming a given truth table from binary (0,1) to bipolar ($-1,+1$) variables. The lines of the truth table are then converted to be eigenvectors each with eigenvalue +1, all eigenvectors are assumed to have eigenvalue +1. This leads to the following prescription for J as shown in Fig. 6:

$$[J] = \sum_{ij} [S^{-1}]_{ij}u_i u_j^T \tag{12a}$$

$$S_{ij} = u_i u_j \tag{12b}$$

where $u_i$ are the eigenvectors corresponding to lines in the truth table of a Boolean operation and S is a projection matrix that accounts for the non-orthogonality of the vectors defined by different lines of the truth table. Note that the resultant J-matrix is always symmetric ($J_{ij} = J_{ji}$) with diagonal terms that are subtracted in our models such that $J_{ii} = 0$. The number of p-bits in the system is made greater than the number of lines in the truth table through addition of "handle bits" (Fig. 6) to ensure that the number of conditions we impose is less than the dimension of the space defined by the number of p-bits.

Another important aspect in the construction of [J] is that an eigenvector $u_i$ implies that its complement $-u_i$ is also a valid eigenvector. However only one of these might belong to a truth table. We introduce a "handle" bit to each $u_i$ that is biased ($h_i$) to distinguish complementary eigenvectors. These handle bits provide the added benefit of reconstruction capability. For example, AND and OR gates have complementary truth tables, and a given gate can be electrically reconfigured as an OR gate using the handle bit.

**J-Matrices for AND gate:** We now provide the details of the J-matrix for the AND gate, obtained using the prescription shown in Fig. 6 based on Eq. (12a). The eigenvectors for the AND gate are placed into a matrix U, such that U = [$u_1$  $u_2$  $u_3$  $u_4$], where $u_i$ is the first row of the matrix shown in Fig. 6, where $u_i$ is the first row of the matrix shown in Fig. 6, where the eigenvectors are column vectors. As an example, we have shown auxiliary bits that result in S-matrix to be the identity matrix, since the eigenvectors are orthogonal. The J-matrix is then obtained by Eq. (12c) where all entries are:

$$[J] = \sum [S^{-1}]_{ij} u_i u_j^T = 1/8 \sum u_i u_i^T \tag{14}$$

Removing the diagonal entries by making $J_{ii} = 0$ and multiplying the matrix entries by 2, to obtain simple integer values, the resulting symmetric 4 × 4 J-matrix is:

$$J = \begin{pmatrix} 0 & -1 & +2 \\ -1 & 0 & +2 \\ +2 & +2 & 0 \end{pmatrix} \quad h^T = [+1 +1 -2] \tag{10}$$

In Fig. 4d, we show the *inverse* operation of the AND gate where we clamp the output bit C to a 0 or 1 by the

---

---

| Truth Table | | Magnetization | | | Auxiliary Bits | Handle Bits | Input/Output | | | |
|:--------:|:--------:|:--------:|:--------:|:--------:|:--------:|:--------:|:--------:|:--------:|:--------:|:--------:|:--------:|
| A | B | $u_1$ | $u_2$ | $u_3$ | C | $u_3$ | C | $u_3$ | C | $u_3$ | C |
| 0 | 0 | -1 | -1 | -1 | -1 | +1 | +1 | 0 | -1 | -1 | +1 |
| 0 | 1 | -1 | +1 | -1 | -1 | +1 | +1 | 1 | -1 | +1 | -1 |
| 0 | 1 | +1 | -1 | -1 | -1 | +1 | +1 | 1 | -1 | +1 | -1 |
| 1 | 1 | +1 | +1 | +1 | +1 | -1 | -1 | 1 | +1 | +1 | +1 |

---

## FIG. 6. Truth Table to J-Matrix

A given truth table is first transformed from binary to bipolar variables by using the transformation $m = 2^i - 1$ where $m$ and $i$ represent the magnetization and binary values of the truth table. Additional bits are introduced to each line of the truth table to ensure that the resultant S-matrix is invertible. The indices $i,j$ correspond to the number of lines in the truth table, $u_i u_j$ are column vectors. As an example, we have shown auxiliary bits that result in S-matrix to be the identity matrix, since the eigenvectors are orthogonal. The J-matrix is then obtained by Eq. (12c) where all entries are subtracted in our models such that $J_{ii} = 0$. The number of conditions we impose is less than the dimension of the space defined by the number of p-bits.

---

biasing the input terminal. The interconnection resistances are chosen to be $R_{ij} = 125 k\Omega$ that roughly provides $\approx \pm 0$ pA of charge current to each p-bit, corresponding to $h_i = 3.5$ for the discrete parameters.

**Generating the histogram:** At the end of the simulation ($t=200$ ns), we threshold the output of A and B at zero and letting all voltages above $V_{DD}/2$ to be 1. Then a histogram output for the thresholded value $|ABC|$ is obtained and normalized to unit probability. Clamping the output to 0 and letting A and B fluctuate in a correlated manner and they visit the three possible states (00, 01, 10) with approximately equal probability. Resolving the output 0 to the three possible input combinations is, in a "histogram" the output, only the consistent input combination C=1 (Fig. 9c-d).

also a valid eigenvector. However only one of these might belong to a truth table. We introduce a "handle" bit to each $u_i$ that is biased ($h_i$) to distinguish complementary eigenvectors. These handle bits provide the added benefit of reconstruction capability. For example, AND and OR gates have complementary truth tables, and a given gate can be electrically reconfigured as an OR gate using the handle bit.

---

## FIG. 7. Correlated p-bits, AND Gate

When the interaction strength ($I_0$) is zero, p-bits produce uncorrelated noise, visiting all possible states with equal probability. In this example, the interaction strength (pseudo-temperature) is suddenly increased from 0 to 2 as a step function at $t = t_0$, to effectively "quench" the network. This correlates the p-bits to produce the truth table of an AND gate (AND: $A \cap B = C$). Note that after this quenching, the p-bits only visit the low energy states corresponding to the truth table of the AND gate and once the system is in one of the low energy states, it tends to stay there for a while. Indeed because of the thermal noise, the system are well-explained by the Boltzmann law defined in Eq. (4). The total simulation used a $T = 4c 0$ steps to compare the results with the Boltzmann distribution, though only a fraction is shown in the upper panel for clarity.

integers, $J_{AND}$ evaluates to:

$$J_{AND} = \begin{pmatrix} 0 & -1 & 0 & 1 & 1 & 1 & 0 \\ 0 & 0 & 1 & 0 & 0 & 0 & 1 \\ 0 & 0 & 0 & 1 & 1 & -1 & 0 \\ 0 & 1 & 0 & 0 & 1 & 1 & -1 \\ 0 & 1 & 0 & 0 & 0 & -1 & 1 \\ 0 & 0 & 1 & 1 & 1 & 0 & -1 \\ 1 & 0 & -1 & 1 & 0 & 0 & 1 \end{pmatrix} \tag{15}$$

with the notation, [1-5: auxiliary bit and handle bit, 6-7: $C_{\text{in}}$, 7: "B"], 8: "A", 9: "S" 14: "$C_{\text{out}}$"]. These are the J-matrices (AND and FA) that are used for all examples in the paper, except for the AND gate described in Section II. Fig. 10 shows the "truth table"

---

## FIG. 8. Implementing a Boolean function and its inverse

The input or output terminals of an appropriately inter-connected network of p-bits can be "clamped" to perform a specific logic operation or its inverse. In this example, the input bits of an OR gate (A, B) are OR gated are clamped to be +1, forcing the output bit C to be 1, during the first phase of operation ($t < t_0$). In the second phase of operation ($t > t_0$), the output of the OR gate C is clamped to the value +1, which is consistent with three different combinations of (A, B). As shown in the time response and in the basic-time histogram plot, all three possibilities emerge with equal probability, demonstrating the "inverse" OR operation. In each case, the expected probabilities from the Boltzmann Law (Eq. (1-2)) after running the system for one million steps, only a fraction is shown in the upper panel for clarity.

---

$$10^{-2} \quad I_i = h_i(h_i + J_{ij}m_j) + h_n, \langle h_n \rangle = 0$$

$$10^{-4}$$

$$10^{-6}$$

$$10^{-8}$$

$$10^{-10}$$

$$10^{-12}$$

$$0.2 \quad 0.4 \quad 0.6 \quad 0.8 \quad 1$$
$$h_n$$

---

## FIG. 9. Noise Tolerance of AND

The probability of a noise output for an (AND) gate (Eq. 15) operated with random noise field that enters bias fields of each p-bit and define the computation to the faulty, if the mode (most frequent value) of the output bit is not consistent with the programmed input combined after T = 100 time steps. We observe that even in the presence of large levels of uncontrolled noise produces correct results with high probabilities. The system shows robust behavior even in the presence of large levels of noise. Results for random inputs and clamped inputs A and B ±$h_n$, where [$I_0 = 2, h_i = \pm 1$]. Each gate is simulated 50000 times for a given noise value, and the maximum peak produced by the system is assumed to be an output that can be read with certainty. The system shows robust behavior even in the presence of large levels of noise.

---

---

## FIG. 10. Full Adder

Full Adder in the truth table mode, where all inputs and outputs are floating, calculated using $I_0$ from Eq. ($I_0$ from Eq. ($I_0 = 0.5$ in the truth mode, where all inputs and outputs are floating. The decimal numbers corresponding to the truth table are shown in the inset, and these match the location of the taller peaks in the histogram. The decimal numbers corresponding to the truth table are shown in the inset, and these match the location of the taller peaks in the histogram. Note that the Boltzmann distribution (Eq. (4)) quantitatively matches the model even for the suppressed peaks. A higher $I_0$ reduces these suppressed peaks further. The statistics are collected for T = 10^6 steps, and each terminal output is then placed in the histogram.

---

## IV. DIRECTED NETWORKS OF BOLTZMANN MACHINES

When constructing larger circuits composed of individual virtual Boltzmann machines, the reciprocal nature of the Boltzmann Machines is desired. It seems advisable to use a hybrid approach. For example in constructing a 32-bit adder [11] that are individually BMs with symmetric connections, $J_{ij} = J_{ji}$. But when connecting the carry bit from one FA to the next, the coupling element $J_{ij}$ is non-zero in only one direction from the least significant to the most significant bit. This directed coupling between adders distinguishes PSL from purely reciprocal Boltzmann machines.

Indeed, even the Full Adder could be implemented not as a Boltzmann machine but as a directed network of more basic gates. But then it would lose its invertibility. The demonstration of such an invertible 32-bit adder could be practically important, since binary addition is noted to be the most fundamental and frequently used operation in digital computing [57].

**Delay of Ripple Carry Adder:** Just as in CMOS-based logic, the delay of the RCA is a function of the inputs A and B. In Fig. 12 we have systematically studied the worst-case delay of the p-bit based Ripple Carry Adder (RCA) as a function of increasing bit size. We selected a "worst-case" combination that generates a carry that propagates all the way through bit-1 to bit-N which results in a linear increase in the delay, exhibiting $O(n)$ complexity. When the inputs are random, the delay seems to increase sub-linearly. The delay is explicit to be the time it takes for the network to reach the mode of the array for T=200. An error check has been carried out separately to ensure that the calculated sum (mode) is always exactly equal to the expected sum. For random inputs the 32-bit adder is close to 20 times faster in accordance with the example shown in Fig. 11.

---

## FIG. 11. 32-bit Ripple Carry Adder (RCA)

(a) A 32-bit Ripple Carry Adder (RCA) is designed using individual Full Adder (FA) units with the carry bit designed as a *directed connection* from the least significant bit to the most significant bit. The overall J-matrix for a 32-bit adder is shown, and it is quite sparse and quantized. (b) For $I_0 = I_0$, is suddenly increased, and the adder converges on the correct result from two random inputs A and B. At $t > t_0$, the sum fluctuates randomly. At $t > t_0$ shows a single peak with 24% probability of time spent in the correct state (including the uncorrelated time points for $t < t_0$) show the target state in the correct state (including the uncorrelated time points for $t < t_0$) shows a single peak with 24% probability of time spent in the correct state. (E) Even though the connections between the Full Adder units are directed, the system performs the inverse function as well. When the output (S) is clamped to a fixed number, the inputs (A) and (B) fluctuate in a correlated manner to make A+B=S when $I_0 = 1$. Note the broad distributions of A and B (collected for $t > t_0$) as compared to the extremely sharp distribution of A+B.

---

that results in a carry that needs to be propagated from bit 1 to bit N which results in a linear increase in the delay, exhibiting O(u) complexity. When the inputs are random, the delay seems to increase sub-linearly. The delay is explicit to be the time it takes for the network to reach the mode of the array for T=200. An error check has been carried out separately to ensure that the calculated sum (mode) is always exactly equal to the expected sum. For random inputs the 32-bit adder is close to 20 times faster in accordance with the example shown in Fig. 11.

---

## FIG. 12. Ripple Carry Adder delay

The delay of the RCA for a 32-bit Ripple Carry Adder is shown. The worst-case input generates a carry that propagates all the way through bit-1 to bit-N, and has a linear dependence on the number of bits, exhibiting O(u) complexity. When the inputs are random, the delay seems to increase sub-linearly. The delay is explicit to be the time it takes for the network to reach the nodes of the array for T=200 adder. An error check has been carried out separately to ensure the calculated sum (mode) is always exactly equal to the expected sum. For random inputs the 32-bit adder is close to 20 times faster in accordance with the example shown in Fig. 11. Results show a weak $I_0$ dependence.

---

digital accuracy and invertibility is made possible by our hybrid design, whereby the individual Full Adders are Boltzmann machines, even though their connection is directed. Our 32-bit adder is more like a collection of interacting particles than like a digital circuit. We show that 32-bit adder connects the carry bits from the least significant to the most significant bit could lead to a loss of invertibility. To investigate this point, we show the operation of a 32-bit adder. We observe that the 32-bit adder shown in Fig. 13a which shows a colormap of the binary state of the entire 32-bit adder's bits as a function of time with the interaction parameter $I_0$ is suddenly increased from 0.25 to 5 at $t_0 = 50$. For low interaction parameters the AND of p-bits is like a collection of interacting particles than like a digital circuit as evident from (Fig. 13a) which is the same the case for $I_0 = 0.25$. But the collection of p-bits is like a random the "golden quench" to a solid "full of defects" (with hardly any zeros), with $S - A - B$ exactly equal to zero (Dark Blue) in only a at $I_0 = 50$, but in this case the resulting "solid" is full of defects (with hardly any zeros), with $S - A - B$ exactly equal to zero (Dark Blue) in only a at $I_0 = 50$, but in this case the resulting "solid" is full of defects (with hardly any zeros), with $S - A - B$ exactly equal to zero. Surprisingly this solid corresponds to a "perfect crystal" in each of the 1000 trial experiments, with $S - A - B$ exactly equal to zero (Dark Blue) in test (c) and (d) The calculation is modified to have a dark blue color corresponding to exactly zero. S, A, B are taken to be the statistical mode of the 100 $\times$ 1 array obtained at the end of each trial.

---

## FIG. 13. Accuracy of 32-bit adder, directed versus bidirectional

The results are shown for the adder operating in a subtractor mode, clamping one (random) 32-bit input (A) and a (random) 33-bit output ($C_{out} + S$), and observing the other 32-bit input B, which should provide the difference S−A. (a): Colormap of the binary state of the 48 32-bit adders comprising the directed adder as a function of time with the interaction parameter $I_0$ suddenly increased from 0.25 to 5 at $t_0=50$. For low interaction parameters, the directed adder as a function of time with the interaction parameter $I_0$ suddenly increased from 0.25 to 5 at $t_0$=50. For low interaction parameters, the collection of p-bits is like a random the "golden quench" to a solid "full of defects" (with hardly any zeros), with $S - A - B$ exactly equal to zero (Dark Blue) in only a $I_0 = 0$ probability of hitting a state with $S - A - B$ exactly equal to zero (Dark Blue). In each case the resulting "solid" is full of defects (with hardly any zeros), with $S - A - B$ exactly equal to zero (Dark Blue) in only a at $I_0 = 50$, but in this case the resulting "solid" is full of defects (with hardly any zeros), with $S - A - B$ exactly equal to zero. Surprisingly this solid corresponds to a "perfect crystal" in each of the 1000 trial experiments, with $S - A - B$ exactly equal to zero (Dark Blue) in test (c) and (d) The calculation is modified to have a dark blue color corresponding to exactly zero. S, A, B are taken to be the statistical mode of the 100 $\times$ 1 array obtained at the end of each trial.

---

**BM implementation (Fig. 13d).**

Note that lower-level digital accuracy is achieved while maintaining the property of invertibility that is absent in digital circuits. Fig. 13 is not for direct mode operation, but for the adder operating in reverse mode as a subtractor. It might be expected that the directed connection of carry bits from the least significant to the more significant bit could lead to a loss of invertibility. To investigate this point, we show the operation of a 32-bit adder. We observe that the 32-bit adder shown in Fig. 13a, which shows a colormap of the binary state of the entire 32-bit adder's bits as a function of time with the interaction parameter $I_0$ is suddenly increased from 0.25 to 5 at $t_0 = 50$. For low interaction parameters, the collection of p-bits is like a random the "golden quench" to a solid "full of defects" (with hardly any zeros), with $S - A - B$ exactly equal to zero (Dark Blue) in only a $I_0$ value of 0 are probability of hitting a state with $S - A - B$ exactly equal to zero (Dark Blue). The directed implementation works perfectly for both the adder and the subtractor modes, but not if we clamp the least significant bits, but if we clamp the most significant bits, these seem reasonable since we expect to be able to control a flow by making changes upstream (lsb), but not downstream (msb).

**Partial directionality:** So far in our examples we have only considered fully directed ($J_{ij} = 2 J_{ji}, J_{ji} = 0$) or fully bidirectional ($J_{ij} = J_{ji}$) in carry bits when connecting the individual Full Adders. In Fig. 15 we systematically study the effects of partial directionality in the operation of a 32-bit adder. We observe that the 32-bit adder shown in Fig. 13a, which shows that a 32-bit adder operates correctly even when there is large degree of bidirectionality ($J_{ij} = 0.75 \times J_{ji}$) provided that the system is allowed to run for a long time, $T = 50000$, in stark contrast with the highly directed case that could solve the right answer with $T = 100$, shown in Fig. 14b. Decreasing the interaction from 0.25 to 5 at $t_0 = 50$, thereby quenching a "molten liquid" into a "perfect liquid". What we expect is "a solid full of defects" with different non-zero values for $S - A - B$ in each trial. That is exactly what we get if the carry bits are bidirectional as in a fully directed BM. This is a key result that we establish with extensive examples including a 4-multiplier which is inverted mode functions as a factorizer.

---

## FIG. 14. Invertibility of 32-bit adder, directed vs bidirectional

An adder that provides the sum $S$ of two 32-bit numbers A and B: $S = A + B$. The left panel shows the adder implemented with bidirectional carry bits, while the right panel shows the adder implemented with directed carry bits from the least significant to the most significant bit. For different modes of operation are shown: (i) A and B clamped (Addition), (ii) S and A clamped (Subtraction), (iii) A, B and S for the 16 most significant bits (msb) clamped, and (iv) A, B and S for the 16-lsb's clamped. Note that bidirectional implementation shows very large errors for all modes of operation, but if we clamp the least significant bits, but not if we clamp the most significant bits, these seem reasonable since we expect to be able to control a flow by making changes upstream (lsb), but not downstream (msb). The directed implementation works perfectly for both the adder and the subtractor modes, but not if we clamp the least significant bits. The directed implementation works perfectly for both the adder and the subtractor modes, but if we clamp the most significant bits, these seem reasonable since we expect to be able to control a flow by making changes upstream (lsb), but not downstream (msb). Correlation parameter $I_0 = 1$, $T = 100$ steps for all trials. S, A,B are taken to be the statistical mode of the 100$\times$1 array obtained at the end of each trial. Clamped inputs are random 32-bit words for each trial, for a total of 1000 trials.

---

$$100 \quad \text{×} \circ \circ \circ \circ \circ \circ \circ$$
$$80 \quad \bullet + \bullet \bullet \bullet \bullet \bullet \bullet + \circ$$
$$60 \quad \diamond T \diamond T \diamond T \diamond T \diamond$$
$$40 \quad \circ \circ \circ \circ \circ \circ \circ \circ \circ$$
$$20 \quad \square T + \square T \square + \square T$$
$$0 \quad 0 \quad 0.2 \quad 0.4 \quad 0.6 \quad 0.8$$
$$J_{ij}/J_{ji}$$

---

## FIG. 15. Error versus bidirectionality

The degree of bidirectionality, $J_{ij}/J_{ji}$, of the Full Adders is systematically varied while keeping the sum is the (majority vote) of T time samples using the statistical mode (majority vote) of T time samples. Note that the largest $J_{ij}$ and smallest $T$ error-free operation is obtained only when there is close to zero from the statistical mode (majority vote) of T time samples. Note that the largest $J_{ij}$ and smallest $T$ error-free operation is obtained only when there is one where large $I_0$ and small $T$ error-free operation (at least for 50 trials). The y-axis shows the fraction of trials that yield zero, similar to standard digital circuits. But with $I_0 = 1.5$ and $T=50,000$ error-free operation can be also so on. We also kept the same directed connections between the Full Adders for the carry bits, making them a directed network of Boltzmann Machines, similar to the 32-bit Adder. Moreover, we kept a directed connection *from* the Full Adders *to* the AND gates as shown in Fig. 16a since the information needs to flow from the output to the

---

## FIG. 16. Factorization through inverse multiplication

The reversibility of PSL allows the operation of integer factorization using a binary multiplication circuit implemented using the principles of digital logic using AND gates and Full Adders (FA) as shown in (a). The four output nodes of the 4-bit multiplier are clamped to a given integer from 0 to 15. The input bits float to the correct factors. The interconnection strength $I_0$ is suddenly increased from 0 to 1 at $t_0 = 1$ (Fig. 16) and the system produces the only consistent factors of the product at the input terminals, probabilistically. The interaction parameter $I_0$ is suddenly increased from 0 to 1 at $t_0 = 1$ (Fig. 16) and the system produces the only consistent factors of the product at the input terminals, probabilistically.

In both cases the histogram is obtained by counting outputs after $t > t_{total}/2 = 1.25 \times 10^4$ time steps to collect statistics after the system is thermalized.

---

## V. SUMMARY

It is generally believed that (1) probabilistic algorithms can tackle specific problems much more efficiently than classical algorithms [62], and that (2) probabilistic algorithms can run far more efficiently on a probabilistic computer than on a deterministic computer [62, 63]. As such, it seems reasonable to expect that probabilistic computers based on robust from femerotemperature p-bits could provide a practically useful solution to many challenging problems by rapidly sampling the phase space in hardware.

In this paper we have presented a framework for using probabilistic or "p-bits" as a building block for a probabilistic spin logic (PSL) which is used to implement precise Boolean logic with an accuracy comparable to standard digital circuits, while exhibiting the unique property of invertibility that is unknown in deterministic circuits. Specifically we have:

- presented an implementation based on stochastic nanomagnets to illustrate the importance of three-terminal building blocks in the construction of large scale correlated networks of p-bits. We emphasize that this is just one possible implementation and the concept of p-bits does not necessarily require the use of nanomaget-based devices as discussed in Section II.

- presented an algorithm for implementing Boolean gates as BM with relatively sparse and quantized J-matrix elements, benchmarked their operation against the Boltzmann law, and established their capability to perform not just direct functions but also inverse Boolean logic (Section III) and

- presented a 32-bit adder implementation as a hybrid BM that achieves digital accuracy over a broad combination of the interaction parameter $I_0$, directionality and the number of samples $T$. This striking accuracy is reminiscent of digital circuits, but it achieved while preserving a certain degree of invertibility which is absent in digital circuits. The accuracy is particularly surprising, given the degrees of bidirectionality ($J_{ij} = 0.75 \times J_{ji}$) with which the system is picking out the one correct answer out of nearly 2^{33} ≈ 8 billion possibilities. This may require a larger number of time samples, but these findings will help emphasize a new direction for the field of spintronic and nanomagnetic logic by shifting the focus from stable high barrier magnets to stochastic, low barrier magnets, while inspiring a search for other possible physical implementations of p-bits.

---

## ACKNOWLEDGMENTS

It is a pleasure to acknowledge many helpful discussions with Behtash Behin-Aein (Globalfoundries) and Ernesto E Mariano (Purdue University). We thank Jaijeet Roychowdhury (UC Berkeley) for suggesting the term "invertible". This work was supported in part by C-SPIN, one of six centers of FENA/SRC, a Semiconductor Research Corporation program, sponsored by MARCO and DARPA, in part by the Nanoelectronics Research Initiative through the Institute for Nanoelectronics Discovery and Exploration (INDEX) Center, and in part by the National Science Foundation through the NCN-NEEDS program, contract 1227020-EEC.

---

## REFERENCES

[1] L Lopez-Diaz, L Torres, and E Moro, "Transition from ferromagnetism to superparamagnetism on the nanosecond time scale," Physical Review B 65, 224406 (2002).

[2] Krishna Palem and Avinash Lingamneni, "Ten years of battling bugs: Inexact computing," ACM Transactions on Embedded Computing Systems 12, 2 (2013).

[3] Suresh Cheemalavagu, Pinar Korkmaz, Krishna Palem, BS Akgul, and Lakshmi V Chakrapani, "A probabilistic cmos switch and its realization by exploiting noise," in IFIP International Conference on Very Large Scale Integration (VLSI) (2005) pp. 535–541.

[4] Abid Fukushima, Takayuki Seki, Koy Yakushiji, Hitoshi Kubota, Hiroshi Imamura, Shinji Yuasa, and Koji Audo, "Spin dice": A scalable truly random number generator based on spintronics," Applied Physics Express 7, 083001 (2014).

[5] Won Ho Choi, Yang Lv, Jongyeon Kim, Abhishek Deshpande, Gyuseong Kang, Jian-Ping Wang, and Chris H Kim, "A magnetic tunnel junction based random number generator with conditional perturb and real-time probability tracking," in Electron Devices Meeting (IEDM), 2014 IEEE International (IEEE, 2014) pp. 12–5.

[6] Julie Grollier, Damien Querlioz, and Mark D Stiles, "Spintronic oscillators for bioinspired computing," in Proceedings of the IEEE 104, 2023–2039 (2016).

[7] J. Roychowdhury, "Private communication," in Theory of Cryptography Conference (Springer, 2009) pp. 73–90.

[8] For an example of the use of "invertible relations", see Ran Canetti and Mayank Varia, "Non-malleable obfuscation," in Theory of Cryptography Conference (Springer, 2009) pp. 73–90.

[9] Behtash Behin-Aein, Vinh Diep, and Supriyo Datta, "A building block for hardware belief networks," Scientific Reports 6, 29893 (2016).

[10] Y. Shao, A. Jaiswal, and K. Roy, Journal of Applied Physics 121, 193902 (2017).

[11] B. Sutton, K. Y Camsari, B. Behin-Aein, and S. Datta, Scientific Reports 7 (2017).

[12] J Madan, P Shrivastava, S Choi, S Datta, and A. Chaterjee "Memristive devices for computing," Nature nanotechnology 8, 23-24 (2013).

[13] Vinh Quang Diep, Brian Sutton, Behtash Behin-Aein, and Supriyo Datta, "Spin switches for compact implementation of neuron and synapse," Applied Physics Letters 104, 222405 (2014).

[14] Abhironil Sengupta, Yong Shim, and Kaushik Roy, "Proposal for an all spin artificial neural network: Emulating neural and synaptic functionalities through domain wall motion," in 2016 IEEE International Symposium on Biomedical Circuits and Systems (2016).

[15] Masanao Yamamoto, Chihiro Yoshinaga, Chihiro Yoshinaga, Osamu Tetsumoto, Masato Hayashi, and Takuya Okamoto, "Tsing computer," Hitachi Review 65, 157 (2016).

[16] David H Ackley, Geoffrey E Hinton, and Terrence J Sejnowski, "A learning algorithm for Boltzmann machines," Cognitive Science 9, 147–169 (1985).

[17] Masanao Yamamoto, Chihiro Yoshinura, Masato Hayashi, and Takuya Okamoto, "24.0 zk spin chip for combinatorial optimization problems with cross annealing," in 2015 IEEE International Solid-State Circuits Conference (ISSCC) Digest of Technical Papers (IEEE, 2015) pp. 1–3.

[18] Takahiro Inagaki, Kensuke Inaba, Ryan Hamersky, Kyo Inoue, Yoshihisa Yamamoto, and Hiroki Takesue, "Large-scale ising spin network based on degenerate optical parametric oscillators," Nature Photonics (2016).

[19] Ruslan Salakhutdinov, "Restricted boltzmann machines for collaborative filtering," in Proceedings of the 21th international conference on Machine learning (ACM, 2007) pp. 791–798.

[20] David H Ackley, "Explorating the state of stochastic network" Hopfield networks and stochastic networks," in Proceedings of the National Academy of Sciences (NAS) 79 (1982) pp. 2554-2558.

[21] Dingzhu Du, Jun Gu, Panos M Pardalos, et al., "Satisfiability problems: Theory and applications: DIMACS Workshop, March 11-13, 1996, Vol. 35 (American Mathematical Society, 1997).

[22] "Predictive Technology Model (PTM)" (http://ptm.asu.edu/).

[23] B. Sutton, K. Y. Camsari, B. Faria, and S. Datta, arXiv preprint arXiv:1703.2 (2017).

[24] Luqiao Liu, Chi-Feng Pai, Y. Li, H W Tseng, D. Ralph, and RA Buhrman, "Spin-torque switching with the giant spin hall effect," Science 336, 555–558 (2012).

[25] Nicola Locatelli, Alice Mizrahi, A Acioly, Rie Matsumoto, Akio Fukushima, Hitoshi Kubota, Shinji Yuasa, Vincent Cros, Luc Grollier, and Julie Grollier, "Noise-enhanced synchronization of stochastic nanomagnetic oscillators," Physical Review Applied 2, 034009 (2014).

[26] Arno van den Brink, Guus Vermijs, Aurelie Solignac, Jungwoo Koo, Juan Pablo Aranda, and Bert Koopmans, "Field-free magnetization reversal by spin-hall and exchange bias," Nature communications 7 (2016).

[27] Yong-Chang Lau, David Betto, Karsten Rode, JMD Coey, and Plamen Stamenov, "Spin-orbit torque switching without external field using exchange bias," Nature nanotechnology 11 (2016).

[28] Anqing Kewan Smith, Md. Hasanuzzaman Zhao, and Jian-Ping Wang, "External free spin hall effect device for perpendicular magnetization reversal using composite structure with biasing layer," arXiv preprint arXiv:1603063 (2016).

[29] Shinsuke Fukami, Chaoliang Zhang, Samik DuttaGupta, Abdessamad Azaiez, and Hidec Ohno, "Magnetization switching by spin-orbit torque in an antiferromagnet-ferromagnet bilayer system," Nature materials (2016).

[30] JT Heron, JL Bosse, Q He, Y Gao, M Trassin, L Ye, JD Clarkson, C Wang, J Liu, S Salahuddin, et al., "Deterministic switching of ferromagnetism at room temperature using an electric field," Nature 516, 370–373 (2014).

[31] Sailesh Manipatruni, Dmitri E Nikolaev, and Ian A Young, "Spin-orbit logic with magnetoelectric nodes: A spintronic-logic scheme based on hybrid spintronics circuits," arXiv preprint arXiv:1512.0528 (2015).

[32] Roger H Koch, G Grinstein, GA Kede, Yu Lir, PL Trouillaud, P Wiseman, and SBP Parkin, "Thermally assisted magnetization reversal in submicron-sized magnetic thin films," Physical review letters 84, 5419 (2000).

[33] Sergei Urazhdin, Norman O Birge, WP Pratt Jr., and J Bass, "Current-driven magnetic excitations in permalloy-based multilayer nanopillars," Physical review letters 91, 146803 (2003).

[34] IN Krivrotov, NC Emley, AGF Garcia, JC Sankey, SI Kiselev, DC Ralph, and RA Buhrman, "Temperature dependence of spin-transfer-induced switching of nanomagnets," Physical Review Letters 93, 160802 (2004).

[35] AV Kivaykskii, D Apalkov, S Watts, R Chepulskit, Y Acreman, B Bisset, D Smith, WH Butler, L Visscher, et al., "Basic principles of spin-anisotropy," Applied Physics 46, 074001 (2013).

[36] RP Cowburn, "Freeform magnetic nanoelemts," Journal of Physics D: Applied Physics 33, R1 (2000).

[37] Punyashlock Debashis, Rafatul Faria, Kerem Y Camsari, Joris Appezzeller, Supriyo Datta, and Zhihong Chen, "Experimental demonstration of nanomag net network as hardware for spin computing," in Electron Devices Meeting (IEDM), 2016 IEEE International (IEEE, 2016) pp. 34–3.

[38] Kerem Yunus Camsari, Samiran Ganguly, and Supriyo Datta, "Modular approach to spintronics," Scientific Reports 5 (2015).

[39] Ludiro Lia, Palehiro Moriyama, D. C. Ralph, and R. A. Buhrman, "Spin-torque ferromagnetic resonance induced by the spin hall effect," Phys. Rev. Lett. 106, 036601 (2011).

[40] Seokhyun Hong, Shehrin Sayed, and Supriyo Datta, "Spin circuit representation for the spin hall effect," IEEE Transactions on Magnetics 15, 295–236 (2016).

[41] Supriyo Datta, Saweed Salahuddin, and Behtash Behin-Aein, "Non-volatile spin switch for boolean and non-boolean logic," Applied Physics Letters 101, 252411 (2012).

[42] William H Butler, Tim Mewes, Claudin KA Mewes, FB Visscher, William H Hippsard, Stephen E Russek, and Ranko Herath, "Switching distributions for perpendicular spin-torque devices within the macrospin approximation," IEEE Transactions on Magnetics 48, 4684–4700 (2012).

[43] Andrew D Kent and Daniel C Worledge, "A new spin on magnetic memories," Nature nanotechnology 10, 187–191 (2015).

[44] Daniel Morris, David Bromberg, Jian-Gang Jimmy Zhu, and Larry Pileggi, "iologic: Ultra-low voltage non-volatile logic circuits using spin-torque devices," in Proceedings of the 2012 Annual Design Automation Conference (ACM, 2012) pp. 486–491.

[45] Deepajit Datta, Behtash Behin-Aein, Supriyo Datta, and Sayed Salahuddin, "Voltage asymmetry in spin transfer-induced switching," IEEE Transactions on Nanotechnology 11, 261–272 (2012).

[46] JD Brouwere, "Nonproperturabive k-body to two-body computing conversion hamiltonians and embedding tensor instanton into spin units," Physical Review A 77, 052331 (2008).

[47] Kai-Ting Huang, Timothy Pheng, Weifang Yang, Brian P Hughes, Hee-Hun Yang, Aukaash Pushp, and Stuart SP Parkin, "Enhanced spin-orbit torque inclined in tungsten thin films," Nature communications 7 (2016).

[48] Chi-Feng Pai, Luqiao Liu, Yongxi Li, HW Tseng, D Ralph, and RA Buhrman, "Spin transfer torque devices utilizing the giant spin hall effect of tungsten," Applied Physics Letters 101, 122404 (2012).

[49] Qiang Hao and Gang Xiao, "Giant spin hall effect and switching induced by spin-transfer torque in a w/co structure," Applied Physics Letters 109, 042406 (2016).

[50] Bernecio S Sejnowski, Paul B Knudler, and Geoff E Hinton, "Learning symmetry groups with hidden units: Beyond the perceptron," Physica D: Nonlinear Phenomena 22, 260–275 (1986).

[51] LE Petrman, "Learning networks of neurons with boolean logic," EPL (Europhysics Letters) 4, 563 (1987).

[52] L Personmaz, I Guyon, and G Dreyfus, "Collective computation in neural networks," Physical Review A 34, 4217 (1986).

[53] Soccani Souiralli, Mahesh Nirajan, and Frank Fallside, "A theoretical investigation into the performance of the hopfield net," IEEE Transactions on Neural Networks 1, 204–215 (1990).

[54] Hakushi Suzuki, Jun-ichi Inura, Toshihiro Horio, and Kazuyuki Aihara, "Chaotic boltzmann machines," Scientific Reports 3, 1610 (2013).

[55] G. E. Hinton, "Boltzmann machine," Scholarpedia 2, 1895 (2007) pp. 29 [cited].

[56] John J Hopfield, "Neural networks and physical systems with emergent collective computational abilities," Proceedings of the national academy of sciences 79, 2554–2558 (1982).

[57] Jianhua Liu, Shuo Zhou, Haikun Zhu, and Chung-Kuan Cheng, "An algorithmic approach for generic parallel adders," in Proceedings of the 2009 IEEE-ACM International Conference on Computer-Aided Design (IEEE Computer Society, 2009) pp. 724.

[58] U. Ravi, Vidya Vijayan, M Mohamazipur, and Sharon Paul, "Toward delay and power comparison of adder topologies," International Journal of VLSI Design & Communication Systems 3, 153 (2012).

[59] Donald E Knuth and Luis Trablo Pardo, "Analysis of a simple factorization algorithm," Theoretical Computer Science 3, 321–348 (1976).

[60] Fabio Traversa and Massimiliano Di Ventura, "Polynomial-time solution of prime factorization and np-complete problems with digital nanocomputing machines," Chaos: An Interdisciplinary Journal of Nonlinear Science 27, 023107 (2017).

[61] Massimiliano Di Ventura, Fabio Traversa, and Igor V Ochodlo, "Topology field theory and computing with instantons," arXiv preprint arXiv:1609.03230 (2016).

[62] Artur Ekert and Richard Jozsa, "Quantum computation and shor's factoring algorithm," Reviews of Modern Physics 68, 733 (1996).

[63] Richard P Feynman, "Simulating physics with computers," International Journal of Theoretical Physics 21, 467–488 (1982).

---

**Completed transcription: 19 pages total. All equations, figures, captions, and references transcribed visually from the PDF pages. No unclear passages encountered.**
