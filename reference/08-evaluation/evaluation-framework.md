# Evaluation Framework

## Purpose

Gibbsiq implementations must prove three things independently:

1. They preserve the optimization model exactly.
2. They sample with the intended energy signs and metadata.
3. They report sampler health honestly enough to catch misleading wins.

The framework is diagnostics-first: a solver can find the right best sample and still fail evaluation if conversion, trace metadata, diversity, or baseline accounting is wrong.

## Test Layers

### 1. Model Compatibility

Required checks:

- deterministic variable ordering;
- QUBO/BQM/Ising energy equivalence over all states for `n <= 16`;
- offset preservation;
- source format and conversion metadata;
- exact `to_dimod()` round trip when dimod is installed.

Fixture source: `fixtures/exact-small-instances.json`.

Pass criteria:

- every state energy matches expected value within `1e-9`;
- `best_energy`, `best_sample`, and degeneracy match fixture values;
- no fixture may depend on dictionary iteration order.

### 2. THRML Lowering and Gibbs Signs

Required checks:

- local field uses `gamma_i = h_i + sum_j J_ij s_j`;
- single-site conditional uses `sigmoid(-2 * beta * gamma_i)`;
- two-spin Boltzmann probabilities match exact enumeration at fixed beta;
- block updates never place adjacent interacting variables in the same independent-color block unless the THRML program explicitly handles joint updates.

Pass criteria:

- analytic conditional probabilities in the fixture match within `1e-9`;
- empirical two-spin frequencies fall within a predeclared confidence interval when run with enough reads;
- fixed seeds reproduce identical traces on the same backend/device.

### 3. Result Schema

Every solver result must include:

- `samples`;
- `variables`;
- `energies`;
- `best_sample`;
- `best_energy`;
- `traces`;
- `diagnostics`;
- `metadata`;
- `to_dimod()`.

Metadata must include:

- solver and backend versions;
- device;
- seed;
- schedule;
- block strategy;
- timing split into compile/sample/diagnostics;
- source model format;
- conversion offset;
- fixture or benchmark instance id when applicable.

### 4. Diagnostics

Required scalar traces:

- energy;
- best-so-far energy;
- magnetization when spin samples are available;
- violation count when constraints are available;
- distance to best state.

Required diagnostic families:

- autocorrelation and ESS-style estimate;
- unique sample fraction;
- top-k mass;
- entropy;
- mean pairwise Hamming distance;
- chain disagreement / R-hat-style warning;
- feasibility rate;
- no-recent-improvement warning;
- mode-collapse warning.

Fixture source: `fixtures/diagnostic-fixtures.json`.

Pass criteria:

- constant traces do not produce NaN diagnostics in public output;
- mode collapse fixtures raise `mode_collapse`;
- disagreement fixtures raise `chain_disagreement`;
- diagnostics explicitly distinguish "not enough data" from "healthy".

## JSON Evaluator

Candidate implementations should emit a JSON file in this shape:

```json
{
  "results": [
    {
      "id": "fixture_id",
      "actual": {
        "field_from_expected_fixture": "candidate value"
      }
    }
  ]
}
```

Run:

```bash
PYTHONPATH=src python -m gibbsiq.evaluation test_suite/examples/evaluation-candidate.example.json
```

The evaluator prints a JSON report with `passed`, `summary`, per-fixture `status`, and structured `differences`. It exits with status `0` only when every known fixture is present and passing.

### 5. Baselines

Required v0 baselines:

- exact exhaustive solver for small instances;
- simulated annealing through dimod/dwave-samplers or neal;
- optional OpenJij;
- optional simulated bifurcation.

Comparison rules:

- same instance and energy convention;
- fixed seeds;
- separate fixed-work from fixed-time comparisons;
- report tuning time separately and include it in operational scorecards;
- report distribution statistics, not only best energy.

### 6. Benchmark Families

v0 families:

- exact toy Ising and QUBO fixtures;
- Max-Cut triangle and cycle fixtures;
- generated ER Max-Cut with stored seed;
- SK spin glass with stored seed;
- sparse Ising with stored seed;
- small knapsack QUBO;
- small TSP QUBO;
- planted or externally sourced benchmark instances only after source/license review.

Every benchmark artifact must store:

- instance id;
- source;
- seed or downloaded file checksum;
- exact energy or best-known energy;
- formulation metadata;
- solver config;
- raw samples;
- raw traces;
- diagnostics output;
- timings.

## Non-Negotiable Failure Cases

An implementation fails evaluation if any of these happen:

- QUBO-to-Ising conversion changes any enumerated energy.
- Offset is dropped from `best_energy` or metadata.
- The Gibbs conditional has the wrong sign.
- Repeated samples are reported as high diversity.
- A constant trace yields a healthy ESS.
- R-hat-style checks are described as proof of optimality.
- Baseline comparisons omit seed, version, device, or tuning budget.
- A benchmark uses a "best known" value without recording the source.

## Suggested Test Layout

```text
test_suite/tests/
  test_energy_equivalence.py
  test_exact_fixtures.py
  test_gibbs_conditionals.py
  test_result_schema.py
  test_diagnostics_fixtures.py
  test_baseline_adapters.py
  test_benchmark_artifacts.py
```

## Exit Criteria for v0

The first implementation is acceptable when:

- all exact fixtures pass;
- at least one THRML-backed two-spin run matches analytic probabilities;
- exact and simulated annealing baselines run against the same fixture IDs;
- diagnostics catch all fixture failure modes;
- benchmark outputs are reproducible from stored seeds and config.


