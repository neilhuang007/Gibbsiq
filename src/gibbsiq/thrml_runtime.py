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

import functools
import math
import random
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from gibbsiq.blocks import BlockPartition, color_blocks, graph_density, validate_partition
from gibbsiq.conversions import compile_ising, compile_qubo
from gibbsiq.diagnostics import compute_diagnostics, distance_to_best_trace, magnetization_trace
from gibbsiq.model import IsingModel, Variable, finite_float
from gibbsiq.result import SampleResult, best_index

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


@dataclass(frozen=True, slots=True)
class SamplerConfig:
    """Controls for one THRML block-Gibbs run.

    ``beta`` is the inverse temperature used while samples are collected.
    ``warmup_beta_ladder`` optionally anneals the warmup phase: the
    ``n_warmup`` sweeps are split across the ladder entries in order (the
    last entry absorbs the remainder) before sampling starts at ``beta``.
    ``num_chains`` runs vmapped independent chains from one split seed; the
    result records a chain id for every sample so later diagnostics can
    compute between-chain disagreement without rerunning the sampler.
    ``parallel_tempering_betas`` enables opt-in replica exchange. It is a
    strictly increasing inverse-temperature ladder whose last entry must equal
    ``beta``; returned samples come from that cold slot.
    """

    beta: float = 1.0
    n_warmup: int = 100
    steps_per_sample: int = 1
    num_chains: int = 1
    seed: int = 0
    init: str = "hinton"
    warmup_beta_ladder: tuple[float, ...] | None = None
    parallel_tempering_betas: tuple[float, ...] | None = None
    parallel_tempering_swap_interval: int = 1

    def __post_init__(self) -> None:
        beta = finite_float(self.beta, name="beta")
        if beta <= 0.0:
            raise ValueError(f"beta must be positive, got {self.beta!r}")
        object.__setattr__(self, "beta", beta)
        for name in (
            "n_warmup",
            "steps_per_sample",
            "num_chains",
            "seed",
            "parallel_tempering_swap_interval",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer, got {value!r}")
        if self.n_warmup < 0:
            raise ValueError(f"n_warmup must be >= 0, got {self.n_warmup}")
        if self.steps_per_sample < 1:
            raise ValueError(f"steps_per_sample must be >= 1, got {self.steps_per_sample}")
        if self.num_chains < 1:
            raise ValueError(f"num_chains must be >= 1, got {self.num_chains}")
        if self.parallel_tempering_swap_interval < 1:
            raise ValueError(
                f"parallel_tempering_swap_interval must be >= 1, got {self.parallel_tempering_swap_interval}"
            )
        if self.init not in INIT_POLICIES:
            raise ValueError(f"init must be one of {INIT_POLICIES}, got {self.init!r}")
        if self.warmup_beta_ladder is not None:
            ladder = tuple(
                finite_float(value, name="warmup_beta_ladder entry") for value in self.warmup_beta_ladder
            )
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
        if self.parallel_tempering_betas is not None:
            if self.warmup_beta_ladder is not None:
                raise ValueError(
                    "warmup_beta_ladder and parallel_tempering_betas are separate schedule modes; "
                    "set only one of them"
                )
            ladder = tuple(
                finite_float(value, name="parallel_tempering_betas entry")
                for value in self.parallel_tempering_betas
            )
            if len(ladder) < 2:
                raise ValueError("parallel_tempering_betas must contain at least two beta values")
            if any(value <= 0.0 for value in ladder):
                raise ValueError(f"parallel_tempering_betas entries must be positive, got {ladder!r}")
            if any(left >= right for left, right in zip(ladder, ladder[1:])):
                raise ValueError(
                    f"parallel_tempering_betas must be strictly increasing from hot to cold, got {ladder!r}"
                )
            if ladder[-1] != beta:
                raise ValueError(
                    "parallel_tempering_betas must end at beta so returned samples have a fixed "
                    f"target distribution; got beta={beta!r}, ladder={ladder!r}"
                )
            object.__setattr__(self, "parallel_tempering_betas", ladder)

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


@functools.lru_cache(maxsize=1)
def _edgeless_ising_ebm_class() -> Any:
    """THRML's ``IsingEBM.factors`` indexes ``edges[0]`` and cannot represent a
    model with no couplings; this subclass drops the empty coupling factor so
    isolated-spin models (h only) still lower cleanly."""
    _, _, thrml, thrml_models = _require_thrml()

    class _EdgelessIsingEBM(thrml_models.IsingEBM):  # type: ignore[name-defined]
        @property
        def factors(self) -> list[Any]:
            return [thrml_models.SpinEBMFactor([thrml.Block(self.nodes)], self.beta * self.biases)]

    return _EdgelessIsingEBM


class _Lowering:
    """Static THRML artifacts for one model, reusable across beta values."""

    def __init__(self, model: IsingModel, partition: BlockPartition):
        jax, jnp, thrml, thrml_models = _require_thrml()
        self._jax = jax
        self._jnp = jnp
        self._thrml_models = thrml_models
        self.nodes = [thrml.SpinNode() for _ in model.variables]
        node_of = dict(zip(model.variables, self.nodes))
        self.edges = [(node_of[left], node_of[right]) for left, right in model.quadratic]
        # THRML sign mapping (see module docstring): biases = -h, weights = -J.
        self.biases = jnp.asarray([-model.linear[variable] for variable in model.variables])
        self.weights = jnp.asarray([-coefficient for coefficient in model.quadratic.values()])
        self.free_blocks = [
            thrml.Block([node_of[variable] for variable in block]) for block in partition.blocks
        ]
        position_of = {variable: index for index, variable in enumerate(model.variables)}
        self.block_positions = tuple(
            tuple(position_of[variable] for variable in block) for block in partition.blocks
        )
        self.observed_blocks = [thrml.Block(self.nodes)]

    def program(self, beta: float) -> tuple[Any, Any]:
        """Build the ``(ebm, program)`` pair for one inverse temperature."""
        ebm_class = self._thrml_models.IsingEBM if self.edges else _edgeless_ising_ebm_class()
        ebm = ebm_class(self.nodes, self.edges, self.biases, self.weights, self._jnp.asarray(beta))
        return ebm, self._thrml_models.IsingSamplingProgram(ebm, self.free_blocks, clamped_blocks=[])

    def initial_state(self, key: Any, ebm: Any, policy: str) -> list[Any]:
        """Build per-block boolean initial states for one chain."""
        if policy == "hinton":
            return self._thrml_models.hinton_init(key, ebm, self.free_blocks, ())
        sizes = [len(block.nodes) for block in self.free_blocks]
        if policy == "random":
            keys = self._jax.random.split(key, len(sizes))
            return [
                self._jax.random.bernoulli(block_key, 0.5, (size,)) for block_key, size in zip(keys, sizes)
            ]
        return [self._jnp.full((size,), policy == "all_up", dtype=bool) for size in sizes]

    def sample_from_state(self, state: list[Any], variables: tuple[Variable, ...]) -> dict[Variable, int]:
        """Decode a free-block state list into model variable order."""
        spins = [0] * len(variables)
        for positions, block_state in zip(self.block_positions, state):
            host_values = self._jax.device_get(block_state)
            for position, value in zip(positions, host_values):
                spins[position] = 1 if bool(value) else -1
        return {variable: spins[position] for position, variable in enumerate(variables)}


@dataclass(frozen=True, slots=True)
class _DecodedChains:
    """Decoded samples and per-chain traces from THRML boolean states."""

    samples: list[dict[Variable, int]]
    chain_ids: list[int]
    energy_trace: list[list[float]]
    best_trace: list[list[float]]
    sample_chains: list[list[dict[Variable, int]]]


@dataclass(frozen=True, slots=True)
class _TemperingChain:
    """One independent parallel-tempering ladder's cold samples and swap evidence."""

    samples: list[dict[Variable, int]]
    energy_trace: list[float]
    best_trace: list[float]
    per_beta_energy: list[list[float]]
    swap_trace: list[dict[str, Any]]
    swap_attempts: int
    swap_accepts: int
    swap_attempts_by_pair: dict[str, int]
    swap_accepts_by_pair: dict[str, int]


@dataclass(frozen=True, slots=True)
class _DecodedTempering:
    """Merged cold-beta samples and traces from all PT ladders."""

    samples: list[dict[Variable, int]]
    chain_ids: list[int]
    energy_trace: list[list[float]]
    best_trace: list[list[float]]
    sample_chains: list[list[dict[Variable, int]]]
    per_beta_energy: list[list[list[float]]]
    swap_trace: list[dict[str, Any]]
    swap_attempts: int
    swap_accepts: int
    swap_attempts_by_pair: dict[str, int]
    swap_accepts_by_pair: dict[str, int]


def _decode_sample_chains(
    spins: Any,
    model: IsingModel,
    *,
    num_reads: int,
    num_chains: int,
) -> _DecodedChains:
    """Convert THRML spin arrays into Gibbsiq samples and aligned traces."""
    samples: list[dict[Variable, int]] = []
    chain_ids: list[int] = []
    energy_trace: list[list[float]] = []
    best_trace: list[list[float]] = []
    sample_chains: list[list[dict[Variable, int]]] = []
    for chain_index in range(num_chains):
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
    return _DecodedChains(samples, chain_ids, energy_trace, best_trace, sample_chains)


def _advance_block_state(
    *,
    thrml: Any,
    key: Any,
    program: Any,
    state: list[Any],
    free_blocks: list[Any],
    sweeps: int,
) -> list[Any]:
    """Run ``sweeps`` Gibbs sweeps and return the final free-block state."""
    schedule = thrml.SamplingSchedule(n_warmup=sweeps - 1, n_samples=1, steps_per_sample=1)
    observed = thrml.sample_states(key, program, schedule, state, [], free_blocks)
    return [block_states[-1] for block_states in observed]


def _pair_key(left_index: int, right_index: int) -> str:
    return f"{left_index}-{right_index}"


def _run_tempering_chain(
    *,
    thrml: Any,
    jax: Any,
    lowering: _Lowering,
    model: IsingModel,
    config: SamplerConfig,
    programs: Sequence[tuple[float, Any, Any]],
    chain_key: Any,
    chain_index: int,
    num_reads: int,
) -> _TemperingChain:
    """Run one PT ladder and return target-beta samples plus raw swap evidence."""
    beta_ladder = [beta for beta, _, _ in programs]
    key = chain_key
    init_keys = jax.random.split(key, len(programs) + 1)
    key = init_keys[-1]
    states = [
        lowering.initial_state(init_keys[beta_index], ebm, config.init)
        for beta_index, (_, _, ebm) in enumerate(programs)
    ]

    if config.n_warmup:
        for beta_index, (_, program, _) in enumerate(programs):
            key, segment_key = jax.random.split(key)
            states[beta_index] = _advance_block_state(
                thrml=thrml,
                key=segment_key,
                program=program,
                state=states[beta_index],
                free_blocks=lowering.free_blocks,
                sweeps=config.n_warmup,
            )

    energies = [model.energy(lowering.sample_from_state(state, model.variables)) for state in states]
    swap_rng = random.Random(f"{config.seed}:pt:{chain_index}")
    swap_attempts = 0
    swap_accepts = 0
    swap_attempts_by_pair: dict[str, int] = {}
    swap_accepts_by_pair: dict[str, int] = {}
    swap_trace: list[dict[str, Any]] = []
    per_beta_energy: list[list[float]] = [[] for _ in programs]
    samples: list[dict[Variable, int]] = []
    energy_trace: list[float] = []
    best_trace: list[float] = []
    swap_round = 0

    for read_index in range(num_reads):
        for beta_index, (_, program, _) in enumerate(programs):
            key, local_key = jax.random.split(key)
            states[beta_index] = _advance_block_state(
                thrml=thrml,
                key=local_key,
                program=program,
                state=states[beta_index],
                free_blocks=lowering.free_blocks,
                sweeps=config.steps_per_sample,
            )
            energies[beta_index] = model.energy(
                lowering.sample_from_state(states[beta_index], model.variables)
            )

        if (read_index + 1) % config.parallel_tempering_swap_interval == 0:
            parity = swap_round % 2
            swap_round += 1
            for left_index in range(parity, len(programs) - 1, 2):
                right_index = left_index + 1
                beta_left = beta_ladder[left_index]
                beta_right = beta_ladder[right_index]
                energy_left = energies[left_index]
                energy_right = energies[right_index]
                log_acceptance = (beta_left - beta_right) * (energy_right - energy_left)
                uniform = swap_rng.random()
                accepted = log_acceptance >= 0.0 or math.log(uniform) < log_acceptance
                pair = _pair_key(left_index, right_index)
                swap_attempts += 1
                swap_attempts_by_pair[pair] = swap_attempts_by_pair.get(pair, 0) + 1
                if accepted:
                    swap_accepts += 1
                    swap_accepts_by_pair[pair] = swap_accepts_by_pair.get(pair, 0) + 1
                    states[left_index], states[right_index] = states[right_index], states[left_index]
                    energies[left_index], energies[right_index] = energies[right_index], energies[left_index]
                swap_trace.append(
                    {
                        "chain_id": chain_index,
                        "read_index": read_index,
                        "left_beta_index": left_index,
                        "right_beta_index": right_index,
                        "left_beta": beta_left,
                        "right_beta": beta_right,
                        "left_energy_before": energy_left,
                        "right_energy_before": energy_right,
                        "log_acceptance": log_acceptance,
                        "uniform": uniform,
                        "accepted": accepted,
                    }
                )

        for beta_index, energy in enumerate(energies):
            per_beta_energy[beta_index].append(energy)
        cold_sample = lowering.sample_from_state(states[-1], model.variables)
        cold_energy = energies[-1]
        samples.append(cold_sample)
        energy_trace.append(cold_energy)
        best_trace.append(cold_energy if not best_trace else min(best_trace[-1], cold_energy))

    return _TemperingChain(
        samples=samples,
        energy_trace=energy_trace,
        best_trace=best_trace,
        per_beta_energy=per_beta_energy,
        swap_trace=swap_trace,
        swap_attempts=swap_attempts,
        swap_accepts=swap_accepts,
        swap_attempts_by_pair=swap_attempts_by_pair,
        swap_accepts_by_pair=swap_accepts_by_pair,
    )


def _merge_tempering_chains(
    chains: Sequence[_TemperingChain],
    *,
    num_reads: int,
    num_chains: int,
    beta_count: int,
) -> _DecodedTempering:
    samples: list[dict[Variable, int]] = []
    chain_ids: list[int] = []
    energy_trace: list[list[float]] = []
    best_trace: list[list[float]] = []
    sample_chains: list[list[dict[Variable, int]]] = []
    per_beta_energy: list[list[list[float]]] = []
    swap_trace: list[dict[str, Any]] = []
    swap_attempts = 0
    swap_accepts = 0
    swap_attempts_by_pair: dict[str, int] = {}
    swap_accepts_by_pair: dict[str, int] = {}

    for chain_index in range(num_chains):
        if chain_index >= len(chains):
            energy_trace.append([])
            best_trace.append([])
            sample_chains.append([])
            per_beta_energy.append([[] for _ in range(beta_count)])
            continue
        chain = chains[chain_index]
        remaining = num_reads - len(samples)
        take = max(0, min(remaining, len(chain.samples)))
        samples.extend(chain.samples[:take])
        chain_ids.extend([chain_index] * take)
        energy_trace.append(chain.energy_trace[:take])
        best_trace.append(chain.best_trace[:take])
        sample_chains.append(chain.samples[:take])
        per_beta_energy.append([row[:take] for row in chain.per_beta_energy])
        swap_trace.extend(event for event in chain.swap_trace if event["read_index"] < take)
        swap_attempts += sum(1 for event in chain.swap_trace if event["read_index"] < take)
        swap_accepts += sum(
            1 for event in chain.swap_trace if event["read_index"] < take and event["accepted"]
        )
        for event in chain.swap_trace:
            if event["read_index"] >= take:
                continue
            pair = _pair_key(event["left_beta_index"], event["right_beta_index"])
            swap_attempts_by_pair[pair] = swap_attempts_by_pair.get(pair, 0) + 1
            if event["accepted"]:
                swap_accepts_by_pair[pair] = swap_accepts_by_pair.get(pair, 0) + 1
    return _DecodedTempering(
        samples=samples,
        chain_ids=chain_ids,
        energy_trace=energy_trace,
        best_trace=best_trace,
        sample_chains=sample_chains,
        per_beta_energy=per_beta_energy,
        swap_trace=swap_trace,
        swap_attempts=swap_attempts,
        swap_accepts=swap_accepts,
        swap_attempts_by_pair=swap_attempts_by_pair,
        swap_accepts_by_pair=swap_accepts_by_pair,
    )


def _build_metadata(
    config: SamplerConfig,
    model: IsingModel,
    partition: BlockPartition,
    thrml: Any,
    jax: Any,
    device: Any,
    *,
    num_reads: int,
    reads_per_chain: int,
    lower_seconds: float,
    sample_seconds: float,
) -> dict[str, Any]:
    """Assemble runtime provenance for a ``SampleResult``."""
    metadata = {
        "sampler": "gibbsiq.THRMLSampler",
        "thrml_version": getattr(thrml, "__version__", "unknown"),
        "jax_version": jax.__version__,
        "device_platform": device.platform,
        "device_kind": device.device_kind,
        "seed": config.seed,
        "beta": config.beta,
        "warmup_beta_ladder": None if config.warmup_beta_ladder is None else list(config.warmup_beta_ladder),
        "parallel_tempering_enabled": config.parallel_tempering_betas is not None,
        "parallel_tempering_betas": (
            None if config.parallel_tempering_betas is None else list(config.parallel_tempering_betas)
        ),
        "parallel_tempering_swap_interval": config.parallel_tempering_swap_interval,
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
    return metadata


class THRMLSampler:
    """Sample Gibbsiq Ising models through THRML block-Gibbs programs."""

    def __init__(self, config: SamplerConfig | None = None):
        self.config = SamplerConfig() if config is None else config
        _require_thrml()

    def sample_qubo(
        self, qubo: Mapping[Any, Any], *, num_reads: int = 1, **compile_kwargs: Any
    ) -> SampleResult:
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

    def _sample_parallel_tempering(
        self,
        model: IsingModel,
        *,
        num_reads: int,
        partition: BlockPartition,
        lowering: _Lowering,
        lower_started: float,
    ) -> SampleResult:
        """Run opt-in replica exchange and return cold-beta samples."""
        jax, _, thrml, _ = _require_thrml()
        config = self.config
        assert config.parallel_tempering_betas is not None
        programs = []
        for beta in config.parallel_tempering_betas:
            ebm, program = lowering.program(beta)
            programs.append((beta, program, ebm))
        reads_per_chain = -(-num_reads // config.num_chains)
        lower_seconds = time.perf_counter() - lower_started

        sample_started = time.perf_counter()
        root_key = jax.random.key(config.seed)
        chain_keys = jax.random.split(root_key, config.num_chains)
        chains: list[_TemperingChain] = []
        for chain_index in range(config.num_chains):
            remaining = num_reads - chain_index * reads_per_chain
            chain_reads = max(0, min(reads_per_chain, remaining))
            if chain_reads <= 0:
                break
            chains.append(
                _run_tempering_chain(
                    thrml=thrml,
                    jax=jax,
                    lowering=lowering,
                    model=model,
                    config=config,
                    programs=programs,
                    chain_key=chain_keys[chain_index],
                    chain_index=chain_index,
                    num_reads=chain_reads,
                )
            )
        decoded = _merge_tempering_chains(
            chains,
            num_reads=num_reads,
            num_chains=config.num_chains,
            beta_count=len(programs),
        )
        sample_seconds = time.perf_counter() - sample_started

        diagnostics_started = time.perf_counter()
        flat_energies = [energy for chain in decoded.energy_trace for energy in chain]
        best_sample = decoded.samples[best_index(flat_energies)]
        beta_schedule = [
            {
                "phase": "warmup",
                "mode": "parallel_tempering",
                "beta_ladder": list(config.parallel_tempering_betas),
                "sweeps_per_beta": config.n_warmup,
            },
            {
                "phase": "sampling",
                "mode": "parallel_tempering",
                "target_beta": config.beta,
                "beta_ladder": list(config.parallel_tempering_betas),
                "n_samples": reads_per_chain,
                "steps_per_sample": config.steps_per_sample,
                "swap_interval": config.parallel_tempering_swap_interval,
            },
        ]
        magnetization_chains = magnetization_trace(decoded.sample_chains, model.variables)
        distance_chains = distance_to_best_trace(decoded.sample_chains, best_sample, model.variables)
        traces: dict[str, Any] = {
            "energy": decoded.energy_trace,
            "best_energy_so_far": decoded.best_trace,
            "sample_chain_ids": decoded.chain_ids,
            "beta_schedule": beta_schedule,
            "magnetization": magnetization_chains,
            "distance_to_best": distance_chains,
            "parallel_tempering": {
                "beta_ladder": list(config.parallel_tempering_betas),
                "target_beta_index": len(config.parallel_tempering_betas) - 1,
                "per_beta_energy": decoded.per_beta_energy,
                "swap_trace": decoded.swap_trace,
                "swap_attempts": decoded.swap_attempts,
                "swap_accepts": decoded.swap_accepts,
                "swap_acceptance_rate": (
                    decoded.swap_accepts / decoded.swap_attempts if decoded.swap_attempts else None
                ),
                "swap_attempts_by_pair": decoded.swap_attempts_by_pair,
                "swap_accepts_by_pair": decoded.swap_accepts_by_pair,
            },
        }

        device = jax.devices()[0]
        metadata = _build_metadata(
            config,
            model,
            partition,
            thrml,
            jax,
            device,
            num_reads=num_reads,
            reads_per_chain=reads_per_chain,
            lower_seconds=lower_seconds,
            sample_seconds=sample_seconds,
        )
        metadata.update(
            {
                "parallel_tempering_swap_attempts": decoded.swap_attempts,
                "parallel_tempering_swap_accepts": decoded.swap_accepts,
                "parallel_tempering_swap_acceptance_rate": (
                    decoded.swap_accepts / decoded.swap_attempts if decoded.swap_attempts else None
                ),
                "parallel_tempering_swap_rng": "python.random.Random(seed='seed:pt:chain_id')",
            }
        )

        diagnostics = compute_diagnostics(
            energy_chains=decoded.energy_trace,
            samples=decoded.samples,
            variables=model.variables,
            magnetization_chains=magnetization_chains,
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
            model, decoded.samples, traces=traces, diagnostics=diagnostics, metadata=metadata
        )

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

        if config.parallel_tempering_betas is not None:
            return self._sample_parallel_tempering(
                model,
                num_reads=num_reads,
                partition=partition,
                lowering=lowering,
                lower_started=lower_started,
            )

        segments = config.warmup_segments()
        sampling_ebm, sampling_program = lowering.program(config.beta)
        # The chain initializes at the first warmup beta (or the sampling beta
        # when there is no ladder), so the first segment's EBM doubles as the
        # init EBM.
        init_ebm = sampling_ebm
        segment_programs: list[tuple[Any, int]] = []
        for beta, sweeps in segments:
            ebm, program = lowering.program(beta)
            if not segment_programs:
                init_ebm = ebm
            segment_programs.append((program, sweeps))
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
            for (program, sweeps), segment_key in zip(segment_programs, keys[1:-1]):
                # One segment = `sweeps` full sweeps at that beta; the last
                # sweep doubles as the observation that carries the state out.
                segment_schedule = thrml.SamplingSchedule(
                    n_warmup=sweeps - 1, n_samples=1, steps_per_sample=1
                )
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

        decoded = _decode_sample_chains(
            spins,
            model,
            num_reads=num_reads,
            num_chains=config.num_chains,
        )

        # Trace post-processing and diagnostics share one timing bucket
        # (EVAL-EQ-010 resource split): everything after decode is telemetry.
        diagnostics_started = time.perf_counter()
        flat_energies = [energy for chain in decoded.energy_trace for energy in chain]
        best_sample = decoded.samples[best_index(flat_energies)]

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
        magnetization_chains = magnetization_trace(decoded.sample_chains, model.variables)
        distance_chains = distance_to_best_trace(decoded.sample_chains, best_sample, model.variables)
        traces: dict[str, Any] = {
            "energy": decoded.energy_trace,
            "best_energy_so_far": decoded.best_trace,
            "sample_chain_ids": decoded.chain_ids,
            "beta_schedule": beta_schedule,
            "magnetization": magnetization_chains,
            "distance_to_best": distance_chains,
        }

        device = jax.devices()[0]
        metadata = _build_metadata(
            config,
            model,
            partition,
            thrml,
            jax,
            device,
            num_reads=num_reads,
            reads_per_chain=reads_per_chain,
            lower_seconds=lower_seconds,
            sample_seconds=sample_seconds,
        )

        diagnostics = compute_diagnostics(
            energy_chains=decoded.energy_trace,
            samples=decoded.samples,
            variables=model.variables,
            magnetization_chains=magnetization_chains,
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
            model, decoded.samples, traces=traces, diagnostics=diagnostics, metadata=metadata
        )
