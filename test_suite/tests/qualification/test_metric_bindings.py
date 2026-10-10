"""Frozen evaluation mappings prevent post-run selection of metric inputs."""

from __future__ import annotations

from dataclasses import replace
import unittest

from gibbsiq.qualification.contracts import MetricBinding
from test_suite.tests.qualification.test_contracts import acceptance_contract, bounded_metric, workload
from gibbsiq.qualification.contracts import PlannedRun, ResourceBudget, RunPlan


class MetricBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workload = workload(
            contract=acceptance_contract(bounded_metric(planned_units=2)),
            resources=ResourceBudget(4, 30, 1024 * 1024),
        )
        self.runs = tuple(
            PlannedRun(f"run-{index}", "case-1", "activation", "evaluation", {"samples": 32})
            for index in range(2)
        )
        self.binding = MetricBinding("mean-error", "mean", ("run-0", "run-1"), reference_value=0.5)

    def test_frozen_mapping_retains_run_order_and_reference_without_mutable_aliases(self) -> None:
        selected = ["run-1", "run-0"]
        binding = replace(self.binding, run_ids=selected)
        plan = RunPlan(self.workload, self.runs, metric_bindings=(binding,))
        selected.clear()
        self.assertEqual(plan.metric_bindings[0].run_ids, ("run-1", "run-0"))
        self.assertEqual(plan.metric_bindings[0].reference_value, 0.5)

    def test_mapping_rejects_omitted_extra_repeated_and_unplanned_replication_units(self) -> None:
        for selected in (("run-0",), ("run-0", "run-1", "run-2"), ("run-0", "run-0"), ("run-0", "absent")):
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                binding = replace(self.binding, run_ids=selected)
                RunPlan(self.workload, self.runs, metric_bindings=(binding,))

    def test_mapping_cannot_omit_or_rename_a_declared_metric(self) -> None:
        binding = replace(self.binding, metric_id="unplanned-error")
        with self.assertRaises(ValueError):
            RunPlan(self.workload, self.runs, metric_bindings=(binding,))

    def test_reference_and_observation_name_are_validated_before_execution(self) -> None:
        for changes in (
            {"reference_value": float("nan")},
            {"reference_value": True},
            {"observation_name": ""},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(self.binding, **changes)


if __name__ == "__main__":
    unittest.main()
