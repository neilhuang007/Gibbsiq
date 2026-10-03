"""Offline, identity-aware comparison of retained qualification bundles."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any

from gibbsiq.qualification.artifacts import inspect_bundle, record_to_dict
from gibbsiq.qualification.contracts import CostRecord, MetricResult, canonical_json
from gibbsiq.qualification.costs import compare_costs


def _issue_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return record_to_dict(value)
    if isinstance(value, Mapping):
        return {str(key): _issue_value(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return [_issue_value(child) for child in value]
    return value


def _issue(issues: list[dict[str, Any]], field: str, baseline: Any, candidate: Any) -> None:
    issues.append({"field": field, "baseline": _issue_value(baseline), "candidate": _issue_value(candidate)})


def _same(issues: list[dict[str, Any]], field: str, baseline: Any, candidate: Any) -> None:
    if baseline != candidate:
        _issue(issues, field, baseline, candidate)


def _candidate_allowed(left: Any, right: Any, expected: str | None) -> bool:
    if left == right:
        return True
    return expected is not None and right.identity == expected


def _precision_allowed(left: Any, right: Any, *, spin_change: bool) -> bool:
    left_value = dict(left)
    right_value = dict(right)
    if spin_change:
        left_profile = left_value.pop("profile", None)
        right_profile = right_value.pop("profile", None)
        if (left_profile, right_profile) not in {
            ("iid", "sign-reversed"),
            ("sign-reversed", "iid"),
        }:
            return False
    return left_value == right_value


def _contract_semantics(contract: Any) -> tuple[Any, ...]:
    return (
        contract.alpha_total,
        tuple(
            (
                item.metric_id,
                item.units,
                item.direction,
                item.comparison,
                item.acceptance,
                item.evidence_mode,
                item.replication_unit,
                item.scope,
                item.bounds,
                item.mandatory,
                item.aggregation,
            )
            for item in contract.metrics
        ),
    )


def _compatibility(baseline: Any, candidate: Any, expected: str | None) -> list[dict[str, Any]]:
    left = baseline.plan.workload
    right = candidate.plan.workload
    issues: list[dict[str, Any]] = []
    for field in (
        "workload_id",
        "sources",
        "model_config",
        "checkpoint",
        "inputs",
        "operations",
        "dtype",
        "reference",
        "cost_scope",
    ):
        _same(issues, field, getattr(left, field), getattr(right, field))
    _same(
        issues,
        "contract",
        _contract_semantics(left.contract),
        _contract_semantics(right.contract),
    )
    if not _candidate_allowed(left.candidate, right.candidate, expected):
        _issue(issues, "candidate", left.candidate, right.candidate)
    spin_change = (
        expected is not None
        and left.workload_id == right.workload_id == "spin-conditional-v1"
        and {left.precision.get("profile"), right.precision.get("profile")} == {"iid", "sign-reversed"}
    )
    if not _precision_allowed(left.precision, right.precision, spin_change=spin_change):
        _issue(issues, "precision", dict(left.precision), dict(right.precision))
    left_metrics = {item.metric_id: item for item in baseline.report.metrics} if baseline.report else {}
    right_metrics = {item.metric_id: item for item in candidate.report.metrics} if candidate.report else {}
    if left_metrics.keys() != right_metrics.keys():
        _issue(issues, "report.metrics", sorted(left_metrics), sorted(right_metrics))
    else:
        for metric_id in left_metrics:
            if left_metrics[metric_id].procedure != right_metrics[metric_id].procedure:
                _issue(
                    issues,
                    f"metrics.{metric_id}.procedure",
                    left_metrics[metric_id].procedure,
                    right_metrics[metric_id].procedure,
                )
    return issues


def _metric(left: MetricResult, right: MetricResult) -> dict[str, Any]:
    item: dict[str, Any] = {
        "metric_id": left.metric_id,
        "baseline": record_to_dict(left),
        "candidate": record_to_dict(right),
        "delta": None,
        "difference_interval": None,
        "joint_error_bound": None,
        "difference_procedure": "union-bound-difference-v1",
        "reason": None,
    }
    if left.availability != "available" or right.availability != "available":
        reasons = []
        for name, result in (("baseline", left), ("candidate", right)):
            if result.availability != "available":
                reasons.append(f"{name}: {result.availability} ({result.reason})")
        item["reason"] = "; ".join(reasons)
        return item
    assert left.estimate is not None and right.estimate is not None
    item["delta"] = right.estimate - left.estimate
    if left.interval is None or right.interval is None:
        item["reason"] = "difference interval unavailable because an original interval is missing"
        return item
    item["difference_interval"] = {
        "lower": right.interval.lower - left.interval.upper,
        "upper": right.interval.upper - left.interval.lower,
    }
    item["joint_error_bound"] = (left.alpha or 0.0) + (right.alpha or 0.0)
    return item


def _aggregate_costs(snapshot: Any) -> dict[tuple[Any, ...], tuple[CostRecord, int, int]]:
    grouped: dict[tuple[Any, ...], list[CostRecord]] = defaultdict(list)
    complete_attempts = [attempt for attempt in snapshot.attempts if attempt.execution == "complete"]
    for attempt in complete_attempts:
        for cost in attempt.costs:
            key = (
                cost.quantity,
                cost.units,
                canonical_json(record_to_dict(cost.scope)),
                cost.provenance,
                cost.method,
                cost.omissions,
            )
            grouped[key].append(cost)
    result = {}
    for key, records in grouped.items():
        available = [item.value for item in records if item.availability == "available"]
        if len(records) != len(complete_attempts):
            template = records[0]
            aggregate = CostRecord(
                template.quantity,
                template.units,
                template.scope,
                template.provenance,
                "unavailable",
                reason=f"cost claim missing from {len(complete_attempts) - len(records)} complete runs",
                method=template.method,
                omissions=template.omissions,
            )
        elif len(available) == len(records):
            template = records[0]
            average = sum(value for value in available if value is not None) / len(available)
            aggregate = CostRecord(
                template.quantity,
                template.units,
                template.scope,
                template.provenance,
                "available",
                average,
                method=template.method,
                omissions=template.omissions,
            )
        else:
            template = records[0]
            reasons = sorted(
                {item.reason or item.availability for item in records if item.availability != "available"}
            )
            aggregate = CostRecord(
                template.quantity,
                template.units,
                template.scope,
                template.provenance,
                "unavailable",
                reason="; ".join(reasons),
                method=template.method,
                omissions=template.omissions,
            )
        result[key] = (aggregate, len(records), len(complete_attempts))
    return result


def _costs(baseline: Any, candidate: Any) -> list[dict[str, Any]]:
    left = _aggregate_costs(baseline)
    right = _aggregate_costs(candidate)
    entries = []
    for key in sorted(set(left) | set(right), key=lambda item: repr(item)):
        left_item = left.get(key)
        right_item = right.get(key)
        if left_item is None or right_item is None:
            entries.append(
                {
                    "quantity": key[0],
                    "baseline": None if left_item is None else record_to_dict(left_item[0]),
                    "candidate": None if right_item is None else record_to_dict(right_item[0]),
                    "baseline_count": 0 if left_item is None else left_item[1],
                    "candidate_count": 0 if right_item is None else right_item[1],
                    "baseline_complete_runs": 0 if left_item is None else left_item[2],
                    "candidate_complete_runs": 0 if right_item is None else right_item[2],
                    "availability": "unavailable",
                    "delta": None,
                    "ratio": None,
                    "reason": "cost claim is absent from one bundle",
                }
            )
            continue
        comparison = compare_costs(left_item[0], right_item[0])
        entries.append(
            {
                "quantity": key[0],
                "baseline": record_to_dict(left_item[0]),
                "candidate": record_to_dict(right_item[0]),
                "baseline_count": left_item[1],
                "candidate_count": right_item[1],
                "baseline_complete_runs": left_item[2],
                "candidate_complete_runs": right_item[2],
                "availability": comparison.availability,
                "delta": comparison.delta,
                "ratio": comparison.ratio,
                "reason": comparison.reason,
            }
        )
    return entries


def _bundle_summary(snapshot: Any) -> dict[str, Any]:
    return {
        "execution": snapshot.execution,
        "qualification": snapshot.qualification,
        "reason": snapshot.reason,
        "workload_digest": snapshot.plan.workload.semantic_digest(),
        "candidate": record_to_dict(snapshot.plan.workload.candidate),
        "planned_runs": len(snapshot.plan.runs),
        "completed_runs": len({item.run_id for item in snapshot.attempts if item.execution == "complete"}),
        "manifest_digest": snapshot.manifest_digest,
        "retained_bytes": snapshot.retained_bytes,
    }


def _scientific_outcome(left: Any, right: Any) -> str:
    snapshots = (left, right)
    if any(item.execution == "cancelled" for item in snapshots):
        return "cancelled"
    if any(item.execution == "error" for item in snapshots):
        return "error"
    reports = tuple(item.report for item in snapshots)
    if any(report is not None and report.qualification == "invalid" for report in reports):
        return "invalid"
    if any(
        item.qualification == "unsupported" or (report is not None and report.qualification == "unsupported")
        for item, report in zip(snapshots, reports)
    ):
        return "unsupported"
    if any(item.execution != "complete" or report is None for item, report in zip(snapshots, reports)):
        return "inconclusive"
    left_report, right_report = reports
    assert left_report is not None and right_report is not None
    if left_report.qualification == "pass" and right_report.qualification == "fail":
        return "regression"
    if left_report.qualification == right_report.qualification == "pass":
        return "no_regression_under_contract"
    return "inconclusive"


def compare_bundles(
    baseline: str | Path, candidate: str | Path, *, candidate_change: str | None = None
) -> dict[str, Any]:
    """Verify and compare two local bundles without executing either backend."""
    if candidate_change is not None and (type(candidate_change) is not str or not candidate_change.strip()):
        raise ValueError("candidate_change must be a nonblank candidate identity")
    left = inspect_bundle(baseline, verify=True)
    right = inspect_bundle(candidate, verify=True)
    issues = _compatibility(left, right, candidate_change)
    summary: dict[str, Any] = {
        "schema": "qualification-comparison-v1",
        "compatible": not issues,
        "outcome": "incompatible" if issues else "inconclusive",
        "issues": issues,
        "baseline": _bundle_summary(left),
        "candidate": _bundle_summary(right),
        "metrics": [],
        "costs": [],
        "environment": {
            "baseline": dict(left.environment),
            "candidate": dict(right.environment),
        },
        "limitations": [
            "Difference ranges use a union bound and are not paired confidence intervals.",
            "Timing deltas are descriptive; unavailable energy is not treated as zero.",
            "The outcome applies only to the shared declared acceptance contract.",
        ],
    }
    if issues:
        return summary
    summary["outcome"] = _scientific_outcome(left, right)
    if left.report is None or right.report is None:
        summary["issues"] = [{"field": "report", "reason": "a retained report is missing"}]
        return summary
    right_metrics = {item.metric_id: item for item in right.report.metrics}
    summary["metrics"] = [_metric(item, right_metrics[item.metric_id]) for item in left.report.metrics]
    summary["costs"] = _costs(left, right)
    return summary


__all__ = ["compare_bundles"]
