"""Shared strict validation helpers for qualification values."""

from __future__ import annotations

import math
from typing import Any


def _integer(value: Any, *, name: str, minimum: int) -> int:
    if type(value) is not int or value < minimum:
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
