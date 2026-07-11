"""Checks for the CATEGORICAL (k-ary / Potts-style) result schema extension."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq import SampleResult, compile_ising  # noqa: E402
from gibbsiq.result import normalize_result_vartype  # noqa: E402


class DimodStyleDiscrete:
    """Stand-in for a dimod Vartype enum member exposing a ``name`` attribute."""

    name = "DISCRETE"


class NormalizeResultVartypeTests(unittest.TestCase):
    def test_spin_binary_vartypes_pass_through(self) -> None:
        self.assertEqual(normalize_result_vartype("SPIN"), "SPIN")
        self.assertEqual(normalize_result_vartype("binary"), "BINARY")

    def test_categorical_dimod_discrete_alias(self) -> None:
        self.assertEqual(normalize_result_vartype("CATEGORICAL"), "CATEGORICAL")
        self.assertEqual(normalize_result_vartype("discrete"), "CATEGORICAL")
        self.assertEqual(normalize_result_vartype(DimodStyleDiscrete()), "CATEGORICAL")

    def test_unknown_vartype_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_result_vartype("POTTS")


class CategoricalSampleResultTests(unittest.TestCase):
    def test_broadcast_num_states_accepts_valid_samples(self) -> None:
        result = SampleResult(
            samples=({"a": 0, "b": 2}, {"a": 1, "b": 0}),
            variables=("a", "b"),
            energies=(1.5, -0.5),
            vartype="CATEGORICAL",
            num_states=3,
        )
        self.assertEqual(result.vartype, "CATEGORICAL")
        self.assertEqual(result.num_states, {"a": 3, "b": 3})
        self.assertEqual(result.best_sample, {"a": 1, "b": 0})
        self.assertEqual(result.best_energy, -0.5)

    def test_per_variable_num_states_heterogeneous_domains(self) -> None:
        result = SampleResult(
            samples=({"site": 4, "flag": 1},),
            variables=("site", "flag"),
            energies=(0.0,),
            vartype="CATEGORICAL",
            num_states={"site": 5, "flag": 2},
        )
        self.assertEqual(result.num_states, {"site": 5, "flag": 2})

    def test_out_of_range_value_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid categorical value"):
            SampleResult(
                samples=({"a": 3},),
                variables=("a",),
                energies=(0.0,),
                vartype="CATEGORICAL",
                num_states=3,
            )

    def test_bool_sample_values_are_rejected(self) -> None:
        cases = (
            {"samples": ({"a": True},), "vartype": "SPIN", "message": "invalid spin value"},
            {"samples": ({"a": False},), "vartype": "BINARY", "message": "invalid binary value"},
            {
                "samples": ({"a": True},),
                "vartype": "CATEGORICAL",
                "num_states": 2,
                "message": "invalid categorical value",
            },
        )
        for case in cases:
            with self.subTest(vartype=case["vartype"]):
                with self.assertRaisesRegex(ValueError, case["message"]):
                    SampleResult(
                        samples=case["samples"],
                        variables=("a",),
                        energies=(0.0,),
                        vartype=case["vartype"],
                        num_states=case.get("num_states"),
                    )

    def test_categorical_requires_num_states(self) -> None:
        with self.assertRaisesRegex(ValueError, "require num_states"):
            SampleResult(
                samples=({"a": 0},),
                variables=("a",),
                energies=(0.0,),
                vartype="CATEGORICAL",
            )

    def test_num_states_missing_variable_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing variables"):
            SampleResult(
                samples=({"a": 0, "b": 0},),
                variables=("a", "b"),
                energies=(0.0,),
                vartype="CATEGORICAL",
                num_states={"a": 3},
            )

    def test_num_states_below_two_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "integer >= 2"):
            SampleResult(
                samples=({"a": 0},),
                variables=("a",),
                energies=(0.0,),
                vartype="CATEGORICAL",
                num_states=1,
            )

    def test_num_states_is_rejected_for_spin_results(self) -> None:
        with self.assertRaisesRegex(ValueError, "applies only to CATEGORICAL"):
            SampleResult(
                samples=({"a": 1},),
                variables=("a",),
                energies=(0.0,),
                vartype="SPIN",
                num_states=2,
            )

    def test_to_dict_serializes_num_states(self) -> None:
        categorical = SampleResult(
            samples=({"a": 2},),
            variables=("a",),
            energies=(0.0,),
            vartype="CATEGORICAL",
            num_states=4,
        )
        self.assertEqual(categorical.to_dict()["num_states"], {"a": 4})
        self.assertEqual(categorical.to_dict()["vartype"], "CATEGORICAL")

        spin = SampleResult(samples=({"a": -1},), variables=("a",), energies=(0.0,))
        self.assertIsNone(spin.to_dict()["num_states"])


class IsingBoundaryTests(unittest.TestCase):
    """The Ising model layer stays SPIN/BINARY; categorical samples stop at the result schema."""

    def test_model_energy_rejects_categorical_vartype(self) -> None:
        model = compile_ising({"a": 0.5}, {})
        with self.assertRaises(ValueError):
            model.energy({"a": 0}, vartype="CATEGORICAL")

    def test_from_model_rejects_categorical_vartype(self) -> None:
        model = compile_ising({"a": 0.5}, {})
        with self.assertRaises(ValueError):
            SampleResult.from_model(model, [{"a": 0}], vartype="CATEGORICAL")

    def test_spin_binary_results_unchanged(self) -> None:
        model = compile_ising({"a": 0.5}, {})
        result = SampleResult.from_model(model, [{"a": -1}, {"a": 1}])
        self.assertEqual(result.vartype, "SPIN")
        self.assertIsNone(result.num_states)
        self.assertEqual(result.best_energy, -0.5)


if __name__ == "__main__":
    unittest.main()
