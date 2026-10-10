"""Bounded software-only stochastic profiles for the pinned Z1T experiment."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from gibbsiq.qualification._validation import _integer
from gibbsiq.qualification.adapters._jax import run_key
from gibbsiq.qualification.adapters.z1t import NumericalZ1T, _operation_groups
from gibbsiq.qualification.contracts import canonical_json
from gibbsiq.qualification.engine import RandomizationIdentity
from gibbsiq.qualification.profiles import DY4P_VALUES, _coefficient, encode_dy4p


_MAX_SAMPLES = 4096
_MAX_FIELD_ELEMENTS = 65536
_MAX_SPIN_WORK = 8388608
_CHUNK = 64


@dataclass(frozen=True, slots=True)
class IIDSampleResult:
    mean: Any
    conditional_mean: Any
    mean_variance: Any
    samples: int
    spin_draws: int
    draws: Any | None


@dataclass(frozen=True, slots=True)
class Dy4pSampleResult:
    mean: float
    samples: int
    parent_codes: Any | None
    draws: Any | None


def _count(value: Any, name: str, maximum: int) -> int:
    return _integer(value, name=name, minimum=1, maximum=maximum)


def _trace_control(retain_draws: Any, max_trace_bytes: Any) -> None:
    if type(retain_draws) is not bool:
        raise ValueError("retain_draws must be an exact boolean")
    _integer(max_trace_bytes, name="max_trace_bytes", minimum=0)


def _purpose_key(randomization: RandomizationIdentity, profile: str, operation_id: str, purpose: str) -> Any:
    import jax

    key = run_key(randomization)
    digest = hashlib.sha256(
        canonical_json(
            {
                "profile": profile,
                "operation_id": operation_id,
                "purpose": purpose,
            }
        )
    ).digest()
    for position in range(0, 32, 4):
        key = jax.random.fold_in(key, int.from_bytes(digest[position : position + 4], "big"))
    return key


def sample_iid_tanh(
    field: Any,
    *,
    randomization: RandomizationIdentity,
    operation_id: str,
    samples: int,
    chunk_size: int = 64,
    retain_draws: bool = False,
    max_trace_bytes: int = 1048576,
) -> IIDSampleResult:
    """Draw independent conditional spins at each coordinate and draw index."""
    import jax
    import jax.numpy as jnp
    import numpy as np

    count = _count(samples, "samples", _MAX_SAMPLES)
    chunk = _count(chunk_size, "chunk_size", _CHUNK)
    _trace_control(retain_draws, max_trace_bytes)
    if type(operation_id) is not str or not operation_id.strip():
        raise ValueError("operation_id must be a nonblank string")
    if not isinstance(randomization, RandomizationIdentity):
        raise ValueError("randomization must be RandomizationIdentity")
    if type(field) is float:
        elements = 1
    elif isinstance(field, (jax.Array, np.ndarray, np.generic)):
        if np.dtype(field.dtype) != np.dtype("float32"):
            raise ValueError("field must have float32 dtype")
        elements = int(field.size)
    else:
        raise ValueError("field must be a float32 scalar or tensor")
    if elements > _MAX_FIELD_ELEMENTS:
        raise ValueError("field must have at most 65536 elements")
    work = elements * count
    if work > _MAX_SPIN_WORK:
        raise ValueError("requested spin work exceeds 8388608 draws")
    if retain_draws and work > max_trace_bytes:
        raise ValueError("requested spin trace exceeds max_trace_bytes")
    try:
        field_array = jnp.asarray(field, dtype=jnp.float32)
    except (TypeError, ValueError) as error:
        raise ValueError("field must be a float32 scalar or tensor") from error
    if not bool(jax.device_get(jnp.all(jnp.isfinite(field_array)))):
        raise ValueError("field must be finite")

    key = _purpose_key(randomization, "ideal-tanh-iid-v1", operation_id, "projection-spins")
    conditional_mean = jnp.tanh(field_array)
    probability_up = (1.0 + conditional_mean) / 2.0
    total = jnp.zeros_like(field_array, dtype=jnp.int32)
    host_draws = np.empty((count, *field_array.shape), dtype=np.int8) if retain_draws else None

    def draw_one(index: Any) -> Any:
        draw_key = jax.random.fold_in(key, index)
        up = jax.random.bernoulli(draw_key, probability_up, shape=field_array.shape)
        return jnp.where(up, jnp.int8(1), jnp.int8(-1))

    draw_many = jax.vmap(draw_one)
    for start in range(0, count, chunk):
        stop = min(start + chunk, count)
        draws = draw_many(jnp.arange(start, stop, dtype=jnp.uint32))
        total = total + jnp.sum(draws, axis=0, dtype=jnp.int32)
        if host_draws is not None:
            host_draws[start:stop] = jax.device_get(draws)
    if host_draws is not None:
        host_draws.setflags(write=False)
    return IIDSampleResult(
        total.astype(field_array.dtype) / count,
        conditional_mean,
        (1.0 - conditional_mean * conditional_mean) / count,
        count,
        work,
        host_draws,
    )


def _dy4p_masses(values: Any) -> tuple[float, ...]:
    from gibbsiq.qualification._validation import _finite

    if isinstance(values, (str, bytes, bytearray, Mapping, set, frozenset)):
        raise ValueError("parent_probabilities must contain 16 masses")
    try:
        raw = tuple(values)
    except TypeError as error:
        raise ValueError("parent_probabilities must contain 16 masses") from error
    if len(raw) != 16:
        raise ValueError("parent_probabilities must contain 16 masses")
    masses = tuple(_finite(value, name=f"parent_probabilities[{i}]") for i, value in enumerate(raw))
    if any(value < 0 for value in masses):
        raise ValueError("parent probabilities must be nonnegative")
    try:
        normalizer = math.fsum(masses)
    except OverflowError as error:
        raise ValueError("parent probability sum must remain finite") from error
    if abs(normalizer - 1.0) > 1e-12:
        raise ValueError("parent probabilities must sum to one within 1e-12")
    return tuple(value / normalizer for value in masses)


def sample_dy4p(
    *,
    weight: float = 1.0,
    bias: float = 0.0,
    value: float | None = None,
    parent_probabilities: Sequence[float] | None = None,
    randomization: RandomizationIdentity,
    samples: int = 32,
    retain_draws: bool = False,
    max_trace_bytes: int = 1048576,
) -> Dy4pSampleResult:
    """Draw the joint parent word, then its conditional output spin, locally."""
    import jax
    import jax.numpy as jnp
    import numpy as np

    canonical_weight = _coefficient(weight, "weight")
    canonical_bias = _coefficient(bias, "bias")
    count = _count(samples, "samples", _MAX_SAMPLES)
    _trace_control(retain_draws, max_trace_bytes)
    if not isinstance(randomization, RandomizationIdentity):
        raise ValueError("randomization must be RandomizationIdentity")
    if (value is None) == (parent_probabilities is None):
        raise ValueError("provide exactly one of value and parent_probabilities")
    fixed = encode_dy4p(value) if value is not None else None
    masses = None if fixed is not None else _dy4p_masses(parent_probabilities)
    # One code byte and one spin byte per requested retained draw.
    if retain_draws and 2 * count > max_trace_bytes:
        raise ValueError("requested dy4p trace exceeds max_trace_bytes")
    parent_key = _purpose_key(randomization, "dy4p-conditional-iid-v1", "dy4p-local", "parent-word")
    spin_key = _purpose_key(randomization, "dy4p-conditional-iid-v1", "dy4p-local", "output-spin")
    logits = None if masses is None else jnp.log(jnp.asarray(masses, dtype=jnp.float32))
    codebook = jnp.asarray(DY4P_VALUES, dtype=jnp.float32)
    weight32 = jnp.float32(canonical_weight)
    bias32 = jnp.float32(canonical_bias)
    total = jnp.int32(0)
    host_codes = np.empty(count, dtype=np.uint8) if retain_draws else None
    host_draws = np.empty(count, dtype=np.int8) if retain_draws else None

    def draw_one(index: Any) -> tuple[Any, Any]:
        if fixed is None:
            parent = jax.random.categorical(jax.random.fold_in(parent_key, index), logits)
        else:
            parent = jnp.int32(fixed.code)
        field = bias32 + weight32 * codebook[parent]
        up = jax.random.bernoulli(jax.random.fold_in(spin_key, index), (1.0 + jnp.tanh(field)) / 2.0)
        return parent.astype(jnp.uint8), jnp.where(up, jnp.int8(1), jnp.int8(-1))

    draw_many = jax.vmap(draw_one)
    for start in range(0, count, _CHUNK):
        stop = min(start + _CHUNK, count)
        codes, draws = draw_many(jnp.arange(start, stop, dtype=jnp.uint32))
        total = total + jnp.sum(draws, dtype=jnp.int32)
        if host_codes is not None and host_draws is not None:
            host_codes[start:stop], host_draws[start:stop] = jax.device_get((codes, draws))
    if host_codes is not None and host_draws is not None:
        host_codes.setflags(write=False)
        host_draws.setflags(write=False)
    return Dy4pSampleResult(float(jax.device_get(total)) / count, count, host_codes, host_draws)


class IdealTanhModel:
    """Compose S04 numerical execution with selected IID projection outputs."""

    profile_id = "ideal-tanh-iid-v1"

    def __init__(
        self,
        numerical: NumericalZ1T,
        *,
        samples: int = 32,
        operation_samples: Mapping[str, int] | None = None,
    ) -> None:
        if not isinstance(numerical, NumericalZ1T):
            raise ValueError("numerical must be NumericalZ1T")
        default_count = _count(samples, "samples", _MAX_SAMPLES)
        operations = numerical.operations
        names = tuple(operation.operation_id for operation in operations)
        if operation_samples is None:
            overrides: Mapping[str, int] = {}
        elif isinstance(operation_samples, Mapping):
            overrides = operation_samples
        else:
            raise ValueError("operation_samples must be a mapping")
        if any(type(name) is not str or name not in names for name in overrides):
            raise ValueError("operation_samples contains an unknown operation ID")
        counts = {
            name: _count(overrides[name], name, _MAX_SAMPLES) if name in overrides else default_count
            for name in names
        }
        self.numerical = numerical
        self.operation_samples = MappingProxyType(counts)
        self.operation_groups = MappingProxyType(_operation_groups(operations))

    def forward(
        self,
        tokens: Sequence[int] | Any,
        randomization: RandomizationIdentity,
        *,
        sampled_operations: Sequence[str] | None = None,
        observe: Sequence[str] = (),
        retention: str = "summaries",
        max_trace_bytes: int = 1048576,
    ) -> Any:
        if not isinstance(randomization, RandomizationIdentity):
            raise ValueError("randomization must be RandomizationIdentity")
        if sampled_operations is None:
            selected = tuple(self.operation_samples)
        else:
            try:
                selected = tuple(sampled_operations)
            except TypeError as error:
                raise ValueError("sampled_operations must contain operation IDs") from error
            if any(type(name) is not str or name not in self.operation_samples for name in selected) or len(
                selected
            ) != len(set(selected)):
                raise ValueError("sampled_operations contains an unknown or duplicate operation ID")
        token_array = self.numerical._tokens(tokens)
        widths = {
            operation.operation_id: operation.output_features for operation in self.numerical.operations
        }
        work = sum(int(token_array.size) * widths[name] * self.operation_samples[name] for name in selected)
        if work > _MAX_SPIN_WORK:
            raise ValueError("whole-model spin work exceeds 8388608 draws")
        selected_set = set(selected)

        def transform(name: str, _inputs: Any, field: Any, numerical_output: Any) -> Any:
            if name not in selected_set:
                return numerical_output
            return sample_iid_tanh(
                field, randomization=randomization, operation_id=name, samples=self.operation_samples[name]
            ).mean

        return self.numerical.forward(
            token_array,
            observe=observe,
            retention=retention,
            max_trace_bytes=max_trace_bytes,
            transform=transform if selected else None,
        )
