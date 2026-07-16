"""Direct TSU-target admissibility and graph-evidence contracts."""

from __future__ import annotations

import json
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.conversions import compile_ising  # noqa: E402
from gibbsiq.hardware import (  # noqa: E402
    FixedPointSpec,
    ParameterProvenance,
    TSUSpec,
)
from gibbsiq.hardware_assessment import assess_target_admissibility  # noqa: E402
from gibbsiq.topology import ExplicitTopology  # noqa: E402


class _OpaqueLabel:
    """Hashable label that the standard JSON encoder cannot serialize."""


def _target(name: str = "test-target", **parameters: Any) -> TSUSpec:
    provenance = {
        parameter: ParameterProvenance("assumed", "unit-test target fixture")
        for parameter, value in parameters.items()
        if value is not None
    }
    return TSUSpec(name=name, provenance=provenance, **parameters)


class LogicalGraphEvidenceTests(unittest.TestCase):
    def test_path_graph_facts_and_constructive_two_phase_schedule(self) -> None:
        variables = tuple(range(5))
        model = compile_ising(
            {variable: 0.125 for variable in variables},
            {(left, left + 1): 0.25 for left in range(4)},
            variables=variables,
        )
        assessment = assess_target_admissibility(
            model,
            _target(
                pbit_capacity=5,
                max_degree=2,
                max_color_phases=2,
                coefficient_format=FixedPointSpec(2, 3),
            ),
        )

        self.assertEqual(assessment.status, "conditional")
        self.assertEqual(assessment.graph.variable_count, 5)
        self.assertEqual(assessment.graph.edge_count, 4)
        self.assertEqual(assessment.graph.maximum_degree, 2)
        self.assertAlmostEqual(assessment.graph.mean_degree, 1.6)
        self.assertEqual(assessment.graph.degree_histogram, ((1, 2), (2, 3)))
        self.assertEqual(assessment.graph.connected_component_sizes, (5,))
        self.assertAlmostEqual(assessment.graph.density, 0.4)
        self.assertEqual(assessment.graph.block_count, 2)
        self.assertEqual(assessment.graph.block_sizes, (3, 2))
        self.assertEqual(assessment.graph.color_count_bound, "exact")
        self.assertEqual(assessment.check("color_phases").status, "pass")
        self.assertEqual(assessment.check("topology_locality").status, "not_evaluated")

    def test_rectangular_grid_is_bipartite_and_reports_degree_distribution(self) -> None:
        rows, columns = 3, 4
        variables = tuple((row, column) for row in range(rows) for column in range(columns))
        edges: dict[tuple[tuple[int, int], tuple[int, int]], float] = {}
        for row in range(rows):
            for column in range(columns):
                if row + 1 < rows:
                    edges[((row, column), (row + 1, column))] = -0.5
                if column + 1 < columns:
                    edges[((row, column), (row, column + 1))] = -0.5
        assessment = assess_target_admissibility(
            compile_ising({}, edges, variables=variables),
            _target(pbit_capacity=12, max_degree=4, max_color_phases=2),
        )

        self.assertEqual(assessment.graph.edge_count, 17)
        self.assertEqual(assessment.graph.maximum_degree, 4)
        self.assertEqual(assessment.graph.degree_histogram, ((2, 4), (3, 6), (4, 2)))
        self.assertTrue(assessment.graph.is_bipartite)
        self.assertEqual(assessment.graph.block_count, 2)
        self.assertEqual(assessment.check("color_phases").status, "pass")
        self.assertEqual(assessment.status, "conditional")

    def test_complete_graph_phase_limit_is_a_proven_hard_failure(self) -> None:
        variables = tuple(range(5))
        edges = {(left, right): 0.25 for left in variables for right in variables if left < right}
        assessment = assess_target_admissibility(
            compile_ising({}, edges, variables=variables),
            _target(pbit_capacity=5, max_degree=4, max_color_phases=4),
        )

        self.assertEqual(assessment.status, "inadmissible")
        self.assertTrue(assessment.graph.is_complete)
        self.assertEqual(assessment.graph.density, 1.0)
        self.assertEqual(assessment.graph.coloring_method, "deterministic DSATUR")
        self.assertEqual(assessment.graph.color_count_bound, "exact")
        self.assertEqual(assessment.graph.known_chromatic_lower_bound, 5)
        phase_check = assessment.check("color_phases")
        self.assertEqual(phase_check.status, "fail")
        self.assertIn("lower bound 5", phase_check.reason)

    def test_isolated_variables_make_topology_vacuous_and_can_be_admissible(self) -> None:
        variables = ("a", "b", "c")
        assessment = assess_target_admissibility(
            compile_ising({}, variables=variables),
            _target(
                pbit_capacity=3,
                max_degree=0,
                max_color_phases=1,
                coefficient_format=FixedPointSpec(0, 2),
            ),
        )

        self.assertEqual(assessment.status, "admissible")
        self.assertEqual(assessment.graph.connected_component_count, 3)
        self.assertEqual(assessment.graph.connected_component_sizes, (1, 1, 1))
        self.assertEqual(assessment.graph.degree_histogram, ((0, 3),))
        self.assertEqual(assessment.graph.block_sizes, (3,))
        self.assertEqual(assessment.check("topology_locality").status, "pass")


class ConstraintDecisionTests(unittest.TestCase):
    def test_capacity_and_degree_boundaries_pass_but_one_below_fails(self) -> None:
        model = compile_ising({}, {(0, 1): 0.25}, variables=(0, 1))
        boundary = assess_target_admissibility(
            model,
            _target(pbit_capacity=2, max_degree=1, max_color_phases=2),
        )
        self.assertEqual(boundary.check("pbit_capacity").status, "pass")
        self.assertEqual(boundary.check("maximum_degree").status, "pass")

        capacity_failure = assess_target_admissibility(
            model,
            _target(pbit_capacity=1, max_degree=1, max_color_phases=2),
        )
        self.assertEqual(capacity_failure.status, "inadmissible")
        self.assertEqual(capacity_failure.check("pbit_capacity").status, "fail")

        degree_failure = assess_target_admissibility(
            model,
            _target(pbit_capacity=2, max_degree=0, max_color_phases=2),
        )
        self.assertEqual(degree_failure.status, "inadmissible")
        self.assertEqual(degree_failure.check("maximum_degree").status, "fail")

    def test_unknown_target_facts_are_not_guessed(self) -> None:
        model = compile_ising({}, {(0, 1): 1.0}, variables=(0, 1))
        assessment = assess_target_admissibility(model, TSUSpec("unknown-target"))

        self.assertEqual(assessment.status, "conditional")
        self.assertEqual(
            {row.name for row in assessment.checks if row.status == "not_evaluated"},
            {
                "pbit_capacity",
                "maximum_degree",
                "color_phases",
                "coefficient_format",
                "topology_locality",
            },
        )

    def test_accumulator_range_failure_prevents_admissible_status(self) -> None:
        target = TSUSpec(
            name="narrow-accumulator",
            accumulator_format=FixedPointSpec(0, 0),
            provenance={
                "accumulator_format": ParameterProvenance(
                    "assumed",
                    "unit-test accumulator fixture",
                    sensitivity_note="compare wider signed accumulators",
                )
            },
        )
        assessment = assess_target_admissibility(
            compile_ising({"x": 0.5}),
            target,
        )

        self.assertEqual(assessment.status, "inadmissible")
        accumulator = assessment.check("accumulator_format")
        self.assertEqual(accumulator.status, "fail")
        self.assertIn("0.5", str(accumulator.observed))
        self.assertIn("[-1.0, 0.0]", str(accumulator.limit))

    def test_accumulator_pass_requires_range_and_grid_representability(self) -> None:
        target = TSUSpec(
            name="accumulator-grid",
            accumulator_format=FixedPointSpec(1, 1),
            provenance={
                "accumulator_format": ParameterProvenance(
                    "assumed",
                    "unit-test accumulator fixture",
                    sensitivity_note="compare accumulator width and fractional precision",
                )
            },
        )
        exact = assess_target_admissibility(
            compile_ising(
                {"x": 0.5},
                {("x", "y"): 0.5},
                variables=("x", "y"),
            ),
            target,
        )
        self.assertEqual(exact.check("accumulator_format").status, "pass")
        self.assertEqual(
            exact.check("accumulator_format").observed,
            "[-0.5, 1.0]",
        )

        rounded = assess_target_admissibility(
            compile_ising({"x": 0.25}),
            target,
        )
        self.assertEqual(rounded.status, "conditional")
        self.assertEqual(
            rounded.check("accumulator_format").status,
            "not_evaluated",
        )
        self.assertIn("not exactly representable", rounded.check("accumulator_format").reason)

    def test_accumulator_uses_implemented_quantized_coefficients(self) -> None:
        target = TSUSpec(
            name="quantized-accumulator",
            coefficient_format=FixedPointSpec(1, 0, rounding="toward_zero"),
            accumulator_format=FixedPointSpec(0, 1),
            provenance={
                parameter: ParameterProvenance(
                    "assumed",
                    f"unit-test {parameter} fixture",
                    sensitivity_note="compare alternate fixed-point formats",
                )
                for parameter in ("coefficient_format", "accumulator_format")
            },
        )
        assessment = assess_target_admissibility(
            compile_ising({"x": 0.75}),
            target,
        )

        self.assertEqual(
            assessment.quantization.maximum_absolute_coefficient_error,
            0.75,
        )
        self.assertEqual(
            assessment.quantization.zeroed_nonzero_count,
            1,
        )
        accumulator = assessment.check("accumulator_format")
        self.assertEqual(accumulator.status, "pass")
        self.assertEqual(accumulator.observed, "[0.0, 0.0]")

    def test_topology_capacity_is_used_when_scalar_capacity_is_absent(self) -> None:
        topology = ExplicitTopology(node_count=1, edges=())
        target = TSUSpec(
            name="one-node-topology",
            topology=topology,
            provenance={
                "topology": ParameterProvenance(
                    "assumed",
                    "unit-test topology fixture",
                    sensitivity_note="compare topologies with more nodes",
                )
            },
        )
        assessment = assess_target_admissibility(
            compile_ising({}, variables=("a", "b")),
            target,
        )

        self.assertEqual(assessment.status, "inadmissible")
        capacity = assessment.check("pbit_capacity")
        self.assertEqual(capacity.status, "fail")
        self.assertEqual(capacity.limit, 1)
        self.assertIn("topology capacity", capacity.reason)

    def test_topology_locality_reason_distinguishes_topology_from_placement(self) -> None:
        topology = ExplicitTopology(node_count=2, edges=((0, 1),))
        target = TSUSpec(
            name="two-node-topology",
            topology=topology,
            provenance={
                "topology": ParameterProvenance(
                    "assumed",
                    "unit-test topology fixture",
                    sensitivity_note="compare alternate physical adjacencies",
                )
            },
        )
        assessment = assess_target_admissibility(
            compile_ising({}, {("a", "b"): 1.0}, variables=("a", "b")),
            target,
        )

        locality = assessment.check("topology_locality")
        self.assertEqual(locality.status, "not_evaluated")
        self.assertIn("physical topology", locality.reason)
        self.assertIn("placement", locality.reason)
        self.assertNotIn("has no physical topology", locality.reason)

    def test_dsatur_upper_bound_above_limit_without_matching_lower_bound_is_conditional(self) -> None:
        # A wheel with an odd rim needs four colors, but the deliberately cheap
        # assessment records only the generic non-bipartite lower bound of three.
        rim = tuple(range(5))
        hub = 5
        edges = {(rim[i], rim[(i + 1) % len(rim)]): 1.0 for i in range(len(rim))}
        edges.update({(vertex, hub): 1.0 for vertex in rim})
        assessment = assess_target_admissibility(
            compile_ising({}, edges, variables=(*rim, hub)),
            _target(pbit_capacity=6, max_degree=5, max_color_phases=3),
        )

        self.assertEqual(assessment.graph.block_count, 4)
        self.assertEqual(assessment.graph.color_count_bound, "upper_bound")
        self.assertEqual(assessment.check("color_phases").status, "not_evaluated")
        self.assertIn("does not prove infeasibility", assessment.check("color_phases").reason)
        self.assertEqual(assessment.status, "conditional")

    def test_reject_overflow_becomes_evidence_not_an_exception(self) -> None:
        assessment = assess_target_admissibility(
            compile_ising({"high": 2.0}),
            _target(
                pbit_capacity=1,
                max_degree=0,
                max_color_phases=1,
                coefficient_format=FixedPointSpec(0, 1, overflow="reject"),
            ),
        )

        self.assertEqual(assessment.status, "inadmissible")
        self.assertEqual(assessment.check("coefficient_format").status, "fail")
        self.assertEqual(assessment.quantization.status, "failed")
        self.assertEqual(assessment.quantization.out_of_range_count, 1)
        self.assertIn("overflow='reject'", assessment.quantization.reason)

    def test_saturation_is_computed_and_is_a_hard_range_failure(self) -> None:
        assessment = assess_target_admissibility(
            compile_ising({"high": 2.0, "low": -2.0}),
            _target(
                pbit_capacity=2,
                max_degree=0,
                max_color_phases=1,
                coefficient_format=FixedPointSpec(0, 1, overflow="saturate"),
            ),
        )

        self.assertEqual(assessment.status, "inadmissible")
        self.assertEqual(assessment.quantization.status, "computed")
        self.assertEqual(assessment.quantization.saturation_count, 2)
        self.assertEqual(assessment.quantization.out_of_range_count, 2)
        self.assertEqual(assessment.check("coefficient_format").observed, 2)

    def test_in_range_rounding_without_an_acceptance_threshold_is_conditional(self) -> None:
        assessment = assess_target_admissibility(
            compile_ising({"rounded": 0.2}),
            _target(
                pbit_capacity=1,
                max_degree=0,
                max_color_phases=1,
                coefficient_format=FixedPointSpec(1, 2),
            ),
        )

        self.assertEqual(assessment.status, "conditional")
        self.assertEqual(assessment.quantization.out_of_range_count, 0)
        self.assertGreater(assessment.quantization.maximum_absolute_coefficient_error or 0.0, 0.0)
        self.assertEqual(assessment.check("coefficient_format").status, "not_evaluated")
        self.assertIn("no acceptable", assessment.check("coefficient_format").reason)

    def test_beta_scaled_numeric_overflow_is_explicit(self) -> None:
        assessment = assess_target_admissibility(
            compile_ising({"high": 1e308}),
            _target(
                pbit_capacity=1,
                max_degree=0,
                max_color_phases=1,
                coefficient_format=FixedPointSpec(4, 2),
            ),
            beta=2.0,
        )
        self.assertEqual(assessment.status, "inadmissible")
        self.assertEqual(assessment.quantization.nonfinite_effective_count, 1)
        self.assertIn("must be finite", assessment.quantization.reason)

    def test_extreme_saturation_remains_explicit_if_a_later_bound_overflows(self) -> None:
        assessment = assess_target_admissibility(
            compile_ising({"high": 1e308}),
            _target(
                pbit_capacity=1,
                max_degree=0,
                max_color_phases=1,
                coefficient_format=FixedPointSpec(4, 2, overflow="saturate"),
            ),
        )

        self.assertEqual(assessment.status, "inadmissible")
        self.assertEqual(assessment.quantization.status, "failed")
        self.assertEqual(assessment.quantization.out_of_range_count, 1)
        self.assertEqual(assessment.quantization.saturation_count, 1)
        self.assertIn("local logit error bound", assessment.quantization.reason)


class FixedBetaTopologyTests(unittest.TestCase):
    def test_beta_zero_uses_edgeless_effective_graph_and_proves_uniformity(self) -> None:
        variables = ("a", "b", "c")
        model = compile_ising(
            {"a": 3.0, "b": -2.0, "c": 1.0},
            {("a", "b"): 1.0, ("a", "c"): -1.0, ("b", "c"): 2.0},
            variables=variables,
        )
        assessment = assess_target_admissibility(
            model,
            _target(
                pbit_capacity=3,
                max_degree=0,
                max_color_phases=1,
                coefficient_format=FixedPointSpec(0, 0),
            ),
            beta=-0.0,
        )

        self.assertEqual(assessment.beta, 0.0)
        self.assertEqual(assessment.status, "admissible")
        self.assertEqual(
            assessment.graph_basis,
            "fixed_beta_zero_effective_interaction_graph",
        )
        self.assertEqual(assessment.logical_edge_count, 3)
        self.assertEqual(assessment.graph.edge_count, 0)
        self.assertEqual(assessment.graph.maximum_degree, 0)
        self.assertEqual(assessment.graph.connected_component_sizes, (1, 1, 1))
        self.assertEqual(assessment.graph.block_sizes, (3,))
        self.assertEqual(assessment.check("maximum_degree").status, "pass")
        self.assertEqual(assessment.check("color_phases").status, "pass")
        self.assertEqual(assessment.check("topology_locality").status, "pass")
        self.assertIn(
            "assessed fixed-beta interaction graph is edgeless",
            assessment.check("topology_locality").reason,
        )
        self.assertTrue(assessment.quantization.exactly_representable)
        self.assertEqual(assessment.quantization.exact_total_variation, 0.0)
        self.assertEqual(assessment.quantization.exact_num_states, 8)
        payload = assessment.to_dict()
        self.assertEqual(payload["schema_version"], "hardware-assessment-v2")
        self.assertEqual(payload["graph_basis"], "fixed_beta_zero_effective_interaction_graph")
        self.assertEqual(payload["logical_edge_count"], 3)
        json.dumps(payload, allow_nan=False)

    def test_beta_zero_does_not_remove_variable_capacity(self) -> None:
        model = compile_ising({}, {("a", "b"): 1.0}, variables=("a", "b", "c"))
        assessment = assess_target_admissibility(
            model,
            _target(
                pbit_capacity=2,
                max_degree=0,
                max_color_phases=1,
                coefficient_format=FixedPointSpec(0, 0),
            ),
            beta=0.0,
        )

        self.assertEqual(assessment.status, "inadmissible")
        self.assertEqual(assessment.graph.variable_count, 3)
        self.assertEqual(assessment.check("pbit_capacity").status, "fail")
        self.assertEqual(assessment.check("maximum_degree").status, "pass")

    def test_positive_beta_requires_the_original_nonzero_interaction_graph(self) -> None:
        model = compile_ising({}, {("a", "b"): 1.0}, variables=("a", "b"))
        assessment = assess_target_admissibility(
            model,
            _target(
                pbit_capacity=2,
                max_degree=0,
                max_color_phases=1,
                coefficient_format=FixedPointSpec(2, 0),
            ),
            beta=1.0,
        )

        self.assertEqual(assessment.status, "inadmissible")
        self.assertEqual(assessment.graph_basis, "logical_interaction_graph")
        self.assertEqual(assessment.logical_edge_count, 1)
        self.assertEqual(assessment.graph.edge_count, 1)
        self.assertEqual(assessment.check("maximum_degree").status, "fail")
        self.assertEqual(assessment.check("color_phases").status, "fail")
        self.assertEqual(assessment.check("topology_locality").status, "not_evaluated")
        self.assertIn(
            "not a reusable multi-beta schedule certificate",
            assessment.to_dict()["scope"]["temperature_scope"],
        )


class QuantizationAndSerializationTests(unittest.TestCase):
    def test_exact_comparison_is_included_only_within_state_cap(self) -> None:
        variables = tuple(range(5))
        model = compile_ising(
            {variable: 0.13 for variable in variables},
            {(left, left + 1): 0.27 for left in range(4)},
            variables=variables,
        )
        target = _target(
            pbit_capacity=5,
            max_degree=2,
            max_color_phases=2,
            coefficient_format=FixedPointSpec(2, 3),
        )
        exact = assess_target_admissibility(model, target, max_exact_variables=5)
        skipped = assess_target_admissibility(model, target, max_exact_variables=4)

        self.assertEqual(exact.quantization.exact_comparison_status, "computed")
        self.assertEqual(exact.quantization.exact_num_states, 32)
        self.assertIsNotNone(exact.quantization.exact_total_variation)
        self.assertEqual(
            skipped.quantization.exact_comparison_status,
            "not_computed_too_many_variables",
        )
        self.assertIsNone(skipped.quantization.exact_num_states)
        self.assertIsNone(skipped.quantization.to_dict()["exact_comparison"])
        self.assertIn("max_exact_variables=4", skipped.quantization.exact_comparison_reason or "")

    def test_arbitrary_hashable_labels_do_not_leak_into_json_evidence(self) -> None:
        labels = ((_OpaqueLabel(), 1), 7, "plain")
        model = compile_ising(
            {labels[0]: 0.125, labels[1]: -0.25},
            {(labels[0], labels[1]): 0.375, (labels[1], labels[2]): -0.5},
            variables=labels,
        )
        assessment = assess_target_admissibility(
            model,
            _target(
                pbit_capacity=3,
                max_degree=2,
                max_color_phases=2,
                coefficient_format=FixedPointSpec(2, 3),
            ),
        )

        json.dumps(assessment.to_dict(), allow_nan=False)
        self.assertEqual(assessment.graph.variable_count, 3)

    def test_records_are_immutable_and_serialization_is_detached(self) -> None:
        assessment = assess_target_admissibility(
            compile_ising({"a": 0.25}),
            _target(
                pbit_capacity=1,
                max_degree=0,
                max_color_phases=1,
                coefficient_format=FixedPointSpec(1, 2),
            ),
        )
        with self.assertRaises(FrozenInstanceError):
            assessment.status = "conditional"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            assessment.checks[0] = assessment.checks[0]  # type: ignore[index]

        payload = assessment.to_dict()
        payload["checks"][0]["status"] = "fail"
        self.assertEqual(assessment.checks[0].status, "pass")
        json.dumps(assessment.to_dict(), allow_nan=False)

    def test_large_sparse_path_smoke_uses_linear_space_graph_analysis(self) -> None:
        variable_count = 20_000
        variables = tuple(range(variable_count))
        model = compile_ising(
            {},
            {(left, left + 1): 1.0 for left in range(variable_count - 1)},
            variables=variables,
        )
        assessment = assess_target_admissibility(
            model,
            _target(
                pbit_capacity=variable_count,
                max_degree=2,
                max_color_phases=2,
            ),
            max_exact_variables=0,
        )

        self.assertEqual(assessment.graph.variable_count, variable_count)
        self.assertEqual(assessment.graph.edge_count, variable_count - 1)
        self.assertEqual(assessment.graph.connected_component_sizes, (variable_count,))
        self.assertEqual(assessment.graph.block_sizes, (10_000, 10_000))
        self.assertEqual(assessment.check("color_phases").status, "pass")


class InputValidationTests(unittest.TestCase):
    def test_rejects_invalid_inputs(self) -> None:
        model = compile_ising({"a": 0.0})
        target = TSUSpec("unknown")
        for beta in (-1.0, True, float("nan"), float("inf")):
            with self.subTest(beta=beta), self.assertRaises(ValueError):
                assess_target_admissibility(model, target, beta=beta)
        for cap in (-1, True, 1.5):
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                assess_target_admissibility(
                    model,
                    target,
                    max_exact_variables=cap,  # type: ignore[arg-type]
                )
        with self.assertRaises(TypeError):
            assess_target_admissibility("model", target)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            assess_target_admissibility(model, "target")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
