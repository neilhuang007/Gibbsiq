"""Behavioral tests for schema-1 evidence bundles."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from gibbsiq.qualification.artifacts import (
    AttemptRecord,
    BundleWriter,
    bound_metric_values,
    inspect_bundle,
    plan_from_dict,
    record_to_dict,
)
from gibbsiq.qualification.contracts import (
    AcceptanceContract,
    MetricBinding,
    Observation,
    OperationSpec,
    PlannedRun,
    ResourceBudget,
    RunPlan,
    QualificationReport,
)
from gibbsiq.qualification.statistics import evaluate_metrics
from test_suite.tests.qualification.test_contracts import exact_metric, workload


STREAM = "sha256:" + "a" * 64


def small_plan() -> RunPlan:
    spec = replace(
        workload(resources=ResourceBudget(4, 30, 1024 * 1024)),
        operations=(OperationSpec("activation", (), ()),),
    )
    return RunPlan(
        spec,
        (
            PlannedRun("run-1", "case-1", "activation", "evaluation", {"samples": 1}),
            PlannedRun("run-2", "case-2", "activation", "evaluation", {"samples": 1}),
        ),
    )


def observed_attempt() -> AttemptRecord:
    observation = Observation("mean", "activation", "case-1", "run-1", "float64", (), (), (-0.5,))
    return AttemptRecord("run-1", "attempt-1", "complete", STREAM, (observation,))


class BundleTests(unittest.TestCase):
    def test_unfinished_bundle_preserves_completed_observation_across_resume(self) -> None:
        plan = small_plan()
        attempt = observed_attempt()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bundle"
            writer = BundleWriter.create(destination, plan)
            writer.append_attempt(attempt)

            snapshot = inspect_bundle(destination)
            self.assertEqual(snapshot.plan, plan)
            self.assertEqual(snapshot.attempts, (attempt,))
            self.assertEqual(snapshot.execution, "partial")
            self.assertEqual(snapshot.qualification, "inconclusive")

            resumed = BundleWriter.resume(destination, plan)
            with self.assertRaises(ValueError):
                resumed.append_attempt(replace(attempt, attempt_id="cherry-picked-retry"))
            self.assertEqual(inspect_bundle(destination).attempts, (attempt,))

    def test_complete_bundle_is_immutable_and_payload_corruption_is_rejected(self) -> None:
        plan = small_plan()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bundle"
            writer = BundleWriter.create(destination, plan)
            writer.append_attempt(observed_attempt())
            writer.append_attempt(AttemptRecord("run-2", "attempt-2", "complete", STREAM))
            snapshot = writer.finish(execution="complete")
            self.assertEqual(snapshot.execution, "complete")
            self.assertEqual(snapshot.qualification, "inconclusive")
            with self.assertRaises(ValueError):
                BundleWriter.resume(destination, plan)
            with self.assertRaises(ValueError):
                writer.append_attempt(AttemptRecord("run-2", "attempt-3", "complete", STREAM))

            journal = destination / "runs.jsonl"
            journal.write_bytes(journal.read_bytes().replace(b"-0.5", b"-0.4"))
            with self.assertRaises(ValueError):
                inspect_bundle(destination)

    def test_torn_journal_and_future_schema_are_rejected(self) -> None:
        plan = small_plan()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bundle"
            writer = BundleWriter.create(destination, plan)
            writer.append_attempt(observed_attempt())
            journal = destination / "runs.jsonl"
            journal.write_bytes(journal.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError, "torn"):
                inspect_bundle(destination)
            with self.assertRaises(ValueError):
                BundleWriter.resume(destination, plan)

        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bundle"
            BundleWriter.create(destination, plan)
            plan_path = destination / "plan.json"
            payload = json.loads(plan_path.read_text(encoding="utf-8"))
            payload["schema_version"] = 2
            plan_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "schema_version"):
                inspect_bundle(destination)

    def test_interrupted_finish_discards_stale_summaries_on_resume(self) -> None:
        plan = small_plan()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bundle"
            writer = BundleWriter.create(destination, plan)
            writer.append_attempt(observed_attempt())
            # Crash after these final summaries, before the final marker.
            (destination / "metrics.json").write_text("{}", encoding="utf-8")
            (destination / "costs.json").write_text("[]", encoding="utf-8")
            (destination / "report.md").write_text("stale", encoding="utf-8")
            resumed = BundleWriter.resume(destination, plan)
            for name in ("metrics.json", "costs.json", "report.md"):
                self.assertFalse((destination / name).exists())
            resumed.append_attempt(AttemptRecord("run-2", "attempt-2", "complete", STREAM))
            snapshot = resumed.finish(execution="complete")
            self.assertIsNone(snapshot.report)
            self.assertEqual(snapshot.attempts[0].observations[0].values, (-0.5,))

    def test_malformed_json_and_unknown_manifest_fields_are_rejected(self) -> None:
        plan = small_plan()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bundle"
            BundleWriter.create(destination, plan)
            plan_path = destination / "plan.json"
            original = plan_path.read_bytes()
            malformed = (
                b'{"schema_version":1,' + original[1:],
                b"[]",
                original.replace(b'"schema_version":1', b'"schema_version":NaN', 1),
            )
            for payload in malformed:
                with self.subTest(payload=payload[:30]):
                    plan_path.write_bytes(payload)
                    with self.assertRaises(ValueError):
                        inspect_bundle(destination)
            plan_path.write_bytes(original)
            with self.assertRaises(ValueError):
                inspect_bundle(destination, verify="yes")

            writer = BundleWriter.resume(destination, plan)
            writer.append_attempt(observed_attempt())
            writer.append_attempt(AttemptRecord("run-2", "attempt-2", "complete", STREAM))
            writer.finish(execution="complete")
            manifest = destination / "manifest.json"
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["python_module"] = "untrusted.evidence.code"
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                inspect_bundle(destination)

    def test_duplicate_run_ids_and_malformed_nested_lists_reject_at_codec(self) -> None:
        plan = small_plan()
        payload = record_to_dict(plan)
        payload["runs"].append(payload["runs"][0])
        with self.assertRaisesRegex(ValueError, "run IDs"):
            plan_from_dict(payload)
        payload["runs"] = None
        with self.assertRaises(ValueError):
            plan_from_dict(payload)
        payload["runs"] = []
        payload["workload"]["inputs"]["cases"] = None
        with self.assertRaises(ValueError):
            plan_from_dict(payload)

    def test_missing_runs_and_unsafe_links_are_rejected(self) -> None:
        plan = small_plan()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bundle"
            writer = BundleWriter.create(destination, plan)
            writer.append_attempt(observed_attempt())
            with self.assertRaisesRegex(ValueError, "every planned run"):
                writer.finish(execution="complete")
            outside = Path(temporary) / "outside"
            outside.mkdir()
            link = destination / "arrays"
            try:
                os.symlink(outside, link, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlink creation unavailable on this platform")
            with self.assertRaises(ValueError):
                inspect_bundle(destination)

    def test_terminal_error_resume_retains_failed_attempt_and_lineage(self) -> None:
        plan = small_plan()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bundle"
            writer = BundleWriter.create(destination, plan)
            failure = AttemptRecord("run-1", "attempt-1", "error", STREAM, reason="worker stopped")
            writer.append_attempt(failure)
            self.assertEqual(writer.finish(execution="error").execution, "error")
            resumed = BundleWriter.resume(destination, plan)
            resumed.append_attempt(replace(observed_attempt(), attempt_id="attempt-2", retry_of="attempt-1"))
            resumed.append_attempt(AttemptRecord("run-2", "attempt-3", "complete", STREAM))
            snapshot = resumed.finish(execution="complete")
            self.assertEqual(snapshot.attempts[0], failure)
            self.assertEqual(snapshot.attempts[1].retry_of, "attempt-1")
            history = json.loads((destination / "history.json").read_text(encoding="utf-8"))
            self.assertEqual(history[0]["execution"], "error")

    def test_absolute_array_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            writer = BundleWriter.create(Path(temporary) / "bundle", small_plan())
            with self.assertRaises(ValueError):
                writer.add_array("C:/private/array.npy", object(), axes=())
            with self.assertRaises(ValueError):
                writer.add_array("/private/array.npy", object(), axes=())

    def test_bound_report_must_match_retained_scalar_observation(self) -> None:
        spec = replace(small_plan().workload, contract=AcceptanceContract((exact_metric(),)))
        plan = RunPlan(
            spec,
            (PlannedRun("run-1", "case-1", "activation", "evaluation", {}),),
            metric_bindings=(MetricBinding("exact-error", "mean", ("run-1",)),),
        )
        attempt = observed_attempt()
        actual = bound_metric_values(plan, (attempt,))
        self.assertEqual(actual, {"exact-error": (-0.5,)})
        report = QualificationReport(
            workload_digest=spec.semantic_digest(),
            contract=spec.contract,
            execution="complete",
            qualification="pass",
            metrics=evaluate_metrics(spec.contract, actual),
            expected_run_ids=("run-1",),
            completed_run_ids=("run-1",),
        )
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bundle"
            writer = BundleWriter.create(destination, plan)
            writer.append_attempt(attempt)
            self.assertEqual(writer.finish(execution="complete", report=report).qualification, "pass")

        forged = replace(report, metrics=evaluate_metrics(spec.contract, {"exact-error": (0.0,)}))
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bundle"
            writer = BundleWriter.create(destination, plan)
            writer.append_attempt(attempt)
            with self.assertRaisesRegex(ValueError, "bound observations"):
                writer.finish(execution="complete", report=forged)

    def test_array_path_and_npy_structure_are_checked_before_retention(self) -> None:
        plan = small_plan()
        with tempfile.TemporaryDirectory() as temporary:
            writer = BundleWriter.create(Path(temporary) / "bundle", plan)
            with self.assertRaises(ValueError):
                writer.add_array("../outside.npy", object(), axes=())

            if importlib.util.find_spec("numpy") is None:
                self.skipTest("NumPy optional extra is not installed")
            import numpy as np

            with self.assertRaises(ValueError):
                writer.add_array("arrays/object.npy", np.array([object()]), axes=("item",))
            ref = writer.add_array("arrays/mean.npy", np.array(-0.5, dtype=np.float64), axes=())
            stored = (writer.destination / ref.path).read_bytes()
            self.assertIn(b"False", stored)
            corrupted = stored.replace(b"False", b"True ", 1)
            (writer.destination / ref.path).write_bytes(corrupted)
            altered = replace(
                ref,
                digest="sha256:" + hashlib.sha256(corrupted).hexdigest(),
                byte_length=len(corrupted),
            )
            observation = Observation(
                "mean", "activation", "case-1", "run-1", "float64", (), (), array=altered
            )
            with self.assertRaisesRegex(ValueError, "storage order"):
                writer.append_attempt(AttemptRecord("run-1", "attempt-1", "complete", STREAM, (observation,)))

    def test_truncated_object_and_oversized_npy_evidence_is_rejected(self) -> None:
        if importlib.util.find_spec("numpy") is None:
            self.skipTest("NumPy optional extra is not installed")
        import numpy as np

        for label, alteration in (
            ("truncated", lambda payload: payload[:-1]),
            ("object", lambda payload: payload.replace(b"<f8", b"|O8", 1)),
            ("oversized-header", lambda payload: payload[:8] + b"\xff\xff" + payload[10:]),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                writer = BundleWriter.create(Path(temporary) / "bundle", small_plan())
                ref = writer.add_array("arrays/mean.npy", np.array(-0.5, dtype=np.float64), axes=())
                altered = alteration((writer.destination / ref.path).read_bytes())
                (writer.destination / ref.path).write_bytes(altered)
                ref = replace(
                    ref, digest="sha256:" + hashlib.sha256(altered).hexdigest(), byte_length=len(altered)
                )
                observation = Observation(
                    "mean", "activation", "case-1", "run-1", "float64", (), (), array=ref
                )
                with self.assertRaises(ValueError):
                    writer.append_attempt(
                        AttemptRecord("run-1", "attempt-1", "complete", STREAM, (observation,))
                    )

        with tempfile.TemporaryDirectory() as temporary:
            writer = BundleWriter.create(Path(temporary) / "bundle", small_plan())
            ref = writer.add_array("arrays/mean.npy", np.array(-0.5, dtype=np.float64), axes=())
            observation = Observation("mean", "activation", "case-1", "run-1", "float64", (), (), array=ref)
            writer.append_attempt(AttemptRecord("run-1", "attempt-1", "complete", STREAM, (observation,)))
            self.assertEqual(inspect_bundle(writer.destination).payload_validation, "verified")
            self.assertEqual(
                inspect_bundle(writer.destination, verify=False).payload_validation, "unavailable"
            )
            with patch.dict("sys.modules", {"numpy": None}):
                snapshot = inspect_bundle(writer.destination)
            self.assertEqual(snapshot.payload_validation, "unavailable")
            self.assertEqual(snapshot.qualification, "unsupported")

        with tempfile.TemporaryDirectory() as temporary:
            huge_operation = OperationSpec("activation", (2**60,), ("draw",))
            spec = replace(small_plan().workload, operations=(huge_operation,))
            plan = RunPlan(spec, (PlannedRun("run-1", "case-1", "activation", "evaluation", {}),))
            writer = BundleWriter.create(Path(temporary) / "bundle", plan)
            ref = writer.add_array("arrays/mean.npy", np.array(-0.5, dtype=np.float64), axes=())
            oversized_ref = replace(ref, shape=(2**60,), axes=("draw",))
            observation = Observation(
                "mean", "activation", "case-1", "run-1", "float64", (2**60,), ("draw",), array=oversized_ref
            )
            with self.assertRaisesRegex(ValueError, "allocation"):
                writer.append_attempt(AttemptRecord("run-1", "attempt-1", "complete", STREAM, (observation,)))

        with tempfile.TemporaryDirectory() as temporary:
            writer = BundleWriter.create(Path(temporary) / "bundle", small_plan())
            writer.add_array("arrays/orphan.npy", np.array(1, dtype=np.int64), axes=())
            writer.append_attempt(AttemptRecord("run-1", "attempt-1", "complete", STREAM))
            writer.append_attempt(AttemptRecord("run-2", "attempt-2", "complete", STREAM))
            with self.assertRaisesRegex(ValueError, "unreferenced"):
                writer.finish(execution="complete")


if __name__ == "__main__":
    unittest.main()
