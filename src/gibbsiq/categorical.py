"""Immutable pairwise categorical energy models.

The state order is supplied explicitly: variables follow ``variables`` and each
variable's categories follow its domain sequence. Pair tables are stored in
that variable order so later compiler passes never guess an orientation.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, TypeAlias

from gibbsiq._frozen import freeze, thaw
from gibbsiq.model import Variable, finite_float, finite_sum, variable_sort_key

Category: TypeAlias = Any
CategoricalSample: TypeAlias = Mapping[Variable, Category]

PAIR_ORIENTATION_POLICY = (
    "pair tables are stored in variables order; reversed input is transposed; "
    "supplying both orientations is rejected"
)


def _ordered_sequence(value: Any, *, name: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be an ordered list or tuple, got {value!r}")
    return tuple(value)


def _require_hashable(value: Any, *, name: str) -> None:
    try:
        hash(value)
    except TypeError as error:
        raise ValueError(f"{name} must be hashable, got {value!r}") from error


def _finite_table_value(value: Any, *, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number, not boolean")
    return finite_float(value, name=name)


def _format_items(values: set[Any]) -> list[Any]:
    return sorted(values, key=variable_sort_key)


@dataclass(frozen=True, slots=True)
class CategoricalModel:
    """Finite pairwise categorical energy in an explicit deterministic order.

    A missing whole unary table means an all-zero table. A supplied unary or
    pair table must be complete; individual missing entries are rejected.
    Self-pairs are unsupported and should be folded into the unary table first.
    """

    variables: tuple[Variable, ...]
    domains: Mapping[Variable, Sequence[Category]]
    unary: Mapping[Variable, Mapping[Category, Any]] = field(default_factory=dict)
    pairwise: Mapping[
        tuple[Variable, Variable],
        Mapping[tuple[Category, Category], Any],
    ] = field(default_factory=dict)
    offset: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)
    reversed_pair_count: int = field(init=False)
    _domain_indices: Mapping[Variable, Mapping[Category, int]] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        variables = _ordered_sequence(self.variables, name="variables")
        for position, variable in enumerate(variables):
            _require_hashable(variable, name=f"variable at position {position}")
        if len(set(variables)) != len(variables):
            raise ValueError("variables must be unique")
        variable_positions = {variable: position for position, variable in enumerate(variables)}

        if not isinstance(self.domains, Mapping):
            raise ValueError("domains must map every variable to an ordered list or tuple")
        raw_domains = dict(self.domains)
        domain_variables = set(raw_domains)
        expected_variables = set(variables)
        missing_domains = expected_variables - domain_variables
        unknown_domains = domain_variables - expected_variables
        if missing_domains or unknown_domains:
            raise ValueError(
                "domains must match variables exactly; "
                f"missing={_format_items(missing_domains)!r}, "
                f"unknown={_format_items(unknown_domains)!r}"
            )

        domains: dict[Variable, tuple[Category, ...]] = {}
        domain_indices: dict[Variable, Mapping[Category, int]] = {}
        for variable in variables:
            domain = _ordered_sequence(raw_domains[variable], name=f"domain for {variable!r}")
            if not domain:
                raise ValueError(f"domain for {variable!r} must contain at least one category")
            for position, category in enumerate(domain):
                _require_hashable(
                    category,
                    name=f"category at position {position} for {variable!r}",
                )
            if len(set(domain)) != len(domain):
                raise ValueError(f"domain for {variable!r} must contain unique categories")
            domains[variable] = domain
            domain_indices[variable] = MappingProxyType(
                {category: position for position, category in enumerate(domain)}
            )

        if not isinstance(self.unary, Mapping):
            raise ValueError("unary must map variables to complete category tables")
        raw_unary = dict(self.unary)
        unknown_unary = set(raw_unary) - expected_variables
        if unknown_unary:
            raise ValueError(f"unary tables reference unknown variables {_format_items(unknown_unary)!r}")
        unary: dict[Variable, Mapping[Category, float]] = {}
        for variable in variables:
            domain = domains[variable]
            if variable not in raw_unary:
                unary[variable] = MappingProxyType({category: 0.0 for category in domain})
                continue
            raw_table = raw_unary[variable]
            if not isinstance(raw_table, Mapping):
                raise ValueError(f"unary table for {variable!r} must be a mapping")
            table = dict(raw_table)
            expected_categories = set(domain)
            supplied_categories = set(table)
            missing = expected_categories - supplied_categories
            extra = supplied_categories - expected_categories
            if missing or extra:
                raise ValueError(
                    f"unary table for {variable!r} must cover its domain exactly; "
                    f"missing={_format_items(missing)!r}, extra={_format_items(extra)!r}"
                )
            unary[variable] = MappingProxyType(
                {
                    category: _finite_table_value(
                        table[category],
                        name=f"unary value for {variable!r}, {category!r}",
                    )
                    for category in domain
                }
            )

        if not isinstance(self.pairwise, Mapping):
            raise ValueError("pairwise must map variable pairs to complete rectangular tables")
        pairwise: dict[
            tuple[Variable, Variable],
            Mapping[tuple[Category, Category], float],
        ] = {}
        reversed_pair_count = 0
        for raw_pair, raw_table in self.pairwise.items():
            if not isinstance(raw_pair, tuple) or len(raw_pair) != 2:
                raise ValueError(f"pairwise key {raw_pair!r} must be a two-variable tuple")
            raw_left, raw_right = raw_pair
            if raw_left not in variable_positions or raw_right not in variable_positions:
                raise ValueError(f"pairwise key {raw_pair!r} references an unknown variable")
            if raw_left == raw_right:
                raise ValueError(f"pairwise key {raw_pair!r} is a self-pair; fold it into the unary table")
            if not isinstance(raw_table, Mapping):
                raise ValueError(f"pairwise table for {raw_pair!r} must be a mapping")

            raw_left_domain = domains[raw_left]
            raw_right_domain = domains[raw_right]
            table = dict(raw_table)
            expected_entries = {
                (left_category, right_category)
                for left_category in raw_left_domain
                for right_category in raw_right_domain
            }
            supplied_entries = set(table)
            missing_entries = expected_entries - supplied_entries
            extra_entries = supplied_entries - expected_entries
            if missing_entries or extra_entries:
                raise ValueError(
                    f"pairwise table for {raw_pair!r} must cover the domain product exactly; "
                    f"missing={sorted(missing_entries, key=repr)!r}, "
                    f"extra={sorted(extra_entries, key=repr)!r}"
                )

            is_reversed = variable_positions[raw_left] > variable_positions[raw_right]
            pair = (raw_right, raw_left) if is_reversed else (raw_left, raw_right)
            if pair in pairwise:
                raise ValueError(
                    f"pairwise interaction {pair!r} was supplied more than once, "
                    "possibly in both orientations"
                )
            if is_reversed:
                reversed_pair_count += 1
                canonical_table = {
                    (right_category, left_category): _finite_table_value(
                        table[(left_category, right_category)],
                        name=(
                            f"pairwise value for {raw_left!r}, {left_category!r}; "
                            f"{raw_right!r}, {right_category!r}"
                        ),
                    )
                    for left_category in raw_left_domain
                    for right_category in raw_right_domain
                }
            else:
                canonical_table = {
                    (left_category, right_category): _finite_table_value(
                        table[(left_category, right_category)],
                        name=(
                            f"pairwise value for {raw_left!r}, {left_category!r}; "
                            f"{raw_right!r}, {right_category!r}"
                        ),
                    )
                    for left_category in raw_left_domain
                    for right_category in raw_right_domain
                }
            pairwise[pair] = MappingProxyType(canonical_table)

        pairwise = dict(
            sorted(
                pairwise.items(),
                key=lambda item: (
                    variable_positions[item[0][0]],
                    variable_positions[item[0][1]],
                ),
            )
        )

        if isinstance(self.offset, bool):
            raise ValueError("offset must be a finite number, not boolean")
        canonical_offset = finite_float(self.offset, name="categorical offset")
        if not isinstance(self.metadata, Mapping):
            raise ValueError("metadata must be a mapping")

        object.__setattr__(self, "variables", variables)
        object.__setattr__(self, "domains", MappingProxyType(domains))
        object.__setattr__(self, "unary", MappingProxyType(unary))
        object.__setattr__(self, "pairwise", MappingProxyType(pairwise))
        object.__setattr__(self, "offset", canonical_offset)
        object.__setattr__(self, "metadata", freeze(dict(self.metadata)))
        object.__setattr__(self, "reversed_pair_count", reversed_pair_count)
        object.__setattr__(self, "_domain_indices", MappingProxyType(domain_indices))

    @property
    def domain_sizes(self) -> tuple[int, ...]:
        return tuple(len(self.domains[variable]) for variable in self.variables)

    @property
    def joint_state_count(self) -> int:
        return math.prod(self.domain_sizes)

    @property
    def pair_orientation_policy(self) -> str:
        return PAIR_ORIENTATION_POLICY

    def assignment_indices(self, sample: CategoricalSample) -> tuple[int, ...]:
        """Validate one complete assignment and return ordered category indices."""
        if not isinstance(sample, Mapping):
            raise TypeError(f"sample must be a mapping, got {type(sample).__name__}")
        supplied = set(sample)
        expected = set(self.variables)
        missing = expected - supplied
        extra = supplied - expected
        if missing or extra:
            raise ValueError(
                "categorical sample keys must match variables exactly; "
                f"missing={_format_items(missing)!r}, extra={_format_items(extra)!r}"
            )
        indices: list[int] = []
        for variable in self.variables:
            category = sample[variable]
            try:
                position = self._domain_indices[variable][category]
            except (KeyError, TypeError) as error:
                raise ValueError(
                    f"sample category {category!r} is not in the domain for {variable!r}"
                ) from error
            indices.append(position)
        return tuple(indices)

    def energy(self, sample: CategoricalSample) -> float:
        """Evaluate the canonical offset-plus-unary-plus-pair energy."""
        self.assignment_indices(sample)
        terms = [self.offset]
        terms.extend(self.unary[variable][sample[variable]] for variable in self.variables)
        terms.extend(table[(sample[left], sample[right])] for (left, right), table in self.pairwise.items())
        return finite_sum(terms, name="categorical energy")

    def to_dict(self) -> dict[str, Any]:
        """Serialize tables as ordered rows without stringifying arbitrary labels."""
        return {
            "variables": list(self.variables),
            "domains": [
                {
                    "variable": variable,
                    "categories": list(self.domains[variable]),
                }
                for variable in self.variables
            ],
            "unary_tables": [
                {
                    "variable": variable,
                    "values": [self.unary[variable][category] for category in self.domains[variable]],
                }
                for variable in self.variables
            ],
            "pairwise_tables": [
                {
                    "left": left,
                    "right": right,
                    "values": [
                        [table[(left_category, right_category)] for right_category in self.domains[right]]
                        for left_category in self.domains[left]
                    ],
                }
                for (left, right), table in self.pairwise.items()
            ],
            "offset": self.offset,
            "domain_sizes": list(self.domain_sizes),
            "joint_state_count": self.joint_state_count,
            "pair_orientation_policy": self.pair_orientation_policy,
            "reversed_pair_count": self.reversed_pair_count,
            "metadata": thaw(self.metadata),
        }
