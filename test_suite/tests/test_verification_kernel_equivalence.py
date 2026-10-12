"""Sparse kernel construction and histogram counting equal dense brute-force references."""

from __future__ import annotations

import itertools
import math
import random
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.exact_distribution import exact_boltzmann_distribution  # noqa: E402
from gibbsiq.model import IsingModel  # noqa: E402
from gibbsiq.verification import (  # noqa: E402
    build_exact_transition_kernel,
    verify_empirical_distribution,
    verify_transition_kernel,
)


def seeded_model(seed, size):
    rng = random.Random(seed)
    variables = tuple(f"x{index}" for index in range(size))
    linear = {variable: rng.choice([0.0, rng.uniform(-2.0, 2.0)]) for variable in variables}
    quadratic = {}
    for left, right in itertools.combinations(variables, 2):
        if rng.random() < 0.7:
            pair = (left, right) if rng.random() < 0.5 else (right, left)
            quadratic[pair] = rng.choice([0.0, rng.uniform(-3.0, 3.0), -rng.random()])
    return IsingModel(variables, linear, quadratic, offset=rng.uniform(-1.0, 1.0))


def reference_up(model, variable, state, beta):
    positions = {label: index for index, label in enumerate(model.variables)}
    terms = [model.linear[variable]]
    for (left, right), coefficient in model.quadratic.items():
        if left == variable:
            terms.append(coefficient * state[positions[right]])
        elif right == variable:
            terms.append(coefficient * state[positions[left]])
    gamma = math.fsum(terms)
    if beta == 0.0:
        return 0.5
    argument = -2.0 * beta * gamma
    if argument >= 0.0:
        return 1.0 / (1.0 + math.exp(-argument))
    exponential = math.exp(argument)
    return exponential / (1.0 + exponential)


def reference_block_matrix(model, states, beta, block):
    index = {state: row for row, state in enumerate(states)}
    positions = [model.variables.index(variable) for variable in block]
    matrix = []
    for state in states:
        ups = [reference_up(model, model.variables[position], state, beta) for position in positions]
        row = [0.0] * len(states)
        for assignment in itertools.product((-1, 1), repeat=len(positions)):
            probability = 1.0
            destination = list(state)
            for position, spin, up in zip(positions, assignment, ups):
                destination[position] = spin
                probability *= up if spin == 1 else 1.0 - up
            row[index[tuple(destination)]] += probability
        matrix.append(row)
    return matrix


def dense_product(left, right):
    size = len(left)
    return [
        [math.fsum(left[row][mid] * right[mid][col] for mid in range(size)) for col in range(size)]
        for row in range(size)
    ]


def reference_matrix(model, states, beta, schedule, blocks):
    size = len(states)
    singles = [reference_block_matrix(model, states, beta, (variable,)) for variable in model.variables]
    if schedule == "random_single_site":
        weight = 1.0 / len(singles)
        return [
            [math.fsum(site[row][col] for site in singles) * weight for col in range(size)]
            for row in range(size)
        ]
    if schedule == "systematic":
        factors = singles
    else:
        factors = [reference_block_matrix(model, states, beta, block) for block in blocks]
    matrix = [[1.0 if row == col else 0.0 for col in range(size)] for row in range(size)]
    for factor in factors:
        matrix = dense_product(matrix, factor)
    return matrix


class KernelEquivalenceTests(unittest.TestCase):
    def test_kernel_equals_dense_reference_for_every_schedule(self):
        for size in (2, 3, 4, 5):
            for seed in range(3):
                model = seeded_model(100 * size + seed, size)
                for beta in (0.0, 0.7, 3.0):
                    for schedule in ("random_single_site", "systematic", "blocked"):
                        kernel = build_exact_transition_kernel(model, beta, update_schedule=schedule)
                        expected = reference_matrix(model, kernel.states, beta, schedule, kernel.blocks)
                        with self.subTest(size=size, seed=seed, beta=beta, schedule=schedule):
                            self.assertEqual([list(row) for row in kernel.matrix], expected)

    def test_user_supplied_blocks_equal_dense_reference(self):
        model = IsingModel(
            ("x0", "x1", "x2", "x3"),
            {"x0": 0.4, "x1": -0.3, "x2": 0.0, "x3": 0.9},
            {("x0", "x1"): 1.2, ("x2", "x1"): -0.7, ("x2", "x3"): 0.5, ("x3", "x0"): -1.1},
        )
        blocks = (("x0", "x2"), ("x1", "x3"))
        kernel = build_exact_transition_kernel(model, 1.3, update_schedule="blocked", blocks=blocks)
        expected = reference_matrix(model, kernel.states, 1.3, "blocked", kernel.blocks)
        self.assertEqual([list(row) for row in kernel.matrix], expected)

    def test_kernel_rows_stay_stochastic_and_verified(self):
        model = seeded_model(11, 5)
        kernel = build_exact_transition_kernel(model, 1.1, update_schedule="systematic")
        for row in kernel.matrix:
            self.assertAlmostEqual(math.fsum(row), 1.0, places=12)
            self.assertGreaterEqual(min(row), 0.0)
        self.assertTrue(verify_transition_kernel(model, 1.1, kernel).passed)


def brute_force_intervals(model, samples, beta, confidence=0.99):
    exact = exact_boltzmann_distribution(model, beta)
    spins = [tuple(sample[variable] for variable in model.variables) for sample in samples]
    count = len(spins)
    size = len(model.variables)
    observables = []
    for position in range(size):
        target = math.fsum(p for state, p in zip(exact.states, exact.probabilities) if state[position] == 1)
        estimate = math.fsum(state[position] == 1 for state in spins) / count
        observables.append((f"probability_up:{position}", target, estimate, 0.0, 1.0))
    for left, right in itertools.combinations(range(size), 2):
        target = math.fsum(
            p * state[left] * state[right] for state, p in zip(exact.states, exact.probabilities)
        )
        estimate = math.fsum(state[left] * state[right] for state in spins) / count
        observables.append((f"pair_correlation:{left},{right}", target, estimate, -1.0, 1.0))
    exact_energies = [model.energy(dict(zip(model.variables, state))) for state in exact.states]
    sample_energies = [model.energy(dict(zip(model.variables, state))) for state in spins]
    for energy in sorted(set(exact_energies)):
        target = math.fsum(p for e, p in zip(exact_energies, exact.probabilities) if e == energy)
        estimate = math.fsum(e == energy for e in sample_energies) / count
        observables.append((f"energy_probability:{energy!r}", target, estimate, 0.0, 1.0))
    for index, (state, target) in enumerate(zip(exact.states, exact.probabilities)):
        estimate = math.fsum(s == state for s in spins) / count
        observables.append((f"state_probability:{index}:{state!r}", target, estimate, 0.0, 1.0))
    total = len(observables)
    alpha = 1.0 - confidence
    intervals = []
    for name, target, estimate, low, high in observables:
        span = high - low
        half = span * math.sqrt(math.log(2.0 * total / alpha) / (2.0 * count))
        lower = max(low, estimate - half)
        upper = min(high, estimate + half)
        intervals.append(
            {
                "observable": name,
                "target": target,
                "estimate": estimate,
                "lower": lower,
                "upper": upper,
                "half_width": half,
                "covered": lower <= target <= upper,
                "informative": half < span,
            }
        )
    return intervals


class EmpiricalEquivalenceTests(unittest.TestCase):
    def test_empirical_report_equals_brute_force_intervals(self):
        for size in (2, 3, 4, 5):
            model = seeded_model(900 + size, size)
            rng = random.Random(size)
            samples = [{v: rng.choice([-1, 1]) for v in model.variables} for _ in range(200)]
            for beta in (0.0, 1.0, 2.5):
                report = verify_empirical_distribution(model, samples, beta).to_dict()
                with self.subTest(size=size, beta=beta):
                    self.assertEqual(report["intervals"], brute_force_intervals(model, samples, beta))
                    self.assertEqual(report["num_comparisons"], len(report["intervals"]))

    def test_signed_zero_energies_share_one_bucket(self):
        model = IsingModel(("a", "b"), {"a": 0.0, "b": -0.0}, {("a", "b"): 0.0})
        samples = [{"a": 1, "b": -1}, {"a": -1, "b": -1}, {"a": 1, "b": 1}]
        report = verify_empirical_distribution(model, samples, 1.0).to_dict()
        self.assertEqual(report["intervals"], brute_force_intervals(model, samples, 1.0))


if __name__ == "__main__":
    unittest.main()
