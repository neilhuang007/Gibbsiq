# Thermodynamic significance of QUBO encoding on quantum annealers

**Authors:**
Emery Doucet¹,²,³,* Zakaria Mzaouli⁴,⁵,† Reece Robertson⁶,²,³
Bartlomiej Gardas,⁷ Sebastian Deffner²,³,⁸ and Krzysztof Domino⁹,†

**Affiliations:**
¹Department of Physics, University of Massachusetts, Boston, Boston, MA 02125, USA
²Department of Physics, University of Maryland, Baltimore County, Baltimore, MD 21250, USA
³Quantum Science Institute, University of Maryland, Baltimore County, Baltimore, MD 21250, USA
⁴Institut für Theoretische Physik, Universität Tübingen,
   Auf der Morgenstelle 14, 72076 Tübingen, Germany
⁵Jülich Supercomputing Centre, Institute for Advanced Simulation,
   Forschungszentrum Jülich, Wilhelm-Johnen-Straße, Jülich, 52428, Germany.
⁶Department of Computer Science and Electrical Engineering,
   University of Maryland, Baltimore County, Baltimore, MD 21250, USA
⁷Institute of Theoretical and Applied Informatics,
   Polish Academy of Sciences, Baltycka 5, Gliwice, 44-100, Poland
⁸National Quantum Laboratory, College Park, MD 20740, USA

## Abstract

Quadratic unconstrained binary optimization (QUBO) is the standard interface to quantum annealers, yet a single constrained task admits many QUBO encodings whose penalty choices reshape the energy landscape experienced by hardware. We study a Job Shop Scheduling instance using a two-parameter family of encodings controlled by penalty weights $p_{\text{sum}}$ (one-hot/sum constraints) and $p_{\text{pair}}$ (precedence constraints). Sweeping the $(p_{\text{sum}}, p_{\text{pair}})$ plane, we observe sharp transitions in feasibility and solve success across classical annealing-inspired heuristics and on a D-Wave Advantage processor. Going beyond solution probability, we treat the annealer as an open thermodynamic system and perform cycle-reversal annealing experiments initialized from thermal samples, measuring the stochastic process energy change. From the first two moments of this energy change we infer lower bounds on entropy production, work, and heat via thermodynamic uncertainty relations, and corroborate the observed trends with adiabatic master equation simulations. We find that the same encoding transitions that govern computational hardness also reorganize dissipation: weak penalties generate low-energy infeasible manifolds, while overly strong penalties suppress the effective problem scale and increase irreversibility, reducing the thermodynamic efficiency. Our results establish QUBO penalties as thermodynamic control knobs and motivate thermodynamics-aware encoding strategies for noisy intermediate-scale quantum annealers.

## I. INTRODUCTION

Quantum annealing (QA) provides a hardware-native route to solving discrete optimization problems by encoding them into the low energy state of an Ising Hamiltonian and approximately preparing that ground state through a driven open system evolution [1-7]. Over the last decade, programmable superconducting annealers have grown to thousands of coupled qubits with improving connectivity and control, enabling systematic studies of combinatorial workloads under finite temperature, noise, and calibration constraints [8]. A broad range of practical tasks—including scheduling, routing, and resource allocation—can be expressed in the standard quadratic unconstrained binary optimization (QUBO) form and mapped to the Ising model implemented on these devices [9, 10]. This practical expressivity has motivated extensive benchmarking efforts and fueled interest in whether QA can yield computational advantage for optimization [11-13].

At the same time, it is increasingly clear that runtime-based narratives of "quantum advantage" in optimization are difficult to make robust on present-day devices. Reported speedup can depend sensitively on the performance metric, the choice of classical baseline, and, critically, on how one accounts for end-to-end overhead such as programming, readout, thermalization, compilation/transpilation, and hybrid post-processing. Recent reassessments emphasize that on-device hardware overhead is the separation between "pure compute" time and overhead is often not experimentally clean, so omitting these contributions can systematically bias comparisons [14, 15]. This does not diminish the scientific value of QA as a controllable many-body open quantum system, but it motivates broadening the notion of "performance" beyond time-to-solution range [16].

One natural complementary axis of interest is cost: how much work must be invested, how much heat is dissipated, and how irreversible is the physical process that produces candidate solutions [17-22]. Unlike idealized simulations, these thermodynamic quantities are intrinsic to the device-level dynamics and directly reflect the interplay between driving, dissipation, and the encoded energy landscape [23]. Thermodynamic observables can therefore serve as a hardware-grounded diagnostic of why certain problem encodings succeed or fail.

and they can inform encoding strategies aimed at reducing dissipation and improving robustness to noise. In this work we adopt the viewpoint that quantum computers are thermodynamic machines characterized by work, heat, entropy production, and thermodynamic efficiency inferred from experimentally accessible statistics [24-26].

A central practical challenge in QA is that many real-world tasks are naturally formulated as constrained optimization problems, whereas QUBO is unconstrained [27]. Although other methods exist (e.g., [28]), constraints are typically encoded by adding penalty terms with tunable weights. Even for a fixed problem, there is rarely a unique QUBO penalty choice: different structure and penalty magnitude can encode the same feasible optimum while producing markedly different spectra, degeneracies, and barrier structures [29]. Since annealers operate at finite temperature with control noise and limited coefficient ranges, these encoding choices can strongly affect both (i) the probability of recovering feasible near-optimal solutions and (ii) the dissipative cost of the annealing dynamics [30, 31]. Thus, QUBO design is not merely a mathematical preprocessing step but a physically consequential design choice that controls both computational hardness and hardware dynamics [32-34].

Here we make this conception concrete using a Job Shop scheduling problem as a representative constrained workload [35]. We introduce a two-parameter family of QUBO encodings controlled by penalty weights $p_{\text{sum}}$ (one-hot/sum constraints) and $p_{\text{pair}}$ (precedence constraints), and map the resulting encoding space both to solver performance and thermodynamic signatures. On the computational side, we identify sharp regime boundaries separating feasible and infeasible ground states and quantify how these boundaries manifest across classical annealing-inspired solvers and on a D-Wave Advantage processor.

On the thermodynamic side, we extract bounds on entropy production, work, and heat from reverse-annealing experiments using thermodynamic uncertainty relations [36-38], and we complement these measurements with open-system simulations of the annealing dynamics. We show that encoding-induced rearrangement of the energy landscape produce distinct thermodynamic regimes, and that the encoding choices associated with "hard" optimization behavior also correlate with increased dissipation and reduced thermodynamic efficiency. This establishes thermodynamics as an operational lens for understanding and improving QUBO encodings on noisy intermediate-scale quantum annealers.

The outline of this manuscript is as follows. In Sec. II, we introduce the notion of a Job Shop scheduling problem (JSP), a very important class of scheduling problem which we use as a test case throughout this work. In Sec. III, we apply several classical simulated-annealing-type solvers to our problem and show how the penalty parameter space is divided into distinct regions. Section IV gives a description of the thermodynamics of quantum annealing.

## II. JOB SHOP PROBLEM

The Job Shop scheduling problem is a fundamental optimization problem in which multiple jobs undergo a sequence of operations on specific machines under strict precedence and resource constraints [35, 39]. Its practical relevance is demonstrated extensively in manufacturing and production systems, where efficient sequencing of machining and assembly tasks is critical for throughput and cost reduction [40]. JSP principles also underlie planning in complex industrial environments, such as semiconductor fabrication, where thousands of operations must be coordinated on limited equipment [41].

Similar structured sequencing constraints occur in aircraft maintenance, where tasks must be executed on limited facilities and in prescribed orders to ensure operational reliability [42]. Recent manufacturing, Job Shop-type formulations appear naturally in transportation systems, including railway traffic and rescheduling problems, where trains must traverse shared infrastructure while respecting ordered procedures and resource conflicts. The problem is even more interesting in real-time railway rescheduling. When disruptions occur, tasks such as reallocating trains, reordering trains, adjusting meet–pass decisions, or restoring circulation plans require resolving conflicts akin to dynamic Job Shop scheduling under uncertainty. Recovery optimization methods explicitly draw on sequencing and resource-allocation principles from JSP to ensure operational feasibility and minimize delay propagation across the network [44]. Here, the quantum devices are good candidates to handle such problems, as they are, by nature, noisy and prone to errors [3, 5]. Henceforth, assessing the nature of the noise of such (stochastic) solvers is crucial in handling practical scheduling or rescheduling problems under uncertainty.

Let us now introduce the Job Shop problem from the mathematical point of view of scheduling theory [35]. We consider a Job Shop problem with release times ($r_j$) and deadline constraints ($d_j$), where the objective is the total weighted tardiness $\sum_j w_j T_j$, namely:

$$J_m [r_j d_j] \sum_j w_j T_j. \tag{1}$$

Each job has its own schedule corresponding to the sequence of machines it must be processed on, and each machine can process one job at a time (i.e., sometimes jobs have to wait in the buffer before the machine is free).

### A. QUBO Formulation

The standard methodology used when solving a Job Shop problem classically involves representing the problem as an integer linear programming (ILP) problem [35]. (For details on this approach, see Appendix A). For quantum solvers however, the most natural representation used to solve optimization problems is as a quadratic unconstrained binary optimization (QUBO) problem.

Following Ref. [47], we may derive the QUBO directly from the Job Shop problem using a vector $\vec{x}$ of binary decision variables $x_{m,t}$, defined so that job $j$ completes on machine $m$ at time $t$ if and only if 0 otherwise. A detailed construction of the QUBO associated with our Job Shop problems is provided in Appendix B. In summary, the various constraints in the original problem are represented as penalty terms of the form

$$p_{\text{sum}} \sum_{m,j} \left( \sum_{\ell,\ell' \neq \ell} x_{m,j,\ell} - \sum_{\ell} x^2_{m,j,\ell} \right) \tag{2}$$

Release constraints are the earliest possible times jobs may be submitted to the first machine in their schedule, and deadline constraints are the times at which the job must have been processed with all requisite machines. Beyond the deadline, each job should be performed as soon as possible to minimize the weighted tardiness objective. This type of scheduling problem is generally NP-hard [46].

**TABLE I.** Job Shop scheduling benchmark instances used in this work. For each instance we report the number of binary decision variables in the corresponding QUBO formulation (denoted as "#-qubits"), the number of jobs $J$ and machines $M$, the job-specific release times $r_j$, deadlines $d_j$, and tardiness weights $w_j$ (listed in order of job index $j = 1,...,J$). The final column gives the optimal objective value of the original constrained Job Shop problem, defined as the minimum total weighted tardiness $\sum_j w_j T_j$, and serves as the ground-truth reference for evaluating solver performance.

| #-qubits | #-jobs | #-machines | $r_1, ..., r_J$ | $d_1, ..., d_J$ | $w_1, ..., w_J$ | opt. obj. |
|----------|--------|------------|-----------------|-----------------|-----------------|-----------|
| 4        | 2      | 1          | 1, 1            | 3.3             | 1.0,5           | 0.5       |
| 5        | 2      | 1          | 1, 1            | 3.4             | 1.0,5           | 0.25      |
| 6        | 2      | 2          | 1, 1            | 4.3             | 1.0,5           | 0.5       |
| 8        | 2      | 3          | 1, 1            | 4.4             | 1.0,5           | 0.5       |
| 10       | 2      | 2          | 1.2             | $t_f, t_f$      | 1.4             | 0.5       |

and

$$p_{\text{pair}} \sum_i (x_i x_i' + x_i x_i'), \tag{3}$$

included in the objective function of the QUBO. Combined with the original weighted tardiness cost function of the original problem, the objective function is a purely linear contribution to the QUBO,

$$\text{objective}(\vec{x}) = \sum \sum w_j^{\prime} t x_{j,m_j,\text{end}} - \text{offset}. \tag{4}$$

For details on the bounds on these sums and on exactly which terms appear, see Appendix B. What is important here is the structure of the terms.

The Job Shop instances (each job has a predefined sequence of machines) are presented in Tab. I. Various values of $w_j$ yield various job priorities.

## B. Parameter regimes

Structurally, the Job Shop problem we have defined in the previous section remains exactly the same as we vary the penalty parameters $p_{\text{sum}}$ and $p_{\text{pair}}$ used to embed the original constrained optimization problem in QUBO form. That said, there are distinguished points in the parameter space where important changes occur in the nature of the solution to the QUBO or to the encoding regimes. The difficulty in solving the QUBO may potentially be quite different in the different regions of the parameter space, and hence these transitions could be visible in the performance metrics used to benchmark QUBO solvers.

As an example, take the problem instance with 8 variables. For this case, the solution to the QUBO is not a feasible solution to the original Job Shop problem due to constraint violations unless the penalty values are sufficiently large, $p_{\text{sum}} > 0.5$ and $p_{\text{pair}} > 0.25$. This is demonstrated in the left panel of Fig. 2, where the difference between the best feasible solution and the best infeasible solution is plotted showing the clear separation of the parameter space into two regions. Another demarcation not directly related to the optimal solution is plotted in the right panel of Fig. 2, showing the difference between the best infeasible solution and the worst feasible solution. Again we find the parameter space can be split into two regions, one where all feasible solutions have lower objective values than all infeasible solutions and one where they mix. Intuitively this might be expected to change the difficulty of achieving a high-quality solution for annealing-based QUBO solvers. See Sec. III for details on solver performance.

One interesting detail of these plots is that they are not symmetric between $p_{\text{sum}}$ and $p_{\text{pair}}$. This is a consequence of fundamental difference between how the two penalty types interact with the objective function and hence in the efficacy and hierarchy in solving the problem. For this reason, we expect that $p_{\text{sum}}$ should have a larger impact on solver performance (and other proxies for difficulty of the QUBO) than the other penalty terms proportional to $p_{\text{pair}}$.

Physically, annealer devices work with the Ising problem associated with a QUBO problem. The binary decision variables $\vec{x}$ are replaced with spins $s = 2\vec{x} - 1$ taking values in $\{-1,1\}$, producing an energy function to be minimized,

$$E_{\text{Ising}}(s) = \sum_i h_i s_i + \frac{1}{2} \sum_{i \neq i'} J_{ii'} s_i s_i', \tag{5}$$

where the local fields $h_i$ are built from the linear and quadratic part of the binary optimization problem (by linear transformation), and the couplings $J_{ii'}$ from the quadratic part [1]. Zero values of local fields yield degeneracy in the ground state. Henceforth, we expect some linear partial for small $p_{\text{sum}}$ and $p_{\text{pair}}$ on adiabatic master equation simulations.

Such patterns are expected to pinpoint some positive $p_{\text{sum}}$ at zero gap to the presence of the positive objective diagonal terms in Eq. (4), i.e., in the original QUBO form.

## III. BEHAVIOR OF CLASSICAL SOLVERS

We expect that the different regions of the parameter space for a given problem instance will cause solvers to exhibit different behavior, though precisely what differences arise and how important they are will certainly depend on the solver implementation. The most straightforward test of this expectation with any given solver is to perform a two-dimensional parameter sweep across $p_{\text{sum}}$ and $p_{\text{pair}}$, and plot the solution accuracy at each point.

We performed this test using three classical QUBO solvers provided by the D-Wave Ocean SDK [49] with their default settings, one based on simulated annealing and two based on simulated quantum annealing (referred to as "path integral annealing" and "rotor model annealing"). These three specific solvers were chosen for two reasons: first, they are all inspired by the physical annealing process and so will provide an interesting comparison for the results we obtain with quantum annealing; secondly, despite the simplicity and small size of the problem instances we tested with they do not always obtain the optimal solution and hence the solution accuracy is reasonably varied—an important consideration as obtaining the optimal solution for quantum-annealing solvers when performing a parameter sweep is difficult because the solution accuracy varies strongly.

## IV. THERMODYNAMICS OF QUANTUM ANNEALING

### A. Experimental estimation

The dynamics of the D-Wave quantum annealer are well approximated by a transverse-field Ising Hamiltonian given by

$$H(s) = A(s) H_{\text{init}} + B(s) H_{\text{cost}}$$

$$= -A(s) \left( \sum_i \sigma_i^x \right) + B(s) \left( \sum_i h_i \sigma_i^z + \sum_{(i,j)} J_{ij} \sigma_i^z \sigma_j^z \right), \tag{6}$$

where:

- $s \in [0,1]$ is the dimensionless annealing parameter controlled by the user via an annealing schedule.

- $A(s)$ is the transverse-field energy scale, and $B(s)$ is the problem (Ising) energy scale.

- $\sigma_i^z$ are Pauli operators acting on qubit $i$ with eigenvalues $\pm 1$.

- $h_i$ are programmable local fields and $J_{ij}$ are programmable Ising couplings on the hardware graph.

We work in energy units such that the overall scale is dimensionless; in particular, we identify $A(s) = \Gamma[1-s]$ and $B(s) = s$ for simplicity.

The control parameter is steered as a function of physical time $t$ via an annealing schedule $s(t)$,

$$s_F(t) = \frac{t}{\tau}, \quad 0 \leq t \leq \tau. \tag{7}$$

In this work we exploit reverse annealing, which allows us to initialise the device in a chosen classical spin configuration at $s = 1$, reduce the transverse field by decreasing $s$ to a minimum value $s_{\min}$, then return to $s = 1$. The reverse-anneal schedule used in the experiments is a symmetric piecewise linear protocol

$$s(t) = \begin{cases} 1 - 2(1 - s) \frac{t}{\tau}, & 0 \leq t \leq \frac{\tau}{2} \\ -1 + 2s + 2(1 - s) \frac{t}{\tau}, & \frac{\tau}{2} \leq t \leq \tau, \end{cases} \tag{8}$$

so that $s(0) = s(\tau) = 1$ and $s(\tau/2) = s$.

We modeled the processor as initially prepared in a classical Gibbs state at inverse temperature $\beta_1$ with respect to the problem Hamiltonian at $s = 1$. Concretely, for a classical spin configuration $\{\sigma_i^z\}$, the corresponding Ising energy is

$$E_z(\{\sigma_i^z\}) = \sum_i h_i \sigma_i^z + \sum_{(i,j)} J_{ij} \sigma_i^z \sigma_j^z. \tag{9}$$

A thermal sample at inverse temperature $\beta_1$ is generated by drawing configurations with probability

$$p_{\beta_1}(\{\sigma_i^z\}) = \frac{e^{-\beta_1 E_z(\{\sigma_i^z\})}}{Z(\beta_1)}, \quad Z(\beta_1) = \sum_{\{\sigma_i^z\}} e^{-\beta_1 E_z(\{\sigma_i^z\})}. \tag{10}$$

On the hardware, the initial configuration is imposed at $s = 1$ using D-Wave's reverse annealing API ("initial_state" plus a custom "anneal_schedule"), so that the system begins in a classical state with energy $E_1 = \langle E_1 \rangle$.

For a cyclic schedule such as the reverse anneal Eq. (8), the joint statistics of the energy changes $\Delta E_1$ of the processor and $\Delta E_2$ of the environment obey the multivariate fluctuation theorem

$$\mathbb{P}(\Delta E_1, \Delta E_2) = \exp(\beta_1 \Delta E_1 + \beta_2 \Delta E_2). \tag{13}$$

This is understood with respect to a two-projective energy measurement scheme at the beginning and end of the protocol.

Defining the stochastic total entropy production as

$$\Sigma = \beta_1 \Delta E_1 + \beta_2 \Delta E_2, \tag{14}$$

we obtain from (13) the second-law inequality

$$\langle \Sigma \rangle = \beta_1 \langle \Delta E_1 \rangle + \beta_2 \langle \Delta E_2 \rangle \geq 0. \tag{15}$$

Identifying the average heat absorbed by the processor from the environment with $\langle Q \rangle = -\langle \Delta E_2 \rangle$, and the average work performed on the processor + bath compound by the external controller with

$$\langle W \rangle = \langle \Delta E_1 \rangle + \langle \Delta E_2 \rangle, \tag{16}$$

one can classify the operation mode (refrigerator, engine, accelerator, heater) from the signs of $(\Delta E_1)$, $\langle Q \rangle$ and $\langle W \rangle$.

In practice, the environment energy change $\Delta E_2$ is not directly measurable on the D-Wave device, and the only experimentally accessible observable is the processor energy change $\Delta E_1$. To extract information about heat production, heat, and work from $\Delta E_1$ alone, we exploit a thermodynamic uncertainty relation (TUR). Consider a joint distribution $p(\sigma, \phi)$ satisfying

$$\frac{p(\sigma, \phi)}{p(-\sigma, -\phi)} = e^{\sigma}, \tag{17}$$

then the TUR implies the bound

$$\langle \phi \rangle \geq 2 g \left( \frac{\langle \phi \rangle}{\sqrt{\langle \phi^2 \rangle}} \right), \quad g(x) = x \tanh^{-1}(x). \tag{18}$$

By choosing $\sigma = \Sigma$ and $\phi = \Delta E_1$ we obtain the lower bound on the average entropy production

$$\langle \Sigma \rangle \geq 2 g \left( \frac{\langle \Delta E_1 \rangle}{\sqrt{\langle \Delta E_1^2 \rangle}} \right). \tag{19}$$

Combining (19) with the definitions of $\langle Q \rangle$ and $\langle W \rangle$ yields bounds on the average heat and work

$$-\langle Q \rangle \geq \frac{2}{\beta_2} g \left( \frac{\langle \Delta E_1 \rangle}{\sqrt{\text{var}(\Delta E_1)}} \right) - \frac{\beta_1}{\beta_2} \langle \Delta E_1 \rangle, \tag{20}$$

$$\langle W \rangle \geq \frac{2}{\beta_2} g \left( \frac{\langle \Delta E_1 \rangle}{\sqrt{\text{var}(\Delta E_1)}} \right) + \left( 1 - \frac{\beta_1}{\beta_2} \right) \langle \Delta E_1 \rangle, \tag{21}$$

where $\text{var}(\Delta E_1) = \langle \Delta E_1^2 \rangle - \langle \Delta E_1 \rangle^2$. The thermodynamic efficiency follows as:

$$\eta = -\frac{\langle W \rangle}{\langle Q \rangle}. \tag{22}$$

Thus, by measuring only the first two moments of $\Delta E_1$ for each reverse annealing schedule, we obtain lower bounds on the average entropy production, heat exchanged with the environment, and work performed by the driving.

The thermodynamic bounds (19)-(21) depend on the bath inverse temperature $\beta_2$, which is not directly provided by the hardware. We estimate $\beta_2$ from the final state statistics by treating the measured spin configurations as approximate samples of the classical Ising model at some effective temperature.

### B. Simulation and Numerical Estimation

To simulate the quantum annealing process, we employed the stochastic master equation as developed in Refs. [52], with the annealing Hamiltonian as given in Eq. (6). For forward annealing the annealing parameter $s$ increases linearly as $t/\tau$ with $t$ being the annealing time, while for reverse annealing $s$ decreases linearly from 1 to some specified $0 < s_{\min} < 1$ then returns to 1. In simulations, the Hamiltonians are interpolated from the table provided by D-Wave describing the annealing schedule implemented on their hardware [53].

In simulation, we employ control over the initial state input into the annealing process. We use thermal states at a configurable inverse temperature $\beta$ for forward annealing defined using the mixer Hamiltonian $H_{\text{mix}}$ and for reverse annealing defined using the cost Hamiltonian $H_{\text{cost}}$.

Once the initial state has been chosen and the annealing schedule has been finalized, the simulation proceeds by integrating the master equation over a series of small fixed intervals $\delta t = \tau/N$ using tight numerical tolerances to

compute a series of density matrices $\rho(t_k)$ giving the state of the system throughout the annealing process. This is a noisy simulation, so the annealing process is simulated assuming that the qubits are in weak contact with some bath.

Following Ref. [52], the qubits are weakly-coupled to an Ohmic bath with an interaction strength of $10^{-4}$, a cutoff frequency of 4 GHz at a temperature of 16 mK, which is reasonable for comparison to D-Wave's quantum annealers [54, 55]. This time series is then post-processed to reconstruct the thermodynamic quantities in which we are interested.

Computing bounds on the entropy production, heat flux, and work using the thermodynamic uncertainty relation from our simulated results is straightforward. The initial temperature $\beta$ and environment temperature $T_{\text{env}}$ are known, so all that needs to be computed are the expected first and second moments of the energy change, $(\Delta E)$ and $\langle \Delta E^2 \rangle$. Given the initial and final states $\rho(0)$ and $\rho(\tau)$ along with the initial and final Hamiltonians $H(0)$ and $H(\tau)$, these values are computed as

$$\langle \Delta E \rangle = \text{tr}[H(\tau)\rho(\tau)] - \text{tr}[H(0)\rho(0)], \tag{25a}$$

$$\langle \Delta E^2 \rangle = \text{tr}[H(\tau)^2\rho(\tau)] + \text{tr}[H(0)^2\rho(0)] - 2\text{tr}[H(\tau)\rho(\tau) \text{tr}[H(0)\rho(0)]]. \tag{25b}$$

A more detailed analysis of the simulation output allows the change in entropy, heat, and work across each time step to be estimated directly. The easiest of these three quantities to estimate is the entropy production, which we calculate by simply computing the change entropy between each pair of simulated output:

$$\Sigma(t_k) \delta t = - \text{tr}[\rho(t_{k+1}) \log \rho(t_{k+1})] + \text{tr}[\rho(t_k) \log \rho(t_k)], \tag{26}$$

The heat and work flux in each timestep are somewhat more complex to compute. Given the initial and final states of any timestep $\rho(t_k)$ and $\rho(t_{k+1})$, we can easily compute the total change in energy which incorporates both heat and work which we must disentangle. We can always write a quantum map which represents the time evolution across this timestep,

$$\rho(t_{k+1}) = \mathcal{E}_{t_{k+1},t_k}[\rho(t_k)]. \tag{28}$$

which we approximate as being built from the composition of two separate quantum maps,

$$\rho(t_{k+1}) \approx \mathcal{V}_{t_{k+1},t_k} \circ \mathcal{U}_{t_{k+1},t_k}[\rho(t_k)]. \tag{29}$$

## V. RESULTS

### A. Experimental results

Figures 4 to 6 report the experimentally inferred thermodynamic observables for the 10-qubit Job Shop instance implemented on the D-Wave Advantage processor under reverse annealing. For each encoding point ($p_{\text{sum}}, p_{\text{pair}}$), we prepare initial classical configurations from a Gibbs distribution at inverse temperature $\beta_1$ with respect to the programmed Ising cost Hamiltonian at

$s = 1$, execute the cyclic reverse-anneal schedule down to a minimum $s$ and back, and record the stochastic process energy change. From the first two moments of $\Delta E_1$ we compute the TUR-based lower bound on the average entropy production (19) and the bounds on work (21) and heat (20), using an effective bath inverse temperature $\beta_2$ estimated from pseudo-likelihood estimation (24). While these quantities are bounds (rather than direct calorimetric measurements), they depend quantitatively on the first two moments of $\Delta E_1$ and serve as the ground-truth reference for evaluating solver performance.

Across all three minimum annealing points $s$ (before, near, and after the discrete quantum critical region), the maps in Figures 4 to 6 exhibit a pronounced separation between a low-$p_{\text{sum}}$ regime and a higher-$p_{\text{sum}}$ regime. This is the thermodynamic counterpart of the "feasible vs. infeasible" and "split vs. unsplit" boundaries noted spectrally and algorithmically in Figures 2 and 3:

when constraint penalties are too weak, low-energy infeasible configurations proliferate and dominate the low-energy landscape, whereas sufficient strong penalties lift the infeasible manifold and isolate the feasible optimum. In the thermodynamic data, this transition manifests not primarily as a change in a single scalar, but as a coordinated reorganization simultaneously of (i) which states are visited and (ii) how strongly the dynamics couple to the environment.

The observed asymmetry between $p_{\text{sum}}$ and $p_{\text{pair}}$ is expected on structural grounds: the $p_{\text{sum}}$ penalty contributes iteratively and diagonal terms about from pairwise-penalty structure, so too-small $p_{\text{sum}}$ can be "overruled" by objective contributions, yielding a qualitatively altered spectrum with increased degeneracy and mixed feasible/infeasible ordering. Thermodynamically, increased degeneracy near the bottom of the spectrum while work and heat bounds are enhanced.

Panel (a) measures whether the processor typically returns to $s = 1$ at a lower or higher Ising energy than it started with. In the weak-$p_{\text{sum}}$ regime, $\langle \Delta E_1 \rangle$ is comparatively uniform, consistent with a landscape where constraint violations allow many low-lying barriers to lower-lying boundaries and the feasibility boundary is noised spectrally and algorithmically in Figures 2 and 3; lower as feasible regions, $(\Delta E_1)$ is comparatively uniform, consistent with a landscape where constraint violations are absent, and where the system is trapped near the initial condition with little net change.

As $p_{\text{sum}}$ increases, the feasible regime, $(\Delta E_1)$ shows more strongly bounded and becomes spatially structured, reflecting the emergence of a constrained manifold and a modified set of relaxation pathways. Importantly, the same encoding transitions that govern computational hardness also reorganize dissipation: weak penalties generate low-energy infeasible manifolds, while overly strong penalties suppress the effective problem scale and increase irreversibility, reducing the thermodynamic efficiency. Our results establish QUBO penalties as thermodynamic control knobs and motivate thermodynamics-aware encoding strategies for noisy intermediate-scale quantum annealers.

enhancements the density of near-resonant transitions and provides more channels for both-induced transitions during the protocol, which raises irreversibility and reshapes the balance between work-heat driving costs and heat exchange. This explains why the most visible boundaries in the thermodynamic observables run predominantly along the $p_{\text{sum}}$ axis, whereas variation in $p_{\text{pair}}$ mainly modulates these features. The clean boundaries and sharp transitions in Figures 2 and 3 arise from idealized access to the encoded solution spectrum, while $s$ controls which position of that spectrum is dynamically relevant before freeze-out.

The clean boundaries and sharp transitions in Figures 2 and 3 arise from idealized access to the encoded solution spectrum, while $s$ controls which position of that spectrum is dynamically relevant before freeze-out.

**FIG. 4.** Thermodynamics of the Job Shop problem on D-Wave Advantage before the critical region ($s = 0.15$). Job Shop (10 qubits) encoded via reverse annealing on the D-Wave Advantage system. The processor is initialized in a classical Gibbs state at inverse temperature $\beta_1 = 10$ and reverse annealed for $t_a = 10 \mu s$ down to $s = 0.15$ (before the quantum critical region) and back to $s = 1$. Each panel is plotted versus the QUBO penalty weights ($p_{\text{sum}}$, $p_{\text{pair}}$) controlling precedence and one-hot constraints. (a) mean processor energy change $(\Delta E_1) = (E_{1,f} - E_{1,i})$; (b) TUR-based lower bound on the average entropy production (19); (c) work bound (21); (d) heat bound (20); (e) thermodynamic efficiency (22) (f) effective bath inverse temperature $\beta_2$ obtained from pseudo-likelihood estimation (24). The maps reveal a pronounced regime boundary driven primarily by $p_{\text{sum}}$, emphasizing the energetic landscape and operator dissipation (entropy/work/heat) and efficiency, directly demonstrating that QUBO encoding parameters act as thermodynamic control knobs on hardware.

**FIG. 5.** Thermodynamics of the Job Shop problem on D-Wave Advantage near the critical region ($s = 0.27$). Job Shop (10 qubits) encoded via reverse annealing on the D-Wave Advantage system. The processor is initialized in a classical Gibbs state at inverse temperature $\beta_1 = 10$ and reverse annealed for $t_a = 10 \mu s$ down to $s = 0.27$ (near the quantum critical region) and back to $s = 1$. Each panel is plotted versus the QUBO penalty weights ($p_{\text{sum}}$, $p_{\text{pair}}$) controlling precedence and one-hot constraints. (a) mean processor energy change $(\Delta E_1) = (E_{1,f} - E_{1,i})$; (b) TUR-based lower bound on the average entropy production (19); (c) work bound (21); (d) heat bound (20); (e) thermodynamic efficiency (22); (f) effective bath inverse temperature $\beta_2$ obtained from pseudo-likelihood estimation (24). The maps reveal a pronounced regime boundary driven primarily by $p_{\text{sum}}$, emphasizing the energetic landscape and operator dissipation (entropy/work/heat) and efficiency, directly demonstrating that QUBO encoding parameters act as thermodynamic control knobs on hardware.

**FIG. 6.** Thermodynamics of the Job Shop problem on D-Wave Advantage after the critical region ($s = 0.35$). Job Shop (10 qubits) encoded via reverse annealing on the D-Wave Advantage system. The processor is initialized in a classical Gibbs state at inverse temperature $\beta_1 = 10$ and reverse annealed for $t_a = 10 \mu s$ down to $s = 0.35$ (after the quantum critical region) and back to $s = 1$. Each panel is plotted versus the QUBO penalty weights ($p_{\text{sum}}$, $p_{\text{pair}}$) controlling precedence and one-hot constraints. (a) mean processor energy change $(\Delta E_1) = (E_{1,f} - E_{1,i})$; (b) TUR-based lower bound on the average entropy production (19); (c) work bound (21); (d) heat bound (20); (e) thermodynamic efficiency (22); (f) effective bath inverse temperature $\beta_2$ obtained from pseudo-likelihood estimation (24). The efficiency becomes comparatively uniform across encoding space with the work bounds seen to grow in magnitude, consistent with a more classical-frozen-out dominated by dissipation set by the effective temperature $\beta_2$. Together with Figures 4 and 5, these results show that both the encoding parameters ($p_{\text{sum}}, p_{\text{pair}}$) and the dynamical operating point $s$ determine the irreversibility and energetic cost of quantum annealing.

Panel (a) measures whether the processor typically returns to $s = 1$ at a lower or higher Ising energy than it started with. In the weak-$p_{\text{sum}}$ regime, $\langle \Delta E_1 \rangle$ is comparatively uniform, consistent with a landscape where constraint violations allow many low-lying barriers to lower-lying boundaries; in the strong-$p_{\text{sum}}$ regime near the feasible region, $\langle \Delta E_1 \rangle$ shows more strongly bounded and becomes spatially structured, reflecting the emergence of a constrained manifold and a modified set of relaxation pathways. Importantly, as $p_{\text{sum}}$ increases, the feasible region, $(\Delta E_1)$ shows more strongly changes more strongly and becomes spatially structured, reflecting the emergence of a constrained manifold and a modified set of relaxation pathways.

Panel (c) reports the work bound (21) obtained with the bound on work heat bounds in panels (c), (d), indicating that the encoding-controlled spectrum transitions reorganize dissipation and entropy production. We do not see strong features corresponding to transitions in the optimization problem as might be expected from the solution probabilities of Fig. 7, however this agrees with the fact that we do not see such features in our experimental results. Importantly, this indicates that we can use results obtained with TUR-based estimates of thermodynamic quantities obtained with reverse annealing (the limit of what is possible with current-generation devices) to shed light on the overall thermodynamics of both the forward and reverse annealing processes and how they might depend on penalty and embedding parameters.

Additionally, when we look at more fine-grained thermodynamic quantities of excess work and energy, we are able to see features corresponding to level crossings and transitions in the identity of the ground states of the Ising model. In fact, we see more transitions than just those corresponding to the feasible-infeasible transition. Faint features correspond to degeneracies and crossings of higher-lying levels and points where various subgaps are close—similar to level structures visible in the solution probabilities of the classical solvers from Fig. 3. This shows that while we do not see strong indications of detailed structure of the solution probability of the quantum annealer, such details do still affect the quantum annealing process and how difficult the problem is to solve. The effect is simply much weaker, again hinting that quantum annealing may be less sensitive to such details as compared to classical annealing solvers.

One important difference between the simulation results and the results of the three classical solvers tested earlier, but that should not be surprising as we simulated forward annealing of a much smaller problem than was tested on the real device. Qualitatively, we observe the same general structure: for the overall annealing process, the sum penalty terms have a far more pronounced effect than the pair penalty terms. We do not see strong features corresponding to transitions in the optimization problem as might be expected from the solution probabilities of Fig. 7, however this agrees with the fact that we do not see such features in our experimental results. Importantly, this indicates that we can use results obtained with TUR-based estimates of thermodynamic quantities obtained with reverse annealing (the limit of what is possible with current-generation devices) to shed light on the overall thermodynamics of both the forward and reverse annealing processes and how they might depend on penalty and embedding parameters.

Additionally, when we look at more fine-grained thermodynamic quantities of excess work and energy, we are now able to see features corresponding to level crossings and transitions in the identity of the ground states of the Ising model. In left, we see more transitions than just those corresponding to the feasible-infeasible transition. Faint features appear which are visible also in the solution probabilities of the classical solvers from Fig. 3. This shows that while we do not see strong indications of detailed structure of the solution probability of the quantum annealer, such details do still affect the quantum annealing process and how difficult the problem is to solve. The effect is simply much weaker, again hinting that quantum annealing may be less sensitive to such details as compared to classical annealing solvers.

**FIG. 7.** Probability of finding the (left) overall ground state or (right) best feasible solution for the 4 variable instance according to numerical simulations with an initial temperature of $\beta = 10$ and annealing time of $t = 10 ns$.

### B. Simulation results

Figure 7 shows the probabilities of obtaining the ground state of the annealing problem as well as the probability of obtaining the optimal solution to the Job Shop problem. As in the case of the results obtained with the three classical annealing solvers provided by the D-Wave SDK shown in Fig. 3, we find that quantum annealing also shows a sharp drop in the solution probability corresponding to the points where the ground state transitions—points that naturally explains why the most visible boundaries in the thermodynamic observables run predominantly along the $p_{\text{sum}}$ axis, whereas variation in $p_{\text{pair}}$ mainly modulates these features. The clean boundaries and sharp transitions in Figures 2 and 3 arise from idealized access to the encoded solution spectrum, while $s$ controls which position of that spectrum is dynamically relevant before freeze-out.

## VI. CONCLUSION

We established that QUBO encoding is not a neutral preprocessing step, but rather a physically consequential design choice that controls both (i) the computational hardness encountered by a quantum annealer and (ii) the irreversibility and energetic cost of the annealing dynamics.

Focusing on a Job Shop Scheduling instance, we constructed an encoding family parameterized by penalty weights $p_{\text{sum}}$ (one-hot / sum constraints) and $p_{\text{pair}}$ (precedence constraints), and used these parameters as a controlled way to reshape the encoded Ising spectrum. We showed that the ($p_{\text{sum}}, p_{\text{pair}}$) plane naturally separates into distinct encoding regimes, including a feasibility-transition where the QUBO ground state ceases to represent a valid schedule if penalties are too weak, a related "mixed" regime where feasible and infeasible-low-energy states cease to represent a valid schedule, and the more classical region after the critical point (Fig. 6), $s = 0.35$). Near the critical region the instantaneous gap is expected to be smallest and the system most sensitive to both thermal excitation and decoherence, which naturally explains why the most pronounced spatial fluctuations and sign changes in bond-based thermodynamic quantities appear at $s = 0.27$. For $s = 0.35$, the protocol spends less time in the strongly quantum regime and the dynamics are expected to freeze out in a more classical manifold; correspondingly, the efficiency landscape becomes more uniform even though the work bounds can grow in magnitude (partly reflecting the $\beta_2$ normalization in the bounds).

Overall, these results support an operational picture in which encoding controls the spectrum, while $s$ controls which position of that spectrum is dynamically relevant before freeze-out.

The clean boundaries and sharp transitions in Figures 2 and 3 arise from idealized access to the encoded solution spectrum, while $s$ controls which position of that spectrum is dynamically relevant before freeze-out.

Our results also clarify why certain problem encodings succeed and others fail—it is not merely a matter of the one-with largest penalties," but rather the one that balances penalties to (i) enforce feasibility and ensure separation of constraint violations while (ii) maintaining an effective problem energy scale that remains resolvable against hardware noise and decoherence. Our results establish QUBO penalties as thermodynamic control knobs and motivate thermodynamics-aware encoding strategies for noisy intermediate-scale quantum annealers.

## ACKNOWLEDGMENTS

The authors acknowledge the Jülich Supercomputing Centre for providing computing time on the D-Wave Advantage System. JPSN through the Jülich UNified Infrastruture for Quantum Computing (JUNIQ).

E.D. acknowledges U.S. NSF under Grant No. OSI-2325971. K.D. acknowledges Scientific work co-financed from the state budget under the program of the Minister of Science, Poland (of Poland) under the name "Science for Society II" project number NdS-II/SP 038-2023 (1 funding amount 10000000 PLN to the total value of the project 100000 PLN via the webpage https://ncn.gov.pl.

K.D. acknowledges the consultation with the railway operator König Stüssle sp. z o.o. on practical aspects of disturbance mitigation. B.G. acknowledges the Sonata Bis 10 project. No. 2020.38.E-513.0209.

Z.M. acknowledges funding from the Ministry of Economics Affairs, Labour and Tourism Baden-Württemberg in the frame of the Competitive Centre Quantum Computing Baden-Württemberg (project "KQCBW25").

GitHub: https://github.com/QuantumComputingLabUnited/QUBO-encoding-effects-on-quantum-annealing-efficiency

## Appendix A: ILP Encoding

Following the standard encoding of such problems [35] we use the following definitions:

- Let $S_j$ be the schedule of job $j$, i.e. the series of machines it must be processed on.

- Let $p_{j,m}$ be the processing time of job $j$ on machine $m$.

Along with the release times $r_j$, deadlines $d_j$, and weights $w_j$ (listed in order of job index $j = 1, ..., J$). This constitutes a complete definition of a Job Shop problem.

To demonstrate the Job Shop scheme, we encode it as an integer linear programming (ILP) problem—that is, the state-of-the-art approach to such a problem. Hence, we require some additional definitions:

- Let $S_{j,j'}$ be the set of machines used both by $j$ and $j'$.

- Let $\sigma(S_j, m)$ be the machine preceding $m$ in the schedule $S_j$.

- Let $m_{j,\text{start}}$ and $m_{j,\text{end}}$ be the first and last machine of job $j$.

- Let $S_j^\uparrow(m)$ be the schedule of job $j$ up to and including machine $m$ and $S_j^{\downarrow}(m)$ be the remainder such that concatenating $S_j^\uparrow(m)$ and $S_j^{\downarrow}(m)$ produces $S_j$.

The ILP encodings employ the decision variables:

- $t_{j,m} \in \mathbb{Z}^+$ — time job $j$ is finished on machine $m$,

- $p_{j,j',m} \in \{0,1\}$ — precedence variable equal to one if $j$ is performed before $j'$ on machine $m$.

From the definition of a Job Shop scheduling problem, each job must be processed by a series of machines in order. This requirement yields constraints on the decision variables,

$$t_{j,\sigma(S_j,m)} + p_{j,m} \leq t_{j,m}, \quad \forall j \forall m \in S_j (m_j, \text{start}). \tag{A1}$$

Additionally, the fact that each machine can only process a single job at a time produces constraints,

$$t_{j',m} + p_{j',m} \leq M y_{j,j',m} + t_{j,m}, \quad \forall j \neq j' \forall m \in S_{j,j'}. \tag{A2}$$

Here, we use the so-called "big-M encoding" where M is some number chosen to be large enough that the inequality always holds if $y_{j,j',m} = 1$. The minimal M can be computed using the minimal value of $t_{j,m}$, and the maximal value of $t_{j',m}$, which we will discuss later.

The release and deadline constraints yield:

$$r_j + p_{j,m_{\text{start}}} \leq t_{j,m_{\text{start}}}, \quad \forall j, \tag{A3a}$$

$$t_{j,m_{\text{end}}} \leq d_j \quad \forall j. \tag{A3b}$$

We can determine the minimum and maximum values of time variables for each intermediate machine by:

$$t_{\min}(j,m) = r_j + \sum_{m' \in S_j^{\uparrow}(m)} p_{j,m'} \leq t_{j,m}, \quad \forall j \forall m \in S_j, \tag{A4a}$$

$$t_{\max}(j,m) = d_j - \sum_{m' \in S_j^{\downarrow}(m)} p_{j,m'} \geq t_{j,m}, \quad \forall j \forall m \in S_j. \tag{A4b}$$

Finally, the maximal weighted tardiness objective is represented as,

$$\text{objective} = \sum_j w_j t_{j,m_i,\text{end}} - \text{offset}, \tag{A5}$$

where we have introduced

$$w_j' = \frac{w_j}{t_{\max}(j, m_j, \text{end}) - t_{\min}(j, m_j, \text{end})}, \tag{A6a}$$

$$\text{offset} = -\sum_j w_j' t_{\min}(j, m_j, \text{end}). \tag{A6b}$$

Referring to Eq. (A6a) the input from each $t_{j,m_j, \text{end}}$ does not exceed $w_j$.

## Appendix B: QUBO Encoding

In this appendix, we describe how the Job Shop problems studied in the main text are transformed into QUBO problems. We will use the notation introduced in Appendix A, though we do not need to first build an ILP problem to produce a QUBO problem.

One of the key differences which must be overcome in translating a Job Shop scheduling problem into a QUBO is that we must start with a constrained optimization problem and build an equivalent unconstrained optimization problem. We do this by transforming constraints to penalty terms in the objective.

To enforce the release and deadline constraints of a Job Shop problem on our binary decision variables $\vec{x}$, we must impose the constraint that each job completes exactly once in the interval $[t_i]$ (Eq. A.4),

$$t_{\min}(j,m) \sum_{t \in t_{\min}(j,m)}^{t_{\max}(j,m)} x_{j,m,t} = 1 \quad \forall j \forall m \in S_j, \tag{B1}$$

Notice that this is a constraint on the sum of a collection of decision variables. This may be reformulated in terms of penalty terms and encoded in an unconstrained optimization problem [1], which produces terms of the form

$$p_{\text{sum}} \sum \left( \sum_{t \in t_{\text{min}}} x_{m,j,t} x_{m,j,t'} - \sum_t x^2_{m,j,t} \right), \tag{B2}$$

with the precise choice of indices over which the sums run chosen to match with Eq. (B1).

The sequence constraints from Eq. (A1) translate to the decision variables $\vec{x}$ as:

$$\forall j \forall m \in S_j^{\downarrow}(m_j, \text{start})$$

$$x_{j,\ell}, x_{j,m,t} = 0 \quad \forall t_{\min}(j, \sigma) \leq t' \leq t_{\max}(j, m)$$

$$\forall t_{\min}(j, m) \leq t \leq t' + p_{j,m}, \tag{B3}$$

where to save space we have omitted the arguments to $\sigma$. All occurrences are $\sigma(S_j, m)$. The constraint that each machine can work on one job at a time from Eq. (A2) translates to

$$p_{\text{pair}} \sum_{i < i'} (x_i x_i' + x_i x_i'), \tag{B5}$$

again with the indices suitable chosen to correspond to Eqs. (B3) and (B4).

The objective of Eq. (A5) is implemented as the following:

$$\text{objective}(\vec{x}) = \sum \sum w_j^{\prime} t x_{j,m_j, \text{end}} - \text{offset}, \tag{B6}$$

where the bounds on $t$ are evaluated as $t_{\min}(j, m_j, \text{end})$, $t_{\max}(j, m_j, \text{end})$. To solve the Job Shop problem, this objective function should be minimized subject to the constraints given above.

## References

[1] A. Lucas, Ising formulations of many np problems, Frontiers in Physics 2, 5 (2014).

[2] F. Glover, G. Kochenberger, and Y. Du, Quantum bridge analytics: a tutorial on formulating and solving qubo models, 4OR 17, 335 (2019).

[3] E. Domino, E. Robertson, B. Gardas, and S. Deffner, On the baltimore light taillink into the quantum advantage, Reports 1, 2876 (2025).

[4] K. Domino, M. Korzycki, K. Krawiec, K. Jaloiecki, S. Deffner, and B. Gardas, Quantum annealing in the nisq era: Railway conflict management, Entropy 25, 191 (2023).

[5] R. Robertson, E. Doucet, Z. Mzaouli, K. Domino, B. Gardas, and S. Deffner, Quantum annealing with many qubits, NISQ and Quantum Machine Learning, in 2025 IEEE International Conference (QCCE), Vol. 01 (2025) pp. 190-196.

[6] P. Hanussek, J. Pawlowski, Z. Mzaouli, and B. Gardas, Solving quantum-inspired dynamics on quantum annealing and classical annealing (2025), arXiv:2404.03652 [quant-ph].

[7] E. Kzetenyi, W. Crosson, M. Konnerczak, Z. Mzaouli, A. Galadiková, and K. Domino, Quantum and classical algorithms for daily routine scheduling, arXiv:2512.19340 [quant-ph].

[8] N. M. Johnson et al., Quantum annealing with manufactured spins, Nature 473, 194 (2011).

[9] P. Nightingale, E. Iohe, and M. Ghee, Flight gate assignment with a quantum annealer, in Quantum Technology and Optimization (Springer, 2019).

[10] C. Carrion, M. Ferrari-Dorcema, and P. Cremonesi, Evaluating the job shop scheduling problem on a d-wave quantum annealer, Scientific Reports 12, 6539 (2022).

[11] J. Pawlowski, P. Tarasuk, J. Tuziewski, L. Pawela, and B. Gardas, Closing the quantum-classical gap for job-shop-scheduling, arXiv:2505.25514.10.48550/arXiv.2505.25514 (2025).

[12] H. Munoz-Bauza and D. Lidar, Scaling advantage in approximate optimization with quantum annealing, Phys. Rev. Lett. 134, 160601 (2025).

[13] P. Chandarana, A. G. Cadavid, S. V. Romero, A. Stamen, B. Solano, and N. S. Hegade, Runtime quantum advantage with digital quantum optimization, arXiv:2302.08663 arXiv:2302.08663 (2025).

[14] J. Tuziewski, J. Pawlowski, P. Tarasuk, L. Pawela, and B. Gardas, Beating the quantum advantage in digital quantum optimization, (2025), arXiv:2510.06357 [quant-ph].

[15] C. Delcamp, M. M. Sulejeb, A. Sajeh, P. Hespanha, and K. Cunsari, Two-dimensional parallel temperiing for constrained optimization, Phys. Rev. E 112, L032301 (2025).

[16] T. F. Ronnow, Z. Wang, J. Job, S. Boixo, S. V. Isakov, D. Wecker, J. M. Martinis, D. A. Lidar, and M. Tower, Defining and detecting quantum speedup, Science 345, 420-424 (2014).

[17] P. F. Rennow, Z. Wang, J. Boixo, S. V. Isakov, D. Wecker, J. M. Martinis, D. A. Lidar, and M. Tower, Defining and detecting quantum speedup, Science 345, 420-424 (2014).

[18] S. Campbell, I. D'Amico, M. A. Ciampini, J. Anders, A. A. Smerzi, L. Uffele, L. P. Bettmann, M. V. S. Bonanca, T. Busch, M. Campisi, J. Andres, S. Dago, S. Deffner, A. D. Campo, A. Deutschmann-Olek, S. Dorali, E. Doucoet, C. Dioett, K. Ensalm, P. Erker, N. Fabbri, F. Fedele, G. Fiusa, T. Fogarty, L. Fredesgaard, P. Gómez, C.-K. Hu, F. Jemini, B. Karimi, N. Kiesel, G. T. Landi, L. Lapenta, A. López, E. Lidia, D. Lyov, O. Maillet, M. Masseglioni, T. Mendonca, H. J. D. Mller, A. R. Mitchell, M. T. Mitchley, N. Mukherjee, R. F. Pernestrello, J. Pekola, M. Perarnau-Llobet, U. Pöchinger, R. Roland, A. Santos, R. Sarthorn, E. Sela, A. Solanelli, A. M. Sotaro, J. Splettstoesser, D. Tan, L. Tesar, T. V. Vu, A. Widera, N. Y. Halpern, and K. Zawadzki, Roadmap on quantum thermodynamics (2025), arXiv:2504.20145 [quant-ph].

[19] A. Aufeves, Quantum technologies need a quantum energy initiative, PRX Quantum 3, 020101 (2022).

[20] Z. Mzaouli, R. Puebla, J. Goold, M. El Baz, and S. Campbell, Work statistics and symmetry breaking in an excited-state quantum phase transition, Phys. Rev. E 103, 042345 (2021).

[21] J. Stevens and S. Deffner, Hamiltonian quantum gates-generic existence and undecidability, Quantum Science and Technology 10, 041103 (2025).

[22] S. Deffner, Shortcut cost of hamiltonian quantum gates, Europhysics Letters 134, 40002 (2021).

[23] B. Gardas and S. Deffner, Quantum infation theorem for error diagnostics in quantum annealers, Scientific Reports 8, 1711 (2018).

[24] M. Campisi and L. Duffoni, Improved bound on entropy production in a quantum annealers, Phys. Rev. E 104, L022102 (2021).

[25] J. Buffoni and M. Campisi, Thermodynamics of a quantum annealer, Quantum Science and Technology 5, 035013 (2020).

[26] T. Smierzchalski, Z. Mzaouli, S. Deffner, and B. Gardas, Efficiency optimization in quantum computing: balancing thermodynamics and computational performance, Scientific Reports 14, 4555 (2025).

[27] F. Glover, G. Kochenberger, and Y. Du, A tutorial on formulation and use in qubo models, arXiv preprint arXiv:1811.11538 10.48550/arXiv.1811.11538 (2018).

[28] P. P. Angura, E. Martins, P. Blace, and M. Miller, A unification framework for constrained combinatorial optimization, in 2025 IEEE International Conference on Quantum Computing and Engineering (QCCE), Vol. 01 (2025) pp. 65-75.

[29] S. Katumi and H. Romugh, A subgradient approach to unconstrained binary optimization via quantum adiabatic evolution, Quantum Information Processing 16, 10 1007/s11128-017-1633-2 (2017).

[30] N. Gromov and A. Wiegle, EXPEDIS: An exact solution method over discrete sets, Discrete Optimization 44, 100622 (2022).

[31] T. Hrga and J. Gasteiger, MADAMM: A parallel exact solver for uncut based on semiclassic programming and ADMM, Computational Optimization and Applications 89, 347 (2021).

[32] B. Apolloni, C. Carvalho, and D. De Falco, Quantum stochastic optimization, Stochastic Processes and Their Applications 33, 233 (1989).

[33] T. Kadowaki and S. Nishimori, Quantum annealing in the transverse ising model, Physical Review E 58, 5355 (1998).

[34] E. Farhi, J. Goldstone, and S. Gutmann, A quantum adiabatic evolution algorithm, arXiv preprint arXiv:1411.4028 10.48550/arXiv:1411.4028 (2014).

[35] M. L. Pinedo, Scheduling, Vol. 29 (Springer, 2012).

[36] A. C. Barato and U. Seifert, Thermodynamic uncertainty relation for biomolecular processes, Phys. Rev. Lett. 114, 158101 (2015).

[37] T. R. Gingrich, J. M. Horowitz, N. Perunov, and J. L. England, Dissipation bounds all steady-state current fluctuations, Phys. Rev. Lett. 116, 120601 (2016).

[38] U. Seifert, Stochastic thermodynamics, fluctuation theorems and molecular machines, Reports on Progress in Physics 75, 126001 (2012).

[39] J. Blazewicz, J. Ecker, E. Pesch, G. Schmidt, and J. Weglarz, Handbook on Scheduling: From Theory to Applications (Springer, 2007).

[40] A. S. Jain and S. Meeran, Deterministic job-shop scheduling problems: a review, Journal of the Operational Research Society 10, 276 (1999).

[41] L. Monch, J. W. Fowler, and S. J. Mason, Production Planning and Control for Semiconductor Wafer Fabrication (Springer, 2013).

[42] Y. Xia, S. Werdell, and M. S. Sun, Airline scheduling optimization: literature review and a discussion of modelling methodologies, Intelligent Transportation Infrastructure 3, Iod1026 (2024).

[43] D. I. Hansen, State-of-the-art of railway operations research, Journal of Rail Transport Planning & Management 1, 1-12 (2010).

[44] V. Cacchiani, D. Huisman, M. P. Kidd, et al., An overview of recovery models and algorithms for real-time railway rescheduling, Transportation Research Part B 63, 15 (2014).

[45] R. Robertson, C. Rüfel, M. Slodov, and P. Hendrickson, Implementing grover's algorithm on noisy chips, in NAE-CON 2025 - IEEE National Aerospace and Electronics Conference (2025) pp. 1-6.

[46] B. Baptiste, C. Le Pape, and W. Nuijten, Constraint-based scheduling: applying constraint programming to scheduling problems, Vol. 39 (Springer Science & Business Media, 2001).

[47] C. Venturelli, D. Marchand, and G. Rojo, Job shop scheduling on the d-wave quantum annealer, in Proceedings of the 16th International Conference on Quantum Annealing, Simulation and Related Techniques, Vol. 02 (2016) pp. 27-41.

[48] U. Kochenberger, J.-K. Hao, F. Glover, et al., The unconstrained binary optimization problem: a survey, Journal of combinatorial optimization 28, 58 (2014).

[49] D-Wave, D-Wave samplers (2025), accessed: 2025-12-17.

[50] S. Chowdhury, N. A. Audit, A. Grimaldi, E. Raimondo, A. Raut, P. A. Lott, J. H. Mentink, M. M. Mayle, S. Runge, P. Ricci-Broscesi, M. Mirtchell, L. Theugragan, S. Srimath, G. Finocchio, M. Mohseni, and K. Y. Jürgen, Pushing the boundary of quantum advantage in hard combinatorial optimization with probabilistic computing, Nat. Commun. Lett. 16, 3235-6 (2025).

[51] N. A. Audit, A. Grimaldi, M. Carpentieri, L. Theograjan, J. M. Martinis, G. Finocchio, and M. Campsi, Massively parallel probabilistic computing with sparse ising machines, Nat. Electron. 10.1038/s41928-022-00773-2 (2022).

[52] T. Albash, S. Boixo, D. A. Lidar, and P. Zanardi, Quantum adiabatic master equation, New Journal of Physics 14, 123016 (2012).

[53] D-Wave, D-Wave supports (2025), accessed: 2025-12-17.

[54] T. Albash, W. Vinci, A. Mishra, P. A. Warthurton, and D. A. Lidar, Consistency tests of classical and quantum annealer, Phys. Rev. A 91, 042314 (2015).

[55] T. Albash, I. Hen, F. M. Spedalieri, and D. A. Lidar, Reexamination of the evidence for entanglement in a quantum annealer, Phys. Rev. E 92, 062328 (2015).

[56] G. E. Crooks, Nonequilibrium measurements of free energy differences for microscopically reversible markovian systems, Journal of Statistical Physics 90, 1481-1487 (1998).

[57] C. Jarzynski, Equilibrium free-energy differences from nonequilibrium measurements: A master-equation approach, Physical Review E 56, 5018 (1997).

[58] D. Aharonov, W. van Dam, J. Kempe, Z. Landau, S. Lloyd, and O. Regev, Adiabatic quantum computation is equivalent to standard quantum computation, SIAM Review 50, 755-787 (2008).

[59] D. A. Lidar, A. T. Rezakhani, and A. Hamma, Adiabatic approximation with exponential accuracy for many-body systems and quantum computation, Journal of Mathematical Physics 50, 10.1063/1.3236685 (2009).

[60] S. Boixo and R. D. Somma, Necessary condition for the quantum adiabatic approximation, Physical Review A 81, 10.1103/physreva.81.032308 (2010).
