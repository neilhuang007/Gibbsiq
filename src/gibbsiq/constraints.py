"""Bounded QUBO lowerings for the repository's knapsack and TSP fixtures.

Each compiler exposes its penalty certificate, QUBO coefficients, canonical
Ising conversion, decoder, and overhead.  The encodings implement EVAL-EQ-025
only; they do not infer a general constraint language or tune penalties.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal

from gibbsiq._frozen import freeze
from gibbsiq.conversions import compile_qubo
from gibbsiq.model import (
    IsingModel,
    Variable,
    Vartype,
    finite_float,
    finite_sum,
    sample_to_spin_values,
)

ConstraintPenaltyStatus = Literal["not_proved_adequate", "proved_adequate"]


@dataclass(frozen=True, slots=True)
class ConstraintPenaltyPolicy:
    """Caller penalty together with an instance-derived sufficient condition."""

    penalty: float
    strict_boundary: float
    status: ConstraintPenaltyStatus
    selection: Literal["caller_supplied", "derived_strict"]
    certificate_arithmetic: Literal["exact"]
    finite_precision_guarantee: Literal["not_universally_certified"]
    proof_scope: str

    def to_metadata(self) -> dict[str, Any]:
        """Return the complete machine-readable certificate record."""
        return {
            "penalty": self.penalty,
            "strict_boundary": self.strict_boundary,
            "status": self.status,
            "selection": self.selection,
            "certificate_arithmetic": self.certificate_arithmetic,
            "finite_precision_guarantee": self.finite_precision_guarantee,
            "proof_scope": self.proof_scope,
        }


def _positive_float(value: Any, *, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric, not boolean")
    number = finite_float(value, name=name)
    if number <= 0.0:
        raise ValueError(f"{name} must be positive")
    return number


def _nonnegative_float(value: Any, *, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric, not boolean")
    number = finite_float(value, name=name)
    if number < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return number


def _finite_number(value: Any, *, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric, not boolean")
    return finite_float(value, name=name)


def _derived_strict_penalty(strict_boundary: float, *, name: str) -> float:
    """Return a finite binary64 value strictly above an audited boundary."""
    try:
        candidate = float(math.floor(strict_boundary) + 1)
    except OverflowError as error:
        raise ValueError(f"{name} cannot derive a finite strict penalty") from error
    if candidate <= strict_boundary:
        candidate = math.nextafter(strict_boundary, math.inf)
    candidate = finite_float(candidate, name=name)
    if candidate <= strict_boundary:
        raise ValueError(f"{name} cannot derive a finite strict penalty")
    return candidate


def _positive_integer(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _binary_values(
    sample: Mapping[Variable, int],
    variables: tuple[Variable, ...],
    *,
    vartype: Vartype,
) -> dict[Variable, int]:
    if not isinstance(sample, Mapping):
        raise TypeError(f"lowered sample must be a mapping, got {type(sample).__name__}")
    if len(sample) != len(variables):
        raise ValueError("lowered sample keys must match encoded variables exactly")
    spins = sample_to_spin_values(sample, variables, vartype)
    return {variable: (spin + 1) // 2 for variable, spin in zip(variables, spins)}


def _qubo_energy(
    *,
    variables: tuple[Variable, ...],
    linear: Mapping[Variable, float],
    quadratic: Mapping[tuple[Variable, Variable], float],
    offset: float,
    sample: Mapping[Variable, int],
    vartype: Vartype,
    name: str,
) -> float:
    bits = _binary_values(sample, variables, vartype=vartype)
    return finite_sum(
        [offset]
        + [linear[variable] * bits[variable] for variable in variables]
        + [coefficient * bits[left] * bits[right] for (left, right), coefficient in quadratic.items()],
        name=name,
    )


def _add_term(terms: dict[Any, list[float]], key: Any, value: float) -> None:
    if value != 0.0:
        terms.setdefault(key, []).append(value)


def _finalize_qubo(
    variables: tuple[Variable, ...],
    linear_terms: dict[Variable, list[float]],
    quadratic_terms: dict[tuple[Variable, Variable], list[float]],
    offset_terms: list[float],
) -> tuple[Mapping[Variable, float], Mapping[tuple[Variable, Variable], float], float]:
    positions = {variable: index for index, variable in enumerate(variables)}
    linear = MappingProxyType(
        {
            variable: finite_sum(
                linear_terms.get(variable, []),
                name=f"constraint QUBO linear coefficient for {variable!r}",
            )
            for variable in variables
        }
    )
    normalized_quadratic_terms: dict[tuple[Variable, Variable], list[float]] = {}
    for (left, right), values in quadratic_terms.items():
        pair = (left, right) if positions[left] < positions[right] else (right, left)
        normalized_quadratic_terms.setdefault(pair, []).extend(values)
    quadratic: dict[tuple[Variable, Variable], float] = {}
    for pair, values in normalized_quadratic_terms.items():
        coefficient = finite_sum(values, name=f"constraint QUBO quadratic coefficient for {pair!r}")
        if coefficient != 0.0:
            quadratic[pair] = coefficient
    ordered_quadratic = MappingProxyType(
        dict(
            sorted(
                quadratic.items(),
                key=lambda item: (positions[item[0][0]], positions[item[0][1]]),
            )
        )
    )
    return linear, ordered_quadratic, finite_sum(offset_terms, name="constraint QUBO offset")


def _slack_weights(capacity: int) -> tuple[int, ...]:
    """Binary coefficients covering every integer from zero through capacity."""
    bit_count = capacity.bit_length()
    if bit_count == 1:
        return (1,)
    prefix = tuple(1 << index for index in range(bit_count - 1))
    final_weight = capacity - ((1 << (bit_count - 1)) - 1)
    return prefix + (final_weight,)


@dataclass(frozen=True, slots=True)
class KnapsackEncoding:
    """Slack-encoded finite knapsack objective and strict source decoder."""

    weights: tuple[int, ...]
    values: tuple[int, ...]
    capacity: int
    offset: float
    reward_scale: int
    item_variables: tuple[Variable, ...]
    slack_variables: tuple[Variable, ...]
    ancilla_variables: tuple[Variable, ...]
    slack_weights: tuple[int, ...]
    variables: tuple[Variable, ...]
    qubo_linear: Mapping[Variable, float]
    qubo_quadratic: Mapping[tuple[Variable, Variable], float]
    qubo_offset: float
    ising_model: IsingModel
    penalty_policy: ConstraintPenaltyPolicy
    source_objective_map: str
    overhead: Mapping[str, Any]

    def qubo_energy(
        self,
        sample: Mapping[Variable, int],
        *,
        vartype: Vartype = "BINARY",
    ) -> float:
        return _qubo_energy(
            variables=self.variables,
            linear=self.qubo_linear,
            quadratic=self.qubo_quadratic,
            offset=self.qubo_offset,
            sample=sample,
            vartype=vartype,
            name="knapsack QUBO energy",
        )

    def native_evaluation(self, selection: Sequence[int]) -> tuple[int, int]:
        """Return native ``(value, weight)`` after exact index validation."""
        selected = tuple(selection)
        if len(set(selected)) != len(selected):
            raise ValueError("knapsack selection contains duplicate item indices")
        if any(isinstance(index, bool) or not isinstance(index, int) for index in selected):
            raise ValueError("knapsack selection indices must be integers")
        if any(index < 0 or index >= len(self.weights) for index in selected):
            raise ValueError("knapsack selection index is out of range")
        value = sum(self.values[index] for index in selected)
        weight = sum(self.weights[index] for index in selected)
        return value, weight

    def _residual_from_bits(self, bits: Mapping[Variable, int]) -> int:
        selected_weight = sum(
            weight * bits[variable] for variable, weight in zip(self.item_variables, self.weights)
        )
        slack = sum(
            weight * bits[variable] for variable, weight in zip(self.slack_variables, self.slack_weights)
        )
        return selected_weight + slack - self.capacity

    def residual(
        self,
        sample: Mapping[Variable, int],
        *,
        vartype: Vartype = "BINARY",
    ) -> int:
        bits = _binary_values(sample, self.variables, vartype=vartype)
        return self._residual_from_bits(bits)

    def is_valid(
        self,
        sample: Mapping[Variable, int],
        *,
        vartype: Vartype = "BINARY",
    ) -> bool:
        return self.residual(sample, vartype=vartype) == 0

    def decode(
        self,
        sample: Mapping[Variable, int],
        *,
        vartype: Vartype = "BINARY",
    ) -> tuple[int, ...]:
        """Decode a zero-residual word to selected source-item indices."""
        bits = _binary_values(sample, self.variables, vartype=vartype)
        if self._residual_from_bits(bits) != 0:
            raise ValueError("cannot decode a knapsack word whose slack residual is nonzero")
        return tuple(index for index, variable in enumerate(self.item_variables) if bits[variable] == 1)


def compile_knapsack(
    weights: Sequence[int],
    values: Sequence[int],
    capacity: int,
    *,
    penalty: float | None = None,
    offset: float = 0.0,
) -> KnapsackEncoding:
    """Compile the benchmark's finite 0/1 knapsack contract to QUBO/Ising.

    An omitted ``penalty`` derives the smallest integer strictly above the
    EVAL-EQ-025 bound. Explicit values preserve boundary experiments.
    """
    canonical_weights = tuple(_positive_integer(value, name="knapsack weight") for value in weights)
    canonical_values = tuple(_positive_integer(value, name="knapsack value") for value in values)
    if not canonical_weights or len(canonical_weights) != len(canonical_values):
        raise ValueError("knapsack weights and values must be nonempty and have equal lengths")
    canonical_capacity = _positive_integer(capacity, name="knapsack capacity")
    source_offset = _finite_number(offset, name="knapsack source offset")
    reward_scale = canonical_capacity + 1
    strict_boundary = finite_float(
        max(
            0,
            max(reward_scale * value - weight for weight, value in zip(canonical_weights, canonical_values)),
        ),
        name="knapsack penalty strict boundary",
    )
    penalty_selection: Literal["caller_supplied", "derived_strict"]
    if penalty is None:
        canonical_penalty = _derived_strict_penalty(
            strict_boundary,
            name="derived knapsack penalty",
        )
        penalty_selection = "derived_strict"
    else:
        canonical_penalty = _nonnegative_float(penalty, name="knapsack penalty")
        penalty_selection = "caller_supplied"
    item_variables = tuple(
        ("gibbsiq.constraint", "knapsack_item", index) for index in range(len(canonical_weights))
    )
    slack_weights = _slack_weights(canonical_capacity)
    slack_variables = tuple(
        ("gibbsiq.constraint", "knapsack_slack", index) for index in range(len(slack_weights))
    )
    variables = item_variables + slack_variables
    coefficient_by_variable = {
        **dict(zip(item_variables, canonical_weights)),
        **dict(zip(slack_variables, slack_weights)),
    }
    linear_terms: dict[Variable, list[float]] = {variable: [] for variable in variables}
    quadratic_terms: dict[tuple[Variable, Variable], list[float]] = {}
    offset_terms = [source_offset, canonical_penalty * canonical_capacity * canonical_capacity]
    for index, variable in enumerate(variables):
        coefficient = coefficient_by_variable[variable]
        _add_term(
            linear_terms,
            variable,
            canonical_penalty * (coefficient * coefficient - 2.0 * canonical_capacity * coefficient),
        )
        if index < len(item_variables):
            item_index = index
            _add_term(
                linear_terms,
                variable,
                -reward_scale * canonical_values[item_index] + canonical_weights[item_index],
            )
        for other in variables[index + 1 :]:
            _add_term(
                quadratic_terms,
                (variable, other),
                2.0 * canonical_penalty * coefficient * coefficient_by_variable[other],
            )
    linear, quadratic, qubo_offset = _finalize_qubo(
        variables,
        linear_terms,
        quadratic_terms,
        offset_terms,
    )
    status: ConstraintPenaltyStatus = (
        "proved_adequate" if canonical_penalty > strict_boundary else "not_proved_adequate"
    )
    policy = ConstraintPenaltyPolicy(
        penalty=canonical_penalty,
        strict_boundary=strict_boundary,
        status=status,
        selection=penalty_selection,
        certificate_arithmetic="exact",
        finite_precision_guarantee="not_universally_certified",
        proof_scope=(
            "EVAL-EQ-025 exact arithmetic: P > max(0, max_i((C + 1) * value_i - "
            "weight_i)) separates every infeasible word from a feasible selection"
        ),
    )
    overhead = {
        "source_variable_count": len(item_variables),
        "ancilla_count": len(slack_variables),
        "slack_bit_count": len(slack_variables),
        "encoded_variable_count": len(variables),
        "qubo_linear_term_count": sum(value != 0.0 for value in linear.values()),
        "qubo_quadratic_term_count": len(quadratic),
        "capacity": canonical_capacity,
        "reward_scale": reward_scale,
        "source_offset": source_offset,
        "penalty_policy": policy.to_metadata(),
        "equation_contract": "EVAL-EQ-025",
        "objective_relation": "lowered = offset - (C + 1) * value + weight on valid words",
    }
    ising_model = compile_qubo(
        {
            "variables": list(variables),
            "linear": dict(linear),
            "quadratic": dict(quadratic),
            "offset": qubo_offset,
        },
        metadata=overhead,
        source_format="knapsack_slack_qubo",
    )
    return KnapsackEncoding(
        weights=canonical_weights,
        values=canonical_values,
        capacity=canonical_capacity,
        offset=source_offset,
        reward_scale=reward_scale,
        item_variables=item_variables,
        slack_variables=slack_variables,
        ancilla_variables=slack_variables,
        slack_weights=slack_weights,
        variables=variables,
        qubo_linear=linear,
        qubo_quadratic=quadratic,
        qubo_offset=qubo_offset,
        ising_model=ising_model,
        penalty_policy=policy,
        source_objective_map="lexicographic_value_then_weight",
        overhead=freeze(overhead),
    )


@dataclass(frozen=True, slots=True)
class TspEncoding:
    """One-hot cyclic TSP encoding and strict permutation decoder."""

    distance_matrix: tuple[tuple[float, ...], ...]
    offset: float
    objective_scale: float
    city_position_variables: tuple[tuple[Variable, ...], ...]
    ancilla_variables: tuple[Variable, ...]
    variables: tuple[Variable, ...]
    qubo_linear: Mapping[Variable, float]
    qubo_quadratic: Mapping[tuple[Variable, Variable], float]
    qubo_offset: float
    ising_model: IsingModel
    penalty_policy: ConstraintPenaltyPolicy
    source_objective_map: str
    overhead: Mapping[str, Any]

    @property
    def num_cities(self) -> int:
        return len(self.distance_matrix)

    def qubo_energy(
        self,
        sample: Mapping[Variable, int],
        *,
        vartype: Vartype = "BINARY",
    ) -> float:
        return _qubo_energy(
            variables=self.variables,
            linear=self.qubo_linear,
            quadratic=self.qubo_quadratic,
            offset=self.qubo_offset,
            sample=sample,
            vartype=vartype,
            name="TSP QUBO energy",
        )

    def one_hot_violation(
        self,
        sample: Mapping[Variable, int],
        *,
        vartype: Vartype = "BINARY",
    ) -> int:
        bits = _binary_values(sample, self.variables, vartype=vartype)
        return self._one_hot_violation_from_bits(bits)

    def _one_hot_violation_from_bits(self, bits: Mapping[Variable, int]) -> int:
        return sum(
            (1 - sum(bits[self.city_position_variables[city][position]] for city in range(self.num_cities)))
            ** 2
            for position in range(self.num_cities)
        ) + sum(
            (
                1
                - sum(
                    bits[self.city_position_variables[city][position]] for position in range(self.num_cities)
                )
            )
            ** 2
            for city in range(self.num_cities)
        )

    def is_valid(
        self,
        sample: Mapping[Variable, int],
        *,
        vartype: Vartype = "BINARY",
    ) -> bool:
        return self.one_hot_violation(sample, vartype=vartype) == 0

    def native_length(self, tour: Sequence[int]) -> float:
        canonical_tour = tuple(tour)
        if any(isinstance(city, bool) or not isinstance(city, int) for city in canonical_tour):
            raise ValueError("TSP tour city indices must be integers")
        if len(canonical_tour) != self.num_cities or set(canonical_tour) != set(range(self.num_cities)):
            raise ValueError("TSP tour must contain every city exactly once")
        return finite_sum(
            [
                self.distance_matrix[canonical_tour[position]][
                    canonical_tour[(position + 1) % self.num_cities]
                ]
                for position in range(self.num_cities)
            ],
            name="native TSP tour length",
        )

    def decode(
        self,
        sample: Mapping[Variable, int],
        *,
        vartype: Vartype = "BINARY",
    ) -> tuple[int, ...]:
        """Decode a valid one-hot word into city order by tour position."""
        bits = _binary_values(sample, self.variables, vartype=vartype)
        if self._one_hot_violation_from_bits(bits) != 0:
            raise ValueError("cannot decode a TSP word with one-hot violations")
        return tuple(
            next(
                city
                for city in range(self.num_cities)
                if bits[self.city_position_variables[city][position]] == 1
            )
            for position in range(self.num_cities)
        )


def _canonical_distance_matrix(distance_matrix: Sequence[Sequence[float]]) -> tuple[tuple[float, ...], ...]:
    matrix = tuple(tuple(row) for row in distance_matrix)
    if len(matrix) < 3:
        raise ValueError("TSP encoding requires at least three cities")
    if any(len(row) != len(matrix) for row in matrix):
        raise ValueError("TSP distance matrix must be square")
    canonical: list[tuple[float, ...]] = []
    for city, row in enumerate(matrix):
        canonical_row: list[float] = []
        for destination, value in enumerate(row):
            if isinstance(value, bool):
                raise ValueError("TSP distances must be finite numeric values, not boolean")
            distance = finite_float(value, name=f"TSP distance[{city}][{destination}]")
            if distance < 0.0:
                raise ValueError("TSP distances must be nonnegative")
            if city == destination and distance != 0.0:
                raise ValueError("TSP distance matrix diagonal must be zero")
            canonical_row.append(distance)
        canonical.append(tuple(canonical_row))
    for city in range(len(canonical)):
        for destination in range(city + 1, len(canonical)):
            if canonical[city][destination] != canonical[destination][city]:
                raise ValueError("TSP distance matrix must be symmetric")
    return tuple(canonical)


def compile_tsp(
    distance_matrix: Sequence[Sequence[float]],
    *,
    penalty: float | None = None,
    objective_scale: float = 1.0,
    offset: float = 0.0,
) -> TspEncoding:
    """Compile a symmetric finite TSP matrix to a one-hot QUBO/Ising model."""
    matrix = _canonical_distance_matrix(distance_matrix)
    canonical_scale = _positive_float(objective_scale, name="TSP objective scale")
    source_offset = _finite_number(offset, name="TSP source offset")
    n = len(matrix)
    declared_tour_length = finite_sum(
        [matrix[city][(city + 1) % n] for city in range(n)],
        name="declared feasible TSP tour length",
    )
    strict_boundary = finite_float(
        canonical_scale * declared_tour_length / 2.0,
        name="TSP penalty strict boundary",
    )
    penalty_selection: Literal["caller_supplied", "derived_strict"]
    if penalty is None:
        canonical_penalty = _derived_strict_penalty(
            strict_boundary,
            name="derived TSP penalty",
        )
        penalty_selection = "derived_strict"
    else:
        canonical_penalty = _nonnegative_float(penalty, name="TSP penalty")
        penalty_selection = "caller_supplied"
    city_position_variables = tuple(
        tuple(("gibbsiq.constraint", "tsp_city_position", city, position) for position in range(len(matrix)))
        for city in range(len(matrix))
    )
    variables = tuple(variable for row in city_position_variables for variable in row)
    linear_terms: dict[Variable, list[float]] = {variable: [] for variable in variables}
    quadratic_terms: dict[tuple[Variable, Variable], list[float]] = {}
    offset_terms = [source_offset]
    for position in range(n):
        row = tuple(city_position_variables[city][position] for city in range(n))
        offset_terms.append(canonical_penalty)
        for index, variable in enumerate(row):
            _add_term(linear_terms, variable, -canonical_penalty)
            for other in row[index + 1 :]:
                _add_term(quadratic_terms, (variable, other), 2.0 * canonical_penalty)
    for city in range(n):
        column = city_position_variables[city]
        offset_terms.append(canonical_penalty)
        for index, variable in enumerate(column):
            _add_term(linear_terms, variable, -canonical_penalty)
            for other in column[index + 1 :]:
                _add_term(quadratic_terms, (variable, other), 2.0 * canonical_penalty)
    for position in range(n):
        next_position = (position + 1) % n
        for city in range(n):
            for destination in range(n):
                _add_term(
                    quadratic_terms,
                    (
                        city_position_variables[city][position],
                        city_position_variables[destination][next_position],
                    ),
                    canonical_scale * matrix[city][destination],
                )
    linear, quadratic, qubo_offset = _finalize_qubo(
        variables,
        linear_terms,
        quadratic_terms,
        offset_terms,
    )
    declared_tour = tuple(range(n))
    status: ConstraintPenaltyStatus = (
        "proved_adequate" if canonical_penalty > strict_boundary else "not_proved_adequate"
    )
    policy = ConstraintPenaltyPolicy(
        penalty=canonical_penalty,
        strict_boundary=strict_boundary,
        status=status,
        selection=penalty_selection,
        certificate_arithmetic="exact",
        finite_precision_guarantee="not_universally_certified",
        proof_scope=(
            "EVAL-EQ-025 exact arithmetic: every invalid two-way one-hot word has penalty "
            "at least 2P; P > B * declared_feasible_tour_length / 2 separates it from the "
            "declared tour"
        ),
    )
    overhead = {
        "source_city_count": n,
        "ancilla_count": 0,
        "encoded_variable_count": len(variables),
        "one_hot_equation_count": 2 * n,
        "qubo_linear_term_count": sum(value != 0.0 for value in linear.values()),
        "qubo_quadratic_term_count": len(quadratic),
        "declared_feasible_tour": list(declared_tour),
        "declared_feasible_tour_length": declared_tour_length,
        "source_offset": source_offset,
        "objective_scale": canonical_scale,
        "penalty_policy": policy.to_metadata(),
        "equation_contract": "EVAL-EQ-025",
        "objective_relation": "lowered = offset + objective_scale * native_tour_length on valid words",
    }
    ising_model = compile_qubo(
        {
            "variables": list(variables),
            "linear": dict(linear),
            "quadratic": dict(quadratic),
            "offset": qubo_offset,
        },
        metadata=overhead,
        source_format="tsp_one_hot_qubo",
    )
    return TspEncoding(
        distance_matrix=matrix,
        offset=source_offset,
        objective_scale=canonical_scale,
        city_position_variables=city_position_variables,
        ancilla_variables=(),
        variables=variables,
        qubo_linear=linear,
        qubo_quadratic=quadratic,
        qubo_offset=qubo_offset,
        ising_model=ising_model,
        penalty_policy=policy,
        source_objective_map="native_tour_length",
        overhead=freeze(overhead),
    )
