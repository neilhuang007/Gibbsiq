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
from gibbsiq.communication_profile import (
    ChainCommunicationProfile,
    ChainOrderSearchResult,
    PottsObjectiveEvaluation,
    evaluate_potts_assignment,
    profile_chain_communication,
    search_optimal_chain_order,
)
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
from gibbsiq.domain_wall import DomainWallEncoding, compile_domain_wall
from gibbsiq.exact_distribution import (
    DistributionComparison,
    ExactDistribution,
    ExactDistributionNumericalError,
    compare_boltzmann_distributions,
    exact_boltzmann_distribution,
)
from gibbsiq.hardware import FixedPointSpec, ParameterProvenance, TSUSpec
from gibbsiq.hardware_assessment import HardwareAssessment, assess_target_admissibility
from gibbsiq.model import IsingModel, binary_to_spin, spin_to_binary
from gibbsiq.quantization import QuantizationAnalysis, analyze_quantization
from gibbsiq.result import ResultVartype, SampleResult
from gibbsiq.thrml_runtime import SamplerConfig, THRMLSampler

# package version; pyproject.toml reads it through [tool.setuptools.dynamic].
__version__ = "0.1.0"

__all__ = [
    "BlockPartition",
    "CategoricalModel",
    "ChainCommunicationProfile",
    "ChainOrderSearchResult",
    "DistributionComparison",
    "DomainWallEncoding",
    "ExactDistribution",
    "ExactDistributionNumericalError",
    "FixedPointSpec",
    "HardwareAssessment",
    "IsingModel",
    "IsoenergeticClusterMove",
    "ParameterProvenance",
    "PottsObjectiveEvaluation",
    "QuantizationAnalysis",
    "ResultVartype",
    "SampleResult",
    "SamplerConfig",
    "THRMLSampler",
    "TSUSpec",
    "__version__",
    "analyze_quantization",
    "assess_target_admissibility",
    "binary_to_spin",
    "candidate_from_result",
    "chain_flags",
    "chain_section",
    "color_blocks",
    "compare_boltzmann_distributions",
    "compile_bqm",
    "compile_domain_wall",
    "compile_fixture",
    "compile_ising",
    "compile_qubo",
    "compute_diagnostics",
    "diagnostic_candidate_from_input",
    "distance_to_best_trace",
    "diversity_flags",
    "diversity_observations",
    "diversity_section",
    "energy_flags",
    "energy_section",
    "ess_mean",
    "evaluate_potts_assignment",
    "exact_boltzmann_distribution",
    "graph_density",
    "isoenergetic_cluster_move",
    "magnetization_trace",
    "optimal_spin_witnesses",
    "profile_chain_communication",
    "rank_normalized_split_rhat",
    "search_optimal_chain_order",
    "spin_to_binary",
    "split_chains",
    "split_rhat",
    "state_counts",
    "validate_partition",
    "verify_optimum_claim",
]
