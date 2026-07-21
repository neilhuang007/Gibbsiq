"""TM-IMP-001 contracts for the factor-JSON and NetworkX frontends.

Every expected energy in this module is evaluated directly from the source
document or graph data by test-local code.  The importers and the exported
model's energy helper are never used to construct an expected value.
"""

from __future__ import annotations

import copy
import itertools
import json
import random
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.importers import (  # noqa: E402
    FACTOR_GRAPH_SCHEMA_VERSION,
    factor_json_from_program,
    program_from_factor_json,
    program_from_networkx,
)
from gibbsiq.model import IsingModel  # noqa: E402
from gibbsiq.program import ThermodynamicProgram  # noqa: E402

try:
    import networkx
except ImportError:  # pragma: no cover - environment-dependent
    networkx = None  # type: ignore[assignment]

TOLERANCE = 1e-9


def spin_document() -> dict:
    """Canonical three-variable SPIN document with every optional section."""
    return {
        "format": "gibbsiq-factor-graph",
        "schema_version": 1,
        "vartype": "SPIN",
        "offset": 1.25,
        "variables": [
            {"kind": "str", "value": "a"},
            {"kind": "int", "value": "7"},
            {"kind": "tuple", "items": [{"kind": "str", "value": "n"}, {"kind": "bool", "value": True}]},
        ],
        "factors": [
            {"scope": [0], "coefficient": 0.5, "source_id": "linear:0"},
            {"scope": [1], "coefficient": -1.0, "source_id": "linear:1"},
            {"scope": [2], "coefficient": 0.0, "source_id": "linear:2"},
            {"scope": [0, 1], "coefficient": 1.5, "source_id": "quadratic:0:1"},
            {"scope": [1, 2], "coefficient": -0.75, "source_id": "external:coupler-9"},
        ],
        "clamps": [{"position": 1, "value": -1}],
        "coordinates": [
            {"position": 0, "coordinate": [0.0, 0.0]},
            {"position": 1, "coordinate": [1.0, 0.0]},
            {"position": 2, "coordinate": [0.0, 1.0]},
        ],
        "observations": [{"position": 1, "metadata": {"sensor": "left"}}],
        "metadata": {"instance": "unit-3", "weights": [1, 2.5, True, None], "nested": {"depth": 2}},
    }


def binary_document() -> dict:
    """Two-variable BINARY document exercising the QUBO conversion path."""
    return {
        "format": "gibbsiq-factor-graph",
        "schema_version": 1,
        "vartype": "BINARY",
        "offset": 0.75,
        "variables": [
            {"kind": "str", "value": "x"},
            {"kind": "str", "value": "y"},
        ],
        "factors": [
            {"scope": [0], "coefficient": 2.0},
            {"scope": [1], "coefficient": -3.0},
            {"scope": [0, 1], "coefficient": 4.0},
        ],
        "clamps": [{"position": 1, "value": 1}],
    }


def direct_document_energy(document: dict, values: tuple) -> float:
    """Independent oracle: evaluate the document without any importer code."""
    total = document["offset"]
    for factor in document["factors"]:
        term = factor["coefficient"]
        for position in factor["scope"]:
            term *= values[position]
        total += term
    return total


def direct_graph_energy(nodes: list, edges: list, offset: float, values: dict) -> float:
    """Independent oracle over raw (label, attrs) node and (u, v, attrs) edge lists."""
    total = offset
    for label, attrs in nodes:
        total += attrs.get("bias", 0.0) * values[label]
    for left, right, attrs in edges:
        total += attrs["weight"] * values[left] * values[right]
    return total


class _StubGraph:
    """Duck-typed stand-in for the consumed NetworkX Graph API surface."""

    def __init__(self, nodes, edges, graph=None, directed=False, multigraph=False):
        self._nodes = list(nodes)
        self._edges = list(edges)
        self._directed = directed
        self._multigraph = multigraph
        self.graph = dict(graph or {})

    def is_directed(self) -> bool:
        return self._directed

    def is_multigraph(self) -> bool:
        return self._multigraph

    def nodes(self, data: bool = False):
        return list(self._nodes) if data else [label for label, _ in self._nodes]

    def edges(self, data: bool = False):
        if data:
            return [(left, right, attrs) for left, right, attrs in self._edges]
        return [(left, right) for left, right, _ in self._edges]


class FactorJsonImportTests(unittest.TestCase):
    def test_spin_document_energies_match_direct_evaluation(self) -> None:
        document = spin_document()
        program = program_from_factor_json(document)

        self.assertEqual(program.model.variables, ("a", 7, ("n", True)))
        self.assertIs(type(program.model.variables[1]), int)
        self.assertIs(type(program.model.variables[2][1]), bool)
        for values in itertools.product((-1, 1), repeat=3):
            sample = dict(zip(program.model.variables, values))
            self.assertAlmostEqual(
                program.model.energy(sample),
                direct_document_energy(document, values),
                places=12,
            )

    def test_spin_document_roles_and_sections(self) -> None:
        document = spin_document()
        program = program_from_factor_json(document)

        self.assertEqual(program.clamped_variables, (7,))
        self.assertEqual(program.clamp_values[7], -1)
        self.assertEqual(program.logical_coordinates["a"], (0.0, 0.0))
        self.assertEqual(program.coordinate_dimension, 2)
        self.assertEqual(program.observation_metadata[7], {"sensor": "left"})
        self.assertEqual(program.metadata["instance"], "unit-3")
        self.assertEqual(program.metadata["weights"], [1, 2.5, True, None])
        self.assertIs(type(program.metadata["weights"][2]), bool)
        self.assertIs(type(program.metadata["weights"][0]), int)
        self.assertEqual(program.factor_sources["quadratic:1:2"], "external:coupler-9")
        self.assertEqual(program.factor_sources["linear:0"], "linear:0")

    def test_clamped_projection_matches_direct_substitution(self) -> None:
        document = spin_document()
        projected = program_from_factor_json(document).project()

        self.assertEqual(projected.variables, ("a", ("n", True)))
        for free_values in itertools.product((-1, 1), repeat=2):
            values = (free_values[0], -1, free_values[1])
            sample = dict(zip(projected.variables, free_values))
            self.assertAlmostEqual(
                projected.energy(sample),
                direct_document_energy(document, values),
                places=12,
            )

    def test_binary_document_energies_match_direct_evaluation(self) -> None:
        document = binary_document()
        program = program_from_factor_json(document)

        self.assertEqual(program.model.variables, ("x", "y"))
        for bits in itertools.product((0, 1), repeat=2):
            sample = dict(zip(program.model.variables, bits))
            self.assertAlmostEqual(
                program.model.energy(sample, vartype="BINARY"),
                direct_document_energy(document, bits),
                places=12,
            )

    def test_binary_clamp_bit_maps_to_spin(self) -> None:
        program = program_from_factor_json(binary_document())
        self.assertEqual(program.clamp_values["y"], 1)

        zero_clamp = binary_document()
        zero_clamp["clamps"] = [{"position": 1, "value": 0}]
        self.assertEqual(program_from_factor_json(zero_clamp).clamp_values["y"], -1)

    def test_optional_sections_default_empty(self) -> None:
        document = {
            "format": "gibbsiq-factor-graph",
            "schema_version": 1,
            "vartype": "SPIN",
            "offset": 0.0,
            "variables": [{"kind": "str", "value": "solo"}],
            "factors": [],
        }
        program = program_from_factor_json(document)

        self.assertEqual(program.model.variables, ("solo",))
        self.assertEqual(program.model.linear["solo"], 0.0)
        self.assertEqual(program.clamped_variables, ())
        self.assertEqual(dict(program.metadata), {})
        self.assertEqual(program.model.energy({"solo": 1}), 0.0)

    def test_zero_variable_document_is_a_constant_model(self) -> None:
        document = {
            "format": "gibbsiq-factor-graph",
            "schema_version": 1,
            "vartype": "SPIN",
            "offset": -2.5,
            "variables": [],
            "factors": [],
        }
        program = program_from_factor_json(document)
        self.assertEqual(program.model.variables, ())
        self.assertEqual(program.model.energy({}), -2.5)

    def test_typed_labels_survive_import(self) -> None:
        document = {
            "format": "gibbsiq-factor-graph",
            "schema_version": 1,
            "vartype": "SPIN",
            "offset": 0.0,
            "variables": [
                {"kind": "none"},
                {"kind": "bool", "value": True},
                {"kind": "float", "value": (2.5).hex()},
                {"kind": "bytes", "value": "AQI="},
                {"kind": "frozenset", "items": [{"kind": "str", "value": "m"}]},
            ],
            "factors": [{"scope": [0, 4], "coefficient": 1.0}],
        }
        program = program_from_factor_json(document)
        variables = program.model.variables

        self.assertEqual(variables, (None, True, 2.5, b"\x01\x02", frozenset({"m"})))
        self.assertIs(type(variables[1]), bool)
        self.assertIs(type(variables[2]), float)
        self.assertIs(type(variables[3]), bytes)


class FactorJsonRejectionTests(unittest.TestCase):
    def _reject(self, document: dict, message: str) -> None:
        with self.assertRaisesRegex(ValueError, message):
            program_from_factor_json(document)

    def _mutated(self, **overrides) -> dict:
        document = spin_document()
        document.update(overrides)
        return document

    def test_document_envelope_rejections(self) -> None:
        self._reject(self._mutated(format="other-format"), "document format")
        self._reject(self._mutated(schema_version=2), "schema version")
        self._reject(self._mutated(schema_version=True), "schema version")
        self._reject(self._mutated(schema_version=1.0), "schema version")
        self._reject(self._mutated(vartype="ISING"), "SPIN or BINARY")
        self._reject(self._mutated(unexpected=1), "unknown factor-graph document field")
        for missing in ("format", "schema_version", "vartype", "offset", "variables", "factors"):
            document = spin_document()
            del document[missing]
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                program_from_factor_json(document)
        with self.assertRaisesRegex(ValueError, "document must be a mapping"):
            program_from_factor_json([1, 2])  # type: ignore[arg-type]

    def test_offset_and_coefficient_rejections(self) -> None:
        self._reject(self._mutated(offset=True), "offset")
        self._reject(self._mutated(offset=float("inf")), "offset")
        self._reject(self._mutated(offset="1.0"), "offset")
        for coefficient in (True, "2.0", float("nan")):
            document = spin_document()
            document["factors"][0]["coefficient"] = coefficient
            with self.subTest(coefficient=coefficient):
                self._reject(document, "coefficient")

    def test_factor_scope_rejections(self) -> None:
        cases = (
            ([], "one or two"),
            ([0, 1, 2], "one or two"),
            ([1, 0], "strictly increasing"),
            ([0, 0], "strictly increasing"),
            ([True], "variable position"),
            ([3], "variable position"),
            ([-1], "variable position"),
        )
        for scope, message in cases:
            document = spin_document()
            document["factors"].append({"scope": scope, "coefficient": 1.0})
            with self.subTest(scope=scope):
                self._reject(document, message)

    def test_duplicate_factor_scopes_rejected(self) -> None:
        for scope in ([0], [0, 1]):
            document = spin_document()
            document["factors"].append({"scope": scope, "coefficient": 2.0})
            with self.subTest(scope=scope):
                self._reject(document, "duplicate factor scope")

    def test_factor_record_shape_rejections(self) -> None:
        document = spin_document()
        document["factors"].append({"scope": [0, 2], "coefficient": 1.0, "extra": 1})
        self._reject(document, "unknown factor record field")
        document = spin_document()
        document["factors"].append({"scope": [0, 2]})
        self._reject(document, "coefficient")
        document = spin_document()
        document["factors"].append({"scope": [0, 2], "coefficient": 1.0, "source_id": ""})
        self._reject(document, "source")

    def test_variable_label_rejections(self) -> None:
        document = spin_document()
        document["variables"][1] = {"kind": "int", "value": "07"}
        self._reject(document, "canonical")
        aliased = self._mutated(
            variables=[{"kind": "int", "value": "1"}, {"kind": "float", "value": (1.0).hex()}],
            factors=[],
            clamps=[],
            coordinates=[],
            observations=[],
        )
        self._reject(aliased, "variables must be unique")
        bool_alias = self._mutated(
            variables=[{"kind": "int", "value": "1"}, {"kind": "bool", "value": True}],
            factors=[],
            clamps=[],
            coordinates=[],
            observations=[],
        )
        self._reject(bool_alias, "variables must be unique")
        duplicate = self._mutated(
            variables=[{"kind": "str", "value": "a"}, {"kind": "str", "value": "a"}],
            factors=[],
            clamps=[],
            coordinates=[],
            observations=[],
        )
        self._reject(duplicate, "variables must be unique")

    def test_clamp_rejections(self) -> None:
        spin_cases = (
            ({"position": 0, "value": 0}, "-1 or \\+1"),
            ({"position": 0, "value": True}, "boolean"),
            ({"position": 5, "value": 1}, "variable position"),
            ({"position": 0, "value": 1, "extra": 1}, "unknown clamp record field"),
        )
        for record, message in spin_cases:
            document = spin_document()
            document["clamps"] = [record]
            with self.subTest(record=record):
                self._reject(document, message)

        document = spin_document()
        document["clamps"] = [{"position": 0, "value": 1}, {"position": 0, "value": -1}]
        self._reject(document, "conflicting clamps")

        binary = binary_document()
        binary["clamps"] = [{"position": 0, "value": 2}]
        self._reject(binary, "0 or 1")
        binary = binary_document()
        binary["clamps"] = [{"position": 0, "value": True}]
        self._reject(binary, "0 or 1")

    def test_coordinate_and_observation_rejections(self) -> None:
        document = spin_document()
        document["coordinates"].append({"position": 0, "coordinate": [9.0, 9.0]})
        self._reject(document, "duplicate coordinate position")

        document = spin_document()
        document["coordinates"][0]["coordinate"] = [True, 0.0]
        self._reject(document, "boolean")

        document = spin_document()
        document["observations"].append({"position": 1, "metadata": {"again": 1}})
        self._reject(document, "duplicate observation position")

        document = spin_document()
        document["observations"] = [{"position": 0, "metadata": {"free": 1}}]
        self._reject(document, "must be clamped")

    def test_metadata_rejections(self) -> None:
        document = spin_document()
        document["metadata"] = {1: "coerced"}
        self._reject(document, "exact strings")

        document = spin_document()
        document["metadata"] = {"bad": float("inf")}
        self._reject(document, "finite")

        document = spin_document()
        document["metadata"] = {"bad": {"x", "y"}}
        self._reject(document, "unsupported")


class FactorJsonMetamorphicTests(unittest.TestCase):
    def test_record_order_is_irrelevant(self) -> None:
        document = spin_document()
        shuffled = copy.deepcopy(document)
        random.Random(20260721).shuffle(shuffled["factors"])
        shuffled["coordinates"].reverse()

        original = program_from_factor_json(document)
        reordered = program_from_factor_json(shuffled)
        self.assertEqual(factor_json_from_program(original), factor_json_from_program(reordered))

    def test_json_round_trip_is_identity(self) -> None:
        document = spin_document()
        parsed = json.loads(json.dumps(document, sort_keys=True, allow_nan=False))
        self.assertEqual(
            factor_json_from_program(program_from_factor_json(parsed)),
            factor_json_from_program(program_from_factor_json(document)),
        )

    def test_offset_shift_moves_every_energy(self) -> None:
        document = spin_document()
        shifted = copy.deepcopy(document)
        shifted["offset"] = document["offset"] + 4.5

        base = program_from_factor_json(document).model
        moved = program_from_factor_json(shifted).model
        for values in itertools.product((-1, 1), repeat=3):
            sample = dict(zip(base.variables, values))
            self.assertAlmostEqual(moved.energy(sample) - base.energy(sample), 4.5, places=12)

    def test_binary_document_matches_hand_converted_spin_document(self) -> None:
        # x = (1+s)/2 applied by hand to binary_document():
        # offset' = 0.75 + (2-3)/2 + 4/4, h_x = 2/2 + 4/4, h_y = -3/2 + 4/4, J = 4/4.
        spin_twin = {
            "format": "gibbsiq-factor-graph",
            "schema_version": 1,
            "vartype": "SPIN",
            "offset": 1.25,
            "variables": [{"kind": "str", "value": "x"}, {"kind": "str", "value": "y"}],
            "factors": [
                {"scope": [0], "coefficient": 2.0},
                {"scope": [1], "coefficient": -0.5},
                {"scope": [0, 1], "coefficient": 1.0},
            ],
            "clamps": [{"position": 1, "value": 1}],
        }
        binary = program_from_factor_json(binary_document()).model
        spin = program_from_factor_json(spin_twin).model
        for spins in itertools.product((-1, 1), repeat=2):
            sample = dict(zip(spin.variables, spins))
            self.assertAlmostEqual(binary.energy(sample), spin.energy(sample), places=12)


class FactorJsonExportTests(unittest.TestCase):
    def test_export_import_is_byte_stable_on_canonical_documents(self) -> None:
        document = spin_document()
        exported = factor_json_from_program(program_from_factor_json(document))

        self.assertEqual(exported, document)
        self.assertEqual(
            json.dumps(exported, sort_keys=True, allow_nan=False),
            json.dumps(document, sort_keys=True, allow_nan=False),
        )

    def test_export_of_binary_import_is_an_energy_equal_spin_document(self) -> None:
        document = binary_document()
        program = program_from_factor_json(document)
        exported = factor_json_from_program(program)

        self.assertEqual(exported["vartype"], "SPIN")
        reimported = program_from_factor_json(exported).model
        for bits in itertools.product((0, 1), repeat=2):
            spins = tuple(2 * bit - 1 for bit in bits)
            sample = dict(zip(reimported.variables, spins))
            self.assertAlmostEqual(
                reimported.energy(sample),
                direct_document_energy(document, bits),
                places=12,
            )

    def test_export_from_direct_program_construction(self) -> None:
        model = IsingModel(
            variables=("a", "b"),
            linear={"a": 0.5},
            quadratic={("a", "b"): -1.0},
            offset=2.0,
        )
        program = ThermodynamicProgram(model, clamps={"b": 1}, metadata={"run": 3})
        exported = factor_json_from_program(program)

        self.assertEqual(exported["schema_version"], FACTOR_GRAPH_SCHEMA_VERSION)
        self.assertEqual(exported["offset"], 2.0)
        self.assertEqual(
            exported["factors"],
            [
                {"scope": [0], "coefficient": 0.5, "source_id": "linear:0"},
                {"scope": [1], "coefficient": 0.0, "source_id": "linear:1"},
                {"scope": [0, 1], "coefficient": -1.0, "source_id": "quadratic:0:1"},
            ],
        )
        self.assertEqual(exported["clamps"], [{"position": 1, "value": 1}])
        self.assertEqual(exported["metadata"], {"run": 3})
        restored = program_from_factor_json(json.loads(json.dumps(exported, allow_nan=False)))
        for values in itertools.product((-1, 1), repeat=2):
            sample = dict(zip(model.variables, values))
            self.assertAlmostEqual(restored.model.energy(sample), model.energy(sample), places=12)

    def test_export_rejects_categorical_programs(self) -> None:
        from gibbsiq.categorical import CategoricalModel

        model = CategoricalModel(
            variables=("c",),
            domains={"c": ("red", "blue")},
            unary={"c": {"red": 0.0, "blue": 1.0}},
        )
        with self.assertRaisesRegex(TypeError, "IsingModel"):
            factor_json_from_program(ThermodynamicProgram(model))

    def test_export_rejects_non_json_safe_metadata(self) -> None:
        model = IsingModel(variables=("a",), linear={"a": 0.0}, quadratic={})
        for metadata in ({"raw": b"\x00"}, {"tags": frozenset({"x"})}):
            with self.subTest(metadata=metadata), self.assertRaisesRegex(TypeError, "unsupported"):
                factor_json_from_program(ThermodynamicProgram(model, metadata=metadata))


@unittest.skipUnless(networkx is not None, "networkx is not installed")
class NetworkxImportTests(unittest.TestCase):
    def _ring(self):
        graph = networkx.Graph(offset=0.5, family="ring")
        graph.add_node("a", bias=0.25, clamp=-1)
        graph.add_node("b")
        graph.add_node(("c", 2), bias=-0.75, coordinate=(1.0, 2.0))
        graph.add_edge("a", "b", weight=1.5)
        graph.add_edge("b", ("c", 2), weight=-2.0)
        return graph

    def test_graph_energies_match_direct_evaluation(self) -> None:
        graph = self._ring()
        program = program_from_networkx(graph, vartype="SPIN")
        nodes = list(graph.nodes(data=True))
        edges = list(graph.edges(data=True))

        self.assertEqual(set(program.model.variables), {"a", "b", ("c", 2)})
        for values in itertools.product((-1, 1), repeat=3):
            sample = dict(zip(program.model.variables, values))
            self.assertAlmostEqual(
                program.model.energy(sample),
                direct_graph_energy(nodes, edges, 0.5, sample),
                places=12,
            )

    def test_graph_sections_and_metadata(self) -> None:
        program = program_from_networkx(self._ring(), vartype="SPIN")

        self.assertEqual(program.clamp_values["a"], -1)
        self.assertEqual(program.logical_coordinates[("c", 2)], (1.0, 2.0))
        self.assertEqual(program.metadata["source_format"], "networkx")
        self.assertEqual(
            program.metadata["graph_attributes"],
            {"offset": 0.5, "family": "ring"},
        )

    def test_node_and_edge_insertion_order_is_irrelevant(self) -> None:
        forward = self._ring()
        backward = networkx.Graph(offset=0.5, family="ring")
        backward.add_node(("c", 2), bias=-0.75, coordinate=(1.0, 2.0))
        backward.add_node("b")
        backward.add_node("a", bias=0.25, clamp=-1)
        backward.add_edge(("c", 2), "b", weight=-2.0)
        backward.add_edge("b", "a", weight=1.5)

        first = program_from_networkx(forward, vartype="SPIN")
        second = program_from_networkx(backward, vartype="SPIN")
        self.assertEqual(first.model.variables, second.model.variables)
        self.assertEqual(factor_json_from_program(first), factor_json_from_program(second))

    def test_explicit_node_order_overrides_canonical_order(self) -> None:
        order = ("b", ("c", 2), "a")
        program = program_from_networkx(self._ring(), vartype="SPIN", node_order=order)
        self.assertEqual(program.model.variables, order)
        with self.assertRaisesRegex(ValueError, "node_order"):
            program_from_networkx(self._ring(), vartype="SPIN", node_order=("a", "b"))

    def test_binary_graph_matches_direct_binary_evaluation(self) -> None:
        graph = networkx.Graph()
        graph.add_node(0, bias=2.0)
        graph.add_node(1, bias=-3.0, clamp=1)
        graph.add_edge(0, 1, weight=4.0)
        program = program_from_networkx(graph, vartype="BINARY", offset=0.75)
        nodes = list(graph.nodes(data=True))
        edges = list(graph.edges(data=True))

        self.assertEqual(program.clamp_values[1], 1)
        for bits in itertools.product((0, 1), repeat=2):
            sample = dict(zip(program.model.variables, bits))
            self.assertAlmostEqual(
                program.model.energy(sample, vartype="BINARY"),
                direct_graph_energy(nodes, edges, 0.75, sample),
                places=12,
            )

    def test_isolated_node_survives(self) -> None:
        graph = networkx.Graph()
        graph.add_node("lonely")
        graph.add_edge("u", "v", weight=1.0)
        program = program_from_networkx(graph, vartype="SPIN")
        self.assertIn("lonely", program.model.variables)
        self.assertEqual(program.model.linear["lonely"], 0.0)

    def test_graph_rejections(self) -> None:
        directed = networkx.DiGraph()
        directed.add_edge("a", "b", weight=1.0)
        with self.assertRaisesRegex(ValueError, "directed"):
            program_from_networkx(directed, vartype="SPIN")

        multi = networkx.MultiGraph()
        multi.add_edge("a", "b", weight=1.0)
        with self.assertRaisesRegex(ValueError, "multigraph"):
            program_from_networkx(multi, vartype="SPIN")

        looped = networkx.Graph()
        looped.add_edge("a", "a", weight=1.0)
        with self.assertRaisesRegex(ValueError, "self-loop"):
            program_from_networkx(looped, vartype="SPIN")

        unweighted = networkx.Graph()
        unweighted.add_edge("a", "b")
        with self.assertRaisesRegex(ValueError, "coefficient attribute"):
            program_from_networkx(unweighted, vartype="SPIN")
        program = program_from_networkx(unweighted, vartype="SPIN", default_coefficient=1.0)
        self.assertEqual(program.model.quadratic[("a", "b")], 1.0)

        conflicting = networkx.Graph(offset=1.0)
        conflicting.add_node("a")
        with self.assertRaisesRegex(ValueError, "offset"):
            program_from_networkx(conflicting, vartype="SPIN", offset=2.0)

        boolean_bias = networkx.Graph()
        boolean_bias.add_node("a", bias=True)
        with self.assertRaisesRegex(ValueError, "boolean"):
            program_from_networkx(boolean_bias, vartype="SPIN")

    def test_custom_attribute_names(self) -> None:
        graph = networkx.Graph()
        graph.add_node("a", h=0.5)
        graph.add_edge("a", "b", J=-1.0)
        program = program_from_networkx(
            graph,
            vartype="SPIN",
            linear_attribute="h",
            coefficient_attribute="J",
        )
        self.assertEqual(program.model.linear["a"], 0.5)
        self.assertEqual(program.model.quadratic[("a", "b")], -1.0)


class NetworkxStubTests(unittest.TestCase):
    """The graph frontend consumes a duck-typed API and needs no networkx import."""

    def test_stub_graph_import_matches_direct_evaluation(self) -> None:
        nodes = [("a", {"bias": 0.25}), ("b", {}), ("c", {"bias": -0.75})]
        edges = [("a", "b", {"weight": 1.5}), ("b", "c", {"weight": -2.0})]
        program = program_from_networkx(
            _StubGraph(nodes, edges, graph={"offset": 0.5}),
            vartype="SPIN",
        )
        for values in itertools.product((-1, 1), repeat=3):
            sample = dict(zip(program.model.variables, values))
            self.assertAlmostEqual(
                program.model.energy(sample),
                direct_graph_energy(nodes, edges, 0.5, sample),
                places=12,
            )

    def test_duplicate_and_reversed_stub_edges_rejected(self) -> None:
        nodes = [("a", {}), ("b", {})]
        for second in (("a", "b"), ("b", "a")):
            edges = [("a", "b", {"weight": 1.0}), (*second, {"weight": 2.0})]
            with self.subTest(second=second), self.assertRaisesRegex(ValueError, "duplicate edge"):
                program_from_networkx(_StubGraph(nodes, edges), vartype="SPIN")

    def test_non_graph_objects_rejected(self) -> None:
        for value in ({}, object(), [("a", "b")]):
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "graph"):
                program_from_networkx(value, vartype="SPIN")

    def test_vartype_is_required_and_validated(self) -> None:
        stub = _StubGraph([("a", {})], [])
        with self.assertRaisesRegex(ValueError, "SPIN or BINARY"):
            program_from_networkx(stub, vartype="ising")

    def test_importers_module_never_imports_networkx(self) -> None:
        code = (
            "import sys\n"
            "sys.modules['networkx'] = None\n"
            "import gibbsiq.importers as importers\n"
            "graph = type('Stub', (), {})()\n"
            "graph.graph = {}\n"
            "graph.is_directed = lambda: False\n"
            "graph.is_multigraph = lambda: False\n"
            "graph.nodes = lambda data=False: [('a', {'bias': 1.0})] if data else ['a']\n"
            "graph.edges = lambda data=False: []\n"
            "program = importers.program_from_networkx(graph, vartype='SPIN')\n"
            "assert program.model.linear['a'] == 1.0\n"
            "print('independent')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env={"PYTHONPATH": "src", "SYSTEMROOT": "C:\\Windows", "PATH": ""},
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("independent", result.stdout)


if __name__ == "__main__":
    unittest.main()
