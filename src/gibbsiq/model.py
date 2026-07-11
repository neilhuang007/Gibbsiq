"""Ising model IR: variables, linear/quadratic terms, offset.

Convention: E(s)=offset+sum h_i s_i+sum_{i<j} J_ij s_i s_j, s_i in {-1,+1}.
All inputs normalize to this form before sampling/diagnostics.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal, TypeAlias

from gibbsiq._frozen import freeze, thaw

Variable: TypeAlias = Any
SpinSample: TypeAlias = Mapping[Variable, int]
Vartype: TypeAlias = Literal["SPIN", "BINARY"]


def variable_sort_key(variable: Variable) -> tuple[str, str, str]:
    """Deterministic sort key for mixed-type variable labels."""
    cls = type(variable)
    return (cls.__module__, cls.__qualname__, repr(variable))


def variable_index(variables: Sequence[Variable]) -> dict[Variable, int]:
    """Maps variable -> index in canonical order."""
    return {variable: position for position, variable in enumerate(variables)}


def normalize_vartype(vartype: Any) -> Vartype:
    """Normalizes string/dimod vartype to "SPIN"/"BINARY"."""
    name = getattr(vartype, "name", vartype)
    if isinstance(name, str):
        upper = name.upper()
        if upper in {"SPIN", "BINARY"}:
            return upper  # type: ignore[return-value]
    raise ValueError(f"unsupported vartype {vartype!r}; expected SPIN or BINARY")


def finite_float(value: Any, *, name: str) -> float:
    """Casts to float; rejects NaN/inf."""
    coerced = float(value)
    if not math.isfinite(coerced):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return coerced


def finite_sum(values: Sequence[float], *, name: str) -> float:
    """Exact sum via math.fsum; overflow raises ValueError."""
    try:
        total = math.fsum(values)
    except OverflowError as error:
        raise ValueError(f"{name} must be finite; summation overflowed") from error
    return finite_float(total, name=name)


def sample_to_spin(
    sample: Mapping[Variable, int], variables: tuple[Variable, ...], vartype: Vartype
) -> dict[Variable, int]:
    """Validates sample; returns spins keyed by variable."""
    normalized = normalize_vartype(vartype)
    spins: dict[Variable, int] = {}
    for variable in variables:
        if variable not in sample:
            raise ValueError(f"sample is missing variable {variable!r}")
        value = sample[variable]
        if isinstance(value, bool):
            raise ValueError(f"sample value for {variable!r} must not be boolean")
        if normalized == "SPIN":
            if value not in (-1, 1):
                raise ValueError(f"spin value for {variable!r} must be -1 or +1, got {value!r}")
            spins[variable] = int(value)
        elif normalized == "BINARY":
            if value not in (0, 1):
                raise ValueError(f"binary value for {variable!r} must be 0 or 1, got {value!r}")
            spins[variable] = 2 * int(value) - 1
        else:
            raise ValueError(f"cannot convert {vartype!r} samples to spins; expected SPIN or BINARY")
    return spins


def sample_to_spin_values(
    sample: Mapping[Variable, int], variables: tuple[Variable, ...], vartype: Vartype
) -> tuple[int, ...]:
    """Validates sample; returns spins as tuple aligned to variables."""
    normalized = normalize_vartype(vartype)
    values: list[int] = []
    for variable in variables:
        try:
            value = sample[variable]
        except KeyError as error:
            raise ValueError(f"sample is missing variable {variable!r}") from error
        if isinstance(value, bool):
            raise ValueError(f"sample value for {variable!r} must not be boolean")
        if normalized == "SPIN":
            if value != -1 and value != 1:
                raise ValueError(f"spin value for {variable!r} must be -1 or +1, got {value!r}")
            values.append(1 if value == 1 else -1)
        elif normalized == "BINARY":
            if value != 0 and value != 1:
                raise ValueError(f"binary value for {variable!r} must be 0 or 1, got {value!r}")
            values.append(1 if value == 1 else -1)
        else:
            raise ValueError(f"cannot convert {vartype!r} samples to spins; expected SPIN or BINARY")
    return tuple(values)


def spin_to_binary(
    sample: Mapping[Variable, int], variables: tuple[Variable, ...] | None = None
) -> dict[Variable, int]:
    """Spin {-1,+1} -> binary {0,1}."""
    ordered_variables = tuple(sample) if variables is None else variables
    spins = sample_to_spin(sample, ordered_variables, "SPIN")
    return {variable: (spins[variable] + 1) // 2 for variable in ordered_variables}


def binary_to_spin(
    sample: Mapping[Variable, int], variables: tuple[Variable, ...] | None = None
) -> dict[Variable, int]:
    """Binary {0,1} -> spin {-1,+1}."""
    ordered_variables = tuple(sample) if variables is None else variables
    return sample_to_spin(sample, ordered_variables, "BINARY")


@dataclass(frozen=True, slots=True)
class IsingModel:
    """Ising IR. E(s)=offset+sum h_i s_i+sum_{i<j} J_ij s_i s_j, s_i in {-1,+1}."""

    variables: tuple[Variable, ...]
    linear: Mapping[Variable, float]
    quadratic: Mapping[tuple[Variable, Variable], float]
    offset: float = 0.0
    vartype: Literal["SPIN"] = "SPIN"
    source_format: str = "ising"
    variable_order: tuple[Variable, ...] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    _variable_index: Mapping[Variable, int] = field(init=False, repr=False, compare=False)
    _linear_values: tuple[float, ...] | None = field(init=False, repr=False, compare=False)
    _quadratic_edges: tuple[tuple[int, int, float], ...] | None = field(init=False, repr=False, compare=False)
    _neighbors: tuple[tuple[tuple[int, float], ...], ...] | None = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        variables = tuple(self.variables)
        if len(set(variables)) != len(variables):
            raise ValueError("variables must be unique")

        order = variables if self.variable_order is None else tuple(self.variable_order)
        if order != variables:
            raise ValueError("variable_order must match variables exactly")

        index = variable_index(variables)
        for variable in self.linear:
            if variable not in index:
                raise ValueError(f"linear bias for {variable!r} references unknown variable")
        linear = {
            variable: finite_float(self.linear.get(variable, 0.0), name=f"linear bias for {variable!r}")
            for variable in variables
        }
        quadratic: dict[tuple[Variable, Variable], float] = {}
        for pair, coefficient in self.quadratic.items():
            if len(pair) != 2:
                raise ValueError(f"quadratic key {pair!r} must contain two variables")
            left, right = pair
            if left == right:
                raise ValueError("Ising diagonal terms should be folded into offset before IR construction")
            if left not in index or right not in index:
                raise ValueError(f"quadratic pair {pair!r} references unknown variable")
            ordered = (left, right) if index[left] < index[right] else (right, left)
            quadratic[ordered] = quadratic.get(ordered, 0.0) + finite_float(
                coefficient, name=f"quadratic bias for {pair!r}"
            )
        # Sum of finite duplicates can still overflow (e.g. 1e308+1e308); re-check here.
        ordered_quadratic: dict[tuple[Variable, Variable], float] = {}
        for pair, coefficient in sorted(
            quadratic.items(), key=lambda item: (index[item[0][0]], index[item[0][1]])
        ):
            canonical = finite_float(coefficient, name=f"quadratic bias for {pair!r}")
            if canonical != 0.0:
                ordered_quadratic[pair] = canonical

        object.__setattr__(self, "variables", variables)
        object.__setattr__(self, "linear", MappingProxyType(linear))
        object.__setattr__(self, "quadratic", MappingProxyType(ordered_quadratic))
        object.__setattr__(self, "offset", finite_float(self.offset, name="offset"))
        object.__setattr__(self, "variable_order", variables)
        object.__setattr__(
            self,
            "metadata",
            freeze(dict(self.metadata)),
        )
        object.__setattr__(self, "_variable_index", MappingProxyType(index))
        object.__setattr__(self, "_linear_values", None)
        object.__setattr__(self, "_quadratic_edges", None)
        object.__setattr__(self, "_neighbors", None)

    def _linear_cache(self) -> tuple[float, ...]:
        """Lazily cached linear coefficients, ordered by variable index."""
        cached = self._linear_values
        if cached is not None:
            return cached
        cached = tuple(self.linear[variable] for variable in self.variables)
        object.__setattr__(self, "_linear_values", cached)
        return cached

    def _edge_cache(self) -> tuple[tuple[int, int, float], ...]:
        """Lazily cached quadratic terms as (left_idx, right_idx, coefficient)."""
        cached = self._quadratic_edges
        if cached is not None:
            return cached
        cached = tuple(
            (self._variable_index[left], self._variable_index[right], coefficient)
            for (left, right), coefficient in self.quadratic.items()
        )
        object.__setattr__(self, "_quadratic_edges", cached)
        return cached

    def _neighbor_cache(self) -> tuple[tuple[tuple[int, float], ...], ...]:
        """Lazily cached adjacency list, indexed by variable position."""
        cached = self._neighbors
        if cached is not None:
            return cached
        neighbors: list[list[tuple[int, float]]] = [[] for _ in self.variables]
        for left_index, right_index, coefficient in self._edge_cache():
            neighbors[left_index].append((right_index, coefficient))
            neighbors[right_index].append((left_index, coefficient))
        cached = tuple(tuple(row) for row in neighbors)
        object.__setattr__(self, "_neighbors", cached)
        return cached

    @property
    def graph(self) -> tuple[tuple[Variable, Variable], ...]:
        """Quadratic-term edges in canonical variable order."""
        return tuple(self.quadratic)

    def energy(self, sample: Mapping[Variable, int], *, vartype: Vartype = "SPIN") -> float:
        """E(s)=offset+interaction energy, for spin or binary input."""
        spins = sample_to_spin_values(sample, self.variables, vartype)
        return finite_sum(
            [self.offset, self._interaction_energy_from_spins(spins)],
            name="computed energy",
        )

    def interaction_energy(self, sample: Mapping[Variable, int], *, vartype: Vartype = "SPIN") -> float:
        """Offset-free energy (sum h_i s_i+sum J_ij s_i s_j); for stable energy diffs."""
        spins = sample_to_spin_values(sample, self.variables, vartype)
        return self._interaction_energy_from_spins(spins)

    def _interaction_energy_from_spins(self, spins: tuple[int, ...]) -> float:
        terms = [coefficient * spins[position] for position, coefficient in enumerate(self._linear_cache())]
        terms.extend(
            coefficient * spins[left_index] * spins[right_index]
            for left_index, right_index, coefficient in self._edge_cache()
        )
        return finite_sum(terms, name="computed interaction energy")

    def local_field(
        self, variable: Variable, sample: Mapping[Variable, int], *, vartype: Vartype = "SPIN"
    ) -> float:
        """Return ``gamma_i = h_i + sum_j J_ij s_j`` for one variable."""
        try:
            position = self._variable_index[variable]
        except KeyError as error:
            raise ValueError(f"unknown variable {variable!r}") from error
        spins = sample_to_spin_values(sample, self.variables, vartype)
        terms = [self._linear_cache()[position]]
        terms.extend(
            coefficient * spins[neighbor_index]
            for neighbor_index, coefficient in self._neighbor_cache()[position]
        )
        return finite_sum(terms, name=f"local field for {variable!r}")

    def flip_energy_delta(
        self, variable: Variable, sample: Mapping[Variable, int], *, vartype: Vartype = "SPIN"
    ) -> float:
        """Flip delta: E(s_i -> -s_i) - E(s) = -2*s_i*gamma_i."""
        try:
            position = self._variable_index[variable]
        except KeyError as error:
            raise ValueError(f"unknown variable {variable!r}") from error
        spins = sample_to_spin_values(sample, self.variables, vartype)
        gamma = finite_sum(
            [self._linear_cache()[position]]
            + [
                coefficient * spins[neighbor_index]
                for neighbor_index, coefficient in self._neighbor_cache()[position]
            ],
            name=f"local field for {variable!r}",
        )
        return finite_float(
            -2.0 * spins[position] * gamma,
            name=f"flip energy delta for {variable!r}",
        )

    def conditional_probability(
        self,
        variable: Variable,
        sample: Mapping[Variable, int],
        *,
        beta: float = 1.0,
        vartype: Vartype = "SPIN",
    ) -> float:
        """P(s_i=+1 | s_-i) = sigmoid(-2*beta*gamma_i)."""
        canonical_beta = finite_float(beta, name="beta")
        if canonical_beta < 0.0:
            raise ValueError(f"beta must be non-negative, got {beta!r}")
        gamma = self.local_field(variable, sample, vartype=vartype)
        argument = finite_float(
            -2.0 * canonical_beta * gamma,
            name="Gibbs conditional logit",
        )
        if argument >= 0:
            return 1.0 / (1.0 + math.exp(-argument))
        exp_arg = math.exp(argument)
        return exp_arg / (1.0 + exp_arg)

    def to_dict(self) -> dict[str, Any]:
        """Serializes IR to dict; quadratic keys as "left,right" strings."""
        return {
            "variables": list(self.variables),
            "linear": {variable: self.linear[variable] for variable in self.variables},
            "quadratic": {
                f"{left},{right}": coefficient for (left, right), coefficient in self.quadratic.items()
            },
            "offset": self.offset,
            "vartype": self.vartype,
            "graph": [[left, right] for left, right in self.graph],
            "source_format": self.source_format,
            "variable_order": list(self.variables),
            "metadata": thaw(self.metadata),
        }

    def to_dimod(self) -> Any:
        """Returns dimod.BinaryQuadraticModel (requires dimod)."""
        try:
            import dimod  # type: ignore[import-not-found]
        except ImportError as error:  # pragma: no cover - exercised only without optional dep
            raise ImportError("IsingModel.to_dimod() requires the optional 'dimod' package") from error
        return dimod.BinaryQuadraticModel(dict(self.linear), dict(self.quadratic), self.offset, dimod.SPIN)
