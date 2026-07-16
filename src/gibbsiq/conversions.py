"""Input normalization for QUBO, Ising, and optional dimod BQM objects."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from gibbsiq.model import (
    ISING_MODEL_SCHEMA_VERSION,
    IsingModel,
    Variable,
    canonical_variable_sort_key,
    decode_variable_label,
    exact_label_equal,
    exact_mapping_index,
    exact_variable_position,
    finite_float,
    finite_sum,
    normalize_vartype,
    variable_index,
    variable_sort_key,
)


def compile_qubo(
    qubo: Mapping[Any, Any],
    *,
    offset: float | None = None,
    variables: list[Variable] | tuple[Variable, ...] | None = None,
    metadata: Mapping[str, Any] | None = None,
    source_format: str = "qubo",
) -> IsingModel:
    """QUBO -> Ising IR. Accepts {linear,quadratic,...} fixture shape or flat
    {(u,v): coefficient} map; diagonal entries are binary linear terms.
    """
    exact_mapping_index(qubo)
    parsed = _parse_qubo(qubo, offset=offset, variables=variables)
    order = parsed["variables"]
    linear_binary = parsed["linear"]
    quadratic_binary = parsed["quadratic"]

    linear_spin_terms = {variable: [linear_binary.get(variable, 0.0) / 2.0] for variable in order}
    quadratic_spin: dict[tuple[Variable, Variable], float] = {}
    offset_terms = [parsed["offset"]]
    offset_terms.extend(linear_binary.get(variable, 0.0) / 2.0 for variable in order)

    for (left, right), coefficient in quadratic_binary.items():
        coupling = coefficient / 4.0
        quadratic_spin[(left, right)] = coupling
        linear_spin_terms[left].append(coupling)
        linear_spin_terms[right].append(coupling)
        offset_terms.append(coupling)

    linear_spin = {
        variable: finite_sum(terms, name=f"converted linear bias for {variable!r}")
        for variable, terms in linear_spin_terms.items()
    }
    ising_offset = finite_sum(offset_terms, name="converted Ising offset")

    conversion_metadata = dict(metadata or {})
    conversion_metadata.update(
        {
            "source_format": source_format,
            "input_offset": parsed["offset"],
            "conversion_offset": ising_offset,
            "variable_order": list(order),
            "qubo_term_convention": (
                "linear terms plus upper-triangle quadratic terms; symmetric duplicate "
                "pair entries are summed before conversion"
            ),
        }
    )

    return IsingModel(
        variables=order,
        linear=linear_spin,
        quadratic=quadratic_spin,
        offset=ising_offset,
        source_format=source_format,
        metadata=conversion_metadata,
    )


def compile_ising(
    h: Mapping[Any, Any],
    J: Mapping[Any, Any] | None = None,
    *,
    offset: float | None = None,
    variables: list[Variable] | tuple[Variable, ...] | None = None,
    metadata: Mapping[str, Any] | None = None,
    source_format: str | None = None,
) -> IsingModel:
    """h,J -> Ising IR in canonical variable order."""
    exact_mapping_index(h)
    if J is not None:
        exact_mapping_index(J)
    parsed = _parse_ising(h, J, offset=offset, variables=variables)
    serialized_metadata, serialized_source_format = _serialized_ising_provenance(h, J)
    effective_source_format = (
        source_format if source_format is not None else serialized_source_format or "ising"
    )
    model_metadata = dict(serialized_metadata)
    model_metadata.update(metadata or {})
    input_offset = parsed["input_offset"]
    if offset is None and "input_offset" in serialized_metadata:
        input_offset = finite_float(
            serialized_metadata["input_offset"],
            name="serialized Ising input_offset metadata",
        )
    model_metadata.update(
        {
            "source_format": effective_source_format,
            "input_offset": input_offset,
            "conversion_offset": parsed["offset"],
            "variable_order": list(parsed["variables"]),
        }
    )

    return IsingModel(
        variables=parsed["variables"],
        linear=parsed["linear"],
        quadratic=parsed["quadratic"],
        offset=parsed["offset"],
        source_format=effective_source_format,
        metadata=model_metadata,
    )


def _serialized_ising_provenance(
    h: Mapping[Any, Any],
    J: Mapping[Any, Any] | None,
) -> tuple[dict[str, Any], str | None]:
    """Recover non-energy evidence from an ``IsingModel.to_dict`` payload."""
    if J is not None or not _is_structured_model(h) or "schema_version" not in h:
        return {}, None
    schema_version = h.get("schema_version")
    if type(schema_version) is not int or schema_version not in {1, ISING_MODEL_SCHEMA_VERSION}:
        return {}, None
    raw_metadata = h.get("metadata", {})
    if not isinstance(raw_metadata, Mapping):
        raise ValueError("serialized Ising metadata must be a mapping")
    recovered_metadata = dict(raw_metadata)
    # The canonical variable order and conversion fields are regenerated from
    # the parsed energy model below; retaining their wire representation would
    # leave typed labels encoded inside the in-memory metadata.
    recovered_metadata.pop("variable_order", None)
    source_format = h.get("source_format", "ising")
    if not isinstance(source_format, str):
        raise ValueError("serialized Ising source_format must be a string")
    return recovered_metadata, source_format


def compile_bqm(bqm: Any, *, metadata: Mapping[str, Any] | None = None) -> IsingModel:
    """BQM -> Ising IR. Uses to_ising() if present; else duck-types
    linear/quadratic/offset/vartype attributes. No hard dimod dependency.
    """
    model_metadata = dict(metadata or {})
    model_metadata["source_format"] = "bqm"

    if hasattr(bqm, "to_ising"):
        h, J, ising_offset = bqm.to_ising()
        variables = _variables_from_bqm(bqm) or _variables_from_terms(h, _normalize_pairs(J, None))
        model_metadata.update(
            {
                "bqm_vartype": _vartype_name(bqm),
                "input_offset": float(getattr(bqm, "offset", ising_offset)),
                "conversion_offset": float(ising_offset),
                "variable_order": list(variables),
            }
        )
        model = compile_ising(
            h,
            J,
            offset=float(ising_offset),
            variables=variables,
            metadata=model_metadata,
            source_format="bqm",
        )
        return _with_bqm_provenance(
            model,
            bqm_vartype=_vartype_name(bqm),
            input_offset=float(getattr(bqm, "offset", ising_offset)),
        )

    vartype = normalize_vartype(getattr(bqm, "vartype", None))
    linear = dict(bqm.linear)
    quadratic = dict(bqm.quadratic)
    input_offset = float(getattr(bqm, "offset", 0.0))
    variables = _variables_from_bqm(bqm) or _variables_from_terms(linear, _normalize_pairs(quadratic, None))
    model_metadata.update({"bqm_vartype": vartype, "input_offset": input_offset})

    if vartype == "SPIN":
        model = compile_ising(
            linear,
            quadratic,
            offset=input_offset,
            variables=variables,
            metadata=model_metadata,
            source_format="bqm",
        )
    else:
        model = compile_qubo(
            {
                "variables": list(variables),
                "linear": linear,
                "quadratic": quadratic,
                "offset": input_offset,
            },
            metadata=model_metadata,
            source_format="bqm",
        )
    return _with_bqm_provenance(model, bqm_vartype=vartype, input_offset=input_offset)


def _with_bqm_provenance(
    model: IsingModel,
    *,
    bqm_vartype: str,
    input_offset: float,
) -> IsingModel:
    """Re-stamps BQM provenance metadata after Ising/QUBO conversion."""
    metadata = dict(model.metadata)
    metadata.update(
        {
            "source_format": "bqm",
            "bqm_vartype": bqm_vartype,
            "input_offset": input_offset,
            "conversion_offset": model.offset,
            "variable_order": list(model.variables),
        }
    )
    return IsingModel(
        variables=model.variables,
        linear=model.linear,
        quadratic=model.quadratic,
        offset=model.offset,
        source_format="bqm",
        metadata=metadata,
    )


def _parse_qubo(
    qubo: Mapping[Any, Any],
    *,
    offset: float | None,
    variables: list[Variable] | tuple[Variable, ...] | None,
) -> dict[str, Any]:
    term_items: Iterable[tuple[Any, Any]]
    if _is_structured_model(qubo):
        raw_variables = variables if variables is not None else qubo.get("variables")
        raw_offset = qubo.get("offset", 0.0) if offset is None else offset
        raw_linear = qubo.get("linear", {})
        raw_quadratic = qubo.get("quadratic", {})
        exact_mapping_index(raw_linear)
        exact_mapping_index(raw_quadratic)
        linear_terms = {key: [float(value)] for key, value in raw_linear.items()}
        term_items = raw_quadratic.items()
    else:
        raw_variables = variables
        raw_offset = 0.0 if offset is None else offset
        linear_terms = {}
        term_items = qubo.items()

    # Diagonal (u==u) -> linear term; off-diagonal entries remain separate
    # until canonicalization so math.fsum sees every symmetric/aliased input.
    quadratic_items: list[tuple[tuple[Variable, Variable], float]] = []
    for key, value in term_items:
        left, right = _parse_pair_key(key)
        coefficient = float(value)
        if exact_label_equal(left, right):
            linear_terms.setdefault(left, []).append(coefficient)
        else:
            quadratic_items.append(((left, right), coefficient))

    linear = {
        variable: finite_sum(terms, name=f"QUBO linear coefficient for {variable!r}")
        for variable, terms in linear_terms.items()
    }
    return _finish_items(raw_variables, linear, quadratic_items, float(raw_offset))


def _parse_ising(
    h: Mapping[Any, Any],
    J: Mapping[Any, Any] | None,
    *,
    offset: float | None,
    variables: list[Variable] | tuple[Variable, ...] | None,
) -> dict[str, Any]:
    if J is None and _is_structured_model(h) and "schema_version" in h:
        schema_version = h.get("schema_version")
        if type(schema_version) is not int:
            raise ValueError("Ising model schema_version must be an integer")
        if schema_version == ISING_MODEL_SCHEMA_VERSION:
            return _parse_serialized_ising_v2(h, offset=offset, variables=variables)
        if schema_version != 1:
            raise ValueError(f"unsupported Ising model schema version {schema_version!r}")
    if J is None and _is_structured_model(h):
        raw_variables = variables if variables is not None else h.get("variables")
        raw_offset = h.get("offset", 0.0) if offset is None else offset
        raw_linear = h.get("linear", {})
        raw_quadratic = h.get("quadratic", {})
        exact_mapping_index(raw_linear)
        exact_mapping_index(raw_quadratic)
        linear = {key: float(value) for key, value in raw_linear.items()}
        quadratic_input = raw_quadratic
    else:
        raw_variables = variables
        raw_offset = 0.0 if offset is None else offset
        linear = {key: float(value) for key, value in h.items()}
        quadratic_input = {} if J is None else J

    quadratic_items: list[tuple[tuple[Variable, Variable], float]] = []
    offset_terms = [float(raw_offset)]
    for key, value in quadratic_input.items():
        left, right = _parse_pair_key(key)
        coefficient = float(value)
        if exact_label_equal(left, right):
            offset_terms.append(coefficient)
            continue
        quadratic_items.append(((left, right), coefficient))

    folded_offset = finite_sum(offset_terms, name="Ising offset including diagonal terms")
    parsed = _finish_items(raw_variables, linear, quadratic_items, folded_offset)
    parsed["input_offset"] = float(raw_offset)
    return parsed


def _parse_serialized_ising_v2(
    payload: Mapping[Any, Any],
    *,
    offset: float | None,
    variables: list[Variable] | tuple[Variable, ...] | None,
) -> dict[str, Any]:
    """Parse the typed positional model wire format emitted by ``IsingModel.to_dict``."""
    raw_variable_rows = payload.get("variables")
    if not isinstance(raw_variable_rows, (list, tuple)):
        raise ValueError("serialized Ising variables must be a list")
    decoded_variables = tuple(decode_variable_label(row) for row in raw_variable_rows)
    if variables is not None:
        supplied_variables = tuple(variables)
        exact_match = len(supplied_variables) == len(decoded_variables) and all(
            exact_label_equal(supplied, decoded)
            for supplied, decoded in zip(supplied_variables, decoded_variables)
        )
        if not exact_match:
            raise ValueError("explicit variables do not match serialized Ising variables exactly")

    raw_linear = payload.get("linear")
    if not isinstance(raw_linear, (list, tuple)):
        raise ValueError("serialized Ising linear terms must be a list")
    if len(raw_linear) != len(decoded_variables):
        raise ValueError("serialized Ising linear terms must match variable count")
    linear = {variable: float(coefficient) for variable, coefficient in zip(decoded_variables, raw_linear)}

    raw_quadratic = payload.get("quadratic")
    if not isinstance(raw_quadratic, (list, tuple)):
        raise ValueError("serialized Ising quadratic terms must be a list")
    quadratic: dict[tuple[Variable, Variable], float] = {}
    size = len(decoded_variables)
    for row in raw_quadratic:
        if not isinstance(row, Mapping):
            raise ValueError("serialized Ising quadratic row must be a mapping")
        left = row.get("left")
        right = row.get("right")
        if type(left) is not int or type(right) is not int:
            raise ValueError("serialized Ising quadratic positions must be integers")
        if not (0 <= left < right < size):
            raise ValueError("serialized Ising quadratic positions must satisfy 0 <= left < right < n")
        pair = (decoded_variables[left], decoded_variables[right])
        if pair in quadratic:
            raise ValueError("serialized Ising model contains a duplicate quadratic pair")
        quadratic[pair] = finite_float(
            row.get("coefficient"),
            name="serialized Ising quadratic coefficient",
        )

    raw_offset = payload.get("offset", 0.0) if offset is None else offset
    parsed = _finish(decoded_variables, linear, quadratic, float(raw_offset))
    parsed["input_offset"] = float(raw_offset)
    return parsed


def _is_structured_model(value: Mapping[Any, Any]) -> bool:
    """True if mapping uses the structured {linear,quadratic,variables} schema,
    not a flat term map (a variable literally named "linear" stays valid).
    """
    return (
        isinstance(value.get("linear"), Mapping)
        or isinstance(value.get("quadratic"), Mapping)
        or isinstance(value.get("variables"), (list, tuple))
    )


def _finish(
    raw_variables: list[Variable] | tuple[Variable, ...] | None,
    linear: Mapping[Variable, float],
    quadratic: Mapping[tuple[Variable, Variable], float],
    offset: float,
) -> dict[str, Any]:
    """Shared tail of _parse_qubo/_parse_ising: resolves variable order,
    normalizes parsed terms.
    """
    order = _resolve_variables(raw_variables, linear, quadratic)
    # Sparse here; IsingModel.__post_init__ densifies + finite-checks.
    return {
        "variables": order,
        "linear": dict(linear),
        "quadratic": _normalize_pairs(quadratic, order),
        "offset": offset,
    }


def _finish_items(
    raw_variables: list[Variable] | tuple[Variable, ...] | None,
    linear: Mapping[Variable, float],
    quadratic_items: Iterable[tuple[tuple[Variable, Variable], float]],
    offset: float,
) -> dict[str, Any]:
    """Resolve order and normalize without prematurely rounding duplicate terms."""
    items = tuple(quadratic_items)
    referenced_pairs = {pair: 0.0 for pair, _ in items}
    order = _resolve_variables(raw_variables, linear, referenced_pairs)
    return {
        "variables": order,
        "linear": dict(linear),
        "quadratic": _normalize_pair_items(items, order),
        "offset": offset,
    }


def _resolve_variables(
    variables: list[Variable] | tuple[Variable, ...] | None,
    linear: Mapping[Variable, float],
    quadratic: Mapping[tuple[Variable, Variable], float],
) -> tuple[Variable, ...]:
    if variables is not None:
        order = tuple(variables)
    else:
        labels: list[Variable] = list(linear)
        label_index = variable_index(labels)
        for left, right in quadratic:
            for candidate in (left, right):
                try:
                    known_position = label_index[candidate]
                except KeyError:
                    known_position = None
                if known_position is None:
                    labels.append(candidate)
                    label_index[candidate] = len(labels) - 1
                elif not exact_label_equal(candidate, labels[known_position]):
                    # Preserve the equality alias so the uniqueness gate below
                    # fails closed instead of merging typed labels.
                    labels.append(candidate)
        try:
            keyed_labels = [(canonical_variable_sort_key(label), label) for label in labels]
        except TypeError as error:
            raise ValueError(
                "cannot infer a deterministic order for unsupported labels; supply explicit variables"
            ) from error
        keys = [key for key, _ in keyed_labels]
        if len(set(keys)) != len(keys):
            raise ValueError("variable labels have equal canonical sort keys; supply explicit variables")
        order = tuple(label for _, label in sorted(keyed_labels, key=lambda item: item[0]))

    if len(set(order)) != len(order):
        raise ValueError("variables must be unique")
    order_index = variable_index(order)
    referenced = [*linear, *(variable for pair in quadratic for variable in pair)]
    unknown = {candidate for candidate in referenced if _not_exactly_indexed(candidate, order, order_index)}
    if unknown:
        raise ValueError(
            f"terms reference variables not present in variable order: {sorted(unknown, key=variable_sort_key)!r}"
        )
    return order


def _not_exactly_indexed(
    candidate: Variable,
    variables: tuple[Variable, ...],
    index: Mapping[Variable, int],
) -> bool:
    try:
        exact_variable_position(candidate, variables, index)
    except KeyError:
        return True
    return False


def _variables_from_terms(
    linear: Mapping[Variable, Any],
    quadratic: Mapping[tuple[Variable, Variable], Any],
) -> tuple[Variable, ...]:
    return _resolve_variables(None, linear, quadratic)


def _variables_from_bqm(bqm: Any) -> tuple[Variable, ...] | None:
    variables = getattr(bqm, "variables", None)
    if variables is None:
        return None
    return tuple(variables)


def _vartype_name(bqm: Any) -> str:
    """Vartype label from bqm.vartype.name (or the raw value)."""
    vartype = getattr(bqm, "vartype", "unknown")
    return str(getattr(vartype, "name", vartype))


def _normalize_pairs(
    terms: Mapping[Any, Any],
    variables: list[Variable] | tuple[Variable, ...] | None,
) -> dict[tuple[Variable, Variable], float]:
    return _normalize_pair_items(terms.items(), variables)


def _normalize_pair_items(
    term_items: Iterable[tuple[Any, Any]],
    variables: list[Variable] | tuple[Variable, ...] | None,
) -> dict[tuple[Variable, Variable], float]:
    index = variable_index(variables) if variables is not None else None
    contributions: dict[tuple[Variable, Variable], list[float]] = {}
    for key, value in term_items:
        left, right = _parse_pair_key(key)
        pair = (left, right) if exact_label_equal(left, right) else _ordered_pair(left, right, index)
        contributions.setdefault(pair, []).append(float(value))
    normalized = {
        pair: finite_sum(values, name=f"quadratic coefficient for {pair!r}")
        for pair, values in contributions.items()
    }
    if index is None:
        return dict(
            sorted(
                normalized.items(),
                key=lambda item: (variable_sort_key(item[0][0]), variable_sort_key(item[0][1])),
            )
        )
    # Safe: _resolve_variables already validated pair members exist in index.
    return dict(sorted(normalized.items(), key=lambda item: (index[item[0][0]], index[item[0][1]])))


def _parse_pair_key(key: Any) -> tuple[Variable, Variable]:
    if isinstance(key, str) and "," in key:
        left, right = key.split(",", 1)
        return left, right
    if isinstance(key, (tuple, list)) and len(key) == 2:
        return key[0], key[1]
    raise ValueError(f"quadratic/QUBO key {key!r} must be a 2-tuple/list or 'left,right' string")


def _ordered_pair(
    left: Variable,
    right: Variable,
    index: Mapping[Variable, int] | None,
) -> tuple[Variable, Variable]:
    """Orders pair by index position, or by variable_sort_key when unindexed."""
    if index is None:
        return (left, right) if variable_sort_key(left) <= variable_sort_key(right) else (right, left)
    return (left, right) if index[left] < index[right] else (right, left)
