# Baseline Solvers

## Purpose

Normalize non-THRML solver outputs into `SampleResult` for benchmarks and inspector comparison.

## dwave-neal

Sources:

- Docs: https://dwave-neal-docs.readthedocs.io/en/latest/intro.html
- Repo: https://github.com/dwavesystems/dwave-neal

API:

```python
sampler = neal.SimulatedAnnealingSampler()
sampleset = sampler.sample(
    bqm,
    num_reads=128,
    num_sweeps=1000,
    beta_range=None,
    beta_schedule_type="geometric",
    seed=123,
)
```

Record:

- `num_reads`
- `num_sweeps`
- `beta_range`
- `beta_schedule_type`
- `seed`
- `initial_states`

## OpenJij

Sources:

- Tutorial: https://tutorial.openjij.org/en/tutorial/001-openjij_introduction.html
- Repo: https://github.com/Jij-Inc/OpenJij

Methods:

- `sample_ising(h, J)`
- `sample_qubo(Q)`

Response fields:

- `.states`
- `.energies`
- `.indices`
- `.first.sample`
- `.first.energy`

## Simulated Bifurcation

Sources:

- Docs: https://simulated-bifurcation-algorithm.readthedocs.io/en/v2.0.0/
- Repo: https://github.com/bqth29/simulated-bifurcation-algorithm

Key parameters:

- `agents`
- `best_only`
- `domain`
- `device`
- `dtype`
- `early_stopping`
- `convergence_threshold`
- `max_steps`
- `mode`
- `heated`

Diagnostics:

- best energy;
- time to target;
- agent diversity;
- convergence/stability;
- wall-clock.

Do not interpret as an MCMC sampler.

## Comparison Rules

- Same energy convention.
- Same instances.
- Fixed seeds.
- Record package versions and hardware.
- Report best, median, distribution, runtime.
- Separate fixed-time from fixed-work comparisons.

