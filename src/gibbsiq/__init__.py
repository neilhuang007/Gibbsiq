"""THRML-native optimization infrastructure for QUBO / Ising / BQM models."""

from gibbsiq.categorical import CategoricalModel

from gibbsiq.conversions import compile_bqm, compile_ising, compile_qubo

from gibbsiq.model import IsingModel, binary_to_spin, spin_to_binary

from gibbsiq.program import PROGRAM_SCHEMA_VERSION, ThermodynamicProgram

from gibbsiq.result import ResultVartype, SampleResult

__version__ = "0.2.0a1"

__all__ = [
    "CategoricalModel",
    "IsingModel",
    "PROGRAM_SCHEMA_VERSION",
    "ResultVartype",
    "SampleResult",
    "ThermodynamicProgram",
    "__version__",
    "binary_to_spin",
    "compile_bqm",
    "compile_ising",
    "compile_qubo",
    "spin_to_binary",
]
