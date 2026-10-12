"""Spin-tuple and mapping energy paths of IsingModel against direct coefficient sums."""

from __future__ import annotations

import math
import random
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.model import IsingModel, sample_to_spin_values  # noqa: E402


def random_sparse_model(rng: random.Random, variables: tuple, edge_count: int, offset: float) -> IsingModel:
    linear = {variable: rng.uniform(-2.0, 2.0) for variable in variables}
    quadratic = {}
    while len(quadratic) < edge_count:
        left, right = rng.sample(range(len(variables)), 2)
        low, high = min(left, right), max(left, right)
        quadratic[(variables[low], variables[high])] = rng.uniform(-1.5, 1.5)
    return IsingModel(variables=variables, linear=linear, quadratic=quadratic, offset=offset)


def direct_interaction(model: IsingModel, sample: dict) -> float:
    terms = [model.linear[variable] * sample[variable] for variable in model.variables]
    terms.extend(
        coefficient * sample[left] * sample[right] for (left, right), coefficient in model.quadratic.items()
    )
    return math.fsum(terms)


def direct_local_field(model: IsingModel, variable, sample: dict) -> float:
    terms = [model.linear[variable]]
    for (left, right), coefficient in model.quadratic.items():
        if left == variable:
            terms.append(coefficient * sample[right])
        elif right == variable:
            terms.append(coefficient * sample[left])
    return math.fsum(terms)


def random_spins(rng: random.Random, count: int) -> tuple[int, ...]:
    return tuple(rng.choice((-1, 1)) for _ in range(count))


class SpinTuplePathTests(unittest.TestCase):
    def assert_pairs_match(self, model: IsingModel, seed: int) -> None:
        rng = random.Random(seed)
        for _ in range(50):
            spins = random_spins(rng, len(model.variables))
            sample = dict(zip(model.variables, spins))
            expected_interaction = direct_interaction(model, sample)
            expected_energy = math.fsum([model.offset, expected_interaction])
            self.assertEqual(
                model.energy_and_interaction_from_spins(spins), (expected_energy, expected_interaction)
            )
            self.assertEqual(model.energy_and_interaction(sample), (expected_energy, expected_interaction))
            self.assertEqual(model.energy_from_spins(spins), expected_energy)
            self.assertEqual(model.interaction_energy_from_spins(spins), expected_interaction)
            self.assertEqual(model.energy(sample), expected_energy)
            self.assertEqual(model.interaction_energy(sample), expected_interaction)

    def test_spin_tuple_energy_matches_mapping_energy(self) -> None:
        model = random_sparse_model(random.Random(11), tuple(range(12)), 20, 0.75)
        self.assert_pairs_match(model, seed=101)

    def test_tuple_label_spin_energy_matches_direct_sum(self) -> None:
        variables = tuple((row, column) for row in range(3) for column in range(3))
        model = random_sparse_model(random.Random(12), variables, 10, -1.25)
        self.assert_pairs_match(model, seed=102)

    def test_binary_pair_matches_spin_pair(self) -> None:
        model = random_sparse_model(random.Random(13), tuple(range(6)), 8, 0.5)
        spins = random_spins(random.Random(103), 6)
        binary = {variable: (spin + 1) // 2 for variable, spin in zip(model.variables, spins)}
        self.assertEqual(
            model.energy_and_interaction(binary, vartype="BINARY"),
            model.energy_and_interaction_from_spins(spins),
        )

    def test_spin_tuple_rejects_wrong_length(self) -> None:
        model = random_sparse_model(random.Random(14), tuple(range(4)), 3, 0.0)
        for spins in ((1, -1, 1), (1, -1, 1, -1, 1)):
            with self.assertRaisesRegex(ValueError, "length"):
                model.energy_and_interaction_from_spins(spins)
            with self.assertRaisesRegex(ValueError, "length"):
                model.interaction_energy_from_spins(spins)
            with self.assertRaisesRegex(ValueError, "length"):
                model.energy_from_spins(spins)

    def test_spin_tuple_rejects_bool_and_out_of_range_values(self) -> None:
        model = random_sparse_model(random.Random(15), tuple(range(4)), 3, 0.0)
        for bad in (True, False, 0, 2, 1.0):
            spins = (1, -1, bad, 1)
            with self.assertRaisesRegex(ValueError, "position 2"):
                model.energy_and_interaction_from_spins(spins)
            with self.assertRaisesRegex(ValueError, "position 2"):
                model.interaction_energy_from_spins(spins)
            with self.assertRaisesRegex(ValueError, "position 2"):
                model.energy_from_spins(spins)


class SampleToSpinValuesTests(unittest.TestCase):
    def test_bool_key_does_not_match_int_variable(self) -> None:
        with self.assertRaisesRegex(ValueError, "sample is missing variable 1"):
            sample_to_spin_values({True: 1}, (1,), "SPIN")

    def test_float_key_does_not_match_int_variable(self) -> None:
        with self.assertRaisesRegex(ValueError, "sample is missing variable 1"):
            sample_to_spin_values({1.0: 1}, (1,), "SPIN")

    def test_missing_message_names_first_missing_variable(self) -> None:
        with self.assertRaises(ValueError) as caught:
            sample_to_spin_values({"d": 1, "b": -1}, ("a", "b", "c", "d"), "SPIN")
        self.assertEqual(str(caught.exception), "sample is missing variable 'a'")

    def test_missing_variable_precedes_invalid_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing variable 'b'"):
            sample_to_spin_values({"a": 5}, ("b", "a"), "SPIN")

    def test_boolean_value_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be boolean"):
            sample_to_spin_values({"a": True}, ("a",), "SPIN")
        with self.assertRaisesRegex(ValueError, "must not be boolean"):
            sample_to_spin_values({"a": False}, ("a",), "BINARY")

    def test_out_of_range_values_name_vartype(self) -> None:
        with self.assertRaisesRegex(ValueError, "spin value for 'a' must be -1 or"):
            sample_to_spin_values({"a": 0}, ("a",), "SPIN")
        with self.assertRaisesRegex(ValueError, "binary value for 'a' must be 0 or 1"):
            sample_to_spin_values({"a": -1}, ("a",), "BINARY")

    def test_extra_key_is_ignored(self) -> None:
        self.assertEqual(
            sample_to_spin_values({"extra": 7, "b": -1, "a": 1}, ("a", "b"), "SPIN"),
            (1, -1),
        )

    def test_binary_values_map_to_spins(self) -> None:
        self.assertEqual(sample_to_spin_values({"a": 0, "b": 1}, ("a", "b"), "BINARY"), (-1, 1))


class LocalFieldPathTests(unittest.TestCase):
    def test_local_field_and_flip_delta_match_direct_computation(self) -> None:
        model = random_sparse_model(random.Random(16), tuple(range(12)), 20, 0.3)
        spins = random_spins(random.Random(104), 12)
        sample = dict(zip(model.variables, spins))
        for variable in model.variables:
            gamma = direct_local_field(model, variable, sample)
            self.assertEqual(model.local_field(variable, sample), gamma)
            self.assertEqual(model.flip_energy_delta(variable, sample), -2.0 * sample[variable] * gamma)

    def test_flip_delta_matches_energy_difference(self) -> None:
        model = random_sparse_model(random.Random(17), tuple(range(12)), 20, 0.3)
        sample = dict(zip(model.variables, random_spins(random.Random(105), 12)))
        for variable in model.variables:
            flipped = {**sample, variable: -sample[variable]}
            expected = direct_interaction(model, flipped) - direct_interaction(model, sample)
            self.assertAlmostEqual(model.flip_energy_delta(variable, sample), expected, places=12)


if __name__ == "__main__":
    unittest.main()
