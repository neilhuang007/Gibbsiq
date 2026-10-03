"""Decision behavior of the bounded, fixed-input checkpoint experiment."""

from __future__ import annotations

import math
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from gibbsiq.qualification.model_evaluation import CorpusSplit, TokenDocument, language_loss
from tools.qualification.verify_trained_checkpoint import assess_study, run_study


class TrainedCheckpointStudyTests(unittest.TestCase):
    def test_same_model_passes_and_reversed_predictions_fail(self) -> None:
        reference = language_loss([[4.0, 0.0], [0.0, 4.0]], [0, 1], cap=16.0)
        reversed_model = language_loss([[-4.0, 0.0], [0.0, -4.0]], [0, 1], cap=16.0)
        report = assess_study(reference, reference, reversed_model, {8: [], 32: [], 128: []})
        self.assertEqual(report["controls"]["unchanged"]["outcome"], "pass")
        self.assertEqual(report["controls"]["negated_logits"]["outcome"], "fail")
        self.assertAlmostEqual(report["controls"]["negated_logits"]["estimate"], 4.0)

    def test_eight_identical_runs_do_not_create_a_false_guarantee(self) -> None:
        reference = language_loss([[0.0, 0.0]], [0], cap=16.0)
        results = {budget: [reference] * 8 for budget in (8, 32, 128)}
        report = assess_study(reference, reference, reference, results)
        for result in report["candidates"].values():
            self.assertEqual(result["outcome"], "inconclusive")
            self.assertEqual(result["observed_units"], 8)
            self.assertAlmostEqual(result["interval"]["lower"], -math.log(2))
            self.assertGreater(result["interval"]["upper"], 0.5)
        self.assertGreater(report["runs_for_half_width_0_5"], 2000)

    def test_partial_attempt_is_retained_as_incomplete(self) -> None:
        reference = language_loss([[0.0, 0.0]], [0], cap=16.0)
        report = assess_study(reference, reference, reference, {8: [reference], 32: [], 128: []})
        self.assertEqual(report["candidates"]["8"]["observed_units"], 1)
        self.assertEqual(report["candidates"]["8"]["outcome"], "inconclusive")
        self.assertEqual(report["candidates"]["32"]["availability"], "unavailable")

    @unittest.skipUnless(importlib.util.find_spec("z1t"), "optional pinned Z1T environment required")
    def test_real_model_study_retains_all_runs_and_refuses_overwrite(self) -> None:
        from gibbsiq.qualification.adapters.z1t import NumericalZ1T

        numerical = NumericalZ1T()
        corpus = CorpusSplit("evaluation", (TokenDocument("one", "one", (0, 1, 2)),))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            report = run_study(numerical, corpus, output, operation_id="blocks.0.mlp.proj2")
            self.assertEqual(report["status"], "complete")
            self.assertEqual(len(report["runs"]), 24)
            self.assertEqual(len({run["randomization_digest"] for run in report["runs"]}), 24)
            self.assertEqual(report["decisions"]["controls"]["unchanged"]["outcome"], "pass")
            self.assertEqual(sum(run["replay_checked"] for run in report["runs"]), 3)
            self.assertEqual(
                json.loads((output / "results.json").read_text()), json.loads(json.dumps(report))
            )
            before = (output / "results.json").read_bytes()
            with self.assertRaises(FileExistsError):
                run_study(numerical, corpus, output, operation_id="blocks.0.mlp.proj2")
            self.assertEqual((output / "results.json").read_bytes(), before)

    @unittest.skipUnless(importlib.util.find_spec("z1t"), "optional pinned Z1T environment required")
    def test_timeout_records_resource_limit_without_fabricating_results(self) -> None:
        from gibbsiq.qualification.adapters.z1t import NumericalZ1T

        numerical = NumericalZ1T()
        corpus = CorpusSplit("evaluation", (TokenDocument("one", "one", (0, 1)),))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with self.assertRaises(TimeoutError):
                run_study(numerical, corpus, output, operation_id="blocks.0.mlp.proj2", timeout_seconds=0)
            report = json.loads((output / "results.json").read_text())
            self.assertEqual(report["status"], "resource_limited")
            self.assertEqual(report["runs"], [])


if __name__ == "__main__":
    unittest.main()
