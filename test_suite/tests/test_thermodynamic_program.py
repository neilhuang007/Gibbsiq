"""TM-IR-001 contracts for the immutable thermodynamic program envelope.

The energy checks in this module substitute clamps into the original model
directly.  They never call the production projection helper to construct an
expected value.
"""

from __future__ import annotations

import itertools
import json
import math
import sys
import unittest
from collections.abc import Mapping
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.categorical import CategoricalModel  # noqa: E402
from gibbsiq.model import IsingModel  # noqa: E402
from gibbsiq.program import PROGRAM_SCHEMA_VERSION, ThermodynamicProgram  # noqa: E402
from gibbsiq.result import SampleResult  # noqa: E402

TOLERANCE = 1e-9


def _ising_model(*, offset: float = 3.0) -> IsingModel:
    return IsingModel(
        variables=("a", "b", "c"),
        linear={"a": 0.5, "b": -1.0, "c": 0.25},
        quadratic={("a", "b"): 1.5, ("b", "c"): -0.75},
        offset=offset,
        metadata={"source": {"name": "hand-ising"}},
    )


def _categorical_model(*, offset: float = 1.25) -> CategoricalModel:
    variables = ("x", "y", "z")
    domains = {
        "x": ("red", "green"),
        "y": (0, 1, 2),
        "z": ("off", "on"),
    }
    return CategoricalModel(
        variables=variables,
        domains=domains,
        unary={
            "x": {"red": 0.0, "green": 0.75},
            "y": {0: -0.5, 1: 0.25, 2: 1.0},
            "z": {"off": 0.1, "on": -0.2},
        },
        pairwise={
            ("x", "y"): {
                (x, y): float(2 * x_index - y) for x_index, x in enumerate(domains["x"]) for y in domains["y"]
            },
            ("y", "z"): {
                (y, z): float(y + (0.5 if z == "on" else -0.5)) for y in domains["y"] for z in domains["z"]
            },
        },
        offset=offset,
        metadata={"source": {"name": "hand-categorical"}},
    )


def _all_assignments(model: IsingModel | CategoricalModel):
    if isinstance(model, IsingModel):
        domains = [(-1, 1) for _ in model.variables]
    else:
        domains = [model.domains[variable] for variable in model.variables]
    for values in itertools.product(*domains):
        yield dict(zip(model.variables, values))


def _direct_original_energy(
    model: IsingModel | CategoricalModel,
    free_assignment: Mapping[object, object],
    clamps: Mapping[object, object],
) -> float:
    """Independent oracle: merge by original order and evaluate the source model."""
    complete = {
        variable: clamps[variable] if variable in clamps else free_assignment[variable]
        for variable in model.variables
    }
    if isinstance(model, IsingModel):
        return model.energy(complete)  # type: ignore[arg-type]
    return model.energy(complete)


def _assert_projection_equivalent(
    case: unittest.TestCase,
    program: ThermodynamicProgram,
) -> None:
    projected = program.project()
    case.assertIs(type(projected), type(program.model))
    for assignment in _all_assignments(projected):
        expected = _direct_original_energy(
            program.model,
            assignment,
            program.clamp_values,
        )
        actual = projected.energy(assignment)
        case.assertTrue(
            math.isclose(expected, actual, rel_tol=0.0, abs_tol=TOLERANCE),
            msg=f"assignment={assignment!r} expected={expected!r} actual={actual!r}",
        )


class ProgramConstructionTests(unittest.TestCase):
    def test_state_is_defensively_frozen_and_ordered_by_model(self) -> None:
        clamps = {"c": 1, "a": -1}
        coordinates = {"c": [2, 0], "a": [0, 0]}
        observations = {"c": {"sensor": ["right"]}}
        metadata = {"audit": {"seeds": [7]}}
        program = ThermodynamicProgram(
            _ising_model(),
            clamps=clamps,
            coordinates=coordinates,
            observations=observations,
            metadata=metadata,
        )

        clamps["a"] = 1
        coordinates["a"].append(99)
        observations["c"]["sensor"].append("forged")
        metadata["audit"]["seeds"].append(11)

        self.assertEqual(program.free_variables, ("b",))
        self.assertEqual(program.clamped_variables, ("a", "c"))
        self.assertEqual(dict(program.clamp_values), {"a": -1, "c": 1})
        self.assertEqual(program.logical_coordinates["a"], (0.0, 0.0))
        self.assertEqual(program.observation_metadata["c"]["sensor"], ["right"])
        self.assertEqual(program.metadata["audit"]["seeds"], [7])
        with self.assertRaises(TypeError):
            program.clamp_values["a"] = 1  # type: ignore[index]
        with self.assertRaises(TypeError):
            program.metadata["new"] = True  # type: ignore[index]

    def test_exactly_one_supported_logical_model_is_required(self) -> None:
        for invalid in (None, object(), {"linear": {"a": 1.0}}):
            with self.subTest(invalid=type(invalid).__name__), self.assertRaises(TypeError):
                ThermodynamicProgram(invalid)  # type: ignore[arg-type]

    def test_clamp_records_reject_unknown_duplicate_conflict_and_boolean_alias(self) -> None:
        model = _ising_model()
        cases = (
            ([("missing", 1)], "unknown clamp variable"),
            ([("a", 1), ("a", 1)], "duplicate clamp"),
            ([("a", 1), ("a", -1)], "conflicting clamps"),
            ([("a", True)], "boolean"),
            ([("a", 0)], "out of domain"),
        )
        for clamps, message in cases:
            with self.subTest(clamps=clamps), self.assertRaisesRegex(ValueError, message):
                ThermodynamicProgram(model, clamps=clamps)

    def test_program_variable_records_reject_boolean_integer_aliases(self) -> None:
        model = IsingModel(variables=(True,), linear={True: 0.0}, quadratic={})
        with self.assertRaisesRegex(ValueError, "unknown clamp variable"):
            ThermodynamicProgram(model, clamps={1: 1})
        with self.assertRaisesRegex(ValueError, "unknown coordinate variable"):
            ThermodynamicProgram(model, coordinates={1: (0.0,)})

    def test_categorical_clamps_use_exact_type_domain_membership(self) -> None:
        model = _categorical_model()
        with self.assertRaisesRegex(ValueError, "boolean alias"):
            ThermodynamicProgram(model, clamps={"y": True})
        with self.assertRaisesRegex(ValueError, "out of domain"):
            ThermodynamicProgram(model, clamps={"x": "blue"})
        self.assertEqual(ThermodynamicProgram(model, clamps={"y": 1}).clamp_values["y"], 1)

        composite_model = CategoricalModel(
            variables=("x",),
            domains={"x": ((1,),)},
            unary={"x": {(1,): 0.0}},
        )
        self.assertEqual(composite_model.assignment_indices({"x": (1,)}), (0,))
        with self.assertRaisesRegex(ValueError, "not in the domain"):
            composite_model.assignment_indices({"x": (True,)})
        with self.assertRaisesRegex(ValueError, "out of domain"):
            ThermodynamicProgram(composite_model, clamps={"x": (True,)})
        with self.assertRaisesRegex(ValueError, "conflicting clamps"):
            ThermodynamicProgram(
                composite_model,
                clamps=[("x", (1,)), ("x", (True,))],
            )
        with self.assertRaisesRegex(ValueError, "cover its domain exactly"):
            CategoricalModel(
                variables=("x",),
                domains={"x": ((1,),)},
                unary={"x": {(True,): 0.0}},
            )

    def test_coordinates_are_logical_finite_and_dimensionally_consistent(self) -> None:
        model = _ising_model()
        valid = ThermodynamicProgram(model, coordinates={"a": (0, 1), "c": (2.5, -3)})
        self.assertEqual(valid.coordinate_dimension, 2)
        invalid_cases = (
            ({"missing": (0, 1)}, "unknown coordinate variable"),
            ({"a": ()}, "non-empty"),
            ({"a": (0, 1), "b": (2,)}, "same dimension"),
            ({"a": (0, True)}, "boolean"),
            ({"a": (0, math.inf)}, "finite"),
        )
        for coordinates, message in invalid_cases:
            with self.subTest(coordinates=coordinates), self.assertRaisesRegex(ValueError, message):
                ThermodynamicProgram(model, coordinates=coordinates)

    def test_observations_are_associated_only_with_clamped_variables(self) -> None:
        model = _ising_model()
        program = ThermodynamicProgram(
            model,
            clamps={"b": -1},
            observations={"b": {"source": "sensor-7", "time": 3}},
        )
        self.assertEqual(program.observation_metadata["b"]["source"], "sensor-7")
        with self.assertRaisesRegex(ValueError, "observation variable.*clamped"):
            ThermodynamicProgram(model, observations={"a": {"source": "sensor"}})


class ProjectionTests(unittest.TestCase):
    def test_ising_all_free_partial_full_and_isolated_projection(self) -> None:
        model = _ising_model()
        for clamps in ({}, {"b": -1}, {"a": 1, "b": -1, "c": 1}):
            with self.subTest(clamps=clamps):
                program = ThermodynamicProgram(model, clamps=clamps)
                _assert_projection_equivalent(self, program)
        full = ThermodynamicProgram(model, clamps={"a": 1, "b": -1, "c": 1}).project()
        self.assertEqual(full.variables, ())
        self.assertEqual(full.linear, {})
        self.assertEqual(full.quadratic, {})
        self.assertTrue(
            math.isclose(
                full.offset,
                model.energy({"a": 1, "b": -1, "c": 1}),
                rel_tol=0.0,
                abs_tol=TOLERANCE,
            )
        )

        isolated = IsingModel(
            variables=("a", "isolated"),
            linear={"a": 1.0, "isolated": -0.25},
            quadratic={},
            offset=2.0,
        )
        isolated_program = ThermodynamicProgram(isolated, clamps={"a": -1})
        _assert_projection_equivalent(self, isolated_program)
        self.assertEqual(isolated_program.project().variables, ("isolated",))

    def test_ising_projection_folds_incident_pairs_and_preserves_offset(self) -> None:
        projected = ThermodynamicProgram(_ising_model(), clamps={"b": -1}).project()
        self.assertEqual(projected.variables, ("a", "c"))
        self.assertEqual(projected.linear, {"a": -1.0, "c": 1.0})
        self.assertEqual(projected.quadratic, {})
        self.assertEqual(projected.offset, 4.0)

    def test_categorical_all_free_partial_and_fully_clamped_projection(self) -> None:
        model = _categorical_model()
        for clamps in ({}, {"y": 1}, {"x": "green", "y": 2, "z": "off"}):
            with self.subTest(clamps=clamps):
                program = ThermodynamicProgram(model, clamps=clamps)
                _assert_projection_equivalent(self, program)
        partial = ThermodynamicProgram(model, clamps={"y": 1}).project()
        self.assertEqual(partial.variables, ("x", "z"))
        self.assertEqual(partial.domains["x"], ("red", "green"))
        self.assertEqual(partial.pairwise, {})
        full = ThermodynamicProgram(
            model,
            clamps={"x": "green", "y": 2, "z": "off"},
        ).project()
        self.assertEqual(full.variables, ())
        self.assertEqual(full.domains, {})
        self.assertTrue(
            math.isclose(
                full.offset,
                model.energy({"x": "green", "y": 2, "z": "off"}),
                rel_tol=0.0,
                abs_tol=TOLERANCE,
            )
        )

    def test_source_factor_lineage_survives_linear_and_constant_projection(self) -> None:
        program = ThermodynamicProgram(
            _ising_model(),
            clamps={"b": -1},
            factor_sources={
                "linear:1": "input:bias-b",
                "quadratic:0:1": "input:edge-ab",
                "quadratic:1:2": "input:edge-bc",
            },
        )
        transformations = program.project().metadata["thermodynamic_projection"]["transformations"]
        by_source = {row["source_id"]: row for row in transformations}
        self.assertEqual(by_source["input:bias-b"]["target_kind"], "offset")
        self.assertEqual(by_source["input:edge-ab"]["target_kind"], "linear")
        self.assertEqual(by_source["input:edge-bc"]["target_kind"], "linear")

    def test_projection_lineage_uses_destination_positions_after_early_clamp(self) -> None:
        cases = (
            (
                ThermodynamicProgram(_ising_model(), clamps={"a": 1}),
                {
                    "linear:1": {"target_kind": "linear", "variable_position": 0},
                    "linear:2": {"target_kind": "linear", "variable_position": 1},
                    "quadratic:0:1": {"target_kind": "linear", "variable_position": 0},
                    "quadratic:1:2": {
                        "target_kind": "quadratic",
                        "left_position": 0,
                        "right_position": 1,
                    },
                },
            ),
            (
                ThermodynamicProgram(_categorical_model(), clamps={"x": "green"}),
                {
                    "unary:1": {"target_kind": "unary", "variable_position": 0},
                    "unary:2": {"target_kind": "unary", "variable_position": 1},
                    "pairwise:0:1": {"target_kind": "unary", "variable_position": 0},
                    "pairwise:1:2": {
                        "target_kind": "pairwise",
                        "left_position": 0,
                        "right_position": 1,
                    },
                },
            ),
        )
        for program, expected_by_factor in cases:
            with self.subTest(model_type=type(program.model).__name__):
                projected = program.project()
                projection_metadata = projected.metadata["thermodynamic_projection"]
                self.assertEqual(projection_metadata["clamped_variable_positions"], [0])
                transformations = projection_metadata["transformations"]
                by_factor = {row["factor_id"]: row for row in transformations}
                for factor_id, expected_target in expected_by_factor.items():
                    self.assertEqual(
                        {key: by_factor[factor_id][key] for key in expected_target},
                        expected_target,
                    )

    def test_offset_shift_and_spin_gauge_metamorphisms(self) -> None:
        shift = 8.5
        base = _ising_model()
        shifted = _ising_model(offset=base.offset + shift)
        base_projection = ThermodynamicProgram(base, clamps={"b": -1}).project()
        shifted_projection = ThermodynamicProgram(shifted, clamps={"b": -1}).project()
        for assignment in _all_assignments(base_projection):
            self.assertTrue(
                math.isclose(
                    shifted_projection.energy(assignment),
                    base_projection.energy(assignment) + shift,
                    rel_tol=0.0,
                    abs_tol=TOLERANCE,
                )
            )

        flipped = {"a", "b"}
        gauged = IsingModel(
            variables=base.variables,
            linear={
                variable: -coefficient if variable in flipped else coefficient
                for variable, coefficient in base.linear.items()
            },
            quadratic={
                pair: -coefficient if (pair[0] in flipped) != (pair[1] in flipped) else coefficient
                for pair, coefficient in base.quadratic.items()
            },
            offset=base.offset,
        )
        projected = ThermodynamicProgram(base, clamps={"b": -1}).project()
        gauged_projected = ThermodynamicProgram(gauged, clamps={"b": 1}).project()
        for assignment in _all_assignments(projected):
            gauged_assignment = {
                variable: -value if variable in flipped else value for variable, value in assignment.items()
            }
            self.assertTrue(
                math.isclose(
                    projected.energy(assignment),
                    gauged_projected.energy(gauged_assignment),
                    rel_tol=0.0,
                    abs_tol=TOLERANCE,
                )
            )


class ReconstructionAndSerializationTests(unittest.TestCase):
    def test_with_clamps_reconstructs_without_mutating_original(self) -> None:
        original = ThermodynamicProgram(_ising_model(), clamps={"a": -1, "b": 1})
        rebuilt = original.with_clamps({"a": -1})
        self.assertEqual(original.clamped_variables, ("a", "b"))
        self.assertEqual(rebuilt.clamped_variables, ("a",))
        _assert_projection_equivalent(self, original)
        _assert_projection_equivalent(self, rebuilt)

    def test_relabeling_reconstructs_both_model_types_and_preserves_energy(self) -> None:
        for program in (
            ThermodynamicProgram(_ising_model(), clamps={"b": -1}, coordinates={"a": (0,)}),
            ThermodynamicProgram(_categorical_model(), clamps={"y": 1}, coordinates={"z": (2,)}),
        ):
            mapping = {
                variable: ("renamed", position) for position, variable in enumerate(program.model.variables)
            }
            relabeled = program.relabel_variables(mapping)
            self.assertEqual(
                relabeled.model.variables,
                tuple(mapping[variable] for variable in program.model.variables),
            )
            self.assertEqual(
                relabeled.clamped_variables,
                tuple(mapping[variable] for variable in program.clamped_variables),
            )
            projected = program.project()
            relabeled_projected = relabeled.project()
            for assignment in _all_assignments(projected):
                mapped_assignment = {mapping[key]: value for key, value in assignment.items()}
                self.assertTrue(
                    math.isclose(
                        projected.energy(assignment),
                        relabeled_projected.energy(mapped_assignment),
                        rel_tol=0.0,
                        abs_tol=TOLERANCE,
                    )
                )

    def test_relabeling_rejects_missing_unknown_and_colliding_targets(self) -> None:
        program = ThermodynamicProgram(_ising_model())
        cases = (
            ({"a": "x"}, "match variables exactly"),
            ({"a": "x", "b": "y", "c": "z", "missing": "q"}, "match variables exactly"),
            ({"a": "x", "b": "x", "c": "z"}, "unique"),
        )
        for mapping, message in cases:
            with self.subTest(mapping=mapping), self.assertRaisesRegex(ValueError, message):
                program.relabel_variables(mapping)

    def test_relabeling_identity_and_overlapping_permutation_are_immutable(self) -> None:
        program = ThermodynamicProgram(
            _ising_model(),
            clamps={"b": -1},
            coordinates={"a": (0.0,), "b": (1.0,)},
        )
        identity = {variable: variable for variable in program.model.variables}
        self.assertEqual(program.relabel_variables(identity).to_dict(), program.to_dict())

        permutation = {"a": "b", "b": "c", "c": "a"}
        relabeled = program.relabel_variables(permutation)
        self.assertEqual(program.model.variables, ("a", "b", "c"))
        self.assertEqual(relabeled.model.variables, ("b", "c", "a"))
        self.assertEqual(relabeled.clamp_values["c"], -1)
        original_projection = program.project()
        relabeled_projection = relabeled.project()
        for assignment in _all_assignments(original_projection):
            mapped_assignment = {permutation[variable]: value for variable, value in assignment.items()}
            self.assertTrue(
                math.isclose(
                    original_projection.energy(assignment),
                    relabeled_projection.energy(mapped_assignment),
                    rel_tol=0.0,
                    abs_tol=TOLERANCE,
                )
            )

    def test_categorical_relabeling_preserves_pair_normalization_evidence(self) -> None:
        variables = ("a", "b", "c", "d")
        domains = {variable: (0, 1) for variable in variables}
        model = CategoricalModel(
            variables=variables,
            domains=domains,
            pairwise={
                # Canonical pair positions are reversed, forward, reversed.
                ("b", "a"): {(b, a): float(10 * a + b) for b in (0, 1) for a in (0, 1)},
                ("a", "c"): {(a, c): float(20 + 2 * a - 3 * c) for a in (0, 1) for c in (0, 1)},
                ("d", "b"): {(d, b): float(40 + 5 * b - d) for d in (0, 1) for b in (0, 1)},
            },
        )
        program = ThermodynamicProgram(model)
        mapping = {variable: ("renamed", position) for position, variable in enumerate(variables)}

        identity = program.relabel_variables({variable: variable for variable in variables})
        renamed = program.relabel_variables(mapping)

        self.assertEqual(tuple(model.pairwise), (("a", "b"), ("a", "c"), ("b", "d")))
        self.assertEqual(model.reversed_pair_count, 2)
        self.assertEqual(identity.to_dict(), program.to_dict())
        self.assertEqual(renamed.model.reversed_pair_count, model.reversed_pair_count)
        for assignment in _all_assignments(model):
            mapped_assignment = {mapping[variable]: value for variable, value in assignment.items()}
            self.assertTrue(
                math.isclose(
                    model.energy(assignment),
                    renamed.model.energy(mapped_assignment),
                    rel_tol=0.0,
                    abs_tol=TOLERANCE,
                )
            )

    def test_reconstruction_preserves_set_shaped_metadata(self) -> None:
        model = IsingModel(
            variables=("a", "b"),
            linear={"a": 0.5, "b": -0.25},
            quadratic={("a", "b"): 1.0},
            metadata={"model_tags": {"source", "audited"}},
        )
        program = ThermodynamicProgram(
            model,
            clamps={"b": 1},
            observations={"b": {"observation_tags": {"sensor", "fixed"}}},
            metadata={"program_tags": {"logical", "immutable"}},
        )
        original_payload = program.to_dict()

        rebuilt = program.with_clamps({"b": 1})
        relabeled = program.relabel_variables({"a": "x", "b": "y"})
        projected = program.project()
        result = SampleResult.from_program(program, ({"a": -1},))

        self.assertEqual(rebuilt.to_dict()["metadata"], original_payload["metadata"])
        self.assertEqual(
            rebuilt.to_dict()["observations"][0]["metadata"],
            original_payload["observations"][0]["metadata"],
        )
        self.assertEqual(
            relabeled.to_dict()["model"]["metadata"],
            original_payload["model"]["metadata"],
        )
        self.assertEqual(relabeled.to_dict()["metadata"], original_payload["metadata"])
        self.assertEqual(
            relabeled.to_dict()["observations"][0]["metadata"],
            original_payload["observations"][0]["metadata"],
        )
        self.assertIs(type(projected.metadata["model_tags"]), frozenset)
        self.assertIs(
            type(result.metadata["thermodynamic_program_metadata"]["program_tags"]),
            frozenset,
        )

    def test_serialization_is_versioned_deterministic_json_safe_and_lossless(self) -> None:
        first = ("node", 1)
        second = b"node-2"
        model = IsingModel(
            variables=(first, second),
            linear={first: 0.5, second: -0.75},
            quadratic={(first, second): 1.25},
            offset=-2.0,
            metadata={"tags": ["typed-labels", 3]},
        )
        program = ThermodynamicProgram(
            model,
            clamps=[(second, -1)],
            coordinates={first: (0, 1), second: (1, 1)},
            observations={second: {"bytes": b"observed"}},
            factor_sources={"quadratic:0:1": "input:edge-7"},
            metadata={"nested": {"tuple": (1, "two")}},
        )
        payload = program.to_dict()
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        restored = ThermodynamicProgram.from_dict(json.loads(encoded))
        self.assertEqual(payload["schema_version"], PROGRAM_SCHEMA_VERSION)
        self.assertEqual(restored.to_dict(), payload)
        self.assertEqual(restored.model.variables, (first, second))
        self.assertEqual(restored.observation_metadata[second]["bytes"], b"observed")
        _assert_projection_equivalent(self, restored)

    def test_tuple_shaped_metadata_uses_list_records_and_preserves_exact_labels(self) -> None:
        program = ThermodynamicProgram(
            IsingModel(variables=("x",), linear={"x": 0.0}, quadratic={}),
            metadata={
                "sequence": ((1,), (True,)),
                (1, "integer-key"): "integer",
                (True, "boolean-key"): "boolean",
                "typed_members": {("integer", 1), ("boolean", True)},
            },
        )

        payload = program.to_dict()
        metadata_items = payload["metadata"]["items"]
        sequence_row = next(
            row for row in metadata_items if row["key"] == {"kind": "str", "value": "sequence"}
        )
        typed_members_row = next(
            row for row in metadata_items if row["key"] == {"kind": "str", "value": "typed_members"}
        )
        restored = ThermodynamicProgram.from_dict(
            json.loads(json.dumps(payload, sort_keys=True, allow_nan=False))
        )

        self.assertEqual(sequence_row["value"]["kind"], "list")
        self.assertEqual(
            [item["kind"] for item in sequence_row["value"]["items"]],
            ["list", "list"],
        )
        self.assertIs(type(restored.metadata["sequence"][0][0]), int)
        self.assertIs(type(restored.metadata["sequence"][1][0]), bool)
        self.assertEqual(typed_members_row["value"]["kind"], "frozenset")
        self.assertEqual(
            restored.metadata["typed_members"],
            frozenset({("integer", 1), ("boolean", True)}),
        )
        self.assertEqual(restored.metadata[(1, "integer-key")], "integer")
        self.assertEqual(restored.metadata[(True, "boolean-key")], "boolean")
        self.assertEqual(restored.to_dict(), payload)

    def test_non_ascii_frozenset_metadata_round_trip(self) -> None:
        # "é" sorts after "f" by raw code point but before it once JSON
        # ASCII-escapes it to "é", so these members detect any
        # escaped-order emission the decoder's canonical check rejects.
        program = ThermodynamicProgram(
            IsingModel(variables=("x",), linear={"x": 0.0}, quadratic={}),
            metadata={
                "tags": frozenset({"é", "f"}),
                "nested": {"π": [frozenset({"ß", "s"})]},
                frozenset({"é", "f"}): "label-key-control",
            },
        )

        payload = program.to_dict()
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        restored = ThermodynamicProgram.from_dict(json.loads(encoded))

        self.assertEqual(restored.metadata["tags"], frozenset({"é", "f"}))
        self.assertEqual(restored.metadata["nested"]["π"], [frozenset({"ß", "s"})])
        self.assertEqual(restored.metadata[frozenset({"é", "f"})], "label-key-control")
        self.assertEqual(restored.to_dict(), payload)

        # Oracle: emitted member order equals the raw (unescaped) canonical
        # order recomputed here without touching program internals.
        tags_row = next(
            row for row in payload["metadata"]["items"] if row["key"] == {"kind": "str", "value": "tags"}
        )
        raw_order = sorted(
            tags_row["value"]["items"],
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        )
        self.assertEqual(tags_row["value"]["items"], raw_order)

    def test_serialization_rejects_bool_and_float_schema_version_aliases(self) -> None:
        for invalid_version in (True, 1.0):
            with self.subTest(invalid_version=invalid_version):
                payload = ThermodynamicProgram(_ising_model()).to_dict()
                payload["schema_version"] = invalid_version
                with self.assertRaisesRegex(ValueError, "unsupported.*schema version"):
                    ThermodynamicProgram.from_dict(payload)

    def test_serialization_rejects_noncanonical_or_lossy_typed_labels(self) -> None:
        noncanonical_integer = ThermodynamicProgram(
            IsingModel(variables=(1,), linear={1: 0.0}, quadratic={})
        ).to_dict()
        noncanonical_integer["model"]["variables"][0]["value"] = "01"

        duplicate_frozenset = ThermodynamicProgram(
            IsingModel(
                variables=(frozenset({"a", "b"}),),
                linear={frozenset({"a", "b"}): 0.0},
                quadratic={},
            )
        ).to_dict()
        duplicate_frozenset["model"]["variables"][0] = {
            "kind": "frozenset",
            "items": [
                {"kind": "bool", "value": True},
                {"kind": "int", "value": "1"},
            ],
        }

        for payload in (noncanonical_integer, duplicate_frozenset):
            with (
                self.subTest(payload=payload),
                self.assertRaisesRegex(
                    ValueError,
                    "canonical|duplicate",
                ),
            ):
                ThermodynamicProgram.from_dict(payload)

    def test_serialization_normalizes_unordered_input_and_detects_duplicate_records(self) -> None:
        model = _ising_model()
        forward = ThermodynamicProgram(model, clamps={"a": -1, "c": 1})
        reverse = ThermodynamicProgram(model, clamps=[("c", 1), ("a", -1)])
        self.assertEqual(forward.to_dict(), reverse.to_dict())

        payload = forward.to_dict()
        payload["clamps"].append({"variable": 0, "value": {"kind": "int", "value": "1"}})
        with self.assertRaisesRegex(ValueError, "conflicting clamps"):
            ThermodynamicProgram.from_dict(payload)

    def test_categorical_round_trip_preserves_pair_normalization_evidence(self) -> None:
        model = CategoricalModel(
            variables=("left", "right"),
            domains={"left": (0, 1), "right": ("off", "on")},
            pairwise={
                ("right", "left"): {
                    (right, left): float(left + (2 if right == "on" else 0))
                    for right in ("off", "on")
                    for left in (0, 1)
                }
            },
            offset=-0.75,
        )
        self.assertEqual(model.reversed_pair_count, 1)
        program = ThermodynamicProgram(
            model,
            clamps={"right": "on"},
            factor_sources={"pairwise:0:1": "input:reversed-edge"},
        )
        payload = program.to_dict()
        restored = ThermodynamicProgram.from_dict(
            json.loads(json.dumps(payload, sort_keys=True, allow_nan=False))
        )

        self.assertEqual(restored.to_dict(), payload)
        self.assertEqual(restored.model.reversed_pair_count, 1)
        _assert_projection_equivalent(self, restored)

    def test_fully_clamped_and_empty_constant_models_round_trip(self) -> None:
        cases = (
            (
                _ising_model(),
                {"a": 1, "b": -1, "c": 1},
            ),
            (
                _categorical_model(),
                {"x": "green", "y": 2, "z": "off"},
            ),
        )
        for model, clamps in cases:
            with self.subTest(model_type=type(model).__name__):
                full = ThermodynamicProgram(model, clamps=clamps)
                restored_full = ThermodynamicProgram.from_dict(
                    json.loads(json.dumps(full.to_dict(), sort_keys=True, allow_nan=False))
                )
                _assert_projection_equivalent(self, restored_full)
                constant = restored_full.project()
                self.assertEqual(constant.variables, ())

                empty_program = ThermodynamicProgram(constant)
                restored_empty = ThermodynamicProgram.from_dict(
                    json.loads(json.dumps(empty_program.to_dict(), sort_keys=True, allow_nan=False))
                )
                self.assertIs(type(restored_empty.model), type(model))
                self.assertEqual(restored_empty.model.variables, ())
                self.assertTrue(
                    math.isclose(
                        restored_empty.model.offset,
                        model.energy(clamps),
                        rel_tol=0.0,
                        abs_tol=TOLERANCE,
                    )
                )

    def test_serialized_factor_sources_are_complete_and_pairs_are_canonical(self) -> None:
        payload = ThermodynamicProgram(_ising_model()).to_dict()
        payload["factor_sources"].pop()
        with self.assertRaisesRegex(ValueError, "factor sources.*complete"):
            ThermodynamicProgram.from_dict(payload)

        payload = ThermodynamicProgram(_ising_model()).to_dict()
        payload["model"]["quadratic"][0]["left"] = 1
        payload["model"]["quadratic"][0]["right"] = 0
        with self.assertRaisesRegex(ValueError, "canonical variable order"):
            ThermodynamicProgram.from_dict(payload)

    def test_opaque_labels_work_in_memory_and_fail_serialization_without_repr(self) -> None:
        class Opaque:
            repr_calls = 0

            def __repr__(self) -> str:
                self.repr_calls += 1
                return "opaque-address-like"

        left = Opaque()
        right = Opaque()
        model = IsingModel(
            variables=(left, right),
            linear={left: 0.5, right: -0.25},
            quadratic={(left, right): 1.0},
        )
        program = ThermodynamicProgram(model, clamps={right: 1})
        left.repr_calls = 0
        right.repr_calls = 0
        projected = program.project()
        self.assertEqual((left.repr_calls, right.repr_calls), (0, 0))
        self.assertEqual(projected.variables, (left,))
        with self.assertRaisesRegex(TypeError, "unsupported.*label"):
            program.to_dict()
        self.assertEqual((left.repr_calls, right.repr_calls), (0, 0))

    def test_categorical_project_and_relabel_do_not_repr_valid_labels(self) -> None:
        class Opaque:
            def __init__(self) -> None:
                self.repr_calls = 0

            def __repr__(self) -> str:
                self.repr_calls += 1
                return "opaque-address-like"

        source_variables = (Opaque(), Opaque(), Opaque())
        target_variables = (Opaque(), Opaque(), Opaque())
        categories = (
            (Opaque(), Opaque()),
            (Opaque(), Opaque()),
            (Opaque(), Opaque()),
        )
        domains = dict(zip(source_variables, categories))
        left, right = source_variables[1:]
        model = CategoricalModel(
            variables=source_variables,
            domains=domains,
            pairwise={
                (left, right): {
                    (left_category, right_category): 0.0
                    for left_category in categories[1]
                    for right_category in categories[2]
                }
            },
        )
        program = ThermodynamicProgram(
            model,
            clamps={source_variables[0]: categories[0][0]},
        )
        tracked_labels = (
            source_variables
            + target_variables
            + tuple(category for domain in categories for category in domain)
        )
        for label in tracked_labels:
            label.repr_calls = 0

        program.project()
        self.assertEqual([label.repr_calls for label in tracked_labels], [0] * len(tracked_labels))

        program.relabel_variables(dict(zip(source_variables, target_variables)))
        self.assertEqual([label.repr_calls for label in tracked_labels], [0] * len(tracked_labels))


class ResultIntegrationTests(unittest.TestCase):
    def test_from_program_expands_spin_and_binary_samples_and_records_clamps(self) -> None:
        program = ThermodynamicProgram(_ising_model(), clamps={"b": -1})
        spin_rows = ({"a": -1, "c": 1}, {"a": 1, "c": -1})
        spin_result = SampleResult.from_program(program, spin_rows, vartype="SPIN")
        self.assertEqual(spin_result.variables, ("a", "b", "c"))
        self.assertEqual(dict(spin_result.samples[0]), {"a": -1, "b": -1, "c": 1})
        self.assertEqual(spin_result.metadata["thermodynamic_program_schema"], PROGRAM_SCHEMA_VERSION)
        self.assertEqual(spin_result.metadata["clamped_variable_positions"], [1])
        for index, sample in enumerate(spin_result.samples):
            self.assertTrue(
                math.isclose(
                    spin_result.energies[index],
                    program.model.energy(sample),
                    rel_tol=0.0,
                    abs_tol=TOLERANCE,
                )
            )

        binary_rows = ({"a": 0, "c": 1},)
        binary_result = SampleResult.from_program(program, binary_rows, vartype="BINARY")
        self.assertEqual(dict(binary_result.samples[0]), {"a": 0, "b": 0, "c": 1})
        self.assertTrue(
            math.isclose(
                binary_result.energies[0],
                program.model.energy(binary_result.samples[0], vartype="BINARY"),
                rel_tol=0.0,
                abs_tol=TOLERANCE,
            )
        )

    def test_from_program_canonical_provenance_cannot_be_overridden(self) -> None:
        program = ThermodynamicProgram(
            _ising_model(),
            clamps={"b": -1},
            metadata={"run": "program-evidence"},
        )
        result = SampleResult.from_program(
            program,
            ({"a": -1, "c": 1},),
            metadata={
                "thermodynamic_program_schema": 999,
                "clamped_variable_positions": [0],
                "thermodynamic_program_metadata": {"run": "forged"},
            },
        )

        self.assertEqual(result.metadata["thermodynamic_program_schema"], PROGRAM_SCHEMA_VERSION)
        self.assertEqual(result.metadata["clamped_variable_positions"], [1])
        self.assertEqual(
            result.metadata["thermodynamic_program_metadata"],
            {"run": "program-evidence"},
        )


if __name__ == "__main__":
    unittest.main()
