"""Diagnostics-first QUBO / Ising / BQM tooling."""

from gibbsiq.conversions import compile_bqm, compile_ising, compile_qubo
from gibbsiq.model import IsingModel, binary_to_spin, spin_to_binary
from gibbsiq.result import SampleResult

__all__ = [
    "IsingModel",
    "SampleResult",
    "__version__",
    "binary_to_spin",
    "compile_bqm",
    "compile_ising",
    "compile_qubo",
    "spin_to_binary",
]

__version__ = "0.1.0"
