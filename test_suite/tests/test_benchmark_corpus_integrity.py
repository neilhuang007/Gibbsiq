"""Structural integrity checks for the ground-truth benchmark corpus."""

# Doesn't prove the optima -- proves the artifact is fit for verifiable
# rewards: unique IDs, a stable checksum, explicit provenance, and a
# family-specific schema an external scorer can validate before execution.

from __future__ import annotations

import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.benchmark_oracle import FAMILY_SPECS  # noqa: E402


CORPUS_PATH = REPO_ROOT / "reference" / "06-benchmarks" / "fixtures" / "ground-truth-small.json"
FIXTURE_ID_RE = re.compile(r"^gt_[a-z0-9_]+$")


def load_corpus() -> dict:
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8-sig"))


def canonical_sha256(document: dict) -> str:
    without_checksum = {key: value for key, value in document.items() if key != "content_sha256"}
    payload = json.dumps(without_checksum, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class BenchmarkCorpusIntegrityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = load_corpus()
        self.fixtures = self.corpus["fixtures"]

    def test_top_level_metadata_fields(self) -> None:
        self.assertEqual(self.corpus["schema_version"], "2026-05-31")
        self.assertEqual(self.corpus["generator"], "tools/generate_ground_truth.py")
        self.assertIn("E(s) = offset", self.corpus["energy_convention"])
        self.assertEqual(self.corpus["content_sha256"], canonical_sha256(self.corpus))

    def test_fixture_id_format_uniqueness(self) -> None:
        fixture_ids = [fixture["id"] for fixture in self.fixtures]
        self.assertEqual(len(fixture_ids), 27)
        self.assertEqual(len(fixture_ids), len(set(fixture_ids)))
        for fixture_id in fixture_ids:
            self.assertRegex(fixture_id, FIXTURE_ID_RE)

    def test_declared_families_match_oracle_families(self) -> None:
        declared = set(self.corpus["families"])
        observed = {fixture["family"] for fixture in self.fixtures}
        self.assertEqual(declared, observed)
        self.assertEqual(observed, set(FAMILY_SPECS))

    def test_fixture_provenance_is_complete(self) -> None:
        for fixture in self.fixtures:
            provenance = fixture.get("provenance", {})
            with self.subTest(fixture=fixture["id"]):
                self.assertEqual(provenance.get("generator"), "tools/generate_ground_truth.py")
                self.assertIn(
                    provenance.get("method"),
                    {"exhaustive_enumeration", "closed_form_with_enumeration_crosscheck"},
                )
                self.assertIsInstance(provenance.get("formulation_source"), str)
                self.assertGreater(len(provenance["formulation_source"]), 20)
                if provenance["method"] == "exhaustive_enumeration":
                    self.assertIn("seed", provenance)

    def test_family_required_keys_present(self) -> None:
        for fixture in self.fixtures:
            spec = FAMILY_SPECS[fixture["family"]]
            expected = fixture["expected"]
            with self.subTest(fixture=fixture["id"]):
                for key in spec["scalar_keys"]:
                    self.assertIn(key, expected)
                    self.assertIsInstance(expected[key], (int, float, bool))
                self.assertIn(spec["witness_key"], expected)
                self.assertIsInstance(expected[spec["witness_key"]], list)
                self.assertGreater(len(expected[spec["witness_key"]]), 0)

    def test_input_models_have_minimum_decoding_conventions(self) -> None:
        for fixture in self.fixtures:
            model = fixture["input"]
            with self.subTest(fixture=fixture["id"]):
                self.assertIn("format", model)
                if fixture["family"] in {"maxcut", "sk_spin_glass"}:
                    variables = model["variables"]
                    self.assertEqual(variables, [str(index) for index in range(len(variables))])
                if fixture["family"] == "maxcut":
                    edge_set = {tuple(edge) for edge in model["edges"]}
                    self.assertEqual(len(edge_set), len(model["edges"]))
                    for left, right in model["edges"]:
                        self.assertIn(left, model["variables"])
                        self.assertIn(right, model["variables"])
                        self.assertLess(int(left), int(right))
                if fixture["family"] == "sk_spin_glass":
                    self.assertEqual(set(model["linear"]), set(model["variables"]))
                    for pair in model["quadratic"]:
                        left, right = pair.split(",")
                        self.assertLess(int(left), int(right))
                        self.assertIn(left, model["variables"])
                        self.assertIn(right, model["variables"])
                if fixture["family"] == "tsp":
                    matrix = model["distance_matrix"]
                    self.assertEqual(model["num_cities"], len(matrix))
                    for i, row in enumerate(matrix):
                        self.assertEqual(len(row), len(matrix))
                        self.assertEqual(row[i], 0)
                        for j, value in enumerate(row):
                            self.assertEqual(value, matrix[j][i])


if __name__ == "__main__":
    unittest.main()
