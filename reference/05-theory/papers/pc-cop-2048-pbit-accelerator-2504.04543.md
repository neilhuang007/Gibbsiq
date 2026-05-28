# pc-COP: An Efficient and Configurable 2048-p-Bit Fully-Connected Probabilistic Computing Accelerator for Combinatorial Optimization

**Kiran Magar***†, Shreya Bharathan†, and Utsav Banerjee*

*Electronic Systems Engineering, Indian Institute of Science, Bengaluru, India  
†National Institute of Technology, Tiruchirapalli, India

Email: kirankailash@iisc.ac.in, shreyabharat2306@gmail.com, utsav@iisc.ac.in

## Abstract

Probabilistic computing is an emerging quantum-inspired computing paradigm capable of solving combinatorial optimization and various other classes of computationally hard problems. In this work, we present pc-COP, an efficient and configurable probabilistic computing hardware accelerator with 2048 fully connected probabilistic bits (p-bits) implemented on a state-of-the-art Xilinx UltraScale+ FPGA. We propose a pseudo-parallel p-bit update architecture with speculate-and-select logic which improves overall performance by $4\times$ compared to the traditional sequential p-bit update. Using our FPGA-based accelerator, we demonstrate the standard G-Set graph maximum cut benchmarks with near-99% average accuracy. Compared to state-of-the-art hardware implementations, we achieve similar performance and accuracy with lower FPGA resource utilization.

**Index Terms**— probabilistic computing, fully connected, FPGA, hardware accelerator, combinatorial optimization, Ising machine, G-Set, K2000, max-cut.

## I. INTRODUCTION

Quantum computing [1]–[3] is a pioneering paradigm in computation which applies the principles of quantum mechanics to revolutionize problem-solving capabilities. Unique quantum phenomena such as superposition and entanglement enable quantum computers to tackle complex problems with exponential speedup. While quantum computing holds tremendous potential, it is still in the nascent stages of development and faces significant challenges on its path to practicality and widespread adoption. A major hurdle is stability and coherence, as quantum systems are highly susceptible to environmental noise and decoherence, which can introduce errors and significantly limit their computational power. Additionally, the development of scalable quantum hardware poses a formidable challenge, requiring advancements in fabrication techniques, error correction methods, cooling systems and the integration of control electronics. Addressing these challenges requires interdisciplinary collaboration and sustained investment in fundamental engineering to unlock the transformative capabilities of quantum computing. These challenges have motivated the emergence of many new physics-inspired computing models such as probabilistic computing [6], simulated annealing [7], probabilistic annealing [8] and parallel tempering [9]. These quantum-inspired algorithms are implemented on classical hardware and draw upon some principles and strategies from quantum computing to significantly enhance the performance of classical algorithms to address specific computational challenges.

Probabilistic computing is one of the emerging quantum-inspired computing paradigms and it involves the manipulation of unstable stochastic units known as *probabilistic bits* or *p-bits*. Multiple p-bits are interconnected together to construct probabilistic circuits or p-circuits. Fig. 1 compares the three computing paradigms: classical (digital), quantum and probabilistic. The basic building blocks of classical computing are bits which are deterministically either 0 or 1. The basic building blocks of quantum computing are quantum bits or qubits which can be in a superposition of 0 and 1. In contrast, probabilistic bits or p-bits rapidly fluctuate between 0 and 1. While qubits require near-absolute-zero temperatures for accurate functionality, such p-bits and p-circuits can be realized at room temperature. Although probabilistic computers are not expected to be a direct replacement for quantum computers, they enable novel applications at the intersection of classical and quantum computing using existing as well as emerging hardware technologies [10], [11]. Unlike classical bits which are deterministically either 0 or 1 and quantum bits (qubits) which can exist in a superposition of 0 and 1, p-bits rapidly fluctuate between 0 and 1. While qubits require near-absolute-zero temperatures for accurate functionality, such p-bits and p-circuits can be realized at room temperature, thus enabling novel applications at the intersection of classical and quantum hardware using existing as well as emerging technologies [10], [11]. Recent literature has demonstrated the immense potential of probabilistic computing using various software and hardware implementation platforms such as micro-controllers [12], general purpose micro-processors (GPUs) [13]–[15], field-programmable gate arrays (FPGAs) [16], magnetic tunnel junctions (MTJs) [17], resistive random-access memories (RRAMs) [18], ferro-electric field-effect transistors (FeFETs) [19] and threshold switch devices (TSDs) [20]. However, these hardware implementations have been limited to either small-scale p-circuits using emerging nano-devices or preliminary architectures using FPGAs. They have limited circuit-level analysis, thus leaving plenty of room for design space exploration and algorithm-specific architectural improvement.

Combinatorial optimization [21], [22] is an important class of hard problems which can be solved efficiently using probabilistic computing. In this work, we present pc-COP, an efficient and configurable probabilistic computing hardware accelerator with 2048 fully connected p-bits implemented on state-of-the-art Xilinx UltraScale+ FPGA. It is capable of solving large-scale graph maximum cut combinatorial optimization problems [7], [24] with high accuracy. Our logarithmic adder tree design for sum-of-products computation boosts overall performance. We approximate the activation function and tune the precision of the annealing schedule to reduce FPGA resource utilization. Our proposed pseudo-parallel p-bit update architecture with speculate-and-select logic improves performance by $4\times$ compared to the traditional sequential p-bit update. We implement pc-COP on a Xilinx Zynq UltraScale+ MPSoC ZCU104 Evaluation Board and demonstrate near-99% average accuracy across various G-Set maximum cut benchmarks up to 2,000 nodes [25].

The rest of the paper is organized as follows: Section II summarizes the theory of probabilistic computing and its application to combinatorial optimization problems such as graph max-cut. Section III describes the details of our proposed accelerator hardware architecture. Section IV presents detailed FPGA-based implementation results and Section V provides concluding remarks and future directions.

## II. BACKGROUND

### A. Probabilistic Computing

Probabilistic computing is an emerging quantum-inspired computing paradigm capable of solving many interesting problems such as combinatorial optimization, machine learning, quantum emulation and integer factorization [5], [26]–[30]. The operation of a p-bit can be represented as a binary stochastic neuron, as shown in Fig. 2. The operation of a p-circuit with several p-bits is described in Algorithm 1. The p-bit update equation $(I_i = -\beta \cdot (h_i + \sum_{j=1}^{N_m} J_{i,j} m_j ))$ resembles Boltzmann machines [8] while the sequential nature of the update resembles the sequential nature of the update in Ising machines [28] while the sequential nature of the update assembles the the stochastic Ising machines [28] while the sequential nature of the update assembles the typical evolution in Ising machines [31]. The energy of the system with state $m$ is defined as $E(\{m\}) = -(\sum_{i,j} J_{i,j} m_i m_j + \sum_i h_i m_i)$ which again resembles the quadratic energy model in Ising machines [31]. The inherent stochasticity and non-linear activation function in each p-bit, which is a unique feature of probabilistic computing, ensures that various states $m$ are visited according to their corresponding Boltzmann probability $p_{\{m\}} \propto \exp(-\beta E(\{m\}))$, where $\beta$ acts as an inverse pseudo-temperature which can enhance or suppress probabilities based on energy minima. The system of p-bits evolves over consecutive samples to converge towards a low-energy state corresponding to an optimum or near-optimal solution of the problem encoded in the p-circuit. The value of $\beta$ can be tuned across samples to achieve better convergence, which bears resemblance to simulated annealing [28], [31]. Recent literature has explored the use of emerging technologies to efficiently realize the p-bit functionality in hardware [5], [13], [17]–[20], [26], [32]. Both large-scale implementations of p-circuits using emerging nano-devices are yet to be demonstrated experimentally. Therefore, FPGA-based implementations offer a promising near-term alternative. Preliminary FPGA-based architectures have been demonstrated in [16], [27], [33]. However, detailed circuit-level analysis and architectural optimizations for probabilistic computing are yet to be explored. In this work, we bridge this gap by providing comprehensive analysis of the compute and memory bottlenecks, resource usage on state-of-the-art FPGA, algorithm-specific optimizations, design space exploration, hardware implementation and experimental results.

### B. Combinatorial Optimization Problems

Combinatorial optimization is a sub-field of mathematical optimization which involves finding the optimal solution out of a finite but large set of possibilities where exhaustive search is intractable [21], [22]. Combinatorial optimization is a sub-field of mathematical optimization which involves finding the optimal solution out of a finite set of possibilities. Examples of combinatorial optimization problems (COPs) include the graph maximum cut problem, the traveling salesman problem, the minimum spanning tree problem and the knapsack problem [21], [22]. Solving COPs is fundamental to various real-world applications such as VLSI design, machine learning, bioinformatics, telecommunications, software engineering, finance and data management. Solving large scale COPs using exhaustive search is intractable, thus necessitating specialized techniques such as dynamic programming, approximation algorithms, metaheuristics, hill climbing and simulated annealing. Ising machines have gained significant interest due to their ability to efficiently compute optimal or near-optimal solutions to such problems [21], [22]. In this work, we explore the efficacy of probabilistic computing in solving the prototypical combinatorial problem (COP) of graph maximum cut, also known as max-cut [7]. The max-cut problem is to partition the vertices $V$ of a graph $G = (V, E)$ into two complementary sets $S$ and $\bar{S}$ such that the number of edges $(E \in [between~S~and~\bar{S}]$ is as large as possible. The corresponding p-circuit can be constructed by assigning a p-bit $m_i$ corresponding to each vertex $v_i$. Then, the p-bit solution will result in $m_i = +1$ if $v_i \in S$ and $m_i = -1$ if $v_i \in \bar{S}$ such that the objective function $\sum_{i,j} w_{i,j} m_i m_j$ is minimized, where $w_{i,j}$ is the weight of the edge connecting vertices $v_i$ and $v_j$ [24]. Therefore, the p-bit interaction coefficients are obtained as $J_{i,j} = -w_{i,j}$ and $h_i = 0$. The Stanford G-Set benchmark dataset [25], containing various random, toroidal and planar graphs, is typically used to evaluate max-cut solver implementations. G-Set contains graphs with $w_{i,j} \in \{0, 1\}$ as well as $w_{i,j} \in [-1, 0, +1]$, so we need 2-bit interaction coefficients $J_{i,j}$. This work presents an FPGA-based 2048-p-bit probabilistic computing accelerator demonstrating near-99% average accuracy across G-Set max-cut benchmarks up to 2,000 nodes.

## III. HARDWARE ARCHITECTURE

Fig. 3 shows the top-level architecture of pc-COP, our proposed hardware accelerator for solving large-scale max-cut COPs using probabilistic computing. It supports max-cut instances up to 2048 nodes using 2048 p-bits stored in the 2048-bit register m_Reg, where -1 and +1 p-bit values are encoded as 0 and 1 respectively. According to step 2 of Algorithm 1, the initial random state of the p-bit register m_Reg is configured using a 2048-bit random input. The corresponding 2048×2048 interaction matrix J of 2-bit interaction coefficients $J_{i,j}$ are required. The Stanford G-Set benchmark dataset [25], containing various random, toroidal and planar graphs with $w_{i,j} \in \{0, 1\}$ as well as $w_{i,j} \in [-1, 0, +1]$, so we need 2-bit interaction coefficients $J_{i,j}$. This work presents an FPGA-based 2048-p-bit probabilistic computing accelerator demonstrating near-99% average accuracy across G-Set max-cut benchmarks up to 2,000 nodes.

as well as $w_{i,j} \in [-1, 0, +1]$, so we need 2-bit interaction coefficients $J_{i,j}$. This work presents an FPGA-based 2048-p-bit probabilistic computing accelerator demonstrating near-99% average accuracy across G-Set max-cut benchmarks up to 2,000 nodes.

as $w_{i,j} \in \{0, 1\}$ as well as $w_{i,j} \in [-1, 0, +1]$, so we need 2-bit interaction coefficients $J_{i,j}$. This work presents an FPGA-based 2048-p-bit probabilistic computing accelerator demonstrating near-99% average accuracy across G-Set max-cut benchmarks up to 2,000 nodes.

The corresponding 2048×2048 interaction matrix $J$ of 2-bit interaction coefficients $J_{i,j}$ are required. The Stanford G-Set benchmark dataset [25], containing various random, toroidal and planar graphs with $w_{i,j} \in \{0, 1\}$ as well as $w_{i,j} \in [-1, 0, +1]$, so we need 2-bit interaction coefficients $J_{i,j}$. This work presents an FPGA-based 2048-p-bit probabilistic computing accelerator demonstrating near-99% average accuracy across G-Set max-cut benchmarks up to 2,000 nodes.

as well as $w_{i,j} \in [-1, 0, +1]$, so we need 2-bit interaction coefficients $J_{i,j}$. This work presents an FPGA-based 2048-p-bit probabilistic computing accelerator demonstrating near-99% average accuracy across G-Set max-cut benchmarks up to 2,000 nodes.

as $w_{i,j} \in \{0, 1\}$ as well as $w_{i,j} \in [-1, 0, +1]$, so we need 2-bit interaction coefficients $J_{i,j}$. This work presents an FPGA-based 2048-p-bit probabilistic computing accelerator demonstrating near-99% average accuracy across G-Set max-cut benchmarks up to 2,000 nodes.

The corresponding 2048×2048 interaction matrix $J$ of 2-bit interaction coefficients are required. The Stanford G-Set benchmark dataset [25], containing various random, toroidal and planar graphs is typically used to evaluate max-cut solver implementations. G-Set contains graphs with $w_{i,j} \in \{0, 1\}$ as well as $w_{i,j} \in [-1, 0, +1]$, so we need 2-bit interaction coefficients $J_{i,j}$. This work presents an FPGA-based 2048-p-bit probabilistic computing accelerator demonstrating near-99% average accuracy across G-Set max-cut benchmarks up to 2,000 nodes.

as well as $w_{i,j} \in [-1, 0, +1]$, so we need 2-bit interaction coefficients $J_{i,j}$. This work presents an FPGA-based 2048-p-bit probabilistic computing accelerator demonstrating near-99% average accuracy across G-Set max-cut benchmarks up to 2,000 nodes.

The J_Mem memory is configured with the problem-specific $J$ matrix 32 bits at a time using the 18-bit address input and an address decoder. The functionality of Algorithm 1 is implemented in the p-Bit Update Core and managed by a Finite State Machine (FSM) and control registers. A 512-bit seed input is used to configure the stochasticity in the p-bit update circuitry. The logically organized 2048×2048 interaction matrix allows for efficient reading of an entire row of $J$ in a single cycle via speculate-and-select architecture.

**Algorithm 1** Overview of p-circuit operation [5], [26]

**Require:** number of p-bits $N_m$, interconnection weight matrix $J = [J_{i,j}]_{N_m \times N_m}$ and bias vector $h = [h_i]_{N_m \times 1}$ for application-specific p-circuit, number of samples $N_s$

**Ensure:** final p-bit state $m = \{m_i \mid 1 \leq i \leq N_m\}$

1: define p-bit state $m = \{m_i\}$
2: randomly initialize p-bits $m_i \in \{-1, +1\} \; \forall 1 \leq i \leq N_m$
3: **for** $(s = 1; s \leq N_s; s = s + 1)$ **do**
4: **for** $(i = 1; i \leq N_m; i = i + 1)$ **do**
5: $I_i \leftarrow -\beta \cdot (h_i + \sum_{j=1}^{N_m} J_{i,j} m_j)$
6: $m_i \leftarrow \text{sgn}(\text{rand}(-1, +1) + \tanh(I_i))$
7: **end for**
8: **end for**
9: **return** $m = \{m_i \mid 1 \leq i \leq N_m\}$

## IV. IMPLEMENTATION RESULTS

We implement and validate our proposed accelerator on a Xilinx Zynq UltraScale+ MPSoC ZCU104 Evaluation Board with an XC7Z156E device [23] using Verilog HDL and Xilinx Vivado Design Suite version ML 2022.2. Its programmable logic (PL) contains 230k look-up tables (LUTs) and 461 configurable logic blocks (CLBs), 312 Block RAMs (BRAMs) and 1,728 digital signal processing (DSP) slices, while its processing system (PS) consists of a quad-core ARM Cortex-A53 micro-processor. Vivado HDL (Hardware Description Language) is used to design the hardware accelerator, and Xilinx Vivado Design Suite version ML 2022.2 is utilized for FPGA synthesis, implementation and simulation. Our implementation with 4-way pseudo-parallel p-bit update operates at a clock frequency of 100 MHz, and utilizes 37k LUTs, 95k FFs, 17 DSPs (≈ 7k LUTs) and 256 BRAMs (8 MB) in UltraScale+ FPGA.

Python-based PYNQ software framework provided by Xilinx. We use the standard G-Set max-cut benchmark graphs [25] with versions containing 800, 1000 and 2000 nodes to evaluate the performance and accuracy of our design with the 4-way pseudo-parallel p-bit update as detailed in Section III-A. We conduct 1000 trials for each G-Set benchmark for both $N_s = 1000$ and $N_s = 100$ (with the annealing hyper-parameters discussed in Section III-A) to obtain a reasonable distribution of the accuracy of results (accuracy calculated relative to best known cut values from state-of-the-art [25]). Table II compares our design with previous work on FPGA-based hardware accelerators demonstrating max-cut with G-Set benchmarks. Most of the previous designs are digital annealers and Ising computers implemented using CPU and GPU [7], options [40] and FPGA [8], [41]. While there are many other implementations of FPGA-based digital annealers, we only include those which specifically demonstrated G-Set benchmarks on fair comparisons. [13] is a CPU-based demonstration of G-Set max-cut with probabilistic computing. Compared to previous CPU and GPU-based implementations, we achieve 3 orders of magnitude speedup while maintaining similar accuracy levels. Compared to previous FPGA-based digital annealer implementations, we achieve reasonably comparable performance and accuracy with the new probabilistic computing paradigm while having lower FPGA resource utilization. This clearly demonstrates that hardware-accelerated probabilistic computing is an excellent candidate for realizing efficient and large-scale combinatorial optimization problem solvers.

The detailed experimental results from our FPGA-based hardware implementation are presented in Table II with the best cut value and average accuracy (across 1000 trials) obtained for each benchmark graph. Table II compares our design with previous work on FPGA-based hardware accelerators demonstrating max-cut with G-Set benchmarks. Most of the previous designs are digital annealers and Ising computers implemented using CPU and GPU [7], options [40] and FPGA [8], [41]. While there are many other implementations of FPGA-based digital annealers, we only include those which specifically demonstrated G-Set benchmarks on fair comparisons. [13] is a CPU-based demonstration of G-Set max-cut with probabilistic computing. Compared to previous CPU and GPU-based implementations, we achieve 3 orders of magnitude speedup while maintaining similar accuracy levels. Compared to previous FPGA-based digital annealer implementations, we achieve reasonably comparable performance and accuracy with the new probabilistic computing paradigm while having lower FPGA resource utilization. This clearly demonstrates that hardware-accelerated probabilistic computing is an excellent candidate for realizing efficient and large-scale combinatorial optimization problem solvers.

## V. CONCLUSION

Probabilistic computing is an emerging quantum-inspired computing paradigm capable of solving various classes of computationally hard problems such as combinatorial optimization. In this work, we present pc-COP, an efficient and configurable probabilistic computing hardware accelerator with 2048 fully connected p-bits implemented on Xilinx UltraScale+ FPGA and demonstrate the standard G-Set graph maximum cut benchmarks. Our efficient logarithmic adder tree design for sum-of-products computation reduces critical path delay. We efficiently approximate the activation function and tune the precision of the annealing schedule to save logic resources. Finally, we propose a pseudo-parallel p-bit architecture with speculate-and-select logic which improves overall performance by $4\times$ compared to the traditional sequential p-bit update. We achieve near-99% average accuracy across various G-Set max-cut benchmarks with 800, 1000 and 2000 nodes. Our FPGA-based probabilistic computing hardware accelerators are promising practical systems for efficiently solving large-scale combinatorial optimization problems. Future extensions of our work will explore larger designs with high-precision interaction coefficients, efficient memory architectures exploiting sparsity, problem-specific tuning of hyper-parameters and extensions to other problems such as traveling salesman and Boolean satisfiability.

## ACKNOWLEDGMENT

This work was supported in part by a seed grant from the Indian Institute of Science and in part by a Ph.D. Scholarship from the Ministry of Education, Government of India. The authors would like to thank Yashash Jain for helpful technical discussions and Dr. Shantharam Kalipatapu for helping set up the PYNQ interface.

## REFERENCES

[1] R. P. Feynman, "Simulating Physics with Computers," *International Journal of Theoretical Physics*, vol. 21, no. 6/7, 1982.

[2] M. A. Nielsen and I. L. Chuang, *Quantum Computation and Quantum Information*. Cambridge University Press, 2010.

[3] D. W. Aharonov, "Quantum-Time Prime Factorization and Discrete Logarithms on a Quantum Computer," *SIAM Journal of Computing*, vol. 26, no. 5, pp. 1484–1509, 1997.

[4] M. H. Devoret and R. J. Schoelkopf, "Superconducting Circuits for Quantum Information," *Nature*, vol. 574, no. 7779, pp. 505–510, 2019.

[5] K. V. Gambhir, R. Ramanathan, B. M. Sutton, and S. Datta, "Stochastic Computing using p-Bits for Invertible Logic," *Phys. Rev. X*, vol. 7, p. 031014, 2017.

[6] S. Chowdhury et al., "Efficient Coherent Invertible Logic Stochastic Computing," *IEEE Transactions on Circuits and Systems I*, vol. 66, no. 8, pp. 2820–2834, 2019.

[7] C. Cook et al., "GPU-Based Ring Computing for Solving Max-Cut Combinatorial Optimization Problems," *Integration*, vol. 69, pp. 333–344, 2019.

[8] H. Jing et al., "A Quantum-Inspired Probabilistic Prime Factorization and Discrete Logarithms on a Quantum Simulator," *Nature*, vol. 119, no. 15, pp. 16186–16223, 2023.

[9] V. Zuev et al., "A Parallel Tempering Processing Architecture with Multi-Spin Update for Fully Connected Ising Models," in *IEEE Design, Automation and Test in Europe Conference* (DATE), 2024.

[10] S. Kunasamy and S. Datta, "Dialogue Concerning the Two Chief Computing Systems: Imagine Yourself on a Flight Talking to an Engineer About Stochastic Bit Switching," *IEEE J. Exploratory Solid-State Computational Devices and Circuits*, vol. 9, pp. 4–6, 2023.

[11] S. Chowdhury et al., "A Full-Stack View of Probabilistic Computing with p-Bits: Technologies and Algorithms," *IEEE J. Exploratory Solid-State Computational Devices and Circuits*, vol. 9, pp. 1–11, 2023.

[12] A. Z. Pervaz et al., "Hardware Emulation of Stochastic p-Bits for Inverted-Logic," *Nature Systems Review*, vol. 7, no. 1094, Sep. 2017.

[13] M. Khan and O. Hassan, "Benchmarking of Probabilistic-Bit Based Algorithm for Max-Cut Problem," in *International Conference on Electronics* (ICCE), IEEE, 2022, pp. 433–445.

[14] N. Onizawa et al., "Pseudo-Computing Simulated Annealing," *IEEE Transactions on Neural Networks and Learning Systems*, vol. 34, no. 4, pp. 11995–12005, 2023.

[15] N. Onizawa and T. Hanyu, "Enhanced Convergence in p-Bit Simulated Annealing with Parallel Dissociation Designs," *Nature Scientific Reports*, vol. 14, no. 1, pp. 1830–1852, 2024.

[16] A. Z. Pervaz, "Weighted p-Bits: FPGA Implementation of Probabilistic Circuits," *IEEE Transactions on Circuits and Systems II*, vol. 30, no. 9, pp. 1920–1926, Dec. 2019.

[17] W. A. Borders, A. Z. Pervaz, S. Akam, B. N. Akram, H. Ohno, and S. Miwa, "Integer Factorization Using Stochastic Magnetic Tunnel Junctions," *Nature*, vol. 573, no. 7774, pp. 390–393, Sep. 2019.

[18] Y. Liu et al., "Probabilistic Circuit Implementation Based on p-Bits in Hybrid Multiplexing," *Microelectronics*, vol. 81, no. 6, pp. 7–20, 2022.

[19] S. Luo, Y. He, B. Cai, X. Gong, and G. Liang, "Probabilistic-Bits Based Ferroelectric Transistors for Probabilistic Computing," *IEEE Electron Device Letters*, vol. 44, no. 8, pp. 1356–1359, 2023.

[20] S. Heo et al., "Experimental Demonstration of Probabilistic-Bit (p-bit) Utilizing Stochastic Oscillation of Threshold Switch Devices," *IEEE Symposium on VLSI Technology and Circuits*, pp. 1–2, 2023.

[21] N. A. Aadit et al., "Computing with Invertible Logic: Combinatorial Optimization," *Physics*, vol. 2, p. 74887, 2014.

[22] N. Mohamdi, P. L. McMahon, and T. Byrnes, "Ising Machines as Hardware Solvers of Combinatorial Optimization Problems," *Nature Reviews Physics*, vol. 4, no. 6, pp. 363–379, 2022.

[23] Xilinx Inc., "UltraScale Architecture: Staying a Generation Ahead with an Extra Node of Value," https://www.xilinx.com/products/technology/ultascale.html.

[24] V. Matsuda, "Benchmarking the MAX-CUT Problem on the Simulated Bifurcation Machine," Medium, 2019, https://medium.com/tadipha-shm/benchmarking-the-max-cut-problem-on-the-simulated-bifurcation-machine-e26e1127c0b0.

[25] Stanford University, "G-Set Graph Dataset," https://web.stanford.edu/%7Eyyye/yyye/Gset.

[26] K. Y. Camsari, B. M. Sutton, and S. Datta, "p-Bits for Probabilistic Spin Logic," *Applied Physics Reviews*, vol. 6, no. 1, Mar. 2019.

[27] Y. Jain and I. Jhangiani, "Psyche: A Compact and Configurable Accelerator for Scalable Probabilistic Computing on FPGA," in *IEEE High Performance Extreme Computing Conference* (HPEC), 2023, pp. 1–7.

[28] S. Kirkpatrick, C. D. Gelatt, and M. P. Vecchi, "Optimization by Simulated Annealing," *Science*, vol. 220, no. 4598, pp. 671–680, 1983.

[29] N. A. Aadit et al., "Computing with Invertible Logic: Combinatorial Optimization," *IEEE Journal of Exploratory Solid-State Computational Devices and Circuits*, vol. 7, no. 1, pp. 43–51, 2021.

[30] K. W. Ku et al., "Computing with Invertible Logic: Combinatorial Optimization," *IEEE Journal of Exploratory Solid-State Computational Devices and Circuits*, vol. 7, no. 1, pp. 43–51, 2021.

[31] N. A. Aadit and S. Bhanja, "Associating Adaptive Parallel Tempering with FPGA-based p-Bits," in *IEEE Symposium on VLSI* (ISVLSI), 2023, pp. 1–6.

[32] A. Grimaldi et al., "Experimental Evaluation of Simulated Quantum Annealing with MTJ-Augmented p-Bits," in *International Electron Devices Meeting* (IEDM), Dec. 2021, pp. 40–3.

[33] N. A. Aadit, M. Mohseni, and K. Y. Camsari, "Accelerating Adaptive Parallel Tempering with FPGA-based p-Bits," in *IEEE Symposium on VLSI* (ISVLSI), 2023, pp. 1–6.

[34] N. Onizawa, K. Sumi, D. Sun, and T. Hanyu, "Local Energy Distribution Annealing: A Simple Yet Effective Method for Stochastic Simulated Annealing," *IEEE Journal of Exploratory Solid-State Computational Devices and Circuits*, vol. 4, pp. 452–461, 2023.

[35] J. M. Rabaey, A. P. Chandrakasan, and B. Nikolic, *Digital Integrated Circuits: A Design Perspective*, 2nd ed. Prentice Hall, 2002.

[36] N. H. E. Weste and D. M. Harris, *CMOS VLSI Design: A Circuits and Systems Perspective*. Addison-Wesley, 2011.

[37] R. Ward and J. Molteno, "Table of Linear Feedback Shift Registers," *University of Otago*, Tech. Rep., Oct. 2007.

[38] K. E. Murray, V. Petrov, S. Liu, C. Zhong, Y. Wang, M. A. Khalid, et al., "VTR 8: High-Performance CAD and Customizable FPGA Architecture Modeling," *ACM Transactions on Reconfigurable Technology and Systems* (TRETS), vol. 11, no. 2, pp. 7:1–7:23, 2018.

[39] Y. Zhang et al., "Ultra-High Polynomial Multiplications for FPGAs," *IEEE Transactions on Emerging Topics in Computing*, vol. 10, no. 4, pp. 2074–3078, 2023.

[40] T. Inagaki et al., "A Coherent Ising Machine for 2000-Node Optimization," *Science*, vol. 354, no. 6312, pp. 603–606, 2016.

[41] N. A. Aadit et al., "Integrated Ising Model Solver on a Scalable and Reconfigurable Photonic Hardware," in *IEEE International Symposium on Circuits and Systems* (ISCAS), 2023, pp. 1–5.

[42] H. M. Waddyassooriya and M. Hariyama, "Temporal and Spatial Parallel Processing of Simulated Quantum Annealing on a Multicore CPU," *The Journal of Supercomputing*, pp. 1–18, 2022.

[43] C. Yoshimura et al., "CMOS Annealing Machine: A Domain-Specific Architecture for Combinatorial Optimization Problems," *ACM Transactions on Design Automation of Electronic Systems* (TODAES), vol. 25, no. 6, pp. 673–678, 2020.

[44] S. Xie et al., "Time-CIM: A Reconfigurable and Scalable Compute Within Memory Analog Ising Accelerator for Solving Combinatorial Optimization Problems," *IEEE Journal of Solid-State Circuits*, vol. 57, no. 11, pp. 3453–3465, 2022.
