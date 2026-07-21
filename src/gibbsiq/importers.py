"""Factor-graph JSON (schema v1) and NetworkX frontends for ThermodynamicProgram.

Wire contract: reference/02-interfaces/factor-graph-json-v1.md. The graph frontend
consumes a duck-typed NetworkX surface and never imports networkx, keeping the core
package dependency-free.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from .conversions import compile_ising, compile_qubo
from .model import (
    IsingModel,
    Variable,
    canonical_variable_sort_key,
    decode_variable_label,
    encode_variable_label,
    exact_label_key,
    normalize_vartype,
)
from .program import ThermodynamicProgram

__all__ = [
    "FACTOR_GRAPH_FORMAT",
    "FACTOR_GRAPH_SCHEMA_VERSION",
    "factor_json_from_program",
    "program_from_factor_json",
    "program_from_networkx",
]

FACTOR_GRAPH_FORMAT = "gibbsiq-factor-graph"
FACTOR_GRAPH_SCHEMA_VERSION = 1

_REQUIRED_FIELDS = ("format", "schema_version", "vartype", "offset", "variables", "factors")
_DOCUMENT_FIELDS = frozenset((*_REQUIRED_FIELDS, "clamps", "coordinates", "observations", "metadata"))
_GRAPH_SURFACE = ("is_directed", "is_multigraph", "nodes", "edges")


def _finite_number(value: Any, *, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must not be boolean")
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def _position(value: Any, *, size: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < size:
        raise ValueError(f"{name} must be a valid variable position")
    return value


def _require_record(
    value: Any, *, allowed: frozenset[str], required: tuple[str, ...], name: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} record must be a mapping")
    for key in value:
        if type(key) is not str or key not in allowed:
            raise ValueError(f"unknown {name} record field {key!r}")
    for field_name in required:
        if field_name not in value:
            raise ValueError(f"{name} record is missing required field {field_name!r}")
    return value


def _record_list(document: Mapping[str, Any], field_name: str) -> Sequence[Any]:
    if field_name not in document:
        return ()
    value = document[field_name]
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"factor-graph {field_name} must be a list")
    return value


def _validate_json_safe(value: Any, *, path: str, error: type[Exception]) -> None:
    """Enforce the JSON-safe closure: null/bool/int/finite float/str/array/object."""
    if value is None or type(value) in (bool, int, str):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise error(f"{path} must be finite")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if type(key) is not str:
                raise error(f"{path} mapping keys must be exact strings")
            _validate_json_safe(item, path=f"{path}.{key}", error=error)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            _validate_json_safe(item, path=f"{path}[{index}]", error=error)
        return
    raise error(f"{path} holds an unsupported value of type {type(value).__name__}")


def _json_export_copy(value: Any, *, path: str) -> Any:
    """Deep-copy frozen program values to plain JSON types; reject the rest."""
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise TypeError(f"{path} must be finite")
        return value
    if isinstance(value, Mapping):
        copied: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError(f"{path} mapping keys must be exact strings")
            copied[key] = _json_export_copy(item, path=f"{path}.{key}")
        return copied
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_export_copy(item, path=f"{path}[{index}]") for index, item in enumerate(value)]
    raise TypeError(f"{path} holds an unsupported value of type {type(value).__name__}")


def _decode_canonical_label(payload: Any) -> Variable:
    label = decode_variable_label(payload)
    if encode_variable_label(label) != dict(payload):
        raise ValueError("encoded variable label must use its canonical typed representation")
    return label


def _binary_clamp_to_spin(value: Any, *, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value not in (0, 1):
        raise ValueError(f"clamp value must be 0 or 1 for BINARY {context}")
    return 2 * value - 1


def program_from_factor_json(document: Any) -> ThermodynamicProgram:
    """Import a gibbsiq-factor-graph schema v1 document into a ThermodynamicProgram."""
    if not isinstance(document, Mapping):
        raise ValueError("factor-graph document must be a mapping")
    for key in document:
        if type(key) is not str or key not in _DOCUMENT_FIELDS:
            raise ValueError(f"unknown factor-graph document field {key!r}")
    for field_name in _REQUIRED_FIELDS:
        if field_name not in document:
            raise ValueError(f"factor-graph document is missing required field {field_name!r}")
    if document["format"] != FACTOR_GRAPH_FORMAT:
        raise ValueError("unsupported factor-graph document format")
    schema_version = document["schema_version"]
    if type(schema_version) is not int or schema_version != FACTOR_GRAPH_SCHEMA_VERSION:
        raise ValueError("unsupported factor-graph schema version")
    vartype = document["vartype"]
    if type(vartype) is not str or vartype not in ("SPIN", "BINARY"):
        raise ValueError("factor-graph vartype must be SPIN or BINARY")
    offset = _finite_number(document["offset"], name="factor-graph offset")

    raw_variables = _record_list(document, "variables")
    variables = tuple(_decode_canonical_label(row) for row in raw_variables)
    size = len(variables)

    raw_factors = _record_list(document, "factors")
    linear: dict[Variable, float] = {}
    quadratic: dict[tuple[Variable, Variable], float] = {}
    seen_scopes: set[tuple[int, ...]] = set()
    sources: dict[str, str] = {}
    for row in raw_factors:
        record = _require_record(
            row,
            allowed=frozenset(("scope", "coefficient", "source_id")),
            required=("scope", "coefficient"),
            name="factor",
        )
        scope = record["scope"]
        if not isinstance(scope, Sequence) or isinstance(scope, (str, bytes)) or len(scope) not in (1, 2):
            raise ValueError("factor scope must contain one or two variable positions")
        positions = tuple(_position(entry, size=size, name="factor scope position") for entry in scope)
        if len(positions) == 2 and positions[0] >= positions[1]:
            raise ValueError("factor scope positions must be strictly increasing")
        if positions in seen_scopes:
            raise ValueError(f"duplicate factor scope {list(positions)!r}")
        seen_scopes.add(positions)
        coefficient = _finite_number(record["coefficient"], name="factor coefficient")
        if len(positions) == 1:
            linear[variables[positions[0]]] = coefficient
            identity = f"linear:{positions[0]}"
        else:
            quadratic[(variables[positions[0]], variables[positions[1]])] = coefficient
            identity = f"quadratic:{positions[0]}:{positions[1]}"
        if "source_id" in record:
            source = record["source_id"]
            if type(source) is not str or not source:
                raise ValueError("factor source_id must be a non-empty string")
            sources[identity] = source

    structured = {"linear": linear, "quadratic": quadratic, "offset": offset}
    if vartype == "SPIN":
        model = compile_ising(structured, variables=variables, source_format="factor_json")
    else:
        model = compile_qubo(structured, variables=variables, source_format="factor_json")

    if sources:
        # IR canonicalization drops zero-coefficient pair factors; their source
        # annotations are discarded with them per the schema contract.
        position_index = {variable: index for index, variable in enumerate(model.variables)}
        valid = {f"linear:{index}" for index in range(len(model.variables))}
        valid.update(
            f"quadratic:{position_index[left]}:{position_index[right]}" for left, right in model.quadratic
        )
        sources = {identity: source for identity, source in sources.items() if identity in valid}

    clamp_pairs: list[tuple[Variable, Any]] = []
    for row in _record_list(document, "clamps"):
        record = _require_record(
            row, allowed=frozenset(("position", "value")), required=("position", "value"), name="clamp"
        )
        position = _position(record["position"], size=size, name="clamp position")
        value = record["value"]
        if vartype == "BINARY":
            value = _binary_clamp_to_spin(value, context="documents")
        clamp_pairs.append((variables[position], value))

    coordinates: dict[Variable, Any] = {}
    seen_coordinate_positions: set[int] = set()
    for row in _record_list(document, "coordinates"):
        record = _require_record(
            row,
            allowed=frozenset(("position", "coordinate")),
            required=("position", "coordinate"),
            name="coordinate",
        )
        position = _position(record["position"], size=size, name="coordinate position")
        if position in seen_coordinate_positions:
            raise ValueError("duplicate coordinate position")
        seen_coordinate_positions.add(position)
        coordinates[variables[position]] = record["coordinate"]

    observations: dict[Variable, Any] = {}
    seen_observation_positions: set[int] = set()
    for row in _record_list(document, "observations"):
        record = _require_record(
            row, allowed=frozenset(("position", "metadata")), required=("position",), name="observation"
        )
        position = _position(record["position"], size=size, name="observation position")
        if position in seen_observation_positions:
            raise ValueError("duplicate observation position")
        seen_observation_positions.add(position)
        payload = record.get("metadata", {})
        _validate_json_safe(payload, path="observation metadata", error=ValueError)
        observations[variables[position]] = payload

    metadata: dict[str, Any] = {}
    if "metadata" in document:
        raw_metadata = document["metadata"]
        if not isinstance(raw_metadata, Mapping):
            raise ValueError("factor-graph metadata must be a mapping")
        _validate_json_safe(raw_metadata, path="metadata", error=ValueError)
        metadata = dict(raw_metadata)

    return ThermodynamicProgram(
        model,
        clamps=clamp_pairs,
        coordinates=coordinates,
        observations=observations,
        factor_sources=sources,
        metadata=metadata,
    )


def factor_json_from_program(program: ThermodynamicProgram) -> dict[str, Any]:
    """Export a ThermodynamicProgram as its canonical schema v1 document."""
    if not isinstance(program, ThermodynamicProgram):
        raise TypeError("factor_json_from_program requires a ThermodynamicProgram")
    model = program.model
    if not isinstance(model, IsingModel):
        raise TypeError("factor-graph JSON v1 supports IsingModel programs only")

    position_index = {variable: index for index, variable in enumerate(model.variables)}
    factors: list[dict[str, Any]] = []
    for index, variable in enumerate(model.variables):
        factors.append(
            {
                "scope": [index],
                "coefficient": model.linear[variable],
                "source_id": program.factor_sources[f"linear:{index}"],
            }
        )
    for (left, right), coefficient in model.quadratic.items():
        left_index, right_index = position_index[left], position_index[right]
        factors.append(
            {
                "scope": [left_index, right_index],
                "coefficient": coefficient,
                "source_id": program.factor_sources[f"quadratic:{left_index}:{right_index}"],
            }
        )

    document: dict[str, Any] = {
        "format": FACTOR_GRAPH_FORMAT,
        "schema_version": FACTOR_GRAPH_SCHEMA_VERSION,
        "vartype": "SPIN",
        "offset": model.offset,
        "variables": [encode_variable_label(variable) for variable in model.variables],
        "factors": factors,
    }
    if program.clamp_values:
        document["clamps"] = [
            {"position": position_index[variable], "value": value}
            for variable, value in sorted(
                program.clamp_values.items(), key=lambda item: position_index[item[0]]
            )
        ]
    if program.logical_coordinates:
        document["coordinates"] = [
            {"position": position_index[variable], "coordinate": list(coordinate)}
            for variable, coordinate in sorted(
                program.logical_coordinates.items(), key=lambda item: position_index[item[0]]
            )
        ]
    if program.observation_metadata:
        document["observations"] = [
            {
                "position": position_index[variable],
                "metadata": _json_export_copy(payload, path="observation metadata"),
            }
            for variable, payload in sorted(
                program.observation_metadata.items(), key=lambda item: position_index[item[0]]
            )
        ]
    if program.metadata:
        document["metadata"] = _json_export_copy(dict(program.metadata), path="metadata")
    return document


def program_from_networkx(
    graph: Any,
    *,
    vartype: Any,
    linear_attribute: str = "bias",
    coefficient_attribute: str = "weight",
    clamp_attribute: str = "clamp",
    coordinate_attribute: str = "coordinate",
    default_coefficient: float | None = None,
    offset: float | None = None,
    node_order: Sequence[Variable] | None = None,
) -> ThermodynamicProgram:
    """Import an undirected NetworkX-style graph into a ThermodynamicProgram."""
    normalized_vartype = normalize_vartype(vartype)
    for method_name in _GRAPH_SURFACE:
        if not callable(getattr(graph, method_name, None)):
            raise TypeError(
                "program_from_networkx requires a NetworkX-style graph object exposing "
                "is_directed, is_multigraph, nodes, and edges"
            )
    graph_attributes = getattr(graph, "graph", None)
    if not isinstance(graph_attributes, Mapping):
        raise TypeError("program_from_networkx requires a graph-level attribute mapping at .graph")
    if graph.is_directed():
        raise ValueError("directed graphs are ambiguous for symmetric couplings; supply an undirected graph")
    if graph.is_multigraph():
        raise ValueError("multigraph inputs are ambiguous; merge parallel edges before import")

    if "offset" in graph_attributes:
        if offset is not None:
            raise ValueError("offset supplied both as a keyword and as the graph attribute 'offset'")
        model_offset = _finite_number(graph_attributes["offset"], name="graph attribute offset")
    else:
        model_offset = 0.0 if offset is None else _finite_number(offset, name="offset")

    node_rows = [(label, attributes) for label, attributes in graph.nodes(data=True)]
    row_index: dict[Any, int] = {}
    for row_position, (label, _) in enumerate(node_rows):
        key = exact_label_key(label)
        if key in row_index:
            raise ValueError(f"duplicate graph node {label!r}")
        row_index[key] = row_position

    if node_order is not None:
        ordered = tuple(node_order)
        seen_keys: set[Any] = set()
        for label in ordered:
            key = exact_label_key(label)
            if key not in row_index or key in seen_keys:
                raise ValueError("node_order must list every graph node exactly once")
            seen_keys.add(key)
        if len(ordered) != len(node_rows):
            raise ValueError("node_order must list every graph node exactly once")
    else:
        ordered = tuple(sorted((label for label, _ in node_rows), key=canonical_variable_sort_key))

    linear: dict[Variable, float] = {}
    clamp_pairs: list[tuple[Variable, Any]] = []
    coordinates: dict[Variable, Any] = {}
    for label, attributes in node_rows:
        if not isinstance(attributes, Mapping):
            raise TypeError("graph node attributes must be mappings")
        if linear_attribute in attributes:
            linear[label] = _finite_number(
                attributes[linear_attribute], name=f"node {label!r} {linear_attribute} attribute"
            )
        if clamp_attribute in attributes:
            value = attributes[clamp_attribute]
            if normalized_vartype == "BINARY":
                value = _binary_clamp_to_spin(value, context="graphs")
            clamp_pairs.append((label, value))
        if coordinate_attribute in attributes:
            coordinates[label] = attributes[coordinate_attribute]

    quadratic: dict[tuple[Variable, Variable], float] = {}
    seen_pairs: set[tuple[int, int]] = set()
    for left, right, attributes in graph.edges(data=True):
        try:
            left_row = row_index[exact_label_key(left)]
            right_row = row_index[exact_label_key(right)]
        except KeyError:
            raise ValueError(
                f"edge ({left!r}, {right!r}) references a label that is not a graph node"
            ) from None
        if left_row == right_row:
            raise ValueError(f"self-loop edge on {left!r} has no pairwise Ising reading")
        pair = (left_row, right_row) if left_row < right_row else (right_row, left_row)
        if pair in seen_pairs:
            raise ValueError(f"duplicate edge between {left!r} and {right!r}")
        seen_pairs.add(pair)
        if coefficient_attribute in attributes:
            coefficient = _finite_number(
                attributes[coefficient_attribute],
                name=f"edge ({left!r}, {right!r}) {coefficient_attribute} attribute",
            )
        elif default_coefficient is not None:
            coefficient = _finite_number(default_coefficient, name="default_coefficient")
        else:
            raise ValueError(
                f"edge ({left!r}, {right!r}) is missing coefficient attribute "
                f"{coefficient_attribute!r} and no default_coefficient is set"
            )
        quadratic[(left, right)] = coefficient

    _validate_json_safe(graph_attributes, path="graph attributes", error=ValueError)
    metadata = {"source_format": "networkx", "graph_attributes": dict(graph_attributes)}

    structured = {"linear": linear, "quadratic": quadratic, "offset": model_offset}
    if normalized_vartype == "SPIN":
        model = compile_ising(structured, variables=ordered, source_format="networkx")
    else:
        model = compile_qubo(structured, variables=ordered, source_format="networkx")
    return ThermodynamicProgram(model, clamps=clamp_pairs, coordinates=coordinates, metadata=metadata)
