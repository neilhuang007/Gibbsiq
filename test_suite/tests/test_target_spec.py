"""Complete provenanced target and independently enumerated topology contracts."""

from __future__ import annotations

import json
import sys
import unittest
from collections import deque
from dataclasses import FrozenInstanceError
from itertools import product
from pathlib import Path
from typing import TypeVar

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.hardware import (  # noqa: E402
    CommunicationSpec,
    FixedPointSpec,
    HostTransferSpec,
    ParameterProvenance,
    PhysicalQuantity,
    ProgrammingSpec,
    TSUSpec,
)
from gibbsiq.topology import ExplicitTopology, GridTopology  # noqa: E402

NodeT = TypeVar("NodeT")


def assumed(
    source: str = "unit-test scenario",
    *,
    sensitivity_range: tuple[float, float] | None = None,
    sensitivity_unit: str | None = None,
    sensitivity_note: str = "",
) -> ParameterProvenance:
    return ParameterProvenance(
        "assumed",
        source,
        sensitivity_range=sensitivity_range,
        sensitivity_unit=sensitivity_unit,
        sensitivity_note=sensitivity_note,
    )


def modeled(
    source: str = "doi:10.1038/s44335-026-00075-3",
    *,
    sensitivity_range: tuple[float, float] | None = None,
    sensitivity_unit: str | None = None,
) -> ParameterProvenance:
    return ParameterProvenance(
        "modeled",
        source,
        accessed_on="2026-07-15",
        sensitivity_range=sensitivity_range,
        sensitivity_unit=sensitivity_unit,
    )


def quantity(
    value: float,
    unit: str,
    lower: float,
    upper: float,
    *,
    provenance: ParameterProvenance | None = None,
) -> PhysicalQuantity:
    return PhysicalQuantity(
        value=value,
        unit=unit,
        sensitivity_lower=lower,
        sensitivity_upper=upper,
        provenance=modeled() if provenance is None else provenance,
    )


def independent_grid_edges(
    shape: tuple[int, ...],
    origin: tuple[int, ...],
    offsets: tuple[tuple[int, ...], ...],
) -> set[tuple[tuple[int, ...], tuple[int, ...]]]:
    """Enumerate adjacency without consuming ``GridTopology`` derived facts."""
    coordinates = {
        tuple(origin[axis] + local[axis] for axis in range(len(shape)))
        for local in product(*(range(length) for length in shape))
    }
    edges: set[tuple[tuple[int, ...], tuple[int, ...]]] = set()
    for left in coordinates:
        for offset in offsets:
            right = tuple(left[axis] + offset[axis] for axis in range(len(shape)))
            if right in coordinates:
                edges.add(tuple(sorted((left, right))))
    return edges


def independent_degrees(
    nodes: set[tuple[int, ...]],
    edges: set[tuple[tuple[int, ...], tuple[int, ...]]],
) -> dict[tuple[int, ...], int]:
    degrees = {node: 0 for node in nodes}
    for left, right in edges:
        degrees[left] += 1
        degrees[right] += 1
    return degrees


def independent_distance(
    nodes: set[NodeT],
    edges: set[tuple[NodeT, NodeT]],
    start: NodeT,
    stop: NodeT,
) -> int | None:
    adjacency = {node: set() for node in nodes}
    for left, right in edges:
        adjacency[left].add(right)
        adjacency[right].add(left)
    visited = {start}
    queue: deque[tuple[NodeT, int]] = deque([(start, 0)])
    while queue:
        node, depth = queue.popleft()
        if node == stop:
            return depth
        for neighbor in adjacency[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, depth + 1))
    return None


class GridTopologyTests(unittest.TestCase):
    def test_grid_adjacency_capacity_degree_and_distance_match_independent_oracle(self) -> None:
        shape = (3, 4)
        origin = (-2, 7)
        offsets = ((-1, 0), (0, -1), (0, 1), (1, 0))
        topology = GridTopology(
            shape=shape,
            origin=origin,
            neighbor_offsets=reversed(offsets),
            tile_shape=(1, 2),
        )

        expected_edges = independent_grid_edges(shape, origin, offsets)
        nodes = {
            tuple(origin[axis] + local[axis] for axis in range(2))
            for local in product(range(shape[0]), range(shape[1]))
        }
        degrees = independent_degrees(nodes, expected_edges)

        self.assertEqual(topology.capacity, len(nodes))
        self.assertEqual(set(topology.cells()), nodes)
        self.assertEqual(set(topology.edges()), expected_edges)
        self.assertEqual(topology.maximum_degree, max(degrees.values()))
        self.assertEqual(topology.degree((-1, 8)), degrees[(-1, 8)])
        self.assertTrue(topology.allows_edge((-2, 7), (-1, 7)))
        self.assertFalse(topology.allows_edge((-2, 7), (0, 7)))
        self.assertEqual(topology.distance((-2, 7), (0, 10)), 5)
        self.assertEqual(
            topology.to_dict(),
            {
                "kind": "grid",
                "shape": [3, 4],
                "origin": [-2, 7],
                "tile_shape": [1, 2],
                "neighbor_offsets": [[-1, 0], [0, -1], [0, 1], [1, 0]],
            },
        )

    def test_translation_and_reflection_preserve_grid_facts(self) -> None:
        offsets = ((-1, 0), (0, -1), (0, 1), (1, 0))
        original = GridTopology(shape=(2, 3), neighbor_offsets=offsets)
        transformed = GridTopology(
            shape=(2, 3),
            origin=(11, -5),
            neighbor_offsets=tuple((-left, -right) for left, right in reversed(offsets)),
        )

        original_degrees = sorted(original.degree(cell) for cell in original.cells())
        transformed_degrees = sorted(transformed.degree(cell) for cell in transformed.cells())
        self.assertEqual(original.capacity, transformed.capacity)
        self.assertEqual(original.maximum_degree, transformed.maximum_degree)
        self.assertEqual(original_degrees, transformed_degrees)
        self.assertEqual(original.distance((0, 0), (1, 2)), 3)
        self.assertEqual(transformed.distance((11, -5), (12, -3)), 3)

    def test_grid_validation_fails_closed(self) -> None:
        invalid = (
            {"shape": (0, 2), "neighbor_offsets": ()},
            {"shape": (2, 2), "origin": (0,), "neighbor_offsets": ()},
            {"shape": (2, 2), "neighbor_offsets": ((0, 0),)},
            {"shape": (2, 2), "neighbor_offsets": ((1, 0),)},
            {"shape": (2, 2), "neighbor_offsets": ((1, 0), (-1, 0), (1, 0))},
            {"shape": (2, 2), "neighbor_offsets": ((1,), (-1,))},
            {"shape": (3, 4), "neighbor_offsets": (), "tile_shape": (2, 2)},
            {"shape": (2, True), "neighbor_offsets": ()},
        )
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                GridTopology(**kwargs)  # type: ignore[arg-type]

    def test_translated_small_grids_match_independent_oracle(self) -> None:
        offset_families = (
            ((-1, 0), (0, -1), (0, 1), (1, 0)),
            ((-1, -1), (-1, 1), (1, -1), (1, 1)),
            ((-2, 0), (0, -2), (0, 2), (2, 0)),
        )
        case_count = 0
        for rows in range(1, 5):
            for columns in range(1, 5):
                shape = (rows, columns)
                origin = (7 - rows, columns - 9)
                nodes = {
                    (origin[0] + row, origin[1] + column) for row in range(rows) for column in range(columns)
                }
                for offsets in offset_families:
                    topology = GridTopology(
                        shape=shape,
                        origin=origin,
                        neighbor_offsets=tuple(reversed(offsets)),
                    )
                    expected_edges = independent_grid_edges(shape, origin, offsets)
                    degrees = independent_degrees(nodes, expected_edges)
                    self.assertEqual(set(topology.edges()), expected_edges)
                    self.assertEqual(
                        topology.maximum_degree,
                        max(degrees.values(), default=0),
                    )
                    for left in nodes:
                        self.assertEqual(topology.degree(left), degrees[left])
                        for right in nodes:
                            self.assertEqual(
                                topology.distance(left, right),
                                independent_distance(nodes, expected_edges, left, right),
                            )
                    case_count += 1
        self.assertEqual(case_count, 48)


class ExplicitTopologyTests(unittest.TestCase):
    def test_reordered_explicit_graph_has_canonical_adjacency_and_distance(self) -> None:
        first = ExplicitTopology(
            node_count=5,
            edges=((4, 3), (1, 0), (3, 2), (2, 1), (0, 4)),
            tile_shape=(5,),
        )
        second = ExplicitTopology(
            node_count=5,
            edges=((0, 1), (1, 2), (2, 3), (3, 4), (4, 0)),
            tile_shape=(5,),
        )

        expected_edges = {(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)}
        expected_degrees = {node: 0 for node in range(5)}
        for left, right in expected_edges:
            expected_degrees[left] += 1
            expected_degrees[right] += 1

        self.assertEqual(first, second)
        self.assertEqual(set(first.edges), expected_edges)
        self.assertEqual(first.capacity, 5)
        self.assertEqual(first.maximum_degree, max(expected_degrees.values()))
        self.assertEqual(first.degree(3), expected_degrees[3])
        self.assertEqual(first.neighbors(0), (1, 4))
        self.assertEqual(first.distance(0, 3), 2)
        self.assertFalse(first.allows_edge(0, 2))
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_disconnected_explicit_distance_is_unknown(self) -> None:
        topology = ExplicitTopology(node_count=4, edges=((0, 1), (2, 3)))
        self.assertIsNone(topology.distance(0, 3))

    def test_explicit_validation_fails_closed(self) -> None:
        invalid = (
            {"node_count": 0, "edges": ()},
            {"node_count": True, "edges": ()},
            {"node_count": 3, "edges": ((0, 0),)},
            {"node_count": 3, "edges": ((0, 3),)},
            {"node_count": 3, "edges": ((0, 1), (1, 0))},
            {"node_count": 3, "edges": ((False, 1),)},
            {"node_count": 4, "edges": (), "tile_shape": (3,)},
        )
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                ExplicitTopology(**kwargs)  # type: ignore[arg-type]

    def test_all_simple_graphs_through_five_nodes_match_independent_oracle(self) -> None:
        graph_count = 0
        for node_count in range(1, 6):
            possible_edges = tuple(
                (left, right) for left in range(node_count) for right in range(left + 1, node_count)
            )
            nodes = set(range(node_count))
            for edge_mask in range(1 << len(possible_edges)):
                expected_edges = {
                    edge for index, edge in enumerate(possible_edges) if edge_mask & (1 << index)
                }
                topology = ExplicitTopology(
                    node_count=node_count,
                    edges=tuple(reversed(tuple(expected_edges))),
                )
                degrees = {node: 0 for node in nodes}
                for left, right in expected_edges:
                    degrees[left] += 1
                    degrees[right] += 1
                self.assertEqual(set(topology.edges), expected_edges)
                self.assertEqual(topology.maximum_degree, max(degrees.values(), default=0))
                for left in nodes:
                    self.assertEqual(topology.degree(left), degrees[left])
                    for right in nodes:
                        self.assertEqual(
                            topology.distance(left, right),
                            independent_distance(nodes, expected_edges, left, right),
                        )
                graph_count += 1
        self.assertEqual(graph_count, 1_099)


class PhysicalFactTests(unittest.TestCase):
    def test_quantity_requires_canonical_unit_range_and_external_access_date(self) -> None:
        fact = quantity(2e-15, "joule", 1e-15, 4e-15)
        self.assertEqual(fact.value, 2e-15)
        self.assertEqual(fact.to_dict()["sensitivity_range"], [1e-15, 4e-15])

        invalid = (
            {"value": 2.0, "unit": "fJ", "sensitivity_lower": 1.0, "sensitivity_upper": 3.0},
            {
                "value": float("nan"),
                "unit": "joule",
                "sensitivity_lower": 0.0,
                "sensitivity_upper": 3.0,
            },
            {"value": 2.0, "unit": "joule", "sensitivity_lower": 3.0, "sensitivity_upper": 4.0},
            {"value": 2.0, "unit": "joule", "sensitivity_lower": 0.0, "sensitivity_upper": 1.0},
        )
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                PhysicalQuantity(provenance=modeled(), **kwargs)  # type: ignore[arg-type]

        with self.assertRaisesRegex(ValueError, "accessed_on"):
            PhysicalQuantity(
                value=2.0,
                unit="joule",
                sensitivity_lower=1.0,
                sensitivity_upper=3.0,
                provenance=ParameterProvenance("modeled", "doi:example"),
            )

    def test_measured_target_fact_requires_device_artifact(self) -> None:
        measured_without_artifact = ParameterProvenance(
            "measured",
            "device run",
            accessed_on="2026-07-15",
        )
        with self.assertRaisesRegex(ValueError, "evidence_artifact"):
            TSUSpec(
                name="invalid-measurement",
                pbit_capacity=100,
                provenance={"pbit_capacity": measured_without_artifact},
            )

        with self.assertRaisesRegex(ValueError, "evidence_artifact"):
            PhysicalQuantity(
                value=2.0,
                unit="joule",
                sensitivity_lower=1.0,
                sensitivity_upper=3.0,
                provenance=measured_without_artifact,
            )

    def test_v2_modeled_scalar_fact_requires_matching_sensitivity_range(self) -> None:
        topology = GridTopology(shape=(1,), neighbor_offsets=())
        with self.assertRaisesRegex(ValueError, "sensitivity_range"):
            TSUSpec(
                name="missing-sensitivity",
                topology=topology,
                cell_energy_joules=2e-15,
                provenance={
                    "topology": assumed(sensitivity_note="fixed topology scenario"),
                    "cell_energy_joules": modeled(),
                },
            )
        with self.assertRaisesRegex(ValueError, "sensitivity_unit"):
            TSUSpec(
                name="wrong-sensitivity-unit",
                topology=topology,
                cell_energy_joules=2e-15,
                provenance={
                    "topology": assumed(sensitivity_note="fixed topology scenario"),
                    "cell_energy_joules": modeled(
                        sensitivity_range=(1e-15, 4e-15),
                        sensitivity_unit="second",
                    ),
                },
            )

    def test_cost_group_units_and_physical_ranges_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "bit/second"):
            CommunicationSpec(link_bandwidth=quantity(10.0, "second", 5.0, 20.0))
        with self.assertRaisesRegex(ValueError, "positive"):
            HostTransferSpec(bandwidth=quantity(0.0, "bit/second", 0.0, 1.0, provenance=assumed()))
        with self.assertRaisesRegex(ValueError, "non-negative"):
            ProgrammingSpec(
                reprogramming_energy=quantity(
                    -1.0,
                    "joule",
                    -2.0,
                    0.0,
                    provenance=assumed(),
                )
            )


class CompleteTargetTests(unittest.TestCase):
    def test_complete_target_is_immutable_finite_and_deterministic(self) -> None:
        topology = GridTopology(
            shape=(4, 4),
            neighbor_offsets=((1, 0), (0, 1), (-1, 0), (0, -1)),
            tile_shape=(2, 2),
        )
        provenance = {
            "topology": assumed(
                "declared abstract grid",
                sensitivity_note="compare translated/reflected grids and explicit graphs",
            ),
            "pbit_capacity": assumed(
                sensitivity_range=(8, 32),
                sensitivity_unit="count",
            ),
            "max_degree": assumed(
                sensitivity_range=(2, 8),
                sensitivity_unit="count",
            ),
            "max_color_phases": assumed(
                sensitivity_range=(2, 4),
                sensitivity_unit="count",
            ),
            "coefficient_format": assumed(
                "declared coefficient scenario",
                sensitivity_note="compare adjacent integer/fractional bit allocations",
            ),
            "accumulator_format": assumed(
                "declared accumulator scenario",
                sensitivity_note="compare wider accumulator formats",
            ),
            "cell_energy_joules": modeled(
                sensitivity_range=(1e-15, 4e-15),
                sensitivity_unit="joule",
            ),
            "cell_update_seconds": modeled(
                sensitivity_range=(0.5e-7, 2e-7),
                sensitivity_unit="second",
            ),
        }
        target = TSUSpec(
            name="complete-modeled-target",
            topology=topology,
            pbit_capacity=16,
            max_degree=4,
            max_color_phases=2,
            coefficient_format=FixedPointSpec(4, 3),
            accumulator_format=FixedPointSpec(8, 6),
            cell_energy_joules=2e-15,
            cell_update_seconds=1e-7,
            communication=CommunicationSpec(
                clock_frequency=quantity(10e6, "hertz", 5e6, 20e6),
                link_bandwidth=quantity(1e9, "bit/second", 1e8, 1e10),
                link_latency=quantity(2e-9, "second", 1e-9, 10e-9),
                link_energy_per_bit=quantity(0.5e-15, "joule/bit", 0.1e-15, 2e-15),
            ),
            host_transfer=HostTransferSpec(
                bandwidth=quantity(64e9, "bit/second", 16e9, 128e9, provenance=assumed()),
                latency=quantity(5e-6, "second", 1e-6, 20e-6, provenance=assumed()),
                energy_per_bit=None,
            ),
            programming=ProgrammingSpec(
                programming_time=quantity(2e-3, "second", 1e-3, 10e-3, provenance=assumed()),
                programming_energy=None,
                reprogramming_time=quantity(1e-3, "second", 0.5e-3, 5e-3, provenance=assumed()),
                reprogramming_energy=None,
            ),
            provenance=provenance,
        )
        provenance.clear()

        payload = target.to_dict()
        encoded = json.dumps(payload, allow_nan=False, sort_keys=True, separators=(",", ":"))
        reordered = TSUSpec(
            name="complete-modeled-target",
            topology=GridTopology(
                shape=(4, 4),
                neighbor_offsets=((0, -1), (-1, 0), (0, 1), (1, 0)),
                tile_shape=(2, 2),
            ),
            pbit_capacity=16,
            max_degree=4,
            max_color_phases=2,
            coefficient_format=FixedPointSpec(4, 3),
            accumulator_format=FixedPointSpec(8, 6),
            cell_energy_joules=2e-15,
            cell_update_seconds=1e-7,
            communication=target.communication,
            host_transfer=target.host_transfer,
            programming=target.programming,
            provenance={key: target.provenance[key] for key in reversed(tuple(target.provenance))},
        )
        reordered_encoded = json.dumps(
            reordered.to_dict(),
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        self.assertEqual(payload["schema_version"], "tsu-target-v2")
        self.assertEqual(payload["topology"]["kind"], "grid")
        self.assertEqual(payload["accumulator_format"]["total_bits"], 15)
        self.assertIsNone(payload["host_transfer"]["energy_per_bit"])
        self.assertIsNone(payload["programming"]["reprogramming_energy"])
        self.assertEqual(encoded, reordered_encoded)
        with self.assertRaises(FrozenInstanceError):
            target.name = "changed"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            target.provenance["extra"] = assumed()  # type: ignore[index]

    def test_absent_physical_facts_serialize_as_explicit_unknowns(self) -> None:
        payload = TSUSpec("unknown-target").to_dict()
        for field_name in (
            "topology",
            "pbit_capacity",
            "max_degree",
            "max_color_phases",
            "coefficient_format",
            "accumulator_format",
            "cell_energy_joules",
            "cell_update_seconds",
            "communication",
            "host_transfer",
            "programming",
        ):
            with self.subTest(field_name=field_name):
                self.assertIsNone(payload[field_name])
        json.dumps(payload, allow_nan=False)

    def test_topology_capacity_conflict_and_composite_types_fail_closed(self) -> None:
        topology = GridTopology(shape=(2, 3), neighbor_offsets=())
        with self.assertRaisesRegex(ValueError, "topology capacity"):
            TSUSpec(
                name="conflict",
                topology=topology,
                pbit_capacity=5,
                provenance={
                    "topology": assumed(sensitivity_note="fixed topology scenario"),
                    "pbit_capacity": assumed(
                        sensitivity_range=(4, 8),
                        sensitivity_unit="count",
                    ),
                },
            )
        for field_name in ("communication", "host_transfer", "programming"):
            with self.subTest(field_name=field_name), self.assertRaises(ValueError):
                TSUSpec(name="invalid", **{field_name: "unknown"})


if __name__ == "__main__":
    unittest.main()
