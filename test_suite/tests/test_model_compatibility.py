"""Stage-1 checks for model normalization and result schema."""

from __future__ import annotations

import itertools
import json
import math
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq import IsingModel, SampleResult, compile_bqm, compile_ising, compile_qubo  # noqa: E402


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
