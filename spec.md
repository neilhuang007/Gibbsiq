# Gibbsiq Technical Specification

## Scope

Gibbsiq is THRML-native optimization infrastructure for QUBO, Ising, and BQM models. It
provides a path from a standard quadratic optimization model to an auditable THRML sampling
run. A model enters through a stable interface, is converted into the canonical Ising
convention, is lowered into THRML nodes, factors, blocks, and sampling programs, and produces
a result artifact containing raw samples, traces, diagnostics, metadata, and benchmark
evidence. The model interface, fixed-beta THRML runtime, diagnostics, evaluator, strict
benchmark oracle, independent small-state verifier, complete target-fact contract, and
artifact-only Inspector core are implemented. The parallel-tempering correctness path and
diagnostic threshold/flag correction have targeted and full-suite verification recorded on
2026-07-14. General constraint encoding, full Inspector/HTML integration, and
classical-baseline runners remain target behavior.
Pairwise categorical/domain-wall lowering exists and does not constitute a general
higher-order or knapsack/TSP constraint encoder.

ThermoMap is the compiler, auto-mapping, verification, and thermodynamic-roofline capability
track inside Gibbsiq. It does not define a separate package. The normative work order is
`reference/00-roadmap/autonomous-implementation-roadmap.md`, the execution contract is
`reference/00-roadmap/autonomous-agent-runbook.md`, and live task state and claims are in
`reference/00-roadmap/NEXT_TASK.md`. That ledger may authorize multiple disjoint lanes; each
worker owns exactly one bounded task.

The project is not a backend-agnostic diagnostics package. dimod compatibility and diagnostic
fixtures are implemented adoption and audit bridges. Planned classical baselines provide the
independent comparison control. The primary execution path remains THRML.

By analogy, Gibbsiq holds the position that Ocean and dimod hold for D-Wave and that ArviZ
holds for Stan and PyMC: the ingestion, runtime-contract, diagnostics, and
independent-verification layer for the THRML ecosystem, with THRML itself as the general
programming layer for thermodynamic sampling units. The durable contribution is independent
verification and diagnostics, which a hardware vendor cannot credibly supply for its own
device; model ingestion and lowering may later be absorbed by an Extropic-owned optimization
SDK, while the verification and diagnostics contracts remain. The `SampleResult` schema,
diagnostic inputs, and witness-recomputing benchmark oracle are therefore specified to be
backend-portable at the architectural level. This is contract-level portability as a hedge:
the same audited artifacts stay useful for the broader Ising-machine field if the THRML
hardware path is delayed, while execution stays THRML-first.

## Non-Negotiable Technical Contracts

- Canonical energy:

```text
E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j
```

- Spins use `s_i in {-1,+1}`.
- Quadratic terms are upper-triangular and are not double-counted.
- Offsets must survive every QUBO/BQM/Ising conversion and appear in result metadata.
- The audited single-site conditional is:

```text
P(s_i = +1 | s_-i) = sigmoid(-2 * beta * gamma_i)
```

- `gamma_i = h_i + sum_j J_ij s_j`.
- R-hat, ESS, diversity, and related diagnostics are warnings about sampler health, not
  proofs of optimality.
- Benchmark claims require witness states and independent objective recomputation.

## Product Layers

1. **Interface and internal model**
   - Ingest QUBO, Ising, and dimod-style BQM inputs.
   - Normalize them into deterministic internal Ising models.
   - Preserve offsets and source-format metadata.
   - Export to dimod when the optional dependency is installed.

2. **THRML optimization runtime**
   - Lower the internal Ising model into THRML nodes, factors, blocks, and programs.
   - Build graph-aware block partitions from nonzero couplings.
   - Support seeds, initialization policies, fixed-beta schedules, warmup ladders, and an
     independently verified parallel-tempering path.
   - Capture raw samples, energy traces, schedule metadata, block metadata, versions, device,
     and timing.
   - Recompute energies under Gibbsiq's convention instead of trusting backend output.

3. **Diagnostics and telemetry**
   - Compute energy summaries, best-so-far traces, autocorrelation, ESS-style estimates,
     diversity, chain disagreement, and failure flags.
   - Report constraint feasibility as `not_available` until a compatible constraint encoding
     and unpenalized-objective contract exists.
   - Consume Stage 2 `SampleResult` artifacts without rerunning the sampler.
   - Distinguish unhealthy runs from `not_enough_data`.

4. **Inspector and reports**
   - Present topology, trace summaries, warnings, best states, feasibility, and baseline
     comparison.
   - Preserve raw data links and metadata so reports can be audited.

5. **Baselines and benchmarks**
   - Compare THRML-backed runs against exact enumeration and classical baselines under fixed
     seeds and declared resource budgets.
   - Keep fixed-work and fixed-time comparisons separate.
   - Recompute objectives from candidate witnesses.

### ThermoMap Capability Track

ThermoMap crosses the five product layers through two additional capability groups:

- **Compilation and mapping**
   - Maintain target-independent model semantics separately from `TSUSpec` target facts.
   - Validate and transform models, then partition, place, route, quantize, and schedule them
     under explicit target constraints.
   - Record auxiliary variables, rejected mappings, approximation error, and all parameter
     provenance.

- **Verification and thermodynamic roofline**
   - Compare exact small laws and larger reference runs against implemented behavior.
   - Keep circuit, color, communication, mixing, and host costs distinct.
   - Name the observable in every ESS-adjusted metric and distinguish modeled values from
     measurements.

## Data Path

```text
QUBO/BQM/Ising input
-> IsingModel
-> audited private THRML lowering
-> SampleResult
-> diagnostics
-> inspector or benchmark report
```

The current path reaches diagnostics, the benchmark oracle, and deterministic artifact-only
Inspector JSON/Markdown export. Unified HTML, CLI, topology, profile, and baseline report
integration remain target behavior.

Each arrow is a checked boundary. Model conversion is checked by exhaustive small-instance
energy equivalence. THRML lowering is checked by analytic Gibbs conditionals and tiny
Boltzmann distributions. Benchmark reports are checked by witness recomputation.

## Known Non-Claims

- No THRML speedup is claimed until measured against classical and GPU baselines under
  recorded fixed-work or fixed-time budgets.
- Public THRML execution is a JAX/GPU simulation path. A production TSU result requires
  backend-specific hardware evidence and cannot be inferred from simulator output or the
  Jelinčič system-level energy model.
- Fixed-beta Gibbs is a validation target, not a claim of competitive optimization quality.
- R-hat, ESS, diversity, and related diagnostics are warnings about sampler behavior, not
  proofs of optimality.
- Dense QUBO graphs may reduce or eliminate block-parallel advantage because graph coloring
  can produce many small color classes.
- Best-known benchmark values are not correctness oracles unless the source and witness are
  independently verified.

## Stage 2 Runtime Contract

The fixed-beta and parallel-tempering correctness paths are implemented. Their runtime
contracts are:

- `THRMLSampler.sample`;
- `THRMLSampler.sample_qubo`;
- `THRMLSampler.sample_ising`;
- IR-to-THRML lowering;
- graph-coloring block construction;
- seed, initialization, schedule, and `num_reads` controls;
- independent energy recomputation under the canonical convention;
- raw sample and trace capture;
- analytic validation on tiny Ising fixtures.

Parallel tempering must use the EVAL-EQ-014 exchange ratio, advance every replica by the
configured number of local sweeps between exchange opportunities, attempt the sole adjacent
pair at every interval for a two-replica ladder, and preserve cold-slot and per-beta traces.
The 2026-07-14 targeted invariants and optional THRML suite close this correctness criterion.
Device-side/vectorized replica exchange, adaptive ladders, and performance calibration remain
future runtime work and do not reopen the correctness result.

## Evidence Standard

A result is done only when the matching independent check has run and the evidence is
recorded. At minimum, record:

- command used;
- pass/fail result;
- seed and RNG identity;
- solver/backend versions;
- device and operating system when numerics or performance may depend on them;
- raw samples and traces for stochastic claims;
- timing split into compile, sample, diagnostics, tuning, and wall-clock;
- SHA-256 checksum for generated artifacts;
- primary-source URL or DOI for external numbers.

## Current Status

Stages 0-3 have implemented core deliverables: the canonical Ising model, offset-preserving
QUBO/BQM/Ising conversion, `SampleResult`, fixed-beta THRML lowering, graph-colored blocks,
multi-chain traces, diagnostics, the JSON evaluator, and the strict benchmark oracle.
Parallel-tempering correctness and diagnostic threshold/flag semantics have recorded
verification. The diagnostics core still lacks rank-normalized bulk/tail ESS, general
constraint feasibility, and complete joint-mode coverage. Pairwise categorical/domain-wall
lowering, provenanced target facts, quantization, exact small-law comparison, logical target
assessment, and supplied-partition communication analysis form the current ThermoMap analysis
foundation. The artifact-only Inspector core and complete target-fact/topology contract are
implemented. General constraint encoding, automatic physical mapping, calibrated costs, full
Inspector/HTML integration, and classical-baseline runners remain absent. See
`reference/00-roadmap/README.md` for the live status and the autonomous implementation roadmap
for the dependency order.
