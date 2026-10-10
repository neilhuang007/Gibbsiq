"""Negative search outcomes retain their scientific meaning."""

from pathlib import Path
import tempfile
import unittest

from test_suite.tests.qualification.search_fixtures import search_plan, table_evaluator


class SearchNegativeOutcomeTests(unittest.TestCase):
    def test_deadline_overrun_retains_completed_callback_evidence(self):
        from gibbsiq.qualification.policy_search import run_search

        now = [0.0]

        def clock():
            return now[0]

        ordinary = table_evaluator({(8,): 0.01})

        def overrun(candidate, phase, run_plan, destination):
            ordinary(candidate, phase, run_plan, destination)
            now[0] = 100.0

        with tempfile.TemporaryDirectory() as directory:
            result = run_search(
                search_plan(), evaluator=overrun, destination=Path(directory) / "search", clock=clock
            )
        self.assertEqual(result["lifecycle"], "budget_exhausted")
        self.assertEqual(len(result["attempts"]), 1)
        self.assertEqual(result["attempts"][0]["execution"], "complete")

    def test_frozen_final_plan_is_the_exact_callback_plan(self):
        from gibbsiq.qualification.artifacts import plan_from_dict, record_to_dict
        from gibbsiq.qualification.contracts import parse_json
        from gibbsiq.qualification.policy_search import run_search

        calls = []
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "search"
            run_search(
                search_plan(),
                evaluator=table_evaluator({(8,): 0.01, (16,): 0.2, (32,): 0.02}, calls=calls),
                destination=destination,
            )
            frozen = parse_json((destination / "frozen-evaluation-plans.json").read_text(encoding="utf-8"))
        callback_plans = [record_to_dict(plan) for phase, _, plan, _ in calls if phase == "evaluation"]
        self.assertEqual(callback_plans, [record_to_dict(plan_from_dict(item)) for item in frozen])

    def test_missing_objective_is_not_screening_eligible(self):
        from gibbsiq.qualification.policy_search import run_search

        with tempfile.TemporaryDirectory() as directory:
            result = run_search(
                search_plan(),
                evaluator=table_evaluator({(8,): 0.01, (16,): 0.01, (32,): 0.01}, missing_cost=True),
                destination=Path(directory) / "search",
            )
        self.assertEqual(result["lifecycle"], "no_feasible_policy")
        self.assertIsNone(result["selected"])
        self.assertTrue(all(not item["screening_eligible"] for item in result["attempts"]))

    def test_final_fail_is_retained_even_when_baseline_passes(self):
        from gibbsiq.qualification.policy_search import inspect_search, run_search

        values = {(8,): 0.01, (16,): 0.02, (32,): 0.02, ("evaluation", (8,)): 0.9}
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "search"
            result = run_search(search_plan(), evaluator=table_evaluator(values), destination=destination)
            inspected = inspect_search(destination)
        self.assertEqual(result["lifecycle"], "failed_validation")
        self.assertEqual(inspected["final"]["selected"]["qualification"], "fail")
        self.assertEqual(inspected["final"]["baseline"]["qualification"], "pass")
        self.assertIsNone(inspected["policy"])

    def test_search_decoder_rejects_a_rewritten_final_status(self):
        import json

        from gibbsiq.qualification.policy_search import inspect_search, run_search

        values = {(8,): 0.01, (16,): 0.02, (32,): 0.02, ("evaluation", (8,)): 0.9}
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "search"
            run_search(search_plan(), evaluator=table_evaluator(values), destination=destination)
            report = destination / "search-report.json"
            payload = json.loads(report.read_text(encoding="utf-8"))
            payload["final"]["selected"]["qualification"] = "pass"
            report.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                inspect_search(destination)


if __name__ == "__main__":
    unittest.main()
