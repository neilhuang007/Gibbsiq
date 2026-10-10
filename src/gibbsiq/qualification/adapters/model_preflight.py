"""Nonexecuting resource preflight for the pinned public Z1T-0 checkpoint.

This module uses only the standard library. It neither imports the numerical
backend nor fetches or deserializes the checkpoint.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from gibbsiq.qualification._validation import _integer


@dataclass(frozen=True, slots=True)
class Z1TShape:
    vocab: int = 8
    sequence: int = 4
    n_layers: int = 1
    n_embed: int = 8
    aft_heads: int = 4
    aft_ksize: int = 4
    linear_fan_in: int = 4

    def __post_init__(self) -> None:
        for field in ("vocab", "sequence", "n_layers", "n_embed", "aft_heads", "aft_ksize", "linear_fan_in"):
            _integer(getattr(self, field), name=field, minimum=1)
        if self.n_embed % 2 or self.n_embed % self.aft_heads:
            raise ValueError("n_embed must be even and divisible by aft_heads")


def _linear_array_bytes(input_width: int, output_width: int, fan_in: int) -> int:
    selected = min(input_width, fan_in)
    if selected == input_width:
        return 4 * output_width * (input_width + 1)
    return 4 * output_width * (2 * selected + 1)


def estimate_z1t_array_bytes(shape: Z1TShape) -> int:
    """Count pinned float32/int32 model-array leaves, without execution buffers."""
    if not isinstance(shape, Z1TShape):
        raise ValueError("shape must be a Z1TShape")

    width = shape.n_embed
    floats = (
        shape.vocab * width  # embedding
        + shape.vocab * width
        + shape.vocab  # dense classifier
        + shape.sequence * width  # positional table
        + (2 * width + 1)  # final DyT/norm
        + shape.n_layers * (2 * (2 * width + 1) + shape.aft_heads * shape.aft_ksize)
    )
    projections = (
        _linear_array_bytes(width, 2 * width + shape.aft_heads, shape.linear_fan_in)
        + _linear_array_bytes(width, width, shape.linear_fan_in)
        + _linear_array_bytes(width, 4 * width, shape.linear_fan_in)
        + _linear_array_bytes(4 * width, width, shape.linear_fan_in)
    )
    return 4 * floats + shape.n_layers * projections


PINNED_SOURCE_REVISION = "13051e90df9669be5b8f9f34fb097329fa82f674"
PINNED_CHECKPOINT_REVISION = "b5c244cee26b7f4e613b9ddbe83e83b2962ab2e1"
RELEASED_CHECKPOINT_SHA256 = "02577f67eade622036b35eb2200e890045bea1b626ddac1a2004afc882246dcc"
RELEASED_CONFIG_BYTES = 282
RELEASED_CONFIG_SHA256 = "5980a7f0fc2c0afcf1e6fe43aa7f1538b4c1c39adcb8194d62f417b8bea1a227"
REQUIRED_DEPENDENCIES = ("jax", "equinox", "numpy", "z1t", "tiktoken", "huggingface_hub")


@dataclass(frozen=True, slots=True)
class PinnedReleasedCheckpoint:
    source_revision: str
    checkpoint_revision: str
    checkpoint_bytes: int
    shape: Z1TShape
    weights_license: str | None
    tokenizer_note: str


RELEASED_Z1T0 = PinnedReleasedCheckpoint(
    source_revision=PINNED_SOURCE_REVISION,
    checkpoint_revision=PINNED_CHECKPOINT_REVISION,
    checkpoint_bytes=4_968_300_072,
    shape=Z1TShape(50_257, 256, 4, 12_288, 4, 4, 4),
    weights_license=None,
    tokenizer_note="GPT-2/tiktoken inferred from source and research context, unverified by checkpoint metadata",
)


@dataclass(frozen=True, slots=True)
class PreflightReport:
    ready: bool
    issues: tuple[str, ...]
    model_array_bytes: int
    estimated_peak_bytes: int
    required_disk_bytes: int
    notes: tuple[str, ...]


def preflight_checkpoint(
    *,
    memory_bytes: int,
    disk_bytes: int,
    source_revision: str = PINNED_SOURCE_REVISION,
    checkpoint_revision: str = PINNED_CHECKPOINT_REVISION,
    shape: Z1TShape = RELEASED_Z1T0.shape,
    source_tree_verified: bool = False,
    parameter_tree_verified: bool = False,
    tokenizer_verified: bool = False,
    license_basis: str | None = None,
    installed_dependencies: Collection[str] = (),
) -> PreflightReport:
    """Check declared Z1T-0 loading prerequisites without loading or fetching.

    The caller supplies verification declarations. A ready report is only a
    preflight result; it does not establish access rights or authorize loading.
    """
    for name, value in (("memory_bytes", memory_bytes), ("disk_bytes", disk_bytes)):
        _integer(value, name=name, minimum=0)
    for name, revision in (
        ("source_revision", source_revision),
        ("checkpoint_revision", checkpoint_revision),
    ):
        if type(revision) is not str or not revision.strip():
            raise ValueError(f"{name} must be a nonblank string")
    if not isinstance(shape, Z1TShape):
        raise ValueError("shape must be a Z1TShape")
    for name, value in (
        ("source_tree_verified", source_tree_verified),
        ("parameter_tree_verified", parameter_tree_verified),
        ("tokenizer_verified", tokenizer_verified),
    ):
        if type(value) is not bool:
            raise ValueError(f"{name} must be a boolean")
    if license_basis is not None and type(license_basis) is not str:
        raise ValueError("license_basis must be a string or None")
    if isinstance(installed_dependencies, (str, bytes)) or not isinstance(installed_dependencies, Collection):
        raise ValueError("installed_dependencies must be a collection of package names")
    if any(type(name) is not str or not name.strip() for name in installed_dependencies):
        raise ValueError("installed_dependencies must contain nonblank package names")

    model_array_bytes = estimate_z1t_array_bytes(shape)
    estimated_peak_bytes = (
        3 * model_array_bytes
        + RELEASED_Z1T0.checkpoint_bytes
        + 4 * shape.sequence * shape.n_embed * 4
        + 2 * shape.sequence * shape.vocab * 4
    )
    required_disk_bytes = 2 * RELEASED_Z1T0.checkpoint_bytes
    issues: list[str] = []
    if source_revision != PINNED_SOURCE_REVISION:
        issues.append("source revision differs from the pinned implementation")
    if checkpoint_revision != PINNED_CHECKPOINT_REVISION:
        issues.append("checkpoint revision differs from the pinned artifact")
    if shape != RELEASED_Z1T0.shape:
        issues.append("checkpoint config shape differs from the pinned artifact")
    if not source_tree_verified:
        issues.append("source tree verification is missing")
    if not parameter_tree_verified:
        issues.append("parameter tree compatibility is unverified")
    if not tokenizer_verified:
        issues.append("tokenizer compatibility is unverified")
    if license_basis is None or not license_basis.strip():
        issues.append("weights license basis is unresolved")
    installed = {name.strip().lower().replace("-", "_") for name in installed_dependencies}
    for dependency in REQUIRED_DEPENDENCIES:
        if dependency not in installed:
            issues.append(f"missing dependency: {dependency}")
    if memory_bytes < estimated_peak_bytes:
        issues.append("memory budget is below the conservative estimated peak")
    if disk_bytes < required_disk_bytes:
        issues.append("disk budget is below the required download and working copies")

    return PreflightReport(
        ready=not issues,
        issues=tuple(issues),
        model_array_bytes=model_array_bytes,
        estimated_peak_bytes=estimated_peak_bytes,
        required_disk_bytes=required_disk_bytes,
        notes=(
            "Estimate assumes pinned float32/int32 array leaves and explicit initialization, deserialization, and execution buffers; actual compiler/runtime peak may be higher.",
            "Checkpoint metadata does not declare a weights license or tokenizer; caller declarations require independent review.",
            "A ready preflight does not fetch, deserialize, authorize, or execute the checkpoint.",
        ),
    )
