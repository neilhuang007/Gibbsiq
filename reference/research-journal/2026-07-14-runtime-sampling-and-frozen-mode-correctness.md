# 2026-07-14 - Runtime Sampling and Frozen-Mode Correctness

## Paper Hook

This entry feeds the methods and limitations sections of the auditable-sampling
paper. It records how Gibbsiq binds retained samples to declared local work,
distinguishes backend work from retained work, and detects one exact class of
cross-chain failure that scalar energy and magnetization traces cannot expose.

## Context

THRML 0.1.3 records its post-warmup state as sample zero. Its
`steps_per_sample` transitions occur only between later samples. The fixed-beta
runtime previously passed `n_warmup=0`, `n_samples=1`, and
`steps_per_sample=100` directly to that backend, so the sole retained sample was
the initialization state. A one-spin model with `h_s=1`, `beta=20`,
`init="all_up"`, `seed=0`, and zero warmup returned `s=+1` before this change.
The declared target strongly favors `s=-1`.

Energy and mean-magnetization R-hat also share a structural blind spot. Two
chains frozen at `(+,+,-,-)` and `(+,-,+,-)` have equal energy under a constant
energy fixture and equal magnetization zero. Both scalar traces are identical,
although the chains occupy different complete states.

The audit found three smaller boundary defects. Exact integer benchmark fields
were coerced to float during mixed int/float comparison, so `2**53+1` could
equal the rounded float `float(2**53)`. Partition validation admitted empty
blocks and deferred the failure to THRML. The live dimod integration tests
enumerated energies manually but did not invoke dimod's own SampleSet energy
oracle.

## Hard-Parts Analysis

### H1 - The first retained sample requires target-beta work

The fixed-beta schedule now adds `config.steps_per_sample` to the backend
warmup count. Explicit beta-ladder warmup still runs in separate segments.
Consequently, the backend observes sample zero only after the declared number
of target-beta sweeps. Every later observed sample already follows the backend's
between-sample sweep count.

The regression uses `beta=20`, `n_warmup=0`, `steps_per_sample=100`,
`num_chains=4`, `num_reads=1`, `init="all_up"`, and `seed=0`. It records the
retained result `s=-1` and 100 executed target-beta sweeps. Four configured
chains produce one active chain; zero-read chains execute no backend program.

### H2 - Requested reads and executed work are different quantities

Fixed-beta vectorization generates `max(reads_by_chain)` draws for each active
chain. A shorter active chain can therefore generate and discard one final
draw. Parallel tempering runs each active chain for its exact allocation. The
new `local_sweep_accounting` mapping is stored in both traces and metadata. It
records retained reads, backend-generated reads, warmup sweeps, target-beta
sweeps, auxiliary-beta sweeps, discarded target-beta sweeps, and totals by
chain and by run. Its unit is one complete ordered pass over every free block
for one chain and one beta replica.

For the fixed-beta accounting fixture with `reads_by_chain=(3,2,0)`, backend
reads `(3,3,0)`, five warmup sweeps, and three sweeps per sample, the run executes
28 sweeps: 10 warmup sweeps and 18 sampling sweeps. Three target-beta sweeps
belong to the discarded backend draw. For the three-replica parallel-tempering
fixture with exact backend reads `(3,2,0)`, the run executes 75 sweeps: 30
warmup sweeps, 15 target-beta sampling sweeps, and 30 auxiliary-beta sampling
sweeps.

### H3 - Frozen-mode evidence must remain decisive and scalable

The first design computed plain, rank-normalized, and folded R-hat for every
spin coordinate. Critical review rejected that design. An any-coordinate
numeric threshold makes false global warnings increasingly likely with model
dimension, and rank transforms cost `O(variables * reads * log(reads))` in
Python while producing an `O(variables)` payload.

The implemented screen reconstructs sample chains from the recorded energy
chain boundaries. It requires at least two active chains and the existing
`MIN_DRAWS_FOR_RHAT=4` draws per active chain. It fires only when every active
chain repeats one complete state and the representative states differ. The
screen costs `O(variables * reads)`. It reports the differing variables as
explanation, caps that list at 100 entries, and records the full count plus a
truncation field. A `2 chains x 1 draw` fixture reports
`evidence_status="insufficient_data"` and cannot fire.

This screen is a sampler-health warning. It is neither a general per-variable
R-hat calculation nor evidence of convergence or optimality. Non-frozen joint
distribution failures remain outside its detection class.

### H4 - Exact scalar contracts must avoid lossy normalization

Python's direct int/float equality preserves the exact representability check.
The oracle now uses `expected == actual` after excluding booleans instead of
comparing `float(expected)` and `float(actual)`. Exact `12 == 12.0` remains
accepted; `2**53+1` versus `float(2**53)` and `1` versus `True` are rejected.

## Decisions

1. We assign `steps_per_sample` target-beta sweeps to every retained fixed-beta
   read, including sample zero. The prior initialization-as-sample behavior did
   not match the configuration contract.
2. We expose executed and retained sweep counts separately. Resource accounting
   must include vectorized discarded draws and every parallel-tempering replica.
3. We execute only active fixed-beta chains. We retain a single vectorized batch
   for active chains, so unequal positive chain allocations can still generate
   one discarded draw.
4. We use the existing four-draw R-hat minimum for frozen-mode evidence. This
   avoids a new diagnostic threshold and prevents vacuous one-draw freezes.
5. We cap the explanatory differing-variable list at 100 entries. The payload
   retains the uncapped count and a truncation indicator.
6. We reject empty blocks in `validate_partition` before lowering. The empty
   model remains represented by zero blocks and uses the existing exact
   constant-model shortcut.
7. We use `dimod.testing.assert_sampleset_energies` on exhaustive samples from
   seeded QUBO and Ising conversions. Seeds 11, 23, and 47 generate four-variable
   quarter-integer coefficient models; all assignments are checked.
8. We formatted `test_suite/tests/test_dimod_ported_contracts.py`. The tracked
   file caused the repository-wide format check to fail before this audit.

## Rejected Alternatives

- We rejected retaining THRML's sample-zero behavior because it can return an
  untransitioned initialization while claiming configured sampling work.
- We rejected grouping fixed-beta chains by exact read count in this patch.
  Multiple compiled vectorized paths add execution complexity; exact accounting
  makes the remaining discarded draw visible. Zero-read chains are skipped.
- We rejected a full parallel-tempering JAX rewrite. The current change preserves
  the existing every-read PT semantics and limits the patch to correctness and
  accounting.
- We rejected an any-variable `R-hat > 1.01` global flag. It is uncalibrated over
  model dimension and creates a multiplicity-driven false-warning surface.
- We rejected always-on per-variable rank/folded R-hat. Its Python cost and
  payload scale conflict with the intended TSU problem sizes.
- We rejected treating one draw as frozen-mode evidence. One observation cannot
  establish within-chain zero variance under the project's R-hat contract.
- We rejected float coercion for exact integer comparison because IEEE-754
  rounding aliases distinct integers above `2**53`.
- We rejected relying on THRML's empty-block exception because it exposes a
  backend implementation error instead of Gibbsiq's partition contract.

## Sources and Implementations Examined

- THRML 0.1.3 installed source,
  `.venv/Lib/site-packages/thrml/block_sampling.py`: `sample_states` records the
  post-warmup state as sample zero and applies `steps_per_sample` between later
  samples.
- dimod installed public testing API: `dimod.testing.assert_sampleset_energies`.
- Gibbsiq equation contract,
  `reference/08-evaluation/equation-audit.md`: canonical Ising energy and Gibbs
  conditional sign.

## Negative Results and Limitations

The initial per-variable R-hat implementation passed its small regression suite
but failed the scaling and multiplicity audit. It was removed before the final
verification run. The replacement detects only complete-state frozen chains.
Chains that move within disjoint modes can still evade energy, magnetization,
and frozen-state screens. A future general state-space diagnostic needs an
explicit cost budget, calibration across dimension, and an opt-in payload
contract.

Fixed-beta active chains with unequal positive allocations still execute one
discarded final draw on each shorter chain. The metadata records this work. A
future grouped execution path must demonstrate a net compile/runtime benefit
before replacing the single vectorized batch.

No empirical performance or hardware-advantage claim was made. No generated
corpus or result artifact was created. Regression seeds, sampler configuration,
expected raw sample, and work-accounting values are encoded in the tests named
below.

## Verification

Focused regression command after the final diagnostic review:

```powershell
$env:PYTHONPATH = "src"
python -m unittest test_suite.tests.test_diagnostics_ground_truth test_suite.tests.test_metamorphic_diagnostics test_suite.tests.test_runtime_correctness_contracts
```

Result before the final capped-list test: 76 tests ran in 69.722 seconds and
passed. The capped-list test was included in the full-suite result below.

Full verification command:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s test_suite/tests
```

Result: 342 tests ran in 172.789 seconds and passed. ArviZ emitted its existing
constant-trace divide `RuntimeWarning`; no test failed.

Static checks:

```powershell
python -m ruff check .
python -m ruff format --check .
$env:PYTHONPATH = "src"
python -m mypy src
```

Results: Ruff lint passed; Ruff reported 43 files already formatted; mypy
reported success in 11 source files with the existing note that the
`dimod.*` module section is unused.

The regression coverage is located in:

- `test_suite/tests/test_runtime_correctness_contracts.py`
- `test_suite/tests/test_diagnostics_ground_truth.py`
- `test_suite/tests/test_metamorphic_diagnostics.py`
- `test_suite/tests/test_benchmark_oracle.py`
- `test_suite/tests/test_block_partition.py`
- `test_suite/tests/test_conversion_scenarios.py`
