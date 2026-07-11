"""Strict-scoring tests for the ground-truth benchmark oracle."""

# The corpus stores proven witnesses, so a candidate built from the fixtures'
# own `expected` block must pass. Mutation tests confirm the oracle recomputes
# the objective independently rather than trusting a candidate's reported number.

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.benchmark_oracle import FAMILY_SPECS, verify_benchmark_fixture  # noqa: E402


def load_corpus() -> list[dict]:
    path = REPO_ROOT / "reference" / "06-benchmarks" / "fixtures" / "ground-truth-small.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))["fixtures"]


def correct_actual(fixture: dict) -> dict:
    """A candidate output that matches the proven optimum, with one witness."""
    spec = FAMILY_SPECS[fixture["family"]]
    expected = fixture["expected"]
    actual = {key: expected[key] for key in spec["scalar_keys"]}
    actual[spec["witness_key"]] = [expected[spec["witness_key"]][0]]
    return actual


class BenchmarkOracleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixtures = load_corpus()
        self.by_family = {f["family"]: f for f in self.fixtures}

    def test_corpus_covers_all_families(self) -> None:
        self.assertEqual(set(self.by_family), set(FAMILY_SPECS))

    def test_proven_witnesses_pass(self) -> None:
        for fixture in self.fixtures:
            diffs = verify_benchmark_fixture(fixture, correct_actual(fixture), 1e-9)
            self.assertEqual(diffs, [], f"{fixture['id']} should pass: {diffs}")

    def test_every_stored_witness_is_optimal(self) -> None:
        # Every witness the generator stored must independently re-verify.
        for fixture in self.fixtures:
            spec = FAMILY_SPECS[fixture["family"]]
            actual = {key: fixture["expected"][key] for key in spec["scalar_keys"]}
            actual[spec["witness_key"]] = fixture["expected"][spec["witness_key"]]
            diffs = verify_benchmark_fixture(fixture, actual, 1e-9)
            self.assertEqual(diffs, [], f"{fixture['id']} witnesses: {diffs}")

    def test_wrong_optimum_fails(self) -> None:
        fixture = self.by_family["maxcut"]
        actual = correct_actual(fixture)
        actual["best_cut_value"] = actual["best_cut_value"] + 1
        diffs = verify_benchmark_fixture(fixture, actual, 1e-9)
        # The reported scalar no longer matches the proven optimum.
        self.assertTrue(any(d["code"] in {"value_mismatch", "float_mismatch"} for d in diffs))
        # Anti-gaming property: witnesses are re-checked against the fixture's
        # proven optimum (not the candidate's claim), so a genuinely optimal
        # witness still verifies even when the reported number is wrong.
        self.assertFalse(any(d["code"] == "witness_not_optimal" for d in diffs))

    def test_wrong_degeneracy_fails(self) -> None:
        fixture = self.by_family["sk_spin_glass"]
        actual = correct_actual(fixture)
        actual["ground_state_degeneracy"] = actual["ground_state_degeneracy"] + 2
        diffs = verify_benchmark_fixture(fixture, actual, 1e-9)
        self.assertTrue(any("degeneracy" in d["path"] for d in diffs))

    def test_missing_witness_fails(self) -> None:
        fixture = self.by_family["tsp"]
        actual = correct_actual(fixture)
        actual["witness_tours"] = []
        diffs = verify_benchmark_fixture(fixture, actual, 1e-9)
        self.assertTrue(any(d["code"] == "missing_witness" for d in diffs))

    def test_tampered_witness_fails(self) -> None:
        # Correct optimum, suboptimal tour: the oracle recomputes the tour
        # length itself and rejects it.
        fixture = self.by_family["tsp"]
        actual = correct_actual(fixture)
        good = actual["witness_tours"][0]
        bad = good[:]
        bad[0], bad[1] = bad[1], bad[0]  # adjacent swap -> different (worse) tour
        actual["witness_tours"] = [bad]
        diffs = verify_benchmark_fixture(fixture, actual, 1e-9)
        # Confirms the corpus instance is discriminating even if the swap tied.
        self.assertTrue(
            any(d["code"] == "witness_not_optimal" for d in diffs),
            f"expected a non-optimal witness rejection, got {diffs}",
        )

    def test_infeasible_knapsack_witness_fails(self) -> None:
        fixture = self.by_family["knapsack"]
        actual = correct_actual(fixture)
        # Select every item: almost certainly over capacity.
        actual["witness_selections"] = [list(range(len(fixture["input"]["weights"])))]
        diffs = verify_benchmark_fixture(fixture, actual, 1e-9)
        self.assertTrue(any(d["code"] == "witness_not_optimal" for d in diffs))

    def test_partition_witness_must_use_all_numbers(self) -> None:
        fixture = self.by_family["number_partition"]
        actual = correct_actual(fixture)
        tampered = copy.deepcopy(actual["witness_partitions"][0])
        tampered["set_plus"] = tampered["set_plus"][:-1]  # drop a number
        actual["witness_partitions"] = [tampered]
        diffs = verify_benchmark_fixture(fixture, actual, 1e-9)
        self.assertTrue(any(d["code"] == "witness_not_optimal" for d in diffs))

    def test_boolean_witness_values_rejected(self) -> None:
        spin_fixture = self.by_family["maxcut"]
        spin_actual = correct_actual(spin_fixture)
        spin_witness = copy.deepcopy(spin_actual["witness_spin_samples"][0])
        if 1 not in spin_witness.values():
            spin_witness = {key: -value for key, value in spin_witness.items()}
        plus_key = next(key for key, value in spin_witness.items() if value == 1)
        spin_witness[plus_key] = True
        spin_actual["witness_spin_samples"] = [spin_witness]

        knapsack_fixture = self.by_family["knapsack"]
        knapsack_actual = correct_actual(knapsack_fixture)
        selection = list(knapsack_actual["witness_selections"][0])
        selection[selection.index(0)] = False
        knapsack_actual["witness_selections"] = [selection]

        tsp_fixture = self.by_family["tsp"]
        tsp_actual = correct_actual(tsp_fixture)
        tour = list(tsp_actual["witness_tours"][0])
        tour[tour.index(0)] = False
        tsp_actual["witness_tours"] = [tour]

        for fixture, actual in (
            (spin_fixture, spin_actual),
            (knapsack_fixture, knapsack_actual),
            (tsp_fixture, tsp_actual),
        ):
            with self.subTest(family=fixture["family"]):
                differences = verify_benchmark_fixture(fixture, actual, 1e-9)
                self.assertTrue(
                    any(
                        difference["code"] in {"invalid_witness", "witness_not_optimal"}
                        for difference in differences
                    ),
                    differences,
                )

    def test_spin_witness_rejects_unknown_key(self) -> None:
        fixture = self.by_family["maxcut"]
        actual = correct_actual(fixture)
        witness = copy.deepcopy(actual["witness_spin_samples"][0])
        witness["unknown"] = 1
        actual["witness_spin_samples"] = [witness]
        differences = verify_benchmark_fixture(fixture, actual, 1e-9)
        self.assertTrue(any(difference["code"] == "invalid_witness" for difference in differences))


if __name__ == "__main__":
    unittest.main()
