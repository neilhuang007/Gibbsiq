"""Public-package smoke test for the reviewed ThermoMap analysis tranche."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

import gibbsiq  # noqa: E402
from gibbsiq import (  # noqa: E402
    CategoricalModel,
    ChainCommunicationProfile,
    ChainOrderSearchResult,
    CommunicationSpec,
    CubicMonomialLowering,
    DistributionComparison,
    DomainWallEncoding,
    EmpiricalInterval,
    EmpiricalVerificationReport,
    ExactDistribution,
    ExactDistributionNumericalError,
    ExactTransitionKernel,
    ExplicitTopology,
    FixedPointSpec,
    GridTopology,
    HardwareAssessment,
    HostTransferSpec,
    Inspector,
    IsoenergeticClusterMove,
    KnapsackEncoding,
    ParameterProvenance,
    PhysicalQuantity,
    PottsObjectiveEvaluation,
    PROGRAM_SCHEMA_VERSION,
    ProgrammingSpec,
    QuantizationAnalysis,
    ReferenceGibbsSampler,
    ReferenceSampleResult,
    ReferenceSamplerConfig,
    ReferenceTransitionEvent,
    SampleResult,
    TSUSpec,
    ThermodynamicProgram,
    TransitionVerificationReport,
    TspEncoding,
    analyze_quantization,
    assess_target_admissibility,
    build_exact_transition_kernel,
    compare_boltzmann_distributions,
    compile_domain_wall,
    compile_ising,
    compile_knapsack,
    compile_tsp,
    evaluate_potts_assignment,
    exact_boltzmann_distribution,
    isoenergetic_cluster_move,
    profile_chain_communication,
    reduce_cubic_monomial,
    search_optimal_chain_order,
    verify_empirical_distribution,
    verify_transition_kernel,
    verify_transition_matrix,
)


THERMOMAP_PUBLIC_NAMES = (
    "CategoricalModel",
    "ChainCommunicationProfile",
    "ChainOrderSearchResult",
    "CommunicationSpec",
    "CubicMonomialLowering",
    "DistributionComparison",
    "DomainWallEncoding",
    "EmpiricalInterval",
    "EmpiricalVerificationReport",
    "ExactDistribution",
    "ExactDistributionNumericalError",
    "ExactTransitionKernel",
    "ExplicitTopology",
    "FixedPointSpec",
    "GridTopology",
    "HardwareAssessment",
    "HostTransferSpec",
    "Inspector",
    "IsoenergeticClusterMove",
    "KnapsackEncoding",
    "ParameterProvenance",
    "PhysicalQuantity",
    "PottsObjectiveEvaluation",
    "PROGRAM_SCHEMA_VERSION",
    "ProgrammingSpec",
    "QuantizationAnalysis",
    "ReferenceGibbsSampler",
    "ReferenceSampleResult",
    "ReferenceSamplerConfig",
    "ReferenceTransitionEvent",
    "TSUSpec",
    "ThermodynamicProgram",
    "TransitionVerificationReport",
    "TspEncoding",
    "analyze_quantization",
    "assess_target_admissibility",
    "build_exact_transition_kernel",
    "compare_boltzmann_distributions",
    "compile_domain_wall",
    "compile_ising",
    "compile_knapsack",
    "compile_tsp",
    "evaluate_potts_assignment",
    "exact_boltzmann_distribution",
    "isoenergetic_cluster_move",
    "profile_chain_communication",
    "reduce_cubic_monomial",
    "search_optimal_chain_order",
    "verify_empirical_distribution",
    "verify_transition_kernel",
    "verify_transition_matrix",
)


class ThermoMapPublicApiTests(unittest.TestCase):
    def test_public_export_list_is_unique_ordered_and_excludes_private_labels(self) -> None:
        self.assertEqual(len(gibbsiq.__all__), len(set(gibbsiq.__all__)))
        exported_tranche = tuple(name for name in gibbsiq.__all__ if name in THERMOMAP_PUBLIC_NAMES)
        self.assertEqual(exported_tranche, THERMOMAP_PUBLIC_NAMES)
        self.assertNotIn("_DomainWallVariable", gibbsiq.__all__)
        self.assertFalse(hasattr(gibbsiq, "_DomainWallVariable"))
        for name in THERMOMAP_PUBLIC_NAMES:
            with self.subTest(name=name):
                self.assertTrue(hasattr(gibbsiq, name))
        self.assertEqual(PROGRAM_SCHEMA_VERSION, gibbsiq.PROGRAM_SCHEMA_VERSION)
        self.assertIs(ThermodynamicProgram, gibbsiq.ThermodynamicProgram)
        self.assertTrue(issubclass(ExactDistributionNumericalError, ValueError))

    def test_tiny_end_to_end_analysis_path_uses_only_public_imports(self) -> None:
        categorical = CategoricalModel(
            variables=("left", "right"),
            domains={"left": (0, 1), "right": ("off", "on")},
            pairwise={
                ("left", "right"): {
                    (0, "off"): 0.0,
                    (0, "on"): 0.0,
                    (1, "off"): 0.0,
                    (1, "on"): 1.0,
                }
            },
            offset=1.5,
        )
        encoding = compile_domain_wall(categorical, penalty=2.0)
        self.assertIsInstance(encoding, DomainWallEncoding)
        self.assertEqual(len(encoding.variables), 2)

        fixed_point = FixedPointSpec(4, 3)
        provenance = ParameterProvenance("assumed", "public API smoke-test fixture")
        target = TSUSpec(
            name="smoke-test-target",
            pbit_capacity=2,
            max_degree=1,
            max_color_phases=2,
            coefficient_format=fixed_point,
            provenance={
                "pbit_capacity": provenance,
                "max_degree": provenance,
                "max_color_phases": provenance,
                "coefficient_format": provenance,
            },
        )
        assessment = assess_target_admissibility(
            encoding.ising_model,
            target,
            beta=1.0,
        )
        self.assertIsInstance(assessment, HardwareAssessment)
        self.assertEqual(assessment.graph.variable_count, 2)
        self.assertEqual(assessment.quantization.status, "computed")

        quantization = analyze_quantization(
            encoding.ising_model,
            fixed_point,
            beta=1.0,
        )
        self.assertIsInstance(quantization, QuantizationAnalysis)
        self.assertTrue(quantization.exactly_representable)
        comparison = compare_boltzmann_distributions(
            encoding.ising_model,
            quantization.implemented_effective_model,
            target_beta=1.0,
            implemented_beta=1.0,
        )
        self.assertIsInstance(comparison, DistributionComparison)
        self.assertEqual(comparison.total_variation, 0.0)
        exact = exact_boltzmann_distribution(encoding.ising_model, 1.0)
        self.assertIsInstance(exact, ExactDistribution)
        self.assertEqual(len(exact.states), 4)

        left_wall, right_wall = encoding.variables
        partitions = {
            "device-left": (left_wall,),
            "device-right": (right_wall,),
        }
        communication = profile_chain_communication(
            encoding.ising_model,
            partitions,
            chain_order=("device-left", "device-right"),
            link_usable_pins=(8,),
            num_colors=assessment.graph.block_count,
            communication_frequency_hz=1_000_000.0,
        )
        self.assertIsInstance(communication, ChainCommunicationProfile)
        self.assertTrue(communication.has_boundary_traffic)

        order_search = search_optimal_chain_order(
            encoding.ising_model,
            partitions,
            link_usable_pins=(8,),
            num_colors=assessment.graph.block_count,
            communication_frequency_hz=1_000_000.0,
        )
        self.assertIsInstance(order_search, ChainOrderSearchResult)
        self.assertEqual(
            order_search.optimality_status,
            "proven_exact_for_composite_proxy_objective",
        )
        potts_objective = evaluate_potts_assignment(
            encoding.ising_model,
            partitions,
            partition_order=("device-left", "device-right"),
            delta_near=1.0,
            delta_far=2.0,
            balance_penalty_lambda=0.5,
        )
        self.assertIsInstance(potts_objective, PottsObjectiveEvaluation)

        replica_a = {left_wall: -1, right_wall: -1}
        replica_b = {left_wall: 1, right_wall: 1}
        move = isoenergetic_cluster_move(
            encoding.ising_model,
            replica_a,
            replica_b,
            component_index=0,
        )
        self.assertIsInstance(move, IsoenergeticClusterMove)
        metadata = move.to_metadata()
        self.assertTrue(metadata["combined_energy_invariant"])
        self.assertFalse(metadata["replicas_are_independent"])
        self.assertEqual(metadata["semantics"], "optimization_only_replica_coupling")

    def test_new_frontier_types_compose_through_public_imports(self) -> None:
        cubic = reduce_cubic_monomial(
            ("left", "middle", "right"),
            coefficient=-1.0,
            penalty=2.0,
            offset=0.5,
        )
        self.assertIsInstance(cubic, CubicMonomialLowering)
        self.assertEqual(
            cubic.decode({"left": 1, "middle": 1, "right": 0, cubic.ancilla: 1}),
            {
                "left": 1,
                "middle": 1,
                "right": 0,
            },
        )

        knapsack = compile_knapsack((2, 3), (4, 5), 3)
        self.assertIsInstance(knapsack, KnapsackEncoding)
        self.assertEqual(knapsack.penalty_policy.selection, "derived_strict")
        tsp = compile_tsp(((0, 1, 2), (1, 0, 3), (2, 3, 0)))
        self.assertIsInstance(tsp, TspEncoding)
        self.assertEqual(tsp.penalty_policy.selection, "derived_strict")

        model = compile_ising({"spin": 0.25}, variables=("spin",), offset=1.5)
        sampler = ReferenceGibbsSampler(
            ReferenceSamplerConfig(
                beta=0.75,
                n_warmup=2,
                seed=17,
                initialization="all_up",
            )
        )
        result = sampler.sample(model, num_reads=4)
        self.assertIsInstance(result, ReferenceSampleResult)
        self.assertTrue(all(isinstance(event, ReferenceTransitionEvent) for event in result.transitions))

        kernel = build_exact_transition_kernel(model, 0.75)
        self.assertIsInstance(kernel, ExactTransitionKernel)
        transition_report = verify_transition_kernel(model, 0.75, kernel)
        self.assertIsInstance(transition_report, TransitionVerificationReport)
        self.assertTrue(transition_report.passed)
        self.assertTrue(verify_transition_matrix(model, 0.75, kernel.matrix, states=kernel.states).passed)

        empirical = verify_empirical_distribution(
            model,
            [{"spin": -1}, {"spin": -1}, {"spin": 1}, {"spin": -1}],
            0.75,
        )
        self.assertIsInstance(empirical, EmpiricalVerificationReport)
        self.assertTrue(all(isinstance(interval, EmpiricalInterval) for interval in empirical.intervals))

        stored = SampleResult.from_model(model, ({"spin": -1}, {"spin": 1}))
        self.assertEqual(
            Inspector.from_result(stored, model=model).to_dict()["model_association"]["status"],
            "caller_supplied_sample_checked",
        )

        topology = GridTopology(shape=(1,), neighbor_offsets=())
        self.assertIsInstance(topology, GridTopology)
        self.assertIsInstance(ExplicitTopology(node_count=1, edges=()), ExplicitTopology)
        assumed_topology = ParameterProvenance(
            "assumed",
            "public API smoke-test topology",
            sensitivity_note="single-cell exact scenario",
        )
        complete_target = TSUSpec(
            name="single-cell-target",
            topology=topology,
            communication=CommunicationSpec(),
            host_transfer=HostTransferSpec(),
            programming=ProgrammingSpec(),
            provenance={"topology": assumed_topology},
        )
        self.assertEqual(complete_target.to_dict()["topology"]["shape"], [1])

        assumed_quantity = ParameterProvenance("assumed", "public API physical scenario")
        fact = PhysicalQuantity(1.0, "second", 0.5, 2.0, assumed_quantity)
        self.assertEqual(fact.unit, "second")


if __name__ == "__main__":
    unittest.main()
