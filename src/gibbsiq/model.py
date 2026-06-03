"""Core model containers for Gibbsiq.

The public model IR is intentionally small: every accepted input is normalized
to the project Ising convention before any sampler or diagnostic layer sees it.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias

Variable: TypeAlias = Any
SpinSample: TypeAlias = Mapping[Variable, int]
Vartype: TypeAlias = Literal["SPIN", "BINARY"]


def variable_sort_key(variable: Variable) -> tuple[str, str, str]:
    """Return a deterministic key that can sort mixed Python label types."""
    cls = type(variable)
    return (cls.__module__, cls.__qualname__, repr(variable))


def normalize_vartype(vartype: Any) -> Vartype:
    """Normalize string or dimod-style vartype values to a simple literal."""
    name = getattr(vartype, "name", vartype)
    if isinstance(name, str):
        upper = name.upper()
        if upper in {"SPIN", "BINARY"}:
            return upper  # type: ignore[return-value]
    raise ValueError(f"unsupported vartype {vartype!r}; expected SPIN or BINARY")


def finite_float(value: Any, *, name: str) -> float:
    """Coerce a numeric value and reject NaN or infinite coefficients."""
    coerced = float(value)
    if not math.isfinite(coerced):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return coerced


def sample_to_spin(sample: Mapping[Variable, int], variables: tuple[Variable, ...], vartype: Vartype) -> dict[Variable, int]:
    """Validate a sample and return spin values keyed by model variable."""
    spins: dict[Variable, int] = {}
    for variable in variables:
        if variable not in sample:
            raise ValueError(f"sample is missing variable {variable!r}")
        value = sample[variable]
        if vartype == "SPIN":
            if value not in (-1, 1):
                raise ValueError(f"spin value for {variable!r} must be -1 or +1, got {value!r}")
            spins[variable] = int(value)
        else:
            if value not in (0, 1):
                raise ValueError(f"binary value for {variable!r} must be 0 or 1, got {value!r}")
            spins[variable] = 2 * int(value) - 1
    return spins


def spin_to_binary(sample: Mapping[Variable, int], variables: tuple[Variable, ...] | None = None) -> dict[Variable, int]:
    """Convert a spin sample over ``{-1,+1}`` into a binary sample over ``{0,1}``."""
    ordered_variables = tuple(sample) if variables is None else variables
    spins = sample_to_spin(sample, ordered_variables, "SPIN")
    return {variable: (spins[variable] + 1) // 2 for variable in ordered_variables}


def binary_to_spin(sample: Mapping[Variable, int], variables: tuple[Variable, ...] | None = None) -> dict[Variable, int]:
    """Convert a binary sample over ``{0,1}`` into a spin sample over ``{-1,+1}``."""
    ordered_variables = tuple(sample) if variables is None else variables
    return sample_to_spin(sample, ordered_variables, "BINARY")


@dataclass(frozen=True)
class IsingModel:
    """Backend-independent Ising IR using Gibbsiq's audited sign convention."""

    variables: tuple[Variable, ...]
    linear: Mapping[Variable, float]
    quadratic: Mapping[tuple[Variable, Variable], float]
    offset: float = 0.0
    vartype: Literal["SPIN"] = "SPIN"
    source_format: str = "ising"
    variable_order: tuple[Variable, ...] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        variables = tuple(self.variables)
        if len(set(variables)) != len(variables):
            raise ValueError("variables must be unique")

        order = variables if self.variable_order is None else tuple(self.variable_order)
        if order != variables:
            raise ValueError("variable_order must match variables exactly")

        index = {variable: position for position, variable in enumerate(variables)}
        linear = {variable: finite_float(self.linear.get(variable, 0.0), name=f"linear bias for {variable!r}") for variable in variables}
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
            quadratic[ordered] = quadratic.get(ordered, 0.0) + finite_float(coefficient, name=f"quadratic bias for {pair!r}")
        quadratic = {pair: finite_float(coefficient, name=f"quadratic bias for {pair!r}") for pair, coefficient in quadratic.items()}

        object.__setattr__(self, "variables", variables)
        object.__setattr__(self, "linear", linear)
        object.__setattr__(self, "quadratic", dict(sorted(quadratic.items(), key=lambda item: (index[item[0][0]], index[item[0][1]]))))
        object.__setattr__(self, "offset", finite_float(self.offset, name="offset"))
        object.__setattr__(self, "variable_order", variables)
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def graph(self) -> tuple[tuple[Variable, Variable], ...]:
        """Interaction graph edges in canonical variable order."""
        return tuple(self.quadratic)

    def energy(self, sample: Mapping[Variable, int], *, vartype: Vartype = "SPIN") -> float:
        """Evaluate the model energy for a spin or binary assignment."""
        spins = sample_to_spin(sample, self.variables, normalize_vartype(vartype))
        energy = self.offset
        for variable, coefficient in self.linear.items():
            energy += coefficient * spins[variable]
        for (left, right), coefficient in self.quadratic.items():
            energy += coefficient * spins[left] * spins[right]
        return energy

    def local_field(self, variable: Variable, sample: Mapping[Variable, int], *, vartype: Vartype = "SPIN") -> float:
        """Return ``gamma_i = h_i + sum_j J_ij s_j`` for one variable."""
        if variable not in self.variables:
            raise ValueError(f"unknown variable {variable!r}")
        spins = sample_to_spin(sample, self.variables, normalize_vartype(vartype))
        gamma = self.linear[variable]
        for (left, right), coefficient in self.quadratic.items():
            if left == variable:
                gamma += coefficient * spins[right]
            elif right == variable:
                gamma += coefficient * spins[left]
        return gamma

    def conditional_probability(self, variable: Variable, sample: Mapping[Variable, int], *, beta: float = 1.0, vartype: Vartype = "SPIN") -> float:
        """Return ``P(s_i=+1 | s_-i)`` under the audited Gibbs sign."""
        gamma = self.local_field(variable, sample, vartype=vartype)
        argument = -2.0 * float(beta) * gamma
        if argument >= 0:
            return 1.0 / (1.0 + math.exp(-argument))
        exp_arg = math.exp(argument)
        return exp_arg / (1.0 + exp_arg)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the IR with stable string pair keys for JSON fixtures."""
        return {
            "variables": list(self.variables),
            "linear": {variable: self.linear[variable] for variable in self.variables},
            "quadratic": {f"{left},{right}": coefficient for (left, right), coefficient in self.quadratic.items()},
            "offset": self.offset,
            "vartype": self.vartype,
            "graph": [[left, right] for left, right in self.graph],
            "source_format": self.source_format,
            "variable_order": list(self.variable_order or self.variables),
            "metadata": dict(self.metadata),
        }

    def to_dimod(self) -> Any:
        """Return a dimod BinaryQuadraticModel when dimod is installed."""
        try:
            import dimod  # type: ignore[import-not-found]
        except ImportError as error:  # pragma: no cover - exercised only without optional dep
            raise ImportError("IsingModel.to_dimod() requires the optional 'dimod' package") from error
        return dimod.BinaryQuadraticModel(dict(self.linear), dict(self.quadratic), self.offset, dimod.SPIN)
