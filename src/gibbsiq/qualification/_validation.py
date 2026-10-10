"""Shared strict validation helpers for qualification values."""

from __future__ import annotations

import math
from collections.abc import Mapping, Set as AbstractSet
from typing import Any


def _integer(value: Any, *, name: str, minimum: int, maximum: int | None = None) -> int:
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        if maximum is not None:
            raise ValueError(f"{name} must be an integer from {minimum} through {maximum}")
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _finite(value: Any, *, name: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name} must be a finite number") from error
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return 0.0 if result == 0.0 else result


def _probability(value: Any, *, name: str) -> float:
    result = _finite(value, name=name)
    if not 0.0 < result < 1.0:
        raise ValueError(f"{name} must be strictly between zero and one")
    return result


def _json_object(
    value: object,
    expected: AbstractSet[str],
    *,
    name: str,
    optional: AbstractSet[str] = frozenset(),
    require_dict: bool = False,
) -> Mapping[str, Any]:
    """Return a closed-schema JSON object with exact string field names."""
    if require_dict:
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be a JSON object")
        source: Mapping[Any, Any] = value
    else:
        if not isinstance(value, Mapping):
            raise ValueError(f"{name} must be a JSON object")
        source = value
    if any(type(key) is not str for key in source):
        raise ValueError(f"{name} must use exact string field names")
    missing = expected - source.keys()
    unknown = source.keys() - expected - optional
    if missing or unknown:
        raise ValueError(
            f"{name} has unexpected schema fields: missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    return source


def _mean(values: tuple[float, ...]) -> float:
    """Return a finite mean without losing constant extreme observations."""
    if len(values) == 1 or all(value == values[0] for value in values[1:]):
        return values[0]
    try:
        result = math.fsum(values) / len(values)
    except OverflowError:
        anchor = values[0]
        try:
            displacement = math.fsum((value - anchor) / len(values) for value in values)
            result = anchor + displacement
        except OverflowError as error:
            raise ValueError("sample mean exceeds finite binary64 range") from error
    if not math.isfinite(result):
        raise ValueError("sample mean must remain finite")
    return 0.0 if result == 0.0 else result
