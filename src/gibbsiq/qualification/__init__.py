"""Dependency-free contracts and calculations for stochastic qualification.

These foundations do not execute models or create evidence bundles. The legacy
integer ``SampleResult`` remains a separate contract.
"""

from gibbsiq.qualification.contracts import (
    Acceptance,
    AcceptanceContract,
    Bounds,
    MetricResult,
    MetricSpec,
    Observation,
    QualificationReport,
    WorkloadSpec,
)
from gibbsiq.qualification.statistics import (
    evaluate_metric,
    evaluate_metrics,
    paired_difference_bounds,
    required_units,
)

__all__ = [
    "Acceptance",
    "AcceptanceContract",
    "Bounds",
    "MetricResult",
    "MetricSpec",
    "Observation",
    "QualificationReport",
    "WorkloadSpec",
    "evaluate_metric",
    "evaluate_metrics",
    "paired_difference_bounds",
    "required_units",
]
