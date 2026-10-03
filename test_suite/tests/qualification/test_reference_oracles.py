from __future__ import annotations

import math
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from gibbsiq.conversions import compile_ising  # noqa: E402
from gibbsiq.qualification.adapters.reference import (  # noqa: E402
    enumerate_ising,
    four_parent_conditional,
    spin_conditional,
    torx_two_gate_reference,
)


class TorxReferenceTests(unittest.TestCase):
    def test_four_explicit_branches(self) -> None:
        reference = torx_two_gate_reference()
        self.assertEqual(reference.probabilities, (0.5, 0.0, 0.25, 0.25))
        self.assertEqual(reference.bit_means, (0.5, 0.25))
        changed = torx_two_gate_reference((0.0, 0.0), (1, 1))
        self.assertEqual(changed.probabilities, (0.0, 0.5, 0.25, 0.25))
        self.assertNotEqual(torx_two_gate_reference((2.0, -1.0)).probabilities, reference.probabilities)

    def test_rejects_boolean_bits_and_nonfinite_angles(self) -> None:
        for angles, bits in (((0.0, float("inf")), (0, 0)), ((0.0, 0.0), (True, 0))):
            with self.assertRaises(ValueError):
                torx_two_gate_reference(angles, bits)


class SpinConditionalReferenceTests(unittest.TestCase):
    def test_hand_derived_three_to_one_odds(self) -> None:
        result = spin_conditional(math.log(3.0) / 2.0, samples=100)

        self.assertAlmostEqual(result.probability_up, 0.75, places=15)
        self.assertAlmostEqual(result.mean, 0.5, places=15)
        self.assertAlmostEqual(result.variance, 0.75, places=15)
        self.assertAlmostEqual(result.mean_variance, 0.0075, places=15)
        self.assertEqual(result.samples, 100)

    def test_zero_and_large_finite_fields_are_stable(self) -> None:
        zero = spin_conditional(0)
        positive = spin_conditional(1e308)
        negative = spin_conditional(-1e308)

        self.assertEqual(
            (zero.probability_up, zero.mean, zero.variance, zero.mean_variance),
            (0.5, 0.0, 1.0, 1.0),
        )
        self.assertEqual(
            (positive.probability_up, positive.mean, positive.variance),
            (1.0, 1.0, 0.0),
        )
        self.assertEqual(
            (negative.probability_up, negative.mean, negative.variance),
            (0.0, -1.0, 0.0),
        )

    def test_invalid_field_and_sample_count_fail_closed(self) -> None:
        for field in (True, "0", math.nan, math.inf, -math.inf, 10**1000):
            with self.subTest(field=field), self.assertRaises(ValueError):
                spin_conditional(field)  # type: ignore[arg-type]
        for samples in (0, -1, True, 1.0, "1"):
            with self.subTest(samples=samples), self.assertRaises(ValueError):
                spin_conditional(0.0, samples=samples)  # type: ignore[arg-type]


class IsingEnumerationReferenceTests(unittest.TestCase):
    def test_two_spin_energy_and_probability_table_has_explicit_sign_convention(self) -> None:
        coupling = -math.log(3.0) / 2.0
        model = compile_ising(
            {"a": 0.0, "b": 0.0},
            {("a", "b"): coupling},
            offset=7.0,
            variables=("a", "b"),
        )

        result = enumerate_ising(model)

        self.assertEqual(result.variables, ("a", "b"))
        self.assertEqual(result.states, ((-1, -1), (-1, 1), (1, -1), (1, 1)))
        expected_energies = (
            7.0 + coupling,
            7.0 - coupling,
            7.0 - coupling,
            7.0 + coupling,
        )
        for actual, expected in zip(result.energies, expected_energies):
            self.assertAlmostEqual(actual, expected, places=15)
        for actual, expected in zip(result.probabilities, (0.375, 0.125, 0.125, 0.375)):
            self.assertAlmostEqual(actual, expected, places=15)

    def test_beta_zero_is_uniform_but_preserves_direct_energies(self) -> None:
        model = compile_ising(
            {"a": 0.25, "b": -0.5},
            {("a", "b"): 0.75},
            offset=1.25,
            variables=("a", "b"),
        )

        result = enumerate_ising(model, beta=0)

        self.assertEqual(result.states, ((-1, -1), (-1, 1), (1, -1), (1, 1)))
        self.assertEqual(result.energies, (2.25, -0.25, 1.25, 1.75))
        self.assertEqual(result.probabilities, (0.25, 0.25, 0.25, 0.25))

    def test_clamp_is_inserted_in_full_model_order_and_only_free_spins_are_enumerated(self) -> None:
        coupling = math.log(3.0) / 2.0
        model = compile_ising(
            {"a": 0.0, "b": 0.0, "c": 0.0},
            {("a", "b"): coupling},
            offset=-2.0,
            variables=("a", "b", "c"),
        )

        result = enumerate_ising(model, clamped={"b": 1})

        self.assertEqual(result.variables, ("a", "b", "c"))
        self.assertEqual(
            result.states,
            ((-1, 1, -1), (-1, 1, 1), (1, 1, -1), (1, 1, 1)),
        )
        for actual, expected in zip(result.probabilities, (0.375, 0.375, 0.125, 0.125)):
            self.assertAlmostEqual(actual, expected, places=15)
        self.assertAlmostEqual(result.energies[0], -2.0 - coupling, places=15)
        self.assertAlmostEqual(result.energies[2], -2.0 + coupling, places=15)

    def test_fully_clamped_model_has_one_directly_evaluated_state(self) -> None:
        model = compile_ising(
            {"a": 0.5, "b": -0.25},
            {("a", "b"): 0.75},
            offset=2.0,
            variables=("a", "b"),
        )

        result = enumerate_ising(model, clamped={"a": -1, "b": 1}, max_variables=0)

        self.assertEqual(result.states, ((-1, 1),))
        self.assertEqual(result.energies, (0.5,))
        self.assertEqual(result.probabilities, (1.0,))

    def test_free_spin_limit_is_eight_even_if_caller_requests_more(self) -> None:
        model = compile_ising({str(index): 0.0 for index in range(9)})

        with self.assertRaises(ValueError):
            enumerate_ising(model)
        with self.assertRaises(ValueError):
            enumerate_ising(model, max_variables=9)

        bounded = enumerate_ising(model, clamped={"0": 1})
        self.assertEqual(len(bounded.states), 256)
        self.assertTrue(all(state[0] == 1 for state in bounded.states))

    def test_invalid_beta_limit_and_clamps_fail_closed(self) -> None:
        model = compile_ising({"a": 0.0, "b": 0.0})
        invalid_calls = (
            {"beta": True},
            {"beta": -0.1},
            {"beta": math.nan},
            {"max_variables": True},
            {"max_variables": -1},
            {"clamped": {"unknown": 1}},
            {"clamped": {"a": True}},
            {"clamped": {"a": 1.0}},
            {"clamped": {"a": 0}},
        )
        for arguments in invalid_calls:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                enumerate_ising(model, **arguments)
        with self.assertRaises(ValueError):
            enumerate_ising(object())  # type: ignore[arg-type]

    def test_nonfinite_direct_energy_or_log_weight_is_rejected(self) -> None:
        overflowing_energy = compile_ising({"a": 1e308, "b": 1e308})
        overflowing_log_weight = compile_ising({"a": 1e308})

        with self.assertRaises(ValueError):
            enumerate_ising(overflowing_energy, beta=0.0)
        with self.assertRaises(ValueError):
            enumerate_ising(overflowing_log_weight, beta=1e308)


class FourParentConditionalReferenceTests(unittest.TestCase):
    def test_uniform_zero_field_joint_table_is_lexicographic_and_normalized(self) -> None:
        result = four_parent_conditional((0.0, 0.0, 0.0, 0.0))

        self.assertEqual(len(result.parent_states), 16)
        self.assertEqual(result.parent_states[0], (-1, -1, -1, -1))
        self.assertEqual(result.parent_states[-1], (1, 1, 1, 1))
        self.assertEqual(result.fields, (0.0,) * 16)
        self.assertEqual(result.probability_up, (0.5,) * 16)
        self.assertEqual(result.joint_probabilities, (0.03125,) * 32)
        self.assertEqual((result.mean, result.variance), (0.0, 1.0))

    def test_weight_order_and_bias_determine_endpoint_fields(self) -> None:
        result = four_parent_conditional((0.25, 0.125, 0.0625, 0.03125), bias=0.1)

        self.assertAlmostEqual(result.fields[0], -0.36875, places=15)
        self.assertAlmostEqual(result.fields[-1], 0.56875, places=15)
        self.assertAlmostEqual(result.probability_up[0], 0.3235510666515204, places=15)
        self.assertAlmostEqual(result.probability_up[-1], 0.75722034035404, places=15)

    def test_nonlinear_parent_mixture_averages_conditional_means(self) -> None:
        masses = [0.0] * 16
        masses[0] = 0.75
        masses[8] = 0.25

        result = four_parent_conditional((1.0, 0.0, 0.0, 0.0), parent_probabilities=masses)

        self.assertAlmostEqual(result.mean, -0.3807970779778824, places=15)
        self.assertAlmostEqual(result.variance, 0.8549935854035066, places=15)
        self.assertAlmostEqual(math.fsum(result.joint_probabilities), 1.0, places=15)
        self.assertNotAlmostEqual(result.mean, math.tanh(-0.5), places=6)

    def test_tiny_parent_mass_rounding_residual_is_normalized(self) -> None:
        masses = [1.0 / 16.0] * 16
        masses[-1] += 5e-13

        result = four_parent_conditional((0.0, 0.0, 0.0, 0.0), parent_probabilities=masses)

        self.assertAlmostEqual(math.fsum(result.joint_probabilities), 1.0, places=15)
        self.assertAlmostEqual(result.mean, 0.0, places=15)

    def test_invalid_weights_bias_and_parent_law_fail_closed(self) -> None:
        invalid_weight_calls = (
            ((0.0, 0.0, 0.0), {}),
            ((0.0, 0.0, 0.0, True), {}),
            ((0.0, 0.0, 0.0, math.inf), {}),
            ({0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}, {}),
            ({0.0, 1.0, 2.0, 3.0}, {}),
            ((0.0, 0.0, 0.0, 0.0), {"bias": True}),
            ((0.0, 0.0, 0.0, 0.0), {"bias": math.nan}),
        )
        for weights, arguments in invalid_weight_calls:
            with self.subTest(weights=weights, arguments=arguments), self.assertRaises(ValueError):
                four_parent_conditional(weights, **arguments)

        invalid_laws = (
            [1.0],
            [1.0 / 16.0] * 15 + [-1.0 / 16.0],
            [1.0 / 16.0] * 15 + [math.nan],
            [1.0 / 16.0] * 15 + [True],
            [1.0 / 16.0] * 15 + [1.0 / 16.0 + 2e-12],
            {index: 1.0 / 16.0 for index in range(16)},
            {float(index) for index in range(16)},
            [1e308] * 16,
        )
        for law in invalid_laws:
            with self.subTest(law=law), self.assertRaises(ValueError):
                four_parent_conditional((0.0, 0.0, 0.0, 0.0), parent_probabilities=law)

    def test_reference_records_are_immutable(self) -> None:
        result = spin_conditional(0.0)
        with self.assertRaises(FrozenInstanceError):
            result.mean = 1.0  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
