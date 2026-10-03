"""Independent, bounded numerical references for qualification fixtures."""

from __future__ import annotations

import itertools
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from gibbsiq.model import IsingModel, Variable, exact_variable_position
from gibbsiq.qualification._validation import _finite as _finite_float
from gibbsiq.qualification._validation import _integer


_MAX_FREE_SPINS = 8


def _free_spin_limit(value: Any) -> int:
    if type(value) is not int or not 0 <= value <= _MAX_FREE_SPINS:
        raise ValueError(f"max_variables must be an integer from 0 through {_MAX_FREE_SPINS}")
    return value


def _probability_up(field: float) -> float:
    """Return logistic(2*field) without exponentiating a large positive value."""
    if field >= 0.0:
        opposite_weight = math.exp(-2.0 * field)
        return 1.0 / (1.0 + opposite_weight)
    up_weight = math.exp(2.0 * field)
    return up_weight / (1.0 + up_weight)


@dataclass(frozen=True, slots=True)
class SpinMoments:
    probability_up: float
    mean: float
    variance: float
    mean_variance: float
    samples: int


@dataclass(frozen=True, slots=True)
class IsingReference:
    variables: tuple[Variable, ...]
    states: tuple[tuple[int, ...], ...]
    energies: tuple[float, ...]
    probabilities: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class ConditionalReference:
    parent_states: tuple[tuple[int, int, int, int], ...]
    fields: tuple[float, ...]
    probability_up: tuple[float, ...]
    joint_probabilities: tuple[float, ...]
    mean: float
    variance: float


@dataclass(frozen=True, slots=True)
class TorxReference:
    probabilities: tuple[float, float, float, float]
    bit_means: tuple[float, float]


def torx_two_gate_reference(
    theta: Sequence[float] = (0.0, 0.0), initial: Sequence[int] = (0, 0)
) -> TorxReference:
    """Enumerate PNOT(0), PCNOT(0,1) as four independent Bernoulli branches."""
    if isinstance(theta, (str, bytes, Mapping, set, frozenset)) or isinstance(
        initial, (str, bytes, Mapping, set, frozenset)
    ):
        raise ValueError("theta and initial must be length-two sequences")
    try:
        angles, bits = tuple(theta), tuple(initial)
    except TypeError as error:
        raise ValueError("theta and initial must be length-two sequences") from error
    if len(angles) != 2 or len(bits) != 2 or any(type(bit) is not int or bit not in (0, 1) for bit in bits):
        raise ValueError("theta and initial must contain two angles and exact integer bits")
    angles = tuple(_finite_float(value, name=f"theta[{index}]") for index, value in enumerate(angles))

    flip0, flip1 = (_probability_up(value * 0.5) for value in angles)
    masses = [0.0] * 4
    for first_flip, first_mass in ((0, 1.0 - flip0), (1, flip0)):
        first_bit = bits[0] ^ first_flip
        for second_flip, second_mass in ((0, 1.0 - flip1), (1, flip1)):
            second_bit = bits[1] ^ (first_bit & second_flip)
            masses[2 * first_bit + second_bit] += first_mass * second_mass
    probabilities = (masses[0], masses[1], masses[2], masses[3])
    return TorxReference(
        probabilities, (probabilities[2] + probabilities[3], probabilities[1] + probabilities[3])
    )


def spin_conditional(field: float, *, samples: int = 1) -> SpinMoments:
    """Evaluate the analytic two-state spin law at one finite field."""
    canonical_field = _finite_float(field, name="field")
    canonical_samples = _integer(samples, name="samples", minimum=1)
    probability_up = _probability_up(canonical_field)
    mean = 2.0 * probability_up - 1.0
    variance = max(0.0, 1.0 - mean * mean)
    return SpinMoments(
        probability_up=probability_up,
        mean=mean,
        variance=variance,
        mean_variance=variance / canonical_samples,
        samples=canonical_samples,
    )


def _direct_ising_energies(
    state: tuple[int, ...],
    linear: tuple[tuple[int, float], ...],
    quadratic: tuple[tuple[int, int, float], ...],
    offset: float,
) -> tuple[float, float]:
    interaction_terms = [coefficient * state[position] for position, coefficient in linear]
    interaction_terms.extend(
        coefficient * state[left] * state[right] for left, right, coefficient in quadratic
    )
    try:
        interaction = math.fsum(interaction_terms)
        energy = math.fsum((offset, interaction))
    except OverflowError as error:
        raise ValueError("direct Ising energy exceeds finite binary64 range") from error
    if not math.isfinite(interaction) or not math.isfinite(energy):
        raise ValueError("direct Ising energy must remain finite")
    return interaction, energy


def enumerate_ising(
    model: IsingModel,
    *,
    beta: float = 1.0,
    clamped: Mapping[Variable, int] | None = None,
    max_variables: int = 8,
) -> IsingReference:
    """Enumerate a tiny Ising law using the model's stored coefficients directly."""
    if not isinstance(model, IsingModel):
        raise ValueError("model must be an IsingModel")
    canonical_beta = _finite_float(beta, name="beta")
    if canonical_beta < 0.0:
        raise ValueError("beta must be nonnegative")
    limit = _free_spin_limit(max_variables)

    if clamped is None:
        clamp_items: tuple[tuple[Variable, int], ...] = ()
    elif isinstance(clamped, Mapping):
        clamp_items = tuple(clamped.items())
    else:
        raise ValueError("clamped must be a mapping")

    clamp_by_position: dict[int, int] = {}
    for variable, spin in clamp_items:
        try:
            position = exact_variable_position(variable, model.variables)
        except KeyError as error:
            raise ValueError(f"clamped variable {variable!r} is not in the model") from error
        if type(spin) is not int or spin not in {-1, 1}:
            raise ValueError("clamped spins must be exact integers -1 or +1")
        clamp_by_position[position] = spin

    free_positions = tuple(
        position for position in range(len(model.variables)) if position not in clamp_by_position
    )
    if len(free_positions) > limit:
        raise ValueError(f"enumeration has {len(free_positions)} free spins, exceeding max_variables={limit}")

    positions = {variable: position for position, variable in enumerate(model.variables)}
    linear = tuple((position, model.linear[variable]) for position, variable in enumerate(model.variables))
    quadratic = tuple(
        (positions[left], positions[right], coefficient)
        for (left, right), coefficient in model.quadratic.items()
    )
    offset = model.offset

    states: list[tuple[int, ...]] = []
    energies: list[float] = []
    log_weights: list[float] = []
    for free_state in itertools.product((-1, 1), repeat=len(free_positions)):
        state_values = [0] * len(model.variables)
        for position, spin in clamp_by_position.items():
            state_values[position] = spin
        for position, spin in zip(free_positions, free_state):
            state_values[position] = spin
        state = tuple(state_values)
        interaction, energy = _direct_ising_energies(state, linear, quadratic, offset)
        log_weight = -canonical_beta * interaction
        if not math.isfinite(log_weight):
            raise ValueError("Ising log weight must remain finite")
        states.append(state)
        energies.append(energy)
        log_weights.append(log_weight)

    maximum_log_weight = max(log_weights)
    shifted_weights: list[float] = []
    for log_weight in log_weights:
        shifted = log_weight - maximum_log_weight
        if not math.isfinite(shifted):
            raise ValueError("Ising log-weight range must remain finite")
        shifted_weights.append(math.exp(shifted))
    normalizer = math.fsum(shifted_weights)
    if not math.isfinite(normalizer) or normalizer <= 0.0:
        raise ValueError("Ising probability normalizer must be finite and positive")

    return IsingReference(
        variables=tuple(model.variables),
        states=tuple(states),
        energies=tuple(energies),
        probabilities=tuple(weight / normalizer for weight in shifted_weights),
    )


def four_parent_conditional(
    weights: Sequence[float],
    *,
    bias: float = 0.0,
    parent_probabilities: Sequence[float] | None = None,
) -> ConditionalReference:
    """Enumerate a four-parent conditional spin law and its joint distribution."""
    if isinstance(weights, (str, bytes, bytearray, Mapping, set, frozenset)):
        raise ValueError("weights must be a sequence of four finite numbers")
    try:
        raw_weights = tuple(weights)
    except TypeError as error:
        raise ValueError("weights must be a sequence of four finite numbers") from error
    if len(raw_weights) != 4:
        raise ValueError("weights must contain exactly four values")
    canonical_weights = tuple(
        _finite_float(value, name=f"weights[{position}]") for position, value in enumerate(raw_weights)
    )
    canonical_bias = _finite_float(bias, name="bias")

    parent_states = tuple(
        (first, second, third, fourth)
        for first in (-1, 1)
        for second in (-1, 1)
        for third in (-1, 1)
        for fourth in (-1, 1)
    )
    masses: tuple[float, ...]
    if parent_probabilities is None:
        masses = (1.0 / 16.0,) * 16
    else:
        if isinstance(
            parent_probabilities,
            (str, bytes, bytearray, Mapping, set, frozenset),
        ):
            raise ValueError("parent_probabilities must contain exactly 16 masses")
        try:
            raw_masses = tuple(parent_probabilities)
        except TypeError as error:
            raise ValueError("parent_probabilities must contain exactly 16 masses") from error
        if len(raw_masses) != 16:
            raise ValueError("parent_probabilities must contain exactly 16 masses")
        validated_masses = tuple(
            _finite_float(value, name=f"parent_probabilities[{position}]")
            for position, value in enumerate(raw_masses)
        )
        if any(mass < 0.0 for mass in validated_masses):
            raise ValueError("parent probabilities must be nonnegative")
        try:
            total_mass = math.fsum(validated_masses)
        except OverflowError as error:
            raise ValueError("parent probability sum must remain finite") from error
        if abs(total_mass - 1.0) > 1e-12:
            raise ValueError("parent probabilities must sum to one within 1e-12")
        masses = tuple(mass / total_mass for mass in validated_masses)

    fields: list[float] = []
    probabilities_up: list[float] = []
    joint_probabilities: list[float] = []
    conditional_means: list[float] = []
    for parent_state, parent_mass in zip(parent_states, masses):
        try:
            field = math.fsum(
                [canonical_bias] + [weight * spin for weight, spin in zip(canonical_weights, parent_state)]
            )
        except OverflowError as error:
            raise ValueError("conditional field exceeds finite binary64 range") from error
        if not math.isfinite(field):
            raise ValueError("conditional field must remain finite")
        probability_up = _probability_up(field)
        fields.append(field)
        probabilities_up.append(probability_up)
        joint_probabilities.extend((parent_mass * (1.0 - probability_up), parent_mass * probability_up))
        conditional_means.append(parent_mass * (2.0 * probability_up - 1.0))

    mean = math.fsum(conditional_means)
    variance = max(0.0, 1.0 - mean * mean)
    return ConditionalReference(
        parent_states=parent_states,
        fields=tuple(fields),
        probability_up=tuple(probabilities_up),
        joint_probabilities=tuple(joint_probabilities),
        mean=mean,
        variance=variance,
    )
