"""Public numerical regression-comparison behavior."""

from __future__ import annotations

import contextlib
from dataclasses import replace
from io import StringIO
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest


class RegressionComparisonTests(unittest.TestCase):
    def _unfinished(self, root: Path, name: str, plan: object) -> Path:
        from gibbsiq.qualification.artifacts import BundleWriter

        destination = root / name
        BundleWriter.create(destination, plan).finish(execution="partial")
        return destination

    def _terminal(self, root: Path, name: str, plan: object, execution: str) -> Path:
        from gibbsiq.qualification.artifacts import BundleWriter

        destination = root / name
        BundleWriter.create(destination, plan).finish(execution=execution)
        return destination

    def _bundle(self, root: Path, name: str, candidate: str, runs: int = 256) -> Path:
        from gibbsiq.qualification.cli import main

        destination = root / name
        with contextlib.redirect_stdout(StringIO()):
            status = main(
                (
                    "qualify",
                    "--example",
                    "spin-conditional",
                    "--candidate",
                    candidate,
                    "--runs",
                    str(runs),
                    "--output",
                    str(destination),
                )
            )
        self.assertEqual(status, 0 if candidate == "iid" else 1)
        return destination

    def test_known_sign_defect_is_a_declared_regression_with_union_bound(self) -> None:
        from gibbsiq.qualification.comparison import compare_bundles

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = self._bundle(root, "baseline", "iid", 1024)
            candidate = self._bundle(root, "candidate", "sign-reversed")
            summary = compare_bundles(
                baseline, candidate, candidate_change="spin-conditional-sign-reversed-v1"
            )
        self.assertTrue(summary["compatible"])
        self.assertEqual(summary["outcome"], "regression")
        metric = summary["metrics"][0]
        self.assertLess(metric["delta"], -0.8)
        self.assertLess(metric["difference_interval"]["upper"], 0)
        self.assertAlmostEqual(metric["joint_error_bound"], 0.1)
        self.assertEqual(metric["difference_procedure"], "union-bound-difference-v1")

    def test_candidate_change_requires_exact_identity_and_does_not_hide_inputs(self) -> None:
        from gibbsiq.qualification.comparison import compare_bundles

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = self._bundle(root, "baseline", "iid", 1024)
            candidate = self._bundle(root, "candidate", "sign-reversed")
            rejected = compare_bundles(baseline, candidate)
            wrong = compare_bundles(baseline, candidate, candidate_change="wrong-id")
        self.assertFalse(rejected["compatible"])
        self.assertIn("candidate", {item["field"] for item in rejected["issues"]})
        self.assertFalse(wrong["compatible"])

    def test_changed_scientific_boundaries_are_field_specific_incompatibilities(self) -> None:
        from gibbsiq.qualification.comparison import compare_bundles
        from gibbsiq.qualification.contracts import ArtifactIdentity, AcceptanceContract, RunPlan
        from gibbsiq.qualification.examples import spin_conditional_plan

        plan = spin_conditional_plan(runs=1)
        workload = plan.workload
        digest = "sha256:" + "f" * 64
        changed = {
            "model_config": replace(workload, model_config=ArtifactIdentity("other-model", "1", digest)),
            "inputs.tokenizer": replace(
                workload,
                inputs=replace(workload.inputs, tokenizer=ArtifactIdentity("tokenizer", "1", digest)),
            ),
            "inputs.split": replace(
                workload,
                inputs=replace(
                    workload.inputs,
                    cases=(replace(workload.inputs.cases[0], split="development"),),
                ),
            ),
            "precision": replace(workload, precision={**workload.precision, "extra": "changed"}),
            "contract": replace(
                workload,
                contract=AcceptanceContract(
                    (replace(workload.contract.metrics[0], replication_unit="independent_draw"),),
                    workload.contract.alpha_total,
                ),
            ),
            "cost_scope": replace(workload, cost_scope=replace(workload.cost_scope, boundary="other")),
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = self._unfinished(root, "baseline", plan)
            for index, (expected, changed_workload) in enumerate(changed.items()):
                candidate = self._unfinished(
                    root,
                    f"candidate-{index}",
                    RunPlan(changed_workload, plan.runs, metric_bindings=plan.metric_bindings),
                )
                summary = compare_bundles(baseline, candidate)
                fields = {item["field"] for item in summary["issues"]}
                self.assertFalse(summary["compatible"], expected)
                self.assertIn(expected.split(".")[0], fields, (expected, fields))

    def test_partial_cost_records_are_unavailable_instead_of_averaging_present_subset(self) -> None:
        from gibbsiq.qualification.comparison import _aggregate_costs
        from gibbsiq.qualification.contracts import CostRecord, CostScope

        cost = CostRecord(
            "latency",
            "seconds",
            CostScope("complete-evaluation", ("model",), ("startup",)),
            "measured",
            "available",
            0.25,
            method="wall-clock-v1",
            omissions=("startup",),
        )
        snapshot = SimpleNamespace(
            attempts=(
                SimpleNamespace(execution="complete", costs=(cost,)),
                SimpleNamespace(execution="complete", costs=()),
            )
        )
        aggregate, count, complete = next(iter(_aggregate_costs(snapshot).values()))
        self.assertEqual((aggregate.availability, count, complete), ("unavailable", 1, 2))
        self.assertIn("missing from 1 complete runs", aggregate.reason)

    def test_reportless_terminal_lifecycle_is_not_collapsed_to_inconclusive(self) -> None:
        from gibbsiq.qualification.comparison import compare_bundles
        from gibbsiq.qualification.examples import spin_conditional_plan

        plan = spin_conditional_plan(runs=1)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = self._unfinished(root, "baseline", plan)
            error = self._terminal(root, "error", plan, "error")
            cancelled = self._terminal(root, "cancelled", plan, "cancelled")
            self.assertEqual(compare_bundles(baseline, error)["outcome"], "error")
            self.assertEqual(compare_bundles(baseline, cancelled)["outcome"], "cancelled")


if __name__ == "__main__":
    unittest.main()
