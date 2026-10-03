"""Static local capability report for qualification workflows."""

from __future__ import annotations

from importlib import metadata, util
import platform
from pathlib import Path
import shutil
import sys
from typing import Any

from gibbsiq import __version__


_OPTIONAL = (
    ("numpy", "numpy", "2.4.6"),
    ("jax", "jax", "0.10.2"),
    ("jaxlib", "jaxlib", "0.10.2"),
    ("equinox", "equinox", "0.13.8"),
    ("thrml", "thrml", "0.1.4"),
    ("extro-torx", "torx", "0.0.1"),
    ("z1t", "z1t", None),
)


def _version(distribution: str) -> str | None:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return None


def doctor_report() -> dict[str, Any]:
    """Report package metadata and module discoverability without importing backends."""
    optional = []
    for distribution, module, supported_version in _OPTIONAL:
        optional.append(
            {
                "distribution": distribution,
                "version": _version(distribution),
                "supported_version": supported_version,
                "module": module,
                "module_available": util.find_spec(module) is not None,
                "compatibility": "unverified_by_doctor",
            }
        )
    disk = shutil.disk_usage(Path(__file__).anchor)
    return {
        "package": {"name": "gibbsiq", "version": __version__},
        "python": platform.python_version(),
        "platform": platform.platform(),
        "optional": optional,
        "local_disk": {"total_bytes": disk.total, "free_bytes": disk.free},
        "source_support": [
            {
                "name": "thrml",
                "revision": "9c4e6fbb800f5e5c627122e668ff1b158ef3782b",
                "setup_reference": "data/qualification/QUICKSTART.md; https://github.com/extropic-ai/thrml/tree/9c4e6fbb800f5e5c627122e668ff1b158ef3782b",
            },
            {
                "name": "extro-torx",
                "revision": "f8a46c12615019a96997f294ce07f6c2d50cfc82",
                "setup_reference": "data/qualification/QUICKSTART.md; https://github.com/extropic-ai/torx/tree/f8a46c12615019a96997f294ce07f6c2d50cfc82",
            },
            {
                "name": "sparse-transformers/research/z1t",
                "revision": "13051e90df9669be5b8f9f34fb097329fa82f674",
                "setup_reference": "data/qualification/QUICKSTART.md; https://github.com/extropic-ai/sparse-transformers/tree/13051e90df9669be5b8f9f34fb097329fa82f674/research/z1t",
            },
        ],
        "supported_profiles": [
            {
                "profile": "spin-conditional-iid-v1",
                "requirements": [],
                "kind": "software",
            },
            {
                "profile": "ideal-tanh-iid-v1",
                "requirements": ["numpy", "jax"],
                "kind": "software-emulation",
                "setup_reference": "qualification optional dependencies and pinned Z1T source recipe",
            },
            {
                "profile": "dy4p-conditional-iid-v1",
                "requirements": ["numpy", "jax"],
                "kind": "software-emulation",
                "scope": "one local scalar; no whole-model support",
                "setup_reference": "data/qualification/QUICKSTART.md",
            },
            {
                "profile": "torx-two-gate-dfg-v1",
                "requirements": ["numpy", "jax", "extro-torx"],
                "kind": "software-simulator",
                "setup_reference": "pinned Torx compatibility recipe",
            },
        ],
        "limitations": [
            "Installed distributions do not establish source compatibility or a passing backend test.",
            "Doctor performs metadata and local filesystem inspection only; it does not establish backend execution or physical hardware access.",
            f"Interpreter executable: {sys.executable}",
        ],
    }


__all__ = ["doctor_report"]
