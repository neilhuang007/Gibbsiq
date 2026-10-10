"""Target-parameterized hardware descriptions for ThermoMap analysis.

The public Extropic hardware parameters required for a complete mapper are not
available.  These immutable records therefore carry explicit values and their
provenance; they do not provide speculative Z1 defaults.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal, TypeAlias

from gibbsiq._frozen import freeze, thaw
from gibbsiq.topology import ExplicitTopology, GridTopology, TopologySpec

EvidenceClassification: TypeAlias = Literal["measured", "modeled", "assumed", "inferred"]
RoundingPolicy: TypeAlias = Literal["nearest_even", "toward_zero"]
OverflowPolicy: TypeAlias = Literal["reject", "saturate"]
PhysicalUnit: TypeAlias = Literal[
    "bit/second",
    "hertz",
    "joule",
    "joule/bit",
    "second",
]

EVIDENCE_CLASSIFICATIONS = ("measured", "modeled", "assumed", "inferred")
ROUNDING_POLICIES = ("nearest_even", "toward_zero")
OVERFLOW_POLICIES = ("reject", "saturate")
PHYSICAL_UNITS = ("bit/second", "hertz", "joule", "joule/bit", "second")

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
    accessed_on: str | None = None
    evidence_artifact: str | None = None
    sensitivity_range: tuple[float, float] | None = None
    sensitivity_unit: str | None = None
    sensitivity_note: str = ""

    def __post_init__(self) -> None:
        if self.classification not in EVIDENCE_CLASSIFICATIONS:
            raise ValueError(
                f"classification must be one of {EVIDENCE_CLASSIFICATIONS}, got {self.classification!r}"
            )
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("source must be a non-empty string")
        if not isinstance(self.note, str):
            raise ValueError(f"note must be a string, got {self.note!r}")
        accessed_on = self.accessed_on
        if accessed_on is not None:
            if not isinstance(accessed_on, str):
                raise ValueError(f"accessed_on must be an ISO date string or None, got {accessed_on!r}")
            try:
                parsed_date = date.fromisoformat(accessed_on)
            except ValueError as error:
                raise ValueError(f"accessed_on must be a valid ISO date, got {accessed_on!r}") from error
            accessed_on = parsed_date.isoformat()
        evidence_artifact = self.evidence_artifact
        if evidence_artifact is not None:
            if not isinstance(evidence_artifact, str) or not evidence_artifact.strip():
                raise ValueError("evidence_artifact must be a non-empty string or None")
            evidence_artifact = evidence_artifact.strip()

        sensitivity_range = self.sensitivity_range
        if sensitivity_range is not None:
            if not isinstance(sensitivity_range, (tuple, list)) or len(sensitivity_range) != 2:
                raise ValueError("sensitivity_range must be a finite (lower, upper) pair or None")
            lower = _finite_float(sensitivity_range[0], name="sensitivity_range[0]")
            upper = _finite_float(sensitivity_range[1], name="sensitivity_range[1]")
            if lower > upper:
                raise ValueError("sensitivity_range lower bound cannot exceed its upper bound")
            sensitivity_range = (lower, upper)
            if not isinstance(self.sensitivity_unit, str) or not self.sensitivity_unit.strip():
                raise ValueError("sensitivity_unit is required with sensitivity_range")
        elif self.sensitivity_unit is not None:
            raise ValueError("sensitivity_unit requires sensitivity_range")
        if not isinstance(self.sensitivity_note, str):
            raise ValueError(f"sensitivity_note must be a string, got {self.sensitivity_note!r}")

        object.__setattr__(self, "source", self.source.strip())
        object.__setattr__(self, "accessed_on", accessed_on)
        object.__setattr__(self, "evidence_artifact", evidence_artifact)
        object.__setattr__(self, "sensitivity_range", sensitivity_range)
        if self.sensitivity_unit is not None:
            object.__setattr__(self, "sensitivity_unit", self.sensitivity_unit.strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "source": self.source,
            "note": self.note,
            "accessed_on": self.accessed_on,
            "evidence_artifact": self.evidence_artifact,
            "sensitivity_range": (None if self.sensitivity_range is None else list(self.sensitivity_range)),
            "sensitivity_unit": self.sensitivity_unit,
            "sensitivity_note": self.sensitivity_note,
        }


def _finite_float(value: Any, *, name: str) -> float:
    try:
        canonical = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a finite number, got {value!r}") from error
    if isinstance(value, bool) or not math.isfinite(canonical):
        raise ValueError(f"{name} must be a finite number, got {value!r}")
    return 0.0 if canonical == 0.0 else canonical


@dataclass(frozen=True, slots=True)
class PhysicalQuantity:
    """One finite SI fact with provenance and a caller-declared sensitivity range."""

    value: float
    unit: PhysicalUnit
    sensitivity_lower: float
    sensitivity_upper: float
    provenance: ParameterProvenance

    def __post_init__(self) -> None:
        value = _finite_float(self.value, name="value")
        lower = _finite_float(self.sensitivity_lower, name="sensitivity_lower")
        upper = _finite_float(self.sensitivity_upper, name="sensitivity_upper")
        if self.unit not in PHYSICAL_UNITS:
            raise ValueError(f"unit must be one of {PHYSICAL_UNITS}, got {self.unit!r}")
        if lower > upper:
            raise ValueError("sensitivity_lower cannot exceed sensitivity_upper")
        if value < lower or value > upper:
            raise ValueError(f"value={value!r} must lie within sensitivity range [{lower!r}, {upper!r}]")
        if not isinstance(self.provenance, ParameterProvenance):
            raise ValueError("provenance must be ParameterProvenance")
        if self.provenance.classification != "assumed" and self.provenance.accessed_on is None:
            raise ValueError("accessed_on is required for measured, modeled, and inferred physical facts")
        if self.provenance.classification == "measured" and self.provenance.evidence_artifact is None:
            raise ValueError("measured physical facts require an evidence_artifact")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "sensitivity_lower", lower)
        object.__setattr__(self, "sensitivity_upper", upper)

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "sensitivity_range": [self.sensitivity_lower, self.sensitivity_upper],
            "provenance": self.provenance.to_dict(),
        }


def _quantity(
    value: Any,
    *,
    name: str,
    unit: PhysicalUnit,
    positive: bool,
) -> PhysicalQuantity | None:
    if value is None:
        return None
    if not isinstance(value, PhysicalQuantity):
        raise ValueError(f"{name} must be PhysicalQuantity or None, got {value!r}")
    if value.unit != unit:
        raise ValueError(f"{name} must use canonical unit {unit!r}, got {value.unit!r}")
    if positive:
        if value.value <= 0.0 or value.sensitivity_lower <= 0.0:
            raise ValueError(f"{name} and its sensitivity range must be positive")
    elif value.value < 0.0 or value.sensitivity_lower < 0.0:
        raise ValueError(f"{name} and its sensitivity range must be non-negative")
    return value


@dataclass(frozen=True, slots=True)
class CommunicationSpec:
    """Optional per-link communication facts; missing facts remain ``None``."""

    clock_frequency: PhysicalQuantity | None = None
    link_bandwidth: PhysicalQuantity | None = None
    link_latency: PhysicalQuantity | None = None
    link_energy_per_bit: PhysicalQuantity | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "clock_frequency",
            _quantity(
                self.clock_frequency,
                name="clock_frequency",
                unit="hertz",
                positive=True,
            ),
        )
        object.__setattr__(
            self,
            "link_bandwidth",
            _quantity(
                self.link_bandwidth,
                name="link_bandwidth",
                unit="bit/second",
                positive=True,
            ),
        )
        object.__setattr__(
            self,
            "link_latency",
            _quantity(
                self.link_latency,
                name="link_latency",
                unit="second",
                positive=False,
            ),
        )
        object.__setattr__(
            self,
            "link_energy_per_bit",
            _quantity(
                self.link_energy_per_bit,
                name="link_energy_per_bit",
                unit="joule/bit",
                positive=False,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "clock_frequency": (None if self.clock_frequency is None else self.clock_frequency.to_dict()),
            "link_bandwidth": (None if self.link_bandwidth is None else self.link_bandwidth.to_dict()),
            "link_latency": None if self.link_latency is None else self.link_latency.to_dict(),
            "link_energy_per_bit": (
                None if self.link_energy_per_bit is None else self.link_energy_per_bit.to_dict()
            ),
        }


@dataclass(frozen=True, slots=True)
class HostTransferSpec:
    """Optional host/target transfer facts in canonical SI units."""

    bandwidth: PhysicalQuantity | None = None
    latency: PhysicalQuantity | None = None
    energy_per_bit: PhysicalQuantity | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "bandwidth",
            _quantity(
                self.bandwidth,
                name="bandwidth",
                unit="bit/second",
                positive=True,
            ),
        )
        object.__setattr__(
            self,
            "latency",
            _quantity(self.latency, name="latency", unit="second", positive=False),
        )
        object.__setattr__(
            self,
            "energy_per_bit",
            _quantity(
                self.energy_per_bit,
                name="energy_per_bit",
                unit="joule/bit",
                positive=False,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "bandwidth": None if self.bandwidth is None else self.bandwidth.to_dict(),
            "latency": None if self.latency is None else self.latency.to_dict(),
            "energy_per_bit": (None if self.energy_per_bit is None else self.energy_per_bit.to_dict()),
        }


@dataclass(frozen=True, slots=True)
class ProgrammingSpec:
    """Optional first-program and reprogram time/energy facts."""

    programming_time: PhysicalQuantity | None = None
    programming_energy: PhysicalQuantity | None = None
    reprogramming_time: PhysicalQuantity | None = None
    reprogramming_energy: PhysicalQuantity | None = None

    def __post_init__(self) -> None:
        for field_name, unit in (
            ("programming_time", "second"),
            ("programming_energy", "joule"),
            ("reprogramming_time", "second"),
            ("reprogramming_energy", "joule"),
        ):
            object.__setattr__(
                self,
                field_name,
                _quantity(
                    getattr(self, field_name),
                    name=field_name,
                    unit=unit,  # type: ignore[arg-type]
                    positive=False,
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            field_name: (None if getattr(self, field_name) is None else getattr(self, field_name).to_dict())
            for field_name in (
                "programming_time",
                "programming_energy",
                "reprogramming_time",
                "reprogramming_energy",
            )
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
        "accumulator_format",
        "pbit_capacity",
        "max_degree",
        "max_color_phases",
        "coefficient_format",
        "cell_energy_joules",
        "cell_update_seconds",
        "topology",
    }
)

_NUMERIC_PARAMETER_UNITS = {
    "pbit_capacity": "count",
    "max_degree": "count",
    "max_color_phases": "count",
    "cell_energy_joules": "joule",
    "cell_update_seconds": "second",
}


@dataclass(frozen=True, slots=True)
class TSUSpec:
    """Explicit assumptions for one abstract or physical TSU target.

    Every supplied target value requires a provenance row.  Unknown values stay
    ``None`` and must produce an unevaluated hardware check rather than a guessed
    limit or performance estimate.
    """

    name: str
    topology: TopologySpec | None = None
    pbit_capacity: int | None = None
    max_degree: int | None = None
    max_color_phases: int | None = None
    coefficient_format: FixedPointSpec | None = None
    accumulator_format: FixedPointSpec | None = None
    cell_energy_joules: float | None = None
    cell_update_seconds: float | None = None
    communication: CommunicationSpec | None = None
    host_transfer: HostTransferSpec | None = None
    programming: ProgrammingSpec | None = None
    provenance: Mapping[str, ParameterProvenance] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        object.__setattr__(self, "name", self.name.strip())

        if self.topology is not None and not isinstance(
            self.topology,
            (GridTopology, ExplicitTopology),
        ):
            raise ValueError(
                f"topology must be GridTopology, ExplicitTopology, or None, got {self.topology!r}"
            )

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
        if self.accumulator_format is not None and not isinstance(
            self.accumulator_format,
            FixedPointSpec,
        ):
            raise ValueError(
                f"accumulator_format must be FixedPointSpec or None, got {self.accumulator_format!r}"
            )
        for parameter, expected_type in (
            ("communication", CommunicationSpec),
            ("host_transfer", HostTransferSpec),
            ("programming", ProgrammingSpec),
        ):
            value = getattr(self, parameter)
            if value is not None and not isinstance(value, expected_type):
                raise ValueError(f"{parameter} must be {expected_type.__name__} or None, got {value!r}")

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

        for parameter in supplied:
            evidence = provenance[parameter]
            if evidence.classification == "measured" and evidence.evidence_artifact is None:
                raise ValueError(f"measured target parameter {parameter!r} requires an evidence_artifact")

        complete_contract = any(
            value is not None
            for value in (
                self.topology,
                self.accumulator_format,
                self.communication,
                self.host_transfer,
                self.programming,
            )
        )
        if complete_contract:
            for parameter in supplied:
                evidence = provenance[parameter]
                if evidence.classification != "assumed" and evidence.accessed_on is None:
                    raise ValueError(f"external {parameter!r} provenance requires accessed_on")
                if parameter not in _NUMERIC_PARAMETER_UNITS:
                    if evidence.sensitivity_range is None and not evidence.sensitivity_note.strip():
                        raise ValueError(
                            f"complete-contract {parameter!r} provenance requires "
                            "sensitivity_range or sensitivity_note"
                        )
            for parameter, expected_unit in _NUMERIC_PARAMETER_UNITS.items():
                value = getattr(self, parameter)
                if value is None:
                    continue
                evidence = provenance[parameter]
                if evidence.sensitivity_range is None:
                    raise ValueError(f"external {parameter!r} provenance requires sensitivity_range")
                if evidence.sensitivity_unit != expected_unit:
                    raise ValueError(
                        f"external {parameter!r} provenance sensitivity_unit must be "
                        f"{expected_unit!r}, got {evidence.sensitivity_unit!r}"
                    )
                lower, upper = evidence.sensitivity_range
                if float(value) < lower or float(value) > upper:
                    raise ValueError(f"{parameter}={value!r} lies outside its provenance sensitivity_range")

        if self.topology is not None and self.pbit_capacity is not None:
            if self.topology.capacity != self.pbit_capacity:
                raise ValueError(
                    f"topology capacity {self.topology.capacity} conflicts with "
                    f"pbit_capacity={self.pbit_capacity}"
                )
        object.__setattr__(
            self,
            "provenance",
            freeze({parameter: provenance[parameter] for parameter in sorted(provenance)}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "tsu-target-v2",
            "name": self.name,
            "topology": None if self.topology is None else self.topology.to_dict(),
            "pbit_capacity": self.pbit_capacity,
            "max_degree": self.max_degree,
            "max_color_phases": self.max_color_phases,
            "coefficient_format": (
                None if self.coefficient_format is None else self.coefficient_format.to_dict()
            ),
            "accumulator_format": (
                None if self.accumulator_format is None else self.accumulator_format.to_dict()
            ),
            "cell_energy_joules": self.cell_energy_joules,
            "cell_update_seconds": self.cell_update_seconds,
            "communication": (None if self.communication is None else self.communication.to_dict()),
            "host_transfer": (None if self.host_transfer is None else self.host_transfer.to_dict()),
            "programming": None if self.programming is None else self.programming.to_dict(),
            "provenance": {
                parameter: self.provenance[parameter].to_dict() for parameter in sorted(self.provenance)
            },
        }

    def provenance_dict(self) -> dict[str, Any]:
        """Return a detached mutable copy of the recorded provenance."""
        return thaw(
            {parameter: self.provenance[parameter].to_dict() for parameter in sorted(self.provenance)}
        )
