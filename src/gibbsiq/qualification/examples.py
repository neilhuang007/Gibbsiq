"""Small, fully local qualification examples."""

from __future__ import annotations

import math

from gibbsiq.qualification.adapters.reference import spin_conditional
from gibbsiq.qualification._validation import _finite
from gibbsiq.qualification.contracts import (
    Acceptance,
    AcceptanceContract,
    ArtifactIdentity,
    Bounds,
    CostScope,
    InputCase,
    InputSpec,
    MetricBinding,
    MetricSpec,
    OperationSpec,
    PlannedRun,
    RandomizationSpec,
    ResourceBudget,
    RunPlan,
    WorkloadSpec,
    identity_digest,
)

SPIN_FIELD = math.log(3.0) / 2.0
SPIN_CANDIDATES = {
    "iid": "spin-conditional-iid-v1",
    "sign-reversed": "spin-conditional-sign-reversed-v1",
}


def _identity(name: str, value: object) -> ArtifactIdentity:
    return ArtifactIdentity(name, "1", identity_digest(value))


def spin_conditional_plan(
    *,
    runs: int = 1024,
    samples: int = 32,
    seed: int = 7,
    candidate: str = "iid",
    margin: float = 0.125,
) -> RunPlan:
    """Freeze one conditional-spin expectation and independent-run comparison."""
    if type(runs) is not int or not 1 <= runs <= 4096:
        raise ValueError("runs must be an integer from 1 through 4096")
    if type(samples) is not int or not 1 <= samples <= 4096:
        raise ValueError("samples must be an integer from 1 through 4096")
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    if candidate not in SPIN_CANDIDATES:
        raise ValueError("candidate must be iid or sign-reversed")
    margin = _finite(margin, name="margin")
    if margin <= 0:
        raise ValueError("margin must be finite and positive")
    field = SPIN_FIELD
    reference = spin_conditional(field)
    metric_id = "conditional_mean_error"
    operation_id = "conditional_spin"
    case_id = "fixed-field"
    identity = SPIN_CANDIDATES[candidate]
    source = _identity("gibbsiq-spin-conditional-source", {"law": "two-state-conditional", "version": 1})
    model = _identity("gibbsiq-spin-fixed-field", {"field": field, "spin_values": [-1, 1]})
    fixture = _identity("gibbsiq-spin-fixed-input", {"case": case_id, "field": field})
    preprocessing = _identity("gibbsiq-spin-identity-preprocessing", {"version": 1})
    reference_id = _identity("gibbsiq-spin-exponential-reference", {"field": field, "mean": reference.mean})
    candidate_id = _identity(
        identity, {"field": field, "profile": candidate, "rng": "python-random-full-sha256-int-v1"}
    )
    contract = AcceptanceContract(
        (
            MetricSpec(
                metric_id=metric_id,
                units="spin mean difference",
                direction="target",
                comparison="candidate-reference",
                acceptance=Acceptance("equivalence", lower=-margin, upper=margin),
                evidence_mode="bounded_fixed_n",
                planned_units=runs,
                replication_unit="independent_run",
                scope="fixed_inputs",
                bounds=Bounds(-1.5, 0.5),
            ),
        )
    )
    workload = WorkloadSpec(
        workload_id="spin-conditional-v1",
        description="IID software conditional spin at a fixed field",
        sources=(source,),
        model_config=model,
        inputs=InputSpec(
            fixture, preprocessing, (InputCase(case_id, fixture.digest, "evaluation", "fixed-field-group"),)
        ),
        operations=(OperationSpec(operation_id, (), ()),),
        dtype="float64",
        precision={
            "field": field,
            "profile": candidate,
            "rng_recipe": "python-random-mt19937-full-sha256-int-v1",
        },
        reference=reference_id,
        candidate=candidate_id,
        controls=("samples",),
        contract=contract,
        randomization=RandomizationSpec(seed, runs),
        resources=ResourceBudget(runs, 120.0, 16 * 1024 * 1024),
        cost_scope=CostScope(
            "software-candidate-spin-draws",
            ("python_rng", "spin_draw"),
            ("model_inference", "physical_device"),
        ),
        license_refs=("generated-fixture",),
    )
    planned = tuple(
        PlannedRun(f"run-{index:04d}", case_id, operation_id, "evaluation", {"samples": samples})
        for index in range(runs)
    )
    return RunPlan(
        workload,
        planned,
        metric_bindings=(
            MetricBinding(metric_id, "mean", tuple(run.run_id for run in planned), reference.mean),
        ),
    )


__all__ = ["SPIN_CANDIDATES", "SPIN_FIELD", "spin_conditional_plan"]
