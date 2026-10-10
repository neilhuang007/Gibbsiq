"""Public CPU qualification command behavior."""

from __future__ import annotations

import contextlib
from dataclasses import replace
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))


class QualificationCliTests(unittest.TestCase):
    def test_tiny_frozen_example_persists_an_inconclusive_report(self) -> None:
        from gibbsiq.qualification.artifacts import inspect_bundle
        from gibbsiq.qualification.cli import main

        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "evidence"
            stdout = StringIO()
            with contextlib.redirect_stdout(stdout):
                status = main(
                    (
                        "qualify",
                        "--example",
                        "spin-conditional",
                        "--output",
                        str(destination),
                        "--runs",
                        "16",
                        "--samples",
                        "32",
                    )
                )
            self.assertEqual(status, 3)
            snapshot = inspect_bundle(destination)
            self.assertEqual(snapshot.execution, "complete")
            self.assertEqual(snapshot.qualification, "inconclusive")
            self.assertEqual(len(snapshot.attempts), 16)
            self.assertTrue(all(attempt.execution == "complete" for attempt in snapshot.attempts))
            self.assertIn("0.5", stdout.getvalue())
            persisted = destination.joinpath("report.md").read_text(encoding="utf-8")
            self.assertEqual(persisted, stdout.getvalue())
            self.assertIn("16/16", persisted)
            self.assertIn("[-0.125, 0.125]", persisted)

    def test_default_pass_and_named_sign_reversal_fail_with_distinct_codes(self) -> None:
        from gibbsiq.qualification.artifacts import inspect_bundle
        from gibbsiq.qualification.cli import main

        with tempfile.TemporaryDirectory() as temporary:
            passing = Path(temporary) / "pass"
            failing = Path(temporary) / "fail"
            with contextlib.redirect_stdout(StringIO()):
                pass_code = main(("qualify", "--example", "spin-conditional", "--output", str(passing)))
                fail_code = main(
                    (
                        "qualify",
                        "--example",
                        "spin-conditional",
                        "--output",
                        str(failing),
                        "--runs",
                        "256",
                        "--candidate",
                        "sign-reversed",
                    )
                )
            self.assertEqual((pass_code, fail_code), (0, 1))
            self.assertEqual(inspect_bundle(passing).qualification, "pass")
            failed = inspect_bundle(failing)
            self.assertEqual(failed.qualification, "fail")
            self.assertLess(failed.report.metrics[0].interval.upper, -0.125)
            inspect_output = StringIO()
            with contextlib.redirect_stdout(inspect_output):
                self.assertEqual(main(("inspect", str(failing), "--verify", "--json")), 0)
            self.assertEqual(json.loads(inspect_output.getvalue())["qualification"], "fail")

    def test_replay_preserves_core_observations_with_diverse_run_trajectories(self) -> None:
        from gibbsiq.qualification.artifacts import inspect_bundle
        from gibbsiq.qualification.cli import main

        with tempfile.TemporaryDirectory() as temporary:
            paths = (Path(temporary) / "first", Path(temporary) / "again")
            with contextlib.redirect_stdout(StringIO()):
                for path in paths:
                    self.assertEqual(
                        main(
                            (
                                "qualify",
                                "--example",
                                "spin-conditional",
                                "--output",
                                str(path),
                                "--runs",
                                "32",
                                "--samples",
                                "32",
                            )
                        ),
                        3,
                    )
            snapshots = tuple(inspect_bundle(path) for path in paths)
            observed = [
                tuple(attempt.observations[0].values for attempt in snapshot.attempts)
                for snapshot in snapshots
            ]
            self.assertEqual(observed[0], observed[1])
            self.assertGreater(len(set(observed[0])), 1)
            self.assertEqual(
                tuple(attempt.randomization for attempt in snapshots[0].attempts),
                tuple(attempt.randomization for attempt in snapshots[1].attempts),
            )

    def test_spec_is_static_and_recipe_options_are_rejected(self) -> None:
        from gibbsiq.qualification.artifacts import record_to_dict
        from gibbsiq.qualification.cli import main
        from gibbsiq.qualification.contracts import canonical_json
        from gibbsiq.qualification.examples import spin_conditional_plan

        with tempfile.TemporaryDirectory() as temporary:
            plan = spin_conditional_plan(runs=16)
            spec = Path(temporary) / "plan.json"
            spec.write_bytes(canonical_json(record_to_dict(plan)))
            destination = Path(temporary) / "from-spec"
            with contextlib.redirect_stdout(StringIO()):
                self.assertEqual(main(("qualify", "--spec", str(spec), "--output", str(destination))), 3)
            self.assertTrue(destination.joinpath("manifest.json").exists())
            with contextlib.redirect_stderr(StringIO()):
                self.assertEqual(
                    main(
                        (
                            "qualify",
                            "--spec",
                            str(spec),
                            "--output",
                            str(Path(temporary) / "bad"),
                            "--runs",
                            "16",
                        )
                    ),
                    2,
                )

    def test_spec_with_false_model_identity_cannot_run_builtin_profile(self) -> None:
        from gibbsiq.qualification.artifacts import inspect_bundle, record_to_dict
        from gibbsiq.qualification.cli import main
        from gibbsiq.qualification.contracts import canonical_json
        from gibbsiq.qualification.examples import spin_conditional_plan

        with tempfile.TemporaryDirectory() as temporary:
            payload = record_to_dict(spin_conditional_plan(runs=1))
            payload["workload"]["model_config"]["digest"] = "sha256:" + "0" * 64
            spec = Path(temporary) / "false-model.json"
            spec.write_bytes(canonical_json(payload))
            destination = Path(temporary) / "evidence"
            with contextlib.redirect_stdout(StringIO()):
                self.assertEqual(main(("qualify", "--spec", str(spec), "--output", str(destination))), 5)
            snapshot = inspect_bundle(destination)
            self.assertEqual(snapshot.execution, "error")
            self.assertNotEqual(snapshot.qualification, "pass")

    def test_strict_inspection_without_numpy_reports_unavailable_payload(self) -> None:
        if importlib.util.find_spec("numpy") is None:
            self.skipTest("NumPy optional extra is not installed")
        import numpy as np

        from gibbsiq.qualification.artifacts import AttemptRecord, BundleWriter
        from gibbsiq.qualification.contracts import (
            AcceptanceContract,
            MetricBinding,
            Observation,
            PlannedRun,
            QualificationReport,
            RunPlan,
        )
        from gibbsiq.qualification.statistics import evaluate_metrics
        from test_suite.tests.qualification.test_artifacts import STREAM, small_plan
        from test_suite.tests.qualification.test_contracts import exact_metric

        base = small_plan()
        workload = replace(base.workload, contract=AcceptanceContract((exact_metric(),)))
        plan = RunPlan(
            workload,
            (PlannedRun("run-1", "case-1", "activation", "evaluation", {}),),
            metric_bindings=(MetricBinding("exact-error", "mean", ("run-1",)),),
        )
        report = QualificationReport(
            workload.semantic_digest(),
            workload.contract,
            "complete",
            "pass",
            evaluate_metrics(workload.contract, {"exact-error": (-0.5,)}),
            ("run-1",),
            ("run-1",),
        )
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "array-evidence"
            writer = BundleWriter.create(destination, plan)
            array = writer.add_array("arrays/diagnostic.npy", np.array(-0.5, dtype=np.float64), axes=())
            observations = (
                Observation("mean", "activation", "case-1", "run-1", "float64", (), (), (-0.5,)),
                Observation("diagnostic", "activation", "case-1", "run-1", "float64", (), (), array=array),
            )
            writer.append_attempt(AttemptRecord("run-1", "attempt-1", "complete", STREAM, observations))
            writer.finish(execution="complete", report=report)
            environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
            command = [
                sys.executable,
                "-S",
                "-m",
                "gibbsiq.qualification",
                "inspect",
                str(destination),
                "--verify",
                "--json",
            ]
            inspected = subprocess.run(
                command, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=15, check=False
            )
            self.assertEqual(inspected.returncode, 4, inspected.stderr)
            payload = json.loads(inspected.stdout)
            self.assertEqual(payload["payload_validation"], "unavailable")
            self.assertEqual(payload["qualification"], "unsupported")
            self.assertEqual(payload["report"]["qualification"], "pass")
            command.pop()
            human = subprocess.run(
                command, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=15, check=False
            )
            self.assertEqual(human.returncode, 4, human.stderr)
            self.assertIn("Qualification: pass", human.stdout)
            self.assertIn("Payload validation: unavailable", human.stdout)


if __name__ == "__main__":
    unittest.main()
