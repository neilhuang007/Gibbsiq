# Why This Project Matters

## Need

Gibbsiq fills the gap between:

- THRML block-Gibbs execution;
- QUBO / Ising / BQM user APIs;
- sampler diagnostics;
- inspector reports;
- reproducible solver benchmarks.

## Evidence

### Correlated Samples Need Diagnostics

MCMC/Gibbs samples are correlated; raw sample count overstates useful information when autocorrelation is high.

Required Gibbsiq outputs:

- autocorrelation;
- ESS-style estimates;
- chain disagreement;
- trace plots;
- diversity and mode concentration.

Sources:

- Vehtari et al.: https://sites.stat.columbia.edu/gelman/research/published/Vehtari_etal_2020_rhat_ess.pdf
- ArviZ diagnostics: https://arviz-devs.github.io/EABM/Chapters/MCMC_diagnostics.html
- emcee autocorrelation: https://emcee.readthedocs.io/en/stable/tutorials/autocorr/
- Sampler diagnostics benchmark: https://www.auai.org/uai2018/proceedings/papers/37.pdf

### QUBO Solver Performance Is Problem-Dependent

Benchmark studies compare multiple QUBO solvers across multiple problem families because solver rankings change by workload.

Required Gibbsiq outputs:

- baseline comparison;
- fixed-seed configs;
- fixed-time and fixed-work modes;
- raw samples and metadata;
- solver versions and hardware.

Sources:

- QUBO heuristic benchmark: https://www.nature.com/articles/s41598-022-06070-5
- OpenJij tutorial: https://tutorial.openjij.org/en/tutorial/001-openjij_introduction.html
- Simulated bifurcation docs: https://simulated-bifurcation-algorithm.readthedocs.io/en/v2.0.0/
- Amplify Benchmark: https://github.com/fixstars/amplify-benchmark

### THRML Is an Execution Substrate, Not a Full Solver Product

THRML provides JAX-based block Gibbs sampling for PGMs/EBMs. Gibbsiq must add:

- QUBO/BQM compatibility;
- conversion tests;
- result schema;
- diagnostics;
- inspector;
- baselines;
- benchmarks.

Sources:

- THRML docs: https://docs.thrml.ai/
- THRML architecture: https://docs.thrml.ai/en/latest/architecture/
- THRML probabilistic computing: https://docs.thrml.ai/en/latest/examples/00_probabilistic_computing/
- Extropic thermodynamic computing: http://extropic.ai/writing/thermodynamic-computing-from-zero-to-one

