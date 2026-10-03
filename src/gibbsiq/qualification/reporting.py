"""Human rendering from the same frozen plan and stored metric results."""

from __future__ import annotations

from collections.abc import Mapping

from gibbsiq.qualification.contracts import QualificationReport, RunPlan, canonical_json


def _cell(value: object) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("`", "\\`")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def render_report(
    plan: RunPlan,
    *,
    execution: str,
    qualification: str,
    report: QualificationReport | None = None,
) -> str:
    """Render decisions and limitations without recalculating stored metrics."""
    if not isinstance(plan, RunPlan):
        raise ValueError("plan must be RunPlan")
    if report is not None and (report.execution != execution or report.qualification != qualification):
        raise ValueError("report status contradicts requested rendering")
    lines = [
        "# Qualification evidence",
        "",
        f"Workload: {_cell(plan.workload.workload_id)}",
        f"Candidate: {_cell(plan.workload.candidate.identity)}",
        f"Execution: {_cell(execution)}",
        f"Qualification: {_cell(qualification)}",
        "",
        "## Metrics",
        "",
        "| Metric | Reference | Candidate mean | Difference estimate | Independent unit | Count | Difference interval | Margin | Unit bounds | Alpha | Decision | Procedure |",
        "| --- | ---: | ---: | ---: | --- | ---: | --- | --- | --- | ---: | --- | --- |",
    ]
    bindings = {binding.metric_id: binding for binding in plan.metric_bindings}
    results = {} if report is None else {result.metric_id: result for result in report.metrics}
    for spec in plan.workload.contract.metrics:
        binding = bindings.get(spec.metric_id)
        result = results.get(spec.metric_id)
        reference = "unknown" if binding is None else f"{binding.reference_value:.12g}"
        difference = "unavailable" if result is None or result.estimate is None else f"{result.estimate:.12g}"
        candidate_mean = (
            "unavailable"
            if binding is None or result is None or result.estimate is None
            else f"{binding.reference_value + result.estimate:.12g}"
        )
        count = (
            f"0/{spec.planned_units}" if result is None else f"{result.observed_units}/{result.planned_units}"
        )
        interval = (
            "unavailable"
            if result is None or result.interval is None
            else (f"[{result.interval.lower:.12g}, {result.interval.upper:.12g}]")
        )
        acceptance = spec.acceptance
        margin = (
            f"[{acceptance.lower:.12g}, {acceptance.upper:.12g}]"
            if acceptance.kind == "equivalence"
            else f"{acceptance.kind} {acceptance.lower if acceptance.kind == 'lower' else acceptance.upper:.12g}"
        )
        decision = "unavailable" if result is None else result.outcome or result.availability
        procedure = spec.evidence_mode if result is None else result.procedure
        bounds = (
            "unbounded" if spec.bounds is None else f"[{spec.bounds.lower:.12g}, {spec.bounds.upper:.12g}]"
        )
        alpha = "—" if result is None or result.alpha is None else f"{result.alpha:.12g}"
        lines.append(
            "| "
            + " | ".join(
                _cell(item)
                for item in (
                    spec.metric_id,
                    reference,
                    candidate_mean,
                    difference,
                    spec.replication_unit,
                    count,
                    interval,
                    margin,
                    bounds,
                    alpha,
                    decision,
                    procedure,
                )
            )
            + " |"
        )
    samples = sorted(
        {
            canonical_json(run.settings["samples"]).decode("utf-8")
            for run in plan.runs
            if "samples" in run.settings
        }
    )
    lines.extend(
        [
            "",
            "## Scope and limitations",
            "",
            f"- Planned runs: {len(plan.runs)}; samples per run: {_cell(samples if samples else 'unspecified')}.",
            "- Fixed-input software execution; intervals apply to declared independent run summaries.",
        ]
    )
    if report is not None and report.reason:
        lines.append(f"- Reason: {_cell(report.reason)}")
    return "\n".join(lines) + "\n"


def render_comparison(summary: Mapping[str, object]) -> str:
    """Render a comparison summary without recomputing any numerical result."""
    if not isinstance(summary, Mapping) or summary.get("schema") != "qualification-comparison-v1":
        raise ValueError("comparison summary must use qualification-comparison-v1")
    lines = [
        "# Qualification comparison",
        "",
        f"Compatible: {_cell(summary.get('compatible'))}",
        f"Outcome: {_cell(summary.get('outcome'))}",
        "",
    ]
    issues = summary.get("issues")
    if isinstance(issues, list) and issues:
        lines.extend(["## Compatibility issues", ""])
        for issue in issues:
            if isinstance(issue, Mapping):
                lines.append(f"- {_cell(issue.get('field', 'unknown'))}: {_cell(issue)}")
        return "\n".join(lines) + "\n"
    lines.extend(
        [
            "## Metrics",
            "",
            "| Metric | Baseline estimate | Candidate estimate | Delta | Union-bound difference range | Joint error bound |",
            "| --- | ---: | ---: | ---: | --- | ---: |",
        ]
    )
    metrics = summary.get("metrics")
    if isinstance(metrics, list):
        for metric in metrics:
            if not isinstance(metric, Mapping):
                continue
            baseline = metric.get("baseline")
            candidate = metric.get("candidate")
            baseline_estimate = baseline.get("estimate") if isinstance(baseline, Mapping) else None
            candidate_estimate = candidate.get("estimate") if isinstance(candidate, Mapping) else None
            interval = metric.get("difference_interval")
            range_text = (
                "unavailable"
                if not isinstance(interval, Mapping)
                else f"[{interval.get('lower')}, {interval.get('upper')}]"
            )
            lines.append(
                "| "
                + " | ".join(
                    _cell(value)
                    for value in (
                        metric.get("metric_id"),
                        baseline_estimate,
                        candidate_estimate,
                        metric.get("delta"),
                        range_text,
                        metric.get("joint_error_bound"),
                    )
                )
                + " |"
            )
            if metric.get("reason"):
                lines.append(f"  Reason: {_cell(metric.get('reason'))}")
    lines.extend(
        [
            "",
            "## Costs",
            "",
            "| Quantity | Availability | Baseline mean (count) | Candidate mean (count) | Delta | Ratio | Reason |",
            "| --- | --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    costs = summary.get("costs")
    if isinstance(costs, list):
        for cost in costs:
            if not isinstance(cost, Mapping):
                continue
            baseline = cost.get("baseline")
            candidate = cost.get("candidate")
            baseline_value = baseline.get("value") if isinstance(baseline, Mapping) else None
            candidate_value = candidate.get("value") if isinstance(candidate, Mapping) else None
            lines.append(
                "| "
                + " | ".join(
                    _cell(value)
                    for value in (
                        cost.get("quantity"),
                        cost.get("availability"),
                        f"{baseline_value} ({cost.get('baseline_count')})",
                        f"{candidate_value} ({cost.get('candidate_count')})",
                        cost.get("delta"),
                        cost.get("ratio"),
                        cost.get("reason"),
                    )
                )
                + " |"
            )
    lines.extend(["", "## Environment", ""])
    environment = summary.get("environment")
    if isinstance(environment, Mapping):
        for side in ("baseline", "candidate"):
            lines.append(f"- {_cell(side)}: {_cell(environment.get(side, {}))}")
    for side in ("baseline", "candidate"):
        bundle = summary.get(side)
        if isinstance(bundle, Mapping) and bundle.get("reason"):
            lines.append(f"- {_cell(side)} reason: {_cell(bundle.get('reason'))}")
    lines.extend(["", "## Limitations", ""])
    limitations = summary.get("limitations")
    if isinstance(limitations, list):
        lines.extend(f"- {_cell(item)}" for item in limitations)
    return "\n".join(lines) + "\n"


__all__ = ["render_comparison", "render_report"]
