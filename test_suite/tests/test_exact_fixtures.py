"""Independent checks for the exact public evaluation fixtures.

These tests recompute the tiny fixture values from first principles instead of
calling the evaluator. They are intentionally small and deterministic: the goal
is to pin down signs, offsets, probabilities, and Max-Cut objective mapping
before any solver implementation exists.
"""

from __future__ import annotations

import itertools
import json
import math
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


def load_exact() -> dict[str, dict]:
    path = REPO_ROOT / "reference" / "08-evaluation" / "fixtures" / "exact-small-instances.json"
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return {fixture["id"]: fixture for fixture in payload["fixtures"]}


def spin_assignments(variables: list[str]):
    for values in itertools.product((-1, 1), repeat=len(variables)):
        yield dict(zip(variables, values))


def binary_from_spin(spins: dict[str, int]) -> dict[str, int]:
    return {variable: (spin + 1) // 2 for variable, spin in spins.items()}


def pair_key(left: str, right: str) -> str:
    return f"{left},{right}"


def qubo_energy(model: dict, bits: dict[str, int]) -> float:
    energy = float(model.get("offset", 0.0))
    for variable, coefficient in model.get("linear", {}).items():
        energy += float(coefficient) * bits[variable]
    for pair, coefficient in model.get("quadratic", {}).items():
        left, right = pair.split(",")
        energy += float(coefficient) * bits[left] * bits[right]
    return energy


def ising_energy(model: dict, spins: dict[str, int]) -> float:
    energy = float(model.get("offset", 0.0))
    for variable, coefficient in model.get("linear", {}).items():
        energy += float(coefficient) * spins[variable]
    for pair, coefficient in model.get("quadratic", {}).items():
        left, right = pair.split(",")
        energy += float(coefficient) * spins[left] * spins[right]
    return energy


def convert_upper_triangle_qubo_to_ising(model: dict) -> dict:
    variables = list(model["variables"])
    linear = {variable: float(model.get("linear", {}).get(variable, 0.0)) / 2.0 for variable in variables}
    quadratic = {}
    offset = float(model.get("offset", 0.0))

    for variable in variables:
        offset += float(model.get("linear", {}).get(variable, 0.0)) / 2.0

    for pair, coefficient in model.get("quadratic", {}).items():
        left, right = pair.split(",")
        q = float(coefficient)
        quadratic[pair_key(left, right)] = q / 4.0
        linear[left] += q / 4.0
        linear[right] += q / 4.0
        offset += q / 4.0

    return {
        "variables": variables,
        "linear": linear,
        "quadratic": quadratic,
        "offset": offset,
    }


def maxcut_value(edges: list[list[str]], spins: dict[str, int]) -> int:
    return sum(1 for left, right in edges if spins[left] != spins[right])


class ExactFixtureMathTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixtures = load_exact()

    def test_qubo_two_var_conversion_and_energy_table(self) -> None:
        fixture = self.fixtures["qubo_two_var_offset_conversion"]
        model = fixture["input"]
        expected = fixture["expected"]

        converted = convert_upper_triangle_qubo_to_ising(model)
        self.assertEqual(converted["variables"], expected["ising_ir"]["variables"])
        self.assertEqual(converted["linear"], expected["ising_ir"]["linear"])
        self.assertEqual(converted["quadratic"], expected["ising_ir"]["quadratic"])
        self.assertEqual(converted["offset"], expected["ising_ir"]["offset"])

        rows = []
        best_energy = math.inf
        best_bits = []
        for spins in spin_assignments(model["variables"]):
            bits = binary_from_spin(spins)
            q_energy = qubo_energy(model, bits)
            i_energy = ising_energy(converted, spins)
            self.assertAlmostEqual(q_energy, i_energy, places=12)
            rows.append({"binary": bits, "spin": spins, "energy": q_energy})
            if q_energy < best_energy:
                best_energy = q_energy
                best_bits = [bits]
            elif q_energy == best_energy:
                best_bits.append(bits)

        self.assertCountEqual(rows, expected["energy_table"])
        self.assertEqual(best_energy, expected["best_energy"])
        self.assertCountEqual(best_bits, expected["best_binary_samples"])
        self.assertEqual(len(best_bits), expected["ground_state_degeneracy"])

    def test_two_spin_boltzmann_probabilities(self) -> None:
        fixture = self.fixtures["two_spin_ferromagnetic_boltzmann_beta1"]
        model = fixture["input"]
        expected = fixture["expected"]
        beta = float(model["beta"])

        energy_rows = []
        weights = []
        for spins in spin_assignments(model["variables"]):
            energy = ising_energy(model, spins)
            weight = math.exp(-beta * energy)
            weights.append(weight)
            energy_rows.append({"spin": spins, "energy": energy})

        partition = sum(weights)
        self.assertAlmostEqual(partition, expected["partition_function"], places=12)

        rows_with_probabilities = []
        for row, weight in zip(energy_rows, weights):
            rows_with_probabilities.append({**row, "probability": weight / partition})

        for actual, expected_row in zip(rows_with_probabilities, expected["energy_table"]):
            self.assertEqual(actual["spin"], expected_row["spin"])
            self.assertEqual(actual["energy"], expected_row["energy"])
            self.assertAlmostEqual(actual["probability"], expected_row["probability"], places=12)

        self.assertAlmostEqual(
            sum(row["probability"] for row in rows_with_probabilities), 1.0, places=12
        )
        best_energy = min(row["energy"] for row in rows_with_probabilities)
        self.assertEqual(best_energy, expected["best_energy"])
        self.assertEqual(
            sum(1 for row in rows_with_probabilities if row["energy"] == best_energy),
            expected["ground_state_degeneracy"],
        )

    def test_single_site_conditional_sign(self) -> None:
        fixture = self.fixtures["single_site_conditional_sign"]
        model = fixture["input"]
        expected = fixture["expected"]
        beta = float(model["beta"])

        def probability(neighbor_spin: int) -> tuple[float, float]:
            gamma = model["h_target"] + model["coupling_to_neighbor"] * neighbor_spin
            return gamma, 1.0 / (1.0 + math.exp(2.0 * beta * gamma))

        gamma, prob = probability(1)
        self.assertEqual(gamma, expected["when_neighbor_s1_is_plus_1"]["gamma"])
        self.assertAlmostEqual(
            prob, expected["when_neighbor_s1_is_plus_1"]["p_s0_plus_1"], places=12
        )

        gamma, prob = probability(-1)
        self.assertEqual(gamma, expected["when_neighbor_s1_is_minus_1"]["gamma"])
        self.assertAlmostEqual(
            prob, expected["when_neighbor_s1_is_minus_1"]["p_s0_plus_1"], places=12
        )

    def test_maxcut_tiny_graphs_are_exhaustively_correct(self) -> None:
        for fixture_id in ("maxcut_triangle_unweighted", "maxcut_cycle4_unweighted"):
            fixture = self.fixtures[fixture_id]
            model = fixture["input"]
            expected = fixture["expected"]
            edges = model["edges"]

            best_cut = -1
            best_energy = math.inf
            best_spins = []
            for spins in spin_assignments(model["variables"]):
                cut = maxcut_value(edges, spins)
                energy = sum(spins[left] * spins[right] for left, right in edges)
                self.assertEqual(cut, (len(edges) - energy) // 2)
                if cut > best_cut:
                    best_cut = cut
                    best_energy = energy
                    best_spins = [spins]
                elif cut == best_cut:
                    best_spins.append(spins)

            self.assertEqual(len(edges), expected["num_edges"])
            self.assertEqual(best_cut, expected["best_cut_value"])
            self.assertEqual(best_energy, expected["best_ising_energy"])
            self.assertCountEqual(best_spins, expected["best_spin_samples"])
            self.assertEqual(len(best_spins), expected["ground_state_degeneracy"])


if __name__ == "__main__":
    unittest.main()
