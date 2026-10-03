"""Shared verification for trusted pinned optional integration stacks."""

from __future__ import annotations

import hashlib
import importlib.metadata
from collections.abc import Mapping
from pathlib import Path
import sys

from gibbsiq.qualification.engine import UnsupportedCapabilityError


def _source_digest(path: Path) -> str:
    payload = path.read_bytes()
    if path.suffix == ".py":
        payload = payload.replace(b"\r\n", b"\n")
    return hashlib.sha256(payload).hexdigest()


def verify_stack(
    *,
    adapter: str,
    module_file: str,
    distribution_versions: Mapping[str, str],
    source_hashes: Mapping[str, str],
    source_revision: str,
    python_version: tuple[int, int, int] | None = (3, 13, 5),
    error_type: type[Exception] = UnsupportedCapabilityError,
    wrap_missing: bool = True,
) -> None:
    """Reject an optional stack that differs from its tested compatibility envelope."""
    for name, expected in distribution_versions.items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as error:
            if not wrap_missing:
                raise
            raise error_type(f"{adapter} adapter requires pinned {name}=={expected}") from error
        if actual != expected:
            raise error_type(f"{adapter} adapter requires pinned {name}=={expected}")
    if python_version is not None and sys.version_info[:3] != python_version:
        version = ".".join(str(part) for part in python_version)
        raise error_type(f"{adapter} adapter requires pinned Python {version} integration environment")
    root = Path(module_file).parent
    for name, expected in source_hashes.items():
        try:
            actual = _source_digest(root / name)
        except OSError as error:
            if not wrap_missing:
                raise
            raise error_type(f"{adapter} source {name} is unavailable") from error
        if actual != expected:
            raise error_type(f"{adapter} source {name} differs from pinned {source_revision}")


__all__ = ["verify_stack"]
