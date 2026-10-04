"""Decision behavior of the bounded, fixed-input checkpoint experiment."""

from __future__ import annotations

import math
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from gibbsiq.qualification.model_evaluation import CorpusSplit, TokenDocument, language_loss
from tools.qualification.verify_trained_checkpoint import (
    POLICY_OPERATIONS,
    _policy_plan,
    assess_policy_study,
    assess_study,
    run_policy_study,
    run_study,
)


class TrainedCheckpointStudyTests(unittest.TestCase):
    def test_equal_work_policy_decisions_keep_whole_runs_as_units(self) -> None:
        reference = language_loss([[0.0, 0.0]], [0], cap=16.0)
        report = assess_policy_study(reference, [reference] * 32, [reference] * 32)
        self.assertEqual(report["heterogeneous_vs_numerical"]["observed_units"], 32)
        self.assertEqual(report["heterogeneous_vs_numerical"]["outcome"], "inconclusive")
        self.assertEqual(report["heterogeneous_vs_uniform"]["outcome"], "inconclusive")
        self.assertGreater(report["required_runs"]["paired_half_width_0_25"], 10000)

    def test_policy_preflight_matches_work_and_rejects_excess(self) -> None:
        def model(width: int) -> SimpleNamespace:
            return SimpleNamespace(
                operations=tuple(
                    SimpleNamespace(
                        operation_id=name,
                        kind="tanh_sparse_linear",
                        output_features=width,
                    )
                    for name in POLICY_OPERATIONS
                )
            )

        corpus = CorpusSplit("evaluation", (TokenDocument("one", "one", (0, 1, 2, 3, 4)),))
        plan = _policy_plan(model(768), corpus)
        self.assertEqual(plan["modeled_spin_work_per_forward"], 4 * 768 * 136)
        self.assertEqual(plan["modeled_spin_work_per_corpus"], 4 * 768 * 136)
        self.assertEqual(plan["max_field_elements_per_operation"], 4 * 768)
        with self.assertRaisesRegex(ValueError, "spin-work cap"):
            _policy_plan(model(16000), corpus)
        with self.assertRaisesRegex(ValueError, "field-element cap"):
            _policy_plan(model(17000), corpus)

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
    def test_real_model_policy_study_records_cost_boundaries(self) -> None:
        from gibbsiq.qualification.adapters.z1t import NumericalZ1T, TinyZ1TConfig

        numerical = NumericalZ1T(TinyZ1TConfig(n_layers=4))
        corpus = CorpusSplit("evaluation", (TokenDocument("one", "one", (0, 1, 2)),))
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch("tools.qualification.verify_trained_checkpoint.POLICY_RUNS", 2),
        ):
            report = run_policy_study(numerical, corpus, Path(directory))
        self.assertEqual(report["status"], "complete")
        self.assertEqual(len(report["runs"]), 4)
        self.assertEqual(
            {row["execution_order"] for row in report["runs"] if row["policy"] == "heterogeneous"},
            {0, 1},
        )
        self.assertIn("observer_overhead", report)
        self.assertTrue(all("forward_and_transfer_seconds" in row for row in report["runs"]))

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
