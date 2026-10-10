"""End-to-end evidence tests owned by the coordinator, independent of backends."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json
import hashlib
import struct
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

import gibbsiq
from gibbsiq.qualification.artifacts import AttemptRecord, BundleWriter, inspect_bundle
from gibbsiq.qualification.contracts import (
    ArrayRef,
    MetricBinding,
    Observation,
    OperationSpec,
    PlannedRun,
    QualificationReport,
    ResourceBudget,
    RunPlan,
)
from gibbsiq.qualification.statistics import evaluate_metrics
from test_suite.tests.qualification.test_contracts import acceptance_contract, exact_metric, workload


def recovery_plan() -> RunPlan:
    spec = replace(
        workload(resources=ResourceBudget(8, 30, 1024 * 1024)),
        operations=(OperationSpec("activation", (), ()),),
    )
    return RunPlan(
        spec,
        (
            PlannedRun("run-1", "case-1", "activation", "evaluation", {"samples": 1}),
            PlannedRun("run-2", "case-1", "activation", "evaluation", {"samples": 1}),
        ),
    )


class WorkflowRecoveryTests(unittest.TestCase):
    def test_core_rejects_unsafe_npy_payloads_without_requiring_numpy(self) -> None:
        # These are format fixtures written directly as untrusted input. Their
        # contents, rather than NumPy's serializer, determine the expected errors.
        cases = (
            ("object", "|O", (), b"not-a-pickle", False),
            ("truncated", "<f8", (), b"\0" * 4, False),
            ("trailing", "<f8", (), b"\0" * 9, False),
            ("enormous", "<f8", (2**40,), b"", False),
            ("fortran", "<f8", (), b"\0" * 8, True),
        )
        for name, dtype, shape, body, fortran in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                axes = ("feature",) if shape else ()
                plan = recovery_plan()
                plan = replace(
                    plan,
                    workload=replace(plan.workload, operations=(OperationSpec("activation", shape, axes),)),
                )
                destination = Path(directory) / "evidence"
                writer = BundleWriter.create(destination, plan)
                header = (
                    repr({"descr": dtype, "fortran_order": fortran, "shape": shape}).encode("ascii") + b"\n"
                )
                payload = b"\x93NUMPY\x01\x00" + struct.pack("<H", len(header)) + header + body
                array_path = destination / "arrays" / "fixture.npy"
                array_path.parent.mkdir()
                array_path.write_bytes(payload)
                ref = ArrayRef(
                    "arrays/fixture.npy",
                    "sha256:" + hashlib.sha256(payload).hexdigest(),
                    len(payload),
                    "float64",
                    shape,
                    axes,
                )
                observation = Observation(
                    "mean", "activation", "case-1", "run-1", "float64", shape, axes, array=ref
                )
                attempt = AttemptRecord(
                    "run-1", "attempt-1", "complete", "sha256:" + "a" * 64, (observation,)
                )
                with self.assertRaises(ValueError):
                    writer.append_attempt(attempt)

    def test_unfinished_execution_retains_a_bad_result_and_resumes_without_replacing_it(self) -> None:
        plan = recovery_plan()
        observation = Observation("mean", "activation", "case-1", "run-1", "float64", (), (), (-0.5,))
        # A deliberately wrong mean is still a completed execution. Recovery must
        # not throw it away to give the candidate another chance to look good.
        attempt = AttemptRecord("run-1", "run-1-attempt-1", "complete", "sha256:" + "a" * 64, (observation,))
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "evidence"
            writer = BundleWriter.create(destination, plan)
            writer.append_attempt(attempt)
            snapshot = inspect_bundle(destination)
            self.assertEqual(snapshot.execution, "partial")
            self.assertEqual(snapshot.qualification, "inconclusive")
            self.assertEqual(snapshot.attempts[0].observations[0].values, (-0.5,))

            resumed = BundleWriter.resume(destination, plan)
            with self.assertRaises(ValueError):
                resumed.append_attempt(replace(attempt, attempt_id="favorable-retry"))
            with self.assertRaises(ValueError):
                resumed.finish(execution="complete")
            after = inspect_bundle(destination)
            self.assertEqual(after.attempts, (attempt,))
            self.assertNotEqual(after.qualification, "pass")

    def test_a_well_formed_report_cannot_substitute_a_favorable_unobserved_value(self) -> None:
        plan = recovery_plan()
        spec = replace(plan.workload, contract=acceptance_contract(exact_metric()))
        plan = RunPlan(
            spec,
            (plan.runs[0],),
            metric_bindings=(MetricBinding("exact-error", "mean", ("run-1",), reference_value=-0.5),),
        )
        observation = Observation("mean", "activation", "case-1", "run-1", "float64", (), (), (0.5,))
        attempt = AttemptRecord("run-1", "attempt-1", "complete", "sha256:" + "a" * 64, (observation,))
        # These metrics are internally valid, but their zero error was never
        # observed: the stored observation differs from the frozen reference by 1.
        report = QualificationReport(
            spec.semantic_digest(),
            spec.contract,
            "complete",
            "pass",
            evaluate_metrics(spec.contract, {"exact-error": (0.0,)}),
            ("run-1",),
            ("run-1",),
        )
        with tempfile.TemporaryDirectory() as directory:
            writer = BundleWriter.create(Path(directory) / "evidence", plan)
            writer.append_attempt(attempt)
            with self.assertRaises(ValueError):
                writer.finish(execution="complete", report=report)
            self.assertNotEqual(inspect_bundle(Path(directory) / "evidence").qualification, "pass")

    def test_killed_writer_is_inspectable_and_never_claims_complete_execution(self) -> None:
        program = textwrap.dedent(
            """
            import sys
            import time
            from pathlib import Path
            sys.path.insert(0, sys.argv[1])
            from gibbsiq.qualification.artifacts import AttemptRecord, BundleWriter
            from gibbsiq.qualification.contracts import Observation
            from test_suite.tests.qualification.test_workflow_recovery import recovery_plan

            destination, ready = map(Path, sys.argv[2:])
            writer = BundleWriter.create(destination, recovery_plan())
            observation = Observation('mean', 'activation', 'case-1', 'run-1',
                                      'float64', (), (), (-0.5,))
            writer.append_attempt(AttemptRecord('run-1', 'attempt-1', 'complete',
                                                'sha256:' + 'a' * 64, (observation,)))
            ready.write_text('journal flushed', encoding='utf-8')
            while True:
                time.sleep(1)
            """
        )
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "evidence"
            ready = Path(directory) / "ready"
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-S",
                    "-c",
                    program,
                    str(Path(gibbsiq.__file__).resolve().parent.parent),
                    str(destination),
                    str(ready),
                ]
            )
            try:
                deadline = time.monotonic() + 10
                while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(ready.exists(), "writer did not reach the interruption boundary")
            finally:
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=5)
            snapshot = inspect_bundle(destination)
            self.assertEqual((snapshot.execution, snapshot.qualification), ("partial", "inconclusive"))
            self.assertEqual(snapshot.attempts[0].observations[0].values, (-0.5,))
            resumed = BundleWriter.resume(destination, recovery_plan())
            resumed.finish(execution="cancelled")
            self.assertEqual(inspect_bundle(destination).execution, "cancelled")

    def test_isolated_inspection_reads_actual_evidence_with_optional_imports_and_network_blocked(
        self,
    ) -> None:
        program = textwrap.dedent(
            """
            import importlib.abc
            import json
            import socket
            import sys

            class BlockModels(importlib.abc.MetaPathFinder):
                def find_spec(self, fullname, path=None, target=None):
                    if fullname.partition('.')[0] in {'numpy', 'jax', 'equinox', 'torx', 'thrml', 'z1t'}:
                        raise RuntimeError('inspection attempted a model import')

            def no_network(*args, **kwargs):
                raise RuntimeError('inspection attempted network access')

            sys.meta_path.insert(0, BlockModels())
            socket.socket = no_network
            sys.path.insert(0, sys.argv[1])
            from gibbsiq.qualification.artifacts import inspect_bundle
            result = inspect_bundle(sys.argv[2], verify=True)
            print(json.dumps({'execution': result.execution,
                              'qualification': result.qualification,
                              'observed': result.attempts[0].observations[0].values}))
            """
        )
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "evidence"
            writer = BundleWriter.create(destination, recovery_plan())
            observation = Observation("mean", "activation", "case-1", "run-1", "float64", (), (), (-0.5,))
            writer.append_attempt(
                AttemptRecord("run-1", "attempt-1", "complete", "sha256:" + "a" * 64, (observation,))
            )
            writer.finish(execution="partial")
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    "-c",
                    program,
                    str(Path(__file__).resolve().parents[3] / "src"),
                    str(destination),
                ],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                json.loads(result.stdout),
                {"execution": "partial", "qualification": "inconclusive", "observed": [-0.5]},
            )


if __name__ == "__main__":
    unittest.main()
