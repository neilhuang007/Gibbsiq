"""Evaluate frozen metric bindings after bounded trusted-adapter execution."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path

from gibbsiq.qualification.artifacts import (
    BundleWriter,
    StorageLimitError,
    bound_metric_values,
)
from gibbsiq.qualification.contracts import MetricResult, QualificationReport, RunPlan
from gibbsiq.qualification.engine import UnsupportedCapabilityError, execute_plan
from gibbsiq.qualification.statistics import _classify_qualification, evaluate_metrics


def _unavailable(plan: RunPlan, reason: str) -> tuple[MetricResult, ...]:
    return tuple(
        MetricResult(
            metric_id=metric.metric_id,
            availability="unavailable",
            reason=reason,
            planned_units=metric.planned_units,
            procedure="exact-v1" if metric.evidence_mode == "exact" else "bounded-hoeffding-v1",
        )
        for metric in plan.workload.contract.metrics
    )


def qualify(
    plan: RunPlan,
    *,
    backends: Mapping[str, object],
    destination: str | Path,
    resume: bool = False,
    cancel: Callable[[], bool] | None = None,
) -> QualificationReport:
    """Execute a plan and persist a report using its declared observation bindings."""
    if not isinstance(plan, RunPlan) or not plan.metric_bindings:
        raise ValueError("qualify requires a RunPlan with frozen metric bindings")
    if not isinstance(backends, Mapping):
        raise ValueError("backends must map trusted candidate identities to adapters")
    candidate = plan.workload.candidate.identity
    unsupported_reason: str | None = None
    summary = None
    if candidate not in backends:
        unsupported_reason = f"no trusted backend for candidate {candidate!r}"
        writer = BundleWriter.resume(destination, plan) if resume else BundleWriter.create(destination, plan)
        attempts = writer.attempts
    else:
        try:
            summary = execute_plan(
                plan, backend=backends[candidate], destination=destination, resume=resume, cancel=cancel
            )
        except UnsupportedCapabilityError as error:
            unsupported_reason = str(error)
            summary = None
        writer = BundleWriter.resume(destination, plan)
        attempts = summary.attempts if summary is not None else writer.attempts

    reason: str | None
    if unsupported_reason is not None:
        execution = "partial"
        metrics = _unavailable(plan, unsupported_reason)
        qualification = "unsupported"
        reason = unsupported_reason
    else:
        assert summary is not None
        execution = summary.execution
        reason = summary.reason
        try:
            values = bound_metric_values(plan, attempts)
            metrics = evaluate_metrics(plan.workload.contract, values)
        except ValueError as error:
            reason = f"invalid bound metric evidence: {error}"
            metrics = _unavailable(plan, reason)
            qualification = "invalid"
        else:
            qualification = _classify_qualification(plan.workload.contract, metrics, execution)
    completed_ids = {attempt.run_id for attempt in attempts if attempt.execution == "complete"}
    completed = tuple(run.run_id for run in plan.runs if run.run_id in completed_ids)
    report = QualificationReport(
        workload_digest=plan.workload.semantic_digest(),
        contract=plan.workload.contract,
        execution=execution,
        qualification=qualification,
        metrics=metrics,
        expected_run_ids=tuple(run.run_id for run in plan.runs),
        completed_run_ids=completed,
        reason=reason,
    )
    try:
        writer.finish(execution=execution, report=report)
    except StorageLimitError:
        # The journal remains valid and inspection ignores derived files without
        # a final manifest. A computed pass is not a completed evidence bundle.
        return replace(
            report,
            execution="partial",
            qualification="inconclusive" if report.qualification == "pass" else report.qualification,
            reason="retained storage budget exhausted during report finalization; evidence remains partial",
        )
    return report


__all__ = ["qualify"]
