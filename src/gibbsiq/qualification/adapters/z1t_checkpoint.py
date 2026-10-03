"""Trusted-local loading for the pinned Z1T checkpoint structure."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
import stat
from typing import Any

from gibbsiq.qualification.adapters.model_preflight import RELEASED_CHECKPOINT_SHA256, RELEASED_Z1T0
from gibbsiq.qualification.adapters.z1t import NumericalZ1T, TinyZ1TConfig, _load_backend


_TINY_MAX_BYTES = 16 * 1024 * 1024
_CHUNK_ELEMENTS = 262_144


@dataclass(frozen=True, slots=True)
class _ReleasedZ1TConfig:
    vocab: int = RELEASED_Z1T0.shape.vocab
    sequence: int = RELEASED_Z1T0.shape.sequence
    n_layers: int = RELEASED_Z1T0.shape.n_layers
    n_embed: int = RELEASED_Z1T0.shape.n_embed
    aft_heads: int = RELEASED_Z1T0.shape.aft_heads
    aft_ksize: int = RELEASED_Z1T0.shape.aft_ksize
    linear_fan_in: int = RELEASED_Z1T0.shape.linear_fan_in
    dyt_alpha: float = 0.5
    aft_kind: str = "conv"
    attn_fan_in: int | None = None
    mlp_fan_in: int | None = None
    tanh_linear: bool = True
    tanh_mlp: bool = True
    remat: bool = True


def _is_link(path: Path) -> bool:
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(attributes & reparse)


def _file_identity(path: Path, *, maximum: int) -> tuple[int, str]:
    if not path.exists() or _is_link(path) or not path.is_file():
        raise ValueError("checkpoint path must name a regular local file")
    size = path.stat().st_size
    if not 0 < size <= maximum:
        raise ValueError("checkpoint file size is outside the permitted bound")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    if path.stat().st_size != size:
        raise ValueError("checkpoint changed during identity verification")
    return size, digest.hexdigest()


def _upstream_config(config: TinyZ1TConfig | _ReleasedZ1TConfig, components: Any) -> Any:
    if isinstance(config, _ReleasedZ1TConfig):
        return components.Config(**asdict(config))
    return components.Config(
        **asdict(config),
        aft_kind="conv",
        attn_fan_in=None,
        mlp_fan_in=None,
        tanh_linear=True,
        tanh_mlp=True,
        remat=False,
    )


def _cpu_host_view(leaf: Any, *, np: Any) -> Any:
    devices = leaf.devices()
    if not devices or any(device.platform != "cpu" for device in devices):
        raise ValueError("checkpoint loading requires CPU-resident JAX arrays")
    host = np.asarray(leaf)
    if not np.shares_memory(host, np.asarray(leaf)):
        raise ValueError("checkpoint CPU leaf does not expose a shared host view")
    return host


def _validate_loaded_tree(model: Any, *, backend: tuple[Any, Any, Any, Any]) -> None:
    jax, _, np, upstream = backend
    components, _ = upstream
    for leaf in jax.tree_util.tree_leaves(model):
        if not isinstance(leaf, jax.Array):
            continue
        if np.dtype(leaf.dtype).kind not in "fc":
            continue
        flat = _cpu_host_view(leaf, np=np).reshape(-1)
        for start in range(0, int(flat.size), _CHUNK_ELEMENTS):
            if not np.isfinite(flat[start : start + _CHUNK_ELEMENTS]).all():
                raise ValueError("checkpoint contains nonfinite numerical leaves")

    for block in model.blocks:
        projections = (
            block.attn.qkv_proj,
            block.attn.out_proj,
            block.mlp.proj1,
            block.mlp.proj2,
        )
        for projection in projections:
            linear = projection.linear
            if not isinstance(linear, components.SparseLinear):
                raise ValueError("checkpoint has an unsupported projection structure")
            flat = _cpu_host_view(linear.indices, np=np).reshape(-1)
            for start in range(0, int(flat.size), _CHUNK_ELEMENTS):
                values = flat[start : start + _CHUNK_ELEMENTS]
                if np.any(values < 0) or np.any(values >= linear.in_features):
                    raise ValueError("checkpoint sparse index is outside its input width")


def load_z1t_checkpoint(path: str | Path, *, config: TinyZ1TConfig | None = None) -> NumericalZ1T:
    """Load one trusted local Equinox checkpoint without network or remote code.

    ``config=None`` is reserved for the exact released Z1T-0 artifact. Supplying
    a bounded ``TinyZ1TConfig`` permits local fixtures with the same pinned
    architecture; it does not claim that such a fixture was trained.
    """
    if config is not None and not isinstance(config, TinyZ1TConfig):
        raise ValueError("config must be TinyZ1TConfig or None")
    checkpoint = Path(path)
    maximum = RELEASED_Z1T0.checkpoint_bytes if config is None else _TINY_MAX_BYTES
    size, digest = _file_identity(checkpoint, maximum=maximum)
    metadata: TinyZ1TConfig | _ReleasedZ1TConfig
    if config is None:
        if size != RELEASED_Z1T0.checkpoint_bytes or digest != RELEASED_CHECKPOINT_SHA256:
            raise ValueError("checkpoint is not the exact released Z1T-0 artifact")
        metadata = _ReleasedZ1TConfig()
    else:
        metadata = config

    backend = _load_backend()
    jax, _, _, upstream = backend
    components, model_module = upstream
    try:
        import equinox as eqx

        shape = _upstream_config(metadata, components)
        skeleton = eqx.filter_eval_shape(model_module.create_model, shape, jax.random.key(0))
        with checkpoint.open("rb") as stream:
            model = eqx.tree_deserialise_leaves(stream, skeleton)
            if stream.read(1):
                raise ValueError("checkpoint contains trailing bytes")
    except (EOFError, OSError, RuntimeError, TypeError) as error:
        raise ValueError("checkpoint does not match the pinned Z1T structure") from error

    _validate_loaded_tree(model, backend=backend)
    return NumericalZ1T._from_loaded_model(metadata, model, checkpoint_digest=digest, backend=backend)
