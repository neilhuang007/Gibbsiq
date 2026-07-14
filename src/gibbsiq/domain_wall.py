"""Exact thermometer/domain-wall lowering for pairwise categorical energies.

The compiler first constructs a binary QUBO from discrete finite differences,
then delegates QUBO-to-Ising conversion to :func:`gibbsiq.conversions.compile_qubo`.
Exact valid-state energies do not imply that the encoded Markov chain mixes well.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from gibbsiq._frozen import freeze, thaw
from gibbsiq.categorical import CategoricalModel, CategoricalSample
from gibbsiq.conversions import compile_qubo
from gibbsiq.model import IsingModel, Variable, Vartype, finite_float, finite_sum, normalize_vartype

MIXING_WARNING = (
    "valid-state energy equality does not preserve mixing: category order changes one-bit "
    "adjacency, mixed finite differences can densify the wall graph, and invalid wall words "
    "add states that are absent from the categorical model"
)


@dataclass(frozen=True, slots=True)
class _DomainWallVariable:
    """Private typed label, deterministic from canonical compiler positions."""

    variable_position: int
    wall_position: int

    def __deepcopy__(self, memo: dict[int, Any]) -> _DomainWallVariable:
        memo[id(self)] = self
        return self

    def __repr__(self) -> str:
        return (
            "DomainWallVariable("
            f"variable_position={self.variable_position}, wall_position={self.wall_position})"
        )


def _positive_penalty(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("penalty must be a finite positive number, not boolean")
    penalty = finite_float(value, name="domain-wall penalty")
    if penalty <= 0.0:
        raise ValueError(f"penalty must be positive, got {value!r}")
    return penalty


def _difference(values: Sequence[float], *, name: str) -> float:
    return finite_sum(values, name=name)


def _append_term(
    terms: dict[Any, list[float]],
    key: Any,
    coefficient: float,
) -> None:
    if coefficient != 0.0:
        terms.setdefault(key, []).append(coefficient)


@dataclass(frozen=True, slots=True)
class DomainWallEncoding:
    """Immutable QUBO/Ising lowering plus its categorical codec."""

    categorical_model: CategoricalModel
    penalty: float
    wall_variables: Mapping[Variable, tuple[Variable, ...]]
    variables: tuple[Variable, ...]
    qubo_linear: Mapping[Variable, float]
    qubo_quadratic: Mapping[tuple[Variable, Variable], float]
    qubo_offset: float
    ising_model: IsingModel
    overhead_metadata: Mapping[str, Any]

    def _binary_values(
        self,
        sample: Mapping[Variable, int],
        *,
        vartype: Vartype,
    ) -> dict[Variable, int]:
        if not isinstance(sample, Mapping):
            raise TypeError(f"sample must be a mapping, got {type(sample).__name__}")
        normalized = normalize_vartype(vartype)
        supplied = set(sample)
        expected = set(self.variables)
        missing = expected - supplied
        extra = supplied - expected
        if missing or extra:
            raise ValueError(
                "wall sample keys must match encoded variables exactly; "
                f"missing={sorted(missing, key=repr)!r}, extra={sorted(extra, key=repr)!r}"
            )
        bits: dict[Variable, int] = {}
        for variable in self.variables:
            value = sample[variable]
            if isinstance(value, bool):
                raise ValueError(f"wall value for {variable!r} must not be boolean")
            if normalized == "BINARY":
                if value != 0 and value != 1:
                    raise ValueError(f"binary wall value for {variable!r} must be 0 or 1")
                bits[variable] = 1 if value == 1 else 0
            else:
                if value != -1 and value != 1:
                    raise ValueError(f"spin wall value for {variable!r} must be -1 or +1")
                bits[variable] = 1 if value == 1 else 0
        return bits

    def _violation_count_from_bits(self, bits: Mapping[Variable, int]) -> int:
        return sum(
            bits[right] == 1 and bits[left] == 0
            for chain in self.wall_variables.values()
            for left, right in zip(chain, chain[1:])
        )

    def encode(
        self,
        sample: CategoricalSample,
        *,
        vartype: Vartype = "BINARY",
    ) -> dict[Variable, int]:
        """Encode categories as prefix-one thermometer words."""
        normalized = normalize_vartype(vartype)
        category_indices = self.categorical_model.assignment_indices(sample)
        encoded: dict[Variable, int] = {}
        for variable_position, variable in enumerate(self.categorical_model.variables):
            category_index = category_indices[variable_position]
            for wall_position, wall_variable in enumerate(self.wall_variables[variable]):
                bit = 1 if category_index > wall_position else 0
                encoded[wall_variable] = bit if normalized == "BINARY" else 2 * bit - 1
        return encoded

    def violation_count(
        self,
        sample: Mapping[Variable, int],
        *,
        vartype: Vartype = "BINARY",
    ) -> int:
        """Count adjacent reverse walls; malformed samples raise validation errors."""
        bits = self._binary_values(sample, vartype=vartype)
        return self._violation_count_from_bits(bits)

    def is_valid(
        self,
        sample: Mapping[Variable, int],
        *,
        vartype: Vartype = "BINARY",
    ) -> bool:
        """Return whether a well-formed sample has no reverse domain wall."""
        return self.violation_count(sample, vartype=vartype) == 0

    def decode(
        self,
        sample: Mapping[Variable, int],
        *,
        vartype: Vartype = "BINARY",
    ) -> dict[Variable, Any]:
        """Decode a valid wall word; reject invalid or malformed words."""
        bits = self._binary_values(sample, vartype=vartype)
        violations = self._violation_count_from_bits(bits)
        if violations:
            raise ValueError(f"cannot decode wall sample with {violations} reverse-wall violation(s)")
        decoded: dict[Variable, Any] = {}
        for variable in self.categorical_model.variables:
            category_index = sum(bits[wall] for wall in self.wall_variables[variable])
            decoded[variable] = self.categorical_model.domains[variable][category_index]
        return decoded

    def qubo_energy(
        self,
        sample: Mapping[Variable, int],
        *,
        vartype: Vartype = "BINARY",
    ) -> float:
        """Evaluate the constructed QUBO directly for audit and comparison."""
        bits = self._binary_values(sample, vartype=vartype)
        terms = [self.qubo_offset]
        terms.extend(self.qubo_linear[variable] * bits[variable] for variable in self.variables)
        terms.extend(
            coefficient * bits[left] * bits[right]
            for (left, right), coefficient in self.qubo_quadratic.items()
        )
        return finite_sum(terms, name="domain-wall QUBO energy")

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe ordered evidence without exposing private label identity."""
        encoded_positions = {variable: position for position, variable in enumerate(self.variables)}
        return {
            "penalty": self.penalty,
            "wall_variables": [
                {
                    "encoded_position": encoded_positions[wall_variable],
                    "original_variable_position": variable_position,
                    "wall_position": wall_position,
                }
                for variable_position, chain in enumerate(self.wall_variables.values())
                for wall_position, wall_variable in enumerate(chain)
            ],
            "wall_chains": [
                [encoded_positions[wall_variable] for wall_variable in chain]
                for chain in self.wall_variables.values()
            ],
            "qubo_linear": [
                {
                    "encoded_position": encoded_positions[variable],
                    "coefficient": self.qubo_linear[variable],
                }
                for variable in self.variables
            ],
            "qubo_quadratic": [
                {
                    "left_position": encoded_positions[left],
                    "right_position": encoded_positions[right],
                    "coefficient": coefficient,
                }
                for (left, right), coefficient in self.qubo_quadratic.items()
            ],
            "qubo_offset": self.qubo_offset,
            "overhead_metadata": thaw(self.overhead_metadata),
        }


def compile_domain_wall(
    model: CategoricalModel,
    *,
    penalty: float,
) -> DomainWallEncoding:
    """Lower a categorical pairwise energy to an exact valid-state QUBO/Ising model."""
    if not isinstance(model, CategoricalModel):
        raise TypeError(f"model must be CategoricalModel, got {type(model).__name__}")
    canonical_penalty = _positive_penalty(penalty)

    wall_variables: dict[Variable, tuple[Variable, ...]] = {}
    variables: list[Variable] = []
    for variable_position, variable in enumerate(model.variables):
        chain = tuple(
            _DomainWallVariable(variable_position, wall_position)
            for wall_position in range(len(model.domains[variable]) - 1)
        )
        wall_variables[variable] = chain
        variables.extend(chain)
    encoded_variables = tuple(variables)
    encoded_positions = {variable: position for position, variable in enumerate(encoded_variables)}

    linear_terms: dict[Variable, list[float]] = {variable: [] for variable in encoded_variables}
    quadratic_terms: dict[tuple[Variable, Variable], list[float]] = {}
    offset_terms = [model.offset]

    for variable in model.variables:
        domain = model.domains[variable]
        table = model.unary[variable]
        offset_terms.append(table[domain[0]])
        for wall_position, wall_variable in enumerate(wall_variables[variable]):
            difference = _difference(
                [table[domain[wall_position + 1]], -table[domain[wall_position]]],
                name=f"unary first difference for {variable!r} at {wall_position}",
            )
            _append_term(linear_terms, wall_variable, difference)

    pair_mixed_coefficient_capacity = 0
    for (left, right), table in model.pairwise.items():
        left_domain = model.domains[left]
        right_domain = model.domains[right]
        offset_terms.append(table[(left_domain[0], right_domain[0])])

        for wall_position, wall_variable in enumerate(wall_variables[left]):
            difference = _difference(
                [
                    table[(left_domain[wall_position + 1], right_domain[0])],
                    -table[(left_domain[wall_position], right_domain[0])],
                ],
                name=(f"pair first difference for {left!r}, {right!r} along left wall {wall_position}"),
            )
            _append_term(linear_terms, wall_variable, difference)

        for wall_position, wall_variable in enumerate(wall_variables[right]):
            difference = _difference(
                [
                    table[(left_domain[0], right_domain[wall_position + 1])],
                    -table[(left_domain[0], right_domain[wall_position])],
                ],
                name=(f"pair first difference for {left!r}, {right!r} along right wall {wall_position}"),
            )
            _append_term(linear_terms, wall_variable, difference)

        pair_mixed_coefficient_capacity += len(wall_variables[left]) * len(wall_variables[right])
        for left_position, left_wall in enumerate(wall_variables[left]):
            for right_position, right_wall in enumerate(wall_variables[right]):
                mixed_difference = _difference(
                    [
                        table[
                            (
                                left_domain[left_position + 1],
                                right_domain[right_position + 1],
                            )
                        ],
                        -table[
                            (
                                left_domain[left_position],
                                right_domain[right_position + 1],
                            )
                        ],
                        -table[
                            (
                                left_domain[left_position + 1],
                                right_domain[right_position],
                            )
                        ],
                        table[(left_domain[left_position], right_domain[right_position])],
                    ],
                    name=(
                        f"pair mixed difference for {left!r}, {right!r} "
                        f"at walls {left_position}, {right_position}"
                    ),
                )
                _append_term(
                    quadratic_terms,
                    (left_wall, right_wall),
                    mixed_difference,
                )

    constraint_edge_count = 0
    for chain in wall_variables.values():
        for left_wall, right_wall in zip(chain, chain[1:]):
            constraint_edge_count += 1
            _append_term(linear_terms, right_wall, canonical_penalty)
            _append_term(
                quadratic_terms,
                (left_wall, right_wall),
                -canonical_penalty,
            )

    qubo_linear = {
        variable: finite_sum(
            linear_terms[variable],
            name=f"compiled QUBO linear coefficient for {variable!r}",
        )
        for variable in encoded_variables
    }
    qubo_quadratic: dict[tuple[Variable, Variable], float] = {}
    for raw_pair, contributions in quadratic_terms.items():
        left, right = raw_pair
        pair = (left, right) if encoded_positions[left] < encoded_positions[right] else (right, left)
        coefficient = finite_sum(
            contributions,
            name=f"compiled QUBO quadratic coefficient for {pair!r}",
        )
        if coefficient != 0.0:
            qubo_quadratic[pair] = coefficient
    qubo_quadratic = dict(
        sorted(
            qubo_quadratic.items(),
            key=lambda item: (
                encoded_positions[item[0][0]],
                encoded_positions[item[0][1]],
            ),
        )
    )
    qubo_offset = finite_sum(offset_terms, name="compiled domain-wall QUBO offset")

    neighbors: dict[Variable, set[Variable]] = {variable: set() for variable in encoded_variables}
    for left, right in qubo_quadratic:
        neighbors[left].add(right)
        neighbors[right].add(left)
    maximum_degree = max((len(row) for row in neighbors.values()), default=0)
    color_upper_bound = 0 if not encoded_variables else min(len(encoded_variables), maximum_degree + 1)
    domain_sizes = model.domain_sizes
    overhead = {
        "original_variable_count": len(model.variables),
        "original_total_category_count": sum(domain_sizes),
        "original_joint_state_count": model.joint_state_count,
        "domain_sizes": list(domain_sizes),
        "singleton_variable_count": sum(size == 1 for size in domain_sizes),
        "wall_spin_count": len(encoded_variables),
        "constraint_edge_count": constraint_edge_count,
        "pair_mixed_coefficient_capacity": pair_mixed_coefficient_capacity,
        "qubo_edge_count": len(qubo_quadratic),
        "qubo_maximum_degree": maximum_degree,
        "qubo_color_count_upper_bound": color_upper_bound,
        "color_bound_method": ("loose constructive Delta+1 graph bound; zero for an empty encoded graph"),
        "penalty": canonical_penalty,
        "penalty_selection_status": "caller_supplied_not_proven_sufficient",
        "categorical_offset": model.offset,
        "pair_orientation_policy": model.pair_orientation_policy,
        "reversed_pair_table_count": model.reversed_pair_count,
        "singleton_policy": (
            "one-state variables use zero wall spins and fold their energy into "
            "the offset or neighboring first differences"
        ),
        "mixing_warning": MIXING_WARNING,
        "equation_contract": "EVAL-EQ-020",
        "source": "Jelincic and Walker 2026, arXiv:2606.17327v1, Supplementary Note 1",
    }
    ising_model = compile_qubo(
        {
            "variables": list(encoded_variables),
            "linear": qubo_linear,
            "quadratic": qubo_quadratic,
            "offset": qubo_offset,
        },
        metadata=overhead,
        source_format="categorical_domain_wall_qubo",
    )

    return DomainWallEncoding(
        categorical_model=model,
        penalty=canonical_penalty,
        wall_variables=MappingProxyType(dict(wall_variables)),
        variables=encoded_variables,
        qubo_linear=MappingProxyType(qubo_linear),
        qubo_quadratic=MappingProxyType(qubo_quadratic),
        qubo_offset=qubo_offset,
        ising_model=ising_model,
        overhead_metadata=freeze(overhead),
    )
