"""Behavioral coverage for the second-workload portability rehearsal."""

from pathlib import Path
import tempfile
import unittest


class PortabilityRehearsalTests(unittest.TestCase):
    def test_named_candidate_change_preserves_costs_and_complements_only_bit_zero(self):
        from gibbsiq.qualification.adapters.torx import TorxCircuitBackend
        from gibbsiq.qualification.contracts import CostRecord, CostScope, Observation
        from gibbsiq.qualification.engine import ExecutionResult
        from tools.qualification.portability_rehearsal import ComplementedBitBackend

        scope = CostScope("test", ("sample_work",), ())
        costs = (CostRecord("sample_work", "samples", scope, "modeled", "available", 2.0),)
        observations = (
            Observation("bit0_mean", "op", "case", "run", "float64", (), (), (0.25,)),
            Observation("bit1_mean", "op", "case", "run", "float64", (), (), (0.75,)),
        )
        baseline = TorxCircuitBackend()
        baseline.execute = lambda run, randomization: ExecutionResult(observations, costs)
        backend = ComplementedBitBackend(baseline)

        result = backend.execute(None, None)

        self.assertEqual([item.values for item in result.observations], [(0.75,), (0.75,)])
        self.assertEqual(result.costs, costs)
        self.assertNotEqual(backend.capabilities().backend_id, baseline.capabilities().backend_id)

    def test_real_pinned_torx_rehearsal_detects_change(self):
        try:
            import jax  # noqa: F401
            import torx  # noqa: F401
        except ImportError:
            self.skipTest("pinned optional Torx stack is unavailable")
        from gibbsiq.qualification.artifacts import inspect_bundle
        from tools.qualification.portability_rehearsal import rehearse

        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "portability"
            summary = rehearse(destination, runs=128, samples=64)
            self.assertEqual(summary["baseline"]["qualification"], "pass")
            self.assertEqual(summary["changed_candidate"]["qualification"], "fail")
            self.assertEqual(summary["integration_effort"]["shared_contract_changes"], 0)
            self.assertEqual(inspect_bundle(destination / "changed-candidate").qualification, "fail")


if __name__ == "__main__":
    unittest.main()
