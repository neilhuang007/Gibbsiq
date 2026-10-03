"""Trusted backend plan preflight runs in the supervised child before preparation."""

from pathlib import Path
import multiprocessing
import tempfile
import time
import unittest

from gibbsiq.qualification.artifacts import inspect_bundle
from gibbsiq.qualification.engine import UnsupportedCapabilityError, execute_plan
from test_suite.tests.qualification.test_run_engine import FakeBackend, small_plan


class PlanAwareBackend(FakeBackend):
    def validate_plan(self, plan):
        if self.mode == "unsupported":
            raise UnsupportedCapabilityError(
                "pinned backend source is required; install the integration recipe"
            )
        self._run_ids = {run.run_id for run in plan.runs}

    def prepare(self, workload):
        if not getattr(self, "_run_ids", None):
            raise RuntimeError("plan validation was omitted")
        super().prepare(workload)

    def execute(self, run, randomization):
        if run.run_id not in self._run_ids:
            raise RuntimeError("unplanned run reached backend")
        return super().execute(run, randomization)


class MissingDependencyBackend(FakeBackend):
    def capabilities(self):
        raise UnsupportedCapabilityError("optional backend is absent; install the pinned integration recipe")


class UnsupportedPrepareBackend(FakeBackend):
    def prepare(self, workload):
        raise UnsupportedCapabilityError(
            "preparation requires the pinned backend; install the integration recipe"
        )


class UnsupportedRunBackend(FakeBackend):
    def execute(self, run, randomization):
        if run.run_id == "run-2":
            raise UnsupportedCapabilityError("run setting is unsupported; install the integration recipe")
        return super().execute(run, randomization)


class BlockingPreflightBackend(FakeBackend):
    def validate_plan(self, plan):
        Path(self.marker).touch()
        multiprocessing.Event().wait()


class LongUnsupportedBackend(FakeBackend):
    def capabilities(self):
        raise UnsupportedCapabilityError("install the pinned integration recipe " + "x" * 500)


class FailingPreflightBackend(FakeBackend):
    def validate_plan(self, plan):
        raise RuntimeError("private adapter detail must remain in the child")


class BackendPreflightTests(unittest.TestCase):
    def test_preflight_sees_the_frozen_runs_before_preparation(self):
        with tempfile.TemporaryDirectory() as temporary:
            summary = execute_plan(
                small_plan(), backend=PlanAwareBackend(), destination=Path(temporary) / "run"
            )
            self.assertEqual(summary.execution, "complete", summary.reason)
            self.assertEqual(
                [attempt.observations[0].values for attempt in summary.attempts], [(0.5,), (0.5,)]
            )

    def test_unsupported_dependency_or_plan_retains_guidance_and_empty_evidence(self):
        for backend in (
            MissingDependencyBackend(),
            PlanAwareBackend(mode="unsupported"),
            UnsupportedPrepareBackend(),
        ):
            with self.subTest(backend=type(backend).__name__), tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary) / "run"
                with self.assertRaisesRegex(UnsupportedCapabilityError, "install.*integration recipe"):
                    execute_plan(small_plan(), backend=backend, destination=destination)
                snapshot = inspect_bundle(destination)
                self.assertEqual(snapshot.attempts, ())
                self.assertEqual(snapshot.execution, "partial")

    def test_unsupported_run_keeps_preceding_valid_attempt(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "run"
            with self.assertRaisesRegex(UnsupportedCapabilityError, "install.*integration recipe"):
                execute_plan(small_plan(), backend=UnsupportedRunBackend(), destination=destination)
            snapshot = inspect_bundle(destination)
            self.assertEqual([attempt.run_id for attempt in snapshot.attempts], ["run-1"])

    def test_blocked_preflight_is_terminated_within_deadline(self):
        with tempfile.TemporaryDirectory() as temporary:
            marker = Path(temporary) / "entered"
            destination = Path(temporary) / "run"
            before = {process.pid for process in multiprocessing.active_children()}
            started = time.monotonic()
            # Spawn/import time is part of the budget on Windows. Allow that
            # startup before testing termination of a preflight that never returns.
            budget = 3.0
            summary = execute_plan(
                small_plan(max_seconds=budget),
                backend=BlockingPreflightBackend(marker=str(marker)),
                destination=destination,
            )
            self.assertTrue(marker.exists(), "child did not reach preflight within its startup allowance")
            self.assertLess(time.monotonic() - started, budget + 2.0)
            self.assertEqual(summary.execution, "partial")
            self.assertEqual(inspect_bundle(destination).attempts, ())
            self.assertTrue(all(process.pid in before for process in multiprocessing.active_children()))

    def test_unsupported_guidance_is_bounded_and_ordinary_exception_is_sanitized(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(UnsupportedCapabilityError) as caught:
                execute_plan(
                    small_plan(),
                    backend=LongUnsupportedBackend(),
                    destination=Path(temporary) / "unsupported",
                )
            self.assertEqual(len(str(caught.exception)), 240)

            summary = execute_plan(
                small_plan(),
                backend=FailingPreflightBackend(),
                destination=Path(temporary) / "failed",
            )
            self.assertEqual(summary.execution, "error")
            self.assertIn("RuntimeError", summary.reason)
            self.assertNotIn("private adapter detail", summary.reason)


if __name__ == "__main__":
    unittest.main()
