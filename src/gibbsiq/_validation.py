"""Private argument validators shared by the core modules.

Every helper takes the exact error message its call site used to raise.  Message
templates are formatted only when an error is raised, so the success path never
builds a message or calls ``repr``.  Templates may reference ``{name}``,
``{value!r}`` and, for integer bounds, ``{minimum}``.
"""

from __future__ import annotations

import json
from typing import Any

from gibbsiq.model import finite_float

__all__ = [
    "bounded_int",
    "canonical_json",
    "exact_limit",
    "finite_number",
    "nonnegative_beta",
    "nonnegative_float",
    "positive_float",
    "variable_position",
]

_BOOLEAN_NUMBER_MESSAGE = "{name} must be numeric, not boolean"


def canonical_json(value: Any) -> str:
    """Return compact, key-sorted, finite-only JSON text."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def variable_position(value: Any, *, size: int, name: str) -> int:
    """Return ``value`` when it is a non-boolean integer in ``range(size)``."""
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < size:
        raise ValueError(f"{name} must be a valid variable position")
    return value


def bounded_int(
    value: Any,
    *,
    name: str,
    message: str,
    minimum: int | None = 0,
    type_message: str | None = None,
) -> int:
    """Return a non-boolean integer at least ``minimum`` (no bound when ``None``).

    ``type_message`` replaces ``message`` for non-integer input when given.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError((type_message or message).format(name=name, value=value, minimum=minimum))
    if minimum is not None and value < minimum:
        raise ValueError(message.format(name=name, value=value, minimum=minimum))
    return value


def exact_limit(value: Any, *, name: str) -> int:
    """Return a non-negative integer exact-enumeration limit."""
    return bounded_int(value, name=name, message="{name} must be an integer >= 0, got {value!r}")


def finite_number(
    value: Any,
    *,
    name: str,
    bool_message: str = _BOOLEAN_NUMBER_MESSAGE,
) -> float:
    """Return ``float(value)`` after rejecting booleans, NaN and infinity."""
    if isinstance(value, bool):
        raise ValueError(bool_message.format(name=name, value=value))
    return finite_float(value, name=name)


def positive_float(
    value: Any,
    *,
    name: str,
    sign_message: str,
    bool_message: str = _BOOLEAN_NUMBER_MESSAGE,
) -> float:
    """Return a finite float strictly greater than zero."""
    number = finite_number(value, name=name, bool_message=bool_message)
    if number <= 0.0:
        raise ValueError(sign_message.format(name=name, value=value))
    return number


def nonnegative_float(
    value: Any,
    *,
    name: str,
    sign_message: str,
    bool_message: str = _BOOLEAN_NUMBER_MESSAGE,
    normalize_negative_zero: bool = False,
) -> float:
    """Return a finite float that is at least zero, optionally mapping -0.0 to 0.0."""
    number = finite_number(value, name=name, bool_message=bool_message)
    if number < 0.0:
        raise ValueError(sign_message.format(name=name, value=value))
    if normalize_negative_zero and number == 0.0:
        return 0.0
    return number


def nonnegative_beta(value: Any, *, normalize_negative_zero: bool = False) -> float:
    """Return an inverse temperature that is finite and at least zero."""
    return nonnegative_float(
        value,
        name="beta",
        bool_message="{name} must be a finite non-negative number, got {value!r}",
        sign_message="{name} must be non-negative, got {value!r}",
        normalize_negative_zero=normalize_negative_zero,
    )
