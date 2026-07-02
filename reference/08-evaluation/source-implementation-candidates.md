# Source Implementation Candidates

Checked on 2026-05-28 using official docs and GitHub API metadata.

Copy code only when the license is compatible and attribution/license notices are preserved. Prefer modeling APIs and behavior over copying code unless there is a clear need.

| Area | Source | License | Reuse Guidance |
|---|---|---:|---|
| THRML runtime | https://github.com/extropic-ai/thrml | Apache-2.0 | Model block sampling, spin examples, and JAX/PyTree integration patterns. Do not assume it provides Gibbsiq diagnostics or QUBO conversion. |
| THRML docs | https://docs.thrml.ai/en/latest/examples/02_spin_models | Docs | Use for current spin model and block sampling API expectations. |
| BQM/QUBO interface | https://github.com/dwavesystems/dimod | Apache-2.0 | Model `Sampler`, `SampleSet`, vartype, BQM, and exact-solver behavior. Good source for dimod-compatible API shape. |
| Current D-Wave samplers | https://github.com/dwavesystems/dwave-samplers | Apache-2.0 | Prefer over old `dwave-neal` for current simulated annealing adapter patterns. |
| Legacy neal SA | https://github.com/dwavesystems/dwave-neal | Apache-2.0 | Useful for compatibility with existing Ocean examples; repository is older. |
| OpenJij | https://github.com/Jij-Inc/OpenJij | Apache-2.0 | Model `sample_ising` and `sample_qubo` baseline adapter behavior. |
| Simulated bifurcation | https://github.com/bqth29/simulated-bifurcation-algorithm | MIT | Candidate non-MCMC physics baseline. Do not interpret outputs as MCMC diagnostics. |
| ArviZ diagnostics | https://github.com/arviz-devs/arviz | Apache-2.0 | Best source for robust ESS/R-hat implementation details if Gibbsiq chooses to copy or adapt diagnostic code. |
| ArviZ ESS docs | https://python.arviz.org/en/stable/api/generated/arviz.ess.html | Docs | Use for public API expectations around ESS method names. |
| ArviZ R-hat docs | https://python.arviz.org/en/stable/api/generated/arviz.rhat.html | Docs | Use for public API expectations around rank, split, and folded methods. |
| Vehtari reference repo | https://github.com/avehtari/rhat_ess | No GitHub license detected | Do not copy code unless license is clarified. Use the paper formulas and ArviZ instead. |
| Stochastic benchmarking | https://github.com/usra-riacs/stochastic-benchmark | Apache-2.0 | Strong candidate for benchmark scorecards, parameter-strategy reporting, and resource accounting patterns. |
| Amplify benchmark | https://github.com/fixstars/amplify-benchmark | MIT | Candidate benchmark harness and problem set inspiration. |
| QUBO benchmark instances | https://github.com/rliang/qubo-benchmark-instances | MIT | Candidate externally sourced QUBO fixtures after checksum and expected-energy review. |
| NeuroBench QUBO scenario | https://github.com/NeuroBench/system_benchmarks | Apache-2.0 | Candidate higher-level benchmark scenario reference. |
| p-bit examples | https://github.com/IBM/p-kit | BSD-3-Clause | Future probabilistic-computing reference, not needed for v0. |

## Currentness Notes

- THRML GitHub `pushed_at`: 2026-05-26.
- dimod GitHub `pushed_at`: 2026-05-14.
- dwave-samplers GitHub `pushed_at`: 2026-05-08.
- OpenJij GitHub `pushed_at`: 2026-03-17.
- simulated-bifurcation-algorithm GitHub `pushed_at`: 2026-01-16.
- ArviZ GitHub `pushed_at`: 2026-04-24.
- stochastic-benchmark GitHub `pushed_at`: 2026-05-27.
