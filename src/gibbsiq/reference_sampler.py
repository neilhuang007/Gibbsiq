"""Small, auditable CPU Gibbs reference independent of the THRML runtime.

This module is intentionally direct.  It recomputes every local conditional
from the canonical Ising coefficients and records every random draw and state
transition.  It is a correctness oracle for small tests, not a fast solver.
"""

from __future__ import annotations

import hashlib
import math
import platform
import random
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from gibbsiq._frozen import freeze, thaw
from gibbsiq.blocks import BlockPartition, color_blocks, validate_partition
from gibbsiq.model import IsingModel, Variable, finite_float, finite_sum

UpdateSchedule = Literal["random_single_site", "systematic", "blocked"]
Initialization = Literal["random", "all_up", "all_down"]


def _nonnegative_integer(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be an integer >= 0, got {value!r}")
    return value


def _positive_integer(value: Any, *, name: str) -> int:
    canonical = _nonnegative_integer(value, name=name)
    if canonical == 0:
        raise ValueError(f"{name} must be an integer >= 1, got {value!r}")
    return canonical


@dataclass(frozen=True, slots=True)
class ReferenceSamplerConfig:
    """Controls for the deterministic-replay CPU Gibbs reference."""

    beta: float = 1.0
    n_warmup: int = 0
    steps_per_sample: int = 1
    num_chains: int = 1
    seed: int = 0
    initialization: Initialization = "random"
    update_schedule: UpdateSchedule = "random_single_site"
    blocks: tuple[tuple[Variable, ...], ...] | None = None

    def __post_init__(self) -> None:
        if isinstance(self.beta, bool):
            raise ValueError(f"beta must be a finite non-negative number, got {self.beta!r}")
        beta = finite_float(self.beta, name="beta")
        if beta < 0.0:
            raise ValueError(f"beta must be non-negative, got {self.beta!r}")
        object.__setattr__(self, "beta", beta)
        object.__setattr__(
            self,
            "n_warmup",
            _nonnegative_integer(self.n_warmup, name="n_warmup"),
        )
        object.__setattr__(
            self,
            "steps_per_sample",
            _positive_integer(self.steps_per_sample, name="steps_per_sample"),
        )
        object.__setattr__(
            self,
            "num_chains",
            _positive_integer(self.num_chains, name="num_chains"),
        )
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError(f"seed must be an integer, got {self.seed!r}")
        if self.initialization not in {"random", "all_up", "all_down"}:
            raise ValueError(f"unsupported initialization {self.initialization!r}")
        if self.update_schedule not in {
            "random_single_site",
            "systematic",
            "blocked",
        }:
            raise ValueError(f"unsupported update_schedule {self.update_schedule!r}")
        if self.blocks is not None:
            try:
                normalized = tuple(tuple(block) for block in self.blocks)
            except TypeError as error:
                raise TypeError("blocks must be an iterable of variable iterables") from error
            object.__setattr__(self, "blocks", normalized)


@dataclass(frozen=True, slots=True)
class ReferenceTransitionEvent:
    """One recorded single-site conditional evaluation and random draw."""

    chain_id: int
    stage: Literal["warmup", "sample"]
    step_index: int
    retained_index: int | None
    phase_index: int | None
    variable: Variable
    state_before: tuple[int, ...]
    conditioned_state: tuple[int, ...]
    probability_up: float
    uniform: float
    state_after: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "stage": self.stage,
            "step_index": self.step_index,
            "retained_index": self.retained_index,
            "phase_index": self.phase_index,
            "variable": self.variable,
            "state_before": list(self.state_before),
            "conditioned_state": list(self.conditioned_state),
            "probability_up": self.probability_up,
            "uniform": self.uniform,
            "state_after": list(self.state_after),
        }


@dataclass(frozen=True, slots=True)
class ReferenceSampleResult:
    """Retained samples plus the complete replay evidence."""

    variables: tuple[Variable, ...]
    samples: tuple[tuple[int, ...], ...]
    energies: tuple[float, ...]
    interaction_energies: tuple[float, ...]
    chain_ids: tuple[int, ...]
    initial_states: tuple[tuple[int, ...], ...]
    state_traces: tuple[tuple[tuple[int, ...], ...], ...]
    transitions: tuple[ReferenceTransitionEvent, ...]
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", freeze(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "variables": list(self.variables),
            "samples": [list(sample) for sample in self.samples],
            "energies": list(self.energies),
            "interaction_energies": list(self.interaction_energies),
            "chain_ids": list(self.chain_ids),
            "initial_states": [list(state) for state in self.initial_states],
            "state_traces": [[list(state) for state in chain_trace] for chain_trace in self.state_traces],
            "transitions": [event.to_dict() for event in self.transitions],
            "metadata": thaw(self.metadata),
        }


def _stable_probability_up(beta: float, gamma: float) -> float:
    if beta == 0.0:
        return 0.5
    argument = -2.0 * beta * gamma
    if argument == math.inf:
        return 1.0
    if argument == -math.inf:
        return 0.0
    if argument >= 0.0:
        return 1.0 / (1.0 + math.exp(-argument))
    exponential = math.exp(argument)
    return exponential / (1.0 + exponential)


def _probability_up(
    model: IsingModel,
    variable_position: int,
    state: tuple[int, ...],
    beta: float,
) -> float:
    """Direct conditional implementation; does not call model runtime helpers."""
    variable = model.variables[variable_position]
    position = {label: index for index, label in enumerate(model.variables)}
    terms = [model.linear[variable]]
    for (left, right), coefficient in model.quadratic.items():
        if left == variable:
            terms.append(coefficient * state[position[right]])
        elif right == variable:
            terms.append(coefficient * state[position[left]])
    gamma = finite_sum(terms, name=f"reference local field for {variable!r}")
    return _stable_probability_up(beta, gamma)


def _chain_seed(seed: int, chain_id: int) -> int:
    material = f"gibbsiq-reference-v1:{seed}:{chain_id}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _read_allocation(num_reads: int, num_chains: int) -> tuple[int, ...]:
    base, remainder = divmod(num_reads, num_chains)
    return tuple(base + (chain_id < remainder) for chain_id in range(num_chains))


class ReferenceGibbsSampler:
    """Seeded, trace-complete Gibbs reference for small Ising models."""

    def __init__(self, config: ReferenceSamplerConfig | None = None) -> None:
        self.config = ReferenceSamplerConfig() if config is None else config
        if not isinstance(self.config, ReferenceSamplerConfig):
            raise TypeError("config must be ReferenceSamplerConfig")

    def sample(self, model: IsingModel, *, num_reads: int) -> ReferenceSampleResult:
        if not isinstance(model, IsingModel):
            raise TypeError(f"model must be IsingModel, got {type(model).__name__}")
        reads = _positive_integer(num_reads, name="num_reads")
        blocks, block_strategy = self._resolve_blocks(model)
        allocation = _read_allocation(reads, self.config.num_chains)

        samples: list[tuple[int, ...]] = []
        energies: list[float] = []
        interaction_energies: list[float] = []
        chain_ids: list[int] = []
        initial_states: list[tuple[int, ...]] = []
        state_traces: list[tuple[tuple[int, ...], ...]] = []
        transitions: list[ReferenceTransitionEvent] = []
        chain_seeds: list[int] = []

        for chain_id, chain_reads in enumerate(allocation):
            if chain_reads == 0:
                continue
            chain_seed = _chain_seed(self.config.seed, chain_id)
            chain_seeds.append(chain_seed)
            rng = random.Random(chain_seed)
            state = self._initial_state(model, rng)
            initial_states.append(state)
            trace = [state]

            for step_index in range(self.config.n_warmup):
                state, events = self._step(
                    model,
                    state,
                    rng,
                    blocks,
                    chain_id=chain_id,
                    stage="warmup",
                    step_index=step_index,
                    retained_index=None,
                )
                transitions.extend(events)
                trace.append(state)

            for retained_index in range(chain_reads):
                for step_index in range(self.config.steps_per_sample):
                    state, events = self._step(
                        model,
                        state,
                        rng,
                        blocks,
                        chain_id=chain_id,
                        stage="sample",
                        step_index=step_index,
                        retained_index=retained_index,
                    )
                    transitions.extend(events)
                    trace.append(state)
                sample = dict(zip(model.variables, state))
                samples.append(state)
                interaction_energies.append(model.interaction_energy(sample))
                energies.append(model.energy(sample))
                chain_ids.append(chain_id)
            state_traces.append(tuple(trace))

        metadata: dict[str, Any] = {
            "beta": self.config.beta,
            "n_warmup": self.config.n_warmup,
            "steps_per_sample": self.config.steps_per_sample,
            "num_chains_requested": self.config.num_chains,
            "num_chains_active": len(initial_states),
            "read_allocation": list(allocation),
            "seed": self.config.seed,
            "chain_seeds": chain_seeds,
            "rng": "random.Random (MT19937)",
            "python_version": platform.python_version(),
            "initialization": self.config.initialization,
            "update_schedule": self.config.update_schedule,
            "blocks": [list(block) for block in blocks],
            "block_strategy": block_strategy,
            "work_unit": "single_site_conditional_evaluation",
            "conditional_evaluations": len(transitions),
            "offset_handling": "retained in total energies; absent from Gibbs conditionals",
        }
        return ReferenceSampleResult(
            variables=model.variables,
            samples=tuple(samples),
            energies=tuple(energies),
            interaction_energies=tuple(interaction_energies),
            chain_ids=tuple(chain_ids),
            initial_states=tuple(initial_states),
            state_traces=tuple(state_traces),
            transitions=tuple(transitions),
            metadata=metadata,
        )

    def _resolve_blocks(
        self,
        model: IsingModel,
    ) -> tuple[tuple[tuple[Variable, ...], ...], str]:
        if self.config.update_schedule != "blocked":
            if self.config.blocks is not None:
                raise ValueError("blocks are only valid with update_schedule='blocked'")
            return (), "not_applicable"
        if self.config.blocks is None:
            partition = color_blocks(model)
            strategy = partition.strategy
        else:
            partition = BlockPartition(self.config.blocks, strategy="user_supplied")
            strategy = partition.strategy
        validate_partition(model, partition)
        return partition.blocks, strategy

    def _initial_state(self, model: IsingModel, rng: random.Random) -> tuple[int, ...]:
        if self.config.initialization == "all_up":
            return (1,) * len(model.variables)
        if self.config.initialization == "all_down":
            return (-1,) * len(model.variables)
        return tuple(1 if rng.random() < 0.5 else -1 for _ in model.variables)

    def _step(
        self,
        model: IsingModel,
        state: tuple[int, ...],
        rng: random.Random,
        blocks: tuple[tuple[Variable, ...], ...],
        *,
        chain_id: int,
        stage: Literal["warmup", "sample"],
        step_index: int,
        retained_index: int | None,
    ) -> tuple[tuple[int, ...], tuple[ReferenceTransitionEvent, ...]]:
        if not model.variables:
            return state, ()
        positions: tuple[tuple[int | None, tuple[int, ...]], ...]
        if self.config.update_schedule == "random_single_site":
            positions = ((None, (rng.randrange(len(model.variables)),)),)
        elif self.config.update_schedule == "systematic":
            positions = tuple((index, (index,)) for index in range(len(model.variables)))
        else:
            variable_positions = {variable: position for position, variable in enumerate(model.variables)}
            positions = tuple(
                (phase_index, tuple(variable_positions[variable] for variable in block))
                for phase_index, block in enumerate(blocks)
            )

        events: list[ReferenceTransitionEvent] = []
        current = state
        for phase_index, phase_positions in positions:
            conditioned = current
            updates: list[tuple[int, float, float, int]] = []
            for variable_position in phase_positions:
                probability_up = _probability_up(
                    model,
                    variable_position,
                    conditioned,
                    self.config.beta,
                )
                uniform = rng.random()
                updates.append(
                    (
                        variable_position,
                        probability_up,
                        uniform,
                        1 if uniform < probability_up else -1,
                    )
                )
            changed = list(current)
            for variable_position, _, _, spin in updates:
                changed[variable_position] = spin
            after = tuple(changed)
            for variable_position, probability_up, uniform, _ in updates:
                events.append(
                    ReferenceTransitionEvent(
                        chain_id=chain_id,
                        stage=stage,
                        step_index=step_index,
                        retained_index=retained_index,
                        phase_index=phase_index,
                        variable=model.variables[variable_position],
                        state_before=conditioned,
                        conditioned_state=conditioned,
                        probability_up=probability_up,
                        uniform=uniform,
                        state_after=after,
                    )
                )
            current = after
        return current, tuple(events)
