# Agentic Evaluation Research

Snapshot date: 2026-06-01.

## Purpose

This document records the research process and evaluation design for turning Gibbsiq from a
research project into an agentic workflow with verifiable rewards.

An agent working on Gibbsiq must be rewarded on signals that are measurable, hard to fake,
and useful to the project. A good final energy is not a sufficient signal on its own. A
trustworthy workflow separately verifies model preservation, sampler behavior, feasibility,
diagnostics, baselines, and benchmark resource accounting.

## Research Process

Local repository review:

- Read the top-level project docs: `README.md`, `PROJECT_BRIEF.md`, `spec.md`, and
  `CLAUDE.md`.
- Read the evaluation contract: `reference/08-evaluation/README.md`,
  `evaluation-framework.md`, `equation-audit.md`, fixtures, and
  `source-implementation-candidates.md`.
- Read the benchmark corpus and oracle design:
  `reference/06-benchmarks/ground-truth-datasets.md`,
  `src/gibbsiq/evaluation.py`, `src/gibbsiq/benchmark_oracle.py`,
  `test_suite/tests/test_benchmark_oracle.py`, and `tools/generate_ground_truth.py`.
- Reviewed the local paper summaries most relevant to evaluation:
  Lucas 2014 for Ising/QUBO formulations, Vehtari et al. for R-hat and ESS,
  Bernal Neira et al. 2024 for stochastic optimization benchmark methodology,
  penalty-weight and Big-M papers for constrained QUBO failure modes, and QUBO/Ising
  benchmark papers for baseline fairness.

Web research:

- Searched and opened primary sources for THRML, dimod/Ocean conventions, stochastic
  optimization benchmarking, SWE-bench style agent evaluation, and private/held-out agent
  benchmark design.
- Tool note: the web search query endpoint initially returned empty result sets for a few
  broad queries. Narrower queries and direct source opens worked, so the research was
  completed from primary URLs.
- Follow-up Tavily search on 2026-06-01 worked and returned current sources on benchmark
  contamination, reward hacking, hidden-split recomputation, contamination-limited dynamic
  benchmarks, and process rewards for agentic reasoning.

Tavily follow-up findings:

- Reward-hacking benchmark work emphasizes that agents can pass weak checkers by fabricating
  outputs unless the grader recomputes metrics on hidden splits or held-out corruptions.
  Gibbsiq should therefore recompute objective values from witnesses and keep private seeds
  outside the agent-visible repository.
- Recent benchmark-hardening discussions emphasize evaluator isolation: artifacts produced
  by the agent should be treated as untrusted, copied through a controlled channel, and
  scored by a separate evaluator that the agent cannot mutate.
- LiveBench-style contamination-limited evaluation reinforces two useful principles for
  Gibbsiq: frequently generated/updated instances and automatic scoring against objective
  ground truth instead of LLM judges.
- SWE-Cycle and SWE-bench Pro style work reinforces contamination filtering, harder
  multi-step tasks, and benchmark splits that are private or legally unlikely to have been
  used in training.
- Verifiable process reward work suggests a path beyond final-answer reward: intermediate
  steps can also be rewarded when each step has an algorithmic verifier. For Gibbsiq, this
  maps to conversion equivalence, witness feasibility, diagnostic flags, and resource
  accounting before final optimization quality.

## What The Papers Imply

Lucas 2014 establishes that many NP-hard workloads can be encoded as Ising/QUBO models, but
also warns that encodings can require auxiliary variables, strong penalty separations, and
high connectivity. For Gibbsiq, this means evaluation must test the encoding, not only the
solver's final sample.

Vehtari et al. show that naive convergence diagnostics can miss failures, and recommend
rank-normalized, split/folded R-hat and ESS-style checks with multiple chains. For Gibbsiq,
these ideas should be adapted as warnings over scalar traces such as energy, magnetization,
constraint violation count, and distance to best state. They must not be presented as proof
of optimality.

Bernal Neira et al. frame stochastic solvers as parameterized systems whose practical
performance depends on parameter-setting strategy, resource budget, train/test instance
splits, and cross-validation. This maps directly to Gibbsiq's benchmark design: without a
disciplined benchmark, a parameter or answer choice cannot be evaluated except by guesswork;
a benchmark turns parameter tuning into an auditable engineering loop.

Recent penalty and encoding papers reinforce that constrained QUBO is fragile. Bad penalties
can create low-energy infeasible states, suppress the original objective scale, or change
the effective thermodynamic landscape. Gibbsiq therefore needs feasibility and penalty
diagnostics as first-class rewards.

## Public Tests

Public tests should be exhaustive, understandable, and stable. They are for development
feedback, not final claims.

### Model Compatibility

Evaluate:

- deterministic variable ordering;
- QUBO/BQM/Ising energy equivalence over all states for small `n`;
- offset preservation;
- diagonal vs upper-triangle conventions;
- `to_dimod()` round trip when dimod is installed.

Reward:

- exact pass/fail against enumerated energies and expected metadata;
- no credit for a best sample if any state energy is wrong.

### Gibbs And THRML Lowering

Evaluate:

- local field sign;
- single-site conditional probabilities;
- two-spin Boltzmann probabilities;
- block partition validity;
- fixed-seed reproducibility on the same backend.

Reward:

- analytic probability match for tiny cases;
- statistical confidence intervals for empirical sampler frequencies;
- hard failure for wrong sign or missing seed metadata.

### Result Schema

Evaluate:

- samples, variables, energies, best sample, best energy, traces, diagnostics, metadata;
- source format, conversion offset, schedule, seed, block strategy, versions, device, timing;
- raw artifact export.

Reward:

- schema completeness and reproducibility metadata before performance score.

### Diagnostics

Evaluate:

- constant traces;
- repeated samples incorrectly reported as diverse;
- chains stuck in different modes;
- no-recent-improvement;
- low feasibility;
- apparent improvement from penalty terms while native objective does not improve.

Reward:

- required flags on synthetic traps;
- explicit `not_enough_data` status where diagnostics are underpowered;
- no public NaN/inf diagnostics.

### Benchmark Oracle

Evaluate:

- exact optimum value;
- exact degeneracy;
- witness state feasibility and optimality by independent recomputation.

Reward:

- witness validity is mandatory;
- scalar optimum claims are ignored unless a witness recomputes correctly.

## Blind Tests

Blind tests are necessary because an agent with repository access can inspect public fixtures,
write code that matches expected JSON, or overfit thresholds. The public suite should be a
teaching set; the release gate should be a hidden holdout.

### Hidden Generated Instances

Use deterministic generators with private seeds held outside the repo or injected by CI.
Keep all generated instances small enough for exact enumeration:

- Max-Cut;
- sparse Ising;
- SK spin glass;
- number partitioning;
- knapsack;
- small TSP;
- planted-solution QUBO families once the formulation source is audited.

The hidden evaluator should compute the optimum and witness validity at runtime or load a
private fixture bundle unavailable to coding agents.

### Metamorphic Mutations

Generate hidden variants from public fixtures:

- permute variable order;
- add constant offsets;
- split equivalent QUBO terms across symmetric entries, then normalize;
- apply spin gauge transforms and convert back;
- scale coefficients within valid numeric ranges;
- add irrelevant isolated variables;
- relabel graph vertices;
- reorder JSON keys and unordered lists.

Expected invariant: a correct implementation still returns equivalent energies,
valid witnesses, and stable metadata. A fixture-echo implementation fails.

### Private Diagnostic Traps

Hold back traces that look superficially healthy:

- low variance because every sample is identical;
- multiple chains with identical means but different supports;
- a best-so-far trace that improves once then freezes;
- feasibility rate near zero while penalized energy appears good;
- autocorrelation estimates with too few samples.

Expected invariant: diagnostics must distinguish healthy, unhealthy, and not-enough-data.

### Resource-Accounting Traps

Use hidden candidate outputs with missing or false accounting fields:

- omitted tuning time;
- missing seed;
- missing solver version;
- wall-clock reported but compile/diagnostics time omitted;
- fixed-time comparison mixed with fixed-work comparison.

Expected invariant: benchmark claims fail if the method cannot be reproduced or if
resource categories are mixed.

## Anti-Cheating Rules

1. Do not expose hidden fixture IDs, seeds, expected outputs, or optimum values to coding
   agents.
2. Keep the hidden evaluator outside the package import path used by the submitted code.
3. Recompute objectives from candidate witnesses instead of trusting reported energies.
4. Score hidden and public fixtures through the same external interface.
5. Require raw samples/traces for stochastic claims.
6. Reject candidate outputs that contain expected-value-only fields without witnesses.
7. Run mutation tests that are semantically equivalent but syntactically different from
   public examples.
8. Treat "passes public fixtures" as development readiness, not benchmark validity.

## Reward Surface

The recommended reward is hierarchical:

| Layer | Reward | Failure mode blocked |
| --- | --- | --- |
| Model correctness | exact energy equivalence, offset/sign correctness | wrong solver target |
| Witness validity | oracle recomputes objective and feasibility | echoed best values |
| Diagnostics honesty | required flags and no false healthy states | hidden sampler failure |
| Reproducibility | seed/version/device/schedule/timing metadata | non-repeatable claims |
| Baseline fairness | fixed-time and fixed-work comparisons separated | inflated performance |
| Optimization quality | gap, time to target, success probability distribution | best-energy cherry-pick |

Do not collapse these into one scalar too early. A solver that is fast but drops offsets, or
finds a good sample while hiding mode collapse, should fail the corresponding gate.

## Suggested Test Modules

Implemented public modules as of 2026-06-01:

- `test_suite/tests/test_exact_fixtures.py`: independent checks for conversion signs, offsets,
  Boltzmann probabilities, and tiny Max-Cut fixtures.
- `test_suite/tests/test_diagnostic_fixtures.py`: independent checks for diagnostic trap metrics.
- `test_suite/tests/test_benchmark_oracle.py`: strict witness re-verification and anti-echo tests.
- `test_suite/tests/test_evaluation_harness.py`: candidate normalization and public fixture scoring.
  It now also rejects duplicate result IDs, fails unknown fixture outputs, and treats
  candidate strings as inert data.
- `test_suite/tests/test_benchmark_corpus_integrity.py`: corpus checksum, provenance, ID, schema, and
  minimum decoding-convention checks.
- `test_suite/tests/test_ground_truth_exactness.py`: independent exhaustive enumeration over every
  public ground-truth benchmark scalar.
- `test_suite/tests/test_metamorphic_rewards.py`: equivalent-witness and scalar-mandatory checks for
  reward behavior that should generalize to blind mutations.
- `test_suite/tests/test_ground_truth_generator.py`: deterministic generator reproducibility without
  overwriting the checked-in fixture.

Recommended future modules once implementation code exists:

```text
test_suite/tests/
  test_energy_equivalence.py
  test_qubo_ising_conversion.py
  test_gibbs_conditionals.py
  test_result_schema.py
  test_diagnostics_fixtures.py
  test_benchmark_oracle.py
  test_benchmark_artifacts.py
  test_baseline_accounting.py
```

Hidden CI should mirror this structure with private fixtures and metamorphic generators.

## Source Notes And Citations

Project-local sources:

- `reference/08-evaluation/equation-audit.md`
- `reference/08-evaluation/evaluation-framework.md`
- `reference/06-benchmarks/ground-truth-datasets.md`
- `reference/04-diagnostics/papers/vehtari-2021-rhat-ess.md`
- `reference/05-theory/papers/lucas-2014-ising-formulations.md`
- `reference/06-benchmarks/papers/bernal-neira-2024-quantum-heuristics-ising-machines.md`
- `reference/04-diagnostics/papers/alessandroni-2026-penalization-weights.md`
- `reference/04-diagnostics/papers/alessandroni-2025-quantum-big-m.md`
- `reference/04-diagnostics/papers/doucet-2026-qubo-encoding-thermodynamics.md`

External primary sources:

- THRML documentation: https://docs.thrml.ai/
- THRML architecture docs: https://docs.thrml.ai/en/latest/architecture/
- D-Wave dimod docs: https://docs.dwavequantum.com/en/latest/ocean/api_ref_dimod/
- Lucas, "Ising formulations of many NP problems": https://doi.org/10.3389/fphy.2014.00005
- Vehtari et al., "Rank-normalization, folding, and localization": https://projecteuclid.org/journals/bayesian-analysis/volume-16/issue-2/Rank-Normalization-Folding-and-Localization--An-Improved-R%CB%86-for/10.1214/20-BA1221.full
- Bernal Neira et al., stochastic solver benchmarking: https://arxiv.org/abs/2402.10255
- Stochastic-Benchmark repository: https://github.com/usra-riacs/stochastic-benchmark
- QUBO heuristic solver benchmark: https://www.nature.com/articles/s41598-022-06070-5
- OpenAI SWE-bench Verified discussion: https://openai.com/index/introducing-swe-bench-verified/
- METR autonomy-task measurement discussion: https://metr.org/measuring-autonomous-AI-capabilities/
- Reward Hacking Benchmark: https://arxiv.org/html/2605.02964v1
- LiveBench contamination-limited benchmark: https://arxiv.org/abs/2406.19314
- LiveBench ICLR 2025 abstract: https://proceedings.iclr.cc/paper_files/paper/2025/hash/e4a46394ba5378b3f9a186a5b4c650d1-Abstract-Conference.html
- SWE-Cycle contamination filtering: https://arxiv.org/html/2605.13139v1
- SWE-bench Pro methodology: https://labs.scale.com/leaderboard/swe_bench_pro_public
- Verifiable Process Rewards for Agentic Reasoning: https://arxiv.org/html/2605.10325v1
- METR frontier risk report on agent reward hacking: https://metr.org/blog/2026-05-19-frontier-risk-report


