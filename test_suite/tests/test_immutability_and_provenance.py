"""Adversarial contracts for immutable model/result evidence and provenance."""

from __future__ import annotations

import math
import sys
import unittest
from importlib import util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq import SampleResult, compile_ising, compile_qubo  # noqa: E402
from gibbsiq.result import best_index  # noqa: E402

HAS_DIMOD = util.find_spec("dimod") is not None


class ModelImmutabilityTests(unittest.TestCase):
    def test_model_copies_and_freezes_coefficients(self) -> None:
        linear = {"a": 0.5, "b": -0.25}
        quadratic = {("a", "b"): 1.5}
        metadata = {"experiment": "original"}
        model = compile_ising(linear, quadratic, metadata=metadata)
        sample = {"a": 1, "b": -1}
        expected_energy = model.energy(sample)

        linear["a"] = 99.0
        quadratic[("a", "b")] = -99.0
        metadata["experiment"] = "mutated"

        self.assertEqual(model.energy(sample), expected_energy)
        self.assertEqual(model.metadata["experiment"], "original")
        with self.assertRaises(TypeError):
            model.linear["a"] = 99.0  # type: ignore[index]
        with self.assertRaises(TypeError):
            model.quadratic[("a", "b")] = -99.0  # type: ignore[index]
        with self.assertRaises(TypeError):
            model.metadata["new"] = "forged"  # type: ignore[index]

    def test_zero_couplings_omit_graph_edges(self) -> None:
        model = compile_ising(
            {"a": 0.0, "b": 0.0},
            {("a", "b"): 2.0, ("b", "a"): -2.0},
        )
        self.assertEqual(model.quadratic, {})
        self.assertEqual(model.graph, ())

    def test_energy_rejects_overflow(self) -> None:
        interaction_overflow = compile_ising({"a": 1e308, "b": 1e308})
        with self.assertRaisesRegex(ValueError, "computed interaction energy"):
            interaction_overflow.energy({"a": 1, "b": 1})

        total_overflow = compile_ising({"a": 1e308}, offset=1e308)
        with self.assertRaisesRegex(ValueError, "computed energy"):
            total_overflow.energy({"a": 1})

    def test_nested_metadata_freezes_and_to_dict_detaches(self) -> None:
        source_metadata = {
            "audit": {
                "seeds": [3, 5],
                "config": {"beta": 1.0},
            }
        }
        model = compile_ising({"a": 0.0}, metadata=source_metadata)
        source_metadata["audit"]["seeds"].append(7)
        source_metadata["audit"]["config"]["beta"] = 9.0

        self.assertEqual(model.metadata["audit"]["seeds"], [3, 5])
        self.assertEqual(model.metadata["audit"]["config"]["beta"], 1.0)
        with self.assertRaises((AttributeError, TypeError)):
            model.metadata["audit"]["seeds"].append(11)
        with self.assertRaises(TypeError):
            model.metadata["audit"]["config"]["beta"] = 2.0

        payload = model.to_dict()
        self.assertIs(type(payload["metadata"]), dict)
        self.assertIs(type(payload["metadata"]["audit"]["seeds"]), list)
        payload["metadata"]["audit"]["seeds"].append(13)
        payload["metadata"]["audit"]["config"]["beta"] = 4.0
        self.assertEqual(model.metadata["audit"]["seeds"], [3, 5])
        self.assertEqual(model.metadata["audit"]["config"]["beta"], 1.0)


class ResultImmutabilityTests(unittest.TestCase):
    def test_result_copies_and_freezes_evidence(self) -> None:
        sample = {"a": 1}
        result = SampleResult(
            samples=(sample,),
            variables=("a",),
            energies=(-1.0,),
            traces={"energy": [[-1.0]]},
            diagnostics={"flags": []},
            metadata={"seed": 7},
        )
        sample["a"] = -1

        self.assertEqual(result.samples[0]["a"], 1)
        with self.assertRaises(TypeError):
            result.samples[0]["a"] = -1  # type: ignore[index]
        with self.assertRaises(TypeError):
            result.traces["forged"] = True  # type: ignore[index]
        with self.assertRaises(TypeError):
            result.diagnostics["forged"] = True  # type: ignore[index]
        with self.assertRaises(TypeError):
            result.metadata["seed"] = 8  # type: ignore[index]

    def test_result_rejects_nonfinite_energies_and_extra_keys(self) -> None:
        for energy in (math.nan, math.inf, -math.inf):
            with self.subTest(energy=energy), self.assertRaisesRegex(ValueError, "finite"):
                SampleResult(samples=({"a": 1},), variables=("a",), energies=(energy,))

        with self.assertRaisesRegex(ValueError, "unexpected variables"):
            SampleResult(
                samples=({"a": 1, "unscored": -1},),
                variables=("a",),
                energies=(0.0,),
            )

    def test_nested_result_evidence_freezes_to_dict_detaches(self) -> None:
        traces = {"energy": [[-1.0]], "events": [{"accepted": True}]}
        diagnostics = {"flags": ["healthy"], "nested": {"ess": [10.0]}}
        metadata = {"runtime": {"versions": ["jax-test"]}}
        result = SampleResult(
            samples=({"a": 1},),
            variables=("a",),
            energies=(-1.0,),
            traces=traces,
            diagnostics=diagnostics,
            metadata=metadata,
        )
        traces["energy"][0].append(999.0)
        diagnostics["flags"].append("forged")
        metadata["runtime"]["versions"].append("forged")

        self.assertEqual(result.traces["energy"], [[-1.0]])
        self.assertEqual(result.diagnostics["flags"], ["healthy"])
        self.assertEqual(result.metadata["runtime"]["versions"], ["jax-test"])
        with self.assertRaises((AttributeError, TypeError)):
            result.traces["energy"][0].append(2.0)
        with self.assertRaises(TypeError):
            result.traces["events"][0]["accepted"] = False
        with self.assertRaises((AttributeError, TypeError)):
            result.diagnostics["flags"].append("forged")
        with self.assertRaises((AttributeError, TypeError)):
            result.metadata["runtime"]["versions"].append("forged")

        payload = result.to_dict()
        self.assertIs(type(payload["traces"]), dict)
        self.assertIs(type(payload["traces"]["energy"]), list)
        self.assertIs(type(payload["traces"]["events"][0]), dict)
        payload["traces"]["energy"][0].append(3.0)
        payload["traces"]["events"][0]["accepted"] = False
        payload["diagnostics"]["flags"].append("forged")
        payload["metadata"]["runtime"]["versions"].append("forged")
        self.assertEqual(result.traces["energy"], [[-1.0]])
        self.assertTrue(result.traces["events"][0]["accepted"])
        self.assertEqual(result.diagnostics["flags"], ["healthy"])
        self.assertEqual(result.metadata["runtime"]["versions"], ["jax-test"])

    def test_caller_metadata_cannot_override_provenance(self) -> None:
        model = compile_qubo(
            {("a", "a"): -1.0},
            metadata={
                "source_format": "forged",
                "input_offset": -999.0,
                "conversion_offset": -999.0,
                "variable_order": ["forged"],
                "experiment": "retained",
            },
        )
        self.assertEqual(model.metadata["source_format"], "qubo")
        self.assertEqual(model.metadata["input_offset"], 0.0)
        self.assertEqual(model.metadata["conversion_offset"], model.offset)
        self.assertEqual(model.metadata["variable_order"], ["a"])
        self.assertEqual(model.metadata["experiment"], "retained")

        result = SampleResult.from_model(
            model,
            [{"a": 1}],
            metadata={
                "source_model_format": "forged",
                "conversion_offset": -999.0,
                "variable_order": ["forged"],
                "seed": 11,
            },
        )
        self.assertEqual(result.metadata["source_model_format"], "qubo")
        self.assertEqual(result.metadata["conversion_offset"], model.offset)
        self.assertEqual(result.metadata["variable_order"], ["a"])
        self.assertEqual(result.metadata["seed"], 11)


class OffsetStableBestSelectionTests(unittest.TestCase):
    def test_offset_free_objective_breaks_energy_ties(self) -> None:
        fields = {"a": 0.3, "b": -0.4}
        couplings = {("a", "b"): 0.8}
        samples = (
            {"a": 1, "b": 1},
            {"a": -1, "b": 1},
            {"a": 1, "b": -1},
            {"a": -1, "b": -1},
        )
        base_model = compile_ising(fields, couplings)
        shifted_model = compile_ising(fields, couplings, offset=float(2**55))
        interaction_energies = tuple(base_model.interaction_energy(sample) for sample in samples)
        expected_index = min(range(len(samples)), key=interaction_energies.__getitem__)
        base = SampleResult.from_model(base_model, samples)
        shifted = SampleResult.from_model(shifted_model, samples)

        # All shifted energies round to one float, but the objective order
        # stays strict in offset-free interaction space.
        self.assertEqual(len(set(shifted.energies)), 1)
        self.assertNotEqual(best_index(shifted.energies), expected_index)
        self.assertEqual(expected_index, 1)
        self.assertEqual(base.best_index, expected_index)
        self.assertEqual(shifted.best_index, expected_index)
        self.assertEqual(base.best_sample, samples[expected_index])
        self.assertEqual(shifted.best_sample, samples[expected_index])
        self.assertEqual(shifted.interaction_energies, interaction_energies)


class StructuredInputDisambiguationTests(unittest.TestCase):
    def test_reserved_schema_words_remain_valid_variable_labels(self) -> None:
        fields = {
            "linear": 1.0,
            "quadratic": -2.0,
            "variables": 3.0,
            "offset": -4.0,
        }
        model = compile_ising(fields)

        self.assertEqual(model.variables, ("linear", "offset", "quadratic", "variables"))
        self.assertEqual(model.linear, fields)
        self.assertEqual(model.offset, 0.0)


@unittest.skipUnless(HAS_DIMOD, "optional dimod conformance checks require dimod")
class DimodResultOrderTests(unittest.TestCase):
    def test_to_dimod_preserves_explicit_variable_order(self) -> None:
        result = SampleResult(
            samples=({"z": 1, "a": -1}, {"z": -1, "a": 1}),
            variables=("z", "a"),
            energies=(1.0, -1.0),
        )
        sampleset = result.to_dimod()

        self.assertEqual(tuple(sampleset.variables), ("z", "a"))
        self.assertEqual(sampleset.record.sample.tolist(), [[1, -1], [-1, 1]])


if __name__ == "__main__":
    unittest.main()
