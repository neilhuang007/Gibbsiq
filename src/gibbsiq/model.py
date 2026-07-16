"""Ising model IR: variables, linear/quadratic terms, offset.

Convention: E(s)=offset+sum h_i s_i+sum_{i<j} J_ij s_i s_j, s_i in {-1,+1}.
All inputs normalize to this form before sampling/diagnostics.
"""

from __future__ import annotations

import base64
import binascii
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal, TypeAlias

from gibbsiq._frozen import freeze, freeze_json_evidence, thaw

Variable: TypeAlias = Any
SpinSample: TypeAlias = Mapping[Variable, int]
Vartype: TypeAlias = Literal["SPIN", "BINARY"]
ISING_MODEL_SCHEMA_VERSION = 2
LEGACY_ISING_MODEL_SCHEMA_VERSION = 1


def _encoded_label_sort_key(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def encode_variable_label(variable: Variable) -> dict[str, Any]:
    """Encode a supported hashable label without JSON key coercion or repr fallback."""
    variable_type = type(variable)
    if variable is None:
        return {"kind": "none"}
    if variable_type is bool:
        return {"kind": "bool", "value": variable}
    if variable_type is int:
        return {"kind": "int", "value": str(variable)}
    if variable_type is float:
        if not math.isfinite(variable):
            raise TypeError("unsupported variable label: float labels must be finite")
        return {"kind": "float", "value": variable.hex()}
    if variable_type is str:
        return {"kind": "str", "value": variable}
    if variable_type is bytes:
        return {
            "kind": "bytes",
            "value": base64.b64encode(variable).decode("ascii"),
        }
    if variable_type is tuple:
        return {
            "kind": "tuple",
            "items": [encode_variable_label(item) for item in variable],
        }
    if variable_type is frozenset:
        items = [encode_variable_label(item) for item in variable]
        items.sort(key=_encoded_label_sort_key)
        return {"kind": "frozenset", "items": items}
    raise TypeError(
        "unsupported variable label type "
        f"{variable_type.__module__}.{variable_type.__qualname__}; "
        "supported labels are None, bool, int, finite float, str, bytes, tuple, and frozenset"
    )


def decode_variable_label(payload: Any) -> Variable:
    """Decode :func:`encode_variable_label` output and reject malformed records."""
    if not isinstance(payload, Mapping):
        raise ValueError("encoded variable label must be a mapping")
    kind = payload.get("kind")
    if kind == "none":
        if set(payload) != {"kind"}:
            raise ValueError("encoded none label contains unexpected fields")
        return None
    if kind == "bool":
        value = payload.get("value")
        if type(value) is not bool:
            raise ValueError("encoded bool label must contain a boolean value")
        return value
    if kind == "int":
        value = payload.get("value")
        if not isinstance(value, str):
            raise ValueError("encoded int label must contain a decimal string")
        try:
            decoded = int(value)
        except ValueError as error:
            raise ValueError("encoded int label contains an invalid decimal string") from error
        if str(decoded) != value:
            raise ValueError("encoded int label is not in canonical decimal form")
        return decoded
    if kind == "float":
        value = payload.get("value")
        if not isinstance(value, str):
            raise ValueError("encoded float label must contain a hexadecimal string")
        try:
            decoded_float = float.fromhex(value)
        except ValueError as error:
            raise ValueError("encoded float label contains an invalid hexadecimal string") from error
        if not math.isfinite(decoded_float) or decoded_float.hex() != value:
            raise ValueError("encoded float label must be finite and canonical")
        return decoded_float
    if kind == "str":
        value = payload.get("value")
        if not isinstance(value, str):
            raise ValueError("encoded str label must contain a string value")
        return value
    if kind == "bytes":
        value = payload.get("value")
        if not isinstance(value, str):
            raise ValueError("encoded bytes label must contain a base64 string")
        try:
            return base64.b64decode(value, validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError("encoded bytes label contains invalid base64") from error
    if kind in {"tuple", "frozenset"}:
        items = payload.get("items")
        if not isinstance(items, list):
            raise ValueError(f"encoded {kind} label must contain an items list")
        decoded_items = [decode_variable_label(item) for item in items]
        if kind == "tuple":
            return tuple(decoded_items)
        try:
            decoded_set = frozenset(decoded_items)
        except TypeError as error:
            raise ValueError("encoded frozenset label contains an unhashable item") from error
        if len(decoded_set) != len(decoded_items):
            raise ValueError("encoded frozenset label contains duplicate items")
        return decoded_set
    raise ValueError(f"unsupported encoded variable label kind {kind!r}")


def canonical_variable_sort_key(variable: Variable) -> str:
    """Return a stable typed key, failing for labels without a canonical encoding."""
    return _encoded_label_sort_key(encode_variable_label(variable))


def legacy_wire_safe(variables: Sequence[Variable]) -> bool:
    """Return whether labels are lossless in the version-1 object-key schema."""
    return all(type(variable) is str and "," not in variable for variable in variables)


def exact_variable_order(value: Any, variables: Sequence[Variable]) -> bool:
    """Return whether evidence repeats ``variables`` without equality-type aliases."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return False
    return len(value) == len(variables) and all(
        exact_label_equal(candidate, variable) for candidate, variable in zip(value, variables)
    )


def exact_label_equal(candidate: Any, variable: Variable) -> bool:
    """Compare labels recursively without bool/int or other equality aliases."""
    if type(variable) is tuple:
        return (
            type(candidate) is tuple
            and len(candidate) == len(variable)
            and all(exact_label_equal(child, expected) for child, expected in zip(candidate, variable))
        )
    if type(variable) is frozenset:
        if type(candidate) is not frozenset or len(candidate) != len(variable):
            return False
        unmatched = list(candidate)
        for expected in variable:
            for position, child in enumerate(unmatched):
                if exact_label_equal(child, expected):
                    unmatched.pop(position)
                    break
            else:
                return False
        return True
    try:
        return type(candidate) is type(variable) and bool(candidate == variable)
    except (TypeError, ValueError):
        return False


def exact_variable_position(
    variable: Variable,
    variables: Sequence[Variable],
    index: Mapping[Variable, int] | None = None,
) -> int:
    """Return the exact typed-label position, rejecting equality aliases."""
    if index is not None:
        try:
            position = index[variable]
        except (KeyError, TypeError) as error:
            raise KeyError(variable) from error
        if exact_label_equal(variable, variables[position]):
            return position
        raise KeyError(variable)
    for position, expected in enumerate(variables):
        if exact_label_equal(variable, expected):
            return position
    raise KeyError(variable)


def exact_label_key(value: Variable) -> tuple[Any, Any]:
    """Return a hashable recursive type-and-value key for an exact label."""
    if type(value) is tuple:
        return (tuple, tuple(exact_label_key(child) for child in value))
    if type(value) is frozenset:
        return (frozenset, frozenset(exact_label_key(child) for child in value))
    try:
        hash(value)
    except TypeError as error:
        raise TypeError(f"variable label {value!r} must be hashable") from error
    return (type(value), value)


def exact_mapping_index(mapping: Mapping[Any, Any]) -> dict[tuple[Any, Any], Any]:
    """Index mapping keys by recursive typed identity in one pass."""
    index: dict[tuple[Any, Any], Any] = {}
    for candidate in mapping:
        key = exact_label_key(candidate)
        if key in index:
            raise ValueError(f"mapping contains duplicate exact key {candidate!r}")
        index[key] = candidate
    return index


def exact_mapping_key(
    mapping: Mapping[Any, Any],
    variable: Variable,
    key_index: Mapping[tuple[Any, Any], Any] | None = None,
) -> Any:
    """Return the actual mapping key exactly matching ``variable``."""
    if key_index is not None:
        try:
            candidate = key_index[exact_label_key(variable)]
        except (KeyError, TypeError) as error:
            raise KeyError(variable) from error
        if exact_label_equal(candidate, variable):
            return candidate
        raise KeyError(variable)
    matches = [candidate for candidate in mapping if exact_label_equal(candidate, variable)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise KeyError(variable)
    raise ValueError(f"mapping contains multiple exact keys for variable {variable!r}")


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
    sample_key_index = exact_mapping_index(sample)
    for variable in variables:
        try:
            sample_key = exact_mapping_key(sample, variable, sample_key_index)
        except KeyError:
            raise ValueError(f"sample is missing variable {variable!r}") from None
        value = sample[sample_key]
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
    sample_key_index = exact_mapping_index(sample)
    for variable in variables:
        try:
            value = sample[exact_mapping_key(sample, variable, sample_key_index)]
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
    _metadata_has_canonical_variable_order: bool = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        variables = tuple(self.variables)
        if len(set(variables)) != len(variables):
            raise ValueError("variables must be unique")
        if type(self.vartype) is not str or self.vartype != "SPIN":
            raise ValueError("IsingModel vartype must be exactly 'SPIN'")

        order = variables if self.variable_order is None else tuple(self.variable_order)
        if not exact_variable_order(order, variables):
            raise ValueError("variable_order must match variables exactly")

        exact_mapping_index(self.linear)
        exact_mapping_index(self.quadratic)
        index = variable_index(variables)
        for variable in self.linear:
            try:
                exact_variable_position(variable, variables, index)
            except KeyError:
                raise ValueError(f"linear bias for {variable!r} references unknown variable") from None
        linear = {
            variable: finite_float(
                self.linear.get(variable, 0.0),
                name=f"linear bias at variable position {position}",
            )
            for position, variable in enumerate(variables)
        }
        quadratic_terms: dict[tuple[Variable, Variable], list[float]] = {}
        for interaction_position, (pair, coefficient) in enumerate(self.quadratic.items()):
            if len(pair) != 2:
                raise ValueError(f"quadratic key {pair!r} must contain two variables")
            left, right = pair
            try:
                left_position = exact_variable_position(left, variables, index)
                right_position = exact_variable_position(right, variables, index)
            except KeyError:
                raise ValueError(f"quadratic pair {pair!r} references unknown variable") from None
            if left_position == right_position:
                raise ValueError("Ising diagonal terms should be folded into offset before IR construction")
            ordered_positions = (
                (left_position, right_position)
                if left_position < right_position
                else (right_position, left_position)
            )
            ordered = (variables[ordered_positions[0]], variables[ordered_positions[1]])
            quadratic_terms.setdefault(ordered, []).append(
                finite_float(
                    coefficient,
                    name=f"quadratic bias at interaction position {interaction_position}",
                )
            )
        quadratic = {
            pair: finite_sum(values, name=f"canonical quadratic bias for {pair!r}")
            for pair, values in quadratic_terms.items()
        }
        ordered_quadratic: dict[tuple[Variable, Variable], float] = {}
        for interaction_position, (pair, coefficient) in enumerate(
            sorted(quadratic.items(), key=lambda item: (index[item[0][0]], index[item[0][1]]))
        ):
            canonical = finite_float(
                coefficient,
                name=f"canonical quadratic bias at interaction position {interaction_position}",
            )
            if canonical != 0.0:
                ordered_quadratic[pair] = canonical

        object.__setattr__(self, "variables", variables)
        object.__setattr__(self, "linear", MappingProxyType(linear))
        object.__setattr__(self, "quadratic", MappingProxyType(ordered_quadratic))
        object.__setattr__(self, "offset", finite_float(self.offset, name="offset"))
        object.__setattr__(self, "variable_order", variables)
        metadata_has_canonical_variable_order = exact_variable_order(
            self.metadata.get("variable_order"),
            variables,
        )
        object.__setattr__(
            self,
            "metadata",
            freeze(dict(self.metadata)),
        )
        object.__setattr__(self, "_variable_index", MappingProxyType(index))
        object.__setattr__(self, "_linear_values", None)
        object.__setattr__(self, "_quadratic_edges", None)
        object.__setattr__(self, "_neighbors", None)
        object.__setattr__(
            self,
            "_metadata_has_canonical_variable_order",
            metadata_has_canonical_variable_order,
        )

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
            position = exact_variable_position(variable, self.variables, self._variable_index)
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
            position = exact_variable_position(variable, self.variables, self._variable_index)
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
        """Serialize the IR, using typed positional rows whenever legacy keys are lossy."""
        if legacy_wire_safe(self.variables):
            metadata = thaw(freeze_json_evidence(self.metadata, name="metadata"))
            return {
                "schema_version": LEGACY_ISING_MODEL_SCHEMA_VERSION,
                "variables": list(self.variables),
                "linear": {variable: self.linear[variable] for variable in self.variables},
                "quadratic": {
                    f"{left},{right}": coefficient for (left, right), coefficient in self.quadratic.items()
                },
                "graph": [[left, right] for left, right in self.graph],
                "variable_order": list(self.variables),
                "offset": self.offset,
                "vartype": self.vartype,
                "source_format": self.source_format,
                "metadata": metadata,
            }

        positions = variable_index(self.variables)
        encoded_variables = [encode_variable_label(variable) for variable in self.variables]
        metadata_source = dict(self.metadata)
        includes_variable_order = self._metadata_has_canonical_variable_order
        if includes_variable_order:
            metadata_source.pop("variable_order")
        metadata = thaw(freeze_json_evidence(metadata_source, name="metadata"))
        if includes_variable_order:
            metadata["variable_order"] = encoded_variables
        return {
            "schema_version": ISING_MODEL_SCHEMA_VERSION,
            "variables": encoded_variables,
            "linear": [self.linear[variable] for variable in self.variables],
            "quadratic": [
                {
                    "left": positions[left],
                    "right": positions[right],
                    "coefficient": coefficient,
                }
                for (left, right), coefficient in self.quadratic.items()
            ],
            "graph": [[positions[left], positions[right]] for left, right in self.graph],
            "variable_order": encoded_variables,
            "offset": self.offset,
            "vartype": self.vartype,
            "source_format": self.source_format,
            "metadata": metadata,
        }

    def to_dimod(self) -> Any:
        """Returns dimod.BinaryQuadraticModel (requires dimod)."""
        try:
            import dimod  # type: ignore[import-not-found]
        except ImportError as error:  # pragma: no cover - exercised only without optional dep
            raise ImportError("IsingModel.to_dimod() requires the optional 'dimod' package") from error
        return dimod.BinaryQuadraticModel(dict(self.linear), dict(self.quadratic), self.offset, dimod.SPIN)
