"""Small recursive freeze/thaw helpers for audit evidence containers."""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any


class FrozenSequence(tuple[Any, ...]):
    """Tuple-backed sequence that retains value equality with JSON lists."""

    __hash__ = None  # type: ignore[assignment]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Sequence) and not isinstance(other, (str, bytes, bytearray)):
            return tuple.__eq__(self, tuple(other))
        return False


def _stable_set_sort_key(value: Any) -> tuple[Any, ...]:
    """Typed canonical key for supported set members; never falls back to repr."""
    value_type = type(value)
    if value is None:
        return ("none",)
    if value_type is bool:
        return ("bool", value)
    if value_type is int:
        return ("int", str(value))
    if value_type is float:
        return ("float", value.hex())
    if value_type is str:
        return ("str", value)
    if value_type is bytes:
        return ("bytes", value.hex())
    if value_type is tuple:
        return ("tuple", tuple(_stable_set_sort_key(child) for child in value))
    if value_type is frozenset:
        return (
            "frozenset",
            tuple(sorted(_stable_set_sort_key(child) for child in value)),
        )
    raise TypeError(
        "cannot deterministically serialize set member of type "
        f"{value_type.__module__}.{value_type.__qualname__}"
    )


def _freeze_hashable(value: Any) -> Any:
    """Freeze one existing set member without turning tuples unhashable."""
    if type(value) is tuple:
        return tuple(_freeze_hashable(child) for child in value)
    if type(value) is frozenset:
        return frozenset(_freeze_hashable(child) for child in value)
    return copy.deepcopy(value)


def freeze(value: Any) -> Any:
    """Return a recursively immutable defensive copy of JSON-shaped data."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze(child) for key, child in value.items()})
    if isinstance(value, (list, tuple)):
        return FrozenSequence(freeze(child) for child in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_hashable(child) for child in value)
    return copy.deepcopy(value)


def freeze_json_evidence(value: Any, *, name: str) -> Any:
    """Freeze JSON evidence while rejecting keys/values that JSON would coerce or lose."""
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, child in value.items():
            if type(key) is not str:
                raise TypeError(
                    f"{name} mapping keys must be exact strings, got "
                    f"{type(key).__module__}.{type(key).__qualname__}"
                )
            frozen[key] = freeze_json_evidence(child, name=f"{name}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return FrozenSequence(
            freeze_json_evidence(child, name=f"{name}[{position}]") for position, child in enumerate(value)
        )
    if isinstance(value, (set, frozenset)):
        children = [_freeze_json_set_member(child, name=f"{name} set member") for child in value]
        try:
            return frozenset(children)
        except TypeError as error:
            raise TypeError(f"unsupported {name} set member: value is not hashable after freezing") from error
    value_type = type(value)
    if value is None or value_type in {bool, int, str}:
        return value
    if value_type is float:
        if not math.isfinite(value):
            raise ValueError(f"{name} floating-point value must be finite")
        return value
    evidence_kind = name.split(".", 1)[0].split("[", 1)[0]
    raise TypeError(
        f"unsupported {evidence_kind} value at {name}: {value_type.__module__}.{value_type.__qualname__}"
    )


def _freeze_json_set_member(value: Any, *, name: str) -> Any:
    """Validate and freeze a JSON-evidence set member while preserving hashability."""
    if type(value) is tuple:
        return tuple(
            _freeze_json_set_member(child, name=f"{name}[{position}]") for position, child in enumerate(value)
        )
    if type(value) is frozenset:
        return frozenset(_freeze_json_set_member(child, name=f"{name} set member") for child in value)
    frozen = freeze_json_evidence(value, name=name)
    try:
        hash(frozen)
    except TypeError as error:
        raise TypeError(f"unsupported {name}: value is not hashable after freezing") from error
    return frozen


def thaw(value: Any) -> Any:
    """Return a detached mutable JSON-shaped copy of recursively frozen data."""
    if isinstance(value, Mapping):
        return {key: thaw(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return [thaw(child) for child in value]
    if isinstance(value, (set, frozenset)):
        return [thaw(child) for child in sorted(value, key=_stable_set_sort_key)]
    return copy.deepcopy(value)
