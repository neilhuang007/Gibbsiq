"""Fixed-point sensitivity analysis for beta-scaled Ising coefficients.

This module models coefficient quantization only.  It does not model a DAC
applied after local-field accumulation, nonlinear response curves, delayed
boundary states, drift, or other non-Hamiltonian hardware effects.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

from gibbsiq.exact_distribution import (
    DistributionComparison,
    ExactDistributionNumericalError,
    compare_boltzmann_distributions,
)
from gibbsiq.hardware import FixedPointSpec
from gibbsiq.model import IsingModel, Variable, finite_float, finite_sum

CoefficientKind: TypeAlias = Literal["linear", "quadratic"]
ExactComparisonStatus: TypeAlias = Literal[
    "computed",
    "not_computed_numerical_range",
    "not_computed_too_many_variables",
]


@dataclass(frozen=True, slots=True)
class QuantizedCoefficient:
    """One beta-scaled coefficient and its fixed-point image."""

    kind: CoefficientKind
    left: Variable
    right: Variable | None
    target_effective: float
    quantized_effective: float
    error: float
    saturated: bool

    @property
    def zeroed_nonzero(self) -> bool:
        return self.target_effective != 0.0 and self.quantized_effective == 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "left": self.left,
            "right": self.right,
            "target_effective": self.target_effective,
            "quantized_effective": self.quantized_effective,
            "error": self.error,
            "absolute_error": abs(self.error),
            "saturated": self.saturated,
            "zeroed_nonzero": self.zeroed_nonzero,
        }


@dataclass(frozen=True, slots=True)
class LocalLogitErrorBound:
    variable: Variable
    bound: float

    def to_dict(self) -> dict[str, Any]:
        return {"variable": self.variable, "bound": self.bound}


@dataclass(frozen=True, slots=True)
class QuantizationAnalysis:
    """Auditable coefficient errors and optional exact distribution error."""

    beta: float
    fixed_point: FixedPointSpec
    coefficients: tuple[QuantizedCoefficient, ...]
    implemented_effective_model: IsingModel
    saturation_count: int
    zeroed_nonzero_count: int
    maximum_absolute_coefficient_error: float
    rms_coefficient_error: float
    state_log_weight_error_bound: float
    total_variation_upper_bound: float
    local_logit_error_bounds: tuple[LocalLogitErrorBound, ...]
    maximum_local_logit_error_bound: float
    exact_comparison_status: ExactComparisonStatus
    exact_comparison_reason: str | None
    exact_comparison: DistributionComparison | None

    @property
    def exactly_representable(self) -> bool:
        return self.maximum_absolute_coefficient_error == 0.0 and self.saturation_count == 0

    def to_dict(self, *, include_exact_observable_rows: bool = True) -> dict[str, Any]:
        return {
            "beta": self.beta,
            "fixed_point": self.fixed_point.to_dict(),
            "coefficient_count": len(self.coefficients),
            "coefficients": [row.to_dict() for row in self.coefficients],
            "saturation_count": self.saturation_count,
            "zeroed_nonzero_count": self.zeroed_nonzero_count,
            "maximum_absolute_coefficient_error": self.maximum_absolute_coefficient_error,
            "rms_coefficient_error": self.rms_coefficient_error,
            "state_log_weight_error_bound": self.state_log_weight_error_bound,
            "total_variation_upper_bound": self.total_variation_upper_bound,
            "local_logit_error_bounds": [row.to_dict() for row in self.local_logit_error_bounds],
            "maximum_local_logit_error_bound": self.maximum_local_logit_error_bound,
            "exactly_representable": self.exactly_representable,
            "exact_comparison_status": self.exact_comparison_status,
            "exact_comparison_reason": self.exact_comparison_reason,
            "exact_comparison": (
                None
                if self.exact_comparison is None
                else self.exact_comparison.to_dict(include_observable_rows=include_exact_observable_rows)
            ),
            "implemented_target_semantics": (
                "dimensionless Ising Hamiltonian from quantized beta-scaled h/J; "
                "original offset omitted because it cancels from normalized probabilities"
            ),
            "scope_limit": (
                "coefficient quantization only; excludes accumulated-local-field DAC "
                "quantization, arithmetic accumulation error, nonlinear response, delayed "
                "boundary states, drift, and circuit mismatch"
            ),
        }


def _nonnegative_beta(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError(f"beta must be a finite non-negative number, got {value!r}")
    beta = finite_float(value, name="beta")
    if beta < 0.0:
        raise ValueError(f"beta must be non-negative, got {value!r}")
    return beta


def _validate_exact_limit(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"max_exact_variables must be an integer >= 0, got {value!r}")
    return value


def _quantize_value(value: float, fixed_point: FixedPointSpec) -> tuple[float, bool]:
    canonical = finite_float(value, name="effective coefficient")
    outside = canonical < fixed_point.minimum or canonical > fixed_point.maximum
    if outside and fixed_point.overflow == "reject":
        raise ValueError(
            f"effective coefficient {canonical!r} is outside fixed-point range "
            f"[{fixed_point.minimum!r}, {fixed_point.maximum!r}] under overflow='reject'"
        )
    bounded = min(fixed_point.maximum, max(fixed_point.minimum, canonical))
    scaled = math.ldexp(bounded, fixed_point.fractional_bits)
    if fixed_point.rounding == "nearest_even":
        code = round(scaled)
    else:
        code = math.trunc(scaled)
    code = min(fixed_point.maximum_code, max(fixed_point.minimum_code, code))
    quantized = math.ldexp(float(code), -fixed_point.fractional_bits)
    # Avoid a negative zero leaking into serialized evidence.
    return (0.0 if quantized == 0.0 else quantized), outside


def _effective_value(beta: float, coefficient: float, *, name: str) -> float:
    return finite_float(beta * coefficient, name=name)


def _rms(errors: list[float]) -> float:
    if not errors:
        return 0.0
    maximum = max(errors)
    if maximum == 0.0:
        return 0.0
    normalized_square_sum = math.fsum((error / maximum) ** 2 for error in errors)
    return finite_float(
        maximum * math.sqrt(normalized_square_sum / len(errors)),
        name="RMS coefficient error",
    )


def analyze_quantization(
    model: IsingModel,
    fixed_point: FixedPointSpec,
    *,
    beta: float,
    max_exact_variables: int = 16,
) -> QuantizationAnalysis:
    """Quantize ``beta*h`` and ``beta*J`` and bound the resulting Gibbs-law error."""
    if not isinstance(model, IsingModel):
        raise TypeError(f"model must be IsingModel, got {type(model).__name__}")
    if not isinstance(fixed_point, FixedPointSpec):
        raise TypeError(f"fixed_point must be FixedPointSpec, got {type(fixed_point).__name__}")
    if not fixed_point.signed:
        raise ValueError("Ising coefficient quantization requires a signed fixed-point format")
    canonical_beta = _nonnegative_beta(beta)
    exact_limit = _validate_exact_limit(max_exact_variables)

    rows: list[QuantizedCoefficient] = []
    target_linear: dict[Variable, float] = {}
    quantized_linear: dict[Variable, float] = {}
    for variable in model.variables:
        target = _effective_value(
            canonical_beta,
            model.linear[variable],
            name=f"effective linear coefficient for {variable!r}",
        )
        quantized, saturated = _quantize_value(target, fixed_point)
        target_linear[variable] = target
        quantized_linear[variable] = quantized
        rows.append(
            QuantizedCoefficient(
                kind="linear",
                left=variable,
                right=None,
                target_effective=target,
                quantized_effective=quantized,
                error=quantized - target,
                saturated=saturated,
            )
        )

    target_quadratic: dict[tuple[Variable, Variable], float] = {}
    quantized_quadratic: dict[tuple[Variable, Variable], float] = {}
    for pair, coefficient in model.quadratic.items():
        target = _effective_value(
            canonical_beta,
            coefficient,
            name=f"effective quadratic coefficient for {pair!r}",
        )
        quantized, saturated = _quantize_value(target, fixed_point)
        target_quadratic[pair] = target
        quantized_quadratic[pair] = quantized
        rows.append(
            QuantizedCoefficient(
                kind="quadratic",
                left=pair[0],
                right=pair[1],
                target_effective=target,
                quantized_effective=quantized,
                error=quantized - target,
                saturated=saturated,
            )
        )

    format_metadata = fixed_point.to_dict()
    target_effective_model = IsingModel(
        variables=model.variables,
        linear=target_linear,
        quadratic=target_quadratic,
        offset=0.0,
        source_format="effective_ising",
        metadata={
            "effective_inverse_temperature": canonical_beta,
            "target_semantics": "beta-scaled canonical interaction coefficients",
        },
    )
    implemented_effective_model = IsingModel(
        variables=model.variables,
        linear=quantized_linear,
        quadratic=quantized_quadratic,
        offset=0.0,
        source_format="quantized_effective_ising",
        metadata={
            "effective_inverse_temperature": canonical_beta,
            "fixed_point": format_metadata,
            "target_semantics": "quantized beta-scaled canonical interaction coefficients",
            "original_offset_handling": "omitted; cancels from normalized probabilities",
        },
    )

    absolute_errors = [abs(row.error) for row in rows]
    maximum_error = max(absolute_errors, default=0.0)
    epsilon = finite_sum(absolute_errors, name="state log-weight error bound")
    local_field_errors = {variable: abs(rows[index].error) for index, variable in enumerate(model.variables)}
    quadratic_start = len(model.variables)
    for row in rows[quadratic_start:]:
        assert row.right is not None
        error = abs(row.error)
        local_field_errors[row.left] += error
        local_field_errors[row.right] += error
    local_bounds = tuple(
        LocalLogitErrorBound(
            variable=variable,
            bound=finite_float(
                2.0 * local_field_errors[variable],
                name=f"local logit error bound for {variable!r}",
            ),
        )
        for variable in model.variables
    )

    exact_comparison: DistributionComparison | None
    exact_status: ExactComparisonStatus
    exact_reason: str | None = None
    if len(model.variables) <= exact_limit:
        try:
            exact_comparison = compare_boltzmann_distributions(
                target_effective_model,
                implemented_effective_model,
                target_beta=1.0,
                implemented_beta=1.0,
                max_variables=exact_limit,
            )
        except ExactDistributionNumericalError as error:
            exact_comparison = None
            exact_status = "not_computed_numerical_range"
            exact_reason = str(error)
        else:
            exact_status = "computed"
    else:
        exact_comparison = None
        exact_status = "not_computed_too_many_variables"

    return QuantizationAnalysis(
        beta=canonical_beta,
        fixed_point=fixed_point,
        coefficients=tuple(rows),
        implemented_effective_model=implemented_effective_model,
        saturation_count=sum(row.saturated for row in rows),
        zeroed_nonzero_count=sum(row.zeroed_nonzero for row in rows),
        maximum_absolute_coefficient_error=maximum_error,
        rms_coefficient_error=_rms(absolute_errors),
        state_log_weight_error_bound=epsilon,
        total_variation_upper_bound=math.tanh(epsilon),
        local_logit_error_bounds=local_bounds,
        maximum_local_logit_error_bound=max((row.bound for row in local_bounds), default=0.0),
        exact_comparison_status=exact_status,
        exact_comparison_reason=exact_reason,
        exact_comparison=exact_comparison,
    )
