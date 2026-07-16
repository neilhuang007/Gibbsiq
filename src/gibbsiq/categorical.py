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

from gibbsiq._frozen import freeze, freeze_json_evidence, thaw
from gibbsiq.model import (
    Variable,
    exact_mapping_index,
    exact_mapping_key,
    exact_variable_position,
    finite_float,
    finite_sum,
    variable_sort_key,
)

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


def _typed_category_key(value: Category) -> tuple[type[Any], Category]:
    return type(value), value


def _typed_pair_key(
    value: Any,
) -> tuple[tuple[type[Any], Category], tuple[type[Any], Category]] | None:
    if not isinstance(value, tuple) or len(value) != 2:
        return None
    return _typed_category_key(value[0]), _typed_category_key(value[1])


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
    _domain_indices: Mapping[Variable, Mapping[tuple[type[Any], Category], int]] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _variable_positions: Mapping[Variable, int] = field(
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
        exact_mapping_index(self.domains)
        raw_domains = dict(self.domains)
        raw_domain_key_index = exact_mapping_index(raw_domains)
        missing_domains = set()
        for variable in variables:
            try:
                exact_mapping_key(raw_domains, variable, raw_domain_key_index)
            except KeyError:
                missing_domains.add(variable)
        unknown_domains = set()
        for candidate in raw_domains:
            try:
                exact_variable_position(candidate, variables, variable_positions)
            except KeyError:
                unknown_domains.add(candidate)
        if missing_domains or unknown_domains:
            raise ValueError(
                "domains must match variables exactly; "
                f"missing={_format_items(missing_domains)!r}, "
                f"unknown={_format_items(unknown_domains)!r}"
            )

        domains: dict[Variable, tuple[Category, ...]] = {}
        domain_indices: dict[
            Variable,
            Mapping[tuple[type[Any], Category], int],
        ] = {}
        for variable_position, variable in enumerate(variables):
            domain = _ordered_sequence(
                raw_domains[exact_mapping_key(raw_domains, variable, raw_domain_key_index)],
                name=f"domain at variable position {variable_position}",
            )
            if not domain:
                raise ValueError(f"domain for {variable!r} must contain at least one category")
            for position, category in enumerate(domain):
                _require_hashable(
                    category,
                    name=(f"category at position {position} for variable position {variable_position}"),
                )
            if len(set(domain)) != len(domain):
                raise ValueError(f"domain for {variable!r} must contain unique categories")
            domains[variable] = domain
            domain_indices[variable] = MappingProxyType(
                {(type(category), category): position for position, category in enumerate(domain)}
            )

        if not isinstance(self.unary, Mapping):
            raise ValueError("unary must map variables to complete category tables")
        exact_mapping_index(self.unary)
        raw_unary = dict(self.unary)
        raw_unary_key_index = exact_mapping_index(raw_unary)
        unknown_unary = set()
        for candidate in raw_unary:
            try:
                exact_variable_position(candidate, variables, variable_positions)
            except KeyError:
                unknown_unary.add(candidate)
        if unknown_unary:
            raise ValueError(f"unary tables reference unknown variables {_format_items(unknown_unary)!r}")
        unary: dict[Variable, Mapping[Category, float]] = {}
        for variable_position, variable in enumerate(variables):
            domain = domains[variable]
            try:
                unary_key = exact_mapping_key(raw_unary, variable, raw_unary_key_index)
            except KeyError:
                unary[variable] = MappingProxyType({category: 0.0 for category in domain})
                continue
            raw_table = raw_unary[unary_key]
            if not isinstance(raw_table, Mapping):
                raise ValueError(f"unary table for {variable!r} must be a mapping")
            table = dict(raw_table)
            expected_categories = {_typed_category_key(category): category for category in domain}
            supplied_categories = {_typed_category_key(category): category for category in table}
            missing = [
                expected_categories[key] for key in expected_categories.keys() - supplied_categories.keys()
            ]
            extra = [
                supplied_categories[key] for key in supplied_categories.keys() - expected_categories.keys()
            ]
            if missing or extra:
                raise ValueError(
                    f"unary table for {variable!r} must cover its domain exactly; "
                    f"missing={sorted(missing, key=variable_sort_key)!r}, "
                    f"extra={sorted(extra, key=variable_sort_key)!r}"
                )
            unary[variable] = MappingProxyType(
                {
                    category: _finite_table_value(
                        table[category],
                        name=(
                            f"unary value at variable position {variable_position}, "
                            f"category position {category_position}"
                        ),
                    )
                    for category_position, category in enumerate(domain)
                }
            )

        if not isinstance(self.pairwise, Mapping):
            raise ValueError("pairwise must map variable pairs to complete rectangular tables")
        exact_mapping_index(self.pairwise)
        pairwise: dict[
            tuple[Variable, Variable],
            Mapping[tuple[Category, Category], float],
        ] = {}
        reversed_pair_count = 0
        for raw_pair, raw_table in self.pairwise.items():
            if not isinstance(raw_pair, tuple) or len(raw_pair) != 2:
                raise ValueError(f"pairwise key {raw_pair!r} must be a two-variable tuple")
            raw_left, raw_right = raw_pair
            try:
                raw_left_position = exact_variable_position(raw_left, variables, variable_positions)
                raw_right_position = exact_variable_position(raw_right, variables, variable_positions)
            except KeyError:
                raise ValueError(f"pairwise key {raw_pair!r} references an unknown variable") from None
            raw_left = variables[raw_left_position]
            raw_right = variables[raw_right_position]
            if raw_left_position == raw_right_position:
                raise ValueError(f"pairwise key {raw_pair!r} is a self-pair; fold it into the unary table")
            if not isinstance(raw_table, Mapping):
                raise ValueError(f"pairwise table for {raw_pair!r} must be a mapping")

            raw_left_domain = domains[raw_left]
            raw_right_domain = domains[raw_right]
            table = dict(raw_table)
            expected_entries = {
                (
                    _typed_category_key(left_category),
                    _typed_category_key(right_category),
                ): (left_category, right_category)
                for left_category in raw_left_domain
                for right_category in raw_right_domain
            }
            supplied_entries = {}
            malformed_entries = []
            for entry in table:
                typed_key = _typed_pair_key(entry)
                if typed_key is None:
                    malformed_entries.append(entry)
                else:
                    supplied_entries[typed_key] = entry
            missing_entries = [
                expected_entries[key] for key in expected_entries.keys() - supplied_entries.keys()
            ]
            extra_entries = malformed_entries + [
                supplied_entries[key] for key in supplied_entries.keys() - expected_entries.keys()
            ]
            if missing_entries or extra_entries:
                raise ValueError(
                    f"pairwise table for {raw_pair!r} must cover the domain product exactly; "
                    f"missing={sorted(missing_entries, key=repr)!r}, "
                    f"extra={sorted(extra_entries, key=repr)!r}"
                )

            is_reversed = raw_left_position > raw_right_position
            pair = (raw_right, raw_left) if is_reversed else (raw_left, raw_right)
            if pair in pairwise:
                raise ValueError(
                    f"pairwise interaction {pair!r} was supplied more than once, "
                    "possibly in both orientations"
                )
            if is_reversed:
                reversed_pair_count += 1
            canonical_table = {
                (
                    (right_category, left_category) if is_reversed else (left_category, right_category)
                ): _finite_table_value(
                    table[(left_category, right_category)],
                    name=(
                        "pairwise value at variable positions "
                        f"{raw_left_position}, {raw_right_position}; "
                        "category positions "
                        f"{left_category_position}, {right_category_position}"
                    ),
                )
                for left_category_position, left_category in enumerate(raw_left_domain)
                for right_category_position, right_category in enumerate(raw_right_domain)
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
        object.__setattr__(self, "_variable_positions", MappingProxyType(variable_positions))

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
        sample_key_index = exact_mapping_index(sample)
        missing = set()
        for variable in self.variables:
            try:
                exact_mapping_key(sample, variable, sample_key_index)
            except KeyError:
                missing.add(variable)
        extra = set()
        for candidate in sample:
            try:
                exact_variable_position(candidate, self.variables, self._variable_positions)
            except KeyError:
                extra.add(candidate)
        if missing or extra:
            raise ValueError(
                "categorical sample keys must match variables exactly; "
                f"missing={_format_items(missing)!r}, extra={_format_items(extra)!r}"
            )
        indices: list[int] = []
        for variable in self.variables:
            category = sample[exact_mapping_key(sample, variable, sample_key_index)]
            try:
                position = self._domain_indices[variable][(type(category), category)]
            except (KeyError, TypeError) as error:
                raise ValueError(
                    f"sample category {category!r} is not in the domain for {variable!r}"
                ) from error
            indices.append(position)
        return tuple(indices)

    def energy(self, sample: CategoricalSample) -> float:
        """Evaluate the canonical offset-plus-unary-plus-pair energy."""
        category_indices = self.assignment_indices(sample)
        canonical_categories = tuple(
            self.domains[variable][category_indices[position]]
            for position, variable in enumerate(self.variables)
        )
        terms = [self.offset]
        terms.extend(
            self.unary[variable][canonical_categories[position]]
            for position, variable in enumerate(self.variables)
        )
        terms.extend(
            table[
                (
                    canonical_categories[self._variable_positions[left]],
                    canonical_categories[self._variable_positions[right]],
                )
            ]
            for (left, right), table in self.pairwise.items()
        )
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
            "metadata": thaw(freeze_json_evidence(self.metadata, name="metadata")),
        }
