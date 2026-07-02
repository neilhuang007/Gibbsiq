"""THRML-native optimization infrastructure for QUBO / Ising / BQM models."""

from gibbsiq.benchmark_bridge import (
    candidate_from_result,
    compile_fixture,
    optimal_spin_witnesses,
    verify_optimum_claim,
)
from gibbsiq.blocks import BlockPartition, color_blocks, graph_density, validate_partition
from gibbsiq.conversions import compile_bqm, compile_ising, compile_qubo
from gibbsiq.model import IsingModel, binary_to_spin, spin_to_binary
from gibbsiq.result import ResultVartype, SampleResult
from gibbsiq.thrml_runtime import SamplerConfig, THRMLSampler

__all__ = [
    "BlockPartition",
    "IsingModel",
    "ResultVartype",
    "SampleResult",
    "SamplerConfig",
    "THRMLSampler",
    "__version__",
    "binary_to_spin",
    "candidate_from_result",
    "color_blocks",
    "compile_bqm",
    "compile_fixture",
    "compile_ising",
    "compile_qubo",
    "graph_density",
    "optimal_spin_witnesses",
    "spin_to_binary",
    "validate_partition",
    "verify_optimum_claim",
]

__version__ = "0.1.0"
