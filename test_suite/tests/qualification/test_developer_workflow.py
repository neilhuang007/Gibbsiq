"""Planned S09 user-visible offline workflow tests; restore before implementation."""

from __future__ import annotations

import contextlib
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest


class DeveloperWorkflowTests(unittest.TestCase):
    def test_no_feasible_example_retains_failed_calibration_and_exports_no_policy(self):
        from gibbsiq.qualification.cli import main

        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "search"
            stdout = StringIO()
            with contextlib.redirect_stdout(stdout):
                status = main(
                    ("tune", "--example", "no-feasible-policy", "--output", str(destination), "--json")
                )
            self.assertEqual(status, 3)
            report = json.loads((destination / "search-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["lifecycle"], "no_feasible_policy")
            self.assertEqual(len(report["attempts"]), 3)
            self.assertTrue(all(attempt["phase"] == "calibration" for attempt in report["attempts"]))
            self.assertTrue(all(attempt["qualification"] == "fail" for attempt in report["attempts"]))
            self.assertFalse((destination / "policy.json").exists())
            machine = json.loads(stdout.getvalue())
            self.assertIn("no_feasible_policy", json.dumps(machine))


if __name__ == "__main__":
    unittest.main()
