# A Unified Performance–Cost Landscape of Parallel p-bit Ising Machines Based on Update Dynamics


> **Citation.** Canonical entry `onizawa2026` in [`references.bib`](../../references.bib) (resolved via Crossref/DataCite). arXiv:[2604.01564](https://arxiv.org/abs/2604.01564).
>
> **Companion note.** [`onizawa-2026-parallel-pbit-ising.note.md`](./onizawa-2026-parallel-pbit-ising.note.md) — how this paper links to Gibbsiq.

**Naoya Onizawa*** and Takahiro Hanyu*

*Research Institute of Electrical Communication, Tohoku University, Sendai, 980-8577, Japan  
**Corresponding author: naoya.onizawa@tohoku.ac.jp

April 3, 2026

## Abstract

Parallel p-bit Ising machines provide a promising hardware platform for fast and energy-efficient combinatorial optimization, but their scalability and efficiency critically depend on underlying synchronization, hardware timing, and architectural cost. Here we develop a unified performance–cost landscape for parallel p-bit annealing by systematically analyzing synchronous and asynchronous update schemes under realistic constraints, including time delay, time-multiplexed p-bit reuse, and limited input digital-to-analog (DAC) precision. We show that synchronous updates are not inherently unstable, but can suffer from oscillations when excessive update simultaneity is present, while asynchronous updates are structurally constrained by hardware delay and require slower operation to maintain stability. To bridge performance and hardware efficiency, we introduce time-multiplexed reuse of physical p-bits combined with structured synchronous control policies, which preserve statistically valid annealing dynamics while reducing the effective update rate. This reuse decouples statistical correctness from physical resource count, enabling the number of physical p-bits and input DACs to scale approximately as the inverse of the time-multiplexing reuse factor. As a result, synchronous architectures access low-cost operating regimes, achieving comparable or superior solution quality at less than half the normalized hardware cost of optimized asynchronous updates on G-set MaxCut benchmarks with 800–2000 nodes under matched annealing time. We further demonstrate that low-resolution input DACs (typically 3–4 bits) can often achieve performance within a few percent of the best-known solutions (normalized cut ≤ 0.95) when annealing time is appropriately adjusted. Together, these results establish coordinated time-multiplexed p-bit reuse combined with structured synchronous control as a key architectural principle for scalable probabilistic computing hardware, and provide reproducible design guidance for balancing solution quality, hardware cost, and timing constraints under realistic delay and precision limitations.

## Introduction

Probabilistic computing is an emerging computing paradigm that exploits intrinsic stochasticity to efficiently solve inference, sampling, and combinatorial optimization [1] [2]. Its fundamental building block is the *probabilistic bit* (p-bit), a stochastic binary unit whose output fluctuates in time with a tunable mean determined by a weighted sum of inputs [3]. Networks of interacting p-bits can implement invertible Boolean logic and naturally sample from Boltzmann distributions, enabling hardware-friendly realizations of Ising and QUBO models [4]-[7]. Compared with fully digital optimization approaches [8], p-bit networks provide a promising route to domain-specific accelerators that trade numerical precision for massive parallelism and improved energy efficiency, particularly when asynchronous devices such as low-barrier magnetic tunnel junctions (MTJs) provide randomness at nanosecond time scales [9] [10].

Early studies established the principles of probabilistic spin logic, and subsequent device- and circuit-level studies have demonstrated that stochastic p-bits exhibit strong potential for scalable probabilistic inference and optimization, while related hardware approaches to Ising optimization have also been explored in digital annealing, coherent Ising machines, simulated bifurcation, and quantum annealing [12] [13] [14] [15] [16] [17] [18] [19] [20] [21] [22]. Among these directions, simulated annealing using p-bits (pSA) is attractive because it can be implemented on conventional computing platforms while still exploiting the parallelism inherent in p-bit networks. Unlike traditional simulated annealing, which typically updates nodes sequentially, pSA permits parallel updates, but its performance can degrade on larger problems such as MaxCut instances [23] [16]. Recent algorithmic variants have improved large-scale pSA performance [24], which further motivates a systematic study of how update dynamics and hardware constraints influence scalability.

The introduction of these algorithms has opened up the possibility of large-scale implementations of pSA. However, their effectiveness and scalability depend critically on the underlying update dynamics of interacting p-bits. At the algorithmic level, the dynamics of p-bit networks during annealing are strongly influenced by how p-bits are *updated*. In synchronous, clock-driven designs, many p-bits update simultaneously; which simplifies control and enables structured memory access, as commonly observed in parallel Ising machine implementations [15]. However, strong simultaneity can induce oscillatory behavior in tightly coupled graphs, preventing monotonic energy reduction and hindering convergence. As a result, practical p-bit accelerators must jointly co-design the *update policy* and the *mapping* from a logical p-bit network to physical hardware, balancing solution quality against area, power, and throughput.

This paper develops a unified *performance–cost landscape* for parallel p-bit updates by systematically sweeping four key architectural parameters: (i) the update policy, (ii) the update interval $\tau$, (iii) the time-multiplexing reuse factor $c$, defined as the number of logical p-bits mapped onto a single physical p-bit, and (iv) the input-DAC bit width $b$. In particular, we focus on the delay-to-update ratio $(d/\tau)$, which governs the effective coupling between updates and plays a critical role in determining stability, mixing behavior, and convergence under parallel update schemes.

Our central contribution is a time-multiplexed p-bit reuse scheme $(c > 1)$ co-designed with synchronous scheduling, which substantially reduces the required number of physical p-bits and DACs while preserving solution quality through appropriate timing and control.

## Contributions

- We characterize oscillation and stability regimes for parallel p-bit updates and quantify how convergence depends on the delay-to-update ratio $d/\tau$ and the effective update rate.

- We propose practical synchronous control strategies (including randomized and structured block schedules) that mitigate harmful simultaneity while preserving hardware-friendly memory access.

- We introduce a time-multiplexed reuse scheme $(c > 1)$ and evaluate its performance–cost trade-offs, binding reductions in p-bits and input-DAC resources relative to one-to-one mappings.

- We show that low-resolution input DACs (typically 3–4 bits) can achieve near-best normalized cut when the annealing time is adjusted appropriately, further hardware savings.

To address these challenges, this work develops a unified simulation and analysis framework for studying the architectural trade-offs of parallel p-bit Ising machines. Rather than proposing a new probabilistic model, the goal is to systematically analyze how different parallel update policies interact with realistic hardware constraints.

Within this framework, we construct a unified performance–cost landscape by sweeping four key architectural parameters: update policy, update interval $\tau$, time-multiplexing reuse factor $c$, and input-DAC resolution. All update schemes are evaluated under a common simulation environment with identical annealing schedules, fixed hardware delay, and matched total simulation time. This controlled setting allows a fair comparison between synchronous and asynchronous update mechanisms while isolating the architectural factors that determine scalability, solution quality, and hardware efficiency.

## Related Work

### p-bit computing and probabilistic spin logic

Probabilistic bits (p-bits) were originally introduced as stochastic building blocks for invertible Boolean logic and probabilistic computing systems [4] [6]. Networks of interacting p-bits can emulate Ising models and naturally perform Boltzmann sampling, enabling hardware realizations of combinatorial optimization algorithms and probabilistic inference [5] [7]. Experimental and circuit-level studies have demonstrated that stochastic devices such as low-barrier magnetic tunnel junctions (MTJs) can generate the required randomness at nanosecond time scales, enabling compact and energy-efficient hardware implementations [9] [10].

Beyond combinatorial optimization, p-bit networks have been applied to a variety of probabilistic tasks, including neural network training, Bayesian inference, parallel tempering, and Gibbs sampling [12] [13]. These results highlight the potential of probabilistic hardware as an alternative to deterministic digital accelerators for sampling-based computation.

### Update dynamics and parallel sampling

A central issue in p-bit networks and related stochastic optimization methods is the update dynamics of interacting variables. Classical Gibbs sampling theory typically assumes sequential updates, which guarantee convergence to the correct Boltzmann distribution. However, sequential updates can limit hardware parallelism.

Parallel or partially synchronous update schemes have therefore been studied in both statistical physics and machine learning contexts. For example, parallel Gibbs samplers and their parallel variants [27] [28], as well as recent theoretical analyses showing that asynchronous updates can introduce bias and slow mixing when operating on stale information [29] [30] [31].

Beyond algorithmic considerations, scalability is fundamentally constrained by hardware resources. Implementing weighted interactions among p-bits requires interconnect, memory bandwidth, and in-put digital-to-analog conversion (DAC) or equivalent mixed-signal resources, whose area and power can dominate at large problem sizes, as demonstrated in recent experimental p-bit and Ising machine implementations [32]. As a result, practical p-bit accelerators must jointly co-design the *update policy* and the *mapping* from a logical p-bit network to physical hardware, balancing solution quality against area, power, and throughput.

This paper develops a unified *performance–cost landscape* for parallel p-bit updates by systematically sweeping four key architectural parameters, opening up the possibility of large-scale implementations of pSA. However, their effectiveness and scalability depend critically on the underlying update dynamics of interacting p-bits. At the algorithmic level, the dynamics of p-bit networks during annealing are strongly influenced by how p-bits are updated. In synchronous, clock-driven designs, many p-bits update simultaneously, which simplifies control and enables structured memory access, as commonly observed in parallel Ising machine implementations [15]. However, strong simultaneity can induce oscillatory behavior in tightly coupled graphs, preventing monotonic energy reduction and hindering convergence. As a result, practical p-bit accelerators must jointly co-design the update policy and the mapping from a logical p-bit network to physical hardware, balancing solution quality against area, power, and throughput.

## Model and Hardware Assumptions

This section defines the probabilistic-bit model, timing notation, and abstract hardware assumptions used throughout this work. Implementation-specific simulation procedures and update-policy algorithms are described in the Methods section.

### Probabilistic-bit model and Ising formulation

We consider Ising optimization problems with spins $\sigma_i \in \{+1\}$ and energy

$$H(\sigma) = -\frac{1}{2}\sigma^{\top} J \sigma - h^{\top} \sigma \tag{1}$$

Each Ising spin is implemented as a *logical p-bit*, a stochastic binary unit whose output fluctuates in time depending on its input. The probabilistic update rule of a p-bit can be expressed as

$$\sigma_i(t^+) = \mathrm{sgn}\left(r_i(t) + \tanh(I_i(t))\right), \tag{2}$$

where $r_i(t) \in [-1,1]$ is an independently and uniformly distributed random variable at each update event, and $I_i(t)$ is a real-valued input signal. This formulation is equivalent to sampling $\sigma_i(t^+)$ from the Bernoulli distribution

$$\Pr[\sigma_i(t^+) = +1] = \frac{1}{2}(1 + \tanh I_i(t)), \tag{3}$$

ensuring consistency with Boltzmann statistics.

For Ising optimization, the input to each p-bit is computed as

$$I_i(t) = I_0(t)\left(h_i + \sum_j J_{ij}\sigma_j(t)\right), \tag{4}$$

where $h_i$ and $J_{ij}$ denote the bias and coupling weights of the Ising model, respectively. The parameter $I_0(t)$ acts as a *pseudo inverse temperature* that controls the interaction strength and is increased over time to implement simulated annealing.

In hardware-oriented implementations, the random signal $r_i(t)$ may be provided by intrinsic device-level stochasticity (e.g., thermal fluctuations in low-barrier MTJs). Moreover, the input field $I_i(t)$ may be quantized due to finite input digital-to-analog converter (DAC) resolution, allowing the impact of limited precision to be explicitly captured.

### Time-multiplexing factor $c$ and timing

Fig. 2 illustrates the concept of time-multiplexed p-bit reuse. We introduce a *time-multiplexing reuse factor* $c$, defined as the number of logical p-bits that are sequentially mapped onto a single physical p-bit. When $c > 1$, a single physical p-bit maps multiple logical spins over successive time slots, reducing the required number of physical p-bits and input DACs by approximately a factor of $c$.

Let $\tau$ denote the intrinsic update period of a physical p-bit. Under time-multiplexing, a single physical p-bit sequentially updates $c$ logical spins over successive time slots, such that the effective flip/update rate per logical spin becomes

$$\lambda_{\text{spin}} = \frac{1}{\tau c}, \tag{5}$$

where $\tau$ denotes the intrinsic update period of a physical p-bit. We assume a fixed apply delay of $d = 5$ ns to capture device/interconnect/control latency. This is consistent with experimental reports of stochastic MTJs exhibiting nanosecond-scale fluctuation dynamics and nanosecond operation, which sets the natural time scale for p-bit updates [10]. The delay-to-update ratio therefore quantifies the relative severity of delayed updates.

### Abstract hardware cost metrics

We evaluate architectural hardware cost using abstract metrics that capture dominant scaling behavior rather than technology-specific circuit details. The dominant cost $C_{\text{HW}}$ accounts for the two primary scalable resources: physical p-bits and input DACs. With time-multiplexed reuse factor $c$, the number of physical p-bits scales as

$$N_p = \left\lceil \frac{N}{c} \right\rceil, \tag{6}$$

and we assume $N_{\text{DAC}} \propto N_p$. We normalize DAC resolution as $b = b/b_{\text{ref}}$ with $b_{\text{ref}} = 12$ [32] and define

$$C_{\text{HW}} = \alpha N_p + \beta b N_{\text{DAC}}, \tag{7}$$

where $\alpha$ and $\beta$ are positive weighting factors used only to capture relative scaling.

In addition, parallel architectures incur update-policy-dependent access/control overhead related to memory access, address generation, randomness complexity, verification complexity, and synchronization constraints. We refer to these effects collectively as $C_{\text{ACC}}$ and summarize their qualitative trends in Table 1.

## Results

### Overview: performance–cost landscape

All results are obtained under the common simulation conditions summarized in Table 5, and evaluated on the G-set benchmark instances listed in Table 4. Using the normalized hardware cost $C_{\text{HW}}$ defined in Eq. (7), Fig. 1 establishes a global performance–cost landscape that captures the dominant architectural trade-offs between solution quality and hardware cost; detailed analyses follow in the Results section.

Each point in Fig. 1 corresponds to a representative operating condition defined by the update policy, time-multiplexing reuse factor $c$, update interval $\tau$, and DAC resolution. This landscape provides a unifying context for the detailed analyses that follow, allowing individual results to be interpreted as movements along a common performance–cost frontier rather than isolated parameter sweeps.

### Synchronous updates: oscillation and stabilization

Fig. 3 shows representative energy time series under synchronous random updates for six G-set instances (G1, G6, G11, G34, G38, and G39), with the time-multiplexing reuse factor varied over $c \in \{1, 1.25, 1.5, 2, 3\}$. When $c = 1$, a large fraction of logical spins are updated nearly simultaneously at each tick. In strongly coupled graphs, this simultaneity induces coherent collective switching of many p-bits, leading to pronounced oscillations in the energy trajectory. As $c$ increases, update simultaneity is reduced, and effective per-spin update rate becomes $\lambda_{\text{spin}} = 1/(\tau c)$, reducing the coherent switching. For $c \geq 2$, the energy trajectories become markedly smoother across all tested instances, indicating that annealing dynamics recover stability even under fully synchronous control.

These results highlight that oscillations in synchronous architectures are not an inherent limitation but rather a consequence of excessive update simultaneity when many strongly coupled p-bits update at the same tick.

However, as $d/\tau$ approaches unity, performance degrades due to spins acting on stale local fields computed from outdated neighboring states [33]. This temporal inconsistency effect effectively reintroduces correlated update errors, leading to bias and instability despite the absence of explicit asynchronization. The degradation is particularly pronounced at lower DAC resolutions, where quantization noise further amplifies the effect of delayed information.

### Asynchronous updates: sensitivity to hardware delay

Fig. 4 quantifies the impact of hardware delay on asynchronous (Gillespie-type) updates by plotting the normalized mean cut value as a function of the delay-to-update ratio $d/\tau$ for six representative G-set instances, with the apply delay fixed at $d = 5$ ns and a simulation time of 100 ns. In the idealized limit $d/\tau \ll 1$, asynchronous updates avoid global simultaneity and exhibit stable annealing behavior across a wide range of DAC resolutions.

These results demonstrate that asynchrony alone does not guarantee robustness. Correct and efficient asynchronous annealing requires that the hardware delay remain sufficiently small relative to the update interval, imposing a nontrivial constraint on clock frequency and device latency in large-scale implementations.

Although asynchronous updates avoid explicit synchronization, their performance is highly sensitive to the delay-to-update ratio $d/\tau$, imposing a practical constraint on clock frequency and preventing access to low-cost operating regimes.

## Control policies for synchronous updates

Fig. 5 compares three synchronous control policies—random, block-random, and block-random-stride—by reporting, for each time-multiplexing reuse factor $c$, the DAC bit width that maximizes the normalized mean cut value (left), and the corresponding mean normalized cut value at that optimal bit width (right), using a simulation time of 100 ns. The normalized mean cut value is averaged over all G-set benchmarks listed in Table 4.

Across all values of $c$, block-based policies consistently achieve comparable or higher performance with comparable or lower bit width than fully random updates.

All three policies use $b$, the DAC resolution that maximizes performance when annealing time is fixed. However, even at the most favorable date interval considered here, asynchronous updates remain confined to relatively high normalized hardware cost, as time-multiplexed p-bit reuse ($c > 1$) is not readily supported. Consequently, performance recovery in asynchronous schemes is achieved primarily through reduced update-rate rather than improved hardware efficiency.

In contrast, synchronous architectures achieve comparable or higher normalized performance while operating at substantially lower hardware cost. As shown in Fig. 2 (block-random and block-random-stride scheduling with time-multiplexed reuse ($c = 3$) attain near-best normalized cut values at less than half the normalized cost of the best asynchronous configurations. These results indicate that the advantage of synchronous architectures arises not from optimistic timing assumptions, but from their ability to exploit coordinated reuse of physical p-bits and structured synchronous control as a key architectural principle for scalable probabilistic computing hardware.

### DAC precision and annealing time

Fig. 6 summarizes the dependence of annealing performance on input-DAC resolution for both asynchronous and synchronous update schemes. The normalized mean cut value is plotted as a function of DAC bit width $b$ for multiple annealing times, with asynchronous updates evaluated at $\tau \in \{2.5, 5, 7.5, 10, 15, 20\}$ ns and synchronous policies evaluated at $\tau = 5$ ns with time-multiplexing reuse factor $c = 3$. Each curve corresponds to a different total simulation (annealing) time. Reducing DAC resolution degrades performance when annealing time is fixed. However, longer annealing partially compensates for coarse quantization. Synchronous policies exhibit smoother degradation and greater tolerance to low-resolution DACs than asynchronous updates.

These results suggest that DAC precision can be treated as a flexible design parameter rather than a hard constraint. In many cases, 3–4 bit DACs are sufficient to achieve near-optimal performance when combined with moderate increases in annealing time, enabling substantial reductions in hardware area and power without sacrificing solution quality.

### Sequential baseline as an algorithmic reference

To provide a compact algorithmic reference against the representative parallel operating points, we additionally compare a sequential baseline against asynchronous and synchronous updates on four G-set instances (G1, G11, G14, and G34), as summarized in Fig. 7. The asynchronous setting uses Gillespie updates with $\tau = 10$ ns and $c = 1$, the synchronous setting uses tick block-random-stride updates with $\tau = 5$ ns and $c = 3$, and the sequential baseline uses the systematic single-spin update baseline with $\tau = 5$ ns and $c = 1$; all three use $b = 10$ under a common linear annealing schedule and total simulation time of 500 ns. Async denotes Gillespie updates with $\tau = 10$ ns and $c = 1$, Sync denotes tick block-random-stride updates with $\tau = 5$ ns and $c = 3$, and Sequential denotes the systematic single-spin update baseline with $\tau = 5$ ns and $c = 1$. Error bars indicate the standard deviation over 5 repeats, and markers are shown without line connections because the benchmark instances are categorical.

synchronous control in accessing low-cost operating regimes that are fundamentally difficult to reach with fully asynchronous updates.

## Discussion

### Synchronous versus asynchronous architectures

The results presented in this work clarify a fundamental architectural trade-off between synchronous and asynchronous parallel p-bit systems. Synchronous updates offer explicit global coordination and predictable timing, which are naturally compatible with hardware scheduling and memory access, but naïve clock-driven operation can induce collective oscillations when many strongly coupled p-bits update simultaneously. Asynchronous updates, in contrast, avoid explicit synchronization and naturally desynchronize spin updates, but their stability critically depends on the interaction between update statistics and hardware timing. In synchronous systems, excessive simultaneity induces oscillations, whereas in asynchronous systems, excessive hardware delay leads to oscillations and stale information, convergence can slow and solution quality can degrade, a phenomenon closely related to classical results on missing and parallel Markov chain updates [26]. These effects are closely related to classical sampling theory for Gibbs samplers and their parallel variants [27] [28], as well as recent theoretical analyses showing that asynchronous updates can introduce bias and slow mixing when operating on stale information [29] [30] [31].

Beyond algorithmic considerations, scalability is fundamentally constrained by hardware resources. Implementing weighted interactions among p-bits requires interconnect, memory bandwidth, and in-put digital-to-analog conversion (DAC) or equivalent mixed-signal resources, whose area and power can dominate at large problem sizes, as demonstrated in recent experimental p-bit and Ising machine implementations [32]. As a result, practical p-bit accelerators must jointly co-design the update policy and the mapping from a logical p-bit network to physical hardware, balancing solution quality against area, power, and throughput.

This paper develops a unified *performance–cost landscape* for parallel p-bit updates by systematically sweeping four key architectural parameters, opening up the possibility of large-scale implementations of pSA. However, their effectiveness and scalability depend critically on the underlying update dynamics of interacting p-bits. At the algorithmic level, the dynamics of p-bit networks during annealing are strongly influenced by how p-bits are updated. In synchronous, clock-driven designs, many p-bits update simultaneously, which simplifies control and enables structured memory access, as commonly observed in parallel Ising machine implementations [15]. However, strong simultaneity can induce oscillatory behavior in tightly coupled graphs, preventing monotonic energy reduction and hindering convergence. As a result, practical p-bit accelerators must jointly co-design the update policy and the mapping from a logical p-bit network to physical hardware, balancing solution quality against area, power, and throughput.

These observations indicate that asynchrony should not be regarded as inherently more robust. Instead, both synchronous and asynchronous schemes are subject to stability constraints that arise from the interaction between update statistics and hardware timing. In synchronous systems, excessive simultaneity leads to oscillations, whereas in asynchronous systems, excessive hardware delay requires slower operation to maintain stability and preventing coordinated p-bit reuse.

depends on the relationship between the hardware delay $d$ and the update interval $\tau$.

As demonstrated in the Results section, particularly in Fig. 4 and Table 2, asynchronous annealing degrades rapidly as the ratio $d/\tau$ approaches unity, due to spins acting on stale local fields. Although this degradation can be partially mitigated by increasing $\tau$, doing so reduces the effective update rate rather than improving hardware efficiency. As a consequence, asynchronous architectures remain confined to relatively high hardware cost and cannot exploit coordinated time-multiplexed reuse of physical p-bits.

These observations indicate that asynchrony should not be regarded as inherently more robust. Instead, both synchronous and asynchronous schemes are subject to stability constraints that arise from the interaction between update statistics and hardware timing. In synchronous systems, excessive simultaneity induces oscillations, whereas in asynchronous systems, excessive hardware delay requires slower operation to maintain stability and preventing coordinated p-bit reuse.

## Role of time-multiplexed p-bit reuse

A central contribution of this work is the demonstration that time-multiplexed reuse of physical p-bits ($c > 1$) enables substantial reductions in hardware cost without altering the target stationary distribution of the stochastic dynamics. Importantly, this reuse does not modify the update probabilities of individual logical spins; rather, it uniformly rescales their effective update rate as $\lambda_{\text{spin}} = 1/(\tau c)$. As a result, time-multiplexed reuse corresponds to a temporal rescaling of the underlying Markov process rather than a change in the transition kernel.

This separation between statistical correctness and temporal efficiency explains why reuse does not introduce systematic bias. Each logical spin still draws from the same Bernoulli (synchronous) or Poisson (asynchronous) statistics as in the $c = 1$ case, but at a reduced rate. Such thinning arguments are well established in stochastic simulation theory and imply that only the stationary distribution, not the convergence speed, is affected.

Synchronous architectures are particularly well suited to this approach because they provide explicit control over update scheduling and naturally align with the discrete time structure required for reuse. Fully asynchronous architectures, by contrast, lack a straightforward mechanism to guarantee statistically consistent reuse across logical spins without introducing additional buffering, scheduling, control overhead. This limitation is structural rather than algorithmic and explains why asynchronous updates cannot access the low-cost operating regimes observed in Fig. 1 and summarized in Tables 2 and 3.

## Structured synchronous control and hardware implications

The Results further demonstrate that structured synchronous update policies play a critical role in enabling stable and efficient reuse. Block-random and block-random-stride scheduling suppress harmful update correlations associated with simultaneous updates while preserving contiguous or pseudo-contiguous memory access patterns. This combination is particularly advantageous for hardware implementation, as it reduces address-generation complexity, random-number usage, and memory-access overhead.

From a design perspective, the time-multiplexing reuse factor $c$ and the input-DAC resolution $b$ emerge as interacting architectural knobs. Increasing $c$ reduces the number of physical p-bits and DACs approximately as $1/c$, while reducing $b$ lowers mixed-signal area and power at the cost of increased quantization noise. The Results show that moderate increases in annealing time can often compensate for both effects, allowing designers to trade temporal efficiency for substantial hardware savings.

Recent circuit- and device-level advances have further demonstrated that the mixed-signal overhead associated with input digital-to-analog converters can be significantly reduced or even eliminated. In particular, DAC-free p-bit architectures based on stochastic nanodevices have been proposed, where probabilistic tunability and annealing are realized entirely through digital delay-based control without explicit analog inputs [34]. From the perspective of the unified performance–cost framework developed in this work, such DAC-free designs can be interpreted as operating in the extreme low-precision limit of the input representation. In this regime, the dominant architectural trade-offs shift from input resolution toward update dynamics, timing control, and effective update rates.

## Design implications and limitations

Taken together, these results establish coordinated time-multiplexed reuse combined with structured synchronous control as a key architectural principle for scalable probabilistic computing hardware. The advantage of synchronous architectures does not stem from idealized timing assumptions, but from their ability to explicitly coordinate reuse and scheduling under finite hardware delay and limited precision.

Several limitations point to directions for future work. First, the hardware cost model employed here is intentionally abstract and does not capture technology-specific circuit details such as DAC area, noise, or power consumption. Second, device-level variability beyond stochastic bit flips is not explicitly modeled and may further interact with reuse and scheduling strategies. Finally, extremely large-scale systems may introduce additional constraints related to memory bandwidth and interconnect scaling that are not captured by the present model.

Despite these limitations, the unified performance–cost framework developed in this work provides a systematic basis for evaluating architectural trade-offs in parallel p-bit systems. By explicitly linking update statistics, hardware timing, and resource reuse, it offers concrete design guidance for the development of large-scale, energy-efficient probabilistic computing accelerators.

## Methods

This section describes the simulation framework, update-policy implementations, and benchmark settings used throughout this study. All methodological choices are designed to ensure a fair, reproducible comparison across update policies, time-multiplexing reuse factors, and hardware constraints. The simulation parameters and sweep ranges are summarized in Table 5, and the benchmark instances are listed in Table 4.

### Simulation framework and timing

All simulations are performed using a custom Python-based framework that implements both synchronous and asynchronous p-bit update schemes, including explicit modeling of hardware delay and time-multiplexed reuse. Each logical spin $\sigma_i \in \{+1\}$ is updated according to the probabilistic rule defined in Eqs. (2)–(4).

For synchronous schemes, time is discretized into global ticks of duration $\Delta t$. In all synchronous simulations, we choose a hardware-oriented setting

$$\Delta t = \tau = d_i$$

corresponding to a fully clocked design in which each physical p-bit is updated once per tick and the updated state is applied at the subsequent tick.

For asynchronous schemes, updates occur in continuous time using a Gillespie-type event-driven procedure [35]. Each logical spin generates update events with effective rate

$$\lambda_{\text{spin}} = \frac{1}{\tau c},$$

and proposed updates are applied after a fixed delay $d$.

### Update-policy implementations

We evaluate one asynchronous and three synchronous update policies.

In addition, we use a sequential baseline as an algorithmic reference. In this mode, spins are updated one-by-one, and each updated state is immediately used to compute the local field for the next spin, so that one sweep over a system of $N$ spins corresponds to $N$ sequential single-spin updates. This baseline is included to provide a standard sequential Gibbs-like reference for comparison with parallel update policies. A strictly serialized hardware implementation of this procedure would require extremely high clock rates for large $N$, so it should not be interpreted as a practical hardware timing model, but rather as a conceptual algorithmic reference point.

**Gillespie (asynchronous).** Update events are generated in continuous time. At each event, a spin is selected and updated probabilistically based on its local field; the update state is applied after delay $d$. For asynchronous updates, the total simulation (annealing) time is matched to that of synchronous schemes.

**Tick-random (synchronous).** At each tick, an independent Bernoulli mask is generated with probability $p_{\text{spin}} = \Delta t / (\tau c) = 1/c$ for each spin. All selected spins are updated in parallel and applied after delay $d$.

**Tick-block-random (synchronous, contiguous).** Instead of generating a full random mask, a contiguous block of spins is selected at each tick. The block starting index is chosen uniformly at random, and the block length is set to

$$u = \lfloor p_{\text{spin}} N \rfloor = \left\lfloor \frac{N}{c} \right\rfloor.$$

**Tick-block-random-stride (synchronous, pseudo-contiguous).** This variant extends the block-random scheme by introducing a random stride $r$ biased to be coprime with $N$. The updated indices are $Z = \{(s + jr) \mod N\}_{j=0}^{u-1}$, which disperses spatial correlations while retaining simple and hardware-friendly address generation.

### Annealing schedule and quantization

The pseudo inverse temperature $I_0(t)$ is increased linearly from $I_{0,\min}$ to $I_{0,\max}$ over the total simulation time. We use

$$I_{0,\min} = \frac{0.1}{\sigma}, \quad I_{0,\max} = \frac{10}{\sigma}$$

where $\sigma = \sqrt{(N-1)\text{Var}[J_{\text{ij}}]}$ normalizes coupling statistics across problem instances [24].

Input fields are quantized using a b-bit DAC model. The DAC resolution $b$ is swept over the range listed in Table 5.

### Benchmarks and performance metrics

All evaluations are performed on G-set MaxCut benchmark instances summarized in Table 4. For each instance, the cut value obtained at the end of annealing is normalized by the best-known solution for that instance. Reported performance values correspond to the mean normalized cut value averaged across all G-set instances.

Unless otherwise stated, all results use a fixed total simulation time of 500 ns. This ensures that performance differences reflect architectural trade-offs rather than unequal annealing durations.

### Reproducibility

The full set of simulation parameters and sweep ranges is summarized in Table 5. All simulations are conducted using identical annealing schedules and delay assumptions across update policies to ensure a fair comparison. The simulation code used to generate the results is publicly available, enabling full reproducibility of the reported experiments.

## Conclusion

We have developed a unified performance–cost landscape for parallel p-bit Ising machines by jointly analyzing update synchronization, hardware delay, time-multiplexed p-bit reuse, and input-DAC precision under realistic hardware constraints. Through systematic simulations on benchmark Ising and QUBO problems, we demonstrated that the stability and efficiency of parallel p-bit annealing are governed not only by algorithmic update rules, but critically by the interaction between update statistics and hardware timing.

A central finding of this work is that synchronous architectures are not inherently prone to instability, as often assumed, but can achieve stable and efficient annealing dynamics when update simultaneity is properly controlled. By introducing time-multiplexed reuse of physical p-bits and structured synchronous control policies, we showed that the effective update rate can be reduced without altering the target stationary distribution, thereby decoupling statistical correctness from physical resource count.

This decoupling enables the number of physical p-bits and input DACs to scale approximately as the inverse of the time-multiplexing reuse factor, allowing synchronous architectures to access low-cost operating regimes that are fundamentally inaccessible to fully asynchronous updates. In contrast, asynchronous architectures are structurally constrained by hardware delay, requiring slower operation to maintain stability and preventing coordinated p-bit reuse.

We further demonstrated that input-DAC precision is a flexible design parameter rather than a strict requirement. Across a wide range of benchmark instances, near-optimal performance can be achieved using low-resolution input DACs (typically 3–4 bits) when annealing time is appropriately adjusted, enabling additional reductions in hardware area and power.

Taken together, these results establish time-multiplexed reuse combined with structured synchronous control as a key architectural principle for scalable probabilistic computing hardware, and provide reproducible design guidance for balancing solution quality, hardware cost, and timing constraints under realistic delay and precision limitations.

## Data availability

The Python simulation code used to generate the results in this study is publicly available in a GitHub repository [36].

## References

[1] Gaulet, V. C. & Gross, W. J. Stochastic Computing: Techniques and Applications (Springer International Publishing, 2019).

[2] Chowdhury, S. et al. A full-stack view of probabilistic computing with p-bits: devices, architectures, and algorithms. arXiv 2302.06457 (2023).

[3] Borders, W. A. et al. Integer factorization using stochastic magnetic tunnel junctions. Nature 573, 390–393 (2019). https://doi.org/10.1038/s41586-019-1557-9

[4] Camsari, K. Y., Sutton, B. M. & Datta, S. p-bits for probabilistic spin logic. Applied Physics Reviews 6, 011305 (2019).

[5] Camsari, K. Y., Sutton, B. M. & Datta, S. Hardware emulation of stochastic p-bits for invertible logic. Scientific Reports 7, 11011 (2017). https://www.nature.com/articles/s41598-017-11011-8

[6] Camsari, K. Y., Salahuddin, S. & Datta, S. Stochastic p-bits for invertible logic. Physical Review X 7, 031014 (2017).

[7] Smithson, S. C., Onizawa, N., Meyer, B. H., Gross, W. J. & Hanyu, T. In-hardware training of invertible logic using stochastic computing. IEEE Transactions on Circuits and Systems I: Regular Papers 66, 2263–2274 (2019).

[8] Kirkpatrick, S., Gelatt Jr, C. D. & Vecchi, M. P. Optimization by simulated annealing. Science 220, 671–680 (1983).

[9] Hayakawa, K. et al. Nanosecond random telegraph noise in in-plane magnetic tunnel junctions. Physical Review Letters 126, 117202 (2021). https://doi.org/10.1038/s41586-019-1557-9

[10] Safranski, C. et al. Demonstration of nanosecond operation in stochastic magnetic tunnel junctions. Nano Letters 21, 2040–2045 (2021).

[11] Daniel, J. et al. Experimental demonstration of on-chip p-bit core based on stochastic magnetic tunnel junctions and 2d mos2 transistors. Nature Communications 15, 4098 (2024). https://doi.org/10.1038/s41467-024-48152-0

[12] Onizawa, N., Smithson, S. C., Meyer, B. H., Gross, W. J. & Hanyu, T. In-hardware training chip based on cmos invertible logic for machine learning. IEEE Transactions on Circuits and Systems I: Regular Papers 67, 1541–1550 (2020).

[13] Kaiser, J. et al. Hardware-aware in situ learning based on stochastic magnetic tunnel junctions. Physical Review Applied 17, 014016 (2022). https://doi.org/10.1103/PhysRevApplied.17.014016

[14] Grimaldi, A. et al. Spintronics-compatible approach to solving maximum-satisfiability problems with probabilistic computing, introduction and review. Reports on Progress in Physics 85, 104001 (2022). https://doi.org/10.1088/1361-6633/ac35c4

[15] Andor, N. et al. Massively parallel probabilistic computing with sparse ising machines. Nature Electronics 5, 460–468 (2022). https://doi.org/10.1038/s41928-022-00774-2

[16] Onizawa, N., Katsuki, K., Shin, D., Gross, W. J. & Hanyu, T. Fast-converging simulated annealing for ising machines based on stochastic computing. IEEE Transactions on Neural Networks and Learning Systems 34, 10999–11005 (2023). https://ieeexplore.ieee.org/document/9743572

[17] Onizawa, N., Sasaki, R., Shin, D., Gross, W. J. & Hanyu, T. Stochastic simulated quantum annealing for fast solution of combinatorial optimization problems. IEEE Access 12, 102050–102060 (2024).

[18] Aramon, M. et al. Physics-inspired optimization for quadratic unconstrained problems using a digital annealer. Frontiers in Physics 7, 48 (2019). https://www.frontiersin.org/articles/10.3389/fphy.2019.00048

[19] Wang, Z., Marandi, A., Wen, K., Byer, R. L. & Yamamoto, Y. Coherent ising machine based on degenerate optical parametric oscillators. Physical Review A 88, 063853 (2013). https://doi.org/10.1103/PhysRevA.88.063853

[20] Goto, H., Tatsumura, K. & Dixon, A. R. Combinatorial optimization by simulating adiabatic bifurcations in nonlinear hamiltonian systems. Science Advances 5, eaav2372 (2019).

[21] Kadowaki, T. & Nishimori, H. Quantum annealing in the transverse ising model. Physical Review E 58, 5355–5363 (1998).

[22] Yarkoni, S., Raponi, E., Bäck, T. & Schmitt, S. Quantum annealing for industry applications: introduction and review. Reports on Progress in Physics 85, 104001 (2022).

[23] Ye, Y. Computational optimization laboratory (1999). https://web.stanford.edu/~yyye/Codes.html

[24] Onizawa, N. & Hanyu, T. Enhanced convergence in p-bit based simulated annealing with partial deactivation for large-scale combinatorial optimization problems. Scientific Reports 14, 1339 (2024). https://www.nature.com/articles/s41598-024-51639-7

[25] Weigel, M. Performance potential of parallel monte carlo simulations of spin models. Journal of Computational Physics 231, 3064–3082 (2012).

[26] Levin, D. A., Peres, Y. & Wilmer, E. L. Markov Chains and Mixing Times (American Mathematical Society, 2009).

[27] De Sa, C., Olukotun, K. & Ré, C. Ensuring rapid mixing and low bias for asynchronous Gibbs sampling. Proceedings of Machine Learning Research 48 (2016). https://proceedings.mlr.press/v48/de16.html

[28] Gonzalez, J. E., Low, Y., Gu, H., Bickson, D. & Guestrin, C. Parallel gibbs sampling: From colored fields to thin junction trees. Proceedings of the Fourteenth International Conference on Artificial Intelligence and Statistics (AISTATS) (2011). https://proceedings.mlr.press/v15/gonzalez11a/gonzalez11a.pdf

[29] Terenin, A., Simpson, D. & Draper, D. Asynchronous Gibbs sampling. Bernoulli 22, 2459–2488 (2016).

[30] Johnson, T., Saunderson, J. & Willsky, A. Analyzing hogwild parallelism in gibbs sampling. Advances in Neural Information Processing Systems 26 (2013).

[31] Bertsekas, D. P. & Tsitsiklis, J. N. Parallel and Distributed Computation: Numerical Methods (Prentice Hall, 1989).

[32] Si, J. et al. Energy-efficient superparamagnetic ising machine and its application to traveling salesman problems. Nature Communications 15, 3457 (2024).

[33] Nin, F., Recht, B., Re, C. & Wright, S. Hogwild!: A lock-free approach to parallelizing stochastic gradient descent. Advances in Neural Information Processing Systems 24 (2011).

[34] Selcuk, K. et al. Dac-free p-bits: Asynchronous self-coloring and on-chip annealing. In Proceedings of the IEEE International Electron Devices Meeting (IEDM) (2025).

[35] Gillespie, D. T. Exact stochastic simulation of coupled chemical reactions. Journal of Physical Chemistry 81, 2340–2361 (1977).

[36] Onizawa, N. parallel_pbit. https://github.com/nonizawa/parallel_pbit (2026). Accessed: 2026-01-06.

## Funding

This research was supported in part by KIOXIA Corporation and by a research grant from the Murata Science and Education Foundation.

## Author contributions statement

N. O. conducted and analyzed the experiments. T. H. discussed the experiment. All authors reviewed the manuscript.

## Additional information

Competing financial interests: The authors declare no competing financial interests.
