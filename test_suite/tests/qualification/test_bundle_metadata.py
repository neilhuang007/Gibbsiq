"""Offline snapshots provide checked provenance without reopening loose files."""

from pathlib import Path
import tempfile
import unittest

from gibbsiq.qualification.artifacts import BundleWriter, inspect_bundle
from test_suite.tests.qualification.test_workflow_recovery import recovery_plan


class BundleMetadataTests(unittest.TestCase):
    def test_partial_snapshot_exposes_allowlisted_environment_and_actual_retention(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "evidence"
            environment = {"backend": "synthetic", "device": "cpu"}
            BundleWriter.create(destination, recovery_plan(), environment=environment)
            environment["device"] = "changed-after-write"
            snapshot = inspect_bundle(destination)
            self.assertEqual(dict(snapshot.environment), {"backend": "synthetic", "device": "cpu"})
            self.assertEqual(
                snapshot.retained_bytes,
                sum(path.stat().st_size for path in destination.rglob("*") if path.is_file()),
            )
            self.assertIsNone(snapshot.manifest_digest)
            with self.assertRaises(TypeError):
                snapshot.environment["device"] = "modified"


if __name__ == "__main__":
    unittest.main()
