"""Contracts for the domain-neutral categorical energy IR."""

from __future__ import annotations

import itertools
import math
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.categorical import CategoricalModel  # noqa: E402


def complete_pair(left_domain, right_domain, value):
    return {
        (left, right): value(left_index, right_index)
        for left_index, left in enumerate(left_domain)
        for right_index, right in enumerate(right_domain)
    }


class CategoricalModelContractTests(unittest.TestCase):
    def test_arbitrary_hashable_labels_preserve_explicit_state_order(self) -> None:
        left = ("variable", 1)
        right = 7
        left_domain = (None, ("category", 2), "last")
        right_domain = (False, "yes")
        model = CategoricalModel(
            variables=[left, right],  # type: ignore[arg-type]
            domains={left: left_domain, right: right_domain},
            unary={
                left: {None: 0.5, ("category", 2): -1.0, "last": 1.5},
                right: {False: -0.25, "yes": 0.75},
            },
            pairwise={
                (left, right): complete_pair(
                    left_domain,
                    right_domain,
                    lambda left_index, right_index: left_index - 2 * right_index,
                )
            },
            offset=2.25,
            metadata={"nested": [1, 2]},
        )
        self.assertEqual(model.variables, (left, right))
        self.assertEqual(model.domains[left], left_domain)
        self.assertEqual(model.domain_sizes, (3, 2))
        self.assertEqual(model.joint_state_count, 6)
        payload = model.to_dict()
        self.assertEqual(payload["domains"][0]["categories"], list(left_domain))
        self.assertEqual(payload["pairwise_tables"][0]["left"], left)
        with self.assertRaises(TypeError):
            model.domains[left] = ("changed",)  # type: ignore[index]
        with self.assertRaises(TypeError):
            model.unary[left][None] = 99.0  # type: ignore[index]
        with self.assertRaises(TypeError):
            model.metadata["extra"] = 3  # type: ignore[index]
        with self.assertRaises(FrozenInstanceError):
            model.offset = 0.0  # type: ignore[misc]

    def test_missing_whole_unary_table_means_complete_zero_table(self) -> None:
        model = CategoricalModel(
            variables=("x",),
            domains={"x": ("a", "b", "c")},
        )
        self.assertEqual(model.unary["x"], {"a": 0.0, "b": 0.0, "c": 0.0})
        self.assertEqual(model.energy({"x": "b"}), 0.0)

    def test_reversed_pair_is_transposed_into_variable_order(self) -> None:
        domains = {"a": ("a0", "a1"), "b": ("b0", "b1", "b2")}
        reversed_table = complete_pair(
            domains["b"],
            domains["a"],
            lambda b_index, a_index: 10 * b_index + a_index,
        )
        model = CategoricalModel(
            variables=("a", "b"),
            domains=domains,
            pairwise={("b", "a"): reversed_table},
        )
        self.assertEqual(tuple(model.pairwise), (("a", "b"),))
        self.assertEqual(model.reversed_pair_count, 1)
        for a_category, b_category in itertools.product(domains["a"], domains["b"]):
            self.assertEqual(
                model.pairwise[("a", "b")][(a_category, b_category)],
                reversed_table[(b_category, a_category)],
            )
            self.assertEqual(
                model.energy({"a": a_category, "b": b_category}),
                reversed_table[(b_category, a_category)],
            )

    def test_supplying_both_pair_orientations_is_rejected(self) -> None:
        domains = {"a": (0, 1), "b": (0, 1)}
        forward = complete_pair(domains["a"], domains["b"], lambda i, j: i + j)
        reverse = complete_pair(domains["b"], domains["a"], lambda j, i: i + j)
        with self.assertRaisesRegex(ValueError, "both orientations"):
            CategoricalModel(
                variables=("a", "b"),
                domains=domains,
                pairwise={("a", "b"): forward, ("b", "a"): reverse},
            )

    def test_pair_storage_is_independent_of_input_mapping_insertion_order(self) -> None:
        variables = ("a", "b", "c")
        domains = {variable: (0, 1) for variable in variables}
        ab = complete_pair(domains["a"], domains["b"], lambda i, j: i - j)
        ac = complete_pair(domains["a"], domains["c"], lambda i, j: 2 * i + j)
        bc = complete_pair(domains["b"], domains["c"], lambda i, j: i + 3 * j)
        forward = CategoricalModel(
            variables=variables,
            domains=domains,
            pairwise={("a", "b"): ab, ("a", "c"): ac, ("b", "c"): bc},
        )
        reverse_insertion = CategoricalModel(
            variables=variables,
            domains=domains,
            pairwise={("b", "c"): bc, ("a", "c"): ac, ("a", "b"): ab},
        )
        self.assertEqual(tuple(forward.pairwise), (("a", "b"), ("a", "c"), ("b", "c")))
        self.assertEqual(forward, reverse_insertion)
        self.assertEqual(forward.to_dict(), reverse_insertion.to_dict())

    def test_energy_matches_independent_complete_table_oracle(self) -> None:
        variables = ("a", "b", "c")
        domains = {"a": (0, 1), "b": ("x", "y", "z"), "c": (None,)}
        unary = {
            "a": {0: -0.5, 1: 0.75},
            "b": {"x": 1.0, "y": -1.25, "z": 0.5},
            "c": {None: 2.0},
        }
        pairwise = {
            ("a", "b"): complete_pair(domains["a"], domains["b"], lambda i, j: 0.25 * (i - j)),
            ("c", "b"): complete_pair(domains["c"], domains["b"], lambda _i, j: j - 0.5),
        }
        offset = -3.25
        model = CategoricalModel(
            variables=variables,
            domains=domains,
            unary=unary,
            pairwise=pairwise,
            offset=offset,
        )
        for state in itertools.product(*(domains[variable] for variable in variables)):
            sample = dict(zip(variables, state))
            expected = math.fsum(
                [offset]
                + [unary[variable][sample[variable]] for variable in variables]
                + [table[(sample[left], sample[right])] for (left, right), table in pairwise.items()]
            )
            self.assertEqual(model.energy(sample), expected)

    def test_table_and_domain_validation_rejects_ambiguous_models(self) -> None:
        with self.assertRaisesRegex(ValueError, "ordered"):
            CategoricalModel(variables=("x",), domains={"x": {"a", "b"}})
        with self.assertRaisesRegex(ValueError, "at least one"):
            CategoricalModel(variables=("x",), domains={"x": ()})
        with self.assertRaisesRegex(ValueError, "unique categories"):
            CategoricalModel(variables=("x",), domains={"x": (1, True)})
        with self.assertRaisesRegex(ValueError, "hashable"):
            CategoricalModel(variables=(["x"],), domains={})  # type: ignore[list-item]
        with self.assertRaisesRegex(ValueError, "match variables"):
            CategoricalModel(variables=("x",), domains={"y": (0, 1)})
        with self.assertRaisesRegex(ValueError, "cover its domain exactly"):
            CategoricalModel(
                variables=("x",),
                domains={"x": (0, 1)},
                unary={"x": {0: 1.0}},
            )
        with self.assertRaisesRegex(ValueError, "domain product exactly"):
            CategoricalModel(
                variables=("x", "y"),
                domains={"x": (0, 1), "y": (0, 1)},
                pairwise={("x", "y"): {(0, 0): 1.0}},
            )
        with self.assertRaisesRegex(ValueError, "self-pair"):
            CategoricalModel(
                variables=("x",),
                domains={"x": (0, 1)},
                pairwise={("x", "x"): complete_pair((0, 1), (0, 1), lambda i, j: i + j)},
            )

    def test_nonfinite_or_boolean_energy_values_are_rejected(self) -> None:
        for value in (True, float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                CategoricalModel(
                    variables=("x",),
                    domains={"x": (0,)},
                    unary={"x": {0: value}},
                )
        with self.assertRaises(ValueError):
            CategoricalModel(variables=(), domains={}, offset=True)
        for value in (True, float("nan"), float("inf")):
            with self.subTest(pair_value=value), self.assertRaises(ValueError):
                CategoricalModel(
                    variables=("x", "y"),
                    domains={"x": (0,), "y": (0,)},
                    pairwise={("x", "y"): {(0, 0): value}},
                )

    def test_sample_validation_rejects_missing_extra_and_unknown_categories(self) -> None:
        model = CategoricalModel(
            variables=("x", "y"),
            domains={"x": (0, 1), "y": ("a", "b")},
        )
        with self.assertRaisesRegex(ValueError, "match variables exactly"):
            model.energy({"x": 0})
        with self.assertRaisesRegex(ValueError, "match variables exactly"):
            model.energy({"x": 0, "y": "a", "z": 1})
        with self.assertRaisesRegex(ValueError, "not in the domain"):
            model.energy({"x": 3, "y": "a"})


if __name__ == "__main__":
    unittest.main()
