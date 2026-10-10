from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.qualification import check_compatibility_update as maintenance


def _probe(version: str, *, adapter: str, draws: list[list[int]]) -> dict[str, object]:
    counts = [0, 0, 0, 0]
    for left, right in draws:
        counts[left * 2 + right] += 1
    return {
        "schema": "torx-compatibility-probe-v1",
        "environment": {
            "python": "3.13.5",
            "extro_torx": version,
            "jax": "0.10.2",
            "jaxlib": "0.10.2",
            "equinox": "0.13.8",
            "numpy": "2.4.6",
        },
        "pip_check": {"exit_code": 0, "stdout": "No broken requirements found."},
        "adapter": {"status": adapter, "reason": "source/version differs" if adapter != "accepted" else None},
        "exact": {"observed": [0.5, 0.0, 0.25, 0.25], "expected": [0.5, 0.0, 0.25, 0.25]},
        "changed_exact": {
            "observed": [0.0, 0.3318122278318333, 0.6681877721681667, 0.0],
            "expected": [0.0, 0.3318122278318333, 0.6681877721681667, 0.0],
        },
        "sampling": {"draws": len(draws), "counts": counts},
    }


class CompatibilityUpdateTests(unittest.TestCase):
    def test_failed_control_prevents_candidate_promotion(self) -> None:
        draws = [[0, 0]] * 96 + [[1, 0]] * 48 + [[1, 1]] * 48
        candidate = _probe("0.0.2", adapter="accepted", draws=draws)
        for failure in ("law", "exact", "changed_context", "dependencies", "adapter"):
            with self.subTest(failure=failure):
                control = _probe("0.0.1", adapter="accepted", draws=draws)
                if failure == "law":
                    control["sampling"]["counts"] = [0, 192, 0, 0]
                elif failure == "exact":
                    control["exact"]["observed"] = [0.0, 1.0, 0.0, 0.0]
                elif failure == "changed_context":
                    control["changed_exact"]["observed"] = [1.0, 0.0, 0.0, 0.0]
                elif failure == "dependencies":
                    control["pip_check"]["exit_code"] = 1
                else:
                    control["adapter"]["status"] = "rejected_unqualified"
                report = maintenance.compare_probes(control, candidate)
                self.assertEqual(report["outcome"], "invalid_control")
                self.assertEqual(report["recommendation"], "repair_control_before_comparison")

    def test_candidate_requires_numerical_and_dependency_checks_to_pass(self) -> None:
        draws = [[0, 0]] * 96 + [[1, 0]] * 48 + [[1, 1]] * 48
        control = _probe("0.0.1", adapter="accepted", draws=draws)
        for failure in ("none", "law", "exact", "dependencies"):
            with self.subTest(failure=failure):
                candidate = _probe("0.0.2", adapter="accepted", draws=draws)
                if failure == "law":
                    candidate["sampling"]["counts"] = [0, 192, 0, 0]
                elif failure == "exact":
                    candidate["exact"]["observed"] = [0.0, 1.0, 0.0, 0.0]
                elif failure == "dependencies":
                    candidate["pip_check"]["exit_code"] = 1
                report = maintenance.compare_probes(control, candidate)
                self.assertEqual(report["outcome"], "compatible" if failure == "none" else "incompatible")
                self.assertEqual(
                    report["recommendation"],
                    "candidate_eligible_for_review" if failure == "none" else "retain_pinned_control",
                )

    def test_report_classifies_candidate_adapter_rejection_without_losing_upstream_evidence(self) -> None:
        control = _probe("0.0.1", adapter="accepted", draws=[[0, 0]] * 96 + [[1, 0]] * 48 + [[1, 1]] * 48)
        candidate = _probe(
            "0.0.2", adapter="rejected_unqualified", draws=[[0, 0]] * 95 + [[1, 0]] * 49 + [[1, 1]] * 48
        )
        report = maintenance.compare_probes(control, candidate)
        self.assertEqual(report["outcome"], "incompatible")
        self.assertFalse(report["candidate_adapter_supported"])
        self.assertTrue(report["candidate_upstream_exact_reference_passed"])
        self.assertTrue(report["candidate_sample_law_passed"])
        self.assertLess(report["comparison"]["candidate_total_variation"], 0.03)

    def test_report_rejects_bad_numeric_evidence_and_unbounded_output(self) -> None:
        control = _probe("0.0.1", adapter="accepted", draws=[[0, 0]] * 96 + [[1, 0]] * 48 + [[1, 1]] * 48)
        candidate = _probe("0.0.2", adapter="rejected_unqualified", draws=[[0, 1]] * 192)
        report = maintenance.compare_probes(control, candidate)
        self.assertFalse(report["candidate_sample_law_passed"])
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "report.json"
            with self.assertRaisesRegex(RuntimeError, "32 MiB"):
                maintenance.write_report(path, {"payload": "x" * (32 * 1024 * 1024 + 1)})
            self.assertFalse(path.exists())

    def test_runner_uses_each_interpreter_and_records_probe_failures(self) -> None:
        good = _probe("0.0.1", adapter="accepted", draws=[[0, 0]] * 4)
        outcomes = [
            subprocess.CompletedProcess([], 0, json.dumps(good), ""),
            subprocess.CompletedProcess([], 7, "", "candidate import failed"),
        ]
        with patch.object(maintenance.subprocess, "run", side_effect=outcomes) as run:
            report = maintenance.run_cycle(Path("control.exe"), Path("candidate.exe"), timeout_seconds=12)
        self.assertEqual(report["outcome"], "candidate_probe_failed")
        self.assertEqual(report["candidate_probe"]["exit_code"], 7)
        self.assertEqual(run.call_count, 2)
        self.assertTrue(all(call.kwargs["timeout"] == 12 for call in run.call_args_list))


if __name__ == "__main__":
    unittest.main()
