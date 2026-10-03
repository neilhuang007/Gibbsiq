"""Offline examples exercise complete negative experiments with numerical evidence."""

import math
from pathlib import Path
import tempfile
import unittest

from gibbsiq.qualification.artifacts import inspect_bundle


class OfflineExampleTests(unittest.TestCase):
    def test_more_samples_cannot_fix_the_analytic_sign_error(self):
        from gibbsiq.qualification.adapters.analytic_search import tune_no_feasible_policy

        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "search"
            result = tune_no_feasible_policy(destination=destination)
            self.assertEqual(result["lifecycle"], "no_feasible_policy")
            self.assertIsNone(result["policy"])
            self.assertEqual(len(result["attempts"]), 3)
            for attempt in result["attempts"]:
                snapshot = inspect_bundle(destination / attempt["bundle"])
                self.assertEqual(snapshot.plan.workload.inputs.cases[0].split, "calibration")
                self.assertAlmostEqual(snapshot.report.metrics[0].estimate, 2 * math.tanh(0.25))
                self.assertEqual(snapshot.report.metrics[0].outcome, "fail")
                self.assertEqual(
                    snapshot.attempts[0].costs[0].value, snapshot.plan.runs[0].settings["samples"]
                )


if __name__ == "__main__":
    unittest.main()
