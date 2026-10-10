"""A resource-limited experiment preserves evidence without claiming success."""

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from gibbsiq.qualification.adapters.spin import SpinConditionalBackend
from gibbsiq.qualification.artifacts import inspect_bundle
from gibbsiq.qualification.examples import spin_conditional_plan
from gibbsiq.qualification.workflow import qualify


class QualificationLimitTests(unittest.TestCase):
    def test_a_computed_pass_without_room_for_the_report_cannot_return_success(self) -> None:
        plan = spin_conditional_plan(runs=16, margin=1.0)
        plan = replace(
            plan,
            workload=replace(plan.workload, resources=replace(plan.workload.resources, max_bytes=35_000)),
        )
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "evidence"
            report = qualify(
                plan,
                backends={plan.workload.candidate.identity: SpinConditionalBackend()},
                destination=destination,
            )
            self.assertEqual(report.metrics[0].outcome, "pass")
            self.assertEqual((report.execution, report.qualification), ("partial", "inconclusive"))
            snapshot = inspect_bundle(destination)
            self.assertEqual(len(snapshot.attempts), 16)
            self.assertEqual((snapshot.execution, snapshot.qualification), ("partial", "inconclusive"))
            self.assertIsNone(snapshot.report)

    def test_report_storage_exhaustion_returns_partial_retained_observations(self) -> None:
        plan = spin_conditional_plan(runs=16)
        plan = replace(
            plan,
            workload=replace(plan.workload, resources=replace(plan.workload.resources, max_bytes=20_000)),
        )
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "evidence"
            report = qualify(
                plan,
                backends={plan.workload.candidate.identity: SpinConditionalBackend()},
                destination=destination,
            )
            self.assertEqual((report.execution, report.qualification), ("partial", "inconclusive"))
            self.assertIn("storage", report.reason)
            snapshot = inspect_bundle(destination)
            self.assertEqual((snapshot.execution, snapshot.qualification), ("partial", "inconclusive"))
            self.assertGreater(len(snapshot.attempts), 0)
            actual = tuple(attempt.observations[0].values[0] - 0.5 for attempt in snapshot.attempts)
            self.assertEqual(report.metrics[0].unit_summaries, actual)
            self.assertLessEqual(
                sum(path.stat().st_size for path in destination.rglob("*") if path.is_file()), 20_000
            )


if __name__ == "__main__":
    unittest.main()
