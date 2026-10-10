"""THRML-native optimization infrastructure for QUBO / Ising / BQM models."""

from gibbsiq.benchmark_bridge import (
    candidate_from_result,
    compile_fixture,
    optimal_spin_witnesses,
    verify_optimum_claim,
)

from gibbsiq.blocks import BlockPartition, color_blocks, graph_density, validate_partition

from gibbsiq.categorical import CategoricalModel

from gibbsiq.cluster_moves import IsoenergeticClusterMove, isoenergetic_cluster_move

from gibbsiq.constraints import KnapsackEncoding, TspEncoding, compile_knapsack, compile_tsp

from gibbsiq.conversions import compile_bqm, compile_ising, compile_qubo

from gibbsiq.diagnostics import (
    chain_flags,
    chain_section,
    compute_diagnostics,
    diagnostic_candidate_from_input,
    distance_to_best_trace,
    diversity_flags,
    diversity_observations,
    diversity_section,
    energy_flags,
    energy_section,
    ess_mean,
    magnetization_trace,
    rank_normalized_split_rhat,
    split_chains,
    split_rhat,
    state_counts,
)

from gibbsiq.exact_distribution import (
    DistributionComparison,
    ExactDistribution,
    ExactDistributionNumericalError,
    compare_boltzmann_distributions,
    exact_boltzmann_distribution,
)

from gibbsiq.factor_lowering import CubicMonomialLowering, reduce_cubic_monomial

from gibbsiq.model import IsingModel, binary_to_spin, spin_to_binary

from gibbsiq.program import PROGRAM_SCHEMA_VERSION, ThermodynamicProgram

from gibbsiq.reference_sampler import (
    ReferenceGibbsSampler,
    ReferenceSampleResult,
    ReferenceSamplerConfig,
    ReferenceTransitionEvent,
)

from gibbsiq.result import ResultVartype, SampleResult

from gibbsiq.thrml_runtime import SamplerConfig, THRMLSampler

from gibbsiq.verification import (
    EmpiricalInterval,
    EmpiricalVerificationReport,
    ExactTransitionKernel,
    TransitionVerificationReport,
    build_exact_transition_kernel,
    verify_empirical_distribution,
    verify_transition_kernel,
    verify_transition_matrix,
)

__version__ = "0.2.0a1"

__all__ = [
    "BlockPartition",
    "CategoricalModel",
    "CubicMonomialLowering",
    "DistributionComparison",
    "EmpiricalInterval",
    "EmpiricalVerificationReport",
    "ExactDistribution",
    "ExactDistributionNumericalError",
    "ExactTransitionKernel",
    "IsingModel",
    "IsoenergeticClusterMove",
    "KnapsackEncoding",
    "PROGRAM_SCHEMA_VERSION",
    "ReferenceGibbsSampler",
    "ReferenceSampleResult",
    "ReferenceSamplerConfig",
    "ReferenceTransitionEvent",
    "ResultVartype",
    "SampleResult",
    "SamplerConfig",
    "THRMLSampler",
    "ThermodynamicProgram",
    "TransitionVerificationReport",
    "TspEncoding",
    "__version__",
    "binary_to_spin",
    "build_exact_transition_kernel",
    "candidate_from_result",
    "chain_flags",
    "chain_section",
    "color_blocks",
    "compare_boltzmann_distributions",
    "compile_bqm",
    "compile_fixture",
    "compile_ising",
    "compile_knapsack",
    "compile_qubo",
    "compile_tsp",
    "compute_diagnostics",
    "diagnostic_candidate_from_input",
    "distance_to_best_trace",
    "diversity_flags",
    "diversity_observations",
    "diversity_section",
    "energy_flags",
    "energy_section",
    "ess_mean",
    "exact_boltzmann_distribution",
    "graph_density",
    "isoenergetic_cluster_move",
    "magnetization_trace",
    "optimal_spin_witnesses",
    "rank_normalized_split_rhat",
    "reduce_cubic_monomial",
    "spin_to_binary",
    "split_chains",
    "split_rhat",
    "state_counts",
    "validate_partition",
    "verify_empirical_distribution",
    "verify_optimum_claim",
    "verify_transition_kernel",
    "verify_transition_matrix",
]
