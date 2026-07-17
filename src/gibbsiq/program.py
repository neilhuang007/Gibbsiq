"""Immutable target-independent thermodynamic program envelope.

The envelope assigns logical variables free or clamped roles without changing
the source model.  Projection applies the exact substitutions audited in
EVAL-EQ-023 and returns the same logical model type.
"""

from __future__ import annotations

import base64
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, TypeAlias

from gibbsiq._frozen import freeze
from gibbsiq.categorical import CategoricalModel
from gibbsiq.model import (
    IsingModel,
    Variable,
    decode_variable_label,
    encode_variable_label,
    exact_label_equal,
    exact_mapping_index,
    exact_mapping_key,
    exact_variable_position,
    finite_float,
    finite_sum,
    variable_index,
)

PROGRAM_SCHEMA_VERSION = 1

LogicalModel: TypeAlias = IsingModel | CategoricalModel


def _records(value: Any, *, name: str) -> tuple[tuple[Any, Any], ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        return tuple(value.items())
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a mapping or an ordered sequence of pairs")
    records: list[tuple[Any, Any]] = []
    for position, record in enumerate(value):
        if (
            isinstance(record, (str, bytes, bytearray))
            or not isinstance(record, Sequence)
            or len(record) != 2
        ):
            raise ValueError(f"{name} record {position} must contain exactly two values")
        records.append((record[0], record[1]))
    return tuple(records)


def _same_exact_value(left: Any, right: Any) -> bool:
    return exact_label_equal(left, right)


def _has_exact_mapping_key(
    mapping: Mapping[Any, Any],
    variable: Variable,
    key_index: Mapping[tuple[Any, Any], Any],
) -> bool:
    try:
        exact_mapping_key(mapping, variable, key_index)
    except KeyError:
        return False
    return True


def _normalize_clamps(
    model: LogicalModel,
    clamps: Any,
) -> tuple[tuple[Variable, ...], tuple[Variable, ...], Mapping[Variable, Any]]:
    positions = variable_index(model.variables)
    supplied: dict[Variable, Any] = {}
    for variable, value in _records(clamps, name="clamps"):
        try:
            variable_position = exact_variable_position(variable, model.variables, positions)
        except TypeError as error:
            raise ValueError("unknown clamp variable; clamp variables must be hashable") from error
        except KeyError:
            raise ValueError("unknown clamp variable") from None
        variable = model.variables[variable_position]
        if variable in supplied:
            if _same_exact_value(supplied[variable], value):
                raise ValueError("duplicate clamp record")
            raise ValueError("conflicting clamps for one variable")

        if isinstance(model, IsingModel):
            if isinstance(value, bool):
                raise ValueError("Ising clamp value must not be boolean")
            if type(value) is not int or value not in (-1, 1):
                raise ValueError("Ising clamp value is out of domain; expected -1 or +1")
            canonical_value: Any = value
        else:
            domain = model.domains[variable]
            exact_matches = [category for category in domain if exact_label_equal(value, category)]
            if not exact_matches:
                if isinstance(value, bool) and any(
                    not isinstance(category, bool) and category == value for category in domain
                ):
                    raise ValueError("categorical clamp is a boolean alias for a domain value")
                raise ValueError("categorical clamp value is out of domain")
            canonical_value = exact_matches[0]
        supplied[variable] = canonical_value

    clamped = tuple(variable for variable in model.variables if variable in supplied)
    free = tuple(variable for variable in model.variables if variable not in supplied)
    ordered = MappingProxyType({variable: supplied[variable] for variable in clamped})
    return free, clamped, ordered


def _normalize_coordinates(
    model: LogicalModel,
    coordinates: Any,
) -> tuple[Mapping[Variable, tuple[float, ...]], int]:
    if coordinates is None:
        return MappingProxyType({}), 0
    if not isinstance(coordinates, Mapping):
        raise TypeError("coordinates must be a mapping")
    exact_mapping_index(coordinates)
    positions = variable_index(model.variables)
    normalized: dict[Variable, tuple[float, ...]] = {}
    dimension: int | None = None
    for variable, raw_coordinate in coordinates.items():
        try:
            variable_position = exact_variable_position(variable, model.variables, positions)
        except TypeError as error:
            raise ValueError("unknown coordinate variable") from error
        except KeyError:
            raise ValueError("unknown coordinate variable") from None
        variable = model.variables[variable_position]
        if (
            isinstance(raw_coordinate, (str, bytes, bytearray))
            or not isinstance(raw_coordinate, Sequence)
            or not raw_coordinate
        ):
            raise ValueError("logical coordinates must be a non-empty ordered sequence")
        coordinate: list[float] = []
        for component in raw_coordinate:
            if isinstance(component, bool):
                raise ValueError("logical coordinate components must not be boolean")
            try:
                value = float(component)
            except (TypeError, ValueError) as error:
                raise ValueError("logical coordinate components must be finite numbers") from error
            if not math.isfinite(value):
                raise ValueError("logical coordinate components must be finite")
            coordinate.append(value)
        if dimension is None:
            dimension = len(coordinate)
        elif len(coordinate) != dimension:
            raise ValueError("all logical coordinates must have the same dimension")
        normalized[variable] = tuple(coordinate)
    ordered = {variable: normalized[variable] for variable in model.variables if variable in normalized}
    return MappingProxyType(ordered), 0 if dimension is None else dimension


def _normalize_observations(
    model: LogicalModel,
    clamped: tuple[Variable, ...],
    observations: Any,
) -> Mapping[Variable, Any]:
    if observations is None:
        return MappingProxyType({})
    if not isinstance(observations, Mapping):
        raise TypeError("observations must be a mapping")
    positions = variable_index(model.variables)
    observation_key_index = exact_mapping_index(observations)
    clamped_set = set(clamped)
    for variable in observations:
        try:
            variable_position = exact_variable_position(variable, model.variables, positions)
        except TypeError as error:
            raise ValueError("unknown observation variable") from error
        except KeyError:
            raise ValueError("unknown observation variable") from None
        variable = model.variables[variable_position]
        if variable not in clamped_set:
            raise ValueError("observation variable must be clamped")
    return freeze(
        {
            variable: observations[exact_mapping_key(observations, variable, observation_key_index)]
            for variable in model.variables
            if _has_exact_mapping_key(observations, variable, observation_key_index)
        }
    )


def _factor_ids(model: LogicalModel) -> tuple[str, ...]:
    positions = variable_index(model.variables)
    if isinstance(model, IsingModel):
        identifiers = [f"linear:{position}" for position in range(len(model.variables))]
        identifiers.extend(
            f"quadratic:{positions[left]}:{positions[right]}" for left, right in model.quadratic
        )
        return tuple(identifiers)
    identifiers = [f"unary:{position}" for position in range(len(model.variables))]
    identifiers.extend(f"pairwise:{positions[left]}:{positions[right]}" for left, right in model.pairwise)
    return tuple(identifiers)


def _normalize_factor_sources(
    model: LogicalModel,
    factor_sources: Any,
) -> Mapping[str, str]:
    if factor_sources is None:
        factor_sources = {}
    if not isinstance(factor_sources, Mapping):
        raise TypeError("factor_sources must be a mapping")
    exact_mapping_index(factor_sources)
    valid = _factor_ids(model)
    valid_set = set(valid)
    unknown = [identifier for identifier in factor_sources if identifier not in valid_set]
    if unknown:
        raise ValueError("factor_sources contains an unknown factor identity")
    normalized: dict[str, str] = {}
    for identifier in valid:
        source = factor_sources.get(identifier, identifier)
        if not isinstance(source, str) or not source:
            raise ValueError("factor source identities must be non-empty strings")
        normalized[identifier] = source
    return MappingProxyType(normalized)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _unsupported_value(value: Any, *, label: bool) -> TypeError:
    cls = type(value)
    role = "label" if label else "metadata value"
    return TypeError(f"unsupported {role} type {cls.__module__}.{cls.__qualname__}")


def _encode_value(value: Any, *, label: bool = False) -> dict[str, Any]:
    if label:
        return encode_variable_label(value)
    value_type = type(value)
    if value is None:
        return {"kind": "none"}
    if value_type is bool:
        return {"kind": "bool", "value": value}
    if value_type is int:
        return {"kind": "int", "value": str(value)}
    if value_type is float:
        if not math.isfinite(value):
            raise ValueError("serialized floating-point values must be finite")
        return {"kind": "float", "value": value.hex()}
    if value_type is str:
        return {"kind": "str", "value": value}
    if value_type is bytes:
        return {
            "kind": "bytes",
            "value": base64.b64encode(value).decode("ascii"),
        }
    if value_type is frozenset:
        items = [_encode_value(item, label=True) for item in value]
        items.sort(key=_canonical_json)
        return {"kind": "frozenset", "items": items}
    if isinstance(value, Mapping):
        items = [
            {
                "key": _encode_value(key, label=True),
                "value": _encode_value(child),
            }
            for key, child in value.items()
        ]
        items.sort(key=lambda item: _canonical_json(item["key"]))
        return {"kind": "mapping", "items": items}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return {"kind": "list", "items": [_encode_value(item) for item in value]}
    raise _unsupported_value(value, label=False)


def _require_mapping(value: Any, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def _require_list(value: Any, *, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return value


def _decode_label(payload: Any) -> Any:
    row = _require_mapping(payload, name="encoded label")
    value = decode_variable_label(row)
    if encode_variable_label(value) != dict(row):
        raise ValueError("encoded label must use its canonical typed representation")
    return value


def _decode_value(payload: Any) -> Any:
    row = _require_mapping(payload, name="encoded value")
    kind = row.get("kind")
    if kind in {"none", "bool", "int", "float", "str", "bytes", "frozenset"}:
        return _decode_label(row)
    if kind == "list":
        items = [_decode_value(item) for item in _require_list(row.get("items"), name="items")]
        return items
    if kind == "mapping":
        decoded_mapping: dict[Any, Any] = {}
        for item in _require_list(row.get("items"), name="mapping items"):
            item_row = _require_mapping(item, name="mapping item")
            key = _decode_label(item_row.get("key"))
            try:
                duplicate = key in decoded_mapping
            except TypeError as error:
                raise ValueError("decoded metadata mapping key must be hashable") from error
            if duplicate:
                raise ValueError("encoded mapping contains duplicate keys")
            decoded_mapping[key] = _decode_value(item_row.get("value"))
        return decoded_mapping
    raise ValueError("encoded value has an unsupported kind")


def _position(value: Any, *, size: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < size:
        raise ValueError(f"{name} must be a valid variable position")
    return value


def _payload_float(value: Any, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite JSON number")
    return finite_float(value, name=name)


@dataclass(frozen=True, slots=True)
class ThermodynamicProgram:
    """One immutable logical model plus roles and target-independent evidence."""

    model: LogicalModel
    clamps: Any = field(default_factory=tuple, repr=False, compare=False)
    coordinates: Any = field(default_factory=dict, repr=False, compare=False)
    observations: Any = field(default_factory=dict, repr=False, compare=False)
    factor_sources: Any = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    free_variables: tuple[Variable, ...] = field(init=False)
    clamped_variables: tuple[Variable, ...] = field(init=False)
    clamp_values: Mapping[Variable, Any] = field(init=False)
    logical_coordinates: Mapping[Variable, tuple[float, ...]] = field(init=False)
    coordinate_dimension: int = field(init=False)
    observation_metadata: Mapping[Variable, Any] = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.model, (IsingModel, CategoricalModel)):
            raise TypeError("ThermodynamicProgram requires an IsingModel or CategoricalModel")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        free, clamped, clamp_values = _normalize_clamps(self.model, self.clamps)
        coordinates, coordinate_dimension = _normalize_coordinates(
            self.model,
            self.coordinates,
        )
        observations = _normalize_observations(
            self.model,
            clamped,
            self.observations,
        )
        factor_sources = _normalize_factor_sources(self.model, self.factor_sources)
        object.__setattr__(self, "clamps", clamp_values)
        object.__setattr__(self, "coordinates", coordinates)
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "factor_sources", factor_sources)
        object.__setattr__(self, "metadata", freeze(dict(self.metadata)))
        object.__setattr__(self, "free_variables", free)
        object.__setattr__(self, "clamped_variables", clamped)
        object.__setattr__(self, "clamp_values", clamp_values)
        object.__setattr__(self, "logical_coordinates", coordinates)
        object.__setattr__(self, "coordinate_dimension", coordinate_dimension)
        object.__setattr__(self, "observation_metadata", observations)

    def project(self) -> LogicalModel:
        """Substitute all clamps and return the same logical model type."""
        if isinstance(self.model, IsingModel):
            return self._project_ising()
        return self._project_categorical()

    def _projection_metadata(self, transformations: list[dict[str, Any]]) -> dict[str, Any]:
        model_metadata = dict(self.model.metadata)
        clamped_set = set(self.clamped_variables)
        model_metadata["thermodynamic_projection"] = {
            "schema_version": PROGRAM_SCHEMA_VERSION,
            "clamped_variable_positions": [
                position for position, variable in enumerate(self.model.variables) if variable in clamped_set
            ],
            "transformations": transformations,
        }
        return model_metadata

    def _project_ising(self) -> IsingModel:
        model = self.model
        assert isinstance(model, IsingModel)
        source_positions = variable_index(model.variables)
        target_positions = variable_index(self.free_variables)
        free_set = set(self.free_variables)
        linear_terms = {variable: [model.linear[variable]] for variable in self.free_variables}
        offset_terms = [model.offset]
        transformations: list[dict[str, Any]] = []

        for variable in model.variables:
            factor_id = f"linear:{source_positions[variable]}"
            if variable in free_set:
                target_kind = "linear"
                target = {"variable_position": target_positions[variable]}
            else:
                offset_terms.append(model.linear[variable] * self.clamp_values[variable])
                target_kind = "offset"
                target = {}
            transformations.append(
                {
                    "factor_id": factor_id,
                    "source_id": self.factor_sources[factor_id],
                    "target_kind": target_kind,
                    **target,
                }
            )

        quadratic: dict[tuple[Variable, Variable], float] = {}
        for (left, right), coefficient in model.quadratic.items():
            left_source_position = source_positions[left]
            right_source_position = source_positions[right]
            factor_id = f"quadratic:{left_source_position}:{right_source_position}"
            left_free = left in free_set
            right_free = right in free_set
            if left_free and right_free:
                quadratic[(left, right)] = coefficient
                target_kind = "quadratic"
                target = {
                    "left_position": target_positions[left],
                    "right_position": target_positions[right],
                }
            elif left_free:
                linear_terms[left].append(coefficient * self.clamp_values[right])
                target_kind = "linear"
                target = {"variable_position": target_positions[left]}
            elif right_free:
                linear_terms[right].append(coefficient * self.clamp_values[left])
                target_kind = "linear"
                target = {"variable_position": target_positions[right]}
            else:
                offset_terms.append(coefficient * self.clamp_values[left] * self.clamp_values[right])
                target_kind = "offset"
                target = {}
            transformations.append(
                {
                    "factor_id": factor_id,
                    "source_id": self.factor_sources[factor_id],
                    "target_kind": target_kind,
                    **target,
                }
            )

        linear = {
            variable: finite_sum(linear_terms[variable], name="projected linear bias")
            for variable in self.free_variables
        }
        offset = finite_sum(offset_terms, name="projected Ising offset")
        return IsingModel(
            variables=self.free_variables,
            linear=linear,
            quadratic=quadratic,
            offset=offset,
            source_format=model.source_format,
            metadata=self._projection_metadata(transformations),
        )

    def _project_categorical(self) -> CategoricalModel:
        model = self.model
        assert isinstance(model, CategoricalModel)
        source_positions = variable_index(model.variables)
        target_positions = variable_index(self.free_variables)
        free_set = set(self.free_variables)
        unary_terms: dict[Variable, dict[Any, list[float]]] = {
            variable: {category: [model.unary[variable][category]] for category in model.domains[variable]}
            for variable in self.free_variables
        }
        offset_terms = [model.offset]
        transformations: list[dict[str, Any]] = []

        for variable in model.variables:
            factor_id = f"unary:{source_positions[variable]}"
            if variable in free_set:
                target_kind = "unary"
                target = {"variable_position": target_positions[variable]}
            else:
                offset_terms.append(model.unary[variable][self.clamp_values[variable]])
                target_kind = "offset"
                target = {}
            transformations.append(
                {
                    "factor_id": factor_id,
                    "source_id": self.factor_sources[factor_id],
                    "target_kind": target_kind,
                    **target,
                }
            )

        pairwise: dict[tuple[Variable, Variable], Mapping[tuple[Any, Any], float]] = {}
        for (left, right), table in model.pairwise.items():
            left_source_position = source_positions[left]
            right_source_position = source_positions[right]
            factor_id = f"pairwise:{left_source_position}:{right_source_position}"
            left_free = left in free_set
            right_free = right in free_set
            if left_free and right_free:
                pairwise[(left, right)] = table
                target_kind = "pairwise"
                target = {
                    "left_position": target_positions[left],
                    "right_position": target_positions[right],
                }
            elif left_free:
                right_value = self.clamp_values[right]
                for category in model.domains[left]:
                    unary_terms[left][category].append(table[(category, right_value)])
                target_kind = "unary"
                target = {"variable_position": target_positions[left]}
            elif right_free:
                left_value = self.clamp_values[left]
                for category in model.domains[right]:
                    unary_terms[right][category].append(table[(left_value, category)])
                target_kind = "unary"
                target = {"variable_position": target_positions[right]}
            else:
                offset_terms.append(table[(self.clamp_values[left], self.clamp_values[right])])
                target_kind = "offset"
                target = {}
            transformations.append(
                {
                    "factor_id": factor_id,
                    "source_id": self.factor_sources[factor_id],
                    "target_kind": target_kind,
                    **target,
                }
            )

        unary = {
            variable: {
                category: finite_sum(
                    unary_terms[variable][category],
                    name="projected categorical unary value",
                )
                for category in model.domains[variable]
            }
            for variable in self.free_variables
        }
        return CategoricalModel(
            variables=self.free_variables,
            domains={variable: model.domains[variable] for variable in self.free_variables},
            unary=unary,
            pairwise=pairwise,
            offset=finite_sum(offset_terms, name="projected categorical offset"),
            metadata=self._projection_metadata(transformations),
        )

    def with_clamps(self, clamps: Any) -> "ThermodynamicProgram":
        """Return a reconstructed program with a replacement clamp set."""
        _, clamped, normalized = _normalize_clamps(self.model, clamps)
        clamped_set = set(clamped)
        observations = {
            variable: value
            for variable, value in self.observation_metadata.items()
            if variable in clamped_set
        }
        return ThermodynamicProgram(
            self.model,
            clamps=tuple(normalized.items()),
            coordinates=dict(self.logical_coordinates),
            observations=observations,
            factor_sources=dict(self.factor_sources),
            metadata=dict(self.metadata),
        )

    def relabel_variables(self, mapping: Mapping[Variable, Variable]) -> "ThermodynamicProgram":
        """Return an equivalent program under a complete one-to-one relabeling."""
        if not isinstance(mapping, Mapping):
            raise TypeError("relabel mapping must be a mapping")
        mapping_key_index = exact_mapping_index(mapping)
        exact_keys = len(mapping) == len(self.model.variables) and all(
            _has_exact_mapping_key(mapping, variable, mapping_key_index) for variable in self.model.variables
        )
        if not exact_keys:
            raise ValueError("relabel mapping keys must match variables exactly")
        targets = tuple(
            mapping[exact_mapping_key(mapping, variable, mapping_key_index)]
            for variable in self.model.variables
        )
        canonical_mapping = dict(zip(self.model.variables, targets))
        try:
            unique_targets = len(set(targets)) == len(targets)
        except TypeError as error:
            raise ValueError("relabel targets must be hashable and unique") from error
        if not unique_targets:
            raise ValueError("relabel targets must be unique")

        if isinstance(self.model, IsingModel):
            model: LogicalModel = IsingModel(
                variables=targets,
                linear={
                    canonical_mapping[variable]: coefficient
                    for variable, coefficient in self.model.linear.items()
                },
                quadratic={
                    (canonical_mapping[left], canonical_mapping[right]): coefficient
                    for (left, right), coefficient in self.model.quadratic.items()
                },
                offset=self.model.offset,
                source_format=self.model.source_format,
                metadata=dict(self.model.metadata),
            )
        else:
            pairwise: dict[
                tuple[Variable, Variable],
                Mapping[tuple[Any, Any], float],
            ] = {}
            for pair_position, ((left, right), table) in enumerate(self.model.pairwise.items()):
                target_left = canonical_mapping[left]
                target_right = canonical_mapping[right]
                if pair_position < self.model.reversed_pair_count:
                    pairwise[(target_right, target_left)] = {
                        (right_category, left_category): table[(left_category, right_category)]
                        for right_category in self.model.domains[right]
                        for left_category in self.model.domains[left]
                    }
                else:
                    pairwise[(target_left, target_right)] = table
            model = CategoricalModel(
                variables=targets,
                domains={
                    canonical_mapping[variable]: self.model.domains[variable]
                    for variable in self.model.variables
                },
                unary={
                    canonical_mapping[variable]: self.model.unary[variable]
                    for variable in self.model.variables
                },
                pairwise=pairwise,
                offset=self.model.offset,
                metadata=dict(self.model.metadata),
            )
        return ThermodynamicProgram(
            model,
            clamps=[(canonical_mapping[variable], value) for variable, value in self.clamp_values.items()],
            coordinates={
                canonical_mapping[variable]: coordinate
                for variable, coordinate in self.logical_coordinates.items()
            },
            observations={
                canonical_mapping[variable]: value for variable, value in self.observation_metadata.items()
            },
            factor_sources=dict(self.factor_sources),
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic, versioned, JSON-safe positional payload."""
        positions = variable_index(self.model.variables)
        if isinstance(self.model, IsingModel):
            model_payload: dict[str, Any] = {
                "kind": "ising",
                "variables": [_encode_value(variable, label=True) for variable in self.model.variables],
                "linear": [self.model.linear[variable] for variable in self.model.variables],
                "quadratic": [
                    {
                        "left": positions[left],
                        "right": positions[right],
                        "coefficient": coefficient,
                    }
                    for (left, right), coefficient in self.model.quadratic.items()
                ],
                "offset": self.model.offset,
                "source_format": self.model.source_format,
                "metadata": _encode_value(self.model.metadata),
            }
        else:
            model_payload = {
                "kind": "categorical",
                "variables": [_encode_value(variable, label=True) for variable in self.model.variables],
                "domains": [
                    [_encode_value(category, label=True) for category in self.model.domains[variable]]
                    for variable in self.model.variables
                ],
                "unary": [
                    [self.model.unary[variable][category] for category in self.model.domains[variable]]
                    for variable in self.model.variables
                ],
                "pairwise": [
                    {
                        "left": positions[left],
                        "right": positions[right],
                        "values": [
                            [
                                table[(left_category, right_category)]
                                for right_category in self.model.domains[right]
                            ]
                            for left_category in self.model.domains[left]
                        ],
                    }
                    for (left, right), table in self.model.pairwise.items()
                ],
                "offset": self.model.offset,
                "reversed_pair_count": self.model.reversed_pair_count,
                "metadata": _encode_value(self.model.metadata),
            }
        return {
            "schema_version": PROGRAM_SCHEMA_VERSION,
            "model": model_payload,
            "clamps": [
                {
                    "variable": positions[variable],
                    "value": _encode_value(value, label=True),
                }
                for variable, value in self.clamp_values.items()
            ],
            "coordinates": [
                {
                    "variable": positions[variable],
                    "values": list(coordinate),
                }
                for variable, coordinate in self.logical_coordinates.items()
            ],
            "observations": [
                {
                    "variable": positions[variable],
                    "metadata": _encode_value(value),
                }
                for variable, value in self.observation_metadata.items()
            ],
            "factor_sources": [
                {"factor_id": factor_id, "source_id": source_id}
                for factor_id, source_id in self.factor_sources.items()
            ],
            "metadata": _encode_value(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ThermodynamicProgram":
        """Reconstruct a program from :meth:`to_dict` output with duplicate checks."""
        root = _require_mapping(payload, name="program payload")
        schema_version = root.get("schema_version")
        if type(schema_version) is not int or schema_version != PROGRAM_SCHEMA_VERSION:
            raise ValueError("unsupported thermodynamic program schema version")
        model_row = _require_mapping(root.get("model"), name="model payload")
        variables = tuple(
            _decode_label(value)
            for value in _require_list(model_row.get("variables"), name="model variables")
        )
        kind = model_row.get("kind")
        if kind == "ising":
            linear_values = [
                _payload_float(value, name="Ising linear value")
                for value in _require_list(model_row.get("linear"), name="Ising linear values")
            ]
            if len(linear_values) != len(variables):
                raise ValueError("Ising linear values must match variable count")
            quadratic: dict[tuple[Any, Any], Any] = {}
            for entry in _require_list(model_row.get("quadratic"), name="Ising quadratic rows"):
                row = _require_mapping(entry, name="Ising quadratic row")
                left = _position(row.get("left"), size=len(variables), name="quadratic left")
                right = _position(row.get("right"), size=len(variables), name="quadratic right")
                if left >= right:
                    raise ValueError("serialized quadratic factors must use canonical variable order")
                pair = (variables[left], variables[right])
                if pair in quadratic:
                    raise ValueError("serialized model contains a duplicate quadratic factor")
                quadratic[pair] = _payload_float(
                    row.get("coefficient"),
                    name="Ising quadratic coefficient",
                )
            source_format = model_row.get("source_format")
            if not isinstance(source_format, str):
                raise ValueError("Ising source_format must be a string")
            model: LogicalModel = IsingModel(
                variables=variables,
                linear=dict(zip(variables, linear_values)),
                quadratic=quadratic,
                offset=_payload_float(model_row.get("offset"), name="Ising offset"),
                source_format=source_format,
                metadata=_decoded_metadata(model_row.get("metadata"), name="model metadata"),
            )
        elif kind == "categorical":
            domain_rows = _require_list(model_row.get("domains"), name="categorical domains")
            unary_rows = _require_list(model_row.get("unary"), name="categorical unary rows")
            pairwise_rows = _require_list(
                model_row.get("pairwise"),
                name="categorical pairwise rows",
            )
            reversed_pair_count = model_row.get("reversed_pair_count")
            if (
                isinstance(reversed_pair_count, bool)
                or not isinstance(reversed_pair_count, int)
                or not 0 <= reversed_pair_count <= len(pairwise_rows)
            ):
                raise ValueError("categorical reversed_pair_count must be between zero and the pair count")
            if len(domain_rows) != len(variables) or len(unary_rows) != len(variables):
                raise ValueError("categorical domain and unary rows must match variable count")
            domains = {
                variable: tuple(
                    _decode_label(value) for value in _require_list(domain_rows[position], name="domain")
                )
                for position, variable in enumerate(variables)
            }
            unary: dict[Any, dict[Any, Any]] = {}
            for position, variable in enumerate(variables):
                values = [
                    _payload_float(value, name="categorical unary value")
                    for value in _require_list(
                        unary_rows[position],
                        name="categorical unary values",
                    )
                ]
                if len(values) != len(domains[variable]):
                    raise ValueError("categorical unary values must match domain size")
                unary[variable] = dict(zip(domains[variable], values))
            pairwise: dict[tuple[Any, Any], dict[tuple[Any, Any], Any]] = {}
            canonical_pairs: set[tuple[int, int]] = set()
            for pair_position, entry in enumerate(pairwise_rows):
                row = _require_mapping(entry, name="categorical pairwise row")
                left_position = _position(row.get("left"), size=len(variables), name="pairwise left")
                right_position = _position(row.get("right"), size=len(variables), name="pairwise right")
                if left_position >= right_position:
                    raise ValueError("serialized pairwise factors must use canonical variable order")
                position_pair = (left_position, right_position)
                if position_pair in canonical_pairs:
                    raise ValueError("serialized model contains a duplicate pairwise factor")
                canonical_pairs.add(position_pair)
                left = variables[left_position]
                right = variables[right_position]
                is_reversed = pair_position < reversed_pair_count
                pair = (right, left) if is_reversed else (left, right)
                matrix = _require_list(row.get("values"), name="pairwise matrix")
                if len(matrix) != len(domains[left]):
                    raise ValueError("pairwise matrix must match left domain size")
                table: dict[tuple[Any, Any], Any] = {}
                for left_index, left_category in enumerate(domains[left]):
                    values = _require_list(matrix[left_index], name="pairwise matrix row")
                    if len(values) != len(domains[right]):
                        raise ValueError("pairwise matrix must match right domain size")
                    for right_index, right_category in enumerate(domains[right]):
                        category_pair = (
                            (right_category, left_category)
                            if is_reversed
                            else (left_category, right_category)
                        )
                        table[category_pair] = _payload_float(
                            values[right_index],
                            name="categorical pairwise value",
                        )
                pairwise[pair] = table
            model = CategoricalModel(
                variables=variables,
                domains=domains,
                unary=unary,
                pairwise=pairwise,
                offset=_payload_float(model_row.get("offset"), name="categorical offset"),
                metadata=_decoded_metadata(model_row.get("metadata"), name="model metadata"),
            )
        else:
            raise ValueError("model payload has an unsupported kind")

        clamp_records: list[tuple[Any, Any]] = []
        for entry in _require_list(root.get("clamps"), name="clamps"):
            row = _require_mapping(entry, name="clamp row")
            position = _position(row.get("variable"), size=len(variables), name="clamp variable")
            clamp_records.append((variables[position], _decode_label(row.get("value"))))

        coordinates: dict[Any, Any] = {}
        for entry in _require_list(root.get("coordinates"), name="coordinates"):
            row = _require_mapping(entry, name="coordinate row")
            position = _position(row.get("variable"), size=len(variables), name="coordinate variable")
            variable = variables[position]
            if variable in coordinates:
                raise ValueError("serialized program contains a duplicate coordinate record")
            coordinates[variable] = _require_list(row.get("values"), name="coordinate values")

        observations: dict[Any, Any] = {}
        for entry in _require_list(root.get("observations"), name="observations"):
            row = _require_mapping(entry, name="observation row")
            position = _position(row.get("variable"), size=len(variables), name="observation variable")
            variable = variables[position]
            if variable in observations:
                raise ValueError("serialized program contains a duplicate observation record")
            observations[variable] = _decode_value(row.get("metadata"))

        factor_sources: dict[str, str] = {}
        for entry in _require_list(root.get("factor_sources"), name="factor_sources"):
            row = _require_mapping(entry, name="factor source row")
            factor_id = row.get("factor_id")
            source_id = row.get("source_id")
            if not isinstance(factor_id, str) or not isinstance(source_id, str):
                raise ValueError("factor source identities must be strings")
            if factor_id in factor_sources:
                raise ValueError("serialized program contains a duplicate factor source")
            factor_sources[factor_id] = source_id
        if set(factor_sources) != set(_factor_ids(model)):
            raise ValueError("serialized factor sources must be complete for the logical model")

        return cls(
            model,
            clamps=clamp_records,
            coordinates=coordinates,
            observations=observations,
            factor_sources=factor_sources,
            metadata=_decoded_metadata(root.get("metadata"), name="program metadata"),
        )


def _decoded_metadata(payload: Any, *, name: str) -> Mapping[Any, Any]:
    value = _decode_value(payload)
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must decode to a mapping")
    return value
