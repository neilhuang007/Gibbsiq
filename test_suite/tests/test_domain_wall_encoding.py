"""Independent exhaustive contracts for categorical domain-wall lowering."""

from __future__ import annotations

import itertools
import json
import math
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.categorical import CategoricalModel  # noqa: E402
from gibbsiq.domain_wall import compile_domain_wall  # noqa: E402


def complete_pair(left_domain, right_domain, value):
    return {
        (left, right): value(left_index, right_index)
        for left_index, left in enumerate(left_domain)
        for right_index, right in enumerate(right_domain)
    }


def independent_categorical_energy(sample, variables, unary, pairwise, offset):
    return math.fsum(
        [offset]
        + [unary.get(variable, {}).get(sample[variable], 0.0) for variable in variables]
        + [table[(sample[left], sample[right])] for (left, right), table in pairwise.items()]
    )


def independent_qubo_energy(encoding, bits):
    return math.fsum(
        [encoding.qubo_offset]
        + [encoding.qubo_linear[variable] * bits[variable] for variable in encoding.variables]
        + [
            coefficient * bits[left] * bits[right]
            for (left, right), coefficient in encoding.qubo_quadratic.items()
        ]
    )


def heterogeneous_fixture():
    variables = (("node", 0), 9, "singleton", frozenset({"tail"}))
    domains = {
        variables[0]: ("red", None, ("blue", 2)),
        variables[1]: (10, 20),
        variables[2]: ("fixed",),
        variables[3]: ("u", "v", "w", "x"),
    }
    unary = {
        variables[0]: {"red": 0.25, None: -0.5, ("blue", 2): 1.0},
        variables[1]: {10: -0.75, 20: 0.5},
        variables[2]: {"fixed": 0.75},
        variables[3]: {"u": -0.25, "v": 0.5, "w": -0.75, "x": 1.25},
    }
    pairwise = {
        (variables[1], variables[0]): complete_pair(
            domains[variables[1]],
            domains[variables[0]],
            lambda i, j: 0.25 * (i + 1) * (j - 1),
        ),
        (variables[0], variables[3]): complete_pair(
            domains[variables[0]],
            domains[variables[3]],
            lambda i, j: 0.125 * (2 * i - j + i * j),
        ),
        (variables[2], variables[1]): complete_pair(
            domains[variables[2]],
            domains[variables[1]],
            lambda _i, j: 0.5 * j - 0.25,
        ),
        (variables[1], variables[3]): complete_pair(
            domains[variables[1]],
            domains[variables[3]],
            lambda i, j: 0.25 * (i - 2 * j),
        ),
    }
    return variables, domains, unary, pairwise, -2.75


class DomainWallExactnessTests(unittest.TestCase):
    def test_every_valid_heterogeneous_assignment_matches_independent_oracle(self) -> None:
        variables, domains, unary, pairwise, offset = heterogeneous_fixture()
        model = CategoricalModel(
            variables=variables,
            domains=domains,
            unary=unary,
            pairwise=pairwise,
            offset=offset,
        )
        encoding = compile_domain_wall(model, penalty=5.0)

        for state in itertools.product(*(domains[variable] for variable in variables)):
            sample = dict(zip(variables, state))
            expected = independent_categorical_energy(
                sample,
                variables,
                unary,
                pairwise,
                offset,
            )
            bits = encoding.encode(sample)
            spins = encoding.encode(sample, vartype="SPIN")
            self.assertTrue(encoding.is_valid(bits))
            self.assertTrue(encoding.is_valid(spins, vartype="SPIN"))
            self.assertEqual(encoding.decode(bits), sample)
            self.assertEqual(encoding.decode(spins, vartype="SPIN"), sample)
            self.assertEqual(model.energy(sample), expected)
            self.assertEqual(independent_qubo_energy(encoding, bits), expected)
            self.assertEqual(encoding.qubo_energy(bits), expected)
            self.assertEqual(encoding.qubo_energy(spins, vartype="SPIN"), expected)
            self.assertEqual(
                encoding.ising_model.energy(bits, vartype="BINARY"),
                expected,
            )
            self.assertEqual(encoding.ising_model.energy(spins), expected)

    def test_qubo_to_ising_equality_holds_for_every_valid_and_invalid_word(self) -> None:
        variables, domains, unary, pairwise, offset = heterogeneous_fixture()
        encoding = compile_domain_wall(
            CategoricalModel(
                variables=variables,
                domains=domains,
                unary=unary,
                pairwise=pairwise,
                offset=offset,
            ),
            penalty=3.0,
        )
        for word in itertools.product((0, 1), repeat=len(encoding.variables)):
            bits = dict(zip(encoding.variables, word))
            self.assertEqual(
                independent_qubo_energy(encoding, bits),
                encoding.ising_model.energy(bits, vartype="BINARY"),
            )
            independent_violations = sum(
                bits[right] == 1 and bits[left] == 0
                for chain in encoding.wall_variables.values()
                for left, right in zip(chain, chain[1:])
            )
            self.assertEqual(encoding.violation_count(bits), independent_violations)

    def test_two_by_two_pair_table_matches_hand_finite_differences(self) -> None:
        pair_table = {
            ("a0", "b0"): 1.0,
            ("a0", "b1"): 3.0,
            ("a1", "b0"): 4.0,
            ("a1", "b1"): 10.0,
        }
        encoding = compile_domain_wall(
            CategoricalModel(
                variables=("a", "b"),
                domains={"a": ("a0", "a1"), "b": ("b0", "b1")},
                pairwise={("a", "b"): pair_table},
            ),
            penalty=2.0,
        )
        left_wall = encoding.wall_variables["a"][0]
        right_wall = encoding.wall_variables["b"][0]
        self.assertEqual(encoding.qubo_offset, 1.0)
        self.assertEqual(encoding.qubo_linear[left_wall], 3.0)
        self.assertEqual(encoding.qubo_linear[right_wall], 2.0)
        self.assertEqual(encoding.qubo_quadratic[(left_wall, right_wall)], 4.0)

    def test_all_singleton_model_becomes_exact_constant_model(self) -> None:
        model = CategoricalModel(
            variables=("a", "b"),
            domains={"a": ("only-a",), "b": ("only-b",)},
            unary={"a": {"only-a": 3.0}, "b": {"only-b": -2.0}},
            pairwise={("a", "b"): {("only-a", "only-b"): 4.0}},
            offset=1.25,
        )
        encoding = compile_domain_wall(model, penalty=1.0)
        sample = {"a": "only-a", "b": "only-b"}
        self.assertEqual(encoding.variables, ())
        self.assertEqual(encoding.wall_variables, {"a": (), "b": ()})
        self.assertEqual(encoding.encode(sample), {})
        self.assertEqual(encoding.decode({}), sample)
        self.assertEqual(encoding.qubo_offset, 6.25)
        self.assertEqual(encoding.ising_model.variables, ())
        self.assertEqual(encoding.ising_model.offset, 6.25)
        self.assertEqual(encoding.overhead_metadata["qubo_color_count_upper_bound"], 0)

    def test_original_offset_is_preserved_for_valid_and_invalid_words(self) -> None:
        kwargs = {
            "variables": ("x",),
            "domains": {"x": ("a", "b", "c")},
            "unary": {"x": {"a": 0.25, "b": -0.5, "c": 1.0}},
        }
        baseline = compile_domain_wall(CategoricalModel(**kwargs), penalty=2.0)
        shifted = compile_domain_wall(
            CategoricalModel(**kwargs, offset=7.5),
            penalty=2.0,
        )
        self.assertEqual(baseline.variables, shifted.variables)
        self.assertEqual(baseline.qubo_linear, shifted.qubo_linear)
        self.assertEqual(baseline.qubo_quadratic, shifted.qubo_quadratic)
        self.assertEqual(shifted.qubo_offset - baseline.qubo_offset, 7.5)
        self.assertEqual(shifted.ising_model.offset - baseline.ising_model.offset, 7.5)
        for word in itertools.product((0, 1), repeat=2):
            bits = dict(zip(baseline.variables, word))
            self.assertEqual(shifted.qubo_energy(bits) - baseline.qubo_energy(bits), 7.5)


class DomainWallPenaltyAndCodecTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = CategoricalModel(
            variables=("x",),
            domains={"x": ("a", "b", "c", "d", "e")},
            unary={"x": {"a": 0.0, "b": 0.25, "c": -0.5, "d": 0.75, "e": -1.0}},
        )

    def positional_word(self, encoding, word):
        return dict(zip(encoding.wall_variables["x"], word))

    def test_invalid_energy_changes_by_penalty_delta_times_violation_count(self) -> None:
        low = compile_domain_wall(self.model, penalty=1.5)
        high = compile_domain_wall(self.model, penalty=4.0)
        invalid_word = (0, 1, 0, 1)
        low_bits = self.positional_word(low, invalid_word)
        high_bits = self.positional_word(high, invalid_word)
        self.assertEqual(low.violation_count(low_bits), 2)
        self.assertEqual(high.violation_count(high_bits), 2)
        self.assertEqual(
            high.qubo_energy(high_bits) - low.qubo_energy(low_bits),
            (4.0 - 1.5) * 2,
        )
        self.assertFalse(low.is_valid(low_bits))
        with self.assertRaisesRegex(ValueError, "2 reverse-wall"):
            low.decode(low_bits)
        self.assertEqual(
            low.overhead_metadata["penalty_selection_status"],
            "caller_supplied_not_proven_sufficient",
        )

    def test_valid_words_are_penalty_independent(self) -> None:
        low = compile_domain_wall(self.model, penalty=0.25)
        high = compile_domain_wall(self.model, penalty=100.0)
        for word in ((0, 0, 0, 0), (1, 0, 0, 0), (1, 1, 0, 0), (1, 1, 1, 1)):
            low_bits = self.positional_word(low, word)
            high_bits = self.positional_word(high, word)
            self.assertEqual(low.qubo_energy(low_bits), high.qubo_energy(high_bits))

    def test_penalty_is_required_positive_and_finite(self) -> None:
        with self.assertRaises(TypeError):
            compile_domain_wall(self.model)  # type: ignore[call-arg]
        for penalty in (0.0, -1.0, True, float("nan"), float("inf")):
            with self.subTest(penalty=penalty), self.assertRaises(ValueError):
                compile_domain_wall(self.model, penalty=penalty)
        with self.assertRaisesRegex(TypeError, "CategoricalModel"):
            compile_domain_wall({}, penalty=1.0)  # type: ignore[arg-type]

    def test_codec_rejects_malformed_samples(self) -> None:
        encoding = compile_domain_wall(self.model, penalty=2.0)
        chain = encoding.wall_variables["x"]
        with self.assertRaisesRegex(ValueError, "match encoded variables"):
            encoding.decode({chain[0]: 0})
        with self.assertRaisesRegex(ValueError, "match encoded variables"):
            encoding.decode({**{wall: 0 for wall in chain}, "extra": 0})
        bad_value = {wall: 0 for wall in chain}
        bad_value[chain[0]] = 2
        with self.assertRaisesRegex(ValueError, "must be 0 or 1"):
            encoding.is_valid(bad_value)
        boolean_value = {wall: 0 for wall in chain}
        boolean_value[chain[0]] = True
        with self.assertRaisesRegex(ValueError, "must not be boolean"):
            encoding.violation_count(boolean_value)
        with self.assertRaisesRegex(ValueError, "match variables exactly"):
            encoding.encode({})
        with self.assertRaisesRegex(ValueError, "not in the domain"):
            encoding.encode({"x": "unknown"})

    def test_codec_uses_exact_type_categorical_membership(self) -> None:
        encoding = compile_domain_wall(
            CategoricalModel(
                variables=("x",),
                domains={"x": (0, 1)},
            ),
            penalty=2.0,
        )
        for alias in (False, True, 0.0, 1.0):
            with (
                self.subTest(alias=alias),
                self.assertRaisesRegex(
                    ValueError,
                    "not in the domain",
                ),
            ):
                encoding.encode({"x": alias})

        decoded = encoding.decode({encoding.wall_variables["x"][0]: 1})
        self.assertEqual(decoded, {"x": 1})
        self.assertIs(type(decoded["x"]), int)


class DomainWallEvidenceAndIdentityTests(unittest.TestCase):
    def test_private_wall_labels_are_frozen_user_collision_safe_and_deterministic(self) -> None:
        user_variable = ("DomainWallVariable", 0, 0)
        model = CategoricalModel(
            variables=(user_variable,),
            domains={user_variable: ("a", "b", "c")},
        )
        first = compile_domain_wall(model, penalty=2.0)
        second = compile_domain_wall(model, penalty=2.0)
        self.assertTrue(set(model.variables).isdisjoint(first.variables))
        self.assertEqual(first.variables, second.variables)
        self.assertEqual(first.ising_model, second.ising_model)
        with self.assertRaises(FrozenInstanceError):
            first.variables[0].wall_position = 9  # type: ignore[attr-defined]
        with self.assertRaises(TypeError):
            first.wall_variables[user_variable] = ()  # type: ignore[index]

    def test_pair_insertion_order_produces_identical_compiler_evidence(self) -> None:
        variables = ("a", "b", "c")
        domains = {variable: (0, 1) for variable in variables}
        tables = {
            ("a", "b"): complete_pair((0, 1), (0, 1), lambda i, j: i - j),
            ("a", "c"): complete_pair((0, 1), (0, 1), lambda i, j: 2 * i + j),
            ("b", "c"): complete_pair((0, 1), (0, 1), lambda i, j: i + 3 * j),
        }
        forward = compile_domain_wall(
            CategoricalModel(variables=variables, domains=domains, pairwise=tables),
            penalty=2.0,
        )
        reversed_order = compile_domain_wall(
            CategoricalModel(
                variables=variables,
                domains=domains,
                pairwise=dict(reversed(tuple(tables.items()))),
            ),
            penalty=2.0,
        )
        self.assertEqual(forward.ising_model, reversed_order.ising_model)
        self.assertEqual(forward.to_dict(), reversed_order.to_dict())

    def test_overhead_metadata_matches_constructed_qubo_graph(self) -> None:
        variables, domains, unary, pairwise, offset = heterogeneous_fixture()
        model = CategoricalModel(
            variables=variables,
            domains=domains,
            unary=unary,
            pairwise=pairwise,
            offset=offset,
        )
        encoding = compile_domain_wall(model, penalty=5.0)
        metadata = encoding.overhead_metadata
        neighbors = {variable: set() for variable in encoding.variables}
        for left, right in encoding.qubo_quadratic:
            neighbors[left].add(right)
            neighbors[right].add(left)
        maximum_degree = max((len(row) for row in neighbors.values()), default=0)
        expected_mixed_capacity = sum(
            (len(model.domains[left]) - 1) * (len(model.domains[right]) - 1) for left, right in model.pairwise
        )
        self.assertEqual(metadata["original_variable_count"], 4)
        self.assertEqual(metadata["original_total_category_count"], 10)
        self.assertEqual(metadata["original_joint_state_count"], 24)
        self.assertEqual(metadata["domain_sizes"], [3, 2, 1, 4])
        self.assertEqual(metadata["singleton_variable_count"], 1)
        self.assertEqual(metadata["reversed_pair_table_count"], 2)
        self.assertEqual(metadata["wall_spin_count"], 6)
        self.assertEqual(metadata["qubo_edge_count"], len(encoding.qubo_quadratic))
        self.assertEqual(metadata["qubo_maximum_degree"], maximum_degree)
        self.assertEqual(
            metadata["qubo_color_count_upper_bound"],
            min(len(encoding.variables), maximum_degree + 1),
        )
        self.assertIn("loose constructive Delta+1", metadata["color_bound_method"])
        self.assertEqual(
            metadata["pair_mixed_coefficient_capacity"],
            expected_mixed_capacity,
        )
        self.assertIn("does not preserve mixing", metadata["mixing_warning"])
        self.assertEqual(
            encoding.ising_model.source_format,
            "categorical_domain_wall_qubo",
        )
        self.assertEqual(encoding.ising_model.metadata["input_offset"], encoding.qubo_offset)
        self.assertEqual(encoding.ising_model.metadata["equation_contract"], "EVAL-EQ-020")

    def test_encoding_evidence_is_json_safe_without_private_label_keys(self) -> None:
        encoding = compile_domain_wall(
            CategoricalModel(
                variables=("a", "b"),
                domains={"a": (0, 1, 2), "b": ("x", "y")},
                pairwise={
                    ("a", "b"): complete_pair(
                        (0, 1, 2),
                        ("x", "y"),
                        lambda i, j: 0.25 * (i - j),
                    )
                },
            ),
            penalty=3.0,
        )
        payload = encoding.to_dict()
        json.dumps(payload, allow_nan=False)
        self.assertEqual(
            [row["encoded_position"] for row in payload["wall_variables"]],
            list(range(len(encoding.variables))),
        )
        self.assertTrue(all(isinstance(row, dict) for row in payload["qubo_linear"]))


if __name__ == "__main__":
    unittest.main()
