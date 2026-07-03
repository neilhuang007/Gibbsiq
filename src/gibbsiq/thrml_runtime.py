"""THRML optimization runtime: lower the Ising IR into block-Gibbs programs.

Sign convention audit. THRML's ``IsingEBM`` defines

```text
E_thrml(s) = -beta * (sum_i b_i s_i + sum_(i,j) w_ij s_i s_j)
```

and samples ``p(s) proportional to exp(-E_thrml(s))``, while Gibbsiq's audited
convention is ``E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j``
targeted at ``p(s) proportional to exp(-beta * E(s))``. Equating the two
Boltzmann distributions requires ``b = -h`` and ``w = -J``. The offset shifts
every energy equally, never changes the distribution, and is preserved because
all reported energies are recomputed through ``IsingModel.energy`` rather than
read back from THRML. THRML represents spin states as booleans with ``True``
meaning ``+1``. The two-spin analytic-distribution test pins this mapping.

The ``thrml`` and ``jax`` imports are deferred so that ``import gibbsiq``
works without the optional ``thrml`` extra, mirroring the ``dimod`` pattern.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from gibbsiq.blocks import BlockPartition, color_blocks, graph_density, validate_partition
from gibbsiq.conversions import compile_ising, compile_qubo
from gibbsiq.diagnostics import compute_diagnostics, distance_to_best_trace, magnetization_trace
from gibbsiq.model import IsingModel, Variable, finite_float
from gibbsiq.result import SampleResult

INIT_POLICIES = ("hinton", "random", "all_up", "all_down")


def _require_thrml() -> tuple[Any, Any, Any, Any]:
    """Import the optional THRML/JAX stack or fail with an install hint."""
    try:
        import jax
        import jax.numpy as jnp
        import thrml
        from thrml import models as thrml_models
    except ImportError as error:  # pragma: no cover - exercised only without optional dep
        raise ImportError(
            "THRMLSampler requires the optional 'thrml' package; install with pip install gibbsiq[thrml]"
        ) from error
    return jax, jnp, thrml, thrml_models


@dataclass(frozen=True)
class SamplerConfig:
    """Controls for one THRML block-Gibbs run.

    ``beta`` is the inverse temperature used while samples are collected.
    ``warmup_beta_ladder`` optionally anneals the warmup phase: the
    ``n_warmup`` sweeps are split across the ladder entries in order (the
    last entry absorbs the remainder) before sampling starts at ``beta``.
    ``num_chains`` runs vmapped independent chains from one split seed; the
    result records a chain id for every sample so later diagnostics can
    compute between-chain disagreement without rerunning the sampler.
    """

    beta: float = 1.0
    n_warmup: int = 100
    steps_per_sample: int = 1
    num_chains: int = 1
    seed: int = 0
    init: str = "hinton"
    warmup_beta_ladder: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        beta = finite_float(self.beta, name="beta")
        if beta <= 0.0:
            raise ValueError(f"beta must be positive, got {self.beta!r}")
        object.__setattr__(self, "beta", beta)
        for name in ("n_warmup", "steps_per_sample", "num_chains", "seed"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer, got {value!r}")
        if self.n_warmup < 0:
            raise ValueError(f"n_warmup must be >= 0, got {self.n_warmup}")
        if self.steps_per_sample < 1:
            raise ValueError(f"steps_per_sample must be >= 1, got {self.steps_per_sample}")
        if self.num_chains < 1:
            raise ValueError(f"num_chains must be >= 1, got {self.num_chains}")
        if self.init not in INIT_POLICIES:
            raise ValueError(f"init must be one of {INIT_POLICIES}, got {self.init!r}")
        if self.warmup_beta_ladder is not None:
            ladder = tuple(finite_float(value, name="warmup_beta_ladder entry") for value in self.warmup_beta_ladder)
            if not ladder:
                raise ValueError("warmup_beta_ladder must contain at least one beta")
            if any(value <= 0.0 for value in ladder):
                raise ValueError(f"warmup_beta_ladder entries must be positive, got {ladder!r}")
            if self.n_warmup < len(ladder):
                raise ValueError(
                    f"n_warmup={self.n_warmup} cannot cover a {len(ladder)}-entry warmup_beta_ladder; "
                    "each ladder beta needs at least one sweep"
                )
            object.__setattr__(self, "warmup_beta_ladder", ladder)

    def warmup_segments(self) -> tuple[tuple[float, int], ...]:
        """Return ``(beta, sweeps)`` warmup segments; the remainder lands on the last."""
        if self.warmup_beta_ladder is None:
            return ()
        count = len(self.warmup_beta_ladder)
        base = self.n_warmup // count
        segments = [(beta, base) for beta in self.warmup_beta_ladder]
        last_beta, _ = segments[-1]
        segments[-1] = (last_beta, self.n_warmup - base * (count - 1))
        return tuple(segments)


_EDGELESS_EBM_CLASS: Any = None


def _edgeless_ising_ebm_class() -> Any:
    """THRML's ``IsingEBM.factors`` indexes ``edges[0]`` and cannot represent a
    model with no couplings; this subclass drops the empty coupling factor so
    isolated-spin models (h only) still lower cleanly."""
    global _EDGELESS_EBM_CLASS
    if _EDGELESS_EBM_CLASS is None:
        _, _, thrml, thrml_models = _require_thrml()

        class _EdgelessIsingEBM(thrml_models.IsingEBM):
            @property
            def factors(self) -> list[Any]:
                return [thrml_models.SpinEBMFactor([thrml.Block(self.nodes)], self.beta * self.biases)]

        _EDGELESS_EBM_CLASS = _EdgelessIsingEBM
    return _EDGELESS_EBM_CLASS


class _Lowering:
    """Static THRML artifacts for one model, reusable across beta values."""

    def __init__(self, model: IsingModel, partition: BlockPartition):
        jax, jnp, thrml, thrml_models = _require_thrml()
        self._thrml = thrml
        self._thrml_models = thrml_models
        self._jnp = jnp
        self.nodes = [thrml.SpinNode() for _ in model.variables]
        node_of = dict(zip(model.variables, self.nodes))
        self.edges = [(node_of[left], node_of[right]) for left, right in model.quadratic]
        # THRML sign mapping (see module docstring): biases = -h, weights = -J.
        self.biases = jnp.asarray([-model.linear[variable] for variable in model.variables])
        self.weights = jnp.asarray([-coefficient for coefficient in model.quadratic.values()])
        self.free_blocks = [thrml.Block([node_of[variable] for variable in block]) for block in partition.blocks]
        self.observed_blocks = [thrml.Block(self.nodes)]

    def program(self, beta: float) -> tuple[Any, Any]:
        """Build the ``(ebm, program)`` pair for one inverse temperature."""
        ebm_class = self._thrml_models.IsingEBM if self.edges else _edgeless_ising_ebm_class()
        ebm = ebm_class(self.nodes, self.edges, self.biases, self.weights, self._jnp.asarray(beta))
        return ebm, self._thrml_models.IsingSamplingProgram(ebm, self.free_blocks, clamped_blocks=[])

    def initial_state(self, key: Any, ebm: Any, policy: str) -> list[Any]:
        """Build per-block boolean initial states for one chain."""
        jax, jnp, _, thrml_models = _require_thrml()
        if policy == "hinton":
            return thrml_models.hinton_init(key, ebm, self.free_blocks, ())
        sizes = [len(block.nodes) for block in self.free_blocks]
        if policy == "random":
            keys = jax.random.split(key, len(sizes))
            return [jax.random.bernoulli(block_key, 0.5, (size,)) for block_key, size in zip(keys, sizes)]
        return [jnp.full((size,), policy == "all_up", dtype=bool) for size in sizes]


class THRMLSampler:
    """Sample Gibbsiq Ising models through THRML block-Gibbs programs."""

    def __init__(self, config: SamplerConfig | None = None):
        self.config = SamplerConfig() if config is None else config
        _require_thrml()

    def sample_qubo(self, qubo: Mapping[Any, Any], *, num_reads: int = 1, **compile_kwargs: Any) -> SampleResult:
        """Compile a QUBO through ``compile_qubo`` and sample it."""
        return self.sample(compile_qubo(qubo, **compile_kwargs), num_reads=num_reads)

    def sample_ising(
        self,
        h: Mapping[Any, Any],
        J: Mapping[Any, Any] | None = None,
        *,
        num_reads: int = 1,
        **compile_kwargs: Any,
    ) -> SampleResult:
        """Compile Ising fields through ``compile_ising`` and sample them."""
        return self.sample(compile_ising(h, J, **compile_kwargs), num_reads=num_reads)

    def sample(
        self,
        model: IsingModel,
        *,
        num_reads: int = 1,
        partition: BlockPartition | None = None,
    ) -> SampleResult:
        """Run block Gibbs on ``model`` and return exactly ``num_reads`` samples.

        Reads are split evenly across chains (``ceil(num_reads / num_chains)``
        per chain); surplus samples are dropped from the end of the last chain
        and the per-chain traces are truncated to match, so the flat
        ``energies`` tuple always equals the concatenated ``traces["energy"]``.
        """
        if isinstance(num_reads, bool) or not isinstance(num_reads, int) or num_reads < 1:
            raise ValueError(f"num_reads must be an integer >= 1, got {num_reads!r}")
        if not model.variables:
            raise ValueError("cannot sample a model with no variables")

        jax, jnp, thrml, _ = _require_thrml()
        config = self.config

        lower_started = time.perf_counter()
        if partition is None:
            partition = color_blocks(model)
        validate_partition(model, partition)
        lowering = _Lowering(model, partition)

        segments = config.warmup_segments()
        segment_programs = [(lowering.program(beta)[1], beta, sweeps) for beta, sweeps in segments]
        sampling_ebm, sampling_program = lowering.program(config.beta)
        init_beta = segments[0][0] if segments else config.beta
        init_ebm = lowering.program(init_beta)[0] if segments else sampling_ebm
        reads_per_chain = -(-num_reads // config.num_chains)
        final_warmup = 0 if segments else config.n_warmup
        sampling_schedule = thrml.SamplingSchedule(
            n_warmup=final_warmup,
            n_samples=reads_per_chain,
            steps_per_sample=config.steps_per_sample,
        )
        lower_seconds = time.perf_counter() - lower_started

        def run_chain(chain_key: Any) -> Any:
            keys = jax.random.split(chain_key, len(segment_programs) + 2)
            state = lowering.initial_state(keys[0], init_ebm, config.init)
            for (program, _, sweeps), segment_key in zip(segment_programs, keys[1:-1]):
                # One segment = `sweeps` full sweeps at that beta; the last
                # sweep doubles as the observation that carries the state out.
                segment_schedule = thrml.SamplingSchedule(n_warmup=sweeps - 1, n_samples=1, steps_per_sample=1)
                observed = thrml.sample_states(
                    segment_key, program, segment_schedule, state, [], lowering.free_blocks
                )
                state = [block_states[-1] for block_states in observed]
            return thrml.sample_states(
                keys[-1], sampling_program, sampling_schedule, state, [], lowering.observed_blocks
            )[0]

        sample_started = time.perf_counter()
        root_key = jax.random.key(config.seed)
        chain_keys = jax.random.split(root_key, config.num_chains)
        if config.num_chains == 1:
            stacked = run_chain(chain_keys[0])[None, ...]
        else:
            stacked = jax.vmap(run_chain)(chain_keys)
        spins = jax.device_get(jnp.where(stacked, 1, -1))
        sample_seconds = time.perf_counter() - sample_started

        samples: list[dict[Variable, int]] = []
        chain_ids: list[int] = []
        energy_trace: list[list[float]] = []
        best_trace: list[list[float]] = []
        sample_chains: list[list[dict[Variable, int]]] = []
        for chain_index in range(config.num_chains):
            remaining = num_reads - len(samples)
            chain_energies: list[float] = []
            chain_best: list[float] = []
            chain_samples: list[dict[Variable, int]] = []
            for row in spins[chain_index][:remaining]:
                sample = {variable: int(value) for variable, value in zip(model.variables, row)}
                energy = model.energy(sample)
                samples.append(sample)
                chain_ids.append(chain_index)
                chain_energies.append(energy)
                chain_best.append(energy if not chain_best else min(chain_best[-1], energy))
                chain_samples.append(sample)
            energy_trace.append(chain_energies)
            best_trace.append(chain_best)
            sample_chains.append(chain_samples)

        # Trace post-processing and diagnostics share one timing bucket
        # (EVAL-EQ-010 resource split): everything after decode is telemetry.
        diagnostics_started = time.perf_counter()
        flat_energies = [energy for chain in energy_trace for energy in chain]
        best_sample = samples[min(range(len(flat_energies)), key=flat_energies.__getitem__)]

        beta_schedule = [
            {"phase": "warmup", "beta": beta, "sweeps": sweeps} for beta, sweeps in segments
        ] or [{"phase": "warmup", "beta": config.beta, "sweeps": config.n_warmup}]
        beta_schedule.append(
            {
                "phase": "sampling",
                "beta": config.beta,
                "n_samples": reads_per_chain,
                "steps_per_sample": config.steps_per_sample,
            }
        )
        traces = {
            "energy": energy_trace,
            "best_energy_so_far": best_trace,
            "sample_chain_ids": chain_ids,
            "beta_schedule": beta_schedule,
            "magnetization": magnetization_trace(sample_chains, model.variables),
            "distance_to_best": distance_to_best_trace(sample_chains, best_sample, model.variables),
        }

        device = jax.devices()[0]
        metadata = {
            "sampler": "gibbsiq.THRMLSampler",
            "thrml_version": getattr(thrml, "__version__", "unknown"),
            "jax_version": jax.__version__,
            "device_platform": device.platform,
            "device_kind": device.device_kind,
            "seed": config.seed,
            "beta": config.beta,
            "warmup_beta_ladder": None if config.warmup_beta_ladder is None else list(config.warmup_beta_ladder),
            "n_warmup": config.n_warmup,
            "steps_per_sample": config.steps_per_sample,
            "num_chains": config.num_chains,
            "num_reads": num_reads,
            "reads_per_chain": reads_per_chain,
            "init": config.init,
            "graph_density": graph_density(model),
            "energy_convention": "E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j",
            "thrml_sign_mapping": "biases = -h, weights = -J; boolean True state = +1",
            "lower_seconds": lower_seconds,
            "sample_seconds": sample_seconds,
        }
        metadata.update(partition.to_metadata())

        diagnostics = compute_diagnostics(
            energy_chains=energy_trace,
            samples=samples,
            variables=model.variables,
            magnetization_chains=traces["magnetization"],
            timings={
                "lower_seconds": lower_seconds,
                "sample_seconds": sample_seconds,
                "device_platform": device.platform,
                "device_kind": device.device_kind,
            },
        )
        diagnostics_seconds = time.perf_counter() - diagnostics_started
        diagnostics["runtime"]["diagnostics_seconds"] = diagnostics_seconds
        metadata["diagnostics_seconds"] = diagnostics_seconds

        return SampleResult.from_model(
            model, samples, traces=traces, diagnostics=diagnostics, metadata=metadata
        )
