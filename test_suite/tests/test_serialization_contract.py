"""Regression tests for lossless, deterministic model/result serialization."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gibbsiq import (  # noqa: E402
    CategoricalModel,
    IsingModel,
    SampleResult,
    compile_ising,
    compile_qubo,
)


class _AmbiguousLabel:
    def __init__(self, identity: int) -> None:
        self.identity = identity

    def __hash__(self) -> int:
        return self.identity

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _AmbiguousLabel) and self.identity == other.identity

    def __repr__(self) -> str:
        return "ambiguous"


class SerializationContractTest(unittest.TestCase):
    def test_quadratic_comma_labels_round_trip_without_collision(self) -> None:
        model = compile_ising(
            {"a,b": 0.0, "c": 0.0, "a": 0.0, "b,c": 0.0},
            {("a,b", "c"): 1.0, ("a", "b,c"): 2.0},
            variables=("a,b", "c", "a", "b,c"),
        )

        payload = json.loads(json.dumps(model.to_dict(), sort_keys=True, allow_nan=False))
        restored = compile_ising(payload)

        self.assertEqual(payload["schema_version"], 2)
        self.assertIsInstance(payload["quadratic"], list)
        self.assertEqual(restored.variables, model.variables)
        self.assertEqual(restored.linear, model.linear)
        self.assertEqual(restored.quadratic, model.quadratic)
        self.assertEqual(restored.offset, model.offset)

    def test_typed_labels_round_trip_without_json_key_coercion(self) -> None:
        model = compile_ising(
            {1: 0.25, "1": -0.75},
            {(1, "1"): 1.5},
            variables=(1, "1"),
        )

        payload = json.loads(json.dumps(model.to_dict(), sort_keys=True, allow_nan=False))
        restored = compile_ising(payload)

        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual([row["kind"] for row in payload["variables"]], ["int", "str"])
        self.assertEqual(restored.variables, (1, "1"))
        self.assertEqual(restored.linear, {1: 0.25, "1": -0.75})
        self.assertEqual(restored.quadratic, {(1, "1"): 1.5})

    def test_result_typed_labels_use_positional_samples(self) -> None:
        model = compile_ising({1: 0.25, "1": -0.75}, variables=(1, "1"))
        result = SampleResult.from_model(model, ({1: 1, "1": -1},))

        payload = json.loads(json.dumps(result.to_dict(), sort_keys=True, allow_nan=False))

        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual([row["kind"] for row in payload["variables"]], ["int", "str"])
        self.assertEqual(payload["samples"], [[1, -1]])
        self.assertEqual(payload["best_sample"], [1, -1])

    def test_supported_typed_labels_are_json_round_trip_safe(self) -> None:
        labels = (
            None,
            False,
            2,
            1.5,
            "x",
            b"y",
            ("tuple", 3),
            frozenset({"b", "a"}),
        )
        model = compile_ising({}, variables=labels)

        payload = json.loads(json.dumps(model.to_dict(), sort_keys=True, allow_nan=False))
        restored = compile_ising(payload)

        self.assertEqual(restored.variables, labels)

    def test_model_round_trip_preserves_source_format_and_custom_metadata(self) -> None:
        model = compile_ising(
            {1: 0.25, "1": -0.75},
            {(1, "1"): 1.5},
            variables=(1, "1"),
            metadata={"custom": {"seeds": [7, 11]}},
            source_format="audit_fixture",
        )

        payload = json.loads(json.dumps(model.to_dict(), sort_keys=True, allow_nan=False))
        restored = compile_ising(payload)

        self.assertEqual(restored.source_format, model.source_format)
        self.assertEqual(restored.metadata, model.metadata)
        self.assertEqual(restored.to_dict(), payload)

    def test_converted_qubo_round_trip_preserves_original_input_offset(self) -> None:
        model = compile_qubo(
            {("a", "a"): -1.0, ("a", "b"): 4.0},
            offset=3.0,
            variables=("a", "b"),
        )
        payload = json.loads(json.dumps(model.to_dict(), sort_keys=True, allow_nan=False))

        restored = compile_ising(payload)

        self.assertEqual(restored.metadata["input_offset"], 3.0)
        self.assertEqual(restored.metadata, model.metadata)
        self.assertEqual(restored.to_dict(), payload)

    def test_frozenset_variable_order_alias_does_not_replace_metadata_evidence(self) -> None:
        variable = frozenset({1})
        model = IsingModel(
            variables=(variable,),
            linear={variable: 0.0},
            quadratic={},
            metadata={"variable_order": [frozenset({True})]},
        )

        payload = model.to_dict()

        self.assertEqual(payload["metadata"]["variable_order"], [[True]])
        self.assertNotEqual(payload["metadata"]["variable_order"], payload["variable_order"])

    def test_typed_payload_rejects_duplicate_quadratic_positions(self) -> None:
        model = compile_ising({1: 0.0, "1": 0.0}, {(1, "1"): 1.0}, variables=(1, "1"))
        payload = model.to_dict()
        payload["quadratic"].append(dict(payload["quadratic"][0]))

        with self.assertRaisesRegex(ValueError, "duplicate quadratic pair"):
            compile_ising(payload)

    def test_legacy_structured_input_remains_supported(self) -> None:
        restored = compile_ising(
            {
                "schema_version": 1,
                "variables": ["a", "b"],
                "linear": {"a": 0.25, "b": -0.75},
                "quadratic": {"a,b": 1.5},
                "offset": 2.0,
            }
        )

        self.assertEqual(restored.variables, ("a", "b"))
        self.assertEqual(restored.linear, {"a": 0.25, "b": -0.75})
        self.assertEqual(restored.quadratic, {("a", "b"): 1.5})
        self.assertEqual(restored.offset, 2.0)

    def test_schema_version_remains_a_valid_flat_variable_label(self) -> None:
        model = compile_ising({"schema_version": 1.25})

        self.assertEqual(model.variables, ("schema_version",))
        self.assertEqual(model.linear, {"schema_version": 1.25})

    def test_inferred_opaque_labels_fail_closed_but_explicit_order_works(self) -> None:
        first = _AmbiguousLabel(1)
        second = _AmbiguousLabel(2)

        with self.assertRaisesRegex(ValueError, "explicit variables"):
            compile_ising({first: 0.0, second: 0.0})

        model = compile_ising(
            {first: 0.0, second: 0.0},
            variables=(second, first),
        )
        self.assertEqual(model.variables, (second, first))
        with self.assertRaisesRegex(TypeError, "unsupported variable label"):
            model.to_dict()

    def test_set_metadata_serializes_identically_across_hash_seeds(self) -> None:
        script = (
            "import json; from gibbsiq import compile_ising; "
            "m=compile_ising({'x': 0.0}, metadata={'tags': "
            "{'alpha','beta','gamma','delta','epsilon'}}); "
            "print(json.dumps(m.to_dict(), sort_keys=True, separators=(',', ':')))"
        )
        outputs: list[str] = []
        for hash_seed in ("1", "2", "3", "4"):
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(SRC)
            environment["PYTHONHASHSEED"] = hash_seed
            outputs.append(
                subprocess.check_output(
                    [sys.executable, "-c", script],
                    cwd=ROOT,
                    env=environment,
                    text=True,
                ).strip()
            )

        self.assertEqual(len(set(outputs)), 1)
        self.assertEqual(
            json.loads(outputs[0])["metadata"]["tags"],
            ["alpha", "beta", "delta", "epsilon", "gamma"],
        )

    def test_set_metadata_supports_hashable_tuple_members(self) -> None:
        model = compile_ising(
            {"x": 0.0},
            metadata={"tag_pairs": {("beta", 2), ("alpha", 1)}},
        )

        self.assertEqual(
            model.to_dict()["metadata"]["tag_pairs"],
            [["alpha", 1], ["beta", 2]],
        )

    def test_model_metadata_rejects_json_key_coercion_recursively(self) -> None:
        model = compile_ising(
            {"x": 0.0},
            metadata={"nested": {1: "integer", "1": "string"}},
        )

        with self.assertRaisesRegex(TypeError, "metadata.*keys must be exact strings"):
            model.to_dict()

    def test_result_metadata_rejects_json_key_coercion(self) -> None:
        model = compile_ising({"x": 0.0})

        result = SampleResult.from_model(
            model,
            ({"x": 1},),
            metadata={1: "integer", "1": "string"},
        )

        with self.assertRaisesRegex(TypeError, "metadata.*keys must be exact strings"):
            result.to_dict()

    def test_categorical_metadata_rejects_json_key_coercion(self) -> None:
        model = CategoricalModel(
            variables=("x",),
            domains={"x": ("a", "b")},
            metadata={1: "integer", "1": "string"},
        )

        with self.assertRaisesRegex(TypeError, "metadata.*keys must be exact strings"):
            model.to_dict()

    def test_typed_model_does_not_exempt_untrusted_variable_order_metadata(self) -> None:
        model = IsingModel(
            variables=(1,),
            linear={1: 0.0},
            quadratic={},
            metadata={"variable_order": {1: "integer", "1": "string"}},
        )

        with self.assertRaisesRegex(TypeError, "metadata.*keys must be exact strings"):
            model.to_dict()

    def test_metadata_rejects_unsupported_values_without_repr_fallback(self) -> None:
        opaque = _AmbiguousLabel(1)

        model = compile_ising({"x": 0.0}, metadata={"opaque": opaque})

        with self.assertRaisesRegex(TypeError, "unsupported metadata value"):
            model.to_dict()

    def test_string_key_json_metadata_shape_is_unchanged(self) -> None:
        metadata = {
            "nested": {
                "values": [1, True, None, {"name": "evidence"}],
            }
        }

        payload = compile_ising({"x": 0.0}, metadata=metadata).to_dict()

        self.assertEqual(payload["metadata"]["nested"], metadata["nested"])


if __name__ == "__main__":
    unittest.main()
