"""Dependency-free execution, evidence and stochastic qualification workflows.

Trusted adapters are supplied explicitly; inspection only reads evidence. The
legacy integer ``SampleResult`` remains a separate contract.
"""

from gibbsiq.qualification.artifacts import inspect_bundle

from gibbsiq.qualification.contracts import (
    Acceptance,
    AcceptanceContract,
    Bounds,
    MetricBinding,
    MetricResult,
    MetricSpec,
    Observation,
    QualificationReport,
    RunPlan,
    WorkloadSpec,
)

from gibbsiq.qualification.workflow import qualify

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
    "MetricBinding",
    "MetricResult",
    "MetricSpec",
    "Observation",
    "QualificationReport",
    "RunPlan",
    "WorkloadSpec",
    "evaluate_metric",
    "evaluate_metrics",
    "inspect_bundle",
    "paired_difference_bounds",
    "required_units",
    "qualify",
]
