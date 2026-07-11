"""Tests for the public JSON evaluation harness."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.evaluation import (  # noqa: E402
    compare_values,
    evaluate_candidate,
    load_fixture_sets,
    normalize_candidate,
)
from gibbsiq.benchmark_oracle import FAMILY_SPECS  # noqa: E402


def load_json(relative_path: str) -> dict:
    return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8-sig"))


def complete_candidate_from_fixtures() -> dict:
    fixture_sets = load_fixture_sets(REPO_ROOT / "reference" / "08-evaluation" / "fixtures")
    results = []
    for fixture_id, fixture in fixture_sets["fixtures"].items():
        if fixture_id in fixture_sets["groups"]["benchmark"]:
            spec = FAMILY_SPECS[fixture["family"]]
            expected = fixture["expected"]
            actual = {key: expected[key] for key in spec["scalar_keys"]}
            actual[spec["witness_key"]] = [expected[spec["witness_key"]][0]]
        else:
            actual = fixture["expected"]
        results.append({"id": fixture_id, "actual": actual})
    return {"results": results}


class EvaluationHarnessTest(unittest.TestCase):
    def test_candidate_normalization_accepts_supported_shapes(self) -> None:
        self.assertEqual(
            normalize_candidate({"results": [{"id": "a", "actual": {"x": 1}}]}),
            {"a": {"x": 1}},
        )
        self.assertEqual(
            normalize_candidate({"fixtures": [{"fixture_id": "b", "output": {"y": 2}}]}),
            {"b": {"y": 2}},
        )
        self.assertEqual(
            normalize_candidate({"schema_version": "test", "c": {"z": 3}}),
            {"c": {"z": 3}},
        )

    def test_candidate_normalization_rejects_duplicate_result_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicates fixture id"):
            normalize_candidate(
                {
                    "results": [
                        {"id": "same", "actual": {"x": 1}},
                        {"id": "same", "actual": {"x": 2}},
                    ]
                }
            )

    def test_unordered_fixture_lists_are_compared_as_multisets(self) -> None:
        expected = {
            "required_flags": ["mode_collapse", "low_diversity"],
            "best_spin_samples": [{"a": 1}, {"a": -1}],
        }
        actual = {
            "required_flags": ["low_diversity", "mode_collapse"],
            "best_spin_samples": [{"a": -1}, {"a": 1}],
        }

        self.assertEqual(compare_values(expected, actual, "fixture", 1e-9), [])

    def test_unordered_nested_numbers_honor_float_tolerance(self) -> None:
        expected = {
            "best_spin_samples": [
                {"sample": {"a": -1}, "energy": -1.0},
                {"sample": {"a": 1}, "energy": 2.0},
            ]
        }
        actual = {
            "best_spin_samples": [
                {"sample": {"a": 1}, "energy": 2.0 + 5e-10},
                {"sample": {"a": -1}, "energy": -1.0 - 5e-10},
            ]
        }

        self.assertEqual(compare_values(expected, actual, "fixture", 1e-9), [])
        differences = compare_values(expected, actual, "fixture", 1e-12)
        self.assertEqual(len(differences), 1)
        self.assertEqual(differences[0].code, "unordered_list_mismatch")

    def test_bool_and_int_not_interchangeable(self) -> None:
        for expected, actual in ((True, 1), (False, 0), (1, True), (0, False)):
            with self.subTest(expected=expected, actual=actual):
                differences = compare_values(expected, actual, "fixture.scalar", 1e-9)
                self.assertEqual(len(differences), 1)
                self.assertEqual(differences[0].code, "value_mismatch")

    def test_example_candidate_matches_golden_fixtures(self) -> None:
        candidate = normalize_candidate(load_json("test_suite/examples/evaluation-candidate.example.json"))

        with tempfile.TemporaryDirectory() as tmpdir:
            empty_benchmark = Path(tmpdir) / "empty-benchmark.json"
            empty_benchmark.write_text(
                json.dumps({"schema_version": "test-empty", "fixtures": []}),
                encoding="utf-8",
            )
            fixture_sets = load_fixture_sets(
                REPO_ROOT / "reference" / "08-evaluation" / "fixtures",
                benchmark_path=empty_benchmark,
            )

        for group in ("exact", "diagnostic"):
            for fixture_id in fixture_sets["groups"][group]:
                fixture = fixture_sets["fixtures"][fixture_id]
                differences = compare_values(fixture["expected"], candidate[fixture_id], fixture_id, 1e-9)
                self.assertEqual(differences, [], fixture_id)

    def test_default_evaluator_reports_missing_benchmark_fixtures(self) -> None:
        report = evaluate_candidate(load_json("test_suite/examples/evaluation-candidate.example.json"))

        self.assertFalse(report["passed"])
        self.assertEqual(report["summary"]["passed"], 12)
        self.assertEqual(report["summary"]["missing"], 27)
        self.assertEqual(report["summary"]["failed"], 0)
        self.assertTrue(
            all(
                result["status"] == "missing"
                for result in report["results"]
                if result["id"].startswith("gt_")
            )
        )

    def test_unknown_fixture_ids_fail_evaluation(self) -> None:
        candidate = complete_candidate_from_fixtures()
        candidate["results"].append({"id": "unknown_fixture", "actual": {"answer": 1}})

        report = evaluate_candidate(candidate)

        self.assertFalse(report["passed"])
        self.assertEqual(report["summary"]["unknown"], 1)
        self.assertEqual(report["unknown_fixture_ids"], ["unknown_fixture"])

    def test_candidate_strings_are_data_not_code(self) -> None:
        differences = compare_values(
            {"energy": 1},
            {"energy": "__import__('pathlib').Path('should_not_exist').write_text('x')"},
            "malicious_payload",
            1e-9,
        )

        self.assertEqual(len(differences), 1)
        self.assertFalse((REPO_ROOT / "should_not_exist").exists())


if __name__ == "__main__":
    unittest.main()
