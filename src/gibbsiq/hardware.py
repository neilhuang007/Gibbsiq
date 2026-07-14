"""Target-parameterized hardware descriptions for ThermoMap analysis.

The public Extropic hardware parameters required for a complete mapper are not
available.  These immutable records therefore carry explicit values and their
provenance; they do not provide speculative Z1 defaults.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias

from gibbsiq._frozen import freeze, thaw

EvidenceClassification: TypeAlias = Literal["measured", "modeled", "assumed", "inferred"]
RoundingPolicy: TypeAlias = Literal["nearest_even", "toward_zero"]
OverflowPolicy: TypeAlias = Literal["reject", "saturate"]

EVIDENCE_CLASSIFICATIONS = ("measured", "modeled", "assumed", "inferred")
ROUNDING_POLICIES = ("nearest_even", "toward_zero")
OVERFLOW_POLICIES = ("reject", "saturate")

# IsingModel stores IEEE-754 binary64 coefficients.  Limiting a fixed-point
# code word to 53 bits keeps every integer code exactly representable in that
# host format and makes rounding deterministic.
MAX_EXACT_FLOAT_CODE_BITS = 53


def _plain_int(value: Any, *, name: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}, got {value!r}")
    return value


def _optional_positive_float(value: Any, *, name: str) -> float | None:
    if value is None:
        return None
    try:
        canonical = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a finite positive number, got {value!r}") from error
    if isinstance(value, bool) or not math.isfinite(canonical) or canonical <= 0.0:
        raise ValueError(f"{name} must be a finite positive number, got {value!r}")
    return canonical


@dataclass(frozen=True, slots=True)
class ParameterProvenance:
    """Evidence classification and source for one target parameter."""

    classification: EvidenceClassification
    source: str
    note: str = ""

    def __post_init__(self) -> None:
        if self.classification not in EVIDENCE_CLASSIFICATIONS:
            raise ValueError(
                f"classification must be one of {EVIDENCE_CLASSIFICATIONS}, got {self.classification!r}"
            )
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("source must be a non-empty string")
        if not isinstance(self.note, str):
            raise ValueError(f"note must be a string, got {self.note!r}")
        object.__setattr__(self, "source", self.source.strip())

    def to_dict(self) -> dict[str, str]:
        return {
            "classification": self.classification,
            "source": self.source,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class FixedPointSpec:
    """Binary fixed-point coefficient format with explicit numeric behavior.

    ``integer_bits`` excludes the sign bit.  A signed ``s{I}{F}`` format
    represents multiples of ``2**-F`` over ``[-2**I, 2**I - 2**-F]``.
    """

    integer_bits: int
    fractional_bits: int
    signed: bool = True
    rounding: RoundingPolicy = "nearest_even"
    overflow: OverflowPolicy = "reject"

    def __post_init__(self) -> None:
        _plain_int(self.integer_bits, name="integer_bits", minimum=0)
        _plain_int(self.fractional_bits, name="fractional_bits", minimum=0)
        if not isinstance(self.signed, bool):
            raise ValueError(f"signed must be boolean, got {self.signed!r}")
        if self.rounding not in ROUNDING_POLICIES:
            raise ValueError(f"rounding must be one of {ROUNDING_POLICIES}, got {self.rounding!r}")
        if self.overflow not in OVERFLOW_POLICIES:
            raise ValueError(f"overflow must be one of {OVERFLOW_POLICIES}, got {self.overflow!r}")
        if self.total_bits < 1:
            raise ValueError("fixed-point format must contain at least one code bit")
        if self.total_bits > MAX_EXACT_FLOAT_CODE_BITS:
            raise ValueError(
                "fixed-point total_bits exceeds the 53-bit exact-integer domain of "
                f"binary64 coefficients: {self.total_bits}"
            )

    @property
    def total_bits(self) -> int:
        return self.integer_bits + self.fractional_bits + int(self.signed)

    @property
    def step(self) -> float:
        return math.ldexp(1.0, -self.fractional_bits)

    @property
    def minimum(self) -> float:
        return -math.ldexp(1.0, self.integer_bits) if self.signed else 0.0

    @property
    def maximum(self) -> float:
        return math.ldexp(1.0, self.integer_bits) - self.step

    @property
    def minimum_code(self) -> int:
        return -(1 << (self.total_bits - 1)) if self.signed else 0

    @property
    def maximum_code(self) -> int:
        return (1 << (self.total_bits - int(self.signed))) - 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "integer_bits": self.integer_bits,
            "fractional_bits": self.fractional_bits,
            "signed": self.signed,
            "rounding": self.rounding,
            "overflow": self.overflow,
            "total_bits": self.total_bits,
            "step": self.step,
            "minimum": self.minimum,
            "maximum": self.maximum,
        }


_TARGET_PARAMETER_NAMES = frozenset(
    {
        "pbit_capacity",
        "max_degree",
        "max_color_phases",
        "coefficient_format",
        "cell_energy_joules",
        "cell_update_seconds",
    }
)


@dataclass(frozen=True, slots=True)
class TSUSpec:
    """Explicit assumptions for one abstract or physical TSU target.

    Every supplied target value requires a provenance row.  Unknown values stay
    ``None`` and must produce an unevaluated hardware check rather than a guessed
    limit or performance estimate.
    """

    name: str
    pbit_capacity: int | None = None
    max_degree: int | None = None
    max_color_phases: int | None = None
    coefficient_format: FixedPointSpec | None = None
    cell_energy_joules: float | None = None
    cell_update_seconds: float | None = None
    provenance: Mapping[str, ParameterProvenance] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        object.__setattr__(self, "name", self.name.strip())

        for field_name, minimum in (
            ("pbit_capacity", 1),
            ("max_degree", 0),
            ("max_color_phases", 1),
        ):
            value = getattr(self, field_name)
            if value is not None:
                _plain_int(value, name=field_name, minimum=minimum)
        if self.coefficient_format is not None and not isinstance(self.coefficient_format, FixedPointSpec):
            raise ValueError(
                f"coefficient_format must be FixedPointSpec or None, got {self.coefficient_format!r}"
            )

        object.__setattr__(
            self,
            "cell_energy_joules",
            _optional_positive_float(self.cell_energy_joules, name="cell_energy_joules"),
        )
        object.__setattr__(
            self,
            "cell_update_seconds",
            _optional_positive_float(self.cell_update_seconds, name="cell_update_seconds"),
        )

        if not isinstance(self.provenance, Mapping):
            raise ValueError("provenance must be a mapping")
        provenance = dict(self.provenance)
        for parameter, evidence in provenance.items():
            if not isinstance(parameter, str) or not isinstance(evidence, ParameterProvenance):
                raise ValueError("provenance must map parameter-name strings to ParameterProvenance values")
        unknown = sorted(set(provenance) - _TARGET_PARAMETER_NAMES)
        if unknown:
            raise ValueError(f"provenance contains unknown target parameter names {unknown!r}")

        supplied = {
            parameter for parameter in _TARGET_PARAMETER_NAMES if getattr(self, parameter) is not None
        }
        missing = sorted(supplied - set(provenance))
        if missing:
            raise ValueError(f"supplied target parameters require provenance entries {missing!r}")
        dangling = sorted(set(provenance) - supplied)
        if dangling:
            raise ValueError(f"provenance supplied for unset target parameters {dangling!r}")
        object.__setattr__(self, "provenance", freeze(provenance))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "pbit_capacity": self.pbit_capacity,
            "max_degree": self.max_degree,
            "max_color_phases": self.max_color_phases,
            "coefficient_format": (
                None if self.coefficient_format is None else self.coefficient_format.to_dict()
            ),
            "cell_energy_joules": self.cell_energy_joules,
            "cell_update_seconds": self.cell_update_seconds,
            "provenance": {parameter: evidence.to_dict() for parameter, evidence in self.provenance.items()},
        }

    def provenance_dict(self) -> dict[str, Any]:
        """Return a detached mutable copy of the recorded provenance."""
        return thaw({parameter: evidence.to_dict() for parameter, evidence in self.provenance.items()})
