"""Planned S09 coordinator regression contracts based on persisted execution."""

from __future__ import annotations

import contextlib
from copy import deepcopy
from dataclasses import replace
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from gibbsiq.qualification.adapters.spin import SpinConditionalBackend
from gibbsiq.qualification.artifacts import BundleWriter, inspect_bundle, record_to_dict, workload_from_dict
from gibbsiq.qualification.examples import SPIN_CANDIDATES, spin_conditional_plan
from gibbsiq.qualification.workflow import qualify
from test_suite.tests.qualification.policy_fixtures import identity, templates


class RegressionComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from gibbsiq.qualification.comparison import compare_bundles

        cls.compare = staticmethod(compare_bundles)
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.paths = {name: cls.root / name for name in ("pass", "fail", "inconclusive")}
        for name, profile, runs in (
            ("pass", "iid", 1024),
            ("fail", "sign-reversed", 256),
            ("inconclusive", "iid", 4),
        ):
            plan = spin_conditional_plan(runs=runs, candidate=profile)
            report = qualify(
                plan,
                backends={plan.workload.candidate.identity: SpinConditionalBackend(profile)},
                destination=cls.paths[name],
            )
            if report.qualification != name:
                raise AssertionError((name, report.qualification))

    def test_known_sign_defect_is_an_explicit_compatible_regression(self):
        report = self.compare(
            self.paths["pass"], self.paths["fail"], candidate_change=SPIN_CANDIDATES["sign-reversed"]
        )
        self.assertTrue(report["compatible"])
        self.assertEqual(report["outcome"], "regression")
        self.assertLess(report["metrics"][0]["delta"], -0.8)

    def test_candidate_change_requires_the_exact_right_hand_identity(self):
        for allowed in (None, "different-candidate"):
            report = self.compare(self.paths["pass"], self.paths["fail"], candidate_change=allowed)
            self.assertFalse(report["compatible"])
            self.assertEqual(report["outcome"], "incompatible")
            self.assertFalse(report["metrics"])
            self.assertTrue(any("candidate" in str(issue) for issue in report["issues"]))

    def test_difference_range_uses_both_stored_intervals_and_union_error_bound(self):
        report = self.compare(
            self.paths["pass"], self.paths["fail"], candidate_change=SPIN_CANDIDATES["sign-reversed"]
        )
        left = inspect_bundle(self.paths["pass"]).report.metrics[0]
        right = inspect_bundle(self.paths["fail"]).report.metrics[0]
        metric = report["metrics"][0]
        self.assertAlmostEqual(metric["delta"], right.estimate - left.estimate)
        self.assertAlmostEqual(
            metric["difference_interval"]["lower"], right.interval.lower - left.interval.upper
        )
        self.assertAlmostEqual(
            metric["difference_interval"]["upper"], right.interval.upper - left.interval.lower
        )
        self.assertAlmostEqual(metric["joint_error_bound"], 0.1)
        self.assertEqual(metric["difference_procedure"], "union-bound-difference-v1")

    def test_pass_against_itself_and_insufficient_runs_keep_their_scientific_meaning(self):
        self.assertEqual(
            self.compare(self.paths["pass"], self.paths["pass"])["outcome"], "no_regression_under_contract"
        )
        self.assertEqual(
            self.compare(self.paths["pass"], self.paths["inconclusive"])["outcome"], "inconclusive"
        )

    def test_missing_physical_energy_cannot_be_reported_as_a_saving(self):
        report = self.compare(
            self.paths["pass"], self.paths["fail"], candidate_change=SPIN_CANDIDATES["sign-reversed"]
        )
        energy = next(item for item in report["costs"] if item["quantity"] == "energy")
        self.assertEqual(energy["availability"], "unavailable")
        self.assertIsNone(energy["delta"])
        self.assertIsNone(energy["ratio"])
        self.assertIn("physical energy", energy["reason"])

    def test_compare_cli_reports_regression_and_incompatible_exit_codes(self):
        from gibbsiq.qualification.cli import main

        with contextlib.redirect_stdout(StringIO()):
            self.assertEqual(
                main(
                    (
                        "compare",
                        str(self.paths["pass"]),
                        str(self.paths["fail"]),
                        "--candidate-change",
                        SPIN_CANDIDATES["sign-reversed"],
                        "--json",
                    )
                ),
                1,
            )
            self.assertEqual(main(("compare", str(self.paths["pass"]), str(self.paths["fail"]), "--json")), 2)

    def test_corruption_is_rejected_before_comparison(self):
        bad = self.root / "corrupt"
        bad.mkdir()
        (bad / "manifest.json").write_text('{"unfinished":', encoding="utf-8")
        with self.assertRaises(ValueError):
            self.compare(self.paths["pass"], bad)


class ComparisonIdentityTests(unittest.TestCase):
    def test_named_candidate_allowance_cannot_hide_changed_target_or_representation(self):
        from gibbsiq.qualification.comparison import compare_bundles

        original = templates()["evaluation"]
        base = record_to_dict(original.workload)
        rows = {
            name: deepcopy(base)
            for name in ("model_config", "tokenizer", "preprocessing", "profile", "cost_scope")
        }
        rows["model_config"]["model_config"] = record_to_dict(identity("different-model", {}))
        rows["tokenizer"]["inputs"]["tokenizer"] = record_to_dict(identity("different-tokenizer", {}))
        rows["preprocessing"]["inputs"]["preprocessing"] = record_to_dict(
            identity("different-processing", {})
        )
        rows["profile"]["precision"]["profile_id"] = "different-profile"
        rows["cost_scope"]["cost_scope"]["boundary"] = "partial-model"
        changes = {name: workload_from_dict(row) for name, row in rows.items()}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = root / "baseline"
            BundleWriter.create(baseline, original).finish(execution="partial")
            for field, workload in changes.items():
                with self.subTest(field=field):
                    destination = root / field
                    BundleWriter.create(destination, replace(original, workload=workload)).finish(
                        execution="partial"
                    )
                    report = compare_bundles(baseline, destination, candidate_change="toy-candidate")
                    self.assertFalse(report["compatible"])
                    self.assertEqual(report["outcome"], "incompatible")
                    self.assertFalse(report["metrics"])
                    self.assertTrue(report["issues"])


if __name__ == "__main__":
    unittest.main()
