"""Brute-force equivalence of exact marginals and pair correlations."""

from __future__ import annotations

import itertools
import math
import random
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.conversions import compile_ising  # noqa: E402
from gibbsiq.exact_distribution import (  # noqa: E402
    compare_boltzmann_distributions,
    exact_boltzmann_distribution,
)


def random_model(rng: random.Random, size: int, *, zero_couplings: bool):
    variables = [f"v{index}" for index in range(size)]
    linear = {name: rng.uniform(-1.5, 1.5) for name in variables}
    quadratic = {}
    for left, right in itertools.combinations(variables, 2):
        quadratic[(left, right)] = 0.0 if zero_couplings else rng.uniform(-1.5, 1.5)
    return compile_ising(linear, quadratic, variables=variables)


def brute_force_marginals(distribution):
    rows = []
    for position in range(len(distribution.variables)):
        terms = [
            probability
            for state, probability in zip(distribution.states, distribution.probabilities)
            if state[position] == 1
        ]
        rows.append(math.fsum(terms))
    return rows


def brute_force_correlations(distribution):
    rows = []
    for left, right in itertools.combinations(range(len(distribution.variables)), 2):
        terms = [
            probability * state[left] * state[right]
            for state, probability in zip(distribution.states, distribution.probabilities)
        ]
        rows.append(math.fsum(terms))
    return rows


class ExactObservableEquivalenceTests(unittest.TestCase):
    def assert_observables_match(self, target, implemented, target_beta, implemented_beta):
        comparison = compare_boltzmann_distributions(
            target, implemented, target_beta=target_beta, implemented_beta=implemented_beta
        )
        target_law = exact_boltzmann_distribution(target, target_beta)
        implemented_law = exact_boltzmann_distribution(implemented, implemented_beta)
        marginals = comparison.marginal_errors
        self.assertEqual([row.target_probability_up for row in marginals], brute_force_marginals(target_law))
        self.assertEqual(
            [row.implemented_probability_up for row in marginals], brute_force_marginals(implemented_law)
        )
        pairs = comparison.pair_correlation_errors
        self.assertEqual([row.target_correlation for row in pairs], brute_force_correlations(target_law))
        self.assertEqual(
            [row.implemented_correlation for row in pairs], brute_force_correlations(implemented_law)
        )

    def test_random_models_match_brute_force(self) -> None:
        rng = random.Random(20260712)
        for size in (2, 3, 4, 5):
            for _ in range(6):
                target = random_model(rng, size, zero_couplings=False)
                implemented = random_model(rng, size, zero_couplings=False)
                self.assert_observables_match(
                    target, implemented, rng.uniform(0.1, 2.0), rng.uniform(0.1, 2.0)
                )

    def test_zero_couplings_match_brute_force(self) -> None:
        rng = random.Random(7)
        for size in (2, 3, 4, 5):
            target = random_model(rng, size, zero_couplings=True)
            implemented = random_model(rng, size, zero_couplings=True)
            self.assert_observables_match(target, implemented, 1.0, 0.5)

    def test_zero_beta_matches_brute_force(self) -> None:
        rng = random.Random(11)
        for size in (2, 3, 4, 5):
            target = random_model(rng, size, zero_couplings=False)
            implemented = random_model(rng, size, zero_couplings=False)
            self.assert_observables_match(target, implemented, 0.0, 0.0)
            self.assert_observables_match(target, implemented, 0.0, 1.3)

    def test_zero_variable_model_has_no_observable_rows(self) -> None:
        empty = compile_ising({})
        comparison = compare_boltzmann_distributions(empty, empty, target_beta=1.0, implemented_beta=1.0)
        self.assertEqual(comparison.marginal_errors, ())
        self.assertEqual(comparison.pair_correlation_errors, ())


if __name__ == "__main__":
    unittest.main()
