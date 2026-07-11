"""Small recursive freeze/thaw helpers for audit evidence containers."""

from __future__ import annotations

import copy
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


def freeze(value: Any) -> Any:
    """Return a recursively immutable defensive copy of JSON-shaped data."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze(child) for key, child in value.items()})
    if isinstance(value, (list, tuple)):
        return FrozenSequence(freeze(child) for child in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(freeze(child) for child in value)
    return copy.deepcopy(value)


def thaw(value: Any) -> Any:
    """Return a detached mutable JSON-shaped copy of recursively frozen data."""
    if isinstance(value, Mapping):
        return {key: thaw(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return [thaw(child) for child in value]
    if isinstance(value, (set, frozenset)):
        return [thaw(child) for child in value]
    return copy.deepcopy(value)
