"""Behavioral tests for bounded, isolated qualification execution."""

from __future__ import annotations

from dataclasses import dataclass, replace
import multiprocessing
import os
from pathlib import Path
import random
import sys
import tempfile
import time
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from gibbsiq.qualification.artifacts import inspect_bundle  # noqa: E402
from gibbsiq.qualification.contracts import (  # noqa: E402
    Observation,
    OperationSpec,
    PlannedRun,
    ResourceBudget,
    RunPlan,
    parse_json,
)
from gibbsiq.qualification.engine import (  # noqa: E402
    BackendCapabilities,
    ExecutionResult,
    RandomizationIdentity,
    UnsupportedCapabilityError,
    execute_plan,
)
from test_suite.tests.qualification.test_contracts import workload  # noqa: E402


def small_plan(*, max_seconds: float = 10, max_jobs: int = 4) -> RunPlan:
    spec = replace(
        workload(resources=ResourceBudget(max_jobs, max_seconds, 1024 * 1024)),
        operations=(OperationSpec("activation", (), ()),),
    )
    return RunPlan(
        spec,
        (
            PlannedRun("run-1", "case-1", "activation", "evaluation", {"samples": 1}),
            PlannedRun("run-2", "case-2", "activation", "evaluation", {"samples": 1}),
        ),
    )


@dataclass
class FakeBackend:
    mode: str = "valid"
    marker: str | None = None

    def capabilities(self) -> BackendCapabilities:
        if self.mode == "blocked_capabilities":
            if self.marker is not None:
                Path(self.marker).write_text("entered capabilities", encoding="utf-8")
            multiprocessing.Event().wait()
        identity = "other-backend" if self.mode == "wrong_backend" else "candidate-backend"
        return BackendCapabilities(identity, ("samples",), ("mean",))

    def prepare(self, workload_spec: object) -> None:
        if self.marker is not None and self.mode != "blocked_second":
            Path(self.marker).write_text("prepared", encoding="utf-8")
        if self.mode == "blocked_prepare":
            multiprocessing.Event().wait()

    def execute(self, run: PlannedRun, randomization: RandomizationIdentity) -> ExecutionResult:
        if self.mode == "blocked_second" and run.run_id == "run-2":
            if self.marker is not None:
                Path(self.marker).write_text("entered run 2", encoding="utf-8")
            multiprocessing.Event().wait()
        if self.mode == "hard_exit_second" and run.run_id == "run-2":
            os._exit(7)
        if self.mode == "fail_second" and run.run_id == "run-2":
            raise RuntimeError("adapter failed after first result")
        run_id = "other" if self.mode == "wrong_run" else run.run_id
        axes = ("item",) if self.mode == "wrong_axes" else ()
        shape = (1,) if self.mode == "wrong_axes" else ()
        value = (
            random.Random(int(randomization.digest[7:], 16)).random() if self.mode == "stream_value" else 0.5
        )
        observation = Observation(
            "mean",
            run.operation_id,
            run.case_id,
            run_id,
            "float64",
            shape,
            axes,
            (value,),
        )
        return ExecutionResult((observation,), ())


class RunEngineTests(unittest.TestCase):
    def test_planned_execution_replays_same_stream_and_values(self) -> None:
        plan = small_plan()
        with tempfile.TemporaryDirectory() as temporary:
            destinations = [Path(temporary) / name for name in ("first", "again")]
            summaries = [
                execute_plan(plan, backend=FakeBackend("stream_value"), destination=path)
                for path in destinations
            ]
            self.assertEqual(tuple(summary.execution for summary in summaries), ("complete", "complete"))
            snapshots = [inspect_bundle(path) for path in destinations]
            self.assertEqual(
                tuple((attempt.run_id, attempt.observations) for attempt in snapshots[0].attempts),
                tuple((attempt.run_id, attempt.observations) for attempt in snapshots[1].attempts),
            )
            values = tuple(attempt.observations[0].values[0] for attempt in snapshots[0].attempts)
            self.assertNotEqual(values[0], values[1])
            environment = parse_json((destinations[0] / "environment.json").read_text(encoding="utf-8"))
            self.assertEqual(environment["backend"], plan.workload.candidate.identity)
            self.assertIn("python", environment)
            self.assertIn("platform", environment)
            self.assertIn("package", environment)

    def test_wrong_run_or_axes_cannot_complete(self) -> None:
        plan = small_plan()
        with tempfile.TemporaryDirectory() as temporary:
            for mode in ("wrong_run", "wrong_axes"):
                with self.subTest(mode=mode):
                    destination = Path(temporary) / mode
                    summary = execute_plan(plan, backend=FakeBackend(mode), destination=destination)
                    self.assertEqual(summary.execution, "error")
                    snapshot = inspect_bundle(destination)
                    self.assertFalse(any(attempt.execution == "complete" for attempt in snapshot.attempts))

    def test_prior_success_survives_backend_exception_and_resume_keeps_lineage(self) -> None:
        plan = small_plan()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bundle"
            failed = execute_plan(plan, backend=FakeBackend("fail_second"), destination=destination)
            self.assertEqual(failed.execution, "error")
            before = inspect_bundle(destination).attempts
            self.assertEqual(tuple(attempt.execution for attempt in before), ("complete", "error"))
            resumed = execute_plan(plan, backend=FakeBackend(), destination=destination, resume=True)
            self.assertEqual(resumed.execution, "complete")
            after = inspect_bundle(destination).attempts
            self.assertEqual(tuple(attempt.run_id for attempt in after), ("run-1", "run-2", "run-2"))
            self.assertEqual(after[2].retry_of, after[1].attempt_id)
            self.assertEqual(after[2].randomization, after[1].randomization)
            self.assertEqual(after[0], before[0])

    def _assert_blocked_phase_reaped(self, mode: str) -> None:
        # The deadline includes Windows spawn/import time. Give the child enough
        # startup time to reach the phase whose termination this test exercises.
        budget = 3.0
        plan = small_plan(max_seconds=budget)
        with tempfile.TemporaryDirectory() as temporary:
            marker = Path(temporary) / "entered-phase"
            destination = Path(temporary) / "bundle"
            prior = {process.pid for process in multiprocessing.active_children()}
            started = time.monotonic()
            summary = execute_plan(plan, backend=FakeBackend(mode, str(marker)), destination=destination)
            self.assertTrue(marker.exists(), f"child did not reach {mode} within its startup allowance")
            self.assertLess(time.monotonic() - started, budget + 2.0)
            self.assertEqual(summary.execution, "partial")
            self.assertTrue(all(process.pid in prior for process in multiprocessing.active_children()))
            snapshot = inspect_bundle(destination)
            self.assertEqual(snapshot.execution, "partial")
            self.assertEqual(snapshot.attempts, ())

    def test_preparation_deadline_terminates_child(self) -> None:
        self._assert_blocked_phase_reaped("blocked_prepare")

    def test_capability_deadline_is_part_of_total_budget(self) -> None:
        self._assert_blocked_phase_reaped("blocked_capabilities")

    def test_retained_storage_limit_is_partial_and_inspectable(self) -> None:
        plan = small_plan()
        plan = replace(plan, workload=replace(plan.workload, resources=ResourceBudget(4, 10, 7000)))
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bundle"
            summary = execute_plan(plan, backend=FakeBackend(), destination=destination)
            self.assertEqual(summary.execution, "partial")
            self.assertEqual(inspect_bundle(destination).attempts, ())

    def test_cancelled_plan_resumes_without_discarding_first_result(self) -> None:
        plan = small_plan()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bundle"

            def cancel_after_first() -> bool:
                return destination.exists() and len(inspect_bundle(destination).attempts) == 1

            stopped = execute_plan(
                plan, backend=FakeBackend(), destination=destination, cancel=cancel_after_first
            )
            self.assertEqual(stopped.execution, "cancelled")
            retained = inspect_bundle(destination).attempts
            self.assertEqual(tuple(attempt.run_id for attempt in retained), ("run-1",))
            resumed = execute_plan(plan, backend=FakeBackend(), destination=destination, resume=True)
            self.assertEqual(resumed.execution, "complete")
            attempts = inspect_bundle(destination).attempts
            self.assertEqual(attempts[0], retained[0])
            self.assertEqual(tuple(attempt.run_id for attempt in attempts), ("run-1", "run-2"))

    def test_cancelled_running_attempt_keeps_retry_lineage(self) -> None:
        plan = small_plan()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bundle"
            marker = Path(temporary) / "entered-run-2"
            stopped = execute_plan(
                plan,
                backend=FakeBackend("blocked_second", str(marker)),
                destination=destination,
                cancel=marker.exists,
            )
            self.assertTrue(marker.exists())
            self.assertEqual(stopped.execution, "cancelled")
            retained = inspect_bundle(destination).attempts
            self.assertEqual(tuple(item.execution for item in retained), ("complete", "cancelled"))
            resumed = execute_plan(plan, backend=FakeBackend(), destination=destination, resume=True)
            self.assertEqual(resumed.execution, "complete")
            attempts = inspect_bundle(destination).attempts
            self.assertEqual(attempts[2].retry_of, attempts[1].attempt_id)
            self.assertEqual(attempts[2].randomization, attempts[1].randomization)

    def test_hard_child_exit_keeps_preceding_success(self) -> None:
        plan = small_plan()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bundle"
            before = {process.pid for process in multiprocessing.active_children()}
            summary = execute_plan(plan, backend=FakeBackend("hard_exit_second"), destination=destination)
            self.assertEqual(summary.execution, "error")
            self.assertTrue(all(process.pid in before for process in multiprocessing.active_children()))
            self.assertEqual(
                tuple(attempt.execution for attempt in inspect_bundle(destination).attempts),
                ("complete", "error"),
            )

    def test_unsupported_control_rejected_before_preparation(self) -> None:
        plan = small_plan()
        unsupported = replace(plan, runs=(replace(plan.runs[0], settings={"warmup": 1}), plan.runs[1]))
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bundle"
            marker = Path(temporary) / "prepared"
            with self.assertRaises(UnsupportedCapabilityError):
                execute_plan(unsupported, backend=FakeBackend(marker=str(marker)), destination=destination)
            self.assertFalse(marker.exists())
            self.assertEqual(inspect_bundle(destination).attempts, ())

    def test_wrong_backend_identity_rejected_before_preparation(self) -> None:
        plan = small_plan()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bundle"
            marker = Path(temporary) / "prepared"
            with self.assertRaises(UnsupportedCapabilityError):
                execute_plan(plan, backend=FakeBackend("wrong_backend", str(marker)), destination=destination)
            self.assertFalse(marker.exists())
            self.assertEqual(inspect_bundle(destination).attempts, ())

    def test_attempt_ceiling_includes_prior_failed_attempt_on_resume(self) -> None:
        plan = small_plan(max_jobs=2)
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bundle"
            first = execute_plan(plan, backend=FakeBackend("fail_second"), destination=destination)
            self.assertEqual(first.execution, "error")
            resumed = execute_plan(plan, backend=FakeBackend(), destination=destination, resume=True)
            self.assertEqual(resumed.execution, "partial")
            self.assertEqual(len(inspect_bundle(destination).attempts), 2)


if __name__ == "__main__":
    unittest.main()
