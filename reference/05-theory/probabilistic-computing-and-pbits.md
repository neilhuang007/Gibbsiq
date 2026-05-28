# Theory References

## Gibbs / THRML

Target distribution:

```text
P(s) proportional to exp(-beta * E(s))
```

Block Gibbs updates non-interacting variable blocks from conditionals.

Sources:

- THRML docs: https://docs.thrml.ai/
- THRML probabilistic computing: https://docs.thrml.ai/en/latest/examples/00_probabilistic_computing/
- Extropic essay: http://extropic.ai/writing/thermodynamic-computing-from-zero-to-one

## p-Bits

p-bits are stochastic binary units with tunable mean. Networks implement correlated stochastic spin systems and invertible logic.

Common local input form:

```text
I_i = beta * (h_i + sum_j J_ij m_j)
```

Sources:

- Stochastic p-bits: https://arxiv.org/abs/1610.00377
- p-Bits for PSL: https://arxiv.org/abs/1809.04028
- Weighted p-bits FPGA: https://ieeexplore.ieee.org/document/8515266
- Hardware emulation: https://www.nature.com/articles/s41598-017-11011-8
- IBM p-kit: https://github.com/IBM/p-kit

## pc-COP

Source:

- https://arxiv.org/html/2504.04543v1

Relevant form:

```text
E(m) = -(sum_{i<j} J_ij m_i m_j + sum_i h_i m_i)
```

Use for hardware-oriented p-bit optimization references.

## Simulated Bifurcation

Not Gibbs/MCMC. Physics-inspired heuristic based on nonlinear oscillator dynamics.

Sources:

- Docs: https://simulated-bifurcation-algorithm.readthedocs.io/en/v2.0.0/
- Background: https://simulated-bifurcation-algorithm.readthedocs.io/en/v2.0.0/background/simulated_bifurcation_algorithm.html
- Repo: https://github.com/bqth29/simulated-bifurcation-algorithm
- Toshiba papers: https://www.global.toshiba/ww/products-solutions/ai-iot/sbm/paper.html#contents

Use as a strong non-THRML optimization baseline.

## Formulations

- Lucas, Ising formulations of NP problems: https://www.frontiersin.org/articles/10.3389/fphy.2014.00005/full

Use for Max-Cut, TSP, knapsack, graph coloring, independent set, and penalty design.

