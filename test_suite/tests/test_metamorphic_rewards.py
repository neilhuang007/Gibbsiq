"""Metamorphic tests for verifiable reward behavior.

These checks exercise equivalent encodings or equivalent witnesses. They help
catch agents that memorize one public JSON shape instead of implementing the
underlying objective.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.benchmark_oracle import FAMILY_SPECS, verify_benchmark_fixture  # noqa: E402


def load_fixtures() -> dict[str, dict]:
    path = REPO_ROOT / "reference" / "06-benchmarks" / "fixtures" / "ground-truth-small.json"
    return {
        fixture["id"]: fixture for fixture in json.loads(path.read_text(encoding="utf-8-sig"))["fixtures"]
    }


def correct_actual(fixture: dict) -> dict:
    spec = FAMILY_SPECS[fixture["family"]]
    expected = fixture["expected"]
    actual = {key: expected[key] for key in spec["scalar_keys"]}
    actual[spec["witness_key"]] = [copy.deepcopy(expected[spec["witness_key"]][0])]
    return actual


def spin_flip(witness: dict[str, int]) -> dict[str, int]:
    return {variable: -spin for variable, spin in witness.items()}


class MetamorphicRewardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixtures = load_fixtures()

    def test_maxcut_global_spin_flip_is_still_an_optimal_witness(self) -> None:
        fixture = self.fixtures["gt_maxcut_petersen"]
        actual = correct_actual(fixture)
        actual["witness_spin_samples"] = [spin_flip(actual["witness_spin_samples"][0])]

        self.assertEqual(verify_benchmark_fixture(fixture, actual, 1e-9), [])

    def test_zero_field_spin_glass_global_spin_flip_is_still_optimal(self) -> None:
        fixture = self.fixtures["gt_sk_n12_s15"]
        actual = correct_actual(fixture)
        actual["witness_spin_samples"] = [spin_flip(actual["witness_spin_samples"][0])]

        self.assertEqual(verify_benchmark_fixture(fixture, actual, 1e-9), [])

    def test_partition_side_swap_is_still_an_optimal_witness(self) -> None:
        fixture = self.fixtures["gt_partition_frustrated_n13_v7_s17"]
        actual = correct_actual(fixture)
        witness = actual["witness_partitions"][0]
        actual["witness_partitions"] = [{"set_plus": witness["set_minus"], "set_minus": witness["set_plus"]}]

        self.assertEqual(verify_benchmark_fixture(fixture, actual, 1e-9), [])

    def test_knapsack_selection_order_is_not_part_of_the_reward(self) -> None:
        fixture = self.fixtures["gt_knapsack_n14_s9"]
        actual = correct_actual(fixture)
        actual["witness_selections"] = [list(reversed(actual["witness_selections"][0]))]

        self.assertEqual(verify_benchmark_fixture(fixture, actual, 1e-9), [])

    def test_tsp_rotation_and_reversal_are_equivalent_witnesses(self) -> None:
        fixture = self.fixtures["gt_tsp_n8_s11"]
        base_actual = correct_actual(fixture)
        tour = base_actual["witness_tours"][0]
        variants = [
            tour[3:] + tour[:3],
            list(reversed(tour)),
        ]

        for variant in variants:
            actual = correct_actual(fixture)
            actual["witness_tours"] = [variant]
            with self.subTest(tour=variant):
                self.assertEqual(verify_benchmark_fixture(fixture, actual, 1e-9), [])

    def test_one_bad_witness_fails_even_when_another_witness_is_valid(self) -> None:
        fixture = self.fixtures["gt_knapsack_n10_s8"]
        actual = correct_actual(fixture)
        actual["witness_selections"].append(list(range(len(fixture["input"]["weights"]))))

        diffs = verify_benchmark_fixture(fixture, actual, 1e-9)
        self.assertTrue(any(diff["code"] == "witness_not_optimal" for diff in diffs))

    def test_every_required_scalar_is_mandatory_for_each_family(self) -> None:
        for family in FAMILY_SPECS:
            fixture = next(fixture for fixture in self.fixtures.values() if fixture["family"] == family)
            for key in FAMILY_SPECS[family]["scalar_keys"]:
                actual = correct_actual(fixture)
                del actual[key]
                with self.subTest(family=family, key=key):
                    diffs = verify_benchmark_fixture(fixture, actual, 1e-9)
                    self.assertTrue(
                        any(diff["code"] == "missing_key" and diff["path"].endswith(key) for diff in diffs),
                        diffs,
                    )


if __name__ == "__main__":
    unittest.main()
