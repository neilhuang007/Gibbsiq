"""Run the TSP QUBO example as a subprocess and check its printed evidence."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

exampleScript = Path(__file__).resolve().parents[2] / "examples" / "tsp_qubo_ground_state.py"


class TspExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.completed = subprocess.run(
            [sys.executable, str(exampleScript)],
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_exits_cleanly(self) -> None:
        self.assertEqual(self.completed.returncode, 0, self.completed.stderr)

    def test_reports_optimal_length(self) -> None:
        self.assertIn("exact tour length  : 18", self.completed.stdout)
        self.assertIn("best sampled length: 18.0", self.completed.stdout)

    def test_reports_penalty_certificate(self) -> None:
        self.assertIn("penalty status     : proved_adequate", self.completed.stdout)


if __name__ == "__main__":
    unittest.main()
