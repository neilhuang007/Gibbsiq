"""Conversion edge cases for the canonical Ising IR.

These tests are deliberately independent of optional third-party libraries.
They mirror public conventions from dimod/Ocean and PyQUBO using small
duck-typed objects and exhaustive energy checks.
"""

from __future__ import annotations

import itertools
import json
import sys
import unittest
from importlib import import_module, util
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq import SampleResult, binary_to_spin, compile_bqm, compile_ising, compile_qubo, spin_to_binary  # noqa: E402

HAS_DIMOD = util.find_spec("dimod") is not None


def spin_assignments(variables: tuple[Any, ...]):
    for values in itertools.product((-1, 1), repeat=len(variables)):
        yield dict(zip(variables, values))


def binary_assignments(variables: tuple[Any, ...]):
    for values in itertools.product((0, 1), repeat=len(variables)):
        yield dict(zip(variables, values))


def bits_from_spins(spins: dict[Any, int]) -> dict[Any, int]:
    return {variable: (spin + 1) // 2 for variable, spin in spins.items()}


def qubo_energy(
    linear: dict[Any, float],
    quadratic: dict[tuple[Any, Any], float],
    bits: dict[Any, int],
    offset: float = 0.0,
) -> float:
    energy = float(offset)
    for variable, coefficient in linear.items():
        energy += float(coefficient) * bits[variable]
    for (left, right), coefficient in quadratic.items():
        energy += float(coefficient) * bits[left] * bits[right]
    return energy


def benchmark_fixtures() -> list[dict[str, Any]]:
    path = REPO_ROOT / "reference" / "06-benchmarks" / "fixtures" / "ground-truth-small.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))["fixtures"]


class BinaryDuckBQM:
    def __init__(self) -> None:
        self.linear = {"b": -1.25, "a": 2.5}
        self.quadratic = {("b", "a"): 3.0, ("c", "a"): -2.0}
        self.offset = -4.5
        self.vartype = "BINARY"
        self.variables = ["c", "a", "b"]


class BadVartypeBQM:
    linear: dict[str, float] = {}
    quadratic: dict[tuple[str, str], float] = {}
    offset = 0.0
    vartype = "INTEGER"
    variables = []


class ConversionScenarioTest(unittest.TestCase):
    def test_dimod_documented_qubo_to_ising_example(self) -> None:
        model = compile_qubo(
            {
                ("x1", "x1"): -22,
                ("x2", "x2"): -6,
                ("x3", "x3"): -14,
                ("x1", "x2"): 20,
                ("x1", "x3"): 28,
            },
            offset=9,
            variables=["x1", "x2", "x3"],
        )

        self.assertEqual(model.linear, {"x1": 1.0, "x2": 2.0, "x3": 0.0})
        self.assertEqual(model.quadratic, {("x1", "x2"): 5.0, ("x1", "x3"): 7.0})
        self.assertEqual(model.offset, 0.0)
        for spins in spin_assignments(model.variables):
            bits = bits_from_spins(spins)
            expected = qubo_energy(
                {"x1": -22, "x2": -6, "x3": -14},
                {("x1", "x2"): 20, ("x1", "x3"): 28},
                bits,
                offset=9,
            )
            self.assertAlmostEqual(model.energy(spins), expected, places=12)

    def test_symmetric_qubo_pair_folding_preserves_energy(self) -> None:
        variables = ["z", "a", "m"]
        flat_qubo = {
            ("a", "a"): -3.0,
            ("m", "m"): 1.5,
            ("z", "z"): 0.25,
            ("a", "z"): 2.0,
            ("z", "a"): -6.0,
            ("m", "a"): 4.5,
            ("z", "m"): -1.0,
            ("m", "z"): 0.5,
        }
        model = compile_qubo(flat_qubo, offset=-2.25, variables=variables)

        self.assertEqual(model.variables, tuple(variables))
        self.assertEqual(model.quadratic, {("z", "a"): -1.0, ("z", "m"): -0.125, ("a", "m"): 1.125})
        for spins in spin_assignments(model.variables):
            bits = bits_from_spins(spins)
            expected = (
                sum(float(value) * bits[left] * bits[right] for (left, right), value in flat_qubo.items())
                - 2.25
            )
            self.assertAlmostEqual(model.energy(spins), expected, places=12)

    def test_structured_qubo_isolated_variables_string_keys(self) -> None:
        model = compile_qubo(
            {
                "variables": ["isolated", "left", "right"],
                "linear": {"left": -2.0},
                "quadratic": {"right,left": 8.0},
                "offset": 1.0,
            }
        )

        self.assertEqual(model.variables, ("isolated", "left", "right"))
        self.assertEqual(model.linear["isolated"], 0.0)
        self.assertEqual(model.quadratic, {("left", "right"): 2.0})
        for spins in spin_assignments(model.variables):
            bits = bits_from_spins(spins)
            expected = qubo_energy({"left": -2.0}, {("right", "left"): 8.0}, bits, offset=1.0)
            self.assertAlmostEqual(model.energy(spins), expected, places=12)

    def test_compile_ising_reversed_pairs_diagonal_self_terms(self) -> None:
        model = compile_ising(
            {"a": 1.0, "b": -2.0, "c": 0.5},
            {("b", "a"): 3.0, ("a", "b"): -1.25, ("c", "c"): 4.0},
            offset=-7.0,
            variables=["c", "a", "b"],
        )

        self.assertEqual(model.variables, ("c", "a", "b"))
        self.assertEqual(model.quadratic, {("a", "b"): 1.75})
        self.assertEqual(model.offset, -3.0)
        for spins in spin_assignments(model.variables):
            expected = -7.0 + 4.0
            expected += 1.0 * spins["a"] - 2.0 * spins["b"] + 0.5 * spins["c"]
            expected += 3.0 * spins["b"] * spins["a"]
            expected += -1.25 * spins["a"] * spins["b"]
            self.assertAlmostEqual(model.energy(spins), expected, places=12)

    def test_binary_duck_typed_bqm_uses_qubo_conversion_path(self) -> None:
        bqm = BinaryDuckBQM()
        model = compile_bqm(bqm)

        self.assertEqual(model.source_format, "bqm")
        self.assertEqual(model.variables, ("c", "a", "b"))
        self.assertEqual(model.metadata["bqm_vartype"], "BINARY")
        for bits in binary_assignments(model.variables):
            expected = qubo_energy(bqm.linear, bqm.quadratic, bits, offset=bqm.offset)
            self.assertAlmostEqual(model.energy(bits, vartype="BINARY"), expected, places=12)

    def test_mixed_hashable_labels_preserve_energy(self) -> None:
        variables = [1, "1", ("tuple", 1)]
        model = compile_qubo(
            {
                (1, 1): 0.5,
                ("1", "1"): -1.0,
                (("tuple", 1), ("tuple", 1)): 2.0,
                ("1", 1): 3.0,
                (("tuple", 1), "1"): -4.0,
            },
            offset=0.75,
            variables=variables,
        )

        self.assertEqual(model.variables, tuple(variables))
        for spins in spin_assignments(model.variables):
            bits = bits_from_spins(spins)
            expected = qubo_energy(
                {1: 0.5, "1": -1.0, ("tuple", 1): 2.0},
                {("1", 1): 3.0, (("tuple", 1), "1"): -4.0},
                bits,
                offset=0.75,
            )
            self.assertAlmostEqual(model.energy(spins), expected, places=12)

    def test_ambiguous_inputs_raise_validation_errors(self) -> None:
        with self.assertRaisesRegex(ValueError, "variables must be unique"):
            compile_qubo({("a", "a"): 1.0}, variables=["a", "a"])
        with self.assertRaisesRegex(ValueError, "terms reference variables"):
            compile_qubo({("a", "b"): 1.0}, variables=["a"])
        with self.assertRaisesRegex(ValueError, "unsupported vartype"):
            compile_bqm(BadVartypeBQM())

    def test_nonfinite_numeric_inputs_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "finite"):
            compile_qubo({("a", "a"): float("nan")})
        with self.assertRaisesRegex(ValueError, "finite"):
            compile_qubo({("a", "a"): 1.0}, offset=float("inf"))
        with self.assertRaisesRegex(ValueError, "finite"):
            compile_ising({"a": float("-inf")}, {})
        with self.assertRaisesRegex(ValueError, "finite"):
            compile_ising({"a": 0.0}, {("a", "a"): float("nan")})

    def test_spin_binary_helpers_round_trip_validation(self) -> None:
        spins = {"b": -1, "a": 1}
        binary = spin_to_binary(spins, variables=("a", "b"))

        self.assertEqual(binary, {"a": 1, "b": 0})
        self.assertEqual(binary_to_spin(binary, variables=("a", "b")), {"a": 1, "b": -1})
        with self.assertRaisesRegex(ValueError, "binary value"):
            binary_to_spin({"a": 2}, variables=("a",))
        with self.assertRaisesRegex(ValueError, "spin value"):
            spin_to_binary({"a": 0}, variables=("a",))

    def test_sk_benchmark_fixtures_witness_energy(self) -> None:
        sk_fixtures = [fixture for fixture in benchmark_fixtures() if fixture["family"] == "sk_spin_glass"]
        self.assertEqual(len(sk_fixtures), 3)

        for fixture in sk_fixtures:
            source = fixture["input"]
            model = compile_ising(
                source["linear"],
                source["quadratic"],
                offset=source["offset"],
                variables=source["variables"],
            )
            for witness in fixture["expected"]["witness_spin_samples"]:
                self.assertAlmostEqual(
                    model.energy(witness), fixture["expected"]["ground_state_energy"], places=12
                )

    def test_maxcut_benchmark_fixtures_ising_convention(self) -> None:
        maxcut_fixtures = [fixture for fixture in benchmark_fixtures() if fixture["family"] == "maxcut"]
        self.assertEqual(len(maxcut_fixtures), 14)

        for fixture in maxcut_fixtures:
            source = fixture["input"]
            linear = {variable: 0.0 for variable in source["variables"]}
            quadratic = {tuple(edge): 1.0 for edge in source["edges"]}
            model = compile_ising(linear, quadratic, variables=source["variables"])
            for witness in fixture["expected"]["witness_spin_samples"]:
                energy = model.energy(witness)
                cut = sum(1 for left, right in source["edges"] if witness[left] != witness[right])
                self.assertEqual(cut, fixture["expected"]["best_cut_value"])
                self.assertAlmostEqual(energy, fixture["expected"]["best_ising_energy"], places=12)


@unittest.skipUnless(HAS_DIMOD, "optional dimod conformance checks require dimod")
class DimodConformanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dimod = import_module("dimod")

    def test_compile_qubo_matches_dimod_qubo_to_ising(self) -> None:
        qubo = {
            ("a", "a"): -2.0,
            ("b", "b"): 3.5,
            ("c", "c"): -1.25,
            ("a", "b"): 4.0,
            ("a", "c"): -6.0,
            ("b", "c"): 0.75,
        }
        offset = 1.125
        expected_h, expected_j, expected_offset = self.dimod.qubo_to_ising(qubo, offset)
        model = compile_qubo(qubo, offset=offset, variables=["a", "b", "c"])

        self.assertEqual(model.linear, expected_h)
        self.assertEqual(model.quadratic, expected_j)
        self.assertAlmostEqual(model.offset, expected_offset, places=12)

    def test_compile_bqm_matches_dimod_binary_bqm_energy(self) -> None:
        qubo = {
            ("a", "a"): -1.0,
            ("b", "b"): 2.0,
            ("c", "c"): 0.5,
            ("a", "b"): -3.0,
            ("b", "c"): 4.0,
        }
        bqm = self.dimod.BinaryQuadraticModel.from_qubo(qubo, offset=-2.25)
        model = compile_bqm(bqm)

        self.assertEqual(model.variables, tuple(bqm.variables))
        for bits in binary_assignments(model.variables):
            self.assertAlmostEqual(model.energy(bits, vartype="BINARY"), bqm.energy(bits), places=12)

    def test_compile_bqm_matches_dimod_spin_bqm_energy(self) -> None:
        bqm = self.dimod.BinaryQuadraticModel(
            {"a": 1.5, "b": -0.25, "c": 0.0},
            {("a", "b"): -2.0, ("a", "c"): 3.25},
            -1.75,
            self.dimod.SPIN,
        )
        model = compile_bqm(bqm)

        self.assertEqual(model.variables, tuple(bqm.variables))
        for spins in spin_assignments(model.variables):
            self.assertAlmostEqual(model.energy(spins), bqm.energy(spins), places=12)

    def test_ising_model_to_dimod_preserves_spin_energy(self) -> None:
        model = compile_ising(
            {"a": 1.25, "b": -2.5, "c": 0.75},
            {("b", "a"): -3.0, ("a", "c"): 4.5},
            offset=2.25,
            variables=["c", "a", "b"],
        )
        bqm = model.to_dimod()

        self.assertEqual(tuple(bqm.variables), model.variables)
        self.assertEqual(bqm.vartype, self.dimod.SPIN)
        self.assertAlmostEqual(bqm.offset, model.offset, places=12)
        for spins in spin_assignments(model.variables):
            self.assertAlmostEqual(bqm.energy(spins), model.energy(spins), places=12)

    def test_sample_result_to_dimod_round_trip(self) -> None:
        model = compile_qubo(
            {
                "variables": ["a", "b"],
                "linear": {"a": -2.0, "b": 1.0},
                "quadratic": {"a,b": 3.0},
                "offset": -0.5,
            }
        )
        result = SampleResult.from_model(
            model,
            [{"a": 0, "b": 0}, {"a": 1, "b": 0}, {"a": 1, "b": 1}],
            vartype="BINARY",
            metadata={"seed": 99},
        )
        sampleset = result.to_dimod()

        self.assertEqual(list(sampleset.variables), list(result.variables))
        self.assertEqual(sampleset.vartype, self.dimod.BINARY)
        self.assertEqual(sampleset.info["seed"], 99)
        actual_rows = [
            ({variable: int(value) for variable, value in dict(sample).items()}, float(energy))
            for sample, energy in sampleset.data(["sample", "energy"])
        ]
        expected_rows = [(sample, energy) for sample, energy in zip(result.samples, result.energies)]
        self.assertCountEqual(actual_rows, expected_rows)


if __name__ == "__main__":
    unittest.main()
