"""Input normalization for QUBO, Ising, and optional dimod BQM objects."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
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
    """QUBO -> Ising IR. Accepts {linear,quadratic,...} fixture shape or flat
    {(u,v): coefficient} map; diagonal entries are binary linear terms.
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
    source_format: str = "ising",
) -> IsingModel:
    """h,J -> Ising IR in canonical variable order."""
    parsed = _parse_ising(h, J, offset=offset, variables=variables)
    model_metadata = dict(metadata or {})
    model_metadata.update(
        {
            "source_format": source_format,
            "input_offset": parsed["offset"],
            "conversion_offset": parsed["offset"],
            "variable_order": list(parsed["variables"]),
        }
    )

    return IsingModel(
        variables=parsed["variables"],
        linear=parsed["linear"],
        quadratic=parsed["quadratic"],
        offset=parsed["offset"],
        source_format=source_format,
        metadata=model_metadata,
    )


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
        linear = {key: float(value) for key, value in dict(qubo.get("linear", {})).items()}
        term_items = dict(qubo.get("quadratic", {})).items()
    else:
        raw_variables = variables
        raw_offset = 0.0 if offset is None else offset
        linear = {}
        term_items = qubo.items()

    # Diagonal (u==u) -> linear term; off-diagonal accumulated, canonicalized in _finish/_normalize_pairs.
    quadratic: dict[tuple[Variable, Variable], float] = {}
    for key, value in term_items:
        left, right = _parse_pair_key(key)
        coefficient = float(value)
        if left == right:
            linear[left] = linear.get(left, 0.0) + coefficient
        else:
            quadratic[(left, right)] = quadratic.get((left, right), 0.0) + coefficient

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

    quadratic: dict[tuple[Variable, Variable], float] = {}
    folded_offset = float(raw_offset)
    for key, value in quadratic_input.items():
        left, right = _parse_pair_key(key)
        coefficient = float(value)
        if left == right:
            folded_offset += coefficient
            continue
        quadratic[(left, right)] = quadratic.get((left, right), 0.0) + coefficient

    return _finish(raw_variables, linear, quadratic, folded_offset)


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
        raise ValueError(
            f"terms reference variables not present in variable order: {sorted(unknown, key=variable_sort_key)!r}"
        )
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
    """Vartype label from bqm.vartype.name (or the raw value)."""
    vartype = getattr(bqm, "vartype", "unknown")
    return str(getattr(vartype, "name", vartype))


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
