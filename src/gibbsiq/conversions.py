"""Input normalization for QUBO, Ising, and optional dimod BQM objects."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gibbsiq.model import (
    IsingModel,
    Variable,
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
    """Normalize a QUBO into the canonical Ising IR.

    Accepted inputs are either fixture-style objects with ``linear`` and
    ``quadratic`` fields, or a flat mapping of ``(u, v) -> coefficient`` where
    diagonal entries are binary linear terms.
    """
    parsed = _parse_qubo(qubo, offset=offset, variables=variables)
    order = parsed["variables"]
    linear_binary = parsed["linear"]
    quadratic_binary = parsed["quadratic"]

    linear_spin = {variable: linear_binary.get(variable, 0.0) / 2.0 for variable in order}
    quadratic_spin: dict[tuple[Variable, Variable], float] = {}
    ising_offset = parsed["offset"]

    for variable in order:
        ising_offset += linear_binary.get(variable, 0.0) / 2.0

    for (left, right), coefficient in quadratic_binary.items():
        coupling = coefficient / 4.0
        quadratic_spin[(left, right)] = coupling
        linear_spin[left] += coupling
        linear_spin[right] += coupling
        ising_offset += coupling

    conversion_metadata = {
        "source_format": source_format,
        "input_offset": parsed["offset"],
        "conversion_offset": ising_offset,
        "variable_order": list(order),
        "qubo_term_convention": (
            "linear terms plus upper-triangle quadratic terms; symmetric duplicate "
            "pair entries are summed before conversion"
        ),
    }
    if metadata:
        conversion_metadata.update(metadata)

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
    source_format: str = "ising",
) -> IsingModel:
    """Normalize Ising fields and couplings into canonical variable order."""
    parsed = _parse_ising(h, J, offset=offset, variables=variables)
    model_metadata = {
        "source_format": source_format,
        "input_offset": parsed["offset"],
        "conversion_offset": parsed["offset"],
        "variable_order": list(parsed["variables"]),
    }
    if metadata:
        model_metadata.update(metadata)

    return IsingModel(
        variables=parsed["variables"],
        linear=parsed["linear"],
        quadratic=parsed["quadratic"],
        offset=parsed["offset"],
        source_format=source_format,
        metadata=model_metadata,
    )


def compile_bqm(bqm: Any, *, metadata: Mapping[str, Any] | None = None) -> IsingModel:
    """Normalize a dimod-style BinaryQuadraticModel into the canonical Ising IR.

    The function has no hard dependency on dimod. If the object exposes
    ``to_ising()``, that method is used. Otherwise, a duck-typed object with
    ``linear``, ``quadratic``, ``offset``, and ``vartype`` attributes is accepted.
    """
    model_metadata = {"source_format": "bqm"}
    if metadata:
        model_metadata.update(metadata)

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
        return compile_ising(
            h,
            J,
            offset=float(ising_offset),
            variables=variables,
            metadata=model_metadata,
            source_format="bqm",
        )

    vartype = normalize_vartype(getattr(bqm, "vartype", None))
    linear = dict(getattr(bqm, "linear"))
    quadratic = dict(getattr(bqm, "quadratic"))
    input_offset = float(getattr(bqm, "offset", 0.0))
    variables = _variables_from_bqm(bqm) or _variables_from_terms(linear, _normalize_pairs(quadratic, None))
    model_metadata.update({"bqm_vartype": vartype, "input_offset": input_offset})

    if vartype == "SPIN":
        return compile_ising(
            linear,
            quadratic,
            offset=input_offset,
            variables=variables,
            metadata=model_metadata,
            source_format="bqm",
        )
    return compile_qubo(
        {"variables": list(variables), "linear": linear, "quadratic": quadratic, "offset": input_offset},
        metadata=model_metadata,
        source_format="bqm",
    )


def _parse_qubo(
    qubo: Mapping[Any, Any],
    *,
    offset: float | None,
    variables: list[Variable] | tuple[Variable, ...] | None,
) -> dict[str, Any]:
    if _is_structured_model(qubo):
        raw_variables = variables if variables is not None else qubo.get("variables")
        raw_offset = qubo.get("offset", 0.0) if offset is None else offset
        linear = {key: float(value) for key, value in dict(qubo.get("linear", {})).items()}
        term_items = dict(qubo.get("quadratic", {})).items()
    else:
        raw_variables = variables
        raw_offset = 0.0 if offset is None else offset
        linear = {}
        term_items = qubo.items()

    # Binary diagonal entries (u == u) are linear terms; off-diagonal entries are
    # accumulated onto their canonically-ordered pair.
    index = variable_index(raw_variables) if raw_variables is not None else None
    quadratic: dict[tuple[Variable, Variable], float] = {}
    for key, value in term_items:
        left, right = _parse_pair_key(key)
        coefficient = float(value)
        if left == right:
            linear[left] = linear.get(left, 0.0) + coefficient
        else:
            pair = _ordered_pair(left, right, index)
            quadratic[pair] = quadratic.get(pair, 0.0) + coefficient

    return _finish(raw_variables, linear, quadratic, float(raw_offset))


def _parse_ising(
    h: Mapping[Any, Any],
    J: Mapping[Any, Any] | None,
    *,
    offset: float | None,
    variables: list[Variable] | tuple[Variable, ...] | None,
) -> dict[str, Any]:
    if J is None and _is_structured_model(h):
        raw_variables = variables if variables is not None else h.get("variables")
        raw_offset = h.get("offset", 0.0) if offset is None else offset
        linear = {key: float(value) for key, value in dict(h.get("linear", {})).items()}
        quadratic_input = dict(h.get("quadratic", {}))
    else:
        raw_variables = variables
        raw_offset = 0.0 if offset is None else offset
        linear = {key: float(value) for key, value in dict(h).items()}
        quadratic_input = {} if J is None else dict(J)

    index = variable_index(raw_variables) if raw_variables is not None else None
    quadratic: dict[tuple[Variable, Variable], float] = {}
    folded_offset = float(raw_offset)
    for key, value in quadratic_input.items():
        left, right = _parse_pair_key(key)
        coefficient = float(value)
        if left == right:
            folded_offset += coefficient
            continue
        pair = _ordered_pair(left, right, index)
        quadratic[pair] = quadratic.get(pair, 0.0) + coefficient

    return _finish(raw_variables, linear, quadratic, folded_offset)


def _is_structured_model(value: Mapping[Any, Any]) -> bool:
    return any(key in value for key in ("linear", "quadratic", "variables", "offset"))


def _complete_linear(variables: tuple[Variable, ...], linear: Mapping[Variable, float]) -> dict[Variable, float]:
    return {variable: float(linear.get(variable, 0.0)) for variable in variables}


def _finish(
    raw_variables: list[Variable] | tuple[Variable, ...] | None,
    linear: Mapping[Variable, float],
    quadratic: Mapping[tuple[Variable, Variable], float],
    offset: float,
) -> dict[str, Any]:
    """Resolve variable order and normalize the parsed terms into the parse result.

    Shared tail of ``_parse_qubo`` and ``_parse_ising``; the two parsers differ
    only in how each routes diagonal terms (QUBO -> linear, Ising -> offset).
    """
    order = _resolve_variables(raw_variables, linear, quadratic)
    return {
        "variables": order,
        "linear": _complete_linear(order, linear),
        "quadratic": _normalize_pairs(quadratic, order),
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
        labels = set(linear)
        for left, right in quadratic:
            labels.add(left)
            labels.add(right)
        order = tuple(sorted(labels, key=variable_sort_key))

    if len(set(order)) != len(order):
        raise ValueError("variables must be unique")
    known = set(order)
    referenced = set(linear) | {variable for pair in quadratic for variable in pair}
    unknown = referenced - known
    if unknown:
        raise ValueError(f"terms reference variables not present in variable order: {sorted(unknown, key=variable_sort_key)!r}")
    return order


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
    """Human-readable vartype label from a dimod-style object (its enum ``.name``)."""
    vartype = getattr(bqm, "vartype", None)
    return str(getattr(vartype, "name", getattr(bqm, "vartype", "unknown")))


def _normalize_pairs(
    terms: Mapping[Any, Any],
    variables: list[Variable] | tuple[Variable, ...] | None,
) -> dict[tuple[Variable, Variable], float]:
    index = variable_index(variables) if variables is not None else None
    normalized: dict[tuple[Variable, Variable], float] = {}
    for key, value in terms.items():
        left, right = _parse_pair_key(key)
        if left == right:
            normalized[(left, right)] = normalized.get((left, right), 0.0) + float(value)
            continue
        pair = _ordered_pair(left, right, index)
        normalized[pair] = normalized.get(pair, 0.0) + float(value)
    if index is None:
        return dict(sorted(normalized.items(), key=lambda item: (variable_sort_key(item[0][0]), variable_sort_key(item[0][1]))))
    return dict(sorted(normalized.items(), key=lambda item: (index.get(item[0][0], 10**9), index.get(item[0][1], 10**9))))


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
    """Order a pair by ``index`` position, or by ``variable_sort_key`` when unindexed."""
    if index is None:
        return (left, right) if variable_sort_key(left) <= variable_sort_key(right) else (right, left)
    if left not in index or right not in index:
        return left, right
    return (left, right) if index[left] < index[right] else (right, left)
