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


FOUR_CITY_MATRIX = (
    (0, 2, 9, 10),
    (2, 0, 6, 4),
    (9, 6, 0, 3),
    (10, 4, 3, 0),
)


def four_city_word(tour: tuple[int, ...]) -> int:
    """Pack a tour into a 16-bit word with bit city * 4 + position set per stop."""
    return sum(1 << (city * 4 + position) for position, city in enumerate(tour))


def four_city_word_bits(encoding, word: int) -> dict[object, int]:
    return {variable: (word >> index) & 1 for index, variable in enumerate(encoding.variables)}


def four_city_energies(
    matrix: tuple[tuple[int, ...], ...], *, penalty: float, objective_scale: float, offset: float
) -> list[float]:
    """Definitional energy of every 16-bit word via nibble tables, without QUBO coefficients."""
    size = 4
    violation = [(1 - bin(nibble).count("1")) ** 2 for nibble in range(16)]
    pair_length = [
        [
            sum(matrix[c][d] for c in range(size) if (a >> c) & 1 for d in range(size) if (b >> d) & 1)
            for b in range(16)
        ]
        for a in range(16)
    ]

    def transpose(word: int) -> int:
        return sum(
            1 << (position * 4 + city)
            for city in range(size)
            for position in range(size)
            if (word >> (city * 4 + position)) & 1
        )

    transpose_low = [transpose(byte) for byte in range(256)]
    transpose_high = [transpose(byte << 8) for byte in range(256)]
    energies = []
    for word in range(1 << 16):
        by_position = transpose_low[word & 255] | transpose_high[word >> 8]
        p0, p1, p2, p3 = by_position & 15, (by_position >> 4) & 15, (by_position >> 8) & 15, by_position >> 12
        c0, c1, c2, c3 = word & 15, (word >> 4) & 15, (word >> 8) & 15, word >> 12
        one_hot = (
            violation[p0]
            + violation[p1]
            + violation[p2]
            + violation[p3]
            + violation[c0]
            + violation[c1]
            + violation[c2]
            + violation[c3]
        )
        length = pair_length[p0][p1] + pair_length[p1][p2] + pair_length[p2][p3] + pair_length[p3][p0]
        energies.append(offset + penalty * one_hot + objective_scale * length)
    return energies


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

    def test_four_city_ground_state_is_the_shortest_tour(self) -> None:
        matrix = FOUR_CITY_MATRIX
        offset = 1.5
        cycle_lengths = {
            tour: independent_tsp_length(matrix, tour) for tour in itertools.permutations(range(4))
        }
        self.assertEqual(set(cycle_lengths.values()), {18, 21, 29})
        self.assertEqual(cycle_lengths[(0, 1, 3, 2)], 18)
        self.assertEqual(cycle_lengths[(0, 1, 2, 3)], 21)
        self.assertEqual(cycle_lengths[(0, 2, 1, 3)], 29)

        encoding = compile_tsp(matrix, penalty=None, offset=offset)
        policy = encoding.penalty_policy
        self.assertEqual(policy.selection, "derived_strict")
        self.assertEqual(policy.status, "proved_adequate")
        self.assertEqual(policy.strict_boundary, 10.5)
        self.assertEqual(policy.penalty, 11.0)

        energies = four_city_energies(matrix, penalty=11.0, objective_scale=1.0, offset=offset)
        minimum = min(energies)
        self.assertEqual(minimum, offset + 18)
        argmin = {word for word, energy in enumerate(energies) if energy == minimum}
        rotations = {(0, 1, 3, 2)[shift:] + (0, 1, 3, 2)[:shift] for shift in range(4)}
        expected_tours = rotations | {tour[::-1] for tour in rotations}
        self.assertEqual(len(expected_tours), 8)
        self.assertEqual(argmin, {four_city_word(tour) for tour in expected_tours})
        for word in argmin:
            self.assertIn(encoding.decode(four_city_word_bits(encoding, word)), expected_tours)

        valid_words = {four_city_word(tour): tour for tour in cycle_lengths}
        self.assertEqual(len(valid_words), 24)
        for word, tour in valid_words.items():
            bits = four_city_word_bits(encoding, word)
            self.assertEqual(encoding.decode(bits), tour)
            self.assertEqual(energies[word], offset + cycle_lengths[tour])
            self.assertEqual(direct_qubo_energy(encoding, bits), energies[word])
            self.assertEqual(encoding.ising_model.energy(bits, vartype="BINARY"), energies[word])
        for word, energy in enumerate(energies):
            if word not in valid_words:
                self.assertGreater(energy, offset + 18)

        low_weight_words = [
            sum(1 << index for index in chosen)
            for count in range(4)
            for chosen in itertools.combinations(range(16), count)
        ]
        self.assertEqual(len(low_weight_words), 697)
        for word in low_weight_words:
            bits = four_city_word_bits(encoding, word)
            self.assertEqual(direct_qubo_energy(encoding, bits), energies[word])
            violation = independent_one_hot_violation(tuple(bits.values()), 4)
            self.assertEqual(violation == 0, word in valid_words)

    def test_four_city_under_penalty_yields_an_invalid_ground_state(self) -> None:
        encoding = compile_tsp(FOUR_CITY_MATRIX, penalty=5.0)
        self.assertEqual(encoding.penalty_policy.status, "not_proved_adequate")

        energies = four_city_energies(FOUR_CITY_MATRIX, penalty=5.0, objective_scale=1.0, offset=0.0)
        minimum = min(energies)
        argmin = [word for word, energy in enumerate(energies) if energy == minimum]
        self.assertGreaterEqual(len(argmin), 1)
        for word in argmin:
            bits = four_city_word_bits(encoding, word)
            self.assertGreater(independent_one_hot_violation(tuple(bits.values()), 4), 0)
            with self.assertRaises(ValueError):
                encoding.decode(bits)
        shortest_valid = min(energies[four_city_word(tour)] for tour in itertools.permutations(range(4)))
        self.assertLess(minimum, shortest_valid)

    def test_tsp_rejects_asymmetric_negative_and_nonzero_diagonal_matrices(self) -> None:
        with self.assertRaises(ValueError):
            compile_tsp(((0, 1, 2), (3, 0, 1), (2, 1, 0)), penalty=2.0)
        with self.assertRaises(ValueError):
            compile_tsp(((0, -1, 2), (-1, 0, 1), (2, 1, 0)), penalty=2.0)
        with self.assertRaises(ValueError):
            compile_tsp(((1, 1, 2), (1, 0, 1), (2, 1, 0)), penalty=2.0)
        symmetric = ((0, 1, 2), (1, 0, 1), (2, 1, 0))
        for scale in (0.0, -1.0):
            with self.assertRaises(ValueError):
                compile_tsp(symmetric, penalty=2.0, objective_scale=scale)


def enumerate_knapsack_words(encoding, weights, values):
    """Yield (sample, selection, value, weight, slack, lowered_energy) for every word."""
    count = len(weights)
    for word in range(1 << len(encoding.variables)):
        bits = tuple((word >> position) & 1 for position in range(len(encoding.variables)))
        selection = tuple(index for index in range(count) if bits[index])
        slack = sum(w * b for w, b in zip(encoding.slack_weights, bits[count:]))
        sample = dict(zip(encoding.variables, bits))
        yield (
            sample,
            selection,
            sum(values[index] for index in selection),
            sum(weights[index] for index in selection),
            slack,
            direct_qubo_energy(encoding, sample),
        )


def brute_force_feasible(weights, values, capacity):
    """Map each capacity-feasible selection to (value, weight)."""
    feasible = {}
    for mask in range(1 << len(weights)):
        selection = tuple(i for i in range(len(weights)) if (mask >> i) & 1)
        weight = sum(weights[i] for i in selection)
        if weight <= capacity:
            feasible[selection] = (sum(values[i] for i in selection), weight)
    return feasible


class KnapsackExhaustiveTests(unittest.TestCase):
    """Brute-force oracles computed from problem data under the derived penalty."""

    WEIGHTS = (3, 4, 2, 5)
    VALUES = (5, 6, 3, 9)
    CAPACITY = 7

    def test_derived_penalty_ground_state(self) -> None:
        encoding = compile_knapsack(self.WEIGHTS, self.VALUES, self.CAPACITY)
        self.assertEqual(encoding.penalty_policy.selection, "derived_strict")
        self.assertEqual(encoding.penalty_policy.status, "proved_adequate")
        feasible = brute_force_feasible(self.WEIGHTS, self.VALUES, self.CAPACITY)
        top = max(value for value, _ in feasible.values())
        optima = [selection for selection, (value, _) in feasible.items() if value == top]
        self.assertEqual((top, optima), (12, [(2, 3)]))
        reward = self.CAPACITY + 1
        feasible_minimum = min(-reward * value + weight for value, weight in feasible.values())
        rows = list(enumerate_knapsack_words(encoding, self.WEIGHTS, self.VALUES))
        self.assertEqual(len(rows), 1 << 7)
        self.assertEqual(min(row[5] for row in rows), feasible_minimum)
        argmin = [row for row in rows if row[5] == feasible_minimum]
        self.assertEqual(len(argmin), 1)
        self.assertEqual(argmin[0][1], (2, 3))
        self.assertEqual(encoding.decode(argmin[0][0]), (2, 3))
        for sample, _, value, weight, slack, lowered in rows:
            if weight + slack == self.CAPACITY:
                self.assertEqual(lowered, -reward * value + weight)
                continue
            self.assertGreater(lowered, feasible_minimum)
            self.assertFalse(encoding.is_valid(sample))

    def test_tied_optima_decode_to_both_selections(self) -> None:
        weights, values, capacity = (3, 3, 5), (4, 4, 3), 5
        encoding = compile_knapsack(weights, values, capacity)
        self.assertEqual(encoding.slack_weights, (1, 2, 2))
        feasible = brute_force_feasible(weights, values, capacity)
        top = max(value for value, _ in feasible.values())
        optima = {selection for selection, (value, _) in feasible.items() if value == top}
        self.assertEqual(optima, {(0,), (1,)})
        rows = list(enumerate_knapsack_words(encoding, weights, values))
        minimum = min(row[5] for row in rows)
        argmin = [row for row in rows if row[5] == minimum]
        self.assertEqual({row[1] for row in argmin}, optima)
        # Each tied selection needs slack 2, encoded as (0, 1, 0) or (0, 0, 1).
        self.assertEqual(len(argmin), 2 * 2)
        self.assertEqual({encoding.decode(row[0]) for row in argmin}, optima)
        argmin_ids = {id(row) for row in argmin}
        for row in rows:
            if id(row) not in argmin_ids:
                self.assertGreater(row[5], minimum)

    def test_item_data_validation(self) -> None:
        invalid_cases = (
            ((1, 2), (1,), 3),
            ((1,), (1, 2), 3),
            ((), (), 3),
            ((1,), (1,), 0),
            ((1,), (1,), -2),
            ((1,), (1,), True),
            ((1,), (1,), 2.0),
            ((True,), (1,), 2),
            ((1,), (True,), 2),
            ((-1,), (1,), 2),
            ((1,), (-1,), 2),
            ((0,), (1,), 2),
            ((1,), (0,), 2),
            ((1.0,), (1,), 2),
        )
        for weights, values, capacity in invalid_cases:
            with self.subTest(weights=weights, values=values, capacity=capacity):
                with self.assertRaises(ValueError):
                    compile_knapsack(weights, values, capacity)

    def test_penalty_and_offset_validation(self) -> None:
        for penalty in (-1.0, math.inf, math.nan, True):
            with self.subTest(penalty=penalty):
                with self.assertRaises(ValueError):
                    compile_knapsack((1,), (1,), 1, penalty=penalty)
        for offset in (True, math.inf, math.nan):
            with self.subTest(offset=offset):
                with self.assertRaises(ValueError):
                    compile_knapsack((1,), (1,), 1, offset=offset)

    def test_decoder_rejects_malformed_words(self) -> None:
        encoding = compile_knapsack((2, 3), (3, 4), 4)
        valid = dict.fromkeys(encoding.variables, 0)
        valid[encoding.item_variables[0]] = 1
        valid[encoding.slack_variables[1]] = 1
        self.assertEqual(encoding.decode(valid), (0,))
        short = dict(valid)
        del short[encoding.slack_variables[-1]]
        out_of_range = {**valid, encoding.item_variables[1]: 2}
        boolean = {**valid, encoding.item_variables[1]: True}
        overweight = dict.fromkeys(encoding.variables, 0)
        overweight[encoding.item_variables[0]] = 1
        overweight[encoding.item_variables[1]] = 1
        for word in (short, out_of_range, boolean, overweight):
            with self.assertRaises(ValueError):
                encoding.decode(word)
        with self.assertRaises(TypeError):
            encoding.decode([0] * len(encoding.variables))  # type: ignore[arg-type]

    def test_native_evaluation_rejects_bad_selections(self) -> None:
        encoding = compile_knapsack((2, 3), (3, 4), 4)
        self.assertEqual(encoding.native_evaluation((0, 1)), (7, 5))
        self.assertEqual(encoding.native_evaluation(()), (0, 0))
        for selection in ((0, 0), (2,), (-1,), (True,), (0.0,)):
            with self.subTest(selection=selection):
                with self.assertRaises(ValueError):
                    encoding.native_evaluation(selection)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
