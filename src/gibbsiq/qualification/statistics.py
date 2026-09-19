"""Fixed-sample statistical procedures for qualification metrics."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping

from gibbsiq.qualification._validation import _finite as _finite_float
from gibbsiq.qualification._validation import _probability
from gibbsiq.qualification.contracts import (
    AcceptanceContract,
    Bounds,
    MetricResult,
    MetricSpec,
)


_EXACT_PROCEDURE = "exact-v1"
_BOUNDED_PROCEDURE = "bounded-hoeffding-v1"


def _observations(values: Iterable[float], *, limit: int) -> tuple[float, ...]:
    if isinstance(values, (str, bytes, bytearray, Mapping, set, frozenset)):
        raise ValueError("values must be an iterable of finite numbers")
    try:
        iterator = iter(values)
    except TypeError as error:
        raise ValueError("values must be an iterable of finite numbers") from error
    summaries: list[float] = []
    while True:
        try:
            value = next(iterator)
        except StopIteration:
            return tuple(summaries)
        if len(summaries) == limit:
            raise ValueError("observed units cannot exceed planned_units")
        summaries.append(_finite_float(value, name=f"values[{len(summaries)}]"))


def _mean(values: tuple[float, ...]) -> float:
    """Return a finite mean without losing constant extreme observations."""
    if len(values) == 1 or all(value == values[0] for value in values[1:]):
        return values[0]
    try:
        result = math.fsum(values) / len(values)
    except OverflowError:
        anchor = values[0]
        try:
            displacement = math.fsum((value - anchor) / len(values) for value in values)
            result = anchor + displacement
        except OverflowError as error:
            raise ValueError("sample mean exceeds finite binary64 range") from error
    if not math.isfinite(result):
        raise ValueError("sample mean must remain finite")
    return 0.0 if result == 0.0 else result


def required_units(bounds: Bounds, *, alpha: float, half_width: float) -> int:
    """Return the fixed sample size for a two-sided Hoeffding interval."""
    if not isinstance(bounds, Bounds):
        raise ValueError("bounds must be Bounds")
    canonical_alpha = _probability(alpha, name="alpha")
    canonical_half_width = _finite_float(half_width, name="half_width")
    if canonical_half_width <= 0.0:
        raise ValueError("half_width must be positive")

    width = bounds.upper - bounds.lower
    if width == 0.0:
        return 1
    ratio = width / canonical_half_width
    if not math.isfinite(ratio):
        raise ValueError("requested sample size is not representable")
    sample_size = ratio * ratio * (math.log(2.0) - math.log(canonical_alpha)) / 2.0
    if not math.isfinite(sample_size):
        raise ValueError("requested sample size is not representable")
    try:
        return max(1, math.ceil(sample_size))
    except (OverflowError, ValueError) as error:
        raise ValueError("requested sample size is not representable") from error


def paired_difference_bounds(candidate: Bounds, reference: Bounds) -> Bounds:
    """Return the sharp range implied for candidate minus reference summaries."""
    if not isinstance(candidate, Bounds) or not isinstance(reference, Bounds):
        raise ValueError("candidate and reference must be Bounds")
    return Bounds(
        candidate.lower - reference.upper,
        candidate.upper - reference.lower,
    )


def _hoeffding_interval(
    estimate: float,
    bounds: Bounds,
    *,
    alpha: float,
    observed_units: int,
) -> Bounds:
    width = bounds.upper - bounds.lower
    if width == 0.0:
        return bounds
    scale = math.sqrt((math.log(2.0) - math.log(alpha)) / (2.0 * observed_units))
    if scale >= 1.0:
        return bounds
    radius = width * scale
    distance_to_lower = estimate - bounds.lower
    distance_to_upper = bounds.upper - estimate
    lower = bounds.lower if radius >= distance_to_lower else estimate - radius
    upper = bounds.upper if radius >= distance_to_upper else estimate + radius
    return Bounds(lower, upper)


def _unavailable(spec: MetricSpec, *, procedure: str) -> MetricResult:
    return MetricResult(
        metric_id=spec.metric_id,
        availability="unavailable",
        reason="no units were observed",
        observed_units=0,
        planned_units=spec.planned_units,
        procedure=procedure,
    )


def evaluate_metric(
    spec: MetricSpec,
    values: Iterable[float],
    *,
    alpha: float | None = None,
) -> MetricResult:
    """Evaluate one exact or predeclared fixed-sample bounded metric."""
    if not isinstance(spec, MetricSpec):
        raise ValueError("spec must be MetricSpec")
    summaries = _observations(values, limit=spec.planned_units)
    observed = len(summaries)
    if spec.bounds is not None and any(
        value < spec.bounds.lower or value > spec.bounds.upper for value in summaries
    ):
        raise ValueError("observed summary falls outside its declared bounds")

    if spec.evidence_mode == "exact":
        if alpha is not None:
            raise ValueError("exact metrics do not use alpha")
        procedure = _EXACT_PROCEDURE
        canonical_alpha = None
    else:
        if alpha is None:
            raise ValueError("bounded_fixed_n metrics require alpha")
        procedure = _BOUNDED_PROCEDURE
        canonical_alpha = _probability(alpha, name="alpha")

    if observed == 0:
        return _unavailable(spec, procedure=procedure)

    if spec.evidence_mode == "exact":
        estimate = summaries[0]
        interval = Bounds(estimate, estimate)
    else:
        assert spec.bounds is not None
        assert canonical_alpha is not None
        estimate = _mean(summaries)
        interval = _hoeffding_interval(
            estimate,
            spec.bounds,
            alpha=canonical_alpha,
            observed_units=observed,
        )

    if not spec.mandatory:
        outcome = "inconclusive"
        reason = "optional metrics are descriptive and cannot qualify a candidate"
    elif observed < spec.planned_units:
        outcome = "inconclusive"
        reason = "the predeclared fixed sample is incomplete"
    else:
        outcome = spec.acceptance.classify(interval)
        reason = None
    return MetricResult(
        metric_id=spec.metric_id,
        availability="available",
        estimate=estimate,
        interval=interval,
        outcome=outcome,
        reason=reason,
        observed_units=observed,
        planned_units=spec.planned_units,
        procedure=procedure,
        alpha=canonical_alpha,
        unit_summaries=summaries,
    )


def evaluate_metrics(
    contract: AcceptanceContract,
    values_by_id: Mapping[str, Iterable[float]],
) -> tuple[MetricResult, ...]:
    """Evaluate every metric in declaration order with fixed Bonferroni allocation."""
    if not isinstance(contract, AcceptanceContract):
        raise ValueError("contract must be AcceptanceContract")
    if not isinstance(values_by_id, Mapping):
        raise ValueError("values_by_id must be a mapping")
    declared = {metric.metric_id for metric in contract.metrics}
    supplied = set(values_by_id)
    if supplied != declared:
        missing = sorted(declared - supplied)
        extra = sorted(supplied - declared, key=repr)
        raise ValueError(
            f"values_by_id must exactly match declared metrics; missing={missing!r}, extra={extra!r}"
        )

    results: list[MetricResult] = []
    for metric in contract.metrics:
        if metric.evidence_mode == "exact":
            metric_alpha = None
        elif metric.mandatory:
            metric_alpha = contract.alpha_for(metric.metric_id)
        else:
            metric_alpha = contract.alpha_total
        results.append(evaluate_metric(metric, values_by_id[metric.metric_id], alpha=metric_alpha))
    return tuple(results)
