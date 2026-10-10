"""Pinned, generated tiny Z1T numerical reference and selected projections.

The observed AFT-conv traversal adapts the expression order in Extropic AI's
``research/z1t/components.py`` and ``model.py`` at sparse-transformers commit
13051e90df9669be5b8f9f34fb097329fa82f674 (Apache-2.0). See
``Z1T_LICENSE.txt``. The upstream model and its modules perform all parameter
initialization; this adapter adds no trainable model or checkpoint loader.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from gibbsiq.qualification._validation import _integer


_SOURCE_COMMIT = "13051e90df9669be5b8f9f34fb097329fa82f674"
_SOURCE_HASHES = {
    "components.py": "12d30188ce5b65da8a249767e41ebb7d78286a1f83fdd635afad3d5c794dab7b",
    "model.py": "542374ffff99130240fc04be692b803ecc7c379c6188b3b9b7528db385516a68",
}


@dataclass(frozen=True, slots=True)
class TinyZ1TConfig:
    vocab: int = 8
    sequence: int = 4
    n_layers: int = 1
    n_embed: int = 8
    aft_heads: int = 4
    aft_ksize: int = 4
    linear_fan_in: int = 4
    dyt_alpha: float = 0.5

    def __post_init__(self) -> None:
        for name, lower, upper in (
            ("vocab", 2, 256),
            ("sequence", 1, 64),
            ("n_layers", 1, 4),
            ("n_embed", 8, 64),
            ("aft_heads", 1, 8),
            ("aft_ksize", 1, 16),
        ):
            _integer(getattr(self, name), name=name, minimum=lower, maximum=upper)
        if self.n_embed % 2 or self.n_embed % self.aft_heads:
            raise ValueError("n_embed must be even and divisible by aft_heads")
        _integer(self.linear_fan_in, name="linear_fan_in", minimum=1, maximum=self.n_embed - 1)
        if isinstance(self.dyt_alpha, bool) or not isinstance(self.dyt_alpha, (int, float)):
            raise ValueError("dyt_alpha must be finite and positive")
        if not math.isfinite(self.dyt_alpha) or self.dyt_alpha <= 0:
            raise ValueError("dyt_alpha must be finite and positive")


@dataclass(frozen=True, slots=True)
class Operation:
    operation_id: str
    kind: str
    input_features: int
    output_features: int
    fan_in: int
    axes: tuple[str, str] = ("token", "feature")


@dataclass(frozen=True, slots=True)
class TensorCapture:
    shape: tuple[int, int]
    axes: tuple[str, str]
    dtype: str
    minimum: float
    maximum: float
    mean: float
    rms: float
    values: Any | None


@dataclass(frozen=True, slots=True)
class OperationCapture:
    inputs: TensorCapture
    field: TensorCapture
    output: TensorCapture


@dataclass(frozen=True, slots=True)
class ForwardResult:
    logits: Any
    captures: Mapping[str, OperationCapture]


def _load_backend() -> tuple[Any, Any, Any, Any]:
    try:
        import jax
        import jax.numpy as jnp
        import numpy as np
        from z1t import components, model
    except ImportError as error:
        raise ImportError(
            "NumericalZ1T needs the pinned z1t research package with JAX, "
            "Equinox and NumPy installed in an optional integration environment"
        ) from error

    if importlib.metadata.version("z1t") != "0.0.1":
        raise RuntimeError("unsupported z1t distribution version; use pinned 0.0.1")
    for filename, expected in _SOURCE_HASHES.items():
        module = components if filename == "components.py" else model
        actual = hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"unsupported z1t source: {filename} differs from {_SOURCE_COMMIT}")
    return jax, jnp, np, (components, model)


def _parameter_identity(model: Any, jax: Any, np: Any) -> str:
    digest = hashlib.sha256()
    for path, leaf in jax.tree_util.tree_flatten_with_path(model)[0]:
        if not isinstance(leaf, jax.Array):
            continue
        array = np.asarray(leaf)
        digest.update(jax.tree_util.keystr(path).encode("utf-8"))
        digest.update(str(array.shape).encode("ascii"))
        digest.update(str(array.dtype).encode("ascii"))
        view = memoryview(np.ascontiguousarray(array)).cast("B")
        for offset in range(0, len(view), 1024 * 1024):
            digest.update(view[offset : offset + 1024 * 1024])
    return digest.hexdigest()


_DEFAULT_CONFIG = TinyZ1TConfig()


class NumericalZ1T:
    """Optional CPU numerical baseline for generated, bounded tiny models."""

    def __init__(self, config: TinyZ1TConfig = _DEFAULT_CONFIG, *, seed: int = 17) -> None:
        if not isinstance(config, TinyZ1TConfig):
            raise ValueError("config must be TinyZ1TConfig")
        _integer(seed, name="seed", minimum=0, maximum=2**32 - 1)
        jax, jnp, np, upstream = _load_backend()
        components, model_module = upstream
        upstream_config = components.Config(
            **asdict(config), aft_kind="conv", tanh_linear=True, tanh_mlp=True, remat=False
        )
        model = model_module.create_model(upstream_config, jax.random.key(seed))
        self._initialize(
            config,
            model,
            (jax, jnp, np, upstream),
            parameter_identity=_parameter_identity(model, jax, np),
            parameter_identity_type="materialized-values-sha256",
            provenance="generated-untrained",
        )

    @classmethod
    def _from_loaded_model(
        cls,
        config: Any,
        model: Any,
        *,
        checkpoint_digest: str,
        backend: tuple[Any, Any, Any, Any],
    ) -> NumericalZ1T:
        instance = cls.__new__(cls)
        instance._initialize(
            config,
            model,
            backend,
            parameter_identity=checkpoint_digest,
            parameter_identity_type="checkpoint-sha256",
            provenance="loaded-local-checkpoint",
        )
        return instance

    def _initialize(
        self,
        config: Any,
        model: Any,
        backend: tuple[Any, Any, Any, Any],
        *,
        parameter_identity: str,
        parameter_identity_type: str,
        provenance: str,
    ) -> None:
        jax, jnp, np, upstream = backend
        components, _ = upstream
        operations: list[Operation] = []
        for index, block in enumerate(model.blocks):
            if not isinstance(block.attn, components.AFTConv):
                raise RuntimeError("unsupported z1t attention structure")
            for site, module in (
                ("attn.qkv_proj", block.attn.qkv_proj),
                ("attn.out_proj", block.attn.out_proj),
                ("mlp.proj1", block.mlp.proj1),
                ("mlp.proj2", block.mlp.proj2),
            ):
                if not isinstance(module, components.TanhLinear) or not isinstance(
                    module.linear, components.SparseLinear
                ):
                    raise RuntimeError(f"unsupported z1t projection structure: {site}")
                linear = module.linear
                operations.append(
                    Operation(
                        f"blocks.{index}.{site}",
                        "tanh_sparse_linear",
                        linear.in_features,
                        linear.out_features,
                        linear.k,
                    )
                )
        self.config = config
        self.model = model
        self.operations = tuple(operations)
        self.source_identity = f"sparse-transformers:{_SOURCE_COMMIT}:z1t:0.0.1"
        self.parameter_identity = parameter_identity
        self.parameter_identity_type = parameter_identity_type
        self.provenance = provenance
        identity = (self.source_identity, asdict(config), [asdict(item) for item in operations])
        self.operation_map_identity = hashlib.sha256(repr(identity).encode("utf-8")).hexdigest()
        self._jax, self._jnp, self._np = jax, jnp, np

    def _tokens(self, tokens: Any) -> Any:
        np, jnp = self._np, self._jnp
        if isinstance(tokens, (str, bytes, bytearray)):
            raise ValueError("tokens must be a rank-one integer sequence")
        try:
            array = np.asarray(tokens)
        except (TypeError, ValueError) as error:
            raise ValueError("tokens must be a rank-one integer sequence") from error
        if array.ndim != 1 or not 1 <= array.size <= self.config.sequence:
            raise ValueError("tokens must be a nonempty rank-one sequence within configured length")
        boolean_in_sequence = not isinstance(tokens, (np.ndarray, self._jax.Array)) and any(
            type(value) is bool for value in tokens
        )
        if array.dtype.kind not in "iu" or boolean_in_sequence:
            raise ValueError("tokens must contain integers, not booleans or floats")
        if np.any(array < 0) or np.any(array >= self.config.vocab):
            raise ValueError("tokens must be within configured vocabulary")
        return jnp.asarray(array, dtype=jnp.int32)

    def forward(
        self,
        tokens: Sequence[int] | Any,
        *,
        observe: Sequence[str] = (),
        retention: str = "summaries",
        max_trace_bytes: int = 1048576,
        transform: Callable[[str, Any, Any, Any], Any] | None = None,
    ) -> ForwardResult:
        if retention not in {"summaries", "trace"}:
            raise ValueError("retention must be 'summaries' or 'trace'")
        _integer(max_trace_bytes, name="max_trace_bytes", minimum=0)
        allowed = {operation.operation_id for operation in self.operations}
        try:
            selected = tuple(observe)
        except TypeError as error:
            raise ValueError("observe must contain operation IDs") from error
        if (
            any(type(item) is not str for item in selected)
            or len(selected) != len(set(selected))
            or any(item not in allowed for item in selected)
        ):
            raise ValueError("observe contains an unknown or duplicate operation ID")
        if transform is not None and not callable(transform):
            raise ValueError("transform must be callable")
        token_array = self._tokens(tokens)
        if not selected and transform is None:
            return ForwardResult(self.model(token_array), MappingProxyType({}))

        # Pinned AFT-conv traversal, preserving upstream ordering and helpers.
        jax, jnp = self._jax, self._jnp
        from z1t.components import _dwconv1d_causal

        pending: dict[str, tuple[Any, Any, Any]] = {}
        trace_bytes = 0

        def project(name: str, projection: Any, x: Any) -> Any:
            nonlocal trace_bytes
            # vmap covers only the upstream per-token affine module. The trusted
            # callback sees the complete token-by-feature arrays once per site.
            field = jax.vmap(projection.linear)(x)
            numerical_output = jnp.tanh(field)
            output = numerical_output if transform is None else transform(name, x, field, numerical_output)
            if (
                not hasattr(output, "shape")
                or not hasattr(output, "dtype")
                or output.shape != numerical_output.shape
                or output.dtype != numerical_output.dtype
            ):
                raise ValueError(f"transform changed shape or dtype at {name}")
            output = jnp.asarray(output)
            if name in selected:
                if retention == "trace":
                    trace_bytes += sum(int(item.size * item.dtype.itemsize) for item in (x, field, output))
                    if trace_bytes > max_trace_bytes:
                        raise ValueError("selected trace exceeds max_trace_bytes")
                pending[name] = (x, field, output)
            return output

        x = jax.vmap(self.model.embedding)(token_array)
        x = self.model.pe(x)
        for index, block in enumerate(self.model.blocks):
            attn = block.attn
            T, dim = x.shape
            h, hd = attn.heads, attn.dim // attn.heads
            attn_input = block.norm1(x)
            qkv = project(f"blocks.{index}.attn.qkv_proj", attn.qkv_proj, attn_input)
            q, v, k = jnp.split(qkv, [dim, 2 * dim], axis=-1)
            qh, vh = q.reshape(T, h, hd), v.reshape(T, h, hd)
            ek = jnp.exp(jnp.tanh(k))
            kernel = jnp.exp(attn.w_conv) - 1.0
            ekv = ek[:, :, None] * vh
            num_conv = _dwconv1d_causal(ekv.reshape(T, dim).T, jnp.repeat(kernel, hd, axis=0)).T.reshape(
                T, h, hd
            )
            den_conv = _dwconv1d_causal(ek.T, kernel).T
            num = num_conv + jnp.cumsum(ekv, axis=0)
            den = den_conv + jnp.cumsum(ek, axis=0)
            ctx = num / (den[:, :, None] + 1e-6)
            y = (jnp.tanh(qh) * ctx).reshape(T, dim)
            attn_out = project(f"blocks.{index}.attn.out_proj", attn.out_proj, y)
            x = x + attn_out
            mlp_input = block.norm2(x)
            hidden = project(f"blocks.{index}.mlp.proj1", block.mlp.proj1, mlp_input)
            activated = block.mlp.act(hidden)
            mlp_out = project(f"blocks.{index}.mlp.proj2", block.mlp.proj2, activated)
            x = x + mlp_out
        x = self.model.norm(x)
        logits = jax.vmap(self.model.clf)(x)

        arrays = tuple(array for name in selected for array in pending[name])
        device_stats = tuple(
            jnp.stack(
                (jnp.min(array), jnp.max(array), jnp.mean(array), jnp.sqrt(jnp.mean(jnp.square(array))))
            )
            for array in arrays
        )
        # One grouped synchronization for all selected summaries and, in trace
        # mode, only the selected full arrays. The byte cap was checked above.
        host_stats, host_arrays = jax.device_get((device_stats, arrays if retention == "trace" else ()))

        def capture(position: int) -> TensorCapture:
            array = arrays[position]
            stats = host_stats[position]
            if not self._np.isfinite(stats).all():
                raise ValueError("captured tensor has nonfinite summary")
            values = None
            if retention == "trace":
                values = self._np.array(host_arrays[position], copy=True)
                values.setflags(write=False)
            return TensorCapture(
                tuple(array.shape),
                ("token", "feature"),
                str(array.dtype),
                float(stats[0]),
                float(stats[1]),
                float(stats[2]),
                float(stats[3]),
                values,
            )

        captures = {
            name: OperationCapture(*(capture(index * 3 + offset) for offset in range(3)))
            for index, name in enumerate(selected)
        }
        return ForwardResult(logits, MappingProxyType(captures))
