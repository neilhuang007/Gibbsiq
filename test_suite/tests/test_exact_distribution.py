"""Independent contracts for exact offset-free Boltzmann enumeration."""

from __future__ import annotations

import itertools
import json
import math
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.conversions import compile_ising  # noqa: E402
from gibbsiq.exact_distribution import (  # noqa: E402
    ExactDistributionNumericalError,
    compare_boltzmann_distributions,
    exact_boltzmann_distribution,
)


def independent_probabilities(model, beta: float):
    states = tuple(itertools.product((-1, 1), repeat=len(model.variables)))
    energies = [model.interaction_energy(dict(zip(model.variables, state))) for state in states]
    log_weights = [-beta * energy for energy in energies]
    shift = max(log_weights)
    weights = [math.exp(value - shift) for value in log_weights]
    normalization = math.fsum(weights)
    return states, tuple(weight / normalization for weight in weights)


class ExactBoltzmannTests(unittest.TestCase):
    def test_one_spin_matches_analytic_conditional(self) -> None:
        model = compile_ising({"s": 0.75}, offset=12.0)
        beta = 1.5
        result = exact_boltzmann_distribution(model, beta)
        probability_up = result.probabilities[result.states.index((1,))]
        expected = 1.0 / (1.0 + math.exp(2.0 * beta * 0.75))
        self.assertAlmostEqual(probability_up, expected, places=15)
        self.assertAlmostEqual(math.fsum(result.probabilities), 1.0, places=15)

    def test_beta_zero_is_uniform(self) -> None:
        model = compile_ising(
            {"a": 1e308, "b": -1e308},
            {("a", "b"): 1e308},
            offset=1e308,
        )
        result = exact_boltzmann_distribution(model, 0.0)
        self.assertEqual(result.probabilities, (0.25, 0.25, 0.25, 0.25))
        self.assertEqual(result.log_probabilities, (-math.log(4.0),) * 4)

    def test_large_offset_does_not_change_distribution(self) -> None:
        h = {"a": 0.25, "b": -0.5}
        J = {("a", "b"): 0.75}
        baseline = exact_boltzmann_distribution(compile_ising(h, J), 2.0)
        shifted = exact_boltzmann_distribution(
            compile_ising(h, J, offset=1e308),
            2.0,
        )
        self.assertEqual(baseline.probabilities, shifted.probabilities)
        self.assertEqual(baseline.log_probabilities, shifted.log_probabilities)

    def test_zero_variable_model_has_one_certain_state(self) -> None:
        result = exact_boltzmann_distribution(compile_ising({}, offset=-7.0), 3.0)
        self.assertEqual(result.states, ((),))
        self.assertEqual(result.probabilities, (1.0,))
        self.assertEqual(result.log_probabilities, (0.0,))

    def test_extreme_representable_span_reports_underflow_without_nonfinite_json(self) -> None:
        result = exact_boltzmann_distribution(compile_ising({"s": 1000.0}), 1.0)
        self.assertEqual(result.underflowed_probability_count, 1)
        json.dumps(result.to_dict(include_states=True), allow_nan=False)

    def test_unrepresentable_log_span_fails_before_nonfinite_evidence(self) -> None:
        with self.assertRaisesRegex(
            ExactDistributionNumericalError,
            "dynamic range exceeds binary64",
        ):
            exact_boltzmann_distribution(compile_ising({"s": 1e308}), 1.0)

    def test_unrepresentable_interaction_energy_uses_numerical_error_type(self) -> None:
        model = compile_ising({"a": 1e308, "b": 1e308})
        with self.assertRaisesRegex(
            ExactDistributionNumericalError,
            "energy or log weight exceeds binary64",
        ):
            exact_boltzmann_distribution(model, 1.0)

    def test_enumeration_limit_and_beta_validation(self) -> None:
        model = compile_ising({"a": 0.0, "b": 0.0})
        with self.assertRaisesRegex(ValueError, "exceeding"):
            exact_boltzmann_distribution(model, 1.0, max_variables=1)
        for beta in (-1.0, float("nan"), float("inf"), True):
            with self.subTest(beta=beta), self.assertRaises(ValueError):
                exact_boltzmann_distribution(model, beta)
        for limit in (-1, True, 1.5):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                exact_boltzmann_distribution(model, 1.0, max_variables=limit)  # type: ignore[arg-type]


class DistributionComparisonTests(unittest.TestCase):
    def test_identical_models_have_zero_error(self) -> None:
        model = compile_ising(
            {"a": 0.25, "b": -0.5},
            {("a", "b"): 0.75},
        )
        comparison = compare_boltzmann_distributions(
            model,
            model,
            target_beta=1.25,
            implemented_beta=1.25,
        )
        self.assertEqual(comparison.total_variation, 0.0)
        self.assertEqual(comparison.kl_target_to_implemented, 0.0)
        self.assertEqual(comparison.kl_implemented_to_target, 0.0)
        self.assertEqual(comparison.maximum_marginal_error, 0.0)
        self.assertEqual(comparison.maximum_pair_correlation_error, 0.0)

    def test_comparison_matches_independent_state_calculation(self) -> None:
        target = compile_ising(
            {"a": 0.3, "b": -0.2},
            {("a", "b"): 0.4},
        )
        implemented = compile_ising(
            {"a": 0.25, "b": -0.25},
            {("a", "b"): 0.5},
        )
        comparison = compare_boltzmann_distributions(
            target,
            implemented,
            target_beta=1.0,
            implemented_beta=1.0,
        )
        states, target_probabilities = independent_probabilities(target, 1.0)
        implemented_states, implemented_probabilities = independent_probabilities(
            implemented,
            1.0,
        )
        self.assertEqual(states, implemented_states)
        expected_tv = 0.5 * math.fsum(
            abs(left - right) for left, right in zip(target_probabilities, implemented_probabilities)
        )
        expected_target_kl = math.fsum(
            left * math.log(left / right)
            for left, right in zip(target_probabilities, implemented_probabilities)
        )
        self.assertAlmostEqual(comparison.total_variation, expected_tv, places=15)
        self.assertAlmostEqual(
            comparison.kl_target_to_implemented,
            expected_target_kl,
            places=15,
        )
        self.assertEqual(len(comparison.marginal_errors), 2)
        self.assertEqual(len(comparison.pair_correlation_errors), 1)
        json.dumps(comparison.to_dict(), allow_nan=False)

    def test_beta_energy_rescaling_preserves_distribution(self) -> None:
        model = compile_ising(
            {"a": 0.2, "b": -0.4},
            {("a", "b"): 0.6},
        )
        scaled = compile_ising(
            {"a": 0.4, "b": -0.8},
            {("a", "b"): 1.2},
        )
        comparison = compare_boltzmann_distributions(
            model,
            scaled,
            target_beta=2.0,
            implemented_beta=1.0,
        )
        self.assertLessEqual(comparison.total_variation, 1e-16)

    def test_rejects_wrong_model_types_and_variable_order(self) -> None:
        left = compile_ising({"a": 0.0, "b": 0.0}, variables=("a", "b"))
        right = compile_ising({"a": 0.0, "b": 0.0}, variables=("b", "a"))
        with self.assertRaisesRegex(ValueError, "variable order"):
            compare_boltzmann_distributions(
                left,
                right,
                target_beta=1.0,
                implemented_beta=1.0,
            )
        with self.assertRaisesRegex(TypeError, "target_model"):
            compare_boltzmann_distributions(  # type: ignore[arg-type]
                {}, left, target_beta=1.0, implemented_beta=1.0
            )
        with self.assertRaisesRegex(TypeError, "implemented_model"):
            compare_boltzmann_distributions(  # type: ignore[arg-type]
                left, {}, target_beta=1.0, implemented_beta=1.0
            )


if __name__ == "__main__":
    unittest.main()
