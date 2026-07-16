"""Stage-1 checks for model normalization and result schema."""

from __future__ import annotations

import itertools
import json
import math
import sys
import unittest
from collections.abc import Iterator, Mapping
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq import IsingModel, SampleResult, compile_bqm, compile_ising, compile_qubo  # noqa: E402


class _DuplicateExactKeyMapping(Mapping[str, int]):
    def __getitem__(self, key: str) -> int:
        if key != "a":
            raise KeyError(key)
        return 1

    def __iter__(self) -> Iterator[str]:
        return iter(("a", "a"))

    def __len__(self) -> int:
        return 2


def load_exact_fixture(fixture_id: str) -> dict:
    path = REPO_ROOT / "reference" / "08-evaluation" / "fixtures" / "exact-small-instances.json"
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return next(fixture for fixture in payload["fixtures"] if fixture["id"] == fixture_id)


def spin_assignments(variables: list[str]):
    for values in itertools.product((-1, 1), repeat=len(variables)):
        yield dict(zip(variables, values))


def binary_from_spin(spins: dict[str, int]) -> dict[str, int]:
    return {variable: (spin + 1) // 2 for variable, spin in spins.items()}


def qubo_energy(model: dict, bits: dict[str, int]) -> float:
    energy = float(model.get("offset", 0.0))
    for variable, coefficient in model.get("linear", {}).items():
        energy += float(coefficient) * bits[variable]
    for pair, coefficient in model.get("quadratic", {}).items():
        left, right = pair.split(",")
        energy += float(coefficient) * bits[left] * bits[right]
    return energy


class FakeBQM:
    def __init__(self) -> None:
        self.linear = {"b": 0.0, "a": -1.5}
        self.quadratic = {("b", "a"): -1.0}
        self.offset = 2.5
        self.vartype = "SPIN"
        self.variables = ["a", "b"]


class FakeToIsingBQM:
    def __init__(self) -> None:
        self.offset = 3.0
        self.vartype = "BINARY"
        self.variables = ["a", "b"]

    def to_ising(self):
        return {"a": -1.5, "b": 0.0}, {("a", "b"): -1.0}, 2.5


class ModelCompatibilityTest(unittest.TestCase):
    def test_compile_qubo_matches_fixture_and_offset(self) -> None:
        fixture = load_exact_fixture("qubo_two_var_offset_conversion")
        model = compile_qubo(fixture["input"])
        expected_ir = fixture["expected"]["ising_ir"]

        self.assertEqual(model.to_dict()["variables"], expected_ir["variables"])
        self.assertEqual(model.to_dict()["linear"], expected_ir["linear"])
        self.assertEqual(model.to_dict()["quadratic"], expected_ir["quadratic"])
        self.assertEqual(model.offset, expected_ir["offset"])
        self.assertEqual(model.metadata["input_offset"], fixture["input"]["offset"])
        self.assertEqual(model.metadata["conversion_offset"], expected_ir["offset"])

        for spins in spin_assignments(fixture["input"]["variables"]):
            bits = binary_from_spin(spins)
            self.assertAlmostEqual(
                qubo_energy(fixture["input"], bits),
                model.energy(spins),
                places=12,
            )
            self.assertAlmostEqual(model.energy(bits, vartype="BINARY"), model.energy(spins), places=12)

    def test_compile_qubo_sums_duplicate_pairs(self) -> None:
        model = compile_qubo(
            {
                ("a", "a"): -1.0,
                ("b", "b"): 2.0,
                ("a", "b"): -2.5,
                ("b", "a"): -1.5,
            },
            offset=3.0,
            variables=["a", "b"],
        )

        self.assertEqual(model.to_dict()["linear"], {"a": -1.5, "b": 0.0})
        self.assertEqual(model.to_dict()["quadratic"], {"a,b": -1.0})
        self.assertEqual(model.offset, 2.5)

    def test_compile_qubo_duplicate_pair_sum_is_cancellation_stable(self) -> None:
        model = compile_qubo(
            {
                ("a", "b"): 1.0,
                ("b", "a"): -1e16,
                "a,b": 1e16,
            },
            variables=("a", "b"),
        )

        self.assertEqual(model.quadratic, {("a", "b"): 0.25})
        self.assertEqual(model.energy({"a": 1, "b": 1}, vartype="BINARY"), 1.0)

    def test_compile_qubo_accepts_structured_diagonal_terms(self) -> None:
        model = compile_qubo(
            {
                "variables": ["a", "b"],
                "quadratic": {("a", "a"): -1.0, ("b", "b"): 2.0, ("a", "b"): -4.0},
                "offset": 3.0,
            }
        )

        self.assertEqual(model.to_dict()["linear"], {"a": -1.5, "b": 0.0})
        self.assertEqual(model.to_dict()["quadratic"], {"a,b": -1.0})
        self.assertEqual(model.offset, 2.5)

    def test_compile_ising_orders_variables_folds_diagonals(self) -> None:
        model = compile_ising({"z": 2, "a": -1}, {("z", "a"): 3, ("a", "a"): 4})

        self.assertEqual(model.variables, ("a", "z"))
        self.assertEqual(model.to_dict()["linear"], {"a": -1.0, "z": 2.0})
        self.assertEqual(model.to_dict()["quadratic"], {"a,z": 3.0})
        self.assertEqual(model.offset, 4.0)
        self.assertEqual(model.energy({"a": 1, "z": -1}), -2.0)

    def test_compile_ising_diagonal_fold_is_order_independent_under_cancellation(self) -> None:
        forward = compile_ising(
            {},
            {("small", "small"): 1.0, ("large", "large"): -1e16},
            offset=1e16,
        )
        reverse = compile_ising(
            {},
            {("large", "large"): -1e16, ("small", "small"): 1.0},
            offset=1e16,
        )

        self.assertEqual(forward.offset, 1.0)
        self.assertEqual(reverse.offset, 1.0)
        self.assertEqual(forward.metadata["input_offset"], 1e16)
        self.assertEqual(forward.metadata["conversion_offset"], 1.0)

    def test_direct_model_rejects_unknown_linear_variables(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "linear bias for 'unknown' references unknown variable",
        ):
            IsingModel(
                variables=("a",),
                linear={"a": 1.0, "unknown": 3.0},
                quadratic={},
            )

        model = IsingModel(
            variables=("a", "b"),
            linear={"a": 1.0},
            quadratic={},
        )
        self.assertEqual(model.linear, {"a": 1.0, "b": 0.0})

    def test_direct_model_rejects_non_spin_vartype_and_typed_order_alias(self) -> None:
        with self.assertRaisesRegex(ValueError, "vartype.*SPIN"):
            IsingModel(
                variables=("a",),
                linear={"a": 0.0},
                quadratic={},
                vartype="BINARY",  # type: ignore[arg-type]
            )
        with self.assertRaisesRegex(ValueError, "variable_order"):
            IsingModel(
                variables=(1,),
                linear={1: 0.0},
                quadratic={},
                variable_order=(True,),
            )
        tuple_label = ("node", 1)
        with self.assertRaisesRegex(ValueError, "variable_order"):
            IsingModel(
                variables=(tuple_label,),
                linear={tuple_label: 0.0},
                quadratic={},
                variable_order=(["node", 1],),  # type: ignore[arg-type]
            )

    def test_model_operations_reject_boolean_variable_aliases(self) -> None:
        model = IsingModel(variables=(True,), linear={True: 0.5}, quadratic={})

        with self.assertRaisesRegex(ValueError, "missing variable"):
            model.energy({1: 1})
        with self.assertRaisesRegex(ValueError, "unknown variable"):
            model.local_field(1, {True: 1})
        with self.assertRaisesRegex(ValueError, "unknown variable"):
            IsingModel(variables=(True,), linear={1: 0.5}, quadratic={})

    def test_pair_aliases_fail_closed_instead_of_becoming_diagonals(self) -> None:
        with self.assertRaisesRegex(ValueError, "terms reference variables"):
            compile_qubo({(True, 1): 2.0}, variables=(True,))
        with self.assertRaisesRegex(ValueError, "terms reference variables"):
            compile_ising({}, {(True, 1): 2.0}, variables=(True,))

    def test_bulk_sample_alignment_is_linear_and_rejects_duplicate_exact_keys(self) -> None:
        variables = tuple(range(20_000))
        model = IsingModel(
            variables=variables,
            linear={variable: 0.0 for variable in variables},
            quadratic={},
        )
        sample = {variable: 1 for variable in variables}

        self.assertEqual(model.energy(sample), 0.0)
        with self.assertRaisesRegex(ValueError, "duplicate exact key"):
            IsingModel(variables=("a",), linear={"a": 0.0}, quadratic={}).energy(_DuplicateExactKeyMapping())

    def test_gibbs_conditional_uses_audited_sign(self) -> None:
        fixture = load_exact_fixture("single_site_conditional_sign")
        source = fixture["input"]
        model = compile_ising(
            {"s0": source["h_target"], "s1": 0.0},
            {("s0", "s1"): source["coupling_to_neighbor"]},
            variables=["s0", "s1"],
        )

        prob_plus = model.conditional_probability("s0", {"s0": -1, "s1": 1}, beta=source["beta"])
        prob_minus = model.conditional_probability("s0", {"s0": -1, "s1": -1}, beta=source["beta"])
        self.assertAlmostEqual(prob_plus, fixture["expected"]["when_neighbor_s1_is_plus_1"]["p_s0_plus_1"])
        self.assertAlmostEqual(prob_minus, fixture["expected"]["when_neighbor_s1_is_minus_1"]["p_s0_plus_1"])

    def test_local_field_and_flip_delta_match_recomputation(self) -> None:
        model = compile_ising(
            {"a": 0.2, "b": -0.4, "c": 0.7},
            {("a", "b"): -1.5, ("a", "c"): 0.25, ("b", "c"): 0.9},
            variables=("a", "b", "c"),
            offset=1.25,
        )
        sample = {"a": 1, "b": -1, "c": 1}
        for variable in model.variables:
            expected_gamma = model.linear[variable]
            for (left, right), coefficient in model.quadratic.items():
                if left == variable:
                    expected_gamma += coefficient * sample[right]
                elif right == variable:
                    expected_gamma += coefficient * sample[left]
            flipped = dict(sample)
            flipped[variable] = -flipped[variable]
            self.assertAlmostEqual(model.local_field(variable, sample), expected_gamma, places=12)
            self.assertAlmostEqual(
                model.flip_energy_delta(variable, sample),
                model.energy(flipped) - model.energy(sample),
                places=12,
            )

    def test_compile_bqm_accepts_duck_typed_bqm_objects(self) -> None:
        spin_model = compile_bqm(FakeBQM())
        converted_model = compile_bqm(FakeToIsingBQM())

        self.assertEqual(spin_model.source_format, "bqm")
        self.assertEqual(converted_model.source_format, "bqm")
        self.assertEqual(spin_model.to_dict()["quadratic"], {"a,b": -1.0})
        self.assertEqual(converted_model.offset, 2.5)
        self.assertAlmostEqual(spin_model.energy({"a": 1, "b": 1}), 0.0)
        self.assertAlmostEqual(converted_model.energy({"a": 1, "b": 1}), 0.0)

    def test_sample_result_schema_computes_best_sample(self) -> None:
        model = compile_qubo(
            {
                "variables": ["a", "b"],
                "linear": {"a": -1.0, "b": 2.0},
                "quadratic": {"a,b": -4.0},
                "offset": 3.0,
            }
        )
        result = SampleResult.from_model(
            model,
            [{"a": 0, "b": 0}, {"a": 1, "b": 1}],
            vartype="BINARY",
            metadata={"seed": 123},
        )
        payload = result.to_dict()

        self.assertEqual(result.best_sample, {"a": 1, "b": 1})
        self.assertTrue(math.isclose(result.best_energy, 0.0, abs_tol=1e-12))
        self.assertEqual(payload["variables"], ["a", "b"])
        self.assertEqual(payload["best_energy"], 0.0)
        self.assertEqual(payload["metadata"]["seed"], 123)
        self.assertEqual(payload["metadata"]["source_model_format"], "qubo")


if __name__ == "__main__":
    unittest.main()
