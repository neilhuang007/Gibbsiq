"""Behavioral tests for bounded evidence retention inventory."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from gibbsiq.qualification.artifacts import BundleWriter
from test_suite.tests.qualification.test_artifacts import small_plan
from tools.qualification.retention_inventory import inventory_evidence


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }


class RetentionInventoryTests(unittest.TestCase):
    def test_supported_bundle_is_inspected_and_original_bytes_are_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "evidence"
            bundle = root / "schema-1"
            BundleWriter.create(bundle, small_plan())
            before = _tree_bytes(root)

            report = inventory_evidence((root,), max_total_bytes=2 * 1024 * 1024)

            self.assertEqual(report["bundles"][0]["schema"], 1)
            self.assertTrue(report["bundles"][0]["certified"])
            self.assertEqual(report["bundles"][0]["path"], str(bundle.resolve()))
            self.assertEqual(_tree_bytes(root), before)

    def test_corrupt_bundle_is_catalogued_but_not_certified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "evidence"
            bundle = root / "corrupt"
            BundleWriter.create(bundle, small_plan())
            (bundle / "plan.json").write_bytes(b"{}")

            report = inventory_evidence((root,))

            self.assertFalse(report["bundles"][0]["certified"])
            self.assertEqual(report["bundles"][0]["status"], "corrupt")
            self.assertIn("error", report["bundles"][0])

    def test_private_large_classification_and_deletion_targets_are_dry_run_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "evidence"
            bundle = root / "private-run"
            BundleWriter.create(bundle, small_plan())
            before = _tree_bytes(root)

            report = inventory_evidence(
                (root,),
                private_paths=(bundle,),
                deletion_targets=(bundle,),
                large_bytes=1,
            )

            item = report["bundles"][0]
            self.assertTrue(item["private"])
            self.assertTrue(item["large"])
            self.assertEqual(report["dry_run_deletion_targets"], [str(bundle.resolve())])
            self.assertEqual(_tree_bytes(root), before)

    def test_file_level_private_path_marks_its_containing_bundle_private(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "evidence"
            bundle = root / "private-run"
            BundleWriter.create(bundle, small_plan())

            report = inventory_evidence((root,), private_paths=(bundle / "plan.json",))

            self.assertTrue(report["bundles"][0]["private"])

    def test_overlapping_roots_are_walked_and_counted_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "evidence"
            bundle = root / "bundle"
            BundleWriter.create(bundle, small_plan())

            single = inventory_evidence((root,))
            overlapping = inventory_evidence((root, bundle))

            self.assertEqual(overlapping["bytes"], single["bytes"])
            self.assertEqual(overlapping["entries"], single["entries"])
            self.assertEqual(overlapping["bundles"], single["bundles"])

    def test_scope_and_byte_budgets_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "evidence"
            BundleWriter.create(root / "bundle", small_plan())
            with self.assertRaisesRegex(ValueError, "byte budget"):
                inventory_evidence((root,), max_total_bytes=1)
            with self.assertRaisesRegex(ValueError, "inside an inventory root"):
                inventory_evidence((root,), deletion_targets=(Path(temporary).parent,))

    def test_cli_emits_json_and_never_deletes_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "evidence"
            bundle = root / "bundle"
            BundleWriter.create(bundle, small_plan())
            before = _tree_bytes(root)
            command = [
                sys.executable,
                "-S",
                "tools/qualification/retention_inventory.py",
                "--root",
                str(root),
                "--delete-target",
                str(bundle),
            ]
            environment = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}
            result = subprocess.run(command, capture_output=True, text=True, check=False, env=environment)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["mode"], "dry-run")
            self.assertTrue(bundle.exists())
            self.assertEqual(_tree_bytes(root), before)
            from gibbsiq.qualification.artifacts import inspect_bundle

            self.assertEqual(inspect_bundle(bundle).plan, small_plan())


if __name__ == "__main__":
    unittest.main()
