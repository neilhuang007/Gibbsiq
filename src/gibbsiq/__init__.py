"""THRML-native optimization infrastructure for QUBO / Ising / BQM models."""

from gibbsiq.categorical import CategoricalModel

from gibbsiq.conversions import compile_bqm, compile_ising, compile_qubo

from gibbsiq.model import IsingModel, binary_to_spin, spin_to_binary

__version__ = "0.2.0a1"

__all__ = [
    "CategoricalModel",
    "IsingModel",
    "__version__",
    "binary_to_spin",
    "compile_bqm",
    "compile_ising",
    "compile_qubo",
    "spin_to_binary",
]
