"""A fake local release history retains bad evidence and immutable filenames."""

import json
from pathlib import Path
import tempfile
import unittest


class ReleaseRecoveryTests(unittest.TestCase):
    def test_rehearsal_retains_detected_defect_and_qualified_correction(self):
        from gibbsiq.qualification.artifacts import inspect_bundle
        from tools.qualification.release_recovery import rehearse

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "release"
            summary = rehearse(root)
            bad = inspect_bundle(root / "sign-reversed", verify=True)
            correction = inspect_bundle(root / "iid", verify=True)
            self.assertEqual(bad.qualification, "fail")
            self.assertLess(bad.report.metrics[0].estimate, -0.5)
            self.assertEqual(correction.qualification, "pass")
            # The reported metric is candidate-minus-reference, so the corrected
            # conditional law has zero expected error (its raw mean is 0.5).
            interval = correction.report.metrics[0].interval
            self.assertLess(interval.lower, 0.0)
            self.assertGreater(interval.upper, 0.0)
            self.assertEqual(len(bad.attempts), 256)
            self.assertEqual(len(correction.attempts), 1024)
            self.assertEqual(summary["ordinary_selection"]["version"], [0, 2, 1])
            self.assertTrue(summary["exact_bad_pin"]["warning"])
            self.assertEqual(summary["exact_bad_pin"]["qualification"], bad.qualification)
            self.assertEqual(json.loads((root / "recovery.json").read_text(encoding="utf-8")), summary)

    def test_yank_excludes_latest_but_exact_pin_keeps_the_warning_and_reason(self):
        from tools.qualification.release_recovery import LocalReleaseHistory

        history = LocalReleaseHistory()
        history.add((0, 1, 0), "old.whl", "pass")
        history.add((0, 2, 0), "bad.whl", "fail")
        history.yank((0, 2, 0), "conditional mean has the wrong sign")
        self.assertEqual(history.resolve()["filename"], "old.whl")
        pinned = history.resolve(exact=(0, 2, 0))
        self.assertEqual(pinned["qualification"], "fail")
        self.assertEqual(pinned["warning"], "conditional mean has the wrong sign")
        history.add((0, 2, 1), "corrected.whl", "pass")
        self.assertEqual(history.resolve()["version"], [0, 2, 1])
        self.assertEqual(history.resolve(exact=(0, 2, 0)), pinned)

    def test_deletion_never_releases_a_filename_for_reuse(self):
        from tools.qualification.release_recovery import LocalReleaseHistory

        history = LocalReleaseHistory()
        history.add((0, 2, 0), "broken.whl", "fail")
        history.remove("broken.whl")
        with self.assertRaises(ValueError):
            history.add((0, 2, 1), "broken.whl", "pass")
        with self.assertRaises(LookupError):
            history.resolve(exact=(0, 2, 0))
        self.assertEqual(history.records[0]["qualification"], "fail")


if __name__ == "__main__":
    unittest.main()
