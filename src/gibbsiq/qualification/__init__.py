"""Dependency-free execution, evidence and stochastic qualification workflows.

Trusted adapters are supplied explicitly; inspection only reads evidence. The
legacy integer ``SampleResult`` remains a separate contract.
"""

from gibbsiq.qualification.artifacts import inspect_bundle
from gibbsiq.qualification.comparison import compare_bundles
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
from gibbsiq.qualification.policy_search import (
    Candidate,
    SearchPlan,
    SearchSpace,
    inspect_search,
    resolve_policy,
    run_search,
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
    "Candidate",
    "MetricBinding",
    "MetricResult",
    "MetricSpec",
    "Observation",
    "QualificationReport",
    "RunPlan",
    "SearchPlan",
    "SearchSpace",
    "WorkloadSpec",
    "evaluate_metric",
    "evaluate_metrics",
    "compare_bundles",
    "inspect_bundle",
    "inspect_search",
    "paired_difference_bounds",
    "required_units",
    "resolve_policy",
    "run_search",
    "qualify",
]
