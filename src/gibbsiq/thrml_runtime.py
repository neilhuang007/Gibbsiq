"""THRML optimization runtime: lowers the Ising IR into block-Gibbs programs.

Sign mapping: THRML's ``IsingEBM`` uses
``E_thrml(s) = -beta * (sum_i b_i s_i + sum_(i,j) w_ij s_i s_j)``,
Gibbsiq uses ``E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j``.
Equal Boltzmann distributions require ``b = -h``, ``w = -J``. Offset is
never sent to THRML; energies are always recomputed via ``IsingModel.energy``.
THRML boolean ``True`` = spin ``+1`` (pinned by the two-spin analytic test).

``thrml``/``jax`` imports are deferred so ``import gibbsiq`` works without
the optional extra (mirrors the ``dimod`` pattern).
"""

from __future__ import annotations

import functools
import math
import platform
import random
import sys
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
_BACKEND_RELATIVE_ERROR_LIMIT = 1e-6
_LOCAL_LOGIT_ERROR_LIMIT = 1e-4


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

    ``beta``: sampling-phase inverse temperature. ``warmup_beta_ladder``:
    optional annealing schedule, ``n_warmup`` sweeps split across entries
    (remainder to the last), ending at ``beta``. ``num_chains``: vmapped
    chains from one split seed, chain id recorded per sample for
    between-chain diagnostics. ``parallel_tempering_betas``: opt-in replica
    exchange, strictly increasing ladder ending at ``beta`` (cold slot).
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
        if isinstance(self.beta, bool):
            raise ValueError(f"beta must be a finite positive number, got {self.beta!r}")
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
        if not 0 <= self.seed <= 2**32 - 1:
            raise ValueError(f"seed must be in JAX's uint32 key domain [0, {2**32 - 1}], got {self.seed}")
        if self.parallel_tempering_swap_interval < 1:
            raise ValueError(
                f"parallel_tempering_swap_interval must be >= 1, got {self.parallel_tempering_swap_interval}"
            )
        if self.init not in INIT_POLICIES:
            raise ValueError(f"init must be one of {INIT_POLICIES}, got {self.init!r}")
        if self.warmup_beta_ladder is not None:
            raw_ladder = tuple(self.warmup_beta_ladder)
            if any(isinstance(value, bool) for value in raw_ladder):
                raise ValueError("warmup_beta_ladder entries must be finite positive numbers")
            ladder = tuple(finite_float(value, name="warmup_beta_ladder entry") for value in raw_ladder)
            if not ladder:
                raise ValueError("warmup_beta_ladder must contain at least one beta")
            if any(value <= 0.0 for value in ladder):
                raise ValueError(f"warmup_beta_ladder entries must be positive, got {ladder!r}")
            if self.n_warmup < len(ladder):
                raise ValueError(
                    f"n_warmup={self.n_warmup} cannot cover a {len(ladder)}-entry warmup_beta_ladder; "
                    "each ladder beta needs at least one sweep"
                )
            if ladder[-1] != beta:
                raise ValueError(
                    "warmup_beta_ladder must end at beta so warmup hands the chain to the "
                    f"sampling distribution without an unrecorded temperature jump; got beta={beta!r}, "
                    f"ladder={ladder!r}"
                )
            object.__setattr__(self, "warmup_beta_ladder", ladder)
        if self.parallel_tempering_betas is not None:
            if self.warmup_beta_ladder is not None:
                raise ValueError(
                    "warmup_beta_ladder and parallel_tempering_betas are separate schedule modes; "
                    "set only one of them"
                )
            raw_ladder = tuple(self.parallel_tempering_betas)
            if any(isinstance(value, bool) for value in raw_ladder):
                raise ValueError("parallel_tempering_betas entries must be finite positive numbers")
            ladder = tuple(finite_float(value, name="parallel_tempering_betas entry") for value in raw_ladder)
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
        """Return ``(beta, sweeps)`` warmup segments, remainder on the last."""
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
    """Drop the empty coupling factor: ``IsingEBM.factors`` indexes ``edges[0]``
    and fails for edgeless (h-only) models."""
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
        self.variables = model.variables
        self.nodes = [thrml.SpinNode() for _ in model.variables]
        node_of = dict(zip(model.variables, self.nodes))
        position_of = {variable: index for index, variable in enumerate(model.variables)}
        self.edges = [(node_of[left], node_of[right]) for left, right in model.quadratic]
        self.edge_positions = tuple(
            (position_of[left], position_of[right]) for left, right in model.quadratic
        )
        # THRML sign mapping (see module docstring): biases = -h, weights = -J.
        self.bias_values = tuple(-model.linear[variable] for variable in model.variables)
        self.weight_values = tuple(-coefficient for coefficient in model.quadratic.values())
        self.biases = jnp.asarray(self.bias_values)
        self.weights = jnp.asarray(self.weight_values)
        self._validate_backend_values(self.bias_values, self.biases, name="linear biases")
        self._validate_backend_values(self.weight_values, self.weights, name="quadratic weights")
        self.lowered_coefficient_dtype = str(self.biases.dtype)
        self.lowered_beta_dtype = self.lowered_coefficient_dtype
        self.max_local_logit_error_bound = 0.0
        self.lowered_targets: dict[float, dict[str, Any]] = {}
        self.free_blocks = [
            thrml.Block([node_of[variable] for variable in block]) for block in partition.blocks
        ]
        self.block_positions = tuple(
            tuple(position_of[variable] for variable in block) for block in partition.blocks
        )
        self.observed_blocks = [thrml.Block(self.nodes)]

    def _validate_backend_values(
        self,
        source_values: Sequence[float],
        backend_values: Any,
        *,
        name: str,
        require_nonzero: Sequence[bool] | None = None,
    ) -> None:
        """Reject finite host values the active JAX dtype cannot represent."""
        host_values = self._jax.device_get(backend_values).reshape(-1).tolist()
        nonzero_flags = (
            [source != 0.0 for source in source_values] if require_nonzero is None else list(require_nonzero)
        )
        for index, (source, backend, must_be_nonzero) in enumerate(
            zip(source_values, host_values, nonzero_flags)
        ):
            backend_float = float(backend)
            if not math.isfinite(source):
                raise ValueError(f"{name}[{index}] overflows in host arithmetic; rescale the model or beta")
            if not math.isfinite(backend_float):
                raise ValueError(
                    f"{name}[{index}]={source!r} becomes non-finite when lowered to "
                    f"JAX dtype {backend_values.dtype}; enable JAX x64 or rescale the model"
                )
            if must_be_nonzero and backend_float == 0.0:
                raise ValueError(
                    f"{name}[{index}]={source!r} becomes zero when lowered to JAX dtype "
                    f"{backend_values.dtype}; enable JAX x64 or rescale the model"
                )
            if source != 0.0 and not math.isclose(
                source,
                backend_float,
                rel_tol=_BACKEND_RELATIVE_ERROR_LIMIT,
                abs_tol=0.0,
            ):
                relative_error = abs((backend_float - source) / source)
                raise ValueError(
                    f"{name}[{index}]={source!r} changes by relative error "
                    f"{relative_error:.3g} when lowered to JAX dtype {backend_values.dtype}; "
                    "enable JAX x64 or rescale the model"
                )

    def _validate_local_logit_error(
        self,
        source_biases: Sequence[float],
        source_weights: Sequence[float],
        backend_biases: Any,
        backend_weights: Any,
    ) -> None:
        """Bound float32-lowering error per conditional logit (coefficient delta
        plus accumulation cancellation); catches cases that shift the
        conditional distribution beyond ``_LOCAL_LOGIT_ERROR_LIMIT``."""
        lowered_biases = [float(value) for value in self._jax.device_get(backend_biases).tolist()]
        lowered_weights = [float(value) for value in self._jax.device_get(backend_weights).tolist()]
        coefficient_error_bounds = [
            abs(source - lowered) for source, lowered in zip(source_biases, lowered_biases)
        ]
        absolute_term_sums = [abs(value) for value in lowered_biases]
        degrees = [0] * len(lowered_biases)
        for (left, right), source, lowered in zip(
            self.edge_positions,
            source_weights,
            lowered_weights,
        ):
            error = abs(source - lowered)
            coefficient_error_bounds[left] += error
            coefficient_error_bounds[right] += error
            absolute_term_sums[left] += abs(lowered)
            absolute_term_sums[right] += abs(lowered)
            degrees[left] += 1
            degrees[right] += 1

        # Standard summation error bound gamma_k=k*u/(1-k*u) for THRML's
        # jnp.sum reduction (k additions); covers accumulator cancellation
        # even for exactly representable coefficients.
        unit_roundoff = float(self._jnp.finfo(backend_biases.dtype).eps) / 2.0
        field_error_bounds: list[float] = []
        for coefficient_error, absolute_sum, degree in zip(
            coefficient_error_bounds,
            absolute_term_sums,
            degrees,
        ):
            denominator = 1.0 - degree * unit_roundoff
            accumulation_error = (
                math.inf if denominator <= 0.0 else (degree * unit_roundoff / denominator) * absolute_sum
            )
            field_error_bounds.append(coefficient_error + accumulation_error)
        logit_error_bound = 2.0 * max(field_error_bounds, default=0.0)
        self.max_local_logit_error_bound = max(
            self.max_local_logit_error_bound,
            logit_error_bound,
        )
        if logit_error_bound > _LOCAL_LOGIT_ERROR_LIMIT:
            raise ValueError(
                "JAX lowering can change a local Gibbs logit by up to "
                f"{logit_error_bound:.6g}, exceeding the audited limit "
                f"{_LOCAL_LOGIT_ERROR_LIMIT:.6g}; enable JAX x64 or rescale the model"
            )

    def program(self, beta: float) -> tuple[Any, Any]:
        """Build the ``(ebm, program)`` pair for one inverse temperature."""
        beta_array = self._jnp.asarray(beta, dtype=self.biases.dtype)
        self._validate_backend_values([beta], beta_array.reshape((1,)), name="beta")
        effective_biases = beta_array * self.biases
        effective_weights = beta_array * self.weights
        source_effective_biases = [beta * value for value in self.bias_values]
        source_effective_weights = [beta * value for value in self.weight_values]
        self._validate_backend_values(
            source_effective_biases,
            effective_biases,
            name="beta-scaled linear biases",
            require_nonzero=[value != 0.0 for value in self.bias_values],
        )
        self._validate_backend_values(
            source_effective_weights,
            effective_weights,
            name="beta-scaled quadratic weights",
            require_nonzero=[value != 0.0 for value in self.weight_values],
        )
        self._validate_local_logit_error(
            source_effective_biases,
            source_effective_weights,
            effective_biases,
            effective_weights,
        )
        lowered_beta = float(self._jax.device_get(beta_array))
        lowered_biases = tuple(float(value) for value in self._jax.device_get(effective_biases).tolist())
        lowered_weights = tuple(float(value) for value in self._jax.device_get(effective_weights).tolist())
        self.lowered_targets[beta] = {
            "requested_beta": beta,
            "lowered_beta": lowered_beta,
            "effective_biases": lowered_biases,
            "effective_weights": lowered_weights,
        }
        self.lowered_beta_dtype = str(beta_array.dtype)
        ebm_class = self._thrml_models.IsingEBM if self.edges else _edgeless_ising_ebm_class()
        ebm = ebm_class(self.nodes, self.edges, self.biases, self.weights, beta_array)
        return ebm, self._thrml_models.IsingSamplingProgram(ebm, self.free_blocks, clamped_blocks=[])

    def lowered_log_density(self, beta: float, sample: Mapping[Variable, int]) -> float:
        """Evaluate the ideal log density represented by one lowered beta slot."""
        target = self.lowered_targets[beta]
        spins = tuple(int(sample[variable]) for variable in self.variables)
        terms = [coefficient * spins[index] for index, coefficient in enumerate(target["effective_biases"])]
        terms.extend(
            coefficient * spins[left] * spins[right]
            for (left, right), coefficient in zip(
                self.edge_positions,
                target["effective_weights"],
            )
        )
        return finite_float(math.fsum(terms), name="lowered target log density")

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


def _reads_by_chain(num_reads: int, num_chains: int) -> tuple[int, ...]:
    """Distribute reads with chain lengths differing by at most one."""
    base, remainder = divmod(num_reads, num_chains)
    return tuple(base + (chain_index < remainder) for chain_index in range(num_chains))


def _local_sweep_accounting(
    config: SamplerConfig,
    *,
    mode: str,
    reads_by_chain: Sequence[int],
    backend_generated_reads_by_chain: Sequence[int],
    beta_count: int,
) -> dict[str, Any]:
    """Describe executed local work without equating requested and backend reads.

    A sweep is one complete ordered pass over all free blocks for one chain and
    one beta replica. Fixed-beta vectorization can generate a final discarded
    draw for shorter active chains; parallel tempering does not.
    """
    if len(reads_by_chain) != len(backend_generated_reads_by_chain):
        raise ValueError("read allocations and backend read counts must have equal length")
    if beta_count < 1:
        raise ValueError(f"beta_count must be >= 1, got {beta_count!r}")
    if mode not in {"fixed_beta", "parallel_tempering", "constant_model_shortcut"}:
        raise ValueError(f"unsupported sweep-accounting mode {mode!r}")

    shortcut = mode == "constant_model_shortcut"
    active = [generated > 0 for generated in backend_generated_reads_by_chain]
    warmup_by_chain = [
        0 if shortcut or not is_active else config.n_warmup * beta_count for is_active in active
    ]
    retained_target_by_chain = [
        0 if shortcut else int(reads) * config.steps_per_sample for reads in reads_by_chain
    ]
    executed_target_by_chain = [
        0 if shortcut else int(generated) * config.steps_per_sample
        for generated in backend_generated_reads_by_chain
    ]
    executed_auxiliary_by_chain = [
        0 if shortcut else target * (beta_count - 1) for target in executed_target_by_chain
    ]
    executed_sampling_by_chain = [
        target + auxiliary for target, auxiliary in zip(executed_target_by_chain, executed_auxiliary_by_chain)
    ]
    discarded_target_by_chain = [
        executed - retained for executed, retained in zip(executed_target_by_chain, retained_target_by_chain)
    ]
    total_by_chain = [
        warmup + sampling for warmup, sampling in zip(warmup_by_chain, executed_sampling_by_chain)
    ]

    return {
        "mode": mode,
        "unit": "one complete ordered pass over all free blocks for one chain and one beta replica",
        "configured_chains": len(reads_by_chain),
        "active_chains": sum(active),
        "beta_count": beta_count,
        "first_retained_read_target_sweeps": 0 if shortcut else config.steps_per_sample,
        "retained_reads_by_chain": [int(value) for value in reads_by_chain],
        "backend_generated_reads_by_chain": [int(value) for value in backend_generated_reads_by_chain],
        "executed_warmup_sweeps_by_chain": warmup_by_chain,
        "retained_target_beta_sweeps_by_chain": retained_target_by_chain,
        "executed_target_beta_sweeps_by_chain": executed_target_by_chain,
        "discarded_target_beta_sweeps_by_chain": discarded_target_by_chain,
        "executed_auxiliary_beta_sweeps_by_chain": executed_auxiliary_by_chain,
        "executed_sampling_sweeps_by_chain": executed_sampling_by_chain,
        "executed_total_sweeps_by_chain": total_by_chain,
        "retained_target_beta_sweeps": sum(retained_target_by_chain),
        "executed_target_beta_sweeps": sum(executed_target_by_chain),
        "discarded_target_beta_sweeps": sum(discarded_target_by_chain),
        "executed_auxiliary_beta_sweeps": sum(executed_auxiliary_by_chain),
        "executed_sampling_sweeps": sum(executed_sampling_by_chain),
        "executed_warmup_sweeps": sum(warmup_by_chain),
        "executed_total_sweeps": sum(total_by_chain),
    }


def _decode_sample_chains(
    spins: Any,
    model: IsingModel,
    *,
    reads_by_chain: Sequence[int],
) -> _DecodedChains:
    """Convert THRML spin arrays into Gibbsiq samples and aligned traces."""
    samples: list[dict[Variable, int]] = []
    chain_ids: list[int] = []
    energy_trace: list[list[float]] = []
    best_trace: list[list[float]] = []
    sample_chains: list[list[dict[Variable, int]]] = []
    for chain_index, chain_reads in enumerate(reads_by_chain):
        chain_energies: list[float] = []
        chain_best: list[float] = []
        chain_samples: list[dict[Variable, int]] = []
        if chain_reads <= 0:
            energy_trace.append(chain_energies)
            best_trace.append(chain_best)
            sample_chains.append(chain_samples)
            continue
        best_interaction: float | None = None
        best_total: float | None = None
        for row in spins[chain_index][:chain_reads]:
            sample = {variable: int(value) for variable, value in zip(model.variables, row)}
            energy = model.energy(sample)
            interaction = model.interaction_energy(sample)
            samples.append(sample)
            chain_ids.append(chain_index)
            chain_energies.append(energy)
            if best_interaction is None or interaction < best_interaction:
                best_interaction = interaction
                best_total = energy
            assert best_total is not None
            chain_best.append(best_total)
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
    if sweeps < 1:
        raise ValueError(f"sweeps must be >= 1, got {sweeps!r}")
    # THRML 0.1.3 records the post-warmup state directly when n_samples=1;
    # there is no additional steps_per_sample update in that case.
    schedule = thrml.SamplingSchedule(n_warmup=sweeps, n_samples=1, steps_per_sample=1)
    observed = thrml.sample_states(key, program, schedule, state, [], free_blocks)
    return [block_states[-1] for block_states in observed]


def _pair_key(left_index: int, right_index: int) -> str:
    return f"{left_index}-{right_index}"


def _replica_exchange_log_ratio(
    beta_left: float,
    beta_right: float,
    energy_left: float,
    energy_right: float,
) -> float:
    """Return ``log(target_after / target_before)`` for a replica swap."""
    return finite_float(
        (beta_left - beta_right) * (energy_left - energy_right),
        name="replica-exchange log ratio",
    )


def _replica_exchange_accepts(log_acceptance: float, uniform: float) -> bool:
    """Apply the log-domain Metropolis test, including ``random() == 0``."""
    return log_acceptance >= 0.0 or uniform == 0.0 or math.log(uniform) < log_acceptance


def _replica_exchange_pairs(replica_count: int, swap_round: int) -> tuple[tuple[int, int], ...]:
    """Return the non-overlapping adjacent pairs for one exchange round."""
    parity = 0 if replica_count == 2 else swap_round % 2
    return tuple((left, left + 1) for left in range(parity, replica_count - 1, 2))


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

    state_samples = [lowering.sample_from_state(state, model.variables) for state in states]
    energies = [model.energy(sample) for sample in state_samples]
    interaction_energies = [model.interaction_energy(sample) for sample in state_samples]
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
    best_interaction: float | None = None
    best_total: float | None = None
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
            state_sample = lowering.sample_from_state(states[beta_index], model.variables)
            state_samples[beta_index] = state_sample
            energies[beta_index] = model.energy(state_sample)
            interaction_energies[beta_index] = model.interaction_energy(state_sample)

        if (read_index + 1) % config.parallel_tempering_swap_interval == 0:
            exchange_pairs = _replica_exchange_pairs(len(programs), swap_round)
            swap_round += 1
            for left_index, right_index in exchange_pairs:
                beta_left = beta_ladder[left_index]
                beta_right = beta_ladder[right_index]
                energy_left = energies[left_index]
                energy_right = energies[right_index]
                interaction_energy_left = interaction_energies[left_index]
                interaction_energy_right = interaction_energies[right_index]
                sample_left = state_samples[left_index]
                sample_right = state_samples[right_index]
                left_log_density_left = lowering.lowered_log_density(beta_left, sample_left)
                left_log_density_right = lowering.lowered_log_density(beta_left, sample_right)
                right_log_density_left = lowering.lowered_log_density(beta_right, sample_left)
                right_log_density_right = lowering.lowered_log_density(beta_right, sample_right)
                log_acceptance = finite_float(
                    math.fsum(
                        (
                            left_log_density_right,
                            right_log_density_left,
                            -left_log_density_left,
                            -right_log_density_right,
                        )
                    ),
                    name="lowered replica-exchange log ratio",
                )
                uniform = swap_rng.random()
                accepted = _replica_exchange_accepts(log_acceptance, uniform)
                pair = _pair_key(left_index, right_index)
                swap_attempts += 1
                swap_attempts_by_pair[pair] = swap_attempts_by_pair.get(pair, 0) + 1
                if accepted:
                    swap_accepts += 1
                    swap_accepts_by_pair[pair] = swap_accepts_by_pair.get(pair, 0) + 1
                    states[left_index], states[right_index] = states[right_index], states[left_index]
                    state_samples[left_index], state_samples[right_index] = (
                        state_samples[right_index],
                        state_samples[left_index],
                    )
                    energies[left_index], energies[right_index] = energies[right_index], energies[left_index]
                    interaction_energies[left_index], interaction_energies[right_index] = (
                        interaction_energies[right_index],
                        interaction_energies[left_index],
                    )
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
                        "left_interaction_energy_before": interaction_energy_left,
                        "right_interaction_energy_before": interaction_energy_right,
                        "left_sample_before": dict(sample_left),
                        "right_sample_before": dict(sample_right),
                        "left_log_density_left_target": left_log_density_left,
                        "right_log_density_left_target": left_log_density_right,
                        "left_log_density_right_target": right_log_density_left,
                        "right_log_density_right_target": right_log_density_right,
                        "acceptance_target": "lowered_backend_coefficients",
                        "log_acceptance": log_acceptance,
                        "uniform": uniform,
                        "accepted": accepted,
                    }
                )

        for beta_index, energy in enumerate(energies):
            per_beta_energy[beta_index].append(energy)
        cold_sample = lowering.sample_from_state(states[-1], model.variables)
        cold_energy = energies[-1]
        cold_interaction = interaction_energies[-1]
        samples.append(cold_sample)
        energy_trace.append(cold_energy)
        if best_interaction is None or cold_interaction < best_interaction:
            best_interaction = cold_interaction
            best_total = cold_energy
        assert best_total is not None
        best_trace.append(best_total)

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
    lowering: _Lowering | None,
    *,
    num_reads: int,
    reads_per_chain: int,
    reads_by_chain: Sequence[int],
    lower_seconds: float,
    sample_seconds: float,
) -> dict[str, Any]:
    """Assemble runtime provenance for a ``SampleResult``."""
    if lowering is None:
        lowered_coefficient_dtype = None
        lowered_beta_dtype = None
        max_local_logit_error_bound = 0.0
        lowered_targets: list[dict[str, Any]] = []
        sampling_target_semantics = "constant Hamiltonian sampled exactly without lowering a THRML program"
    else:
        lowered_coefficient_dtype = lowering.lowered_coefficient_dtype
        lowered_beta_dtype = lowering.lowered_beta_dtype
        max_local_logit_error_bound = lowering.max_local_logit_error_bound
        lowered_targets = [
            {
                "requested_beta": target["requested_beta"],
                "lowered_beta": target["lowered_beta"],
                "effective_biases": list(target["effective_biases"]),
                "effective_weights": list(target["effective_weights"]),
            }
            for target in lowering.lowered_targets.values()
        ]
        sampling_target_semantics = (
            "THRML backend-coefficient approximation to the canonical Ising target; "
            "local conditional-logit error is bounded by local_logit_error_limit"
        )
    metadata = {
        "sampler": "gibbsiq.THRMLSampler",
        "execution_backend": (
            "deterministic constant-model shortcut" if lowering is None else "THRML JAX simulator"
        ),
        "constant_model_shortcut": lowering is None,
        "thrml_version": getattr(thrml, "__version__", "unknown"),
        "jax_version": jax.__version__,
        "jax_enable_x64": bool(jax.config.read("jax_enable_x64")),
        "jax_default_prng_impl": str(jax.config.jax_default_prng_impl),
        "lowered_coefficient_dtype": lowered_coefficient_dtype,
        "lowered_beta_dtype": lowered_beta_dtype,
        "max_local_logit_error_bound": max_local_logit_error_bound,
        "local_logit_error_limit": _LOCAL_LOGIT_ERROR_LIMIT,
        "lowered_edge_order": [[left, right] for left, right in model.quadratic],
        "lowered_targets": lowered_targets,
        "sampling_target_semantics": sampling_target_semantics,
        "device_platform": device.platform,
        "device_kind": device.device_kind,
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "operating_system": platform.platform(),
        "local_transition_rng": (
            "not_used_constant_model" if lowering is None else "jax.random key splitting"
        ),
        "python_executable": sys.executable,
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
        "reads_by_chain": list(reads_by_chain),
        "init": config.init,
        "graph_density": graph_density(model),
        "energy_convention": "E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j",
        "best_sample_selection_basis": "offset-free Ising interaction energy",
        "diagnostic_energy_basis": "offset-free Ising interaction energy",
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

    def _sample_constant_model(
        self,
        model: IsingModel,
        *,
        num_reads: int,
        partition: BlockPartition,
        lower_started: float,
    ) -> SampleResult:
        """Return the unique empty assignment for an offset-only model; no THRML
        graph to run. Magnetization is marked not-applicable, not fabricated."""
        jax, _, thrml, _ = _require_thrml()
        config = self.config
        reads_by_chain = _reads_by_chain(num_reads, config.num_chains)
        reads_per_chain = max(reads_by_chain)
        sweep_accounting = _local_sweep_accounting(
            config,
            mode="constant_model_shortcut",
            reads_by_chain=reads_by_chain,
            backend_generated_reads_by_chain=(0,) * config.num_chains,
            beta_count=(
                1 if config.parallel_tempering_betas is None else len(config.parallel_tempering_betas)
            ),
        )
        lower_seconds = time.perf_counter() - lower_started

        sample_started = time.perf_counter()
        sample_chains: list[list[dict[Variable, int]]] = [
            [{} for _ in range(chain_reads)] for chain_reads in reads_by_chain
        ]
        samples = [sample for chain in sample_chains for sample in chain]
        sample_chain_ids = [
            chain_index for chain_index, chain_reads in enumerate(reads_by_chain) for _ in range(chain_reads)
        ]
        total_energy_chains = [[model.offset for _ in range(chain_reads)] for chain_reads in reads_by_chain]
        interaction_energy_chains = [[0.0 for _ in range(chain_reads)] for chain_reads in reads_by_chain]
        sample_seconds = time.perf_counter() - sample_started

        diagnostics_started = time.perf_counter()
        if config.parallel_tempering_betas is None:
            segments = config.warmup_segments()
            beta_schedule = [
                {"phase": "warmup", "beta": beta, "sweeps": sweeps} for beta, sweeps in segments
            ] or [{"phase": "warmup", "beta": config.beta, "sweeps": config.n_warmup}]
            beta_schedule.append(
                {
                    "phase": "sampling",
                    "beta": config.beta,
                    "n_samples": reads_per_chain,
                    "reads_by_chain": list(reads_by_chain),
                    "backend_generated_reads_by_chain": [0] * config.num_chains,
                    "pre_first_sample_sweeps": 0,
                    "steps_per_sample": config.steps_per_sample,
                }
            )
        else:
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
                    "reads_by_chain": list(reads_by_chain),
                    "backend_generated_reads_by_chain": [0] * config.num_chains,
                    "pre_first_sample_sweeps": 0,
                    "steps_per_sample": config.steps_per_sample,
                    "swap_interval": config.parallel_tempering_swap_interval,
                },
            ]

        traces: dict[str, Any] = {
            "energy": total_energy_chains,
            "interaction_energy": interaction_energy_chains,
            "best_energy_so_far": total_energy_chains,
            "sample_chain_ids": sample_chain_ids,
            "beta_schedule": beta_schedule,
            "local_sweep_accounting": sweep_accounting,
            "magnetization": None,
            "distance_to_best": [[0 for _ in chain] for chain in sample_chains],
        }
        if config.parallel_tempering_betas is not None:
            traces["parallel_tempering"] = {
                "beta_ladder": list(config.parallel_tempering_betas),
                "target_beta_index": len(config.parallel_tempering_betas) - 1,
                "per_beta_energy": [
                    [list(chain) for _ in config.parallel_tempering_betas] for chain in total_energy_chains
                ],
                "swap_trace": [],
                "swap_attempts": 0,
                "swap_accepts": 0,
                "swap_acceptance_rate": None,
                "swap_attempts_by_pair": {},
                "swap_accepts_by_pair": {},
                "status": "not_applicable_constant_model",
            }

        device = jax.devices()[0]
        metadata = _build_metadata(
            config,
            model,
            partition,
            thrml,
            jax,
            device,
            None,
            num_reads=num_reads,
            reads_per_chain=reads_per_chain,
            reads_by_chain=reads_by_chain,
            lower_seconds=lower_seconds,
            sample_seconds=sample_seconds,
        )
        metadata["local_sweep_accounting"] = sweep_accounting
        if config.parallel_tempering_betas is not None:
            metadata.update(
                {
                    "parallel_tempering_swap_attempts": 0,
                    "parallel_tempering_swap_accepts": 0,
                    "parallel_tempering_swap_acceptance_rate": None,
                    "parallel_tempering_swap_rng": "not_used_constant_model",
                    "parallel_tempering_swap_target": "not_applicable_constant_model",
                }
            )

        diagnostics = compute_diagnostics(
            energy_chains=interaction_energy_chains,
            samples=samples,
            variables=model.variables,
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
            model,
            samples,
            traces=traces,
            diagnostics=diagnostics,
            metadata=metadata,
        )

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
        reads_by_chain = _reads_by_chain(num_reads, config.num_chains)
        reads_per_chain = max(reads_by_chain)
        sweep_accounting = _local_sweep_accounting(
            config,
            mode="parallel_tempering",
            reads_by_chain=reads_by_chain,
            backend_generated_reads_by_chain=reads_by_chain,
            beta_count=len(programs),
        )
        lower_seconds = time.perf_counter() - lower_started

        sample_started = time.perf_counter()
        root_key = jax.random.key(config.seed)
        chain_keys = jax.random.split(root_key, config.num_chains)
        chains: list[_TemperingChain] = []
        for chain_index, chain_reads in enumerate(reads_by_chain):
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
        interaction_energy_chains = [
            [model.interaction_energy(sample) for sample in chain] for chain in decoded.sample_chains
        ]
        flat_interaction_energies = [energy for chain in interaction_energy_chains for energy in chain]
        best_sample = decoded.samples[best_index(flat_interaction_energies)]
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
                "reads_by_chain": list(reads_by_chain),
                "backend_generated_reads_by_chain": list(reads_by_chain),
                "pre_first_sample_sweeps": config.steps_per_sample,
                "steps_per_sample": config.steps_per_sample,
                "swap_interval": config.parallel_tempering_swap_interval,
            },
        ]
        magnetization_chains = magnetization_trace(decoded.sample_chains, model.variables)
        distance_chains = distance_to_best_trace(decoded.sample_chains, best_sample, model.variables)
        traces: dict[str, Any] = {
            "energy": decoded.energy_trace,
            "interaction_energy": interaction_energy_chains,
            "best_energy_so_far": decoded.best_trace,
            "sample_chain_ids": decoded.chain_ids,
            "beta_schedule": beta_schedule,
            "local_sweep_accounting": sweep_accounting,
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
            lowering,
            num_reads=num_reads,
            reads_per_chain=reads_per_chain,
            reads_by_chain=reads_by_chain,
            lower_seconds=lower_seconds,
            sample_seconds=sample_seconds,
        )
        metadata["local_sweep_accounting"] = sweep_accounting
        metadata.update(
            {
                "parallel_tempering_swap_attempts": decoded.swap_attempts,
                "parallel_tempering_swap_accepts": decoded.swap_accepts,
                "parallel_tempering_swap_acceptance_rate": (
                    decoded.swap_accepts / decoded.swap_attempts if decoded.swap_attempts else None
                ),
                "parallel_tempering_swap_rng": "python.random.Random(seed='seed:pt:chain_id')",
                "parallel_tempering_swap_target": "recorded lowered per-beta log densities",
            }
        )

        diagnostics = compute_diagnostics(
            energy_chains=interaction_energy_chains,
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
        """Run block Gibbs on ``model``, return exactly ``num_reads`` samples.

        Reads balanced via ``divmod`` (earlier chains get the extra read);
        per-chain traces sliced to allocation so flat ``energies`` equals
        concatenated ``traces["energy"]``.
        """
        if isinstance(num_reads, bool) or not isinstance(num_reads, int) or num_reads < 1:
            raise ValueError(f"num_reads must be an integer >= 1, got {num_reads!r}")
        jax, jnp, thrml, _ = _require_thrml()
        config = self.config

        lower_started = time.perf_counter()
        if partition is None:
            partition = color_blocks(model)
        validate_partition(model, partition)
        if not model.variables:
            return self._sample_constant_model(
                model,
                num_reads=num_reads,
                partition=partition,
                lower_started=lower_started,
            )
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
        # Chain inits at the first warmup beta (or sampling beta if no ladder).
        init_ebm = sampling_ebm
        segment_programs: list[tuple[Any, int]] = []
        for beta, sweeps in segments:
            ebm, program = lowering.program(beta)
            if not segment_programs:
                init_ebm = ebm
            segment_programs.append((program, sweeps))
        reads_by_chain = _reads_by_chain(num_reads, config.num_chains)
        reads_per_chain = max(reads_by_chain)
        active_chain_count = sum(chain_reads > 0 for chain_reads in reads_by_chain)
        backend_generated_reads_by_chain = tuple(
            reads_per_chain if chain_index < active_chain_count else 0
            for chain_index in range(config.num_chains)
        )
        sweep_accounting = _local_sweep_accounting(
            config,
            mode="fixed_beta",
            reads_by_chain=reads_by_chain,
            backend_generated_reads_by_chain=backend_generated_reads_by_chain,
            beta_count=1,
        )
        final_warmup = 0 if segments else config.n_warmup
        sampling_schedule = thrml.SamplingSchedule(
            # THRML 0.1.3 observes the post-warmup state as sample zero. Advance
            # at the target beta here so that sample zero obeys the same
            # steps-per-sample contract as every later retained sample.
            n_warmup=final_warmup + config.steps_per_sample,
            n_samples=reads_per_chain,
            steps_per_sample=config.steps_per_sample,
        )
        lower_seconds = time.perf_counter() - lower_started

        def run_chain(chain_key: Any) -> Any:
            keys = jax.random.split(chain_key, len(segment_programs) + 2)
            state = lowering.initial_state(keys[0], init_ebm, config.init)
            for (program, sweeps), segment_key in zip(segment_programs, keys[1:-1]):
                state = _advance_block_state(
                    thrml=thrml,
                    key=segment_key,
                    program=program,
                    state=state,
                    free_blocks=lowering.free_blocks,
                    sweeps=sweeps,
                )
            return thrml.sample_states(
                keys[-1], sampling_program, sampling_schedule, state, [], lowering.observed_blocks
            )[0]

        sample_started = time.perf_counter()
        root_key = jax.random.key(config.seed)
        chain_keys = jax.random.split(root_key, config.num_chains)[:active_chain_count]
        if active_chain_count == 1:
            stacked = run_chain(chain_keys[0])[None, ...]
        else:
            stacked = jax.vmap(run_chain)(chain_keys)
        spins = jax.device_get(jnp.where(stacked, 1, -1))
        sample_seconds = time.perf_counter() - sample_started

        decoded = _decode_sample_chains(
            spins,
            model,
            reads_by_chain=reads_by_chain,
        )

        # Trace post-processing and diagnostics share one timing bucket
        # (EVAL-EQ-010 resource split): everything after decode is telemetry.
        diagnostics_started = time.perf_counter()
        interaction_energy_chains = [
            [model.interaction_energy(sample) for sample in chain] for chain in decoded.sample_chains
        ]
        flat_interaction_energies = [energy for chain in interaction_energy_chains for energy in chain]
        best_sample = decoded.samples[best_index(flat_interaction_energies)]

        beta_schedule = [
            {"phase": "warmup", "beta": beta, "sweeps": sweeps} for beta, sweeps in segments
        ] or [{"phase": "warmup", "beta": config.beta, "sweeps": config.n_warmup}]
        beta_schedule.append(
            {
                "phase": "sampling",
                "beta": config.beta,
                "n_samples": reads_per_chain,
                "reads_by_chain": list(reads_by_chain),
                "backend_generated_reads_by_chain": list(backend_generated_reads_by_chain),
                "pre_first_sample_sweeps": config.steps_per_sample,
                "steps_per_sample": config.steps_per_sample,
            }
        )
        magnetization_chains = magnetization_trace(decoded.sample_chains, model.variables)
        distance_chains = distance_to_best_trace(decoded.sample_chains, best_sample, model.variables)
        traces: dict[str, Any] = {
            "energy": decoded.energy_trace,
            "interaction_energy": interaction_energy_chains,
            "best_energy_so_far": decoded.best_trace,
            "sample_chain_ids": decoded.chain_ids,
            "beta_schedule": beta_schedule,
            "local_sweep_accounting": sweep_accounting,
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
            lowering,
            num_reads=num_reads,
            reads_per_chain=reads_per_chain,
            reads_by_chain=reads_by_chain,
            lower_seconds=lower_seconds,
            sample_seconds=sample_seconds,
        )
        metadata["local_sweep_accounting"] = sweep_accounting

        diagnostics = compute_diagnostics(
            energy_chains=interaction_energy_chains,
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
