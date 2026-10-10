"""Versioned software profiles and independent dy4p representation reference.

These rules describe local software experiments, not a physical Z1 compiler.
The reference delegates its conditional law to independent state enumeration.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from gibbsiq.qualification._validation import _finite
from gibbsiq.qualification.adapters.reference import four_parent_conditional


DY4P_WEIGHTS = (1 / 4, 1 / 8, 1 / 16, 1 / 32)
DY4P_VALUES = tuple((2 * code - 15) / 32 for code in range(16))


@dataclass(frozen=True, slots=True)
class StochasticProfile:
    profile_id: str
    boundary: str
    field: str
    weight_representation: str
    input_encoding: str
    rounding: str
    saturation: str
    parent_reuse: str
    sampling: str
    scale_decode: str
    unwrapped_operations: str


PROFILES = MappingProxyType(
    {
        "ideal-tanh-iid-v1": StochasticProfile(
            "ideal-tanh-iid-v1",
            "selected S04 sparse tanh-linear projection",
            "actual current sparse affine field including bias",
            "upstream float32 sparse parameters and indices",
            "existing float32 tensor, unchanged",
            "upstream numerical arithmetic",
            "none; finite fields and stable tanh",
            "fixed actual input within each operation call",
            "independent Bernoulli spins conditional on current field",
            "arithmetic average of exact -1/+1 spins",
            "all S04 exclusions, including final dense head",
        ),
        "dy4p-conditional-iid-v1": StochasticProfile(
            "dy4p-conditional-iid-v1",
            "one local scalar encoded by four parent spins",
            "bias plus weight times decoded four-spin word",
            "finite software weight and bias in [-32,32]; float64 reference, float32 candidate",
            "16 words (2k-15)/32, k=0..15; weights 1/4,1/8,1/16,1/32",
            "nearest ties-to-even for deterministic scalar",
            "reject outside [-15/32,15/32]; no clipping",
            "fixed word or independent joint redraw per output draw",
            "independent joint parent word then conditional output spin",
            "arithmetic average of exact output spins; no physical scale",
            "no whole-model support",
        ),
    }
)


def get_profile(profile_id: str) -> StochasticProfile:
    if type(profile_id) is not str or profile_id not in PROFILES:
        raise ValueError("unsupported stochastic profile ID")
    return PROFILES[profile_id]


@dataclass(frozen=True, slots=True)
class Dy4pEncoding:
    code: int
    spins: tuple[int, int, int, int]
    decoded: float
    error: float


@dataclass(frozen=True, slots=True)
class Dy4pReference:
    parent_mean: float
    numerical_mean: float
    representation_mean: float
    variance: float
    encoding: Dy4pEncoding | None


def _coefficient(value: Any, name: str) -> float:
    result = _finite(value, name=name)
    if not -32.0 <= result <= 32.0:
        raise ValueError(f"{name} must be in [-32,32]")
    return result


def encode_dy4p(value: float) -> Dy4pEncoding:
    """Round an in-range scalar to the 16-word four-spin dyadic codebook."""
    input_value = _finite(value, name="value")
    if not -15 / 32 <= input_value <= 15 / 32:
        raise ValueError("value must be in [-15/32,15/32]")
    code = round((32 * input_value + 15) / 2)
    spins = (
        1 if code & 8 else -1,
        1 if code & 4 else -1,
        1 if code & 2 else -1,
        1 if code & 1 else -1,
    )
    decoded = DY4P_VALUES[code]
    return Dy4pEncoding(code, spins, decoded, decoded - input_value)


def dy4p_reference(
    *,
    weight: float = 1.0,
    bias: float = 0.0,
    value: float | None = None,
    parent_probabilities: Any = None,
) -> Dy4pReference:
    """Enumerate the encoded parent and conditional output law independently."""
    canonical_weight = _coefficient(weight, "weight")
    canonical_bias = _coefficient(bias, "bias")
    if (value is None) == (parent_probabilities is None):
        raise ValueError("provide exactly one of value and parent_probabilities")
    encoding = encode_dy4p(value) if value is not None else None
    if encoding is not None:
        masses = tuple(1.0 if code == encoding.code else 0.0 for code in range(16))
    else:
        masses = parent_probabilities
    oracle = four_parent_conditional(
        tuple(canonical_weight * coefficient for coefficient in DY4P_WEIGHTS),
        bias=canonical_bias,
        parent_probabilities=masses,
    )
    parent_masses = tuple(
        oracle.joint_probabilities[2 * code] + oracle.joint_probabilities[2 * code + 1] for code in range(16)
    )
    parent_mean = math.fsum(mass * decoded for mass, decoded in zip(parent_masses, DY4P_VALUES))
    numerical_input = float(value) if value is not None else parent_mean
    numerical_mean = math.tanh(canonical_weight * numerical_input + canonical_bias)
    return Dy4pReference(parent_mean, numerical_mean, oracle.mean, oracle.variance, encoding)
