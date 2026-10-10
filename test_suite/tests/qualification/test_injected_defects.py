"""Behavioral defect probes against the frozen two-state reference."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from gibbsiq.qualification.adapters.reference import spin_conditional  # noqa: E402
from gibbsiq.qualification.adapters.spin import SpinConditionalBackend  # noqa: E402
from gibbsiq.qualification.artifacts import inspect_bundle  # noqa: E402
from gibbsiq.qualification.engine import ExecutionResult, RandomizationIdentity  # noqa: E402
from gibbsiq.qualification.examples import SPIN_CANDIDATES, SPIN_FIELD, spin_conditional_plan  # noqa: E402
from gibbsiq.qualification.workflow import qualify  # noqa: E402


class ScalingDefect(SpinConditionalBackend):
    def execute(self, run, randomization):
        result = super().execute(run, randomization)
        return ExecutionResult((replace(result.observations[0], values=(2.0,)),), result.costs)


class CastDefect(SpinConditionalBackend):
    def execute(self, run, randomization):
        result = super().execute(run, randomization)
        return ExecutionResult((replace(result.observations[0], values=(1.0,)),), result.costs)


class AxesDefect(SpinConditionalBackend):
    def execute(self, run, randomization):
        result = super().execute(run, randomization)
        return ExecutionResult((replace(result.observations[0], shape=(1,), axes=("batch",)),), result.costs)


class RepeatedKeyDefect(SpinConditionalBackend):
    def execute(self, run, randomization):
        repeated = RandomizationIdentity("sha256:" + "0" * 64, (0,) * 8)
        return super().execute(run, repeated)


class InjectedDefectTests(unittest.TestCase):
    def test_exponential_reference_is_half_and_sign_reversal_confidently_fails(self) -> None:
        reference = spin_conditional(SPIN_FIELD)
        self.assertAlmostEqual(reference.mean, 0.5, places=14)
        plan = spin_conditional_plan(runs=256, candidate="sign-reversed")
        with tempfile.TemporaryDirectory() as temporary:
            report = qualify(
                plan,
                backends={SPIN_CANDIDATES["sign-reversed"]: SpinConditionalBackend("sign-reversed")},
                destination=Path(temporary) / "sign",
            )
            self.assertEqual(report.qualification, "fail")
            self.assertLess(
                report.metrics[0].interval.upper, plan.workload.contract.metrics[0].acceptance.lower
            )

    def test_scaling_out_of_declared_range_is_invalid_and_raw_attempts_survive(self) -> None:
        plan = spin_conditional_plan(runs=4)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "scale"
            report = qualify(plan, backends={SPIN_CANDIDATES["iid"]: ScalingDefect()}, destination=path)
            self.assertEqual((report.execution, report.qualification), ("complete", "invalid"))
            self.assertEqual(report.metrics[0].availability, "unavailable")
            self.assertEqual(len(inspect_bundle(path).attempts), 4)

    def test_float_cast_to_positive_spin_is_detected_as_bias(self) -> None:
        plan = spin_conditional_plan(runs=256)
        with tempfile.TemporaryDirectory() as temporary:
            report = qualify(
                plan, backends={SPIN_CANDIDATES["iid"]: CastDefect()}, destination=Path(temporary) / "cast"
            )
            self.assertEqual(report.qualification, "fail")
            self.assertGreater(report.metrics[0].interval.lower, 0.125)

    def test_wrong_axes_cannot_be_reported_as_complete(self) -> None:
        plan = spin_conditional_plan(runs=4)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "axes"
            report = qualify(plan, backends={SPIN_CANDIDATES["iid"]: AxesDefect()}, destination=path)
            self.assertEqual(report.execution, "error")
            self.assertNotEqual(report.qualification, "pass")
            self.assertFalse(
                any(attempt.execution == "complete" for attempt in inspect_bundle(path).attempts)
            )

    def test_repeated_key_is_visible_as_lost_run_diversity(self) -> None:
        plan = spin_conditional_plan(runs=32)
        with tempfile.TemporaryDirectory() as temporary:
            paths = [Path(temporary) / name for name in ("healthy", "repeated")]
            qualify(plan, backends={SPIN_CANDIDATES["iid"]: SpinConditionalBackend()}, destination=paths[0])
            qualify(plan, backends={SPIN_CANDIDATES["iid"]: RepeatedKeyDefect()}, destination=paths[1])
            trajectories = [
                tuple(attempt.observations[0].values[0] for attempt in inspect_bundle(path).attempts)
                for path in paths
            ]
            self.assertGreater(len(set(trajectories[0])), 1)
            self.assertEqual(len(set(trajectories[1])), 1)


if __name__ == "__main__":
    unittest.main()
