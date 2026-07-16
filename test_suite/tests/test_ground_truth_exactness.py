"""Independent exhaustive checks for every benchmark optimum, via a third enumerator
separate from the generator and the oracle."""

from __future__ import annotations

import itertools
import json
import math
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = REPO_ROOT / "reference" / "06-benchmarks" / "fixtures" / "ground-truth-small.json"


def load_fixtures() -> list[dict]:
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8-sig"))["fixtures"]


def spin_vectors(n: int):
    return itertools.product((-1, 1), repeat=n)


def binary_vectors(n: int):
    return itertools.product((0, 1), repeat=n)


def maxcut_exact(model: dict) -> dict:
    variables = model["variables"]
    edges = [(variables.index(left), variables.index(right)) for left, right in model["edges"]]
    best_cut = -1
    degeneracy = 0
    for spins in spin_vectors(len(variables)):
        cut = sum(1 for left, right in edges if spins[left] != spins[right])
        if cut > best_cut:
            best_cut = cut
            degeneracy = 1
        elif cut == best_cut:
            degeneracy += 1
    best_energy = len(edges) - 2 * best_cut
    return {
        "num_nodes": len(variables),
        "num_edges": len(edges),
        "best_cut_value": best_cut,
        "best_ising_energy": float(best_energy),
        "ground_state_degeneracy": degeneracy,
    }


def partition_exact(model: dict) -> dict:
    numbers = model["numbers"]
    best_diff = math.inf
    degeneracy = 0
    for signs in spin_vectors(len(numbers)):
        diff = abs(sum(number * sign for number, sign in zip(numbers, signs)))
        if diff < best_diff:
            best_diff = diff
            degeneracy = 1
        elif diff == best_diff:
            degeneracy += 1
    return {
        "min_subset_sum_difference": best_diff,
        "best_ising_energy": float(best_diff * best_diff),
        "ground_state_degeneracy": degeneracy,
        "is_perfect_partition": best_diff == 0,
    }


def knapsack_exact(model: dict) -> dict:
    weights = model["weights"]
    values = model["values"]
    capacity = model["capacity"]
    best_value = 0
    best_weight = 0
    degeneracy = 0
    for bits in binary_vectors(len(weights)):
        weight = sum(weight * bit for weight, bit in zip(weights, bits))
        if weight > capacity:
            continue
        value = sum(value * bit for value, bit in zip(values, bits))
        if value > best_value or (value == best_value and weight < best_weight):
            best_value = value
            best_weight = weight
            degeneracy = 1
        elif value == best_value and weight == best_weight:
            degeneracy += 1
    return {
        "max_value": best_value,
        "weight_at_optimum": best_weight,
        "capacity": capacity,
        "num_optimal_selections": degeneracy,
    }


def tsp_exact(model: dict) -> dict:
    distance = model["distance_matrix"]
    n = model["num_cities"]
    best_length = math.inf
    degeneracy = 0
    for suffix in itertools.permutations(range(1, n)):
        if n > 2 and suffix[0] > suffix[-1]:
            continue
        tour = (0,) + suffix
        length = sum(distance[tour[i]][tour[(i + 1) % n]] for i in range(n))
        if length < best_length:
            best_length = length
            degeneracy = 1
        elif length == best_length:
            degeneracy += 1
    return {
        "num_cities": n,
        "optimal_tour_length": best_length,
        "num_optimal_tours": degeneracy,
    }


def sk_exact(model: dict) -> dict:
    variables = model["variables"]
    best_energy = math.inf
    degeneracy = 0
    quadratic = []
    for pair, coupling in model["quadratic"].items():
        left, right = pair.split(",")
        quadratic.append((variables.index(left), variables.index(right), coupling))
    for spins in spin_vectors(len(variables)):
        energy = sum(float(model["linear"][var]) * spins[index] for index, var in enumerate(variables))
        energy += sum(coupling * spins[left] * spins[right] for left, right, coupling in quadratic)
        if energy < best_energy:
            best_energy = energy
            degeneracy = 1
        elif energy == best_energy:
            degeneracy += 1
    return {
        "num_spins": len(variables),
        "ground_state_energy": float(best_energy),
        "ground_state_degeneracy": degeneracy,
    }


FAMILY_SOLVERS = {
    "maxcut": maxcut_exact,
    "number_partition": partition_exact,
    "knapsack": knapsack_exact,
    "tsp": tsp_exact,
    "sk_spin_glass": sk_exact,
}


class GroundTruthExactnessTest(unittest.TestCase):
    def test_benchmark_scalars_match_independent_enumeration(self) -> None:
        for fixture in load_fixtures():
            expected = fixture["expected"]
            actual = FAMILY_SOLVERS[fixture["family"]](fixture["input"])
            with self.subTest(fixture=fixture["id"]):
                for key, value in actual.items():
                    self.assertEqual(value, expected[key])

    def test_stored_witnesses_are_representative(self) -> None:
        # The corpus caps serialized witnesses; degeneracy is the exact count, and
        # witness lists only provide enough examples to verify, not a full state table.
        for fixture in load_fixtures():
            expected = fixture["expected"]
            witness_key = next(key for key in expected if key.startswith("witness_"))
            degeneracy_key = next(
                key
                for key in (
                    "ground_state_degeneracy",
                    "num_optimal_selections",
                    "num_optimal_tours",
                )
                if key in expected
            )
            with self.subTest(fixture=fixture["id"]):
                self.assertLessEqual(len(expected[witness_key]), expected[degeneracy_key])
                self.assertLessEqual(len(expected[witness_key]), 8)


if __name__ == "__main__":
    unittest.main()
