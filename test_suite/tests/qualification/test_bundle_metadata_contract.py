"""Planned S08 tests for search/compare metadata from safe artifact inspection."""

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from gibbsiq.qualification.artifacts import BundleWriter, inspect_bundle
from test_suite.tests.qualification.test_artifacts import observed_attempt, small_plan


class BundleMetadataTests(unittest.TestCase):
    def test_inspection_carries_immutable_environment_through_partial_and_complete_states(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bundle"
            environment = {"python": "fixture-python", "device": "cpu"}
            writer = BundleWriter.create(path, small_plan(), environment=environment)
            environment["device"] = "changed-after-writing"
            writer.append_attempt(observed_attempt())
            partial = inspect_bundle(path)
            self.assertEqual(dict(partial.environment), {"python": "fixture-python", "device": "cpu"})
            self.assertIsNone(partial.manifest_digest)
            self.assertEqual(partial.retained_bytes, sum(item.stat().st_size for item in path.iterdir()))
            with self.assertRaises(TypeError):
                partial.environment["device"] = "mutated"
            writer.append_attempt(
                replace(observed_attempt(), run_id="run-2", attempt_id="attempt-2", observations=())
            )
            completed = writer.finish(execution="complete")
            self.assertEqual(completed.environment, partial.environment)
            self.assertEqual(completed.execution, "complete")
            self.assertEqual(len(completed.attempts), 2)
            self.assertIsNotNone(completed.manifest_digest)
            self.assertGreater(completed.retained_bytes, partial.retained_bytes)
            self.assertEqual(completed.retained_bytes, sum(item.stat().st_size for item in path.iterdir()))

    def test_changed_environment_in_final_bundle_is_rejected_as_corruption(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bundle"
            writer = BundleWriter.create(path, small_plan(), environment={"device": "cpu"})
            writer.append_attempt(observed_attempt())
            writer.finish(execution="partial")
            (path / "environment.json").write_text('{"device":"gpu"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                inspect_bundle(path)


if __name__ == "__main__":
    unittest.main()
