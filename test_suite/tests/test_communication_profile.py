"""Independent contracts for the Aadit S4-S5 communication profiler."""

from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.communication_profile import (  # noqa: E402
    MAX_EXACT_CHAIN_PARTITIONS,
    ChainCommunicationProfile,
    PairCommunicationCost,
    evaluate_potts_assignment,
    profile_chain_communication,
    search_optimal_chain_order,
)
from gibbsiq.conversions import compile_ising  # noqa: E402


class _CollidingPartitionLabel:
    def __repr__(self) -> str:
        return "same-partition-repr"


def pair_row(
    profile: ChainCommunicationProfile,
    left: object,
    right: object,
) -> PairCommunicationCost:
    target = {left, right}
    for row in profile.pair_costs:
        if {row.partition_a, row.partition_b} == target:
            return row
    raise AssertionError(f"no pair row for {left!r}, {right!r}")


class PaperEquationTests(unittest.TestCase):
    def test_reproduces_dsim1_b46_paper_pair_proxy(self) -> None:
        source_vertices = tuple(("p4", index) for index in range(660))
        destination = ("p6", 0)
        singleton_vertices = {label: (f"p{label}", 0) for label in (1, 2, 3, 5)}
        variables = tuple(singleton_vertices.values()) + source_vertices + (destination,)
        model = compile_ising(
            {},
            {(source, destination): 1.0 for source in source_vertices},
            variables=variables,
        )
        partitions = {
            1: (singleton_vertices[1],),
            2: (singleton_vertices[2],),
            3: (singleton_vertices[3],),
            4: source_vertices,
            5: (singleton_vertices[5],),
            6: (destination,),
        }
        f_comm = 100_000_000.0
        profile = profile_chain_communication(
            model,
            partitions,
            chain_order=(1, 2, 3, 4, 5, 6),
            link_usable_pins=(54, 30, 54, 26, 54),
            num_colors=3,
            communication_frequency_hz=f_comm,
        )

        row = pair_row(profile, 4, 6)
        expected_cost = 660 * 2 / 26
        expected_eta = 2 * 3 * expected_cost
        self.assertEqual(row.b_a_to_b, 660)
        self.assertEqual(row.b_b_to_a, 1)
        self.assertEqual(row.b_ab, 660)
        self.assertEqual(row.d_ab, 2)
        self.assertEqual(row.route_link_indices, (3, 4))
        self.assertEqual(row.p_ab, 26)
        self.assertAlmostEqual(row.c_ab, expected_cost)
        self.assertAlmostEqual(profile.paper_pair_c_max, 50.76923076923077)
        self.assertAlmostEqual(profile.paper_pair_c_tot, expected_cost)
        self.assertAlmostEqual(profile.paper_pair_eta_proxy, 304.61538461538464)
        self.assertAlmostEqual(
            row.paper_pair_tau_proxy_seconds,
            2 * expected_cost / f_comm,
        )
        self.assertAlmostEqual(
            profile.paper_pair_tau_proxy_seconds,
            3 * row.paper_pair_tau_proxy_seconds,
        )
        self.assertAlmostEqual(
            profile.paper_pair_frequency_proxy_hz or 0.0,
            f_comm / expected_eta,
        )

    def test_boundary_demand_counts_unique_vertices_not_cut_edges(self) -> None:
        left = ("a0", "a1")
        right = ("b0", "b1", "b2")
        cut_edges = {(a, b): 1.0 for a in left for b in right}
        model = compile_ising({}, cut_edges, variables=left + right)
        profile = profile_chain_communication(
            model,
            {"A": left, "B": right},
            chain_order=("A", "B"),
            link_usable_pins=(1,),
            num_colors=1,
            communication_frequency_hz=1.0,
        )
        row = pair_row(profile, "A", "B")
        self.assertEqual(len(cut_edges), 6)
        self.assertEqual(row.b_a_to_b, 2)
        self.assertEqual(row.b_b_to_a, 3)
        self.assertEqual(row.b_ab, 3)
        self.assertEqual(row.boundary_collapse_policy, "max_directed")
        self.assertNotEqual(row.b_ab, len(cut_edges))

    def test_asymmetric_directed_counts_are_partition_label_invariant(self) -> None:
        left = ("a0", "a1")
        right = ("b0", "b1", "b2")
        model = compile_ising(
            {},
            {(a, b): 1.0 for a in left for b in right},
            variables=left + right,
        )
        baseline = profile_chain_communication(
            model,
            {"left": left, "right": right},
            chain_order=("left", "right"),
            link_usable_pins=(11,),
            num_colors=2,
            communication_frequency_hz=5_000.0,
        )
        relabeled = profile_chain_communication(
            model,
            {99: right, ("partition", 1): left},
            chain_order=(("partition", 1), 99),
            link_usable_pins=(11,),
            num_colors=2,
            communication_frequency_hz=5_000.0,
        )
        baseline_row = baseline.pair_costs[0]
        relabeled_row = relabeled.pair_costs[0]
        self.assertEqual(
            {baseline_row.b_a_to_b, baseline_row.b_b_to_a},
            {relabeled_row.b_a_to_b, relabeled_row.b_b_to_a},
        )
        self.assertEqual(baseline_row.b_ab, relabeled_row.b_ab)
        self.assertEqual(baseline.paper_pair_c_tot, relabeled.paper_pair_c_tot)
        self.assertEqual(baseline.paper_pair_c_max, relabeled.paper_pair_c_max)
        self.assertEqual(baseline.composite_eta_proxy, relabeled.composite_eta_proxy)


class ChainRoutingTests(unittest.TestCase):
    def test_multihop_route_uses_narrowest_link(self) -> None:
        model = compile_ising({}, {("a", "d"): 1.0}, variables=("a", "b", "c", "d"))
        profile = profile_chain_communication(
            model,
            {"A": ("a",), "B": ("b",), "C": ("c",), "D": ("d",)},
            chain_order=("A", "B", "C", "D"),
            link_usable_pins=(100, 7, 50),
            num_colors=1,
            communication_frequency_hz=1_000.0,
        )
        row = pair_row(profile, "A", "D")
        self.assertEqual(row.d_ab, 3)
        self.assertEqual(row.route_link_indices, (0, 1, 2))
        self.assertEqual(row.p_ab, 7)
        self.assertAlmostEqual(row.c_ab, 3 / 7)

    def test_nonpalindromic_pins_make_reversed_orders_distinguishable(self) -> None:
        model = compile_ising({}, {("a", "b"): 1.0}, variables=("a", "b", "c"))
        partitions = {"A": ("a",), "B": ("b",), "C": ("c",)}
        forward = profile_chain_communication(
            model,
            partitions,
            chain_order=("A", "B", "C"),
            link_usable_pins=(5, 100),
            num_colors=1,
            communication_frequency_hz=1_000.0,
        )
        reversed_order = profile_chain_communication(
            model,
            partitions,
            chain_order=("C", "B", "A"),
            link_usable_pins=(5, 100),
            num_colors=1,
            communication_frequency_hz=1_000.0,
        )
        self.assertAlmostEqual(forward.paper_pair_c_max, 1 / 5)
        self.assertAlmostEqual(reversed_order.paper_pair_c_max, 1 / 100)
        self.assertNotEqual(forward.paper_pair_c_max, reversed_order.paper_pair_c_max)

        search = search_optimal_chain_order(
            model,
            partitions,
            link_usable_pins=(5, 100),
            num_colors=1,
            communication_frequency_hz=1_000.0,
        )
        self.assertFalse(search.reversal_reduction_applied)
        self.assertEqual(search.orders_evaluated, math.factorial(3))
        self.assertEqual(
            search.search_method,
            "exhaustive_permutations_without_invalid_reversal_reduction",
        )
        self.assertAlmostEqual(search.profile.paper_pair_c_max, 1 / 100)

    def test_shared_central_link_exceeds_paper_worst_pair_proxy(self) -> None:
        left_partitions = tuple(range(5))
        right_partitions = tuple(range(5, 10))
        variables = left_partitions + right_partitions
        model = compile_ising(
            {},
            {(left, right): 1.0 for left in left_partitions for right in right_partitions},
            variables=variables,
        )
        profile = profile_chain_communication(
            model,
            {partition: (partition,) for partition in variables},
            chain_order=variables,
            link_usable_pins=(1,) * 9,
            num_colors=2,
            communication_frequency_hz=2.0,
        )

        # There are 25 active K5,5 partition pairs. The farthest route has
        # distance nine, but all 25 frames cross the central physical link.
        self.assertEqual(profile.possible_unordered_pair_count, 45)
        self.assertEqual(profile.active_pair_count, 25)
        self.assertEqual(len(profile.pair_costs), 25)
        self.assertEqual(profile.paper_pair_c_tot, 125.0)
        self.assertEqual(profile.paper_pair_c_max, 9.0)
        self.assertEqual(profile.paper_pair_tau_proxy_seconds, 18.0)
        self.assertEqual(
            tuple(row.aggregate_boundary_bits for row in profile.link_loads),
            (5, 10, 15, 20, 25, 20, 15, 10, 5),
        )
        self.assertEqual(profile.max_link_aggregate_load, 25.0)
        self.assertEqual(profile.worst_link_indices, (4,))
        self.assertEqual(profile.aggregate_link_tau_proxy_seconds, 50.0)
        self.assertEqual(profile.composite_work_proxy, 25.0)
        self.assertEqual(profile.composite_tau_proxy_seconds, 50.0)
        self.assertIn("not measured latency", profile.to_dict()["interpretation"])

    def test_symmetric_six_slot_search_uses_360_reversal_classes(self) -> None:
        variables = tuple(range(6))
        model = compile_ising(
            {},
            {(index, index + 1): 1.0 for index in range(5)},
            variables=variables,
        )
        partitions = {index: (index,) for index in variables}
        search = search_optimal_chain_order(
            model,
            partitions,
            link_usable_pins=(10, 10, 10, 10, 10),
            num_colors=2,
            communication_frequency_hz=10_000.0,
        )
        self.assertTrue(search.reversal_reduction_applied)
        self.assertEqual(search.orders_evaluated, math.factorial(6) // 2)
        self.assertEqual(search.profile.chain_order, variables)
        self.assertAlmostEqual(search.profile.paper_pair_c_max, 0.1)
        self.assertEqual(
            search.optimality_status,
            "proven_exact_for_composite_proxy_objective",
        )

        reverse = profile_chain_communication(
            model,
            partitions,
            chain_order=tuple(reversed(variables)),
            link_usable_pins=(10, 10, 10, 10, 10),
            num_colors=2,
            communication_frequency_hz=10_000.0,
        )
        self.assertEqual(reverse.paper_pair_c_max, search.profile.paper_pair_c_max)
        self.assertEqual(reverse.paper_pair_c_tot, search.profile.paper_pair_c_tot)

    def test_search_refuses_above_declared_exact_limit(self) -> None:
        variables = tuple(range(MAX_EXACT_CHAIN_PARTITIONS + 1))
        model = compile_ising({}, variables=variables)
        partitions = {variable: (variable,) for variable in variables}
        with self.assertRaisesRegex(ValueError, "no unproven heuristic fallback"):
            search_optimal_chain_order(
                model,
                partitions,
                link_usable_pins=(10,) * (len(variables) - 1),
                num_colors=1,
                communication_frequency_hz=1.0,
            )
        with self.assertRaisesRegex(ValueError, "audited hard limit"):
            search_optimal_chain_order(
                model,
                partitions,
                link_usable_pins=(10,) * (len(variables) - 1),
                num_colors=1,
                communication_frequency_hz=1.0,
                exact_partition_limit=MAX_EXACT_CHAIN_PARTITIONS + 1,
            )


class DegenerateAndValidationTests(unittest.TestCase):
    def test_disconnected_no_traffic_result_is_finite_and_json_safe(self) -> None:
        model = compile_ising({}, {("a", "b"): 2.0}, variables=("a", "b", "c"))
        profile = profile_chain_communication(
            model,
            {"component": ("a", "b"), "isolated": ("c",)},
            chain_order=("component", "isolated"),
            link_usable_pins=(8,),
            num_colors=2,
            communication_frequency_hz=1_000.0,
        )
        self.assertFalse(profile.has_boundary_traffic)
        self.assertEqual(profile.pair_costs, ())
        self.assertEqual(profile.paper_pair_c_tot, 0.0)
        self.assertEqual(profile.paper_pair_c_max, 0.0)
        self.assertEqual(profile.composite_tau_proxy_seconds, 0.0)
        self.assertEqual(profile.composite_eta_proxy, 0.0)
        self.assertIsNone(profile.composite_frequency_proxy_hz)
        self.assertEqual(profile.proxy_frequency_status, "inactive_no_boundary_traffic")
        self.assertIsNone(profile.paper_worst_pair)
        json.dumps(profile.to_dict(), allow_nan=False)

    def test_single_partition_is_supported_without_physical_links(self) -> None:
        model = compile_ising({}, {("a", "b"): 1.0}, variables=("a", "b"))
        profile = profile_chain_communication(
            model,
            {"only": ("a", "b")},
            chain_order=("only",),
            link_usable_pins=(),
            num_colors=2,
            communication_frequency_hz=10.0,
        )
        self.assertEqual(profile.pair_costs, ())
        self.assertEqual(profile.link_loads, ())
        self.assertEqual(profile.paper_pair_c_tot, 0.0)
        self.assertIsNone(profile.composite_frequency_proxy_hz)

    def test_single_partition_search_does_not_claim_reversal_reduction(self) -> None:
        model = compile_ising({}, variables=("a",))
        result = search_optimal_chain_order(
            model,
            {"only": ("a",)},
            link_usable_pins=(),
            num_colors=1,
            communication_frequency_hz=10.0,
        )

        self.assertEqual(result.orders_evaluated, 1)
        self.assertFalse(result.reversal_reduction_applied)
        self.assertEqual(result.search_method, "exhaustive_single_partition_order")
        self.assertEqual(result.profile.chain_order, ("only",))

    def test_no_edge_400_partition_report_keeps_only_linear_rows(self) -> None:
        variables = tuple(range(400))
        profile = profile_chain_communication(
            compile_ising({}, variables=variables),
            {variable: (variable,) for variable in variables},
            chain_order=variables,
            link_usable_pins=(8,) * 399,
            num_colors=1,
            communication_frequency_hz=1_000.0,
        )
        payload = profile.to_dict()

        self.assertEqual(profile.possible_unordered_pair_count, 79_800)
        self.assertEqual(profile.active_pair_count, 0)
        self.assertEqual(profile.pair_costs, ())
        self.assertEqual(len(profile.partition_summaries), 400)
        self.assertEqual(len(profile.link_loads), 399)
        self.assertEqual(payload["pair_costs"], [])
        self.assertEqual(len(payload["partition_summaries"]), 400)
        self.assertEqual(len(payload["link_loads"]), 399)
        json.dumps(payload, allow_nan=False)

    def test_no_edge_2000_partition_validation_smoke(self) -> None:
        variables = tuple(range(2_000))
        profile = profile_chain_communication(
            compile_ising({}, variables=variables),
            {variable: (variable,) for variable in variables},
            chain_order=tuple(reversed(variables)),
            link_usable_pins=(1,) * (len(variables) - 1),
            num_colors=1,
            communication_frequency_hz=1.0,
        )

        self.assertEqual(profile.active_pair_count, 0)
        self.assertEqual(len(profile.partition_summaries), len(variables))
        self.assertEqual(len(profile.link_loads), len(variables) - 1)

    def test_colliding_partition_audit_keys_are_rejected(self) -> None:
        first = _CollidingPartitionLabel()
        second = _CollidingPartitionLabel()
        with self.assertRaisesRegex(ValueError, "canonical sort key"):
            profile_chain_communication(
                compile_ising({}, variables=("a", "b")),
                {first: ("a",), second: ("b",)},
                chain_order=(first, second),
                link_usable_pins=(1,),
                num_colors=1,
                communication_frequency_hz=1.0,
            )

    def test_partition_coverage_rejects_missing_unknown_duplicate_and_empty(self) -> None:
        model = compile_ising({}, variables=("a", "b"))
        invalid_partitions = (
            {"one": ("a",)},
            {"one": ("a", "b", "c")},
            {"one": ("a",), "two": ("a", "b")},
            {"one": ("a", "b"), "two": ()},
            {},
        )
        for partitions in invalid_partitions:
            with self.subTest(partitions=partitions), self.assertRaises(ValueError):
                profile_chain_communication(
                    model,
                    partitions,
                    chain_order=tuple(partitions),
                    link_usable_pins=(1,) * max(0, len(partitions) - 1),
                    num_colors=1,
                    communication_frequency_hz=1.0,
                )

    def test_partition_coverage_rejects_equality_alias_variables(self) -> None:
        aliases = (
            (True, 1),
            ((True,), (1,)),
            (frozenset({True}), frozenset({1})),
        )
        for supplied_variable, model_variable in aliases:
            with self.subTest(
                supplied_variable=supplied_variable,
                model_variable=model_variable,
            ):
                model = compile_ising({}, variables=(model_variable,))
                with self.assertRaisesRegex(ValueError, "cover model variables exactly"):
                    profile_chain_communication(
                        model,
                        {"one": (supplied_variable,)},
                        chain_order=("one",),
                        link_usable_pins=(),
                        num_colors=1,
                        communication_frequency_hz=1.0,
                    )

    def test_invalid_chain_orders_routes_and_clocks_are_rejected(self) -> None:
        model = compile_ising({}, {("a", "b"): 1.0}, variables=("a", "b"))
        partitions = {"A": ("a",), "B": ("b",)}
        invalid_cases = (
            {"chain_order": ("A", "A"), "link_usable_pins": (1,)},
            {"chain_order": ("A",), "link_usable_pins": (1,)},
            {"chain_order": ("A", "B"), "link_usable_pins": ()},
            {"chain_order": ("A", "B"), "link_usable_pins": (0,)},
            {"chain_order": ("A", "B"), "link_usable_pins": (True,)},
        )
        for case in invalid_cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                profile_chain_communication(
                    model,
                    partitions,
                    chain_order=case["chain_order"],
                    link_usable_pins=case["link_usable_pins"],
                    num_colors=1,
                    communication_frequency_hz=1.0,
                )
        with self.assertRaisesRegex(ValueError, "partition label exactly once"):
            profile_chain_communication(
                compile_ising({}, variables=("a",)),
                {1: ("a",)},
                chain_order=(True,),
                link_usable_pins=(),
                num_colors=1,
                communication_frequency_hz=1.0,
            )
        for colors in (0, True, 1.5):
            with self.subTest(colors=colors), self.assertRaises(ValueError):
                profile_chain_communication(
                    model,
                    partitions,
                    chain_order=("A", "B"),
                    link_usable_pins=(1,),
                    num_colors=colors,  # type: ignore[arg-type]
                    communication_frequency_hz=1.0,
                )
        for frequency in (0.0, -1.0, True, float("nan"), float("inf")):
            with self.subTest(frequency=frequency), self.assertRaises(ValueError):
                profile_chain_communication(
                    model,
                    partitions,
                    chain_order=("A", "B"),
                    link_usable_pins=(1,),
                    num_colors=1,
                    communication_frequency_hz=frequency,
                )

    def test_extreme_clock_that_would_serialize_infinity_is_rejected(self) -> None:
        model = compile_ising({}, {("a", "b"): 1.0}, variables=("a", "b"))
        with self.assertRaisesRegex(ValueError, "paper pair timing proxy"):
            profile_chain_communication(
                model,
                {"A": ("a",), "B": ("b",)},
                chain_order=("A", "B"),
                link_usable_pins=(1,),
                num_colors=1,
                communication_frequency_hz=5e-324,
            )

    def test_huge_color_count_has_controlled_numeric_error(self) -> None:
        model = compile_ising({}, {("a", "b"): 1.0}, variables=("a", "b"))
        with self.assertRaisesRegex(ValueError, "finite binary64 reporting domain"):
            profile_chain_communication(
                model,
                {"A": ("a",), "B": ("b",)},
                chain_order=("A", "B"),
                link_usable_pins=(1,),
                num_colors=10**400,
                communication_frequency_hz=1.0,
            )

    def test_positive_cost_and_time_underflow_are_rejected_not_reported_as_zero(self) -> None:
        model = compile_ising({}, {("a", "b"): 1.0}, variables=("a", "b"))
        partitions = {"A": ("a",), "B": ("b",)}
        with self.assertRaisesRegex(ValueError, "positive pair communication cost underflowed"):
            profile_chain_communication(
                model,
                partitions,
                chain_order=("A", "B"),
                link_usable_pins=(10**400,),
                num_colors=1,
                communication_frequency_hz=1.0,
            )

        # 2**-1074 is representable as the smallest positive binary64 cost,
        # but dividing it by this valid clock underflows the positive time.
        with self.assertRaisesRegex(ValueError, "positive paper pair timing proxy underflowed"):
            profile_chain_communication(
                model,
                partitions,
                chain_order=("A", "B"),
                link_usable_pins=(1 << 1074,),
                num_colors=1,
                communication_frequency_hz=1e308,
            )


class ScalingAndSerializationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = compile_ising({}, {("a", "b"): 1.0}, variables=("a", "b"))
        self.partitions = {"A": ("a",), "B": ("b",)}

    def profile(self, *, pins: int = 10, colors: int = 2, frequency: float = 1_000.0):
        return profile_chain_communication(
            self.model,
            self.partitions,
            chain_order=("A", "B"),
            link_usable_pins=(pins,),
            num_colors=colors,
            communication_frequency_hz=frequency,
        )

    def test_frequency_pin_and_color_monotonicity(self) -> None:
        baseline = self.profile()
        faster_communication = self.profile(frequency=2_000.0)
        wider_link = self.profile(pins=20)
        more_colors = self.profile(colors=4)

        self.assertEqual(faster_communication.paper_pair_c_max, baseline.paper_pair_c_max)
        self.assertEqual(faster_communication.composite_eta_proxy, baseline.composite_eta_proxy)
        self.assertAlmostEqual(
            faster_communication.composite_tau_proxy_seconds,
            baseline.composite_tau_proxy_seconds / 2,
        )
        self.assertAlmostEqual(
            faster_communication.composite_frequency_proxy_hz or 0.0,
            2 * (baseline.composite_frequency_proxy_hz or 0.0),
        )
        self.assertAlmostEqual(wider_link.paper_pair_c_max, baseline.paper_pair_c_max / 2)
        self.assertAlmostEqual(wider_link.composite_eta_proxy, baseline.composite_eta_proxy / 2)
        self.assertAlmostEqual(
            wider_link.composite_frequency_proxy_hz or 0.0,
            2 * (baseline.composite_frequency_proxy_hz or 0.0),
        )
        self.assertAlmostEqual(
            more_colors.composite_eta_proxy,
            2 * baseline.composite_eta_proxy,
        )
        self.assertAlmostEqual(
            more_colors.composite_tau_proxy_seconds,
            2 * baseline.composite_tau_proxy_seconds,
        )
        self.assertAlmostEqual(
            more_colors.composite_frequency_proxy_hz or 0.0,
            (baseline.composite_frequency_proxy_hz or 0.0) / 2,
        )

    def test_arbitrary_labels_serialize_without_nonfinite_values(self) -> None:
        variables = (1, "x", ("z", 3))
        model = compile_ising({}, {(1, "x"): 1.0}, variables=variables)
        profile = profile_chain_communication(
            model,
            {7: (1,), ("tile", 1): ("x", ("z", 3))},
            chain_order=(7, ("tile", 1)),
            link_usable_pins=(4,),
            num_colors=2,
            communication_frequency_hz=1_000.0,
        )
        payload = profile.to_dict()
        json.dumps(payload, allow_nan=False)
        self.assertEqual(payload["chain_order"], [7, ["tile", 1]])
        self.assertIn("boundary_ambiguity", payload)

    def test_search_result_is_json_safe_and_records_scope(self) -> None:
        result = search_optimal_chain_order(
            self.model,
            self.partitions,
            link_usable_pins=(10,),
            num_colors=2,
            communication_frequency_hz=1_000.0,
        )
        payload = result.to_dict()
        json.dumps(payload, allow_nan=False)
        self.assertIn("supplied partition", payload["scope_limit"])
        self.assertEqual(
            payload["objective"],
            [
                "composite_work_proxy",
                "max_link_aggregate_load",
                "paper_pair_c_max",
                "paper_pair_c_tot",
                "canonical_partition_order",
            ],
        )


class PottsObjectiveTests(unittest.TestCase):
    def test_equation_s7_is_evaluated_for_supplied_assignment_only(self) -> None:
        model = compile_ising(
            {},
            {
                ("a", "b"): -2.0,
                ("a", "c"): 3.0,
                ("b", "d"): -4.0,
                ("c", "d"): 5.0,
            },
            variables=("a", "b", "c", "d"),
        )
        evaluation = evaluate_potts_assignment(
            model,
            {"P0": ("a", "b"), "P1": ("c",), "P2": ("d",)},
            partition_order=("P0", "P1", "P2"),
            delta_near=1.0,
            delta_far=10.0,
            balance_penalty_lambda=0.5,
        )
        # Internal edge a-b contributes zero.  The three cut edges contribute
        # 3*1 + 4*10 + 5*1 = 48.  Sizes (2,1,1) give lambda*(2/3) = 1/3.
        self.assertAlmostEqual(evaluation.interaction_term, 48.0)
        self.assertAlmostEqual(evaluation.balance_term, 1 / 3)
        self.assertAlmostEqual(evaluation.total, 48 + 1 / 3)
        self.assertIn("no optimization", evaluation.to_dict()["scope"])
        json.dumps(evaluation.to_dict(), allow_nan=False)

    def test_potts_objective_validates_kernel_penalty_and_order(self) -> None:
        model = compile_ising({}, {("a", "b"): 1.0}, variables=("a", "b"))
        partitions = {"A": ("a",), "B": ("b",)}
        invalid = (
            {"delta_near": 0.0, "delta_far": 2.0, "balance_penalty_lambda": 1.0},
            {"delta_near": 2.0, "delta_far": 2.0, "balance_penalty_lambda": 1.0},
            {"delta_near": 1.0, "delta_far": 2.0, "balance_penalty_lambda": 0.0},
        )
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                evaluate_potts_assignment(
                    model,
                    partitions,
                    partition_order=("A", "B"),
                    **kwargs,
                )
        with self.assertRaisesRegex(ValueError, "partition label exactly once"):
            evaluate_potts_assignment(
                model,
                partitions,
                partition_order=("A", "A"),
                delta_near=1.0,
                delta_far=2.0,
                balance_penalty_lambda=1.0,
            )


if __name__ == "__main__":
    unittest.main()
