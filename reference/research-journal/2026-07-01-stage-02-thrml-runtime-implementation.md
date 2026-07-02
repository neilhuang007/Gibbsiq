# 2026-07-01 - Stage 2 THRML Runtime Implementation

## Paper Hook

Feeds the methods and implementation sections: how Gibbsiq lowers the audited Ising IR into
THRML block-Gibbs programs, and how the sign mapping, offset preservation, and multi-chain
contract are verified before any optimization claim.

## Context

Stage 1 fixed the canonical Ising IR and the `SampleResult` schema. Stage 2 connects that
model to THRML: lower an Ising instance into THRML nodes, factors, graph-colored blocks,
sampling schedules, initialization state, and a sampling program, then return a `SampleResult`
with raw samples, recomputed energies, traces, and metadata. The immediate validation target
was a tiny Ising run whose empirical frequencies match analytic Boltzmann probabilities within
a declared statistical interval, which exercises both the lowering and the conditional sign.

## Sign Mapping Audit

THRML's `IsingEBM` defines

$$
E_{\mathrm{thrml}}(\mathbf{s}) = -\beta \left( \sum_i b_i s_i + \sum_{(i,j)} w_{ij} s_i s_j \right)
$$

and samples $p(\mathbf{s}) \propto \exp(-E_{\mathrm{thrml}}(\mathbf{s}))$, while Gibbsiq's audited
convention is

$$
E(\mathbf{s}) = \mathrm{offset} + \sum_i h_i s_i + \sum_{i \lt j} J_{ij} s_i s_j
$$

targeted at $p(\mathbf{s}) \propto \exp(-\beta E(\mathbf{s}))$. Equating the two Boltzmann
distributions requires $b = -h$ and $w = -J$. THRML represents spin state as boolean arrays with
`True` meaning $+1$. The mapping was verified empirically before implementation with a two-spin
probe: over 20,000 samples the empirical-versus-analytic Boltzmann maximum absolute error was
0.0017. `TwoSpinDistributionTests` in `test_suite/tests/test_thrml_runtime.py` pins it
permanently.

## Decisions

- `thrml` 0.1.3 installed from PyPI, pulling `jax` 0.10.2, `jaxlib` 0.10.2, and `equinox`
  0.13.8; the stack installs cleanly on Windows CPU under Python 3.13. It is added as the
  optional extra `gibbsiq[thrml]`, the dev extra now includes it, and the core package keeps
  zero runtime dependencies.
- Offset preservation and independent energies: every reported energy is recomputed through
  `IsingModel.energy` from decoded samples, so no energy is read back from THRML. An
  offset-shift test with a fixed seed confirms that an offset of 3.25 moves every energy by
  exactly that amount.
- Block construction is a DSATUR coloring implemented in the standard library
  (`src/gibbsiq/blocks.py`, strategy metadata string `"dsatur-coloring"`): each step colors the
  uncolored variable with the highest saturation, breaking ties by higher degree and then
  canonical variable order, so the partition is a pure function of the model. DSATUR was chosen
  because THRML's own spin-model example (`examples/02_spin_models.ipynb`) delegates coloring to
  networkx DSATUR, and DSATUR colors bipartite interaction graphs — the chains, grids, and even
  cycles common in QUBO encodings — optimally with two colors where naive greedy orderings can
  degrade (the crown-graph counterexample). networkx itself was declined to keep the
  zero-dependency core. `validate_partition` rejects any partition that co-blocks coupled
  variables; dense-graph degeneration is recorded through `num_blocks`, `block_sizes`, and
  `graph_density` metadata rather than a separate fallback path.
- Multi-chain execution uses `jax.vmap` over per-chain PRNG keys, with output shape
  `(chains, samples, nodes)`. `num_reads` splits as `ceil(num_reads / num_chains)` per chain;
  surplus samples drop from the last chain and the per-chain traces truncate to match, so the
  flat `energies` tuple always equals the concatenated `traces["energy"]`.
- Annealed warmup: `SamplerConfig.warmup_beta_ladder` splits `n_warmup` sweeps across the ladder
  betas before sampling at the final beta. Because beta is baked into `IsingEBM`, each segment
  gets its own program, and state carries between segments by observing the free blocks with
  `n_samples=1`; `sample_states` returns observations only, and carrying state through the
  lower-level `sample_blocks` would require sampler-state plumbing.
- An edgeless-model workaround handles isolated-spin instances: `IsingEBM.factors`
  unconditionally builds a coupling factor and indexes `edges[0]`
  (`thrml/models/ising.py` line 75, `discrete_ebm.py` line 104), so a model with no couplings
  raises `IndexError`. A private `IsingEBM` subclass drops the empty coupling factor, so
  fields-only models lower cleanly.
- Initialization policies are `hinton` (THRML's `hinton_init` at the first ladder beta),
  `random`, `all_up`, and `all_down`.
- The result contract records, in `SampleResult` metadata: `thrml_version`, `jax_version`,
  device platform and kind, seed, beta, `warmup_beta_ladder`, schedule fields, `num_chains`,
  `reads_per_chain`, init policy, graph density, block metadata, the sign-mapping note, and
  lower/sample wall-clock seconds. Traces record per-chain energy, `best_energy_so_far`,
  `sample_chain_ids`, and a `beta_schedule` list, giving Stage 3 diagnostics enough raw data
  without rerunning THRML.
- Test outcome: 39 new tests were added. The `SamplerConfig` validation and block-partition
  tests run without `thrml`, and the runtime classes skip cleanly when `thrml` is absent.
  Literature edge cases are pinned explicitly: the crown-graph ordering trap and odd-cycle
  chromatic number for DSATUR, the frustrated antiferromagnetic triangle (optimum found and
  multiple degenerate ground states visited), an eight-spin SK instance verified against
  exhaustive enumeration, exhaustive four-variable empirical-versus-analytic Boltzmann
  validation, and QUBO binary-decode energy equivalence. The full suite runs 128 tests, all
  passing.

## Rejected Alternative

Declined: adding `networkx` for the coloring step. Its DSATUR heuristic is reproduced in the
standard library, which preserves the zero-dependency core. Also declined: reading energies back
from THRML; all reported energies are recomputed through the audited convention so the offset and
the sign mapping stay under Gibbsiq's control.

## Sources Read

- `reference/00-roadmap/stage-02-thrml-optimization-runtime.md` for deliverables and exit
  criteria.
- `reference/03-samplers/thrml-optimization-runtime.md` for the v0 inputs, the conditional, and
  the lowering sketch.
- `reference/01-architecture/thrml-runtime.md` for THRML concepts, bundle shape, and block
  strategy risks.
- `reference/00-roadmap/stage-03-diagnostics-pipeline.md` for the trace requirements, so Stage 3
  consumes Stage 2 output without rerunning THRML.
- `src/gibbsiq/model.py`, `result.py`, and `conversions.py` for the IR and result contracts.
- Installed `thrml` 0.1.3 source, especially `thrml/models/ising.py`
  (`IsingEBM.factors`, `IsingSamplingProgram`, `hinton_init`) and the inspect-derived signatures
  of `sample_states`, `sample_blocks`, `SamplingSchedule`, and `make_empty_block_state`.
- THRML API research, source-verified, confirming that `thrml` 0.1.3 is the only PyPI release
  and ships no coloring utility, no annealing primitive (beta is baked into the `IsingEBM`
  factors), no native multi-chain argument (vmap over PRNG keys is the sanctioned pattern, used
  in THRML's own benchmarks), and no offset field (Gibbsiq tracks the offset outside THRML).

## Examples Used

- The lowering sketch in `reference/03-samplers/thrml-optimization-runtime.md` was the template
  for `_Lowering.program`; its constructor guesses matched `thrml` 0.1.3 exactly (`SpinNode`,
  `Block`, `IsingEBM`, `IsingSamplingProgram`, `SamplingSchedule`, `sample_states`,
  `hinton_init`).
- Two scratchpad probes were run before implementation: a two-spin sign probe comparing
  empirical to analytic Boltzmann probabilities, and a vmap probe confirming batched chains.
- Test style follows `test_suite/tests/test_metamorphic_model_properties.py`.

## Follow-Up

The shipped evaluation example candidate covers only the exact and diagnostic fixture groups, so
`gibbsiq-evaluate` exits 1 on the 27 benchmark `gt_*` fixtures. This is a pre-existing gap rather
than a Stage 2 regression. A THRML-runs-to-benchmark-candidate bridge is the natural next
validation step.

## Verification

Ran the full unit suite (`$env:PYTHONPATH="src"; python -m unittest discover -s test_suite/tests`):
128 tests pass, including the two-spin analytic-distribution test and the offset-shift test.
Scanned the edited Markdown for one-line display-math blocks and confirmed every display equation
uses multiline `$$` delimiters with `\lt` in place of a literal `<`.
