"""Exercise statistical results through qualification report validation."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from gibbsiq.qualification.contracts import (  # noqa: E402
    Acceptance,
    AcceptanceContract,
    Bounds,
    MetricSpec,
    QualificationReport,
)
from gibbsiq.qualification.statistics import evaluate_metrics  # noqa: E402


WORKLOAD_DIGEST = "sha256:" + "0" * 64
BOUNDED_RUN_IDS = tuple(f"bounded-{index:02d}" for index in range(64))
EXPECTED_RUN_IDS = ("exact-run", *BOUNDED_RUN_IDS)


def acceptance_contract() -> AcceptanceContract:
    return AcceptanceContract(
        (
            MetricSpec(
                metric_id="exact-error",
                units="absolute error",
                direction="smaller_is_better",
                comparison="candidate-reference",
                acceptance=Acceptance("upper", upper=0.1),
                evidence_mode="exact",
                planned_units=1,
                replication_unit="deterministic",
                scope="fixed_inputs",
            ),
            MetricSpec(
                metric_id="mean-error",
                units="signed error",
                direction="target",
                comparison="candidate-reference",
                acceptance=Acceptance("equivalence", lower=-0.25, upper=0.25),
                evidence_mode="bounded_fixed_n",
                planned_units=64,
                replication_unit="independent_run",
                scope="fixed_inputs",
                bounds=Bounds(-0.5, 0.5),
            ),
        )
    )


class FoundationWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = acceptance_contract()

    def report(
        self,
        values_by_id: dict[str, tuple[float, ...]],
        *,
        execution: str,
        qualification: str,
        completed_run_ids: tuple[str, ...],
    ) -> QualificationReport:
        return QualificationReport(
            workload_digest=WORKLOAD_DIGEST,
            contract=self.contract,
            execution=execution,
            qualification=qualification,
            metrics=evaluate_metrics(self.contract, values_by_id),
            expected_run_ids=EXPECTED_RUN_IDS,
            completed_run_ids=completed_run_ids,
        )

    def test_complete_actual_results_construct_passing_report(self) -> None:
        report = self.report(
            {"exact-error": (0.0,), "mean-error": (0.0,) * 64},
            execution="complete",
            qualification="pass",
            completed_run_ids=EXPECTED_RUN_IDS,
        )

        self.assertEqual(
            tuple(result.procedure for result in report.metrics),
            ("exact-v1", "bounded-hoeffding-v1"),
        )
        self.assertEqual(tuple(result.outcome for result in report.metrics), ("pass", "pass"))

    def test_partial_actual_results_are_inconclusive_and_cannot_be_promoted(self) -> None:
        values = {"exact-error": (0.0,), "mean-error": (0.0,) * 63}
        report = self.report(
            values,
            execution="partial",
            qualification="inconclusive",
            completed_run_ids=EXPECTED_RUN_IDS[:-1],
        )

        self.assertEqual(report.metrics[1].outcome, "inconclusive")
        with self.assertRaises(ValueError):
            self.report(
                values,
                execution="partial",
                qualification="pass",
                completed_run_ids=EXPECTED_RUN_IDS[:-1],
            )

    def test_unavailable_bounded_result_has_no_alpha_and_is_inconclusive(self) -> None:
        report = self.report(
            {"exact-error": (0.0,), "mean-error": ()},
            execution="partial",
            qualification="inconclusive",
            completed_run_ids=("exact-run",),
        )

        bounded = report.metrics[1]
        self.assertEqual(bounded.availability, "unavailable")
        self.assertIsNone(bounded.alpha)
        self.assertEqual(bounded.procedure, "bounded-hoeffding-v1")

    def test_precise_actual_failure_constructs_failing_report(self) -> None:
        report = self.report(
            {"exact-error": (0.2,), "mean-error": (0.0,) * 64},
            execution="complete",
            qualification="fail",
            completed_run_ids=EXPECTED_RUN_IDS,
        )

        failed = report.metrics[0]
        self.assertEqual(failed.outcome, "fail")
        self.assertEqual(failed.interval, Bounds(0.2, 0.2))


if __name__ == "__main__":
    unittest.main()
