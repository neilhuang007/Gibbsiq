"""Shared verification for trusted pinned optional integration stacks."""

from __future__ import annotations

import hashlib
import importlib.metadata
from collections.abc import Mapping
from pathlib import Path
import sys

from gibbsiq.qualification.engine import UnsupportedCapabilityError


def verify_stack(
    *,
    adapter: str,
    module_file: str,
    distribution_versions: Mapping[str, str],
    source_hashes: Mapping[str, str],
    source_revision: str,
    python_version: tuple[int, int, int] = (3, 13, 5),
) -> None:
    """Reject an optional stack that differs from its tested compatibility envelope."""
    for name, expected in distribution_versions.items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as error:
            raise UnsupportedCapabilityError(
                f"{adapter} adapter requires pinned {name}=={expected}"
            ) from error
        if actual != expected:
            raise UnsupportedCapabilityError(f"{adapter} adapter requires pinned {name}=={expected}")
    if sys.version_info[:3] != python_version:
        version = ".".join(str(part) for part in python_version)
        raise UnsupportedCapabilityError(
            f"{adapter} adapter requires pinned Python {version} integration environment"
        )
    root = Path(module_file).parent
    for name, expected in source_hashes.items():
        try:
            actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
        except OSError as error:
            raise UnsupportedCapabilityError(f"{adapter} source {name} is unavailable") from error
        if actual != expected:
            raise UnsupportedCapabilityError(f"{adapter} source {name} differs from pinned {source_revision}")


__all__ = ["verify_stack"]
