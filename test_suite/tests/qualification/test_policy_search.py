"""Search must follow observed quality, actual objective and the frozen holdout."""

from pathlib import Path
import tempfile
import unittest

from gibbsiq.qualification.artifacts import inspect_bundle
from test_suite.tests.qualification.search_fixtures import global_only, search_plan, table_evaluator


class PolicySearchTests(unittest.TestCase):
    def test_enumeration_includes_baseline_and_deduplicates_effective_group_counts(self):
        from gibbsiq.qualification.policy_search import SearchSpace, enumerate_candidates

        candidates = enumerate_candidates(SearchSpace(counts=(8, 16), baseline=32, groups=("a", "b")))
        self.assertEqual([item.default_samples for item in candidates[:3]], [8, 16, 32])
        effective = [
            tuple(dict(item.group_samples).get(group, item.default_samples) for group in ("a", "b"))
            for item in candidates
        ]
        self.assertEqual(len(candidates), 9)
        self.assertEqual(len(set(effective)), 9)
        self.assertIn((8, 32), effective)
        self.assertIn((32, 8), effective)

    def test_nonmonotonic_quality_selects_cheapest_feasible_observed_policy(self):
        from gibbsiq.qualification.policy_search import run_search

        # More samples do not imply better quality: 16 fails while 8 and 32 pass.
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            result = run_search(
                search_plan(),
                evaluator=table_evaluator({(8,): 0.02, (16,): 0.4, (32,): 0.01}, calls=calls),
                destination=Path(directory) / "search",
            )
            self.assertEqual(result["selected"]["default_samples"], 8)
            self.assertEqual(result["lifecycle"], "qualified")
            self.assertEqual([c.default_samples for p, c, _, _ in calls if p == "calibration"], [8, 16, 32])
            final = [plan for phase, _, plan, _ in calls if phase == "evaluation"]
            self.assertEqual(len(final), 2)
            self.assertEqual([plan.workload.contract.alpha_total for plan in final], [0.025, 0.025])
            self.assertEqual(result["policy"]["objective"]["value"], 8)

    def test_group_reduction_is_rejected_when_scheduling_maximum_does_not_improve(self):
        from gibbsiq.qualification.policy_search import run_search

        values = {(8, 8): 0.4, (16, 16): 0.02, (8, 16): 0.01, (16, 8): 0.01}
        with tempfile.TemporaryDirectory() as directory:
            result = run_search(
                search_plan(groups=("a", "b"), counts=(8, 16), baseline=16, method="maximum"),
                evaluator=table_evaluator(values, method="maximum"),
                destination=Path(directory) / "search",
            )
            self.assertEqual(result["selected"], {"default_samples": 16, "group_samples": []})
            self.assertEqual(result["policy"]["objective"]["value"], 16)

    def test_calibration_overfit_fails_final_and_never_searches_holdout_for_a_replacement(self):
        from gibbsiq.qualification.policy_search import run_search

        calls = []
        values = {(8,): 0.01, (16,): 0.02, (32,): 0.02, ("evaluation", (8,)): 0.7}
        with tempfile.TemporaryDirectory() as directory:
            result = run_search(
                search_plan(),
                evaluator=table_evaluator(values, calls=calls),
                destination=Path(directory) / "search",
            )
            self.assertEqual(result["lifecycle"], "failed_validation")
            self.assertIsNone(result["policy"])
            finals = [
                (candidate.default_samples, inspect_bundle(path))
                for phase, candidate, _, path in calls
                if phase == "evaluation"
            ]
            self.assertEqual([count for count, _ in finals], [8, 32])
            self.assertEqual(finals[0][1].report.metrics[0].estimate, 0.7)
            self.assertEqual(finals[0][1].qualification, "fail")
            self.assertEqual(finals[1][1].qualification, "pass")

    def test_no_feasible_candidate_never_opens_development_or_final_inputs(self):
        from gibbsiq.qualification.policy_search import run_search

        calls = []
        with tempfile.TemporaryDirectory() as directory:
            result = run_search(
                search_plan(),
                evaluator=table_evaluator({}, calls=calls),
                destination=Path(directory) / "search",
            )
            self.assertEqual(result["lifecycle"], "no_feasible_policy")
            self.assertIsNone(result["selected"])
            self.assertIsNone(result["policy"])
            self.assertEqual([phase for phase, _, _, _ in calls], ["calibration"] * 3)

    def test_preflight_refuses_job_overrun_and_unsupported_group_controls(self):
        with self.assertRaises(ValueError):
            search_plan(max_jobs=2)
        with self.assertRaises(ValueError):
            global_only(search_plan(groups=("a",)))


if __name__ == "__main__":
    unittest.main()
