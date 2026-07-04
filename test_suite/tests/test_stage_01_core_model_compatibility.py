"""Stage 1 contract tests: core model compatibility.

Stage 1 is not implemented yet, so this file has two layers:

1. executable reference-contract tests that pin down the expected math and
   schema without importing future implementation code;
2. optional API conformance tests that are skipped until the public Stage 1
   functions/classes exist.
"""

from __future__ import annotations

import itertools
import sys
import unittest
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


REQUIRED_IR_FIELDS = {
    "variables",
    "linear",
    "quadratic",
    "offset",
    "vartype",
    "graph",
    "source_format",
    "variable_order",
    "metadata",
}
REQUIRED_RESULT_FIELDS = {
    "samples",
    "variables",
    "energies",
    "best_sample",
    "best_energy",
    "traces",
    "diagnostics",
    "metadata",
}
REQUIRED_RESULT_METADATA = {
    "solver_backend_versions",
    "device",
    "seed",
    "schedule",
    "block_strategy",
    "timing",
    "source_model_format",
    "conversion_offset",
}


def spin_assignments(variables: list[str]):
    for values in itertools.product((-1, 1), repeat=len(variables)):
        yield dict(zip(variables, values))


def bits_from_spins(spins: dict[str, int]) -> dict[str, int]:
    return {variable: (spin + 1) // 2 for variable, spin in spins.items()}


def ordered_pair(left: str, right: str) -> tuple[str, str]:
    return (left, right) if left < right else (right, left)


def pair_key(left: str, right: str) -> str:
    return f"{left},{right}"


def normalize_qubo_terms(terms: dict[Any, float], offset: float = 0.0) -> dict[str, Any]:
    """Normalize common QUBO shapes into the Stage 1 upper-triangle convention."""
    variables: set[str] = set()
    linear: dict[str, float] = {}
    quadratic: dict[str, float] = {}

    for raw_key, raw_value in terms.items():
        value = float(raw_value)
        if isinstance(raw_key, tuple):
            left, right = (str(raw_key[0]), str(raw_key[1]))
        else:
            left = right = str(raw_key)
        variables.update((left, right))

        if left == right:
            linear[left] = linear.get(left, 0.0) + value
            continue

        first, second = ordered_pair(left, right)
        key = pair_key(first, second)
        quadratic[key] = quadratic.get(key, 0.0) + value

    ordered_variables = sorted(variables)
    return {
        "variables": ordered_variables,
        "linear": {var: linear.get(var, 0.0) for var in ordered_variables},
        "quadratic": {key: value for key, value in sorted(quadratic.items()) if value != 0.0},
        "offset": float(offset),
    }


def reference_compile_qubo(terms: dict[Any, float], offset: float = 0.0) -> dict[str, Any]:
    qubo = normalize_qubo_terms(terms, offset)
    linear = {variable: qubo["linear"].get(variable, 0.0) / 2.0 for variable in qubo["variables"]}
    quadratic: dict[str, float] = {}
    ising_offset = float(qubo["offset"])

    for variable in qubo["variables"]:
        ising_offset += qubo["linear"].get(variable, 0.0) / 2.0

    for key, value in qubo["quadratic"].items():
        left, right = key.split(",")
        quadratic[key] = value / 4.0
        linear[left] += value / 4.0
        linear[right] += value / 4.0
        ising_offset += value / 4.0

    return {
        "variables": qubo["variables"],
        "linear": linear,
        "quadratic": quadratic,
        "offset": ising_offset,
        "vartype": "SPIN",
        "source_format": "qubo",
        "variable_order": qubo["variables"],
    }


def reference_compile_ising(
    h: dict[Any, float], j: dict[tuple[Any, Any], float], offset: float = 0.0
) -> dict[str, Any]:
    variables = set(h)
    quadratic: dict[str, float] = {}
    for raw_pair, raw_value in j.items():
        left, right = raw_pair[0], raw_pair[1]
        variables.update((left, right))
        if left == right:
            raise ValueError("self-couplings are not valid Stage 1 Ising quadratic terms")
        first, second = ordered_pair(left, right)
        key = pair_key(first, second)
        quadratic[key] = quadratic.get(key, 0.0) + float(raw_value)

    ordered_variables = sorted(
        variables, key=lambda value: (type(value).__module__, type(value).__qualname__, repr(value))
    )
    return {
        "variables": ordered_variables,
        "linear": {variable: float(h.get(variable, 0.0)) for variable in ordered_variables},
        "quadratic": {key: value for key, value in sorted(quadratic.items()) if value != 0.0},
        "offset": float(offset),
        "vartype": "SPIN",
        "source_format": "ising",
        "variable_order": ordered_variables,
    }


def qubo_energy(terms: dict[Any, float], bits: dict[str, int], offset: float = 0.0) -> float:
    energy = float(offset)
    for raw_key, raw_value in terms.items():
        value = float(raw_value)
        if isinstance(raw_key, tuple):
            left, right = str(raw_key[0]), str(raw_key[1])
        else:
            left = right = str(raw_key)
        energy += value * bits[left] * bits[right]
    return energy


def ising_energy(model: dict[str, Any], spins: dict[str, int]) -> float:
    energy = float(model["offset"])
    for variable, coefficient in model["linear"].items():
        energy += coefficient * spins[variable]
    for pair, coefficient in model["quadratic"].items():
        left, right = pair.split(",")
        energy += coefficient * spins[left] * spins[right]
    return energy


def maybe_import(name: str) -> Any:
    module_name, _, attr = name.rpartition(".")
    try:
        module = import_module(module_name)
    except ModuleNotFoundError:
        return None
    return getattr(module, attr, None)


def as_mapping(model: Any) -> dict[str, Any]:
    if hasattr(model, "to_dict"):
        return model.to_dict()
    if isinstance(model, dict):
        return model
    return {field: getattr(model, field) for field in REQUIRED_IR_FIELDS if hasattr(model, field)}


class Stage01ReferenceContractTest(unittest.TestCase):
    def test_qubo_conversion_preserves_energy_for_mixed_terms(self) -> None:
        terms = {
            ("b", "b"): -1.5,
            ("a", "a"): 2.0,
            ("a", "b"): 4.0,
            ("c", "a"): -2.0,
        }
        offset = 3.25
        model = reference_compile_qubo(terms, offset)

        self.assertEqual(model["variables"], ["a", "b", "c"])
        self.assertEqual(model["quadratic"], {"a,b": 1.0, "a,c": -0.5})
        self.assertEqual(model["source_format"], "qubo")
        for spins in spin_assignments(model["variables"]):
            bits = bits_from_spins(spins)
            self.assertAlmostEqual(
                qubo_energy(terms, bits, offset),
                ising_energy(model, spins),
                places=12,
            )

    def test_symmetric_qubo_entries_are_normalized_before_conversion(self) -> None:
        terms = {
            ("x", "y"): 2.0,
            ("y", "x"): 6.0,
            ("x", "x"): -2.0,
            ("y", "y"): 4.0,
        }
        model = reference_compile_qubo(terms)

        self.assertEqual(model["variables"], ["x", "y"])
        self.assertEqual(model["linear"], {"x": 1.0, "y": 4.0})
        self.assertEqual(model["quadratic"], {"x,y": 2.0})
        self.assertEqual(model["offset"], 3.0)
        for spins in spin_assignments(model["variables"]):
            self.assertAlmostEqual(
                qubo_energy(terms, bits_from_spins(spins)),
                ising_energy(model, spins),
                places=12,
            )

    def test_compile_ising_contract_canonicalizes_quadratic_terms(self) -> None:
        model = reference_compile_ising(
            h={2: -1.0, 0: 0.5},
            j={(2, 0): 3.0, (1, 2): -4.0},
            offset=-7.0,
        )

        self.assertEqual(model["variables"], [0, 1, 2])
        self.assertEqual(model["linear"], {0: 0.5, 1: 0.0, 2: -1.0})
        self.assertEqual(model["quadratic"], {"0,2": 3.0, "1,2": -4.0})
        self.assertEqual(model["offset"], -7.0)
        self.assertEqual(model["variable_order"], [0, 1, 2])

    def test_stage_1_ir_and_result_schema_minimum_fields_are_explicit(self) -> None:
        self.assertEqual(
            REQUIRED_IR_FIELDS,
            {
                "variables",
                "linear",
                "quadratic",
                "offset",
                "vartype",
                "graph",
                "source_format",
                "variable_order",
                "metadata",
            },
        )
        self.assertIn("conversion_offset", REQUIRED_RESULT_METADATA)
        self.assertIn("best_energy", REQUIRED_RESULT_FIELDS)


class Stage01ImplementationConformanceTest(unittest.TestCase):
    compile_qubo: Callable | None = maybe_import("gibbsiq.compile_qubo")
    compile_ising: Callable | None = maybe_import("gibbsiq.compile_ising")
    sample_result_type: type | None = maybe_import("gibbsiq.SampleResult")

    @unittest.skipIf(compile_qubo is None, "Stage 1 compile_qubo API is not implemented yet")
    def test_compile_qubo_matches_reference_contract(self) -> None:
        terms = {("z", "z"): 1.0, ("a", "z"): -3.0, ("a", "a"): 2.0}
        expected = reference_compile_qubo(terms, offset=-0.25)
        actual = as_mapping(type(self).compile_qubo(terms, offset=-0.25))

        for key in ("variables", "linear", "quadratic", "offset", "vartype", "source_format"):
            self.assertEqual(actual[key], expected[key])
        self.assertTrue(REQUIRED_IR_FIELDS.issubset(actual))

    @unittest.skipIf(compile_ising is None, "Stage 1 compile_ising API is not implemented yet")
    def test_compile_ising_matches_reference_contract(self) -> None:
        expected = reference_compile_ising({1: 2.0}, {(1, 0): -0.5}, offset=4.0)
        actual = as_mapping(type(self).compile_ising({1: 2.0}, {(1, 0): -0.5}, offset=4.0))

        for key in ("variables", "linear", "quadratic", "offset", "vartype", "source_format"):
            self.assertEqual(actual[key], expected[key])
        self.assertTrue(REQUIRED_IR_FIELDS.issubset(actual))

    @unittest.skipIf(sample_result_type is None, "Stage 1 SampleResult API is not implemented yet")
    def test_sample_result_exposes_minimum_schema(self) -> None:
        annotations = getattr(self.sample_result_type, "__annotations__", {})
        available = set(annotations) | set(dir(self.sample_result_type))

        self.assertTrue(REQUIRED_RESULT_FIELDS.issubset(available))
        self.assertTrue(hasattr(self.sample_result_type, "to_dimod"))


if __name__ == "__main__":
    unittest.main()
