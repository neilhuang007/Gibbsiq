# Source Map

This file lists the most useful references from the first Tavily research pass. Prefer official docs, primary papers, and source repositories over secondary summaries.

## THRML / Extropic

- THRML docs: https://docs.thrml.ai/
- THRML architecture: https://docs.thrml.ai/en/latest/architecture/
- THRML block sampling API: https://docs.thrml.ai/en/latest/api/block_sampling/
- THRML spin models example: https://docs.thrml.ai/en/latest/examples/02_spin_models/
- THRML probabilistic computing example: https://docs.thrml.ai/en/latest/examples/00_probabilistic_computing/
- THRML repository: https://github.com/extropic-ai/thrml
- THRML repository license/currentness checked 2026-05-28: Apache-2.0, pushed 2026-05-26.
- Extropic software overview: https://extropic.ai/software
- Extropic thermodynamic computing essay: http://extropic.ai/writing/thermodynamic-computing-from-zero-to-one
- Extropic/THRML cited hardware architecture paper: https://arxiv.org/abs/2510.23972

## QUBO / BQM / Formulation APIs

- dimod docs: https://docs.dwavequantum.com/en/latest/ocean/api_ref_dimod/
- `dimod.Sampler.sample`: https://docs.dwavequantum.com/en/latest/ocean/api_ref_dimod/generated/dimod.Sampler.sample.html
- dimod repository: https://github.com/dwavesystems/dimod
- dimod repository license/currentness checked 2026-05-28: Apache-2.0, pushed 2026-05-14.
- PyQUBO getting started: https://pyqubo.readthedocs.io/en/latest/getting_started.html
- PyQUBO repository: https://github.com/recruit-communications/pyqubo
- PyQUBO paper / docs PDF reference found via Tavily: https://arxiv.org/pdf/2103.01708
- QUBOLite toolkit: https://arxiv.org/abs/2509.21321
- QuboAuditor repository: https://github.com/firaskhabour/QuboAuditor

## Baseline Solvers

- dwave-neal docs: https://dwave-neal-docs.readthedocs.io/en/latest/intro.html
- dwave-neal repository: https://github.com/dwavesystems/dwave-neal
- dwave-samplers repository: https://github.com/dwavesystems/dwave-samplers
- dwave-samplers repository license/currentness checked 2026-05-28: Apache-2.0, pushed 2026-05-08.
- OpenJij tutorial: https://tutorial.openjij.org/en/tutorial/001-openjij_introduction.html
- OpenJij repository: https://github.com/Jij-Inc/OpenJij
- OpenJij repository license/currentness checked 2026-05-28: Apache-2.0, pushed 2026-03-17.
- OpenJij homepage: https://www.openjij.org/
- Simulated bifurcation docs: https://simulated-bifurcation-algorithm.readthedocs.io/en/v2.0.0/
- Simulated bifurcation optimizer API: https://simulated-bifurcation-algorithm.readthedocs.io/en/v2.0.0/main_features/simulated_bifurcation_optimizer.html
- Simulated bifurcation repository: https://github.com/bqth29/simulated-bifurcation-algorithm
- Simulated bifurcation repository license/currentness checked 2026-05-28: MIT, pushed 2026-01-16.
- Tabu-enhanced simulated bifurcation: https://www.nature.com/articles/s42005-026-02538-2

## Diagnostics

- Vehtari et al. paper portal: https://research.aalto.fi/en/publications/rank-normalization-folding-and-localization-an-improved-r-hat-for/
- Vehtari et al. PDF: https://acris.aalto.fi/ws/portalfiles/portal/53922181/Vehtari_Rank_Normalization.euclid.ba.1593828229.pdf
- Downloaded local PDF: `reference/04-diagnostics/papers/vehtari-2021-rhat-ess.pdf`
- Online appendix: https://avehtari.github.io/rhat_ess/rhat_ess.html
- Reference repo: https://github.com/avehtari/rhat_ess
- ArviZ repository: https://github.com/arviz-devs/arviz
- ArviZ repository license/currentness checked 2026-05-28: Apache-2.0, pushed 2026-04-24.
- ArviZ docs: https://python.arviz.org/
- ArviZ ESS docs: https://python.arviz.org/en/stable/api/generated/arviz.ess.html
- ArviZ R-hat docs: https://python.arviz.org/en/stable/api/generated/arviz.rhat.html
- BlackJAX repository: https://github.com/blackjax-devs/blackjax
- emcee autocorrelation docs/source: https://emcee.readthedocs.io/
- Alleviating the Quantum Big-M Problem: https://www.nature.com/articles/s41534-025-01067-0
- Thermodynamic significance of QUBO encoding: https://arxiv.org/abs/2601.04402
- Scalable determination of penalization weights for approximate QUBO solvers: https://arxiv.org/abs/2604.02416

## Inspector / Visualization

- D-Wave Inspector docs: https://docs.dwavequantum.com/en/latest/ocean/api_ref_inspector/
- `dwave.inspector.show`: https://docs.dwavequantum.com/en/latest/ocean/api_ref_inspector/generated/dwave.inspector.show.html
- D-Wave Inspector repository: https://github.com/dwavesystems/dwave-inspector
- Minor embedding inspection examples: https://docs.dwavequantum.com/en/latest/quantum_research/embedding_guidance.html

## Probabilistic Computing / p-Bits

- Stochastic p-bits for invertible logic: https://arxiv.org/abs/1610.00377
- p-Bits for Probabilistic Spin Logic: https://arxiv.org/abs/1809.04028
- Weighted p-bits for FPGA implementation of probabilistic circuits: https://ieeexplore.ieee.org/document/8515266
- pc-COP paper: https://arxiv.org/html/2504.04543v1
- IBM p-kit repository: https://github.com/IBM/p-kit
- IBM p-kit repository license/currentness checked 2026-05-28: BSD-3-Clause, pushed 2026-05-26.
- p-bit hardware emulation paper: https://www.nature.com/articles/s41598-017-11011-8
- Extended-variable probabilistic computing with p-dits: https://arxiv.org/abs/2506.00269
- Parallel p-bit Ising machine dynamics: https://arxiv.org/abs/2604.01564
- p-dit probabilistic Ising machine for QAP: https://arxiv.org/abs/2605.24408

## Benchmarks

- Fixstars Amplify Benchmark: https://github.com/fixstars/amplify-benchmark
- Fixstars Amplify Benchmark license checked 2026-05-28: MIT.
- Amplify formulation benchmarks: https://amplify.fixstars.com/en/docs/amplify/v1/benchmark.html
- QUBO benchmark instances: https://github.com/rliang/qubo-benchmark-instances
- QUBO benchmark instances license checked 2026-05-28: MIT.
- MaxCut/QUBO exact solution survey: https://optimization-online.org/wp-content/uploads/2022/02/8782.pdf
- NeuroBench QUBO benchmark scenario: https://github.com/NeuroBench/system_benchmarks/blob/main/QUBO.md
- NeuroBench system benchmarks license checked 2026-05-28: Apache-2.0.
- Lucas, Ising formulations of many NP problems: https://www.frontiersin.org/articles/10.3389/fphy.2014.00005/full
- Downloaded local PDF: `reference/05-theory/papers/lucas-2014-ising-formulations.pdf`
- Benchmarking stochastic quantum heuristics and Ising machines: https://arxiv.org/abs/2402.10255
- Downloaded local PDF: `reference/06-benchmarks/papers/bernal-neira-2024-quantum-heuristics-ising-machines.pdf`
- Stochastic-Benchmark repository: https://github.com/usra-riacs/stochastic-benchmark
- Stochastic-Benchmark repository license/currentness checked 2026-05-28: Apache-2.0, pushed 2026-05-27.
- Comprehensive Max-Cut Ising-machine benchmark: https://arxiv.org/abs/2507.22117

## Evaluation

- Evaluation framework: `reference/08-evaluation/evaluation-framework.md`
- Manually verified equation audit: `reference/08-evaluation/equation-audit.md`
- Exact small-instance fixtures: `reference/08-evaluation/fixtures/exact-small-instances.json`
- Diagnostic fixtures: `reference/08-evaluation/fixtures/diagnostic-fixtures.json`
- Implementation source candidates: `reference/08-evaluation/source-implementation-candidates.md`

