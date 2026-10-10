"""Independent exhaustive public seams for benchmark constraint encodings."""

from __future__ import annotations

import itertools
import math
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.constraints import compile_knapsack, compile_tsp  # noqa: E402


def direct_qubo_energy(encoding, bits: dict[object, int]) -> float:
    """Directly evaluate exposed QUBO coefficients outside production helpers."""
    return math.fsum(
        [encoding.qubo_offset]
        + [encoding.qubo_linear[variable] * bits[variable] for variable in encoding.variables]
        + [
            coefficient * bits[left] * bits[right]
            for (left, right), coefficient in encoding.qubo_quadratic.items()
        ]
    )


def native_knapsack(
    weights: tuple[int, ...], values: tuple[int, ...], bits: tuple[int, ...]
) -> tuple[int, int]:
    return (
        sum(value * bit for value, bit in zip(values, bits)),
        sum(weight * bit for weight, bit in zip(weights, bits)),
    )


class KnapsackLoweringTests(unittest.TestCase):
    """Source and slack enumeration prove the public knapsack seam."""

    def test_every_feasible_source_word_recovers_the_lexicographic_objective(self) -> None:
        weights = (2, 3, 4)
        values = (4, 5, 7)
        capacity = 5
        reward_scale = capacity + 1
        encoding = compile_knapsack(
            weights,
            values,
            capacity,
            penalty=max(reward_scale * value - weight for weight, value in zip(weights, values)) + 1,
            offset=-2.5,
        )

        self.assertEqual(encoding.penalty_policy.status, "proved_adequate")
        self.assertEqual(encoding.source_objective_map, "lexicographic_value_then_weight")
        self.assertEqual(encoding.overhead["slack_bit_count"], 3)
        self.assertEqual(encoding.overhead["source_offset"], -2.5)

        source_minimum = math.inf
        lowered_minimum = math.inf
        for item_bits in itertools.product((0, 1), repeat=len(weights)):
            value, weight = native_knapsack(weights, values, item_bits)
            source = dict(zip(encoding.item_variables, item_bits))
            energies = []
            for slack_bits in itertools.product((0, 1), repeat=len(encoding.slack_variables)):
                bits = {**source, **dict(zip(encoding.slack_variables, slack_bits))}
                energy = direct_qubo_energy(encoding, bits)
                energies.append(energy)
                spins = {variable: 2 * bit - 1 for variable, bit in bits.items()}
                self.assertEqual(encoding.ising_model.energy(bits, vartype="BINARY"), energy)
                self.assertEqual(encoding.ising_model.energy(spins), energy)
            lowered_minimum = min(lowered_minimum, min(energies))
            if weight <= capacity:
                source_energy = -2.5 - reward_scale * value + weight
                source_minimum = min(source_minimum, source_energy)
                self.assertEqual(min(energies), source_energy)
            else:
                self.assertGreater(min(energies), source_minimum)
        self.assertEqual(lowered_minimum, source_minimum)

    def test_slack_codec_covers_each_bounded_integer_and_rejects_invalid_words(self) -> None:
        for capacity, expected_weights in ((1, (1,)), (2, (1, 1)), (5, (1, 2, 2))):
            encoding = compile_knapsack((1,), (1,), capacity, penalty=1.0)
            self.assertEqual(encoding.slack_weights, expected_weights)
            reachable = {
                sum(weight * bit for weight, bit in zip(encoding.slack_weights, values))
                for values in itertools.product((0, 1), repeat=len(encoding.slack_variables))
            }
            self.assertEqual(reachable, set(range(capacity + 1)))

        encoding = compile_knapsack((2,), (2,), 1, penalty=3.0)
        invalid = {variable: 0 for variable in encoding.variables}
        invalid[encoding.item_variables[0]] = 1
        with self.assertRaises(ValueError):
            encoding.decode(invalid)
        with self.assertRaises(ValueError):
            compile_knapsack((1,), (1,), 1, penalty=True)

    def test_exact_knapsack_penalty_boundary_records_equal_and_below_as_unproved(self) -> None:
        # The documented equality counterexample: an infeasible word can tie
        # the empty feasible selection at P = M = 2.
        equal = compile_knapsack((2,), (2,), 1, penalty=2.0)
        below = compile_knapsack((2,), (2,), 1, penalty=0.0)
        above = compile_knapsack((2,), (2,), 1, penalty=2.000001)
        self.assertEqual(equal.penalty_policy.strict_boundary, 2.0)
        self.assertEqual(equal.penalty_policy.status, "not_proved_adequate")
        self.assertEqual(below.penalty_policy.status, "not_proved_adequate")
        self.assertEqual(above.penalty_policy.status, "proved_adequate")

        empty = {variable: 0 for variable in equal.variables}
        empty[equal.slack_variables[0]] = 1
        infeasible = {variable: 0 for variable in equal.variables}
        infeasible[equal.item_variables[0]] = 1
        self.assertEqual(direct_qubo_energy(equal, empty), 0.0)
        self.assertEqual(direct_qubo_energy(equal, infeasible), 0.0)

    def test_derived_penalty_is_strict_above_a_large_binary64_boundary(self) -> None:
        encoding = compile_knapsack((1,), (10**20,), 1)
        self.assertEqual(encoding.penalty_policy.selection, "derived_strict")
        self.assertGreater(
            encoding.penalty_policy.penalty,
            encoding.penalty_policy.strict_boundary,
        )
        self.assertEqual(encoding.penalty_policy.certificate_arithmetic, "exact")
        self.assertEqual(
            encoding.penalty_policy.finite_precision_guarantee,
            "not_universally_certified",
        )
        self.assertIn("exact arithmetic", encoding.penalty_policy.proof_scope)

    def test_redundant_slack_words_decode_to_the_same_native_selection(self) -> None:
        encoding = compile_knapsack((1,), (2,), 2)
        self.assertEqual(encoding.slack_weights, (1, 1))
        decoded = []
        energies = []
        for slack_bits in ((0, 1), (1, 0)):
            bits = {
                encoding.item_variables[0]: 1,
                **dict(zip(encoding.slack_variables, slack_bits)),
            }
            decoded.append(encoding.decode(bits))
            energies.append(direct_qubo_energy(encoding, bits))
        self.assertEqual(decoded, [(0,), (0,)])
        self.assertEqual(energies[0], energies[1])

    def test_item_permutation_preserves_native_and_lowered_energy_correspondence(self) -> None:
        weights = (1, 2, 3)
        values = (2, 5, 4)
        permutation = (2, 0, 1)
        original = compile_knapsack(weights, values, 3, offset=-1.25)
        permuted = compile_knapsack(
            tuple(weights[index] for index in permutation),
            tuple(values[index] for index in permutation),
            3,
            offset=-1.25,
        )

        for item_bits in itertools.product((0, 1), repeat=len(weights)):
            permuted_item_bits = tuple(item_bits[index] for index in permutation)
            self.assertEqual(
                native_knapsack(weights, values, item_bits),
                native_knapsack(permuted.weights, permuted.values, permuted_item_bits),
            )
            for slack_bits in itertools.product((0, 1), repeat=len(original.slack_variables)):
                original_bits = dict(zip(original.variables, item_bits + slack_bits))
                permuted_bits = dict(zip(permuted.variables, permuted_item_bits + slack_bits))
                self.assertEqual(
                    direct_qubo_energy(original, original_bits),
                    direct_qubo_energy(permuted, permuted_bits),
                )


def independent_one_hot_violation(bits: tuple[int, ...], city_count: int) -> int:
    return sum(
        (1 - sum(bits[city * city_count + position] for city in range(city_count))) ** 2
        for position in range(city_count)
    ) + sum(
        (1 - sum(bits[city * city_count + position] for position in range(city_count))) ** 2
        for city in range(city_count)
    )


def independent_tsp_length(matrix: tuple[tuple[int, ...], ...], tour: tuple[int, ...]) -> int:
    return sum(matrix[tour[position]][tour[(position + 1) % len(tour)]] for position in range(len(tour)))


class TspLoweringTests(unittest.TestCase):
    """Full tiny-bit enumeration pins one-hot and native-tour relations."""

    def test_valid_words_preserve_native_length_and_invalid_words_have_the_boundary_trap(self) -> None:
        matrix = (
            (0, 1, 0),
            (1, 0, 1),
            (0, 1, 0),
        )
        offset = 3.25
        encoding = compile_tsp(matrix, penalty=2.0, offset=offset)
        self.assertEqual(encoding.penalty_policy.strict_boundary, 1.0)
        self.assertEqual(encoding.penalty_policy.status, "proved_adequate")
        self.assertEqual(encoding.ancilla_variables, ())
        self.assertEqual(encoding.source_objective_map, "native_tour_length")

        valid_count = 0
        all_energies = []
        valid_energies = []
        for values in itertools.product((0, 1), repeat=len(encoding.variables)):
            bits = dict(zip(encoding.variables, values))
            violation = independent_one_hot_violation(values, 3)
            self.assertEqual(encoding.one_hot_violation(bits), violation)
            energy = direct_qubo_energy(encoding, bits)
            all_energies.append(energy)
            spins = {variable: 2 * bit - 1 for variable, bit in bits.items()}
            self.assertEqual(encoding.ising_model.energy(bits, vartype="BINARY"), energy)
            self.assertEqual(encoding.ising_model.energy(spins), energy)
            if violation == 0:
                tour = encoding.decode(bits)
                self.assertEqual(set(tour), {0, 1, 2})
                expected = offset + independent_tsp_length(matrix, tour)
                self.assertEqual(energy, expected)
                valid_energies.append(energy)
                valid_count += 1
            else:
                self.assertGreaterEqual(violation, 2)
        self.assertEqual(valid_count, math.factorial(3))
        self.assertEqual(min(all_energies), min(valid_energies))

        equal = compile_tsp(matrix, penalty=1.0, offset=offset)
        below = compile_tsp(matrix, penalty=math.nextafter(1.0, -math.inf), offset=offset)
        zero = compile_tsp(matrix, penalty=0.0, offset=offset)
        self.assertEqual(equal.penalty_policy.status, "not_proved_adequate")
        self.assertEqual(below.penalty_policy.status, "not_proved_adequate")
        self.assertEqual(zero.penalty_policy.status, "not_proved_adequate")

        canonical = {variable: 0 for variable in equal.variables}
        for city in range(3):
            canonical[equal.city_position_variables[city][city]] = 1
        invalid = {variable: 0 for variable in equal.variables}
        invalid[equal.city_position_variables[0][2]] = 1
        invalid[equal.city_position_variables[2][1]] = 1
        self.assertEqual(independent_one_hot_violation(tuple(invalid.values()), 3), 2)
        self.assertEqual(direct_qubo_energy(equal, invalid), direct_qubo_energy(equal, canonical))
        self.assertLess(direct_qubo_energy(zero, invalid), direct_qubo_energy(zero, canonical))
        with self.assertRaises(ValueError):
            equal.decode(invalid)

    def test_tsp_rejects_boolean_and_malformed_inputs(self) -> None:
        with self.assertRaises(ValueError):
            compile_tsp(((0, True, 1), (True, 0, 1), (1, 1, 0)), penalty=1.0)
        with self.assertRaises(ValueError):
            compile_tsp(((0, 1), (1, 0)), penalty=1.0)
        encoding = compile_tsp(((0, 1, 1), (1, 0, 1), (1, 1, 0)), penalty=2.0)
        with self.assertRaises(ValueError):
            encoding.native_length((0, True, 2))

    def test_city_relabeling_preserves_every_tour_length_and_lowered_energy(self) -> None:
        matrix = (
            (0, 2, 4),
            (2, 0, 3),
            (4, 3, 0),
        )
        permutation = (2, 0, 1)
        permuted_matrix = tuple(tuple(matrix[left][right] for right in permutation) for left in permutation)
        original = compile_tsp(matrix, offset=2.5)
        permuted = compile_tsp(permuted_matrix, offset=2.5)

        for tour in itertools.permutations(range(3)):
            permuted_tour = tuple(permutation.index(city) for city in tour)
            self.assertEqual(
                original.native_length(tour),
                permuted.native_length(permuted_tour),
            )
            original_bits = {variable: 0 for variable in original.variables}
            permuted_bits = {variable: 0 for variable in permuted.variables}
            for position, city in enumerate(tour):
                original_bits[original.city_position_variables[city][position]] = 1
            for position, city in enumerate(permuted_tour):
                permuted_bits[permuted.city_position_variables[city][position]] = 1
            self.assertEqual(
                direct_qubo_energy(original, original_bits),
                direct_qubo_energy(permuted, permuted_bits),
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
